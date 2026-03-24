# xian-configs

`xian-configs` is the configuration and chain-asset repository for the Xian
workspace. It owns committed network-specific manifests, genesis data, contract
bundles, and other chain metadata that should not live inside the universal
runtime repos.

## Scope

This repo owns:

- canonical network manifests and genesis files
- committed contract assets used for local and canonical network setup
- network-specific metadata such as seeds and snapshot references

This repo does not own:

- deterministic node logic
- operator workflow commands
- Docker or Compose runtime behavior

## Key Directories

- `networks/`: network-first manifests and colocated genesis files
- `contracts/`: canonical contract manifests and source assets
- `scripts/`: config validation helpers
- `docs/`: repo-local notes and structure guidance

## Validation

```bash
uv run --project ../xian-cli python ./scripts/validate-manifests.py
```

## Related Docs

- [AGENTS.md](AGENTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/BACKLOG.md](docs/BACKLOG.md)
- [docs/README.md](docs/README.md)

## Current Layout

The active stack contract now lives in:

- `networks/<name>/manifest.json`
- `networks/<name>/genesis.json`
- `contracts/`
- `templates/<name>.json`

The old `legacy/` tree remains only as an extracted archive. Active code paths
should not depend on it.

`templates/` now contains canonical starter templates for creating purposeful
new Xian networks. These are not live-network manifests; they are reusable
defaults consumed by `xian-cli` when creating or joining operator-managed
networks. Each template now also declares:

- `operator_profile`: the intended operator posture for the network shape
- `monitoring_profile`: how monitoring defaults should behave for that shape

## Intended Direction

This repo is expected to grow into the canonical home for:

- chain metadata
- genesis files
- seed node definitions
- snapshot metadata
- canonical network templates

The canonical network surface is network-first rather than extraction-first.
