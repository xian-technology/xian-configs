"""Claimed unbonds must not accumulate work in future penalty processing."""

import os
from decimal import Decimal
from pathlib import Path

import pytest
from contracting.local import ContractingClient

CONTRACTS = (
    Path(
        os.environ.get("XIAN_CONFIGS_SOURCE_ROOT", Path(__file__).resolve().parents[1])
    )
    / "contracts"
)
NODE = "a1" * 32
OTHER = "b2" * 32
DELEGATOR = "d4" * 32


@pytest.fixture
def chain(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    client.flush()
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
                "unbonding_period_days": 0,
            },
        ),
    ]:
        client.submit(
            (CONTRACTS / f"{name}.s.py").read_text(), name=name, constructor_args=args
        )
    currency = client.get_contract_proxy("currency")
    currency.transfer(amount=10, to=DELEGATOR, signer="founder")
    currency.approve(amount=10, to="validators", signer=DELEGATOR)
    yield client, currency, client.get_contract_proxy("validators")


def test_claim_removes_only_the_claimed_unbond_from_live_indexes(chain):
    client, currency, validators = chain
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    first = validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    second = validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)

    claimed = validators.claim_unbond(unbond_id=first["id"], signer=DELEGATOR)

    assert claimed["claimed"] is True
    assert validators.get_pending_unbond_ids(owner=DELEGATOR) == [second["id"]]
    assert (
        client.raw_driver.get(f"validators.pending_unbond_heads:validator:{NODE}")
        == second["id"]
    )
    assert (
        client.raw_driver.get(f"validators.pending_unbond_tails:validator:{NODE}")
        == second["id"]
    )
    assert validators.get_pending_unbond(unbond_id=first["id"])["claimed"] is True
    with pytest.raises(AssertionError, match="already claimed"):
        validators.claim_unbond(unbond_id=first["id"], signer=DELEGATOR)
    assert currency.balance_of(address=DELEGATOR) == 7


def test_claim_cost_grows_only_with_heap_depth(chain):
    _, _, validators = chain
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    first = validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    second = validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    control = validators.claim_unbond(
        unbond_id=first["id"],
        signer=DELEGATOR,
        metering=True,
        chi=200_000,
        return_full_output=True,
    )
    for _ in range(200):
        validators.undelegate(validator=NODE, amount=Decimal("0.001"), signer=DELEGATOR)

    result = validators.claim_unbond(
        unbond_id=second["id"],
        signer=DELEGATOR,
        metering=True,
        chi=200_000,
        return_full_output=True,
    )

    assert control["status_code"] == result["status_code"] == 0
    assert result["chi_used"] <= control["chi_used"] + 1000
    assert len(validators.get_pending_unbond_ids(owner=DELEGATOR)) == 200


def test_pending_unbond_pages_preserve_order_and_reject_stale_cursors(chain):
    _, _, validators = chain
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(3):
        validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    first = validators.get_pending_unbond_page(owner=DELEGATOR, limit=2)
    assert [record["unbond_id"] for record in first["unbonds"]] == [1, 2]
    assert first["next_cursor"] == 3
    assert "unbond_id" not in validators.get_pending_unbond(unbond_id=1)
    last = validators.get_pending_unbond_page(owner=DELEGATOR, cursor=3, limit=2)
    assert [record["unbond_id"] for record in last["unbonds"]] == [3]
    assert last["next_cursor"] is None
    with pytest.raises(AssertionError, match="cursor"):
        validators.get_pending_unbond_page(owner=OTHER, cursor=3, limit=2)
    validators.claim_unbond(unbond_id=1, signer=DELEGATOR)
    with pytest.raises(AssertionError, match="cursor"):
        validators.get_pending_unbond_page(owner=DELEGATOR, cursor=1, limit=2)


@pytest.mark.parametrize("limit", [0, 101])
def test_pending_unbond_page_size_is_bounded(chain, limit):
    _, _, validators = chain
    with pytest.raises(AssertionError, match="page size"):
        validators.get_pending_unbond_page(owner=DELEGATOR, limit=limit)


def test_validator_summary_cost_is_independent_of_other_users_pending_unbonds(chain):
    _, _, validators = chain
    before = validators.get_validator(
        account=NODE, metering=True, chi=200_000, return_full_output=True
    )
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(200):
        validators.undelegate(validator=NODE, amount=Decimal("0.001"), signer=DELEGATOR)
    after = validators.get_validator(
        account=NODE, metering=True, chi=200_000, return_full_output=True
    )
    assert before["status_code"] == after["status_code"] == 0
    assert after["result"]["pending_unbond_count"] == 200
    assert after["result"]["pending_unbond_total"] == Decimal("0.2")
    assert after["chi_used"] <= before["chi_used"] + 1000


def test_summary_heap_handles_policy_changes_and_arbitrary_claim_order(chain):
    client, currency, validators = chain
    from xian_runtime_types.time import Datetime, Timedelta

    start = Datetime(2026, 12, 1)
    validators.delegate(validator=NODE, amount=10, signer=DELEGATOR)
    records = []
    for index, days in enumerate([7, 1, 5, 0, 3, 2, 9, 4, 6, 8]):
        validators.propose_vote(
            type_of_vote="update_policy",
            arg={"unbonding_period_days": days},
            signer=NODE,
            environment={"now": start},
        )
        validators.vote(
            proposal_id=index + 1, vote="yes", signer=OTHER, environment={"now": start}
        )
        records.append(
            validators.undelegate(
                validator=NODE, amount=1, signer=DELEGATOR, environment={"now": start}
            )
        )
    client.get_contract_proxy("validator_penalties").process_time_anchors(
        signer="__stake_time_driver__", environment={"block_num": 1, "now": start}
    )
    records = [
        validators.get_pending_unbond(unbond_id=record["id"]) for record in records
    ]
    remaining = {record["id"]: record for record in records}
    for index in [5, 0, 9, 2, 4, 1, 8, 6, 3, 7]:
        unbond_id = records[index]["id"]
        validators.claim_unbond(
            unbond_id=unbond_id,
            signer=DELEGATOR,
            environment={"now": start + Timedelta(days=20)},
        )
        del remaining[unbond_id]
        summary = validators.get_validator(account=NODE)
        assert summary["pending_unbond_count"] == len(remaining)
        assert summary["pending_unbond_total"] == len(remaining)
        assert summary["next_unbond_unlock_at"] == min(
            (record["unlock_at"] for record in remaining.values()), default=None
        )
    assert currency.balance_of(address=DELEGATOR) == 10
