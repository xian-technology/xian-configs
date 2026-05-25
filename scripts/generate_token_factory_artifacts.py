#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from contracting.artifacts import build_contract_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKEN_FACTORY_PATH = REPO_ROOT / "contracts" / "token_factory.s.py"
TOKEN_TEMPLATE_PATH = (
    REPO_ROOT
    / "contract-templates"
    / "token_factory_xsc001_token_template.s.py"
)
CONTRACT_TEMPLATE_PATH = (
    REPO_ROOT / "contract-templates" / "token_factory_contract_template.s.py"
)
TOKEN_TEMPLATE_MODULE = "__TEMPLATE__"
VM_PROFILE = "xian_vm_v1"
GENERATED_START_MARKER = "# GENERATED TOKEN FACTORY ARTIFACTS START"
GENERATED_END_MARKER = "# GENERATED TOKEN FACTORY ARTIFACTS END"
STRING_CHUNK_SIZE = 88
CONTRACT_TEMPLATE_PLACEHOLDER = "{{ GENERATED_TOKEN_ARTIFACTS }}"


def _chunked_python_string(name: str, value: str) -> str:
    chunks = [
        value[index : index + STRING_CHUNK_SIZE]
        for index in range(0, len(value), STRING_CHUNK_SIZE)
    ] or [""]
    lines = [f"{name} = ("]
    lines.extend(f"    {chunk!r}" for chunk in chunks)
    lines.append(")")
    return "\n".join(lines)


def render_generated_block() -> str:
    source = TOKEN_TEMPLATE_PATH.read_text(encoding="utf-8")
    artifacts = build_contract_artifacts(
        module_name=TOKEN_TEMPLATE_MODULE,
        source=source,
        lint=True,
        vm_profile=VM_PROFILE,
    )

    lines = [
        GENERATED_START_MARKER,
        (
            "# Source of truth: "
            "contract-templates/token_factory_xsc001_token_template.s.py. "
            "Regenerate via `uv run --project ../xian-cli python "
            "./scripts/generate_token_factory_artifacts.py --write`."
        ),
        _chunked_python_string("XSC001_TOKEN_SOURCE", artifacts["source"]),
        "",
        _chunked_python_string(
            "XSC001_TOKEN_VM_IR_TEMPLATE", artifacts["vm_ir_json"]
        ),
        "",
        'XSC001_TOKEN_ARTIFACT_FORMAT = "xian_contract_artifact_v1"',
        f'XSC001_TOKEN_VM_PROFILE = "{VM_PROFILE}"',
        f'XSC001_TOKEN_TEMPLATE_MODULE = "{TOKEN_TEMPLATE_MODULE}"',
        (
            "XSC001_TOKEN_SOURCE_SHA256 = "
            f'"{artifacts["hashes"]["source_sha256"]}"'
        ),
        (
            "XSC001_TOKEN_INPUT_SOURCE_SHA256 = "
            f'"{artifacts["hashes"]["input_source_sha256"]}"'
        ),
        GENERATED_END_MARKER,
    ]
    return "\n".join(lines)


def render_token_factory_contract() -> str:
    template = CONTRACT_TEMPLATE_PATH.read_text(encoding="utf-8")
    if CONTRACT_TEMPLATE_PLACEHOLDER not in template:
        raise SystemExit(
            "token factory contract template is missing the generated artifacts placeholder"
        )
    return template.replace(
        CONTRACT_TEMPLATE_PLACEHOLDER,
        render_generated_block(),
    )


def verify_token_factory_artifacts() -> None:
    existing = TOKEN_FACTORY_PATH.read_text(encoding="utf-8")
    updated = render_token_factory_contract()
    if updated != existing:
        diff = "".join(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=str(TOKEN_FACTORY_PATH),
                tofile=str(TOKEN_FACTORY_PATH),
            )
        )
        raise SystemExit(
            "token_factory generated artifacts are stale; run "
            "`uv run --project ../xian-cli python "
            "./scripts/generate_token_factory_artifacts.py --write`\n"
            + diff
        )


def write_token_factory_artifacts() -> None:
    TOKEN_FACTORY_PATH.write_text(
        render_token_factory_contract(),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the token_factory embedded deployment artifacts"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if token_factory.s.py is not up to date",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite token_factory.s.py with the generated artifact block",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        verify_token_factory_artifacts()
        return 0
    if args.write:
        write_token_factory_artifacts()
        return 0
    print("specify --check or --write", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
