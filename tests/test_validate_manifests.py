import importlib.util
import json
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
