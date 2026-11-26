"""Canonical native-token accounts must remain spendable by their signing key."""

import os
from decimal import Decimal
from pathlib import Path

import pytest
from contracting.local import ContractingClient

ROOT = Path(
    os.environ.get("XIAN_CONFIGS_SOURCE_ROOT", Path(__file__).resolve().parents[1])
)
SOURCE = (ROOT / "contracts" / "currency.s.py").read_text()
KEY = "ab" * 32
BAD_KEYS = [KEY.upper(), KEY[:32] + KEY[32:].upper()]


@pytest.fixture
def client(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    client.flush()
    return client


@pytest.mark.parametrize("recipient", BAD_KEYS)
def test_transfer_rejects_a_hex_spelling_that_the_signer_cannot_spend(
    client, recipient
):
    client.submit(SOURCE, name="currency", constructor_args={"vk": "founder"})
    token = client.get_contract_proxy("currency")

    with pytest.raises(AssertionError, match="canonical lowercase"):
        token.transfer(amount=1, to=recipient, signer="founder")

    assert token.balance_of(address=recipient) == 0
    assert token.balance_of(address="founder") == Decimal("11111111.1")


@pytest.mark.parametrize("recipient", BAD_KEYS)
def test_transfer_from_rejects_noncanonical_hex_without_spending_approval(
    client, recipient
):
    client.submit(SOURCE, name="currency", constructor_args={"vk": "founder"})
    token = client.get_contract_proxy("currency")
    token.approve(amount=2, to="spender", signer="founder")

    with pytest.raises(AssertionError, match="canonical lowercase"):
        token.transfer_from(
            amount=1, to=recipient, main_account="founder", signer="spender"
        )

    assert token.approvals["founder", "spender"] == 2
    assert token.balance_of(address=recipient) == 0
    assert token.balance_of(address="founder") == Decimal("11111111.1")


@pytest.mark.parametrize("recipient", BAD_KEYS)
def test_configured_genesis_rejects_noncanonical_hex_accounts(client, recipient):
    with pytest.raises(AssertionError, match="canonical lowercase"):
        client.submit(
            SOURCE,
            name="currency",
            constructor_args={
                "vk": "founder",
                "initial_balances": {recipient: "1"},
            },
        )


@pytest.mark.parametrize("recipient", ["", *BAD_KEYS])
def test_default_genesis_rejects_invalid_founder_accounts(client, recipient):
    with pytest.raises(AssertionError, match="non-empty|canonical lowercase"):
        client.submit(SOURCE, name="currency", constructor_args={"vk": recipient})


@pytest.mark.parametrize(
    ("founder", "dao_balance", "team_balance"),
    [("dao", "44444444.4", "66666666.6"), ("team_lock", "33333333.3", "77777777.7")],
)
def test_default_genesis_combines_allocations_to_the_same_account(
    client, founder, dao_balance, team_balance
):
    client.submit(SOURCE, name="currency", constructor_args={"vk": founder})
    token = client.get_contract_proxy("currency")
    assert token.balance_of(address="dao") == Decimal(dao_balance)
    assert token.balance_of(address="team_lock") == Decimal(team_balance)
    assert token.metadata["total_supply"] == 111111111


@pytest.mark.parametrize("recipient", ["invalid:key", "invalid.key"])
def test_account_validator_rejects_reserved_storage_separators(client, recipient):
    client.submit(SOURCE, name="currency", constructor_args={"vk": "founder"})
    token = client.get_contract_proxy("currency")
    with pytest.raises(AssertionError, match="storage separator"):
        token.validate_account(account=recipient)


@pytest.mark.parametrize("recipient", [KEY, "dao", "con_" + "g" * 60])
def test_transfers_preserve_valid_keys_and_named_destinations(client, recipient):
    client.submit(SOURCE, name="currency", constructor_args={"vk": "founder"})
    token = client.get_contract_proxy("currency")
    before = token.balance_of(address=recipient)
    token.transfer(amount=1, to=recipient, signer="founder")
    assert token.balance_of(address=recipient) == before + 1


@pytest.mark.parametrize("reward_key", ["r" * 494, "é" * 247])
def test_active_validator_cannot_poison_all_fee_rewards_with_an_oversized_key(
    client, reward_key
):
    contracts = ROOT / "contracts"
    for name, args in [
        ("currency", {"vk": "founder"}),
        ("dao", {}),
        ("rewards", {}),
        ("chi_cost", {"initial_rate": 20}),
        ("validator_penalties", {}),
        (
            "validators",
            {
                "genesis_nodes": [KEY],
                "genesis_registration_fee": 1000,
            },
        ),
    ]:
        client.submit(
            (contracts / f"{name}.s.py").read_text(), name=name, constructor_args=args
        )
    validators = client.get_contract_proxy("validators")

    with pytest.raises(AssertionError, match="storage key limit"):
        validators.update_profile(reward_key=reward_key, signer=KEY)

    assert validators.get_validator(account=KEY)["reward_key"] == KEY
