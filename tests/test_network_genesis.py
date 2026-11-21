import json
import shutil
from pathlib import Path

import pytest
from xian.execution_policy import validate_genesis_execution_policy
from xian.fee_policy import FEE_POLICY_KEY, fee_policy_state
from xian.genesis_builder import build_bundle_network_genesis
from xian_runtime_types.encoding import encode_wire
from xian_cli.cli import main


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
        fee_policy=manifest["fee_policy"],
        contracts_dir=contracts_dir,
    )
    validate_genesis_execution_policy(genesis)
    # Every network pins its hard chi caps explicitly, in canonical form.
    assert manifest["fee_policy"] == fee_policy_state(manifest["fee_policy"])
    assert [
        entry["value"]
        for entry in genesis["abci_genesis"]["genesis"]
        if entry["key"] == FEE_POLICY_KEY
    ] == [manifest["fee_policy"]]
    bundle = json.loads((contracts_dir / f"contracts_{source['bundle']}.json").read_text())
    names = {entry.get("submit_as") or entry["name"] for entry in bundle["contracts"]}
    names.add("submission")
    profiles = {
        entry["key"].removesuffix(".__xian_ir_v1__"): json.loads(entry["value"])["vm_profile"]
        for entry in genesis["abci_genesis"]["genesis"]
        if entry["key"].endswith(".__xian_ir_v1__")
    }
    assert profiles == dict.fromkeys(names, "xian_vm_v2")


def _bundle_genesis_bytes(manifest: dict, contracts_dir: Path) -> str:
    source = manifest["genesis"]
    genesis = build_bundle_network_genesis(
        chain_id=manifest["chain_id"],
        network=source["bundle"],
        genesis_time=source["genesis_time"],
        runtime_features=manifest.get("runtime_features"),
        fee_policy=manifest["fee_policy"],
        contracts_dir=contracts_dir,
    )
    return encode_wire(genesis, vm_profile="xian_vm_v2")


def test_every_operator_builds_the_same_mainnet_genesis(tmp_path):
    """Operators build a bundle genesis independently: the bytes, not only the
    app hash, must not depend on where the assets live or on the run."""
    manifest = json.loads((ROOT / "networks" / "mainnet" / "manifest.json").read_text())
    copy = tmp_path / "elsewhere" / "contracts"
    shutil.copytree(ROOT / "contracts", copy, ignore=shutil.ignore_patterns("__pycache__"))

    first = _bundle_genesis_bytes(manifest, ROOT / "contracts")

    assert _bundle_genesis_bytes(manifest, copy) == first
    assert json.loads(first)["app_hash"] == json.loads(first)["abci_genesis"]["hash"]


@pytest.mark.parametrize("network", ["mainnet"])
def test_draft_operator_bundles_keep_local_build_intent_and_pin_rendered_genesis(
    tmp_path, capsys, network
):
    output = tmp_path / f"{network}-bundle"
    assert main(
        [
            "network",
            "package-operator-bundle",
            network,
            "--base-dir",
            str(tmp_path),
            "--configs-dir",
            str(ROOT),
            "--output",
            str(output),
            "--bootstrap-seed",
            "fixture@127.0.0.1:26656",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)
    bundled = json.loads(Path(result["manifest_path"]).read_text())
    assert bundled["node_image_mode"] == "local_build"
    assert bundled.get("node_integrated_image") is None
    assert bundled.get("node_split_image") is None
    assert bundled["genesis_build"]["status"] == "draft-rehearsal"
    assert bundled["node_release_manifest"]["build"]["cometbft_version"] == "0.40.0"
    assert bundled["node_release_manifest"]["build"]["cometbft_source_commit"] == (
        "0880b4d378f347ab16e54ec677ff50d803f37d62"
    )
    assert bundled["genesis"] == {"kind": "source", "source": "./genesis.json"}
    genesis = output / "networks" / network / "genesis.json"
    from xian.node_setup import genesis_sha256

    assert bundled["genesis_sha256"] == genesis_sha256(json.loads(genesis.read_text()))
