#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from generate_token_factory_artifacts import verify_token_factory_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PRESET_NAMES = ("local", "devnet", "testnet")
REQUIRED_MASTERNODES_CONSTRUCTOR_ARGS = (
    "genesis_nodes",
    "genesis_registration_fee",
    "default_node_power",
    "selection_mode",
    "max_validators",
    "power_mode",
    "rebalance_interval",
    "activation_delay_epochs",
    "unbonding_period_days",
    "min_self_bond",
    "min_total_bond",
    "max_commission_bps",
    "max_active_set_churn",
    "min_bond_margin_bps",
    "manual_override_enabled",
    "slash_destination",
    "duplicate_vote_slash_bps",
    "duplicate_vote_jail",
    "light_client_attack_slash_bps",
    "light_client_attack_jail",
)
CANONICAL_TESTNET_NODE_COUNT = 5
SUPPORTED_PRIVACY_ARTIFACT_KINDS = {
    "shielded_note",
    "shielded_command",
    "shielded_relay",
}
REQUIRED_GOVERNANCE_CONSTRUCTOR_ARGS = (
    "membership_contract_name",
    "approval_threshold_numerator",
    "approval_threshold_denominator",
    "proposal_expiry_days",
    "min_patch_delay_blocks",
    "emergency_threshold_numerator",
    "emergency_threshold_denominator",
    "emergency_patch_delay_blocks",
)

try:
    from xian_cli.models import (
        read_network_manifest,
        read_network_template,
        read_solution_pack,
    )
except ModuleNotFoundError as exc:
    raise SystemExit(
        "xian-cli must be installed in the current environment; run this "
        "script via `uv run --project ../xian-cli python ./scripts/validate-manifests.py`"
    ) from exc


