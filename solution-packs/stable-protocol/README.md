# Stable Protocol Pack

## Purpose

This pack provides the reusable contract assets and starter metadata for the
Stable Protocol solution pack.

The use case is a governance-owned, multi-contract stable asset protocol with:

- overcollateralized vault issuance
- multi-reporter oracle pricing
- savings-vault fee routing
- liquidation and auction flows
- explicit surplus-buffer and bad-debt accounting
- a peg stability module for reserve-backed mint and redeem

## Recommended Operator Paths

- local development: `single-node-indexed`
- remote deployment: `consortium-3`

These templates match the intended pack posture:

- indexed reads and monitoring for protocol operations
- a realistic shared-network governance environment
- a service-node surface suitable for dashboards, risk views, and automation

## Contents

- `pack.json`: machine-readable starter-flow manifest for `xian-cli`
- `contracts/stable_token.s.py`: stable asset token contract
- `contracts/oracle.s.py`: price oracle contract
- `contracts/savings.s.py`: fee-routing savings vault
- `contracts/vaults.s.py`: vault and liquidation engine
- `contracts/psm.s.py`: peg stability module

## Notes

- This is a solution-pack asset, not a canonical live-network manifest.
- `pack.json` is the canonical machine-readable summary for starter flows.
- The intended deployed contract names in examples are:
  - `stable_token`
  - `oracle`
  - `savings`
  - `vaults`
  - `psm`
- The bootstrap, wiring, and operator scripts live in `xian-stable-protocol/`.
