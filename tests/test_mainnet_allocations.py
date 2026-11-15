"""The mainnet allocation file is the only input of the migrated balances.

Every entry must reach genesis exactly as written, or the sync must refuse it.
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).absolute().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sync_mainnet_allocations", ROOT / "scripts" / "sync-mainnet-allocations.py"
)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)

KEY = "ab" * 32
HEADER = (
    '{"schema": "xian.mainnet_allocations.v1", "schema_version": 1, '
    '"network": "mainnet", "chain_id": "xian-mainnet-1", '
)


def _write(tmp_path: Path, balances_json: str) -> Path:
    path = tmp_path / "mainnet_allocations.json"
    path.write_text(HEADER + '"currency": {"balances": ' + balances_json + "}}")
    return path


def test_exact_decimal_strings_are_kept_digit_for_digit(tmp_path):
    amount = "123456789012345678901234567890.123456789012345678901234567890"
    path = _write(
        tmp_path, json.dumps({KEY: amount, "dao": "0.000000000000000000000000000001"})
    )

    assert sync.load_allocation_balances(path) == {
        KEY: amount,
        "dao": "0.000000000000000000000000000001",
    }


@pytest.mark.parametrize(
    "balances_json",
    (
        # The same holder twice: json.loads would silently keep the last entry.
        f'{{"{KEY}": "1", "{KEY}": "2"}}',
        # A JSON number is parsed as a float and rounded before it is checked.
        f'{{"{KEY}": 12345678901234567.123456789}}',
        # The VM keeps 30 fractional digits; genesis would refuse this later.
        f'{{"{KEY}": "1.0000000000000000000000000000001"}}',
        f'{{"{KEY}": "-1"}}',
        f'{{"{KEY}": "1e6"}}',
        f'{{"{KEY}": " 5"}}',
        # Keys only spend from their canonical lowercase spelling.
        f'{{"{KEY.upper()}": "1"}}',
        f'{{"0x{KEY}": "1"}}',
        f'{{"{KEY[:-1]}": "1"}}',
        f'{{"{KEY[:32]}": "1"}}',
        '{"": "1"}',
        # Not deployed at genesis: whoever first submits con_pairs owns it.
        '{"con_pairs": "1"}',
    ),
    ids=(
        "duplicate-holder",
        "json-number",
        "31-fractional-digits",
        "negative",
        "exponent",
        "whitespace",
        "uppercase-key",
        "0x-key",
        "short-key",
        "half-key",
        "empty-account",
        "undeployed-user-contract",
    ),
)
def test_entries_that_would_not_reach_genesis_exactly_are_refused(
    tmp_path, balances_json
):
    path = _write(tmp_path, balances_json)

    with pytest.raises(ValueError):
        sync.load_allocation_balances(path)


@pytest.mark.parametrize(
    "replace",
    (
        ('"chain_id": "xian-mainnet-1"', '"chain_id": "xian-mainnet-2"'),
        (
            f'"currency": {{"balances": {{"{KEY}": "1"}}}}',
            '"currency": {"balances": {}}',
        ),
        (
            f'"currency": {{"balances": {{"{KEY}": "1"}}}}',
            f'"currency": {{"balances": ["{KEY}"]}}',
        ),
        (f'"{KEY}": "1"', f'"{KEY}": "0"'),
    ),
    ids=("other-chain", "no-holders", "holder-list", "zero-supply"),
)
def test_a_file_for_another_chain_or_without_supply_is_refused(tmp_path, replace):
    path = _write(tmp_path, json.dumps({KEY: "1"}))
    path.write_text(path.read_text().replace(*replace))

    with pytest.raises(ValueError):
        sync.load_allocation_balances(path)


def test_a_single_holder_of_one_token_is_a_valid_allocation(tmp_path):
    path = _write(tmp_path, json.dumps({KEY: "1"}))

    assert sync.load_allocation_balances(path) == {KEY: "1"}


def test_the_bundle_receives_the_allocation_text_unchanged():
    bundle = json.loads((ROOT / "contracts" / "contracts_mainnet.json").read_text())
    balances = {KEY: "0.100000000000000000000000000000", "dao": "7"}

    expected = sync.expected_bundle_payload(bundle, balances)

    assert (
        sync.currency_contract(expected)["constructor_args"]["initial_balances"]
        == balances
    )
