# DEX Pack

## Purpose

This pack pins the Xian DEX contract bundle for reproducible localnet and
operator bootstrap flows.

## Contents

- `contract-bundle.json`: hash-pinned deployment bundle
- `contracts/`: vendored DEX contract snapshot used by the bundle
- `pack.json`: starter-flow metadata surfaced by `xian-cli solution-pack`

## Notes

- Active DEX development belongs in `xian-dex`.
- This solution pack is a pinned snapshot for repeatable network setup.
- Use `xian-stack`'s `localnet-dex-bootstrap` path to deploy this bundle to a
  running local or remote node.
- Override the bundle path only for development or release-candidate testing.
