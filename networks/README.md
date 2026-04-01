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
