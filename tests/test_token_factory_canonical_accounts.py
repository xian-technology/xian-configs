"""Account validation and accounting invariants for factory-created tokens."""

import os
from pathlib import Path

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.decimal import ContractingDecimal, MAX_DECIMAL

SOURCE_ROOT = (
    Path(os.environ["XIAN_RECIPIENT_SOURCE_ROOT"])
    if "XIAN_RECIPIENT_SOURCE_ROOT" in os.environ
    else Path(__file__).absolute().parents[1]
)
CONTRACTS = SOURCE_ROOT / "contracts"


@pytest.fixture
def factory(tmp_path):
    client = ContractingClient(vm_profile="xian_vm_v2", storage_home=tmp_path)
    client.flush()
    for name in ("currency", "token_factory"):
        client.submit(
            (CONTRACTS / f"{name}.s.py").read_text(),
            name=name,
            constructor_args={"vk": "alice"} if name == "currency" else {},
        )
    yield client, client.get_contract_proxy("token_factory")
    client.flush()


def create_token(factory, initial_supply=10, **kwargs):
    client, proxy = factory
    proxy.create_token(
        token_contract="con_token",
        token_name="Token",
        token_symbol="T",
        initial_supply=initial_supply,
        signer="alice",
        **kwargs,
    )
    return client.get_contract_proxy("con_token")


def test_factory_rejects_supply_above_the_transfer_range(factory):
    with pytest.raises(AssertionError, match="decimal range"):
        create_token(factory, initial_supply=10**61)
    assert factory[0].raw_driver.get("con_token.__source__") is None

    token = create_token(factory, initial_supply=10**61 - 1)
    assert token.balance_of(address="alice") == 10**61 - 1


@pytest.mark.parametrize("supply", [0, ContractingDecimal(MAX_DECIMAL)])
def test_factory_preserves_supply_at_the_decimal_boundaries(factory, supply):
    token = create_token(factory, initial_supply=supply)
    if supply:
        token.transfer(amount=supply, to="bob", signer="alice")
        assert token.balance_of(address="alice") == 0
        assert token.balance_of(address="bob") == supply
    else:
        assert token.balance_of(address="alice") == 0
    assert factory[0].get_var("con_token", "metadata", ["total_supply"]) == supply


def test_operator_cannot_change_the_recorded_total_supply(factory):
    client, _ = factory
    token = create_token(factory)

    with pytest.raises(AssertionError, match="total_supply is managed"):
        token.change_metadata(key="total_supply", value=100, signer="alice")

    assert client.get_var("con_token", "metadata", ["total_supply"]) == 10
    assert token.balance_of(address="alice") == 10


def test_token_rejects_empty_transfer_recipients_without_spending(factory):
    token = create_token(factory)
    token.approve(amount=2, to="spender", signer="alice")

    with pytest.raises(AssertionError, match="non-empty"):
        token.transfer(amount=1, to="", signer="alice")
    with pytest.raises(AssertionError, match="non-empty"):
        token.transfer_from(amount=1, to="", main_account="alice", signer="spender")

    assert token.balance_of(address="alice") == 10
    token.transfer_from(amount=2, to="bob", main_account="alice", signer="spender")
    assert token.balance_of(address="alice") == 8
    assert token.balance_of(address="bob") == 2


def test_token_rejects_an_empty_approval_target(factory):
    token = create_token(factory)
    with pytest.raises(AssertionError, match="non-empty"):
        token.approve(amount=1, to="", signer="alice")


@pytest.mark.parametrize("amount", [0, -1])
def test_transfers_require_a_positive_amount(factory, amount):
    token = create_token(factory)
    token.approve(amount=10, to="spender", signer="alice")

    with pytest.raises(AssertionError, match="Cannot send"):
        token.transfer(amount=amount, to="bob", signer="alice")
    with pytest.raises(AssertionError, match="Cannot send"):
        token.transfer_from(
            amount=amount, to="bob", main_account="alice", signer="spender"
        )

    assert token.balance_of(address="alice") == 10
    assert token.balance_of(address="bob") == 0


