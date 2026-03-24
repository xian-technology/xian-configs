# Templates

## Purpose
- This folder contains canonical starter templates for creating purposeful new
  Xian networks and operator node profiles.

## Contents
- one JSON file per template
- network defaults such as runtime backend, block policy, and tracer mode
- bootstrap profile defaults such as service-node, dashboard, and monitoring
  behavior
- operator intent metadata such as `operator_profile` and
  `monitoring_profile`
- creation conveniences such as a default bootstrap validator name

## Notes
- Templates are not live network manifests.
- `xian-cli` consumes these files for `network template ...`,
  `network create --template ...`, and `network join --template ...`.
- `operator_profile` expresses the intended operator posture for the template:
  local development, indexed development, shared network, or embedded backend.
- `monitoring_profile` expresses how the template expects monitoring to work:
  `none`, `local_stack`, or `service_node`.
