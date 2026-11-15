"""Liveness and activation safety: downtime jailing and the activation power cap."""

import json
from pathlib import Path

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.time import Datetime

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
NODES = [f"{index:02x}" * 32 for index in range(0xA1, 0xA7)]
CANDIDATES = [f"{index:02x}" * 32 for index in range(0x10, 0x16)]
DRIVER = "__liveness_driver__"
START = Datetime(2026, 1, 1)


@pytest.fixture
def client(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    client.flush()
    return client


def _submit(client, name, args=None):
    source = (CONTRACTS_DIR / f"{name}.s.py").read_text(encoding="utf-8")
    client.submit(source, name=name, constructor_args=args or {})
    return client.get_contract_proxy(name)


def _deploy(client, nodes=4, **policy):
    currency = _submit(client, "currency", {"vk": "founder"})
    for name in ("dao", "rewards"):
        _submit(client, name)
    _submit(client, "chi_cost", {"initial_rate": 20})
    validators = _submit(
        client,
        "validators",
        {"genesis_nodes": NODES[:nodes], "genesis_registration_fee": 1000, **policy},
    )
    return currency, validators


def _record(validators, absent, block=1, now=START):
    return validators.record_liveness(
        absent=absent, signer=DRIVER, environment={"block_num": block, "now": now}
    )


def test_only_the_liveness_driver_records_liveness(client):
    _, validators = _deploy(client)
    with pytest.raises(AssertionError, match="Driver only"):
        validators.record_liveness(absent=[NODES[0]], signer=NODES[1])


def test_a_signature_resets_the_consecutive_missed_count(client):
    _, validators = _deploy(client, downtime_jail_blocks=5)
    for block in range(1, 4):
        _record(validators, [NODES[0]], block)
    assert validators.get_validator(account=NODES[0])["missed_blocks"] == 3

    _record(validators, [NODES[1]], 4)

    assert validators.get_validator(account=NODES[0])["missed_blocks"] == 0
    assert validators.get_validator(account=NODES[1])["missed_blocks"] == 1


def test_a_validator_absent_for_the_downtime_window_is_jailed_without_slash(client):
    currency, validators = _deploy(client, downtime_jail_blocks=3)
    currency.transfer(amount=100, to=NODES[0], signer="founder")
    currency.approve(amount=100, to="validators", signer=NODES[0])
    validators.bond_self(amount=100, signer=NODES[0])

    for block in range(1, 3):
        _record(validators, [NODES[0]], block)
    assert NODES[0] in validators.get_members()
    _record(validators, [NODES[0]], 3)

    record = validators.get_validator(account=NODES[0])
    assert NODES[0] not in validators.get_members()
    assert record["jailed"] is True and record["jail_reason"] == "downtime"
    assert record["power"] == 0 and record["self_bond"] == 100
    assert record["missed_blocks"] == 0


def test_a_configured_downtime_slash_is_applied(client):
    currency, validators = _deploy(client, downtime_jail_blocks=1, downtime_slash_bps=100)
    currency.transfer(amount=100, to=NODES[0], signer="founder")
    currency.approve(amount=100, to="validators", signer=NODES[0])
    validators.bond_self(amount=100, signer=NODES[0])

    _record(validators, [NODES[0]], 1)

    assert validators.get_validator(account=NODES[0])["self_bond"] == 99


def test_no_one_is_jailed_while_a_third_of_the_power_is_absent(client):
    _, validators = _deploy(client, nodes=6, downtime_jail_blocks=2)
    for block in range(1, 5):
        _record(validators, NODES[:2], block)  # 2 of 6 = 1/3: not more

    # Exactly a third absent is individual downtime: both are jailed.
    assert validators.get_members() == NODES[2:6]
    for block in range(5, 8):
        _record(validators, NODES[2:5], block)  # 3 of 4 active: a partition

    assert len(validators.get_members()) == 4


def test_the_last_active_validator_is_never_jailed_for_downtime(client):
    _, validators = _deploy(client, nodes=1, downtime_jail_blocks=1)

    _record(validators, [NODES[0]], 1)

    assert validators.get_members() == [NODES[0]]


def test_a_downtime_jailed_validator_unjails_itself_after_the_cooldown(client):
    _, validators = _deploy(
        client, nodes=5, downtime_jail_blocks=1, downtime_unjail_cooldown_hours=2
    )
    _record(validators, [NODES[0]], 1, now=START)

    with pytest.raises(AssertionError, match="cooldown"):
        validators.unjail(signer=NODES[0], environment={"now": Datetime(2026, 1, 1, 1)})
    validators.unjail(signer=NODES[0], environment={"now": Datetime(2026, 1, 1, 2)})

    record = validators.get_validator(account=NODES[0])
    assert record["jailed"] is False
    # Downtime is not malicious: back in the active set, manual mode too.
    assert record["status"] == "active" and NODES[0] in validators.get_members()
    assert record["power"] == 10 and record["missed_blocks"] == 0


def _jail_for_downtime(validators, account, block):
    _record(validators, [account], block)
    assert validators.get_validator(account=account)["jail_reason"] == "downtime"


def _unjail(validators, account, block):
    return validators.unjail(
        signer=account, environment={"block_num": block, "now": Datetime(2026, 1, 2)}
    )


def test_re_entry_respects_the_newcomer_cap_per_epoch(client):
    _, validators = _deploy(
        client,
        nodes=6,
        max_validators=10,
        rebalance_interval=100,
        downtime_jail_blocks=1,
        downtime_unjail_cooldown_hours=0,
        max_new_power_bps=2000,
    )
    _jail_for_downtime(validators, NODES[0], 1)
    _jail_for_downtime(validators, NODES[1], 2)

    _unjail(validators, NODES[0], 3)  # 10 of 50: within 20%
    with pytest.raises(AssertionError, match="retry next epoch"):
        _unjail(validators, NODES[1], 4)  # 20 of 60 newly admitted this epoch
    assert validators.get_validator(account=NODES[1])["jailed"] is True

    _unjail(validators, NODES[1], 100)  # the next epoch has its own budget

    assert validators.get_members() == NODES[2:6] + [NODES[0], NODES[1]]


def test_re_entry_into_a_small_set_waits_for_a_wider_cap(client):
    _, validators = _deploy(
        client, nodes=3, downtime_jail_blocks=1, downtime_unjail_cooldown_hours=0
    )
    _jail_for_downtime(validators, NODES[0], 1)

    # One of three is a third of the power: above the 20% cap.
    with pytest.raises(AssertionError, match="retry next epoch"):
        _unjail(validators, NODES[0], 2)


def test_re_entry_requires_the_minimum_stake(client):
    currency, validators = _deploy(
        client,
        nodes=5,
        downtime_jail_blocks=1,
        downtime_unjail_cooldown_hours=0,
        min_self_bond=50,
        min_total_bond=50,
    )
    _jail_for_downtime(validators, NODES[0], 1)

    with pytest.raises(AssertionError, match="minimum"):
        _unjail(validators, NODES[0], 2)
    currency.transfer(amount=50, to=NODES[0], signer="founder")
    currency.approve(amount=50, to="validators", signer=NODES[0])
    validators.bond_self(amount=50, signer=NODES[0])
    _unjail(validators, NODES[0], 3)

    assert NODES[0] in validators.get_members()


def test_without_a_free_seat_an_unjailed_validator_waits_as_a_candidate(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=4,
        max_new_power_bps=10000,
        downtime_jail_blocks=1,
        downtime_unjail_cooldown_hours=0,
    )
    _register(client, currency, validators, CANDIDATES[0], bond=10)
    _jail_for_downtime(validators, NODES[0], 1)  # the jail rebalance fills the seat
    assert CANDIDATES[0] in validators.get_members()

    _unjail(validators, NODES[0], 2)

    record = validators.get_validator(account=NODES[0])
    assert record["jailed"] is False and record["status"] == "approved"
    assert NODES[0] not in validators.get_members()


def test_an_evidence_jail_lifted_by_governance_keeps_manual_re_adding(client):
    _, validators = _deploy(client)
    validators.apply_evidence_penalty(
        member=NODES[0],
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        signer="__evidence_penalty_driver__",
    )
    validators.propose_vote(type_of_vote="unjail_member", arg=NODES[0], signer=NODES[1])
    for voter in NODES[2:4]:
        validators.vote(proposal_id=1, vote="yes", signer=voter)

    record = validators.get_validator(account=NODES[0])
    assert record["jailed"] is False and record["status"] == "approved"
    assert NODES[0] not in validators.get_members()


def test_only_downtime_jails_can_be_lifted_by_the_validator(client):
    _, validators = _deploy(client)
    validators.apply_evidence_penalty(
        member=NODES[0],
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        signer="__evidence_penalty_driver__",
    )
    assert validators.get_validator(account=NODES[0])["jailed"] is True

    with pytest.raises(AssertionError, match="downtime"):
        validators.unjail(signer=NODES[0], environment={"now": Datetime(2027, 1, 1)})


def _register(client, currency, validators, account, bond):
    currency.transfer(amount=1000 + bond, to=account, signer="founder")
    currency.approve(amount=1000 + bond, to="validators", signer=account)
    validators.register(signer=account)
    validators.bond_self(amount=bond, signer=account)


def test_newcomers_add_at_most_the_new_power_cap_per_rebalance(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=10,
        max_active_set_churn=5,
        max_new_power_bps=2000,
    )
    for account in CANDIDATES[:4]:
        _register(client, currency, validators, account, bond=10)

    result = validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    # 4 incumbents of equal power: one newcomer is 1/5 of the new set.
    assert len(result["activated"]) == 1
    assert len(validators.get_members()) == 5


def test_the_power_cap_also_limits_replacements(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=4,
        max_active_set_churn=4,
        max_new_power_bps=2500,
    )
    for account in CANDIDATES[:4]:
        _register(client, currency, validators, account, bond=10)

    validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    assert sum(account in validators.get_members() for account in CANDIDATES) == 1


def test_mainnet_pins_the_liveness_policy():
    bundle = json.loads((CONTRACTS_DIR / "contracts_mainnet.json").read_text())
    [entry] = [c for c in bundle["contracts"] if c["name"] == "validators"]
    args = entry["constructor_args"]

    assert args["max_new_power_bps"] == 2000
    assert 0 < args["downtime_jail_blocks"] < args["rebalance_interval"]
    assert args["downtime_slash_bps"] == 0
    assert args["downtime_unjail_cooldown_hours"] > 0


@pytest.mark.parametrize(
    "arg,message",
    [
        ({"max_new_power_bps": 10001}, "max_new_power_bps"),
        ({"downtime_jail_blocks": 0}, "downtime_jail_blocks"),
        ({"downtime_slash_bps": -1}, "downtime_slash_bps"),
        ({"downtime_unjail_cooldown_hours": -1}, "downtime_unjail_cooldown_hours"),
    ],
)
def test_policy_updates_validate_the_liveness_keys(client, arg, message):
    _, validators = _deploy(client)
    with pytest.raises(AssertionError, match=message):
        validators.propose_vote(type_of_vote="update_policy", arg=arg, signer=NODES[0])


def test_policy_updates_set_the_liveness_keys(client):
    _, validators = _deploy(client, nodes=1)
    validators.propose_vote(
        type_of_vote="update_policy",
        arg={"max_new_power_bps": 1000, "downtime_jail_blocks": 7},
        signer=NODES[0],
    )

    config = validators.get_policy_config()
    assert config["max_new_power_bps"] == 1000 and config["downtime_jail_blocks"] == 7


def test_one_miss_then_a_signature_resets_the_count(client):
    _, validators = _deploy(client, downtime_jail_blocks=5)
    _record(validators, [NODES[0]], 1)
    _record(validators, [NODES[1]], 2)

    assert validators.get_validator(account=NODES[0])["missed_blocks"] == 0


def test_a_missing_downtime_window_reads_as_the_default(client):
    _, validators = _deploy(client, downtime_jail_blocks=1)
    client.raw_driver.set("validators.config:downtime_jail_blocks", None)

    for block in range(1, 4):
        _record(validators, [NODES[0]], block)

    # The default window (500) applies: no jail after three misses.
    assert NODES[0] in validators.get_members()


def test_a_validator_starts_each_active_stint_with_no_missed_blocks(client):
    currency, validators = _deploy(
        client, selection_mode="auto_top_n", max_validators=5, max_new_power_bps=10000
    )
    _register(client, currency, validators, CANDIDATES[0], bond=10)
    # A count left from an earlier stint (an evidence jail keeps it).
    client.raw_driver.set(f"validators.missed_blocks:{CANDIDATES[0]}", 7)

    validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    assert CANDIDATES[0] in validators.get_members()
    assert validators.get_validator(account=CANDIDATES[0])["missed_blocks"] == 0


@pytest.mark.parametrize("newcomer_power,admitted", [(10, False), (9, True)])
def test_the_power_cap_holds_at_its_boundary(client, newcomer_power, admitted):
    currency, validators = _deploy(
        client,
        nodes=3,
        genesis_powers={node: 13 for node in NODES[:3]},
        selection_mode="auto_top_n",
        power_mode="requested",
        max_validators=5,
        max_new_power_bps=2000,
    )
    currency.transfer(amount=1010, to=CANDIDATES[0], signer="founder")
    currency.approve(amount=1010, to="validators", signer=CANDIDATES[0])
    validators.register(requested_validator_power=newcomer_power, signer=CANDIDATES[0])
    validators.bond_self(amount=10, signer=CANDIDATES[0])

    validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    # 10 of 49 is just above 20%, 9 of 48 below it.
    assert (CANDIDATES[0] in validators.get_members()) is admitted


def test_newcomers_fill_no_more_than_the_free_seats(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=5,
        max_active_set_churn=3,
        max_new_power_bps=10000,
    )
    for account in CANDIDATES[:3]:
        _register(client, currency, validators, account, bond=10)

    validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    assert len(validators.get_members()) == 5


@pytest.mark.parametrize("churn,replaced", [(0, 0), (1, 1), (2, 2)])
def test_replacements_spend_the_churn_budget(client, churn, replaced):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=4,
        max_active_set_churn=churn,
        min_bond_margin_bps=0,
        max_new_power_bps=10000,
    )
    for account in CANDIDATES[:3]:
        _register(client, currency, validators, account, bond=10)

    validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    # The set is full: newcomers only replace (unbonded) incumbents.
    members = validators.get_members()
    assert len(members) == 4
    assert sum(account in members for account in CANDIDATES) == replaced


