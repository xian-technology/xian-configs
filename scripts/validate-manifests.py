#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from xian_cli.models import read_network_manifest
except ModuleNotFoundError as exc:
    raise SystemExit(
        "xian-cli must be installed in the current environment; run this "
        "script via `uv run --project ../xian-cli python ./scripts/validate-manifests.py`"
    ) from exc


def main() -> int:
    manifest_paths = sorted((REPO_ROOT / "networks").glob("*/manifest.json"))
    if not manifest_paths:
        raise SystemExit("no canonical manifests found under networks/")

    for manifest_path in manifest_paths:
        read_network_manifest(manifest_path)
        print(f"validated {manifest_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
