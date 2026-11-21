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

CANONICAL = {
    "tx_fee_mode": "paid_metered",
    "max_tx_chi": 200000,
    "max_block_chi": 500000,
}


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
    (
        None,
        {"tx_fee_mode": "paid_metered"},
        {"tx_fee_mode": "paid_metered", "max_tx_chi": 1},
    ),
)
def test_a_missing_or_non_canonical_fee_policy_is_rejected(tmp_path, fee_policy):
    path = _manifest_with(tmp_path, fee_policy)
    with pytest.raises(SystemExit, match="must pin the canonical fee_policy"):
        validate_manifests.validate_pinned_fee_policy(path, read_network_manifest(path))


def _local_manifest(tmp_path: Path, **changes) -> tuple[Path, dict]:
    manifest = (
        json.loads((ROOT / "networks" / "local" / "manifest.json").read_text())
        | changes
    )
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path, read_network_manifest(path)


def _built_genesis_sha256(manifest: dict) -> str:
    from xian.genesis_builder import build_bundle_network_genesis
    from xian.node_setup import genesis_sha256

    return genesis_sha256(
        build_bundle_network_genesis(
            chain_id=manifest["chain_id"],
            network=manifest["genesis"]["bundle"],
            contracts_dir=ROOT / "contracts",
            genesis_time=manifest["genesis"]["genesis_time"],
            runtime_features=manifest.get("runtime_features"),
            fee_policy=manifest["fee_policy"],
        )
    )


def test_a_pinned_genesis_sha256_must_be_the_genesis_the_bundle_builds(tmp_path):
    _, unpinned = _local_manifest(tmp_path)
    path, pinned = _local_manifest(
        tmp_path, genesis_sha256=_built_genesis_sha256(unpinned)
    )
    validate_manifests.validate_pinned_genesis(path, pinned)

    path, stale = _local_manifest(tmp_path, genesis_sha256="0" * 64)
    with pytest.raises(SystemExit, match="genesis_sha256 mismatch"):
        validate_manifests.validate_pinned_genesis(path, stale)


def _mainnet_build(**changes) -> dict:
    manifest = json.loads((ROOT / "networks" / "mainnet" / "manifest.json").read_text())
    return manifest["genesis_build"] | changes


def test_a_draft_mainnet_lists_the_genesis_pin_as_a_finalization_item(tmp_path):
    path, draft = _local_manifest(tmp_path, genesis_build=_mainnet_build())
    validate_manifests.validate_mainnet_genesis_pin(path, draft)

    items = [
        item
        for item in _mainnet_build()["finalization_required"]
        if "genesis_sha256" not in item
    ]
    path, forgotten = _local_manifest(
        tmp_path, genesis_build=_mainnet_build(finalization_required=items)
    )
    with pytest.raises(SystemExit, match="finalization item"):
        validate_manifests.validate_mainnet_genesis_pin(path, forgotten)


def test_a_final_mainnet_must_pin_genesis_sha256(tmp_path):
    path, final = _local_manifest(
        tmp_path, genesis_build=_mainnet_build(status="final")
    )
    with pytest.raises(SystemExit, match="must pin genesis_sha256"):
        validate_manifests.validate_mainnet_genesis_pin(path, final)

    path, pinned = _local_manifest(
        tmp_path, genesis_build=_mainnet_build(status="final"), genesis_sha256="ab" * 32
    )
    validate_manifests.validate_mainnet_genesis_pin(path, pinned)


def _canonical(tmp_path: Path, network: str, **changes) -> tuple[Path, dict]:
    network_dir = shutil.copytree(ROOT / "networks" / network, tmp_path / network)
    path = network_dir / "manifest.json"
    path.write_text(json.dumps(json.loads(path.read_text()) | changes))
    return path, read_network_manifest(path)


@pytest.mark.parametrize("network", ["mainnet"])
def test_canonical_networks_pass_their_rules(network):
    path = ROOT / "networks" / network / "manifest.json"
    validate_manifests.CANONICAL_NETWORK_RULES[network](
        path, read_network_manifest(path)
    )


@pytest.mark.parametrize(
    ("network", "changes", "message"),
    [
        (
            "mainnet",
            {"genesis": {"kind": "bundle", "bundle": "mainnet", "genesis_time": None}},
            "must pin genesis_time",
        ),
        (
            "mainnet",
            {"node_release_manifest": None},
            "must embed node release provenance",
        ),
        ("mainnet", {"chain_id": "xian-mainnet-2"}, "chain_id must be xian-mainnet-1"),
        (
            "mainnet",
            {"runtime_features": {"zk": False}},
            "enable the zk runtime feature",
        ),
        (
            "mainnet",
            {"genesis": {"kind": "bundle", "bundle": "local", "genesis_time": "x"}},
            "derive genesis from the mainnet bundle",
        ),
    ],
)
def test_canonical_network_rules_reject_a_broken_manifest(
    tmp_path, network, changes, message
):
    path, manifest = _canonical(tmp_path, network, **changes)
    with pytest.raises(SystemExit, match=message):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, manifest)


