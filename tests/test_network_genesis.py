import json
from pathlib import Path

import pytest
from xian.execution_policy import validate_genesis_execution_policy
from xian.genesis_builder import build_bundle_network_genesis


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = sorted((ROOT / "networks").glob("*/manifest.json"))


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda path: path.parent.name)
def test_network_genesis_deploys_each_bundle_contract_on_v2(manifest_path):
    manifest = json.loads(manifest_path.read_text())
    source = manifest["genesis"]
    contracts_dir = ROOT / "contracts"
    genesis = build_bundle_network_genesis(
        chain_id=manifest["chain_id"],
        network=source["bundle"],
        genesis_time=source["genesis_time"],
        runtime_features=manifest.get("runtime_features"),
        contracts_dir=contracts_dir,
    )
    validate_genesis_execution_policy(genesis)
    bundle = json.loads((contracts_dir / f"contracts_{source['bundle']}.json").read_text())
    names = {entry.get("submit_as") or entry["name"] for entry in bundle["contracts"]}
    names.add("submission")
    profiles = {
        entry["key"].removesuffix(".__xian_ir_v1__"): json.loads(entry["value"])["vm_profile"]
        for entry in genesis["abci_genesis"]["genesis"]
        if entry["key"].endswith(".__xian_ir_v1__")
    }
    assert profiles == dict.fromkeys(names, "xian_vm_v2")
