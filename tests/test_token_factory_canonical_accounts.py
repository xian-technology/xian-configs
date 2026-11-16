"""Factory-created token balances and authority must retain a spendable owner."""

import os
from pathlib import Path

import pytest
from contracting.local import ContractingClient

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


def create_token(factory, **kwargs):
    client, proxy = factory
    proxy.create_token(
        token_contract="con_token",
        token_name="Token",
        token_symbol="T",
        initial_supply=10,
        signer="alice",
        **kwargs,
    )
    return client.get_contract_proxy("con_token")


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


def test_authored_child_template_enforces_the_same_recipient_policy(factory):
    client, _ = factory
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
        },
    )
    token = client.get_contract_proxy("con_authored_token")
    with pytest.raises(AssertionError, match="canonical lowercase"):
        token.transfer(amount=1, to="B" * 64, signer="alice")
    token.transfer(amount=1, to="b" * 64, signer="alice")
    token.transfer(amount=1, to="con_" + "B" * 60, signer="alice")
    assert token.balance_of(address="alice") == 8
