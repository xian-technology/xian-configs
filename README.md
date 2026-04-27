# xian-configs

`xian-configs` is the canonical repository for Xian network definitions and
committed chain assets. It hosts network manifests, genesis files, reusable
starter templates, installable on-chain modules, and complete reference
solutions. Other repos (`xian-cli`, `xian-stack`, `xian-deploy`) read from
this repo as the source of truth for "which networks exist" and "what
contracts are part of them".

This repo is network-first and asset-centric. It does not contain node
runtime behavior, image build definitions, or operator command surfaces.

## Quick Start

Use this repo to:

- define or review a network manifest under `networks/`
- maintain committed contract assets under `contracts/`
- maintain reusable starter templates under `templates/`
- publish reusable installable modules under `modules/`
- publish complete application / operator solutions under `solutions/`

Inspect the canonical templates from `xian-cli`:

```bash
uv run --project ../xian-cli xian network template list
uv run --project ../xian-cli xian network template show single-node-indexed
```

Validate manifests and contract assets locally:

```bash
uv run --project ../xian-cli    python ./scripts/validate-manifests.py
uv run --project ../xian-linter python ./scripts/validate-solution-contracts.py
```

## Asset Model

`xian-configs` is intentionally data-heavy. It describes the assets that
other repos consume; it does not run nodes or build images itself.

| Asset type | Location | What it answers | Primary consumers |
| --- | --- | --- | --- |
| Network manifest | `networks/<name>/manifest.json` | Which chain exists, what its chain ID is, where genesis / snapshots / seed nodes / runtime settings come from | `xian-cli`, `xian-deploy`, `xian-stack` |
| Genesis and built-ins | `contracts/`, network assets | Which contracts are part of canonical committed chain state | `xian-abci`, `xian-cli` |
| Network template | `templates/*.json` | How to create a new local or operator-managed profile with sensible defaults | `xian-cli network create/join` |
| Module | `modules/<name>/module.json` plus bundles | Which reusable protocol package can be installed onto an existing network | `xian-cli module ...`, localnet harnesses |
| Solution | `solutions/<name>/solution.json` | Which templates, modules, services, docs, and examples form a complete app starter | `xian-cli solution ...`, docs |

The usual flow is:

```text
xian-configs asset
  -> xian-cli resolves and validates it
  -> xian-stack or xian-deploy performs the runtime work
  -> xian-py / xian-js apps interact with the resulting chain
```

For example, a local DEX demo starts from committed config data:

```bash
uv run --project ../xian-cli xian module show dex
uv run --project ../xian-cli xian module validate dex
uv run --project ../xian-cli xian solution starter dex-demo --flow local
```

When adding a new module or solution, keep the source of truth close to the
owning repo:

- the owning product repo keeps canonical source and package tests
- this repo keeps the installable, hash-pinned manifest used by networks
- `xian-cli` validates and installs that manifest
- `xian-docs-web` documents the user-facing workflow

## Principles

- **Network-first.** This repo describes networks and committed chain
  assets, not node runtime behavior or image builds.
- **Templates are not live networks.** Reusable starter templates and
  installable modules live separate from the manifests of real networks.
- **Committed assets only when canonical.** Contract assets belong here when
  they are part of a canonical network, a reusable module, or a solution.
  General runtime code lives in the runtime repos.
- **Explicit manifests, no implicit setup.** Anything a network depends on
  should be visible in a committed manifest, not inferred at deploy time.

## Key Directories

- `networks/` — manifests and genesis files for canonical networks
  (`devnet/`, `testnet/`, `local/`).
- `contracts/` — canonical contract manifests and source assets referenced by
  the networks above.
- `templates/` — reusable starter templates for creating purposeful Xian
  networks (`single-node-dev`, `single-node-indexed`, `consortium-3`,
  `consortium-5`, `embedded-backend`, plus token-factory contract
  templates).
- `modules/` — reusable on-chain protocol or contract modules
  (`dex/`, `stable-protocol/`).
- `solutions/` — complete app / operator patterns that compose templates,
  modules, services, examples, and docs (`credits-ledger`, `dex-demo`,
  `registry-approval`, `workflow-backend`).
- `scripts/` — validation helpers for manifests, modules, and solutions.
- `docs/` — repo-local architecture, backlog, and packaging notes.

## Main Consumers

- `xian-cli` — network creation, joining, module install, and solution
  starter flows
- `xian-stack` — runtime images and local Compose-based operation
- `xian-deploy` — remote host deployment

## Validation

```bash
uv run --project ../xian-cli    python ./scripts/validate-manifests.py
uv run --project ../xian-linter python ./scripts/validate-solution-contracts.py
```

The first script validates manifest schemas and cross-references. The second
runs the contracting linter against committed contract assets.

## Related Docs

- [AGENTS.md](AGENTS.md) — repo-specific guidance for AI agents and contributors
- [docs/README.md](docs/README.md) — index of internal docs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — major components and dependency direction
- [docs/BACKLOG.md](docs/BACKLOG.md) — open work and follow-ups
- [docs/PRIVACY_NETWORK_PACKAGING.md](docs/PRIVACY_NETWORK_PACKAGING.md) — packaging conventions for privacy-enabled networks
- [docs/VALIDATOR_DELEGATION.md](docs/VALIDATOR_DELEGATION.md) — validator delegation manifest model
