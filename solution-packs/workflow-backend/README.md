# Workflow Backend Pack

## Purpose

This pack provides the reusable contract asset for the Workflow Backend
solution pack.

The use case is a shared job-style workflow backend where:

- clients submit workflow items
- workers claim them
- workers complete or fail them
- off-chain systems consume events and indexed state/history

## Recommended Operator Paths

- local development: `single-node-indexed`
- remote deployment: `embedded-backend`

These templates match the intended pack posture:

- BDS-enabled reads for current state and history
- a backend-oriented node layout
- straightforward monitoring and recovery for event-driven services

## Contents

- `contracts/job_workflow.s.py`: the reference workflow state-machine contract

## Notes

- This is a solution-pack asset, not a canonical live-network contract.
- The intended deployed contract name in examples is `con_job_workflow`.
- Python integration examples for this pack live in
  `xian-py/examples/workflow_backend/`.
