# Templates

## Purpose
- This folder contains canonical starter templates for creating purposeful new
  Xian networks and operator node profiles.

## Contents
- one JSON file per template
- network defaults such as runtime backend, block policy, and tracer mode
- bootstrap profile defaults such as service-node, dashboard, and monitoring
  behavior
- creation conveniences such as a default bootstrap validator name

## Notes
- Templates are not live network manifests.
- `xian-cli` consumes these files for `network template ...`,
  `network create --template ...`, and `network join --template ...`.
