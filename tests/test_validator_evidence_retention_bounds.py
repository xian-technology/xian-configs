"""Unbond policy must fit Comet's signed-int64 evidence duration plus a day."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from contracting.local import ContractingClient
from test_validator_unbond_indexes import CONTRACTS, DELEGATOR, NODE, OTHER
from xian_runtime_types.time import Datetime

DAY_NS = 86_400_000_000_000
MAX_UNBOND_DAYS = ((1 << 63) - 1) // DAY_NS - 1
INVALID_DAYS = [
    True,
    False,
    1.5,
    14.0,
    Decimal("1.5"),
    "14",
    -1,
    MAX_UNBOND_DAYS + 1,
    1 << 63,
]


@pytest.fixture
def client(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    for name, args in [
        ("currency", {"vk": "founder"}),
        ("dao", {}),
        ("rewards", {}),
        ("chi_cost", {"initial_rate": 20}),
        ("validator_penalties", {}),
    ]:
        client.submit(
            (CONTRACTS / f"{name}.s.py").read_text(), name=name, constructor_args=args
        )
    yield client
    client.close()


def _seed(client, days):
    client.submit(
        (CONTRACTS / "validators.s.py").read_text(),
        name="validators",
        constructor_args={
            "genesis_nodes": [NODE, OTHER],
            "genesis_registration_fee": 1000,
            "unbonding_period_days": days,
        },
    )
    return client.get_contract_proxy("validators")


@pytest.mark.parametrize("days", INVALID_DAYS)
def test_seed_rejects_an_unrepresentable_unbond_period_atomically(client, days):
    # ABI/wire types can reject before the policy's contract assertion runs.
    with pytest.raises((AssertionError, TypeError)):
        _seed(client, days)
    assert client.raw_driver.get("validators.__code__") is None
    assert client.raw_driver.get("validators.config:unbonding_period_days") is None
    assert client.raw_driver.get("validators.registry_count") is None


@pytest.mark.parametrize("days", INVALID_DAYS)
def test_invalid_governance_period_never_captures_a_proposal(client, days):
    validators = _seed(client, 7)
    with pytest.raises((AssertionError, TypeError)):
        validators.propose_vote(
            type_of_vote="update_policy",
            arg={"unbonding_period_days": days},
            signer=NODE,
        )
    assert validators.total_votes.get() == 0
    assert validators.get_policy_config()["unbonding_period_days"] == 7


@pytest.mark.parametrize("days", [0, 14, MAX_UNBOND_DAYS])
@pytest.mark.parametrize("via_governance", [False, True])
def test_supported_period_creates_and_releases_a_real_unbond(
    client, days, via_governance
):
    validators = _seed(client, 7 if via_governance else days)
    if via_governance:
        validators.propose_vote(
            type_of_vote="update_policy",
            arg={"unbonding_period_days": days},
            signer=NODE,
        )
        result = validators.vote(proposal_id=1, vote="yes", signer=OTHER)
        assert result["status"] == "approved"
    currency = client.get_contract_proxy("currency")
    currency.transfer(amount=1, to=DELEGATOR, signer="founder")
    currency.approve(amount=1, to="validators", signer=DELEGATOR)
    validators.delegate(validator=NODE, amount=1, signer=DELEGATOR)
    start = Datetime(2026, 11, 16)
    record = validators.undelegate(
        validator=NODE, amount=1, signer=DELEGATOR, environment={"now": start}
    )
    expected = datetime(2026, 11, 16) + timedelta(days=days)
    unlock = Datetime(expected.year, expected.month, expected.day)
    assert record["unlock_at"] == unlock
    if days > 0:
        with pytest.raises(AssertionError, match="locked"):
            validators.claim_unbond(
                unbond_id=record["id"], signer=DELEGATOR, environment={"now": start}
            )
    validators.claim_unbond(
        unbond_id=record["id"], signer=DELEGATOR, environment={"now": unlock}
    )
    assert currency.balance_of(address=DELEGATOR) == 1


def test_same_block_policy_reduction_keeps_the_longer_existing_unbond(client):
    validators = _seed(client, 7)
    currency = client.get_contract_proxy("currency")
    currency.transfer(amount=1, to=DELEGATOR, signer="founder")
    currency.approve(amount=1, to="validators", signer=DELEGATOR)
    validators.delegate(validator=NODE, amount=1, signer=DELEGATOR)
    environment = {"now": Datetime(2026, 11, 16), "block_num": 17}

    def change_policy(days, proposal_id):
        validators.propose_vote(
            type_of_vote="update_policy",
            arg={"unbonding_period_days": days},
            signer=NODE,
            environment=environment,
        )
        validators.vote(
            proposal_id=proposal_id,
            vote="yes",
            signer=OTHER,
            environment=environment,
        )

    change_policy(14, 1)
    record = validators.undelegate(
        validator=NODE, amount=1, signer=DELEGATOR, environment=environment
    )
    change_policy(7, 2)

    assert validators.get_policy_config()["unbonding_period_days"] == 7
    assert record["created_block"] == 17
    assert record["unlock_at"] == Datetime(2026, 11, 30)
    with pytest.raises(AssertionError, match="locked"):
        validators.claim_unbond(
            unbond_id=record["id"],
            signer=DELEGATOR,
            environment={"now": Datetime(2026, 11, 23)},
        )