def validate_contract_bundles() -> None:
    contracts_dir = REPO_ROOT / "contracts"
    bundle_paths = sorted(contracts_dir.glob("contracts_*.json"))
    expected_names = {f"contracts_{name}.json" for name in ACTIVE_PRESET_NAMES}
    actual_names = {path.name for path in bundle_paths}
    if actual_names != expected_names:
        raise SystemExit(
            "active contract bundles must match preset set exactly; "
            f"expected {sorted(expected_names)}, found {sorted(actual_names)}"
        )

    for preset_name in ACTIVE_PRESET_NAMES:
        bundle_path = contracts_dir / f"contracts_{preset_name}.json"
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        contracts = payload.get("contracts")
        if not isinstance(contracts, list) or not contracts:
            raise SystemExit(
                f"contract bundle has no contracts array: {bundle_path}"
            )

        members_contract = next(
            (
                contract
                for contract in contracts
                if contract.get("submit_as") == "masternodes"
            ),
            None,
        )
        if members_contract is None:
            raise SystemExit(
                f"contract bundle missing masternodes seed data: {bundle_path}"
            )

        constructor_args = members_contract.get("constructor_args")
        if not isinstance(constructor_args, dict):
            raise SystemExit(
                "masternodes constructor_args must be an object in "
                f"{bundle_path}"
            )

        missing_keys = [
            key
            for key in REQUIRED_MASTERNODES_CONSTRUCTOR_ARGS
            if key not in constructor_args
        ]
        if missing_keys:
            raise SystemExit(
                "masternodes constructor_args must pin the full validator "
                f"policy surface in {bundle_path}; missing {missing_keys}"
            )

        genesis_nodes = constructor_args["genesis_nodes"]
        if not isinstance(genesis_nodes, list) or not genesis_nodes:
            raise SystemExit(
                f"masternodes genesis_nodes must be a non-empty list in {bundle_path}"
            )

        if preset_name == "testnet":
            if len(genesis_nodes) != CANONICAL_TESTNET_NODE_COUNT:
                raise SystemExit(
                    "canonical testnet must define exactly "
                    f"{CANONICAL_TESTNET_NODE_COUNT} genesis nodes in {bundle_path}"
                )

            genesis_powers = constructor_args.get("genesis_powers")
            if not isinstance(genesis_powers, dict):
                raise SystemExit(
                    "canonical testnet must define explicit genesis_powers in "
                    f"{bundle_path}"
                )
            if sorted(genesis_powers) != sorted(genesis_nodes):
                raise SystemExit(
                    "canonical testnet genesis_powers keys must match "
                    f"genesis_nodes exactly in {bundle_path}"
                )
            if any(
                not isinstance(power, int) or power <= 0
                for power in genesis_powers.values()
            ):
                raise SystemExit(
                    "canonical testnet genesis_powers must be positive integers "
                    f"in {bundle_path}"
                )

            genesis_reward_keys = constructor_args.get("genesis_reward_keys")
            if not isinstance(genesis_reward_keys, dict):
                raise SystemExit(
                    "canonical testnet must define explicit genesis_reward_keys in "
                    f"{bundle_path}"
                )
            if sorted(genesis_reward_keys) != sorted(genesis_nodes):
                raise SystemExit(
                    "canonical testnet genesis_reward_keys keys must match "
                    f"genesis_nodes exactly in {bundle_path}"
                )
            if any(
                not isinstance(reward_key, str) or not reward_key
                for reward_key in genesis_reward_keys.values()
            ):
                raise SystemExit(
                    "canonical testnet genesis_reward_keys values must be "
                    f"non-empty strings in {bundle_path}"
                )

            rewards_contract = next(
                (
                    contract
                    for contract in contracts
                    if contract.get("name") == "rewards"
                ),
                None,
            )
            if rewards_contract is None:
                raise SystemExit(
                    f"canonical testnet missing rewards contract in {bundle_path}"
                )
            rewards_args = rewards_contract.get("constructor_args")
            if not isinstance(rewards_args, dict):
                raise SystemExit(
                    "canonical testnet must pin rewards constructor_args in "
                    f"{bundle_path}"
                )
            reward_split = rewards_args.get("initial_split")
            if (
                not isinstance(reward_split, list)
                or len(reward_split) != 4
                or any(not isinstance(item, (int, float)) for item in reward_split)
            ):
                raise SystemExit(
                    "canonical testnet rewards initial_split must be a 4-item "
                    f"numeric list in {bundle_path}"
                )
            if any(item <= 0 for item in reward_split):
                raise SystemExit(
                    "canonical testnet rewards initial_split must contain only "
                    f"positive values in {bundle_path}"
                )
            if abs(sum(reward_split) - 1) > 1e-9:
                raise SystemExit(
                    "canonical testnet rewards initial_split must sum to 1 in "
                    f"{bundle_path}"
                )

            governance_contract = next(
                (
                    contract
                    for contract in contracts
                    if contract.get("name") == "governance"
                ),
                None,
            )
            if governance_contract is None:
                raise SystemExit(
                    f"canonical testnet missing governance contract in {bundle_path}"
                )
            governance_args = governance_contract.get("constructor_args")
            if not isinstance(governance_args, dict):
                raise SystemExit(
                    "canonical testnet must pin governance constructor_args in "
                    f"{bundle_path}"
                )
            missing_governance_keys = [
                key
                for key in REQUIRED_GOVERNANCE_CONSTRUCTOR_ARGS
                if key not in governance_args
            ]
            if missing_governance_keys:
                raise SystemExit(
                    "canonical testnet governance constructor_args must pin the "
                    f"full surface in {bundle_path}; missing "
                    f"{missing_governance_keys}"
                )
            if governance_args["membership_contract_name"] != "masternodes":
                raise SystemExit(
                    "canonical testnet governance membership_contract_name must "
                    f"be masternodes in {bundle_path}"
                )
            if (
                not isinstance(governance_args["approval_threshold_numerator"], int)
                or not isinstance(governance_args["approval_threshold_denominator"], int)
                or governance_args["approval_threshold_numerator"] <= 0
                or governance_args["approval_threshold_denominator"] <= 0
                or governance_args["approval_threshold_numerator"]
                > governance_args["approval_threshold_denominator"]
            ):
                raise SystemExit(
                    "canonical testnet governance approval threshold must be a "
                    f"valid positive ratio in {bundle_path}"
                )
            if (
                not isinstance(governance_args["emergency_threshold_numerator"], int)
                or not isinstance(governance_args["emergency_threshold_denominator"], int)
                or governance_args["emergency_threshold_numerator"] <= 0
                or governance_args["emergency_threshold_denominator"] <= 0
                or governance_args["emergency_threshold_numerator"]
                > governance_args["emergency_threshold_denominator"]
            ):
                raise SystemExit(
                    "canonical testnet governance emergency threshold must be a "
                    f"valid positive ratio in {bundle_path}"
                )
            for key in (
                "proposal_expiry_days",
                "min_patch_delay_blocks",
                "emergency_patch_delay_blocks",
            ):
                value = governance_args[key]
                if not isinstance(value, int) or value <= 0:
                    raise SystemExit(
                        f"canonical testnet governance {key} must be a "
                        f"positive integer in {bundle_path}"
                    )

        print(f"validated {bundle_path.relative_to(REPO_ROOT)}")


