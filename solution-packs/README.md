# Solution Packs

## Purpose

This folder contains reusable assets for the reference Xian solution packs.

These assets are intentionally narrower than the canonical network bundles in
`networks/` and the canonical starter templates in `templates/`.

## Contents

- one folder per solution pack
- `pack.json` machine-readable starter-flow manifest in each pack folder
- pack-specific contract assets
- pack-specific README guidance that points to the recommended local and remote
  operator templates

Current packs:

- `credits-ledger/`
- `registry-approval/`
- `workflow-backend/`

## Notes

- Solution packs are not live network manifests.
- Solution packs are built on top of the existing template/operator surface.
- The machine-readable `pack.json` files are the canonical starter-flow source
  for `xian-cli`.
- Public walkthroughs for these packs belong in `xian-docs-web`.
