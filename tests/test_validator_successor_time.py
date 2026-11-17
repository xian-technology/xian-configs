"""Stake challenge windows start at a successor consensus checkpoint."""

from decimal import Decimal

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.time import Datetime

from test_validator_unbond_indexes import CONTRACTS, NODE, OTHER, DELEGATOR

SYSTEM = "__stake_time_driver__"
STALE = Datetime(2026, 1, 1)
FRESH = Datetime(2026, 4, 11)


@pytest.fixture
def chain(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    for name, args in [
        ("currency", {"vk": "founder"}),
        ("dao", {}),
        ("rewards", {}),
        ("chi_cost", {"initial_rate": 20}),
        ("validator_penalties", {}),
        (
            "validators",
            {
                "genesis_nodes": [NODE, OTHER],
                "genesis_registration_fee": 1000,
                "unbonding_period_days": 14,
            },
        ),
    ]:
        client.submit(
            (CONTRACTS / f"{name}.s.py").read_text(), name=name, constructor_args=args
        )
    currency = client.get_contract_proxy("currency")
    validators = client.get_contract_proxy("validators")
    currency.transfer(amount=10, to=NODE, signer="founder")
    currency.approve(amount=10, to="validators", signer=NODE)
    validators.bond_self(amount=10, signer=NODE)
    yield client, currency, validators
    client.close()


def request(validators, amount=1, height=100, now=STALE):
    return validators.unbond_self(
        amount=amount, signer=NODE, environment={"block_num": height, "now": now}
    )


def anchor(client, *, height=101, now=FRESH, **kwargs):
    return client.get_contract_proxy("validator_penalties").process_time_anchors(
        signer=SYSTEM, environment={"block_num": height, "now": now}, **kwargs
    )


def test_old_consensus_timestamp_cannot_collapse_a_new_unbond_window(chain):
    _, currency, validators = chain
    record = request(validators)
    with pytest.raises(AssertionError, match="anchor"):
        validators.claim_unbond(
            unbond_id=record["id"],
            signer=NODE,
            environment={"block_num": 102, "now": FRESH},
        )
    assert currency.balance_of(address=NODE) == 0


def test_unbond_exposes_no_unlock_date_until_successor_time_is_anchored(chain):
    _, _, validators = chain
    record = request(validators)
    assert record["unlock_at"] is None
    assert record["unbonding_period_days"] == 14


def test_same_height_cannot_anchor_even_when_its_timestamp_jumps(chain):
    client, _, validators = chain
    record = request(validators)
    assert anchor(client, height=100)["processed"] == 0
    assert validators.get_pending_unbond(unbond_id=record["id"])["unlock_at"] is None


def test_successor_anchor_starts_the_captured_period_and_rekeys_heap(chain):
    client, currency, validators = chain
    record = request(validators)
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] is None
    result = anchor(client)
    assert result["processed"] == 1 and result["head"] is None
    current = validators.get_pending_unbond(unbond_id=record["id"])
    expected = Datetime(2026, 4, 25)
    assert current["unlock_at"] == expected
    assert current["created_at"] == STALE and current["created_block"] == 100
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] == expected
    with pytest.raises(AssertionError, match="locked"):
        validators.claim_unbond(
            unbond_id=record["id"],
            signer=NODE,
            environment={"block_num": 102, "now": FRESH},
        )
    validators.claim_unbond(
        unbond_id=record["id"],
        signer=NODE,
        environment={"block_num": 103, "now": expected},
    )
    assert currency.balance_of(address=NODE) == 1


def change_policy(validators, days, *, height=100, now=STALE):
    env = {"block_num": height, "now": now}
    validators.propose_vote(
        type_of_vote="update_policy",
        arg={"unbonding_period_days": days},
        signer=NODE,
        environment=env,
    )
    validators.vote(
        proposal_id=validators.total_votes.get(),
        vote="yes",
        signer=OTHER,
        environment=env,
    )


