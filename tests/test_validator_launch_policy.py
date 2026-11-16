"""The validator-set launch policy: manual start, minimum stake, bounded churn."""

import json
from pathlib import Path

import pytest
from contracting.local import ContractingClient

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
NODE1 = "a1" * 32
NODE2 = "b2" * 32
CANDIDATES = [f"{index:02x}" * 32 for index in range(16, 22)]


@pytest.fixture
def client(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    client.flush()
    return client


def _submit(client, name, args=None):
    source = (CONTRACTS_DIR / f"{name}.s.py").read_text(encoding="utf-8")
    client.submit(source, name=name, constructor_args=args or {})
    return client.get_contract_proxy(name)


def _deploy(client, **policy):
    currency = _submit(client, "currency", {"vk": "founder"})
    for name in ("dao", "rewards"):
        _submit(client, name)
    _submit(client, "chi_cost", {"initial_rate": 20})
    validators = _submit(
        client,
        "validators",
        {"genesis_nodes": [NODE1, NODE2], "genesis_registration_fee": 1000, **policy},
    )
    return currency, validators


def _register(client, currency, validators, account, bond=0, delegated=0):
    currency.transfer(amount=1000 + bond + delegated + 1, to=account, signer="founder")
    currency.approve(amount=1000 + bond, to="validators", signer=account)
    validators.register(signer=account)
    if bond:
        validators.bond_self(amount=bond, signer=account)
    if delegated:
        currency.transfer(amount=delegated, to="delegator", signer="founder")
        currency.approve(amount=delegated, to="validators", signer="delegator")
        validators.delegate(validator=account, amount=delegated, signer="delegator")


def test_filling_empty_slots_counts_against_the_churn_limit(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=7,
        max_active_set_churn=2,
        max_new_power_bps=10000,
    )
    for account in CANDIDATES[:5]:
        _register(client, currency, validators, account, bond=10)

    result = validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert len(result["activated"]) == 2
    assert len(validators.get_members()) == 4
    validators.rebalance(signer=NODE1, environment={"block_num": 2})
    assert len(validators.get_members()) == 6


def test_a_zero_churn_limit_admits_no_one_automatically(client):
    currency, validators = _deploy(client, selection_mode="auto_top_n", max_active_set_churn=0)
    _register(client, currency, validators, CANDIDATES[0], bond=10)

    validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert validators.get_members() == [NODE1, NODE2]


def test_manual_add_member_requires_the_minimum_stake(client):
    currency, validators = _deploy(client, min_self_bond=100, min_total_bond=300)
    candidate = CANDIDATES[0]
    _register(client, currency, validators, candidate, bond=99, delegated=500)
    with pytest.raises(AssertionError, match="minimum self bond"):
        validators.propose_vote(type_of_vote="add_member", arg=candidate, signer=NODE1)

    currency.transfer(amount=1, to=candidate, signer="founder")
    currency.approve(amount=1, to="validators", signer=candidate)
    validators.bond_self(amount=1, signer=candidate)
    validators.propose_vote(type_of_vote="add_member", arg=candidate, signer=NODE1)
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert candidate in validators.get_members()


def test_manual_add_member_requires_the_minimum_total_bond(client):
    currency, validators = _deploy(client, min_self_bond=100, min_total_bond=300)
    _register(client, currency, validators, CANDIDATES[0], bond=100, delegated=199)

    with pytest.raises(AssertionError, match="minimum total bond"):
        validators.propose_vote(type_of_vote="add_member", arg=CANDIDATES[0], signer=NODE1)


def test_an_add_member_vote_is_rejected_when_the_stake_fell_below_the_minimum(client):
    currency, validators = _deploy(client, min_self_bond=100)
    candidate = CANDIDATES[0]
    _register(client, currency, validators, candidate, bond=100)
    validators.propose_vote(type_of_vote="add_member", arg=candidate, signer=NODE1)
    validators.unbond_self(amount=1, signer=candidate)

    result = validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert result["status"] == "rejected"
    assert candidate not in validators.get_members()


def _mainnet_validator_args():
    bundle = json.loads((CONTRACTS_DIR / "contracts_mainnet.json").read_text())
    [validators] = [c for c in bundle["contracts"] if c["name"] == "validators"]
    return validators["constructor_args"]


def test_mainnet_starts_manual_with_a_minimum_stake():
    args = _mainnet_validator_args()

    assert args["selection_mode"] == "manual"
    assert args["min_self_bond"] > 0
    assert args["min_total_bond"] >= args["min_self_bond"]
    assert args["max_active_set_churn"] >= 1


def test_mainnet_registrants_cannot_take_the_set(client):
    """rv-genesis' sybil scenario: twelve fresh registrants with a token of bond."""
    args = _mainnet_validator_args()
    currency = _submit(client, "currency", {"vk": "founder"})
    for name in ("dao", "rewards"):
        _submit(client, name)
    _submit(client, "chi_cost", {"initial_rate": 20})
    validators = _submit(client, "validators", args)
    boot = args["genesis_nodes"][0]
    fee = args["genesis_registration_fee"]
    for index in range(1, 13):
        attacker = f"{index:02x}" * 32
        currency.transfer(amount=fee + 1, to=attacker, signer="founder")
        currency.approve(amount=fee + 1, to="validators", signer=attacker)
        validators.register(signer=attacker, environment={"block_num": 10})
        validators.bond_self(amount=1, signer=attacker, environment={"block_num": 10})

    with pytest.raises(AssertionError, match="Auto selection disabled"):
        validators.rebalance(signer="sys", environment={"block_num": 1440})
    with pytest.raises(AssertionError, match="Validators only"):
        validators.propose_vote(type_of_vote="add_member", arg="01" * 32, signer="01" * 32)
    with pytest.raises(AssertionError, match="minimum self bond"):
        validators.propose_vote(type_of_vote="add_member", arg="01" * 32, signer=boot)
    assert validators.get_members() == [boot]


def test_switching_from_manual_to_automatic_selection_is_one_policy_vote(client):
    currency, validators = _deploy(
        client, min_self_bond=100, max_validators=5, max_new_power_bps=10000
    )
    for node in (NODE1, NODE2):
        currency.transfer(amount=100, to=node, signer="founder")
        currency.approve(amount=100, to="validators", signer=node)
        validators.bond_self(amount=100, signer=node)
    for account in CANDIDATES[:3]:
        _register(client, currency, validators, account, bond=100)

    validators.propose_vote(
        type_of_vote="update_policy", arg={"selection_mode": "auto_top_n"}, signer=NODE1
    )
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    members = validators.get_members()
    assert NODE1 in members and NODE2 in members
    # The switch's own rebalance admits at most the churn limit (1).
    assert len(members) == 3


def _fill_selection_pool(client, currency, validators, stake_order="increasing"):
    accounts = [f"{index:064x}" for index in range(1, 65 - len(validators.get_members()))]
    for index, account in enumerate(accounts):
        bond = 100
        if stake_order == "increasing":
            bond += index
        elif stake_order == "decreasing":
            bond += len(accounts) - index
        _register(client, currency, validators, account, bond=bond)
    return accounts


def test_full_selection_pool_refuses_registration_without_taking_the_fee(client):
    currency, validators = _deploy(client)
    accounts = _fill_selection_pool(client, currency, validators)
    extra = "ff" * 32
    currency.transfer(amount=1000, to=extra, signer="founder")
    currency.approve(amount=1000, to="validators", signer=extra)

    with pytest.raises(AssertionError, match="Validator selection pool full"):
        validators.register(signer=extra)

    assert currency.balance_of(address=extra) == 1000
    assert len(validators.get_pending_candidates()) == 62
    validators.unregister(signer=accounts[-1])
    validators.register(signer=extra)
    assert currency.balance_of(address=extra) == 0
    assert len(validators.get_pending_candidates()) == 62


def test_genesis_refuses_a_validator_set_above_the_selection_pool_limit(client):
    _submit(client, "currency", {"vk": "founder"})
    with pytest.raises(AssertionError, match="Validator selection pool full"):
        _submit(client, "validators", {
            "genesis_nodes": [f"{index:064x}" for index in range(65)],
            "genesis_registration_fee": 1000,
        })


def test_governance_cannot_raise_max_validators_past_the_selection_pool_limit(client):
    _, validators = _deploy(client)
    with pytest.raises(AssertionError, match="max_validators is above its maximum"):
        validators.propose_vote(
            type_of_vote="update_policy", arg={"max_validators": 65}, signer=NODE1
        )


def test_unjailing_a_withdrawn_validator_does_not_restore_its_registration(client):
    currency, validators = _deploy(
        client, max_new_power_bps=10000, downtime_unjail_cooldown_hours=0,
        downtime_jail_blocks=1, genesis_nodes=[NODE1, NODE2, "c3" * 32, "d4" * 32],
    )
    _fill_selection_pool(client, currency, validators)
    validators.record_liveness(
        absent=[NODE1], signer="__liveness_driver__", environment={"block_num": 1},
    )
    validators.unregister(signer=NODE1)
    extra = "ff" * 32
    _register(client, currency, validators, extra)

    record = validators.unjail(signer=NODE1)

    assert record["jailed"] is False
    assert record["status"] == "withdrawn"
    assert NODE1 not in validators.get_members()
    assert len(validators.get_pending_candidates()) == 61
    with pytest.raises(AssertionError, match="Validator selection pool full"):
        validators.register(signer=NODE1)
    validators.unregister(signer=extra)
    currency.transfer(amount=1000, to=NODE1, signer="founder")
    currency.approve(amount=1000, to="validators", signer=NODE1)
    validators.register(signer=NODE1)
    assert validators.get_validator(account=NODE1)["status"] == "pending"


@pytest.mark.parametrize("power_mode", ["equal", "requested", "stake_weighted"])
@pytest.mark.parametrize("stake_order", ["increasing", "decreasing", "equal"])
def test_full_pool_deciding_vote_and_rebalance_fit_the_transaction_chi_cap(
    client, power_mode, stake_order
):
    currency, validators = _deploy(client)
    accounts = _fill_selection_pool(client, currency, validators, stake_order)
    # Reverse-ranked, already-ranked and tied stakes exercise both insertion
    # extremes. This vote admits all 62 eligible newcomers in one transaction.
    validators.propose_vote(
        type_of_vote="update_policy",
        arg={
            "selection_mode": "auto_top_n", "power_mode": power_mode,
            "max_validators": 64, "max_active_set_churn": 64,
            "max_new_power_bps": 10000,
        },
        signer=NODE1,
    )
    deciding_vote = validators.vote(
        proposal_id=1, vote="yes", signer=NODE2,
        environment={"block_num": 1}, metering=True, chi=200_000,
        return_full_output=True,
    )

    assert deciding_vote["status_code"] == 0, deciding_vote["result"]
    assert deciding_vote["result"]["status"] == "approved"
    assert deciding_vote["chi_used"] < 180_000
    ranked = list(reversed(accounts)) if stake_order == "increasing" else accounts
    assert validators.get_members() == ranked + [NODE1, NODE2]

    # Exercise all 64 active validators, then the largest possible set shrink.
    for block, limit in [(2, 64), (3, 1)]:
        client.raw_driver.set("validators.config:max_validators", limit)
        rebalance = validators.rebalance(
            signer=NODE1, environment={"block_num": block},
            metering=True, chi=200_000, return_full_output=True,
        )
        assert rebalance["status_code"] == 0, rebalance["result"]
        assert rebalance["chi_used"] < 180_000
        assert len(rebalance["result"]["selected"]) == limit


@pytest.mark.parametrize("power_mode", ["equal", "requested", "stake_weighted"])
def test_full_pool_can_replace_every_incumbent_within_the_chi_cap(client, power_mode):
    currency, validators = _deploy(
        client, selection_mode="auto_top_n", power_mode=power_mode,
        max_validators=32, max_active_set_churn=32, max_new_power_bps=10000,
    )
    accounts = _fill_selection_pool(client, currency, validators)
    validators.rebalance(signer=NODE1, environment={"block_num": 1})
    incumbents = validators.get_members()
    challengers = [account for account in accounts + [NODE1, NODE2] if account not in incumbents]
    assert len(incumbents) == len(challengers) == 32
    for account in challengers:
        currency.transfer(amount=1000, to=account, signer="founder")
        currency.approve(amount=1000, to="validators", signer=account)
        validators.bond_self(amount=1000, signer=account)

    result = validators.rebalance(
        signer=NODE1, environment={"block_num": 2}, metering=True,
        chi=200_000, return_full_output=True,
    )

    assert result["status_code"] == 0, result["result"]
    assert result["chi_used"] < 180_000
    assert set(result["result"]["activated"]) == set(challengers)
    assert set(result["result"]["deactivated"]) == set(incumbents)


@pytest.mark.parametrize("power_mode", ["equal", "requested", "stake_weighted"])
def test_full_validator_set_can_govern_its_largest_rebalance_within_the_chi_cap(client, power_mode):
    nodes = [f"{index:064x}" for index in range(64)]
    _, validators = _deploy(
        client, genesis_nodes=nodes, selection_mode="auto_top_n",
        max_validators=64, power_mode=power_mode,
    )
    validators.propose_vote(
        type_of_vote="update_policy", arg={"max_validators": 1}, signer=nodes[0],
    )

    for node in nodes[1:52]:
        deciding_vote = validators.vote(
            proposal_id=1, vote="yes", signer=node,
            metering=True, chi=200_000, return_full_output=True,
        )
        assert deciding_vote["status_code"] == 0, deciding_vote["result"]
        assert deciding_vote["chi_used"] < 180_000

    assert deciding_vote["result"]["status"] == "approved"
    assert validators.get_members() == nodes[:1]
