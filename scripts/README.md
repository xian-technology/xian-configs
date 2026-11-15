# Scripts

## Purpose
- This folder contains validation helpers for `xian-configs`.

## Notes
- These scripts should validate committed assets, not grow into a second runtime layer.
- `validate-manifests.py` checks canonical network templates, manifests,
  generated system assets, and contract bundles.
- `sync-mainnet-allocations.py` copies the accepted mainnet allocation source
  from `contracts/mainnet_allocations.json` into the mainnet contract bundle.
  `mainnet_allocations.py` parses that file for both scripts and refuses any
  entry that would not reach genesis exactly as written.
