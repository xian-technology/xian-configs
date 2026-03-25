# Registry / Approval Pack

## Purpose

This pack provides the reusable contract assets for the Registry / Approval
solution pack.

The use case is a shared registry where records must be proposed and approved
before they become active or revoked.

## Recommended Operator Paths

- local development: `single-node-indexed`
- remote deployment: `consortium-3`

These templates match the intended pack posture:

- indexed reads for records and proposal history
- a realistic operator path for shared multi-party state
- monitoring and recovery surfaces suitable for approval workflows

## Contents

- `pack.json`: machine-readable starter-flow manifest for `xian-cli`
- `contracts/registry_records.s.py`: stores the approved registry state
- `contracts/registry_approval.s.py`: manages signers, proposals, approvals,
  and execution into the registry contract

## Notes

- This is a solution-pack asset, not a canonical live-network contract.
- `pack.json` is the canonical machine-readable summary for starter flows.
- The intended deployed contract names in examples are:
  - `con_registry_records`
  - `con_registry_approval`
- Python integration examples for this pack live in
  `xian-py/examples/registry_approval/`.
