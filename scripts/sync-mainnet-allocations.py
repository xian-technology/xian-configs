#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOCATIONS_PATH = REPO_ROOT / "contracts" / "mainnet_allocations.json"
BUNDLE_PATH = REPO_ROOT / "contracts" / "contracts_mainnet.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_amount(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("allocation amounts must not be boolean")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid allocation amount: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"allocation amount must be finite: {value!r}")
    if amount < 0:
        raise ValueError(f"allocation amount must not be negative: {value!r}")
    return format(amount, "f")


def load_allocation_balances(path: Path = ALLOCATIONS_PATH) -> dict[str, str]:
    payload = load_json(path)
    if payload.get("schema") != "xian.mainnet_allocations.v1":
        raise ValueError(f"unsupported allocation schema in {path}")
    if payload.get("schema_version") != 1:
        raise ValueError(f"unsupported allocation schema_version in {path}")
    if payload.get("network") != "mainnet":
        raise ValueError(f"allocation network must be mainnet in {path}")
    if payload.get("chain_id") != "xian-mainnet-1":
        raise ValueError(f"allocation chain_id must be xian-mainnet-1 in {path}")

    currency = payload.get("currency")
    if not isinstance(currency, dict):
        raise ValueError(f"allocation currency must be an object in {path}")
    balances = currency.get("balances")
    if not isinstance(balances, dict) or not balances:
        raise ValueError(f"allocation currency.balances must be a non-empty object in {path}")

    normalized: dict[str, str] = {}
    total_supply = Decimal("0")
    for account, raw_amount in balances.items():
        if not isinstance(account, str) or not account:
            raise ValueError(f"allocation account must be a non-empty string in {path}")
        amount_text = normalize_amount(raw_amount)
        normalized[account] = amount_text
        total_supply += Decimal(amount_text)

    if total_supply <= 0:
        raise ValueError(f"allocation total supply must be positive in {path}")
    return normalized


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

    balances = load_allocation_balances()
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
