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

## Shared Agent Practices
- Keep changes clean, modular, and professional. Prefer small, cohesive modules, clear naming, explicit boundaries, and tests over quick patches.
- When code behavior, public APIs, user workflows, operator workflows, or configuration semantics change, check whether `../xian-docs-web` needs corresponding documentation updates. If this repo is `xian-docs-web`, update the relevant published docs in place. Write durable user/developer documentation, not a changelog entry.
- For code changes, use graphify when available to check cross-repo impact before finishing: query the local `graphify-out/graph.json`, inspect paths with `graphify path` or `graphify explain`, and refresh with `graphify update .` after structural changes when useful.
- If graphify or dependency analysis shows affected sibling repos, update those repos in the same change when the impact is real and the fix is in scope.
- Treat `graphify-out/` as a generated local artifact. Do not commit it.
