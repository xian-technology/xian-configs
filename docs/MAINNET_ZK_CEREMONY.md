# Mainnet ZK Ceremony

This note defines the config-side guardrails for mainnet shielded proving
artifacts.

## Current Mainnet Posture

- `networks/mainnet/manifest.json` enables the chain `zk` runtime feature.
- `networks/mainnet/privacy/artifacts.json` starts with no approved proving
  bundles.
- Mainnet accepts only `ceremony-import` setup mode.
- Mainnet rejects single-party setup artifacts.

That combination lets nodes boot with the native verifier available while
preventing any shielded proving bundle from being treated as approved until the
ceremony output is imported and checksum-pinned.

## Ceremony Import Requirements

Before adding an artifact entry to the mainnet catalog, the launch owner must
record:

- circuit family and statement version
- proving/verifying key artifact hash
- ceremony transcript hash or ceremony package hash
- registry manifest path and SHA256
- `zk_registry` registration parameters
- review sign-off for setup mode, circuit limits, and public-input encoding

The catalog entry must point at a committed registry manifest and its SHA256
must match the file on disk.

## Validation

Run:

```bash
uv run --project ../xian-cli python ./scripts/validate-manifests.py
```

For mainnet, validation requires:

- runtime feature `zk: true`
- privacy setup mode exactly `ceremony-import`
- `allow_single_party: false`
- no approved artifacts until ceremony-derived registry manifests are committed

## Finalization Gate

Do not tag the mainnet release while the catalog references draft, local, or
single-party proving material. Either keep `artifacts` empty or commit the
accepted ceremony artifacts and their registry manifest hashes.
