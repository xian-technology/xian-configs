from pathlib import Path

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.decimal import ContractingDecimal


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"


@pytest.fixture
def client(tmp_path):
    storage_home = tmp_path / "xian"
    storage_home.mkdir(parents=True, exist_ok=True)

    client = ContractingClient(storage_home=storage_home)
    client.flush()
    return client


def submit_contract(
    client: ContractingClient,
    name: str,
    file_name: str,
    constructor_args=None,
):
    source = (CONTRACTS_DIR / file_name).read_text(encoding="utf-8")
    client.submit(
        source,
        name=name,
        constructor_args=constructor_args or {},
    )
    return client.get_contract_proxy(name)


def test_dao_payout_requires_validators(client):
    currency = submit_contract(
        client,
        "currency",
        "currency.s.py",
        {"vk": "founder"},
    )
    dao = submit_contract(client, "dao", "dao.s.py")

    with pytest.raises(AssertionError, match="Only validators"):
        dao.transfer_from_dao(
            args={"contract_name": "currency", "amount": 10, "to": "alice"},
            signer="alice",
        )

    assert currency.balance_of(address="alice") == 0
    assert currency.balance_of(address="dao") == 33333333.3

    dao.transfer_from_dao(
        args={"contract_name": "currency", "amount": 10, "to": "alice"},
        signer="validators",
    )

    assert currency.balance_of(address="alice") == 10
    assert currency.balance_of(address="dao") == 33333323.3


def test_currency_default_seed_preserves_distribution(client):
    currency = submit_contract(
        client,
        "currency",
        "currency.s.py",
        {"vk": "founder"},
    )

    assert currency.balance_of(address="founder") == 11111111.1
    assert currency.balance_of(address="team_lock") == 66666666.6
    assert currency.balance_of(address="dao") == 33333333.3
    assert currency.metadata["total_supply"] == 111111111.0


def test_currency_seed_accepts_configured_genesis_balances(client):
    currency = submit_contract(
        client,
        "currency",
        "currency.s.py",
        {
            "vk": "founder",
            "initial_balances": {
                "alice": "1.25",
                "bob": "2.50",
                "dao": "3.75",
            },
            "token_metadata": {
                "token_website": "https://xian.org/mainnet",
            },
        },
    )

    assert currency.balance_of(address="founder") == 0
    assert currency.balance_of(address="alice") == ContractingDecimal("1.25")
    assert currency.balance_of(address="bob") == ContractingDecimal("2.50")
    assert currency.balance_of(address="dao") == ContractingDecimal("3.75")
    assert currency.metadata["total_supply"] == ContractingDecimal("7.50")
    assert currency.metadata["token_website"] == "https://xian.org/mainnet"


def test_chi_cost_update_requires_validators(client):
    chi_cost = submit_contract(
        client,
        "chi_cost",
        "chi_cost.s.py",
        {"initial_rate": 20},
    )

    with pytest.raises(AssertionError, match="Only validators"):
        chi_cost.set_value(new_value=7, signer="alice")

    assert chi_cost.current_value() == 20

    chi_cost.set_value(new_value=7, signer="validators")

    assert chi_cost.current_value() == 7


def test_rewards_update_requires_validators(client):
    rewards = submit_contract(client, "rewards", "rewards.s.py")
    new_split = [0.65, 0, 0, 0.35]

    with pytest.raises(AssertionError, match="Only validators"):
        rewards.set_value(new_value=new_split, signer="alice")

    assert rewards.current_value() == [0.70, 0, 0, 0.30]

    rewards.set_value(new_value=new_split, signer="validators")

    assert rewards.current_value() == new_split

    with pytest.raises(AssertionError, match="non-negative"):
        rewards.set_value(
            new_value=[0.70, -0.10, 0, 0.40],
            signer="validators",
        )


def test_rewards_seed_validates_the_initial_split(client):
    with pytest.raises(AssertionError, match="non-negative"):
        submit_contract(
            client,
            "rewards",
            "rewards.s.py",
            {"initial_split": [0.70, -0.10, 0, 0.40]},
        )


def _deploy_validators(client):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    submit_contract(client, "dao", "dao.s.py")
    submit_contract(client, "rewards", "rewards.s.py")
    submit_contract(client, "chi_cost", "chi_cost.s.py", {"initial_rate": 20})
    validators = submit_contract(
        client,
        "validators",
        "validators.s.py",
        {"genesis_nodes": ["node1"], "genesis_registration_fee": 1000},
    )
    return client.get_contract_proxy("currency"), validators


def test_validator_registration_requires_the_signing_account(client):
    currency, validators = _deploy_validators(client)
    client.submit(
        "@export\n"
        "def register():\n"
        "    importlib.import_module('currency').approve(amount=1000, to='validators')\n"
        "    importlib.import_module('validators').register()\n",
        name="con_registrar",
    )
    currency.transfer(amount=1000, to="con_registrar", signer="founder")

    with pytest.raises(AssertionError, match="own account"):
        client.get_contract_proxy("con_registrar").register(signer="alice")
    assert not client.raw_driver.get("validators.pending_registrations:con_registrar")
    assert currency.balance_of(address="con_registrar") == 1000

    currency.transfer(amount=1000, to="alice", signer="founder")
    currency.approve(amount=1000, to="validators", signer="alice")
    validators.register(signer="alice")
    assert client.raw_driver.get("validators.pending_registrations:alice") is True
