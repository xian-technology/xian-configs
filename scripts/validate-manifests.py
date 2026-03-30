#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

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

        print(f"validated {bundle_path.relative_to(REPO_ROOT)}")


def main() -> int:
    manifest_paths = sorted((REPO_ROOT / "networks").glob("*/manifest.json"))
    if not manifest_paths:
        raise SystemExit("no canonical manifests found under networks/")

    for manifest_path in manifest_paths:
        read_network_manifest(manifest_path)
        print(f"validated {manifest_path.relative_to(REPO_ROOT)}")

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