def test_approval_can_be_cleared_and_delegated_transfer_can_spend_full_balance(factory):
    token = create_token(factory)
    token.approve(amount=10, to="spender", signer="alice")
    token.approve(amount=0, to="spender", signer="alice")
    with pytest.raises(AssertionError, match="Not enough coins approved"):
        token.transfer_from(amount=1, to="bob", main_account="alice", signer="spender")

    token.approve(amount=10, to="spender", signer="alice")
    token.transfer_from(amount=10, to="bob", main_account="alice", signer="spender")
    assert token.balance_of(address="alice") == 0
    assert token.balance_of(address="bob") == 10


@pytest.mark.parametrize("field", ["initial_holder", "operator_address"])
def test_factory_refuses_unspendable_hex_constructor_accounts(factory, field):
    with pytest.raises(AssertionError, match="canonical lowercase"):
        create_token(factory, **{field: "B" * 64})
    assert factory[0].raw_driver.get("con_token.__source__") is None


@pytest.mark.parametrize(
    "operation", ["transfer", "transfer_from", "approve", "change_operator"]
)
def test_factory_token_refuses_unspendable_hex_recipients_and_authority(
    factory, operation
):
    token = create_token(factory)
    if operation == "transfer_from":
        token.approve(amount=2, to="spender", signer="alice")
    with pytest.raises(AssertionError, match="canonical lowercase"):
        if operation == "change_operator":
            token.change_operator(new_operator="B" * 64, signer="alice")
        elif operation == "transfer_from":
            token.transfer_from(
                amount=1, to="B" * 64, main_account="alice", signer="spender"
            )
        else:
            getattr(token, operation)(amount=1, to="B" * 64, signer="alice")
    assert token.balance_of(address="alice") == 10
    assert token.balance_of(address="B" * 64) == 0
    assert token.operator_of() == "alice"


def test_factory_token_preserves_lowercase_keys_and_named_contract_targets(factory):
    token = create_token(factory)
    token.transfer(amount=1, to="b" * 64, signer="alice")
    token.transfer(amount=2, to="con_receiver", signer="alice")
    token.change_operator(new_operator="con_governor", signer="alice")
    token.change_metadata(key="token_name", value="Updated", signer="con_governor")
    assert token.balance_of(address="b" * 64) == 1
    assert token.balance_of(address="con_receiver") == 2
    long_contract = "con_" + "B" * 60
    token.transfer(amount=1, to=long_contract, signer="alice")
    assert token.balance_of(address=long_contract) == 1


def submit_authored_token(client, **overrides):
    client.submit(
        (
            CONTRACTS / "templates" / "token_factory_xsc001_token_template.s.py"
        ).read_text(),
        name="con_authored_token",
        constructor_args={
            "token_name": "Authored",
            "token_symbol": "A",
            "token_logo_url": "",
            "token_logo_svg": "",
            "token_website": "",
            "initial_supply": 10,
            "initial_holder": "alice",
            "operator_address": "alice",
            **overrides,
        },
    )
    return client.get_contract_proxy("con_authored_token")


@pytest.mark.parametrize(
    "field", ["token_name", "token_symbol", "initial_holder", "operator_address"]
)
@pytest.mark.parametrize("value", ["", None])
def test_authored_child_rejects_invalid_names_and_accounts(factory, field, value):
    client, _ = factory
    with pytest.raises(AssertionError, match=field):
        submit_authored_token(client, **{field: value})
    assert client.raw_driver.get("con_authored_token.__source__") is None


@pytest.mark.parametrize("new_operator", ["", None])
def test_token_keeps_operator_when_replacement_is_invalid(factory, new_operator):
    token = create_token(factory)
    with pytest.raises(AssertionError, match="new_operator must be non-empty"):
        token.change_operator(new_operator=new_operator, signer="alice")
    assert token.operator_of() == "alice"


def test_authored_child_template_enforces_the_same_recipient_policy(factory):
    client, _ = factory
    token = submit_authored_token(client)
    with pytest.raises(AssertionError, match="canonical lowercase"):
        token.transfer(amount=1, to="B" * 64, signer="alice")
    token.transfer(amount=1, to="b" * 64, signer="alice")
    token.transfer(amount=1, to="con_" + "B" * 60, signer="alice")
    assert token.balance_of(address="alice") == 8
