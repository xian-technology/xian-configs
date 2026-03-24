from __future__ import annotations
from pathlib import Path

try:
    from xian_linter import lint_code_inline
except ImportError as exc:  # pragma: no cover - operator guidance path
    raise SystemExit(
        "xian_linter is required; run this script via "
        "`uv run --project ../xian-linter python ./scripts/validate-solution-pack-contracts.py`"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "solution-packs"


def iter_contracts() -> list[Path]:
    return sorted(CONTRACTS_DIR.glob("*/contracts/*.s.py"))


def main() -> int:
    failures = 0
    for path in iter_contracts():
        errors = lint_code_inline(path.read_text(encoding="utf-8"))
        if not errors:
            print(f"ok  {path.relative_to(ROOT)}")
            continue
        failures += 1
        print(f"FAIL {path.relative_to(ROOT)}")
        for error in errors:
            print(f"  - {error}")
    if failures:
        print(f"\n{failures} solution-pack contract file(s) failed linting.")
        return 1
    print(f"\nValidated {len(iter_contracts())} solution-pack contract file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
