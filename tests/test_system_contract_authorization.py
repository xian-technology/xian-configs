from pathlib import Path

import pytest
from contracting.local import ContractingClient


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
    new_split = [0.25, 0.05, 0.05, 0.65]

    with pytest.raises(AssertionError, match="Only validators"):
        rewards.set_value(new_value=new_split, signer="alice")

    assert rewards.current_value() == [0.30, 0.01, 0.01, 0.68]

    rewards.set_value(new_value=new_split, signer="validators")

    assert rewards.current_value() == new_split