def test_the_checked_in_network_manifests_pass(capsys):
    validate_manifests.validate_network_manifests()

    validated = capsys.readouterr().out.splitlines()
    assert validated == [
        f"validated networks/{name}/manifest.json"
        for name in ("local", "mainnet")
    ]


@pytest.mark.parametrize("network", ["mainnet"])
def test_unreleased_network_recipes_do_not_claim_registry_image_provenance(network):
    path = ROOT / "networks" / network / "manifest.json"
    manifest = read_network_manifest(path)
    assert manifest["genesis_build"]["status"] == "draft-rehearsal"
    assert manifest["node_image_mode"] == "local_build"
    assert manifest["node_integrated_image"] is None
    assert manifest["node_split_image"] is None
    expected = {
        "cometbft_version": "0.40.0",
        "cometbft_source_commit": "0880b4d378f347ab16e54ec677ff50d803f37d62",
        "cometbft_source_url": (
            "https://codeload.github.com/cometbft/cometbft/tar.gz/"
            "0880b4d378f347ab16e54ec677ff50d803f37d62"
        ),
        "cometbft_source_sha256": (
            "c421c1461494d4e1e922a334f1899aab2f638e990a465316ed6e2437a8d71a66"
        ),
    }
    for key, value in expected.items():
        assert manifest["node_release_manifest"]["build"][key] == value


@pytest.mark.parametrize("network", ["mainnet"])
def test_a_draft_network_uses_local_builds_until_release_inputs_are_final(
    tmp_path, network
):
    path, draft = _canonical(tmp_path, network)
    validate_manifests.CANONICAL_NETWORK_RULES[network](path, draft)

    draft.update(
        node_image_mode="registry",
        node_integrated_image="ghcr.io/example/node@sha256:" + "a" * 64,
        node_split_image="ghcr.io/example/split@sha256:" + "b" * 64,
    )
    with pytest.raises(SystemExit, match="draft.*local_build"):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, draft)


@pytest.mark.parametrize("network", ["mainnet"])
def test_draft_release_finalization_cannot_omit_release_and_image_pins(
    tmp_path, network
):
    path, draft = _canonical(tmp_path, network)
    draft["genesis_build"]["finalization_required"] = [
        item
        for item in draft["genesis_build"]["finalization_required"]
        if "node_release_manifest" not in item
    ]
    with pytest.raises(SystemExit, match="release and image finalization"):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, draft)


@pytest.mark.parametrize("network", ["mainnet"])
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("cometbft_version", "0.39.3"),
        ("cometbft_source_commit", "0" * 40),
        ("cometbft_source_url", "https://example.invalid/cometbft.tar.gz"),
        ("cometbft_source_sha256", "0" * 64),
    ],
)
def test_canonical_networks_reject_a_mixed_comet_source_recipe(
    tmp_path, network, key, value
):
    path, draft = _canonical(tmp_path, network)
    draft["node_release_manifest"]["build"][key] = value
    with pytest.raises(SystemExit, match="CometBFT 0.40.0 source recipe"):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, draft)


@pytest.mark.parametrize("network", ["mainnet"])
def test_final_networks_require_registry_images_with_immutable_digests(
    tmp_path, network
):
    path, final = _canonical(tmp_path, network)
    final["genesis_build"]["status"] = "final"
    final["genesis_sha256"] = "ab" * 32
    with pytest.raises(SystemExit, match="published registry images"):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, final)

    final.update(
        node_image_mode="registry",
        node_integrated_image="ghcr.io/example/node@sha256:" + "a" * 64,
        node_split_image="ghcr.io/example/split@sha256:" + "b" * 64,
    )
    validate_manifests.CANONICAL_NETWORK_RULES[network](path, final)
    final["node_split_image"] = "ghcr.io/example/split:latest"
    with pytest.raises(SystemExit, match="immutable image digest"):
        validate_manifests.CANONICAL_NETWORK_RULES[network](path, final)


@pytest.mark.parametrize("mode", ["missing", "late"])
def test_canonical_validator_bundle_requires_its_coordinator_before_membership(mode):
    payload = json.loads((ROOT / "contracts" / "contracts_local.json").read_text())
    contracts = payload["contracts"]
    coordinator = next(
        item for item in contracts if item["name"] == "validator_penalties"
    )
    contracts.remove(coordinator)
    if mode == "late":
        contracts.append(coordinator)
    with pytest.raises(SystemExit, match="penalty coordinator"):
        validate_manifests.validate_validator_coordinator(
            contracts, bundle_path=Path("local.json")
        )
