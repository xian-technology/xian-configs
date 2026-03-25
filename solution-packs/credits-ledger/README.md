# Credits Ledger Pack

## Purpose

This pack provides the reusable contract asset for the Credits Ledger Pack.

The use case is an application-controlled internal credits ledger with:

- issuance
- transfers
- burns
- operator and issuer controls
- event history suitable for workers and indexed reads

## Recommended Operator Paths

- local development: `single-node-indexed`
- remote deployment: `embedded-backend`

These templates already match the intended pack posture:

- BDS-enabled reads
- dashboard and health visibility
- straightforward backend integration

## Contents

- `pack.json`: machine-readable starter-flow manifest for `xian-cli`
- `contracts/credits_ledger.s.py`: the reference credits-ledger contract

## Notes

- This is a solution-pack asset, not a canonical live-network contract.
- `pack.json` is the canonical machine-readable summary for starter flows.
- The intended deployed contract name in examples is `con_credits_ledger`.
- Python integration examples for this pack live in `xian-py/examples/credits_ledger/`.
