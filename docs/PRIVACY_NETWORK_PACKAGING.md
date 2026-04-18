# Privacy Network Packaging

This note defines the config-repo side of the current privacy artifact
packaging surface.

## Goal

When a network enables shielded assets, operators need one canonical place to
find:

- approved registry manifests
- the network's retention and compatibility commitment for
  `shielded_wallet_history`
- the relayer/disclosure posture the network expects operators to follow

That packaging belongs in `xian-configs`, not in ad hoc deployment notes.

## Network Manifest Fields

Canonical network manifests can now expose:

- `privacy_artifact_catalog`
  - checksum-pinned pointer to the catalog file under that network directory
- `shielded_history_policy`
  - the current feed version
  - the compatibility commitment (`best_effort` or `versioned`)
  - the retention class (`operator_defined` or `archive`)
  - whether BDS snapshot support is part of the expected operator path
- `privacy_submission_policy`
  - the disclosure posture
  - whether shared relayers require auth
  - the expected hidden-sender submission mode

## Artifact Catalog

Each canonical network now has:

```text
networks/<name>/privacy/artifacts.json
```

That catalog is the approved home for shielded registry manifests.

Current behavior:

- the catalogs are present for `local`, `devnet`, and `testnet`
- they currently carry policy and bundle-admission posture
- they do not yet publish approved shielded registry manifests by default

This is intentional. The packaging surface now exists even though no canonical
public-network privacy artifacts are approved yet.

## Bundle Policy

The catalog also pins the bundle-admission posture for that network:

- `approved_setup_modes`
- `allow_single_party`

That keeps the "what kinds of proving material are acceptable here?" decision
inside the canonical network config instead of burying it in release notes.

## Validation

`scripts/validate-manifests.py` now enforces that:

- every canonical network manifest has a `privacy_artifact_catalog`
- the referenced catalog file exists
- the catalog SHA256 matches the manifest
- catalog schema and bundle-policy fields are valid
- any future artifact entries point at existing registry manifests with matching
  SHA256 values

## What This Does Not Do

This packaging surface does not itself approve any public privacy deployment.
It provides the canonical place and validation rules for that approval to live
later.
