# Network Presets

## Purpose
- This folder contains canonical preset manifests used to build deterministic
  test and development networks.

## Contents
- one directory per supported preset
- manifest data only; genesis is rendered from the preset's contract bundle

## Notes
- Keep preset-owned data here, not in `xian-abci` or `xian-cli`.
- Preset genesis is rendered from the matching contract bundle under
  `contracts/contracts_<preset>.json`.
- Validator policy for active presets is pinned explicitly in those bundles so
  the preset behavior does not depend on hidden contract defaults.
- The canonical `testnet` preset is also the richest real-network fixture: it
  pins published node images and release provenance while still deriving fresh
  deterministic genesis from the current contract bundle.
- Networks can also pin privacy-facing metadata here:
  - `privacy_artifact_catalog`: a checksum-pinned catalog of approved shielded
    registry manifests for that network
  - `shielded_history_policy`: the network's compatibility and retention
    commitment for `shielded_wallet_history`
  - `privacy_submission_policy`: operator-facing policy for relayer auth and
    hidden-sender submission posture

```mermaid
flowchart LR
  Manifest["Network manifest"] --> Genesis["Rendered genesis"]
  Bundle["Preset contract bundle"] --> Genesis
  Manifest --> Seeds["Seed nodes and snapshots"]
  Manifest --> Runtime["Runtime image provenance"]
  Manifest --> Privacy["Privacy-facing metadata"]
  CLI["xian-cli"] --> Manifest
  Deploy["xian-deploy and xian-stack"] --> Manifest
```
