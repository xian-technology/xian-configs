"""Parse ``contracts/mainnet_allocations.json``: the migrated genesis balances.

Each entry must reach genesis exactly as written. Anything that could change
on the way (a JSON number rounded through a float, a holder listed twice, more
fractional digits than the VM keeps, a key spelling no signer spends from) is
refused here, before it becomes chain state.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = "xian.mainnet_allocations.v1"
CHAIN_ID = "xian-mainnet-1"
# A plain non-negative decimal with at most the VM's 30 fractional digits.
AMOUNT_TEXT = re.compile(r"[0-9]+(\.[0-9]{1,30})?")
# An account key as signers spend from it: lowercase 64-hex.
ACCOUNT_KEY = re.compile(r"[0-9a-f]{64}")
# A named holder (a contract), as the submission contract allows names.
ACCOUNT_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
# A name made only of hex digits this long is a mangled key, not a contract.
MANGLED_KEY_LENGTH = 32


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate key {key!r} in allocation file")
        payload[key] = value
    return payload


def read_allocation_payload(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
    )


def require_account(account: Any) -> str:
    if not isinstance(account, str) or not (
        ACCOUNT_KEY.fullmatch(account) or ACCOUNT_NAME.fullmatch(account)
    ):
        raise ValueError(
            f"allocation account is not a canonical key or contract name: {account!r}"
        )
    if (
        len(account) >= MANGLED_KEY_LENGTH
        and len(account) != 64
        and all(character in "0123456789abcdef" for character in account)
    ):
        raise ValueError(f"allocation account looks like a truncated key: {account!r}")
    return account


def require_amount(account: str, amount: Any) -> str:
    if not isinstance(amount, str) or not AMOUNT_TEXT.fullmatch(amount):
        raise ValueError(
            f"allocation for {account} must be a plain decimal string with at most "
            f"30 fractional digits: {amount!r}"
        )
    return amount


def _require_header(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    expected = {
        "schema": SCHEMA,
        "schema_version": 1,
        "network": "mainnet",
        "chain_id": CHAIN_ID,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(f"allocation {field} must be {value!r} in {path}")
    currency = payload.get("currency")
    balances = currency.get("balances") if isinstance(currency, dict) else None
    if not isinstance(balances, dict) or not balances:
        raise ValueError(
            f"allocation currency.balances must be a non-empty object in {path}"
        )
    return balances


def load_allocation_balances(path: Path) -> dict[str, str]:
    """The allocation balances by account, as the exact decimal text written."""
    balances = _require_header(read_allocation_payload(path), path)
    normalized = {
        require_account(account): require_amount(account, amount)
        for account, amount in balances.items()
    }
    if allocation_total(normalized) <= 0:
        raise ValueError(f"allocation total supply must be positive in {path}")
    return normalized


def allocation_total(balances: dict[str, str]) -> Decimal:
    return sum((Decimal(amount) for amount in balances.values()), Decimal(0))
