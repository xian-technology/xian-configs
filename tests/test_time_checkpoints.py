"""Native contract proof for the shared successor-height time registry."""

import json
from pathlib import Path

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.decimal import ContractingDecimal
from xian_runtime_types.time import Datetime
from xian_vm_core import execute_tx

ROOT = Path(__file__).absolute().parents[1]
SOURCE = ROOT / "contracts" / "time_checkpoints.s.py"
SYSTEM = "__time_checkpoints__"
OLD = Datetime(2026, 1, 1)
FRESH = Datetime(2026, 4, 11)
LATER = Datetime(2026, 5, 1)


def env(height, clock=OLD):
    return {"block_num": height, "now": clock}


@pytest.fixture
def registry(tmp_path):
    client = ContractingClient(storage_home=tmp_path / "state")
    client.submit(SOURCE.read_text(), name="time_checkpoints", owner=None)
    yield client, client.get_contract_proxy("time_checkpoints")
    client.close()


def ready(service):
    assert service.process_time_anchors(signer=SYSTEM, environment=env(1)) == 0


@pytest.mark.parametrize("network", ["local", "mainnet"])
def test_canonical_bundles_deploy_the_immutable_registry(network):
    payload = json.loads((ROOT / f"contracts/contracts_{network}.json").read_text())
    matches = [item for item in payload["contracts"] if item["name"] == "time_checkpoints"]
    assert matches == [{"name": "time_checkpoints", "owner": None, "constructor_args": None}]


def test_requests_fail_before_a_real_keeper_has_marked_readiness(registry):
    client, service = registry
    assert service.get_protocol_version() == 1
    assert client.raw_driver.get("time_checkpoints.keeper_ready") is False
    with pytest.raises(AssertionError, match="keeper is not ready"):
        service.request_anchor(signer="alice", environment=env(100))
    assert client.raw_driver.get("time_checkpoints.next_job_id") == 1
    assert client.raw_driver.get("time_checkpoints.queue_head") == 0
    ready(service)
    assert client.raw_driver.get("time_checkpoints.keeper_ready") is True


@pytest.mark.parametrize("caller", ["alice", "sys", "validators", "con_attacker"])
def test_only_the_reserved_keeper_can_mark_readiness_or_process(registry, caller):
    client, service = registry
    with pytest.raises(AssertionError, match="reserved time keeper"):
        service.process_time_anchors(signer=caller, environment=env(1))
    assert client.raw_driver.get("time_checkpoints.keeper_ready") is False


@pytest.mark.parametrize("height", [0, -1, True, False, "100", None])
def test_a_request_uses_only_a_positive_integer_vm_height(registry, height):
    client, service = registry
    ready(service)
    with pytest.raises((AssertionError, TypeError)):
        service.request_anchor(signer="alice", environment=env(height))
    assert client.raw_driver.get("time_checkpoints.queue_head") == 0
    with pytest.raises((AssertionError, TypeError)):
        service.request_anchor(height=100, signer="alice", environment=env(100))


def test_pending_and_served_heights_are_deduplicated_and_never_retimed(registry):
    client, service = registry
    ready(service)
    assert service.get_anchor(height=100) is None
    assert service.request_anchor(signer="alice", environment=env(100)) == 100
    assert service.request_anchor(signer="bob", environment=env(100)) == 100
    assert client.raw_driver.get("time_checkpoints.next_job_id") == 2
    assert service.process_time_anchors(signer=SYSTEM, environment=env(100)) == 0
    assert service.get_anchor(height=100) is None
    assert service.process_time_anchors(signer=SYSTEM, environment=env(101, FRESH)) == 1
    assert service.get_anchor(height=100) == FRESH
    # A repeated served-height request remains idempotent even in an injected
    # older environment; the real node never rewinds its committed height.
    assert service.request_anchor(signer="alice", environment=env(100, LATER)) == 100
    assert service.process_time_anchors(signer=SYSTEM, environment=env(102, LATER)) == 0
    assert service.get_anchor(height=100) == FRESH
    assert client.raw_driver.get("time_checkpoints.next_job_id") == 2
    assert client.raw_driver.get("time_checkpoints.queue_head") == 0
    assert client.raw_driver.get("time_checkpoints.queue_tail") == 0


def test_the_first_positive_height_is_a_valid_request_and_query(registry):
    _, service = registry
    ready(service)
    assert service.get_anchor(height=1) is None
    assert service.request_anchor(signer="alice", environment=env(1)) == 1
    assert service.process_time_anchors(signer=SYSTEM, environment=env(1)) == 0
    assert service.process_time_anchors(signer=SYSTEM, environment=env(2, FRESH)) == 1
    assert service.get_anchor(height=1) == FRESH


@pytest.mark.parametrize("maximum", [0, -1, 33, True, False, "32"])
def test_invalid_work_budgets_cannot_mark_readiness(registry, maximum):
    client, service = registry
    with pytest.raises((AssertionError, TypeError)):
        service.process_time_anchors(max_work=maximum, signer=SYSTEM, environment=env(1))
    assert client.raw_driver.get("time_checkpoints.keeper_ready") is False


@pytest.mark.parametrize("height", [0, -1, True, False, "100", None])
def test_invalid_anchor_query_heights_are_rejected(registry, height):
    _, service = registry
    with pytest.raises((AssertionError, TypeError)):
        service.get_anchor(height=height)