def _sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_privacy_artifact_catalog(
    *,
    manifest_path: Path,
    manifest: dict,
) -> None:
    catalog_ref = manifest.get("privacy_artifact_catalog")
    if not isinstance(catalog_ref, dict):
        raise SystemExit(
            "canonical network manifests must define privacy_artifact_catalog in "
            f"{manifest_path}"
        )

    catalog_path = (manifest_path.parent / catalog_ref["path"]).resolve()
    if not catalog_path.exists():
        raise SystemExit(
            f"privacy artifact catalog path does not exist for {manifest_path}: "
            f"{catalog_path}"
        )
    expected_sha256 = catalog_ref["sha256"]
    observed_sha256 = _sha256_text(catalog_path)
    if observed_sha256 != expected_sha256:
        raise SystemExit(
            f"privacy artifact catalog sha256 mismatch for {catalog_path}; "
            f"expected {expected_sha256}, observed {observed_sha256}"
        )

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise SystemExit(
            f"privacy artifact catalog schema_version must be 1 in {catalog_path}"
        )
    if payload.get("network") != manifest["name"]:
        raise SystemExit(
            f"privacy artifact catalog network must match manifest name in {catalog_path}"
        )
    bundle_policy = payload.get("bundle_policy")
    if not isinstance(bundle_policy, dict):
        raise SystemExit(
            f"privacy artifact catalog must define bundle_policy in {catalog_path}"
        )
    approved_setup_modes = bundle_policy.get("approved_setup_modes")
    if not isinstance(approved_setup_modes, list) or not approved_setup_modes:
        raise SystemExit(
            f"privacy artifact catalog must define non-empty approved_setup_modes in {catalog_path}"
        )
    if any(not isinstance(item, str) or not item for item in approved_setup_modes):
        raise SystemExit(
            f"privacy artifact catalog approved_setup_modes must contain non-empty strings in {catalog_path}"
        )
    if not isinstance(bundle_policy.get("allow_single_party"), bool):
        raise SystemExit(
            f"privacy artifact catalog allow_single_party must be boolean in {catalog_path}"
        )
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise SystemExit(
            f"privacy artifact catalog artifacts must be a list in {catalog_path}"
        )
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise SystemExit(
                f"privacy artifact entry {index} must be an object in {catalog_path}"
            )
        if artifact.get("kind") not in SUPPORTED_PRIVACY_ARTIFACT_KINDS:
            raise SystemExit(
                f"privacy artifact entry {index} has unsupported kind in {catalog_path}"
            )
        registry_manifest_path = artifact.get("registry_manifest_path")
        if not isinstance(registry_manifest_path, str) or not registry_manifest_path:
            raise SystemExit(
                f"privacy artifact entry {index} must define registry_manifest_path in {catalog_path}"
            )
        registry_manifest = (catalog_path.parent / registry_manifest_path).resolve()
        if not registry_manifest.exists():
            raise SystemExit(
                f"privacy artifact registry manifest does not exist: {registry_manifest}"
            )
        artifact_sha256 = artifact.get("sha256")
        if (
            not isinstance(artifact_sha256, str)
            or len(artifact_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in artifact_sha256)
        ):
            raise SystemExit(
                f"privacy artifact entry {index} must define a lowercase sha256 in {catalog_path}"
            )
        observed_artifact_sha256 = _sha256_text(registry_manifest)
        if observed_artifact_sha256 != artifact_sha256:
            raise SystemExit(
                f"privacy artifact registry manifest sha256 mismatch for "
                f"{registry_manifest}; expected {artifact_sha256}, observed "
                f"{observed_artifact_sha256}"
            )
        registry_payload = json.loads(registry_manifest.read_text(encoding="utf-8"))
        if not isinstance(registry_payload.get("registry_entries"), list):
            raise SystemExit(
                f"privacy artifact registry manifest must expose registry_entries in {registry_manifest}"
            )
        if registry_payload.get("contract_name") != artifact.get("contract_name"):
            raise SystemExit(
                f"privacy artifact contract_name mismatch between catalog and registry manifest in {registry_manifest}"
            )