def test_queued_period_cannot_be_shortened_by_later_governance(chain):
    client, _, validators = chain
    record = request(validators)
    change_policy(validators, 0)
    assert validators.get_policy_config()["unbonding_period_days"] == 0
    anchor(client)
    stored = validators.get_pending_unbond(unbond_id=record["id"])
    assert stored["unbonding_period_days"] == 14
    assert stored["unlock_at"] == Datetime(2026, 4, 25)
    instant = request(validators, height=102, now=FRESH)
    assert instant["unlock_at"] == FRESH
    validators.claim_unbond(
        unbond_id=instant["id"],
        signer=NODE,
        environment={"block_num": 102, "now": FRESH},
    )


@pytest.mark.parametrize("limit", [0, 33, -1, True])
def test_time_work_limit_is_enforced_inside_the_contract(chain, limit):
    client, _, _ = chain
    with pytest.raises((AssertionError, TypeError), match="batch work|ABI value"):
        anchor(client, max_work=limit)


def test_only_reserved_driver_and_coordinator_can_change_timing(chain):
    client, _, validators = chain
    record = request(validators)
    penalties = client.get_contract_proxy("validator_penalties")
    for name, kwargs in [
        ("process_time_anchors", {}),
        ("track_exit_time", {"account": NODE}),
        ("track_unbond_time", {"unbond_id": record["id"]}),
    ]:
        with pytest.raises(AssertionError, match="only"):
            getattr(penalties, name)(signer=DELEGATOR, **kwargs)
    with pytest.raises(AssertionError, match="coordinator only"):
        validators.set_unbond_unlock(
            unbond_id=record["id"], unlock_at=STALE, signer=DELEGATOR
        )


def test_bounded_fifo_resumes_after_real_storage_reopen_and_does_not_touch_same_height(
    chain,
):
    client, _, validators = chain
    for _ in range(40):
        request(validators, amount=Decimal("0.01"))
    assert anchor(client, max_work=7) == {"processed": 7, "head": 8}
    storage_home = client.raw_driver.storage_home
    client.raw_driver.commit()
    client.close()
    resumed = ContractingClient(storage_home=storage_home)
    try:
        penalties = resumed.get_contract_proxy("validator_penalties")
        assert penalties.process_time_anchors(
            max_work=32, signer=SYSTEM, environment={"block_num": 102, "now": FRESH}
        ) == {"processed": 32, "head": 40}
        assert penalties.process_time_anchors(
            signer=SYSTEM, environment={"block_num": 102, "now": FRESH}
        ) == {"processed": 1, "head": None}
        before = dict(resumed.raw_driver.items())
        assert (
            penalties.process_time_anchors(
                signer=SYSTEM, environment={"block_num": 102, "now": FRESH}
            )["processed"]
            == 0
        )
        assert dict(resumed.raw_driver.items()) == before
        records = resumed.get_contract_proxy("validators")
        assert all(
            records.get_pending_unbond(unbond_id=i)["unlock_at"]
            == Datetime(2026, 4, 25)
            for i in range(1, 41)
        )
    finally:
        resumed.close()


def test_new_jobs_behind_old_jobs_wait_for_their_own_successor(chain):
    client, _, validators = chain
    first = request(validators)
    second = request(validators, height=101, now=FRESH)
    assert anchor(client, height=101) == {"processed": 1, "head": 2}
    assert validators.get_pending_unbond(unbond_id=first["id"])[
        "unlock_at"
    ] == Datetime(2026, 4, 25)
    assert validators.get_pending_unbond(unbond_id=second["id"])["unlock_at"] is None
    before = dict(client.raw_driver.items())
    assert anchor(client, height=101)["processed"] == 0
    assert dict(client.raw_driver.items()) == before
    assert anchor(client, height=102)["processed"] == 1


def test_heap_keeps_dated_items_before_unanchored_and_rekeys_ties(chain):
    client, _, validators = chain
    older = request(validators)
    change_policy(validators, 0)
    dated = request(validators, height=101, now=FRESH)
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] == FRESH
    validators.claim_unbond(
        unbond_id=dated["id"], signer=NODE, environment={"block_num": 101, "now": FRESH}
    )
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] is None
    anchor(client)
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] == Datetime(
        2026, 4, 25
    )
    assert validators.get_pending_unbond(unbond_id=older["id"])["claimed"] is False