def test_ready_empty_processing_and_duplicate_requests_have_no_writes(registry):
    client, service = registry
    ready(service)
    idle = client.executor.execute(
        sender=SYSTEM,
        contract_name="time_checkpoints",
        function_name="process_time_anchors",
        kwargs={"max_work": 32},
        environment=env(2),
        metering=True,
    )
    assert idle["status_code"] == 0
    assert idle["result"] == 0
    assert not idle["writes"]
    assert idle["chi_used"] > 0
    service.request_anchor(signer="alice", environment=env(100))
    duplicate = client.executor.execute(
        sender="bob",
        contract_name="time_checkpoints",
        function_name="request_anchor",
        kwargs={},
        environment=env(100),
        metering=True,
    )
    assert duplicate["status_code"] == 0
    assert duplicate["result"] == 100
    assert not duplicate["writes"]
    assert duplicate["chi_used"] > 0


def test_public_requests_pay_normal_native_fees_without_partial_intents(registry):
    client, service = registry
    payer = "a" * 64
    balance_key = f"currency.balances:{payer}"
    client.raw_driver.set(balance_key, ContractingDecimal("1000"))
    client.raw_driver.set("chi_cost.S:value", 20)
    client.raw_driver.commit()

    def paid_request():
        storage, pending = client.raw_driver.committed_storage()
        return execute_tx(
            storage,
            pending,
            sender=payer,
            contract_name="time_checkpoints",
            function_name="request_anchor",
            kwargs={},
            context={
                **env(100),
                "signer": payer,
                "caller": payer,
                "this": "time_checkpoints",
                "entry": ("time_checkpoints", "request_anchor"),
                "chain_id": "local-time-checkpoint-test",
                "__input_hash": "11",
            },
            meter=True,
            charge_fees=True,
            chi_budget=1000,
        )

    refused = paid_request()
    assert refused.status_code == 1
    assert "keeper is not ready" in str(refused.result)
    assert set(refused.writes) == {balance_key}
    after_refusal = client.raw_driver.get(balance_key)
    assert after_refusal < 1000
    assert client.raw_driver.get("time_checkpoints.queue_head") == 0
    assert client.raw_driver.get("time_checkpoints.next_job_id") == 1
    ready(service)
    accepted = paid_request()
    assert accepted.status_code == 0
    assert accepted.result == 100
    assert accepted.chi_used > 0
    assert balance_key in accepted.writes
    assert client.raw_driver.get(balance_key) < after_refusal
    assert client.raw_driver.get("time_checkpoints.pending_heights:100") == 1


def test_sparse_height_backlog_is_fifo_and_each_call_processes_at_most_32(registry):
    client, service = registry
    ready(service)
    heights = [100 + index * 1_000_000 for index in range(33)]
    for height in heights:
        assert service.request_anchor(signer="alice", environment=env(height)) == height
    assert client.raw_driver.get("time_checkpoints.queue_head") == 1
    assert client.raw_driver.get("time_checkpoints.queue_tail") == 33
    assert client.raw_driver.get("time_checkpoints.next_job_id") == 34
    successor = heights[-1] + 1
    assert service.process_time_anchors(signer=SYSTEM, environment=env(successor, FRESH)) == 32
    assert [service.get_anchor(height=h) for h in heights[:32]] == [FRESH] * 32
    assert service.get_anchor(height=heights[-1]) is None
    assert client.raw_driver.get("time_checkpoints.queue_head") == 33
    assert service.process_time_anchors(
        max_work=1, signer=SYSTEM, environment=env(successor + 1, LATER)
    ) == 1
    assert service.get_anchor(height=heights[-1]) == LATER
    assert client.raw_driver.get("time_checkpoints.queue_head") == 0


def test_anchor_and_queue_survive_restart_without_callbacks_or_retiming(tmp_path):
    home = tmp_path / "restart"
    with ContractingClient(storage_home=home) as client:
        client.submit(SOURCE.read_text(), name="time_checkpoints", owner=None)
        service = client.get_contract_proxy("time_checkpoints")
        ready(service)
        service.request_anchor(signer="alice", environment=env(100))
        client.raw_driver.commit()
    with ContractingClient(storage_home=home) as client:
        service = client.get_contract_proxy("time_checkpoints")
        assert service.process_time_anchors(signer=SYSTEM, environment=env(101, FRESH)) == 1
        client.raw_driver.commit()
    with ContractingClient(storage_home=home) as client:
        service = client.get_contract_proxy("time_checkpoints")
        assert service.get_anchor(height=100) == FRESH
        assert service.process_time_anchors(signer=SYSTEM, environment=env(102, LATER)) == 0
        assert service.get_anchor(height=100) == FRESH


def test_an_already_recorded_anchor_is_immutable_even_with_a_stale_queued_copy(registry):
    client, service = registry
    ready(service)
    service.request_anchor(signer="alice", environment=env(100))
    client.raw_driver.set("time_checkpoints.anchors:100", OLD)
    client.raw_driver.commit()
    assert service.process_time_anchors(signer=SYSTEM, environment=env(101, FRESH)) == 1
    assert service.get_anchor(height=100) == OLD


@pytest.mark.parametrize("version", [None, True, 2, "1"])
def test_a_malformed_or_unsupported_protocol_fails_closed(registry, version):
    client, service = registry
    client.raw_driver.set("time_checkpoints.protocol_version", version)
    client.raw_driver.commit()
    with pytest.raises(AssertionError, match="unsupported time checkpoint protocol"):
        service.process_time_anchors(signer=SYSTEM, environment=env(1))
    assert client.raw_driver.get("time_checkpoints.keeper_ready") is False
    client.raw_driver.set("time_checkpoints.keeper_ready", True)
    client.raw_driver.commit()
    with pytest.raises(AssertionError, match="unsupported time checkpoint protocol"):
        service.request_anchor(signer="alice", environment=env(100))
