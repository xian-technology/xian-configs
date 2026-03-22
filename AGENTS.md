# Repository Guidelines

## Shared Convention
- Follow the shared repo convention in `xian-meta/docs/REPO_CONVENTIONS.md`.
- Keep this repo aligned with that standard for root docs, backlog placement, and folder-level `README.md` files at major boundaries.

## Scope
- `xian-configs` owns chain-specific configuration assets for the Xian stack.
- Keep committed genesis files, contract manifests, seed metadata, and future
  snapshot metadata here instead of in `xian-abci`.
- Do not add runtime logic, CLI behavior, or Docker orchestration to this repo.

## Project Layout
- `networks/<name>/manifest.json`: canonical per-network manifest consumed by
  `xian-cli`
- `networks/<name>/genesis.json`: canonical genesis file colocated with the
  network manifest
- `contracts/`: canonical contract manifests and source files used to build
  network genesis state
- `legacy/`: archival extracted content only; do not add new active assets here

## Workflow
- Prefer network-first structure for canonical data. Treat `legacy/` as archive
  material, not an active input path.
- Prefer explicit, descriptive filenames. Avoid embedding operator workflows in
  this repo.
- Keep GitHub references under `xian-technology`.

## Validation
- Validate moved assets with the consuming repos:
  - `xian-abci`: `./scripts/validate-repo.sh`
  - `xian-stack`: `make validate` and `make smoke`

## Notes
- This repo is data-first. Expect docs and structure changes more often than
  executable code changes.