def validate_network_manifests() -> None:
    manifest_paths = sorted((REPO_ROOT / "networks").glob("*/manifest.json"))
    if not manifest_paths:
        raise SystemExit("no canonical manifests found under networks/")

    for manifest_path in manifest_paths:
        manifest = read_network_manifest(manifest_path)
        validate_privacy_artifact_catalog(
            manifest_path=manifest_path,
            manifest=manifest,
        )
        if not isinstance(manifest.get("shielded_history_policy"), dict):
            raise SystemExit(
                "canonical network manifests must define shielded_history_policy in "
                f"{manifest_path}"
            )
        if not isinstance(manifest.get("privacy_submission_policy"), dict):
            raise SystemExit(
                "canonical network manifests must define privacy_submission_policy in "
                f"{manifest_path}"
            )
        if manifest["name"] == "testnet":
            if manifest["genesis_preset"] != "testnet":
                raise SystemExit(
                    "canonical testnet must derive genesis from the testnet preset "
                    f"in {manifest_path}"
                )
            if manifest["genesis_time"] is None:
                raise SystemExit(
                    "canonical testnet must pin genesis_time in "
                    f"{manifest_path}"
                )
            if manifest["genesis_source"] is not None:
                raise SystemExit(
                    "canonical testnet must not use a checked-in genesis_source in "
                    f"{manifest_path}"
                )
            if manifest["node_image_mode"] != "registry":
                raise SystemExit(
                    "canonical testnet must pin published registry images in "
                    f"{manifest_path}"
                )
            if (
                manifest["node_integrated_image"] is None
                or manifest["node_split_image"] is None
            ):
                raise SystemExit(
                    "canonical testnet registry image mode requires both node "
                    f"images in {manifest_path}"
                )
            if not isinstance(manifest["node_release_manifest"], dict):
                raise SystemExit(
                    "canonical testnet must embed node release provenance in "
                    f"{manifest_path}"
                )

        print(f"validated {manifest_path.relative_to(REPO_ROOT)}")


def main() -> int:
    verify_token_factory_artifacts()
    validate_network_manifests()

    template_paths = sorted((REPO_ROOT / "templates").glob("*.json"))
    if not template_paths:
        raise SystemExit("no canonical templates found under templates/")

    for template_path in template_paths:
        read_network_template(template_path)
        print(f"validated {template_path.relative_to(REPO_ROOT)}")

    solution_pack_paths = sorted(
        (REPO_ROOT / "solution-packs").glob("*/pack.json")
    )
    if not solution_pack_paths:
        raise SystemExit("no canonical solution packs found under solution-packs/")

    for solution_pack_path in solution_pack_paths:
        read_solution_pack(solution_pack_path)
        print(f"validated {solution_pack_path.relative_to(REPO_ROOT)}")

    validate_contract_bundles()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
