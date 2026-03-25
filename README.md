# xian-configs

`xian-configs` is the canonical repository for Xian network definitions and
chain assets. Use it when you need to define a network, version a genesis or
manifest, or keep committed contract assets outside the runtime repos.

## Common Workflows

Use this repo to:

- define or review a network manifest under `networks/`
- keep committed contract assets under `contracts/`
- maintain reusable starter templates under `templates/`
- keep solution-pack-specific assets under `solution-packs/`

Inspect the canonical templates from `xian-cli`:

```bash
uv run --project ../xian-cli xian network template list
uv run --project ../xian-cli xian network template show single-node-indexed
```

The main consumer repos are:

- `xian-cli` for network creation and local operator commands
- `xian-stack` for runtime images and local Compose-based operation
- `xian-deploy` for remote host deployment

## Principles

- Keep this repo network-first. It should describe networks and committed chain
  assets, not node runtime behavior.
- Keep reusable templates separate from live network manifests.
- Keep contract assets here when they are part of a canonical network or a
  reusable solution pack, not when they are general runtime code.
- Prefer explicit, committed manifests over implicit setup logic.

## Key Directories

- `networks/`: network-first manifests and colocated genesis files
- `contracts/`: canonical contract manifests and source assets used by those
  networks
- `templates/`: reusable starter templates for creating purposeful Xian
  networks
- `solution-packs/`: pack-specific assets that build on top of the network and
  template layer
- `scripts/`: validation helpers for manifests and solution-pack assets
- `docs/`: repo-local architecture and backlog notes

## Validation

```bash
uv run --project ../xian-cli python ./scripts/validate-manifests.py
uv run --project ../xian-linter python ./scripts/validate-solution-pack-contracts.py
```

## Related Docs

- [AGENTS.md](AGENTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/BACKLOG.md](docs/BACKLOG.md)
- [docs/README.md](docs/README.md)
