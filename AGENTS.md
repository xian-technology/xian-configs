# Repository Guidelines

## Shared Convention
- Follow the shared repo convention in `xian-meta/docs/REPO_CONVENTIONS.md`.
- Keep this repo aligned with that standard for root docs, backlog placement, and folder-level `README.md` files at major boundaries.
- Follow the shared change workflow in `xian-meta/docs/CHANGE_WORKFLOW.md`.
- Before push, review whether `xian-docs-web` needs updates and run the local validation path that applies to this repo.

## Scope
- `xian-configs` owns chain-specific configuration assets for the Xian stack.
- Keep canonical network manifests, contract manifests, seed metadata, and
  future snapshot metadata here instead of in runtime repos.
- Do not add runtime logic, CLI behavior, or Docker orchestration to this repo.

## Project Layout
- `networks/<name>/manifest.json`: canonical network manifest consumed by
  `xian-cli`
- `contracts/`: canonical contract manifests and source files used to build
  deterministic genesis state

## Workflow
- Prefer network-first structure for canonical data.
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

## Local Knowledge Graph
- If `graphify-out/graph.json` exists, prefer `graphify query`, `graphify path`, or `graphify explain` for broad architecture and impact questions before scanning files manually.
- Treat `graphify-out/` as a generated local artifact; it is intentionally ignored by Git.
- After structural changes, refresh the local graph with `graphify update .` when useful.
