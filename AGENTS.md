# Repository Guidelines

## Scope
- `xian-configs` owns chain-specific configuration assets for the Xian stack.
- Keep committed genesis files, contract manifests, seed metadata, and future
  snapshot metadata here instead of in `xian-abci`.
- Do not add runtime logic, CLI behavior, or Docker orchestration to this repo.

## Project Layout
- `legacy/genesis/`: extracted legacy genesis bundle from `xian-abci`
- `legacy/genesis/contracts/`: contract manifests and source files used by the
  legacy genesis bundle
- `networks/`: canonical network manifests consumed by `xian-cli`

## Workflow
- Preserve compatibility first when moving assets here. Normalize structure only
  after the consuming repos are already reading from this repo.
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