def remove_member(validators, *, height, now):
    env = {"block_num": height, "now": now}
    validators.propose_vote(
        type_of_vote="remove_member", arg=NODE, signer=OTHER, environment=env
    )
    validators.vote(
        proposal_id=validators.total_votes.get(),
        vote="yes",
        signer=NODE,
        environment=env,
    )


def test_exited_delegation_reuses_successor_exit_window_after_it_has_been_served(chain):
    client, currency, validators = chain
    currency.transfer(amount=2, to=DELEGATOR, signer="founder")
    currency.approve(amount=2, to="validators", signer=DELEGATOR)
    validators.delegate(validator=NODE, amount=2, signer=DELEGATOR)
    remove_member(validators, height=100, now=STALE)
    assert anchor(client)["processed"] == 2  # Exit generation, swept self bond.
    unbond = validators.undelegate(
        validator=NODE,
        amount=1,
        signer=DELEGATOR,
        environment={"block_num": 150, "now": Datetime(2026, 5, 1)},
    )
    assert unbond["unlock_at"] == Datetime(2026, 4, 25)
    validators.claim_unbond(
        unbond_id=unbond["id"],
        signer=DELEGATOR,
        environment={"block_num": 150, "now": Datetime(2026, 5, 1)},
    )
    assert currency.balance_of(address=DELEGATOR) == 1


def test_exit_generations_survive_reregistration_and_later_exit_backlog(chain):
    client, currency, validators = chain
    remove_member(validators, height=100, now=STALE)
    first_id = validators.get_pending_unbond_ids(owner=NODE)[0]
    currency.transfer(amount=1000, to=NODE, signer="founder")
    currency.approve(amount=1000, to="validators", signer=NODE)
    validators.register(signer=NODE, environment={"block_num": 101, "now": FRESH})
    validators.propose_vote(
        type_of_vote="add_member",
        arg=NODE,
        signer=OTHER,
        environment={"block_num": 101, "now": FRESH},
    )
    currency.transfer(amount=2, to=NODE, signer="founder")
    currency.approve(amount=2, to="validators", signer=NODE)
    validators.bond_self(amount=2, signer=NODE)
    remove_member(validators, height=102, now=FRESH)
    second_id = validators.get_pending_unbond_ids(owner=NODE)[-1]
    assert anchor(client, height=103, max_work=2)["processed"] == 2
    next_day = Datetime(2026, 4, 12)
    assert anchor(client, height=104, now=next_day)["processed"] == 2
    assert validators.get_pending_unbond(unbond_id=first_id)["unlock_at"] == Datetime(
        2026, 4, 25
    )
    assert validators.get_pending_unbond(unbond_id=second_id)["unlock_at"] == Datetime(
        2026, 4, 26
    )


def test_pending_slash_does_not_block_the_global_time_queue_or_lose_the_freeze(chain):
    client, _, validators = chain
    record = request(validators)
    validators.apply_evidence_penalty(
        member=NODE,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="fresh-proof",
        evidence_height=100,
        signer="__evidence_penalty_driver__",
        environment={"block_num": 101, "now": FRESH},
    )
    assert anchor(client)["processed"] == 1
    anchored = validators.get_pending_unbond(unbond_id=record["id"])
    assert anchored["unlock_at"] == Datetime(2026, 4, 25)
    assert anchored["amount"] == 1
    with pytest.raises(AssertionError, match="penalty pending"):
        validators.claim_unbond(
            unbond_id=record["id"],
            signer=NODE,
            environment={"block_num": 102, "now": Datetime(2026, 5, 1)},
        )
    result = client.get_contract_proxy("validator_penalties").process_pending_slashes(
        signer="__penalty_driver__", environment={"block_num": 102, "now": FRESH}
    )
    assert result["pending_jobs"] == 0
    assert validators.get_pending_unbond(unbond_id=record["id"])["amount"] == Decimal(
        "0.95"
    )


