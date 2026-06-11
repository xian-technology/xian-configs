# Contracts

## Purpose
- This folder contains canonical contract sources used by the Xian stack.

## Notes
- Treat these as committed shared fixtures, not ad hoc local experiments.
- Contract changes here affect multiple repos that consume canonical network assets.
- The active genesis bundle set is `contracts_local.json`, `contracts_devnet.json`,
  and `contracts_testnet.json`.
- The `validators` constructor args in those bundles must pin the full shipped
  validator policy surface explicitly rather than relying on contract defaults.
