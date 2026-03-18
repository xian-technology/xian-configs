# xian-configs

`xian-configs` is the configuration and chain-asset repository for the Xian
workspace. It owns committed network-specific genesis data, contract manifests,
and other chain metadata that should not live inside the universal node runtime.

## Current Scope

The active stack contract now lives in:

- `networks/<name>/manifest.json`
- `networks/<name>/genesis.json`
- `contracts/`

`networks/` is the canonical network-first layout. Each network owns its own
directory, with a colocated `manifest.json` and `genesis.json`. `contracts/`
contains the canonical contract manifests and source files used for local
genesis construction.

The old `legacy/` tree remains only as an extracted archive. Active code paths
should not depend on it.

Canonical manifests now carry an explicit `schema_version`. Validate them from
the shared workspace with:

```bash
uv run --project ../xian-cli python ./scripts/validate-manifests.py
```

## Intended Direction

This repo is expected to grow into the canonical home for:

- chain metadata
- genesis files
- seed node definitions
- snapshot metadata

The canonical network surface is network-first rather than extraction-first.
