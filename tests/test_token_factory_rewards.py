"""Developer rewards of factory tokens reach someone who can spend them."""

from pathlib import Path

from contracting.local import ContractingClient
from xian.fee_policy import TxFeePolicy
from xian.processor import TxProcessor
from xian.utils.tx import transaction_bytes

CONTRACTS_DIR = Path(__file__).absolute().parents[1] / "contracts"


def _paid_transfer(client: ContractingClient, contract: str, sender: str) -> dict:
    tx = {
        "payload": {
            "sender": sender,
            "contract": contract,
            "function": "transfer",
            "kwargs": {"amount": 1, "to": "bob"},
            "nonce": 0,
            "chi_supplied": 1000,
        },
        "metadata": {"signature": "sig"},
        "b_meta": {
            "nanos": 1_000_000_000,
            "height": 1,
            "hash": "ab",
            "chain_id": "local",
        },
    }
    [response] = TxProcessor(client=client).process_block(
        [tx], [transaction_bytes(tx)], fee_policy=TxFeePolicy.paid_metered()
    )
    return response["tx_result"]


def test_a_factory_token_pays_its_developer_share_to_the_creator(tmp_path):
    client = ContractingClient(vm_profile="xian_vm_v2", storage_home=tmp_path)
    client.flush()
    for name in ("currency", "token_factory"):
        source = (CONTRACTS_DIR / f"{name}.s.py").read_text(encoding="utf-8")
        client.submit(
            source,
            name=name,
            constructor_args={"vk": "alice"} if name == "currency" else {},
        )
    driver = client.raw_driver
    driver.set("chi_cost.S:value", 20)
    driver.set("foundation.owner", "foundation")
    driver.set("validators.active_validators", ["validator"])
    driver.set("rewards.S:value", [0, 0, 0, 1])  # the whole fee to developers
    driver.commit()
    client.get_contract_proxy("token_factory").create_token(
        token_contract="con_tok",
        token_name="T",
        token_symbol="T",
        initial_supply=10,
        signer="alice",
    )

    result = _paid_transfer(client, "con_tok", "alice")

    assert result["status"] == 0, result
    # The factory has no way to move currency, so a share credited to it is lost.
    assert set(result["rewards"]["developer_reward"]) == {"alice"}
