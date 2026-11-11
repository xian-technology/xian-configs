# Contracts

## Purpose
- This folder contains canonical contract sources used by the Xian stack.

## Notes
- Treat these as committed shared fixtures, not ad hoc local experiments.
- Contract changes here affect multiple repos that consume canonical network assets.
- The active genesis bundle set is `contracts_local.json`, `contracts_devnet.json`,
  `contracts_testnet.json`, and `contracts_mainnet.json`.
- The `validators` constructor args in those bundles must pin the full shipped
  validator policy surface explicitly rather than relying on contract defaults.
- `mainnet_allocations.json` is the source file for mainnet currency genesis
  balances. Run `../scripts/sync-mainnet-allocations.py` after editing it, then
  validate with `../scripts/validate-manifests.py`.

## Wallet and Governance Boundaries

`vault.s.py` requires distinct, nonempty owners and a positive quorum no larger
than the owner count. At least one owner must remain. Transaction execution
counts approvals from current owners, so an approval from a removed owner
cannot satisfy quorum. The canonical network bundles do not deploy this vault
asset.

State-patch votes must complete no later than the patch's activation height.
An approval in that block is available to the block's commit-boundary patch
phase. After that height, members must submit a new proposal with a future
activation height and matching patch bundle.