def test_dependent_unbond_after_a_backlogged_exit_uses_exit_time_not_drain_time(chain):
    client, _, validators = chain
    remove_member(validators, height=100, now=STALE)
    record_id = validators.get_pending_unbond_ids(owner=NODE)[0]
    assert anchor(client, max_work=1) == {"processed": 1, "head": 2}
    assert validators.get_pending_unbond(unbond_id=record_id)["unlock_at"] is None
    assert anchor(client, height=150, now=Datetime(2026, 6, 1))["processed"] == 1
    assert validators.get_pending_unbond(unbond_id=record_id)["unlock_at"] == Datetime(
        2026, 4, 25
    )


def test_timing_callback_cannot_clear_or_rewrite_a_committed_anchor(chain):
    client, _, validators = chain
    record = request(validators)
    with pytest.raises(AssertionError, match="already anchored"):
        validators.set_unbond_unlock(
            unbond_id=record["id"], unlock_at=None, signer="validator_penalties"
        )
    anchor(client)
    with pytest.raises(AssertionError, match="already anchored"):
        validators.set_unbond_unlock(
            unbond_id=record["id"], unlock_at=STALE, signer="validator_penalties"
        )
    assert validators.get_pending_unbond(unbond_id=record["id"])[
        "unlock_at"
    ] == Datetime(2026, 4, 25)


def test_untrusted_old_exit_metadata_uses_a_new_request_successor(chain):
    client, currency, validators = chain
    currency.transfer(amount=1, to=DELEGATOR, signer="founder")
    currency.approve(amount=1, to="validators", signer=DELEGATOR)
    validators.delegate(validator=NODE, amount=1, signer=DELEGATOR)
    # A manually constructed export has an old left_at but no authentic
    # successor generation. It must not grant an already served exit window.
    client.raw_driver.set(f"validators.statuses:{NODE}", "removed")
    client.raw_driver.set(f"validators.left_at:{NODE}", STALE)
    client.raw_driver.commit()
    record = validators.undelegate(
        validator=NODE,
        amount=1,
        signer=DELEGATOR,
        environment={"block_num": 100, "now": FRESH},
    )
    assert record["unlock_at"] is None
    anchor(client, now=Datetime(2026, 4, 12))
    assert validators.get_pending_unbond(unbond_id=record["id"])[
        "unlock_at"
    ] == Datetime(2026, 4, 26)


def test_anchoring_different_captured_periods_reorders_the_earliest_date(chain):
    client, _, validators = chain
    later = request(validators)
    change_policy(validators, 7)
    earlier = request(validators)
    anchor(client)
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] == Datetime(
        2026, 4, 18
    )
    validators.claim_unbond(
        unbond_id=earlier["id"],
        signer=NODE,
        environment={"block_num": 102, "now": Datetime(2026, 4, 18)},
    )
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] == Datetime(
        2026, 4, 25
    )
    with pytest.raises(AssertionError, match="locked"):
        validators.claim_unbond(
            unbond_id=later["id"],
            signer=NODE,
            environment={"block_num": 102, "now": Datetime(2026, 4, 18)},
        )


def test_claim_heap_never_promotes_an_older_unanchored_item_over_a_dated_one(chain):
    client, _, validators = chain
    pending = request(validators)
    change_policy(validators, 0)
    first = request(validators, height=101, now=FRESH)
    last = request(validators, height=101, now=FRESH)
    validators.claim_unbond(
        unbond_id=first["id"], signer=NODE, environment={"block_num": 101, "now": FRESH}
    )
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] == FRESH
    assert validators.get_pending_unbond(unbond_id=last["id"])["claimed"] is False
    validators.claim_unbond(
        unbond_id=last["id"], signer=NODE, environment={"block_num": 101, "now": FRESH}
    )
    assert validators.get_validator(account=NODE)["next_unbond_unlock_at"] is None
    assert validators.get_pending_unbond(unbond_id=pending["id"])["unlock_at"] is None
