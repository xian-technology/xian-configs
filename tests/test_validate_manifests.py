import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
from xian_cli.models import read_network_manifest

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "validate_manifests", ROOT / "scripts" / "validate-manifests.py"
)
validate_manifests = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_manifests)

CANONICAL = {"tx_fee_mode": "paid_metered", "max_tx_chi": 200000, "max_block_chi": 500000}


def _manifest_with(tmp_path: Path, fee_policy) -> Path:
    manifest = json.loads((ROOT / "networks" / "local" / "manifest.json").read_text())
    if fee_policy is None:
        manifest.pop("fee_policy", None)
    else:
        manifest["fee_policy"] = fee_policy
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_a_canonical_pinned_fee_policy_is_accepted(tmp_path):
    path = _manifest_with(tmp_path, CANONICAL)
    validate_manifests.validate_pinned_fee_policy(path, read_network_manifest(path))


@pytest.mark.parametrize(
    "fee_policy",
    (None, {"tx_fee_mode": "paid_metered"}, {"tx_fee_mode": "paid_metered", "max_tx_chi": 1}),
)
def test_a_missing_or_non_canonical_fee_policy_is_rejected(tmp_path, fee_policy):
    path = _manifest_with(tmp_path, fee_policy)
    with pytest.raises(SystemExit, match="must pin the canonical fee_policy"):
        validate_manifests.validate_pinned_fee_policy(path, read_network_manifest(path))


def _canonical(tmp_path: Path, network: str, **changes) -> tuple[Path, dict]:
    network_dir = shutil.copytree(ROOT / "networks" / network, tmp_path / network)
    path = network_dir / "manifest.json"
    path.write_text(json.dumps(json.loads(path.read_text()) | changes))
    return path, read_network_manifest(path)


@pytest.mark.parametrize("network", ["testnet", "mainnet"])
def test_canonical_networks_pass_their_rules(network):
    path = ROOT / "networks" / network / "manifest.json"
    validate_manifests.CANONICAL_NETWORK_RULES[network](path, read_network_manifest(path))


@pytest.mark.parametrize(
    ("network", "changes", "message"),
    [
        (
            "testnet",
            {"genesis": {"kind": "bundle", "bundle": "testnet", "genesis_time": None}},
            "must pin genesis_time",
        ),
        ("testnet", {"node_release_manifest": None}, "must embed node release provenance"),
        ("mainnet", {"chain_id": "xian-mainnet-2"}, "chain_id must be xian-mainnet-1"),
        ("mainnet", {"runtime_features": {"zk": False}}, "enable the zk runtime feature"),
        (
            "mainnet",
            {"genesis": {"kind": "bundle", "bundle": "testnet", "genesis_time": "x"}},
            "derive genesis from the mainnet bundle",
        ),
    ],
)
def test_canonical_network_rules_reject_a_broken_manifest(tmp_path, network, changes, message):
    path, manifest = _canonical(tmp_path, network, **changes)
    with pytest.raises(SystemExit, match=message):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, manifest)


def test_the_checked_in_network_manifests_pass(capsys):
    validate_manifests.validate_network_manifests()

    validated = capsys.readouterr().out.splitlines()
    assert validated == [
        f"validated networks/{name}/manifest.json"
        for name in ("devnet", "local", "mainnet", "testnet")
    ]
