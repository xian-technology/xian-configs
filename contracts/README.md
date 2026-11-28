# Contracts

## Purpose
- This folder contains canonical contract sources used by the Xian stack.

## Notes
- Treat these as committed shared fixtures, not ad hoc local experiments.
- Contract changes here affect multiple repos that consume canonical network assets.
- The active genesis bundle set is `contracts_local.json`, `contracts_devnet.json`,
  `contracts_testnet.json`, and `contracts_mainnet.json`.
- Every bundle deploys immutable `time_checkpoints` with protocol version 1.
  Consumers request the current positive VM height before accepting custody,
  then read its immutable successor timestamp. Only the reserved Node keeper
  can mark the service ready or process up to 32 older FIFO requests; the
  service has no callbacks or asset methods. An older runtime that does not
  run this keeper cannot accept requests. Product bundles declare this platform
  dependency instead of deploying their own copy.
- The `validators` constructor args in those bundles must pin the full shipped
  validator policy surface explicitly rather than relying on contract defaults.
- Every bundle deploys `validator_penalties` before `validators`. The coordinator
  owns bounded penalty progress and unbond summary indexes; `validators` retains
  all stake and currency-write authority. Standalone harnesses must deploy both.
- `mainnet_allocations.json` is the source file for mainnet currency genesis
  balances. Run `../scripts/sync-mainnet-allocations.py` after editing it, then
  validate with `../scripts/validate-manifests.py`. Each holder appears once,
  as a lowercase 64-hex account key or a system contract name (a `con_` name
  is refused: its first deployer would own the balance), with its balance as a
  plain decimal string (no sign or exponent, at most 30 fractional digits).
  Anything else is refused, so every balance reaches genesis exactly as
  written; the sync prints the holder count and total supply to check against
  the source ledger.

Native currency transfers reject mixed/uppercase 64-hex account spellings.
`currency.validate_account` also enforces the 511-byte storage-key boundary;
validator reward keys and slash destinations use the same validation before
they can affect payouts.
Account keys exclude the VM's reserved `:` and `.` storage separators. Default
currency genesis uses the same account validation for the founder allocation.
Allocations to a shared account are added together.
The foundation uses that account validation for its withdrawal owner.
`change_owner` nominates a successor. The current owner can cancel until the
nominee calls `accept_ownership`. Chi conversion rates must be positive integers no larger
than `10**61 - 1` at both initialization and governance updates.

## Wallet and Governance Boundaries

`vault.s.py` requires distinct owners with valid currency accounts and a
positive integer quorum no larger than the owner count. At least one owner
must remain. A quorum-approved `addOwner` creates an invitation. Only the
invitee can accept it, and a quorum can revoke it with `removeOwner`.
Transaction execution counts approvals from current owners. The
canonical network bundles omit this optional vault asset.

State-patch votes must complete no later than the patch's activation height.
An approval in that block is available to the block's commit-boundary patch
phase. After that height, members must submit a new proposal with a future
activation height and matching patch bundle.

## Validator and account keys

A fresh network may supply `genesis_consensus_keys` to the `validators`
constructor. Supply exactly one lowercase 3,904-character ML-DSA-65 public key
per genesis member, indexed by the unchanged 64-hex account handle. The node
must use the same consensus suite and signing keys in CometBFT genesis. The
canonical local and draft mainnet recipes omit this option.

In that configuration, a new operator calls `validators.register` directly
from its account with `consensus_public_key` and `consensus_proof`. The latter
is a lowercase hex encoding of a 3,309-byte, pure ML-DSA-65 signature with an
empty FIPS 204 context. Join the following UTF-8 lines with LF and omit the
trailing LF.

```text
xian-validator-key-v1
<chain_id>
<operator_account>
<lowercase_consensus_public_key_hex>
```

The operator proves possession once. Re-registration of the same account uses
the original key and omits both arguments. To replace an operator or its
consensus key, admit a new member under a distinct binding and remove the old
member using the normal validator selection rules. Historical evidence and
rewards keep their original account mapping. Only `validators` records bindings.
Generate and back up account, recovery and consensus signing keys separately.

With a native hybrid account record, the currency permit callback rejects
third-party approvals for that owner. The strict version 2 account policy
disables this callback for all owners. The owner's ordinary `approve` and the
spender's use of existing allowances follow the usual transaction authorization.
Selecting a future strict genesis for imported user balances requires explicit
custody records for their existing handles. The allocation ledger contains
no such records.
