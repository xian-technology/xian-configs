#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).absolute().parent))
from mainnet_allocations import allocation_total, load_allocation_balances  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOCATIONS_PATH = REPO_ROOT / "contracts" / "mainnet_allocations.json"
BUNDLE_PATH = REPO_ROOT / "contracts" / "contracts_mainnet.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def currency_contract(bundle: dict[str, Any]) -> dict[str, Any]:
    contracts = bundle.get("contracts")
    if not isinstance(contracts, list):
        raise ValueError("contract bundle must contain a contracts list")
    for contract in contracts:
        if isinstance(contract, dict) and contract.get("name") == "currency":
            return contract
    raise ValueError("contract bundle missing currency contract")


def expected_bundle_payload(bundle: dict[str, Any], balances: dict[str, str]) -> dict[str, Any]:
    expected = json.loads(json.dumps(bundle))
    currency = currency_contract(expected)
    constructor_args = currency.get("constructor_args")
    if constructor_args is None:
        constructor_args = {}
        currency["constructor_args"] = constructor_args
    if not isinstance(constructor_args, dict):
        raise ValueError("currency constructor_args must be an object")
    constructor_args["initial_balances"] = balances
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize contracts_mainnet.json from mainnet_allocations.json."
    )
    parser.add_argument("--check", action="store_true", help="fail if the bundle is stale")
    args = parser.parse_args()

    balances = load_allocation_balances(ALLOCATIONS_PATH)
    print(f"{len(balances)} holders, total supply {allocation_total(balances)}")
    bundle = load_json(BUNDLE_PATH)
    expected = expected_bundle_payload(bundle, balances)

    if args.check:
        if expected != bundle:
            raise SystemExit("contracts_mainnet.json is stale; run sync-mainnet-allocations.py")
        print("contracts_mainnet.json matches mainnet_allocations.json")
        return 0

    BUNDLE_PATH.write_text(
        json.dumps(expected, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"updated {BUNDLE_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