@pytest.mark.parametrize(
    "arg,message",
    [
        ({"selection_mode": "bogus"}, "Bad selection_mode"),
        ({"duplicate_vote_jail": 1}, "duplicate_vote_jail must be boolean"),
        ({"max_validators": "5"}, "max_validators must be an integer"),
    ],
)
def test_policy_updates_name_the_refused_key(client, arg, message):
    _, validators = _deploy(client)
    with pytest.raises(AssertionError, match=message):
        validators.propose_vote(type_of_vote="update_policy", arg=arg, signer=NODES[0])


def test_a_validator_added_by_governance_starts_with_no_missed_blocks(client):
    currency, validators = _deploy(client, nodes=1)
    _register(client, currency, validators, CANDIDATES[0], bond=10)
    client.raw_driver.set(f"validators.missed_blocks:{CANDIDATES[0]}", 7)

    validators.propose_vote(type_of_vote="add_member", arg=CANDIDATES[0], signer=NODES[0])

    assert CANDIDATES[0] in validators.get_members()
    assert validators.get_validator(account=CANDIDATES[0])["missed_blocks"] == 0


def test_a_newcomer_that_filled_a_seat_does_not_also_replace(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=5,
        max_active_set_churn=2,
        min_bond_margin_bps=0,
        max_new_power_bps=10000,
    )
    _register(client, currency, validators, CANDIDATES[0], bond=20)
    _register(client, currency, validators, CANDIDATES[1], bond=10)

    validators.rebalance(signer=NODES[0], environment={"block_num": 1})

    # One seat filled (the stronger), one unbonded incumbent replaced.
    members = validators.get_members()
    assert len(members) == len(set(members)) == 5
    assert CANDIDATES[0] in members and CANDIDATES[1] in members


def test_rebalance_newcomers_and_re_entries_share_the_epoch_budget(client):
    currency, validators = _deploy(
        client,
        nodes=6,
        selection_mode="auto_top_n",
        max_validators=10,
        rebalance_interval=100,
        max_new_power_bps=2000,
        downtime_jail_blocks=1,
        downtime_unjail_cooldown_hours=0,
    )
    _register(client, currency, validators, CANDIDATES[0], bond=10)
    _jail_for_downtime(validators, NODES[0], 1)  # the jail rebalance admits C0
    assert CANDIDATES[0] in validators.get_members()

    with pytest.raises(AssertionError, match="retry next epoch"):
        _unjail(validators, NODES[0], 2)  # 20 of 70 admitted this epoch
    _unjail(validators, NODES[0], 100)

    assert NODES[0] in validators.get_members()
