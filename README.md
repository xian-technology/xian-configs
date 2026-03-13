# xian-configs

`xian-configs` is the configuration and chain-asset repository for the Xian
workspace. It owns committed network-specific genesis data, contract manifests,
and other chain metadata that should not live inside the universal node runtime.

## Current Scope

This initial version contains the legacy bundle extracted from `xian-abci`:

- exported genesis fixtures under `legacy/genesis/`
- contract manifests under `legacy/genesis/contracts/`
- contract source files used to build those fixtures

The extraction preserves the old filenames on purpose so the workspace can move
to this repo without changing behavior at the same time.

## Intended Direction

This repo is expected to grow into the canonical home for:

- chain metadata
- genesis files
- seed node definitions
- snapshot metadata

The current `legacy/` layout is transitional. A later cleanup can normalize the
structure by network once the consumers are stable.
