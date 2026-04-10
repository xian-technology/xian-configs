# Validator Delegation And Reward Distribution

## Purpose

This note defines the target validator policy model for Xian and the rollout
path from the current manual `masternodes` governance flow to configurable
validator selection with on-chain delegation and reward splitting.

The canonical contract source remains
`xian-configs/contracts/members.s.py`, submitted into genesis as
`masternodes`.

## Current State

- Validator membership is governed manually through `masternodes`.
- The active validator set is the on-chain list `masternodes.nodes`.
- ABCI reads `masternodes.nodes` and optional
  `masternodes.validator_power:<vk>` to build CometBFT validator updates.
- Validator rewards are distributed off-chain in ABCI and currently pay the
  validator reward key directly, optionally weighted by `validator_power`.
- Generic staking contracts exist in `xian-contracts`, but they are not the
  consensus validator registry and they do not model validator delegation.

## Goals

- Keep `currency` as the staking token without embedding validator logic into
  the token contract.
- Preserve backwards compatibility with the current `masternodes.nodes` and
  `masternodes.validator_power` outputs consumed by ABCI.
- Add first-class validator delegation and reward splitting between operator
  and delegators.
- Make validator selection policy configurable per network.
- Support a safe rollout where reward splitting can ship before automatic
  validator-set selection.

## Non-Goals In The First Slice

- Evidence-driven slashing triggers.
- Jailing with evidence integration.
- Stake-weighted CometBFT voting power.
- Per-block validator-set churn.
- High-scale reward indexing for thousands of delegators.

## Operating Modes

The validator policy contract must support the following modes:

- `manual`
  Active validators are changed through governance votes.
- `auto_top_n`
  Active validators are the top `N` eligible validators by total bonded stake.
- `hybrid`
  Governance controls validator eligibility and the active set is chosen as the
  top `N` among approved and eligible validators.

The recommended default for future public networks is `hybrid`.

## Canonical Configuration

The contract must expose on-chain configuration for:

- `selection_mode`
- `max_validators`
- `power_mode`
- `rebalance_interval`
- `activation_delay_epochs`
- `unbonding_period_days`
- `min_self_bond`
- `min_total_bond`
- `max_commission_bps`
- `max_active_set_churn`
- `min_bond_margin_bps`
- `manual_override_enabled`
- `slash_destination`
- `duplicate_vote_slash_bps`
- `duplicate_vote_jail`
- `light_client_attack_slash_bps`
- `light_client_attack_jail`

Recommended defaults:

- `selection_mode = "manual"` during rollout
- `max_validators = 5`
- `power_mode = "equal"`
- `rebalance_interval` measured in epochs, not blocks
- `manual_override_enabled = True`
- `slash_destination = "dao"` until a burn or community-pool path is introduced
- `duplicate_vote_slash_bps = 500`
- `duplicate_vote_jail = True`
- `light_client_attack_slash_bps = 1000`
- `light_client_attack_jail = True`

Implementation note for the current contract:

- until a dedicated epoch driver exists, selection epochs are derived from
  `block_num // rebalance_interval`
- active preset bundles under `xian-configs/contracts/contracts_<preset>.json`
  should pin every shipped validator policy field explicitly at genesis
- public `rebalance()` is limited to once per derived epoch
- governance-triggered policy changes and hybrid approvals may force a
  same-epoch rebalance

Implementation note for the current ABCI runtime:

- `finalize_block` now runs the epoch rebalance automatically when
  `selection_mode != "manual"` and the current derived epoch has not yet been
  processed
- the automatic rebalance runs before static rewards and validator updates are
  computed for the block
- its result is included in the block fingerprint so an otherwise empty block
  still changes app hash when validator state changes
- `finalize_block` also consumes CometBFT `misbehavior` entries and routes them
  through an internal `masternodes.apply_evidence_penalty(...)` call before
  rewards and validator updates are computed

## Validator State Model

The `masternodes` contract remains the source of truth for:

- active validators
- candidate validators
- validator metadata
- requested validator power
- effective validator power
- operator reward key
- validator commission
- self bond
- delegations
- total bonded stake
- pending unbonds
- selection policy config

Required state keys:

- `nodes -> list[str]`
- `candidates -> list[str]`
- `validator_registry -> list[str]`
- `statuses[validator] -> str`
- `validator_power[validator] -> int`
- `requested_power[validator] -> int`
- `reward_keys[validator] -> str`
- `commission_bps[validator] -> int`
- `registration_bonds[validator] -> decimal`
- `self_bond[validator] -> decimal`
- `total_delegated[validator] -> decimal`
- `delegations[delegator, validator] -> decimal`
- `delegator_reward_keys[delegator, validator] -> str | None`
- `delegator_lists[validator] -> list[str]`
- `pending_unbond_counter -> int`
- `pending_unbond_owner_ids[owner] -> list[int]`
- `pending_unbond_validator_ids[validator] -> list[int]`
- `pending_unbonds[id] -> dict`
- `jailed[validator] -> bool`
- `jail_reasons[validator] -> str | None`
- `total_slashed[validator] -> decimal`
- `last_slashed_at[validator] -> datetime | None`
- `processed_evidence[evidence_id] -> bool`
- `config[<name>] -> value`

`holdings` in the existing contract represents the registration bond and should
remain distinct from validator self-bond used for delegation math.

## Validator Lifecycle

### Registration

`register(...)` creates a validator candidate entry and locks the registration
bond. Registration does not make a validator active by itself.

Validators provide:

- validator account key
- operator reward key
- requested validator power
- moniker
- network endpoint
- metadata URI
- commission rate in basis points

### Activation

- `manual`: activation happens through governance.
- `auto_top_n`: activation happens through epoch rebalance when the validator is
  eligible and ranked in the top `N`.
- `hybrid`: governance approves eligibility, epoch rebalance chooses top `N`.

### Leaving

Validators announce leave first, then leave after the configured delay. Leaving
removes the validator from the active set, zeroes active voting power, refunds
the registration bond, and starts release of self-bond and delegations through
the unbonding flow.

### Removal

Governance can remove a validator. Removal ejects the validator from the active
set and starts the same bonded-funds exit path, unless a later slashing design
changes that behavior.

### Jailing

Jailing is a non-destructive emergency deactivation. It differs from removal:

- no registration bond refund
- no forced unbond sweep
- validator is excluded from selection and active membership
- validator stops accepting new self-bond and delegation

The current contract uses governance-controlled `jail_member` and
`unjail_member` actions. In `manual` mode, unjailing returns the validator to
an approved candidate state and a later `add_member` vote reactivates it. In
automatic modes, unjailing is followed by a forced rebalance so the validator
can re-enter the active set if it is otherwise eligible.

### Slashing

Slashing is a financial penalty on bonded stake. In the current contract it is
governance controlled through `slash_member`.

The vote argument shape is:

- `member`
- `slash_bps`
- optional `reason`
- optional `infraction_height`

Current semantics:

- `slash_bps` is an integer basis-point rate in `(0, 10000]`
- slashable stake always includes live stake:
  `self_bond + total_delegated`
- if `infraction_height` is provided, slashable stake also includes unclaimed
  pending unbonds for the same validator whose `created_block` is greater than
  or equal to that infraction height
- registration bonds are not slashable
- slash application is pro-rata across all slashable stake in scope for that
  call
- the slashed amount is transferred to `config["slash_destination"]`

Because the current `currency` contract has no native burn entrypoint, the
default slash destination is `dao`. Networks can override this destination
through policy config if they want slashed value to flow somewhere else.

If automatic selection is enabled, an approved slash forces a same-epoch
rebalance so stake-based eligibility and ranking update immediately.

Observability:

- `validator_record` exposes `total_slashed` and `last_slashed_at`
- the approved governance vote stores the computed slash execution result,
  including the exact `slash_amount`

### Evidence-Driven Penalties

ABCI can now turn CometBFT `FinalizeBlock.misbehavior` entries into internal
penalty calls.

Current supported evidence types:

- `DUPLICATE_VOTE`
- `LIGHT_CLIENT_ATTACK`

Current runtime flow:

1. `finalize_block` receives `misbehavior` entries from CometBFT.
2. ABCI resolves the misbehaving validator by matching the CometBFT validator
   address against the persistent validator registry, not only the current
   active set.
3. ABCI computes a deterministic `evidence_id` and calls
   `masternodes.apply_evidence_penalty(...)` as an internal system sender.
4. The contract deduplicates repeated evidence with `processed_evidence`.
5. The configured slash and jail policy is applied. Evidence slashing uses the
   delivered `evidence_height`, so only pending unbonds created after that
   infraction remain slashable.
6. In automatic modes, the validator set is rebalanced immediately if the
   penalty changed selection state.

Current policy controls:

- `duplicate_vote_slash_bps`
- `duplicate_vote_jail`
- `light_client_attack_slash_bps`
- `light_client_attack_jail`

The current defaults are intentionally conservative placeholders, not final
governance recommendations.

### Candidate Withdrawal

`unregister()` uses the same bonded-funds exit path for pending or approved
validators. This ensures stake cannot remain attached to a withdrawn validator
record.

### Forced Exit Sweep

The contract must treat validator exits as a full bonding-state unwind:

- operator self-bond becomes a pending unbond owned by the validator operator
- every live delegation becomes a pending unbond owned by the delegator
- `self_bond`, `total_delegated`, and `delegations[* , validator]` are zeroed
- `delegator_lists[validator]` is cleared
- the validator stops accepting new delegation immediately

Pending unbonds created by these exit paths should carry a reason field so
clients can distinguish normal undelegation from forced validator exit. The
current contract uses:

- `reason = "left"`
- `reason = "removed"`
- `reason = "withdrawn"`

## Delegator Lifecycle

### Delegate

`delegate(validator, amount, reward_key=None)` transfers `currency` into the
membership contract and increases `delegations[delegator, validator]`.

If this is the first delegation for the `(delegator, validator)` pair, the
delegator is added to `delegator_lists[validator]`.

### Undelegate

`undelegate(validator, amount)` decreases the live delegation and creates a
pending unbond record with an unlock time.

### Claim Unbond

`claim_unbond(unbond_id)` releases funds after the unbonding period.

Because forced validator exits can create pending unbonds for third parties,
the contract must expose an owner-indexed lookup so delegators can discover the
new unbond ids without relying on an event stream.

## Reward Distribution

ABCI remains responsible for applying balance deltas, but the split is derived
from `masternodes` state.

For each validator reward allotment `R`:

1. Read operator commission rate `commission_bps`.
2. Compute `commission = R * commission_bps / 10000`.
3. Compute `remainder = R - commission`.
4. Compute `stake_base = self_bond + total_delegated`.
5. If `stake_base <= 0`, send all of `R` to the operator reward key.
6. Otherwise:
   - operator stake share = `remainder * self_bond / stake_base`
   - delegator share for delegator `d` =
     `remainder * delegation[d, validator] / stake_base`
   - operator total = `commission + operator stake share`

Payout targets:

- operator -> `reward_keys[validator]`
- delegator -> `delegator_reward_keys[delegator, validator]` if set, otherwise
  the delegator account itself

Rounding:

- Use the existing reward precision rules in ABCI.
- Allocate rounding remainder to the final recipient in iteration order to
  preserve exact conservation of value.

This model gives the validator operator two reward components:

- commission for operating the validator
- pro-rata stake yield on the operator self-bond

## Validator Selection

When automatic selection is enabled, eligibility is determined by:

- validator status
- minimum self-bond
- minimum total bond
- not jailed
- not pending forced removal

Ranking key:

- primary: `self_bond + total_delegated`
- secondary: deterministic validator key ordering
- incumbents keep their seat on equal stake and on sub-margin stake leads

Selection output:

- top `max_validators` eligible validators become `nodes`
- all selected validators receive active power according to `power_mode`

`power_mode` values:

- `equal`
  Every active validator receives the same CometBFT power.
- `requested`
  Each active validator receives its configured `requested_power`.
- `stake_weighted`
  Reserved for a later phase.

The recommended rollout mode is `equal`.

## ABCI Integration

Compatibility requirements:

- `masternodes.nodes` remains the active validator list
- `masternodes.validator_power:<vk>` remains the effective CometBFT power source
- `masternodes.reward_keys:<vk>` remains the operator reward key source

ABCI reward handling should evolve as follows:

- keep reading the active validator list from `masternodes.nodes`
- for each validator reward allotment, read:
  - `commission_bps`
  - `self_bond`
  - `total_delegated`
  - `delegator_lists`
  - `delegations`
  - `delegator_reward_keys`
- compute the operator/delegator split off-chain
- emit reward records for both operator and delegators

This lets reward splitting ship before automatic validator-set selection.

## Governance Surface

Governance vote types should eventually include:

- `add_member`
- `remove_member`
- `jail_member`
- `unjail_member`
- `slash_member`
- `set_member_power`
- `change_registration_fee`
- `change_types`
- `set_policy_config`
- `approve_validator`
- `revoke_validator_approval`
- `set_manual_active_set`
- `set_validator_commission_cap`
- existing DAO and chi-cost actions

`manual_override_enabled` must allow emergency operation during rollout.

## Invariants

- `nodes` contains no duplicates.
- Every active validator has `status == active`.
- No jailed validator appears in `nodes`.
- `validator_power[v] == 0` for inactive validators.
- `self_bond[v] >= 0`.
- `total_delegated[v] >= 0`.
- `total_bond[v] = self_bond[v] + total_delegated[v]`.
- `total_slashed[v] >= 0`.
- processed evidence must not be applied twice.
- If `delegations[d, v] == 0`, `d` should eventually be removed from
  `delegator_lists[v]`.
- If `status in {left, removed, withdrawn}`, then `self_bond[v] == 0` and
  `total_delegated[v] == 0`.
- Reward distribution must conserve value exactly.
- Registration bond and self-bond are distinct balances.

## Rollout Plan

### Phase 1

- Keep `selection_mode = manual`.
- Add validator commission, self-bond, delegation state, undelegation queues,
  and reward splitting.
- Update ABCI reward handling to split validator rewards between operator and
  delegators.

### Phase 2

- Add policy config and exported views for automatic selection.
- Add epoch rebalance logic behind `auto_top_n` and `hybrid`.
- Keep `power_mode = equal`.

### Phase 3

- Add governance-controlled slashing on bonded stake, with optional
  `infraction_height` support for pending-unbond slashability.
- Route slashed value to a configurable slash destination.
- Add stronger performance protections for large delegator sets.

### Phase 4

- Add fuller evidence coverage if CometBFT expands delivered misbehavior types.
- Revisit stake-weighted consensus power only if required.

## Implementation Notes

- Canonical contract source: `xian-configs/contracts/members.s.py`
- Canonical network bundle: `xian-configs/contracts/contracts_*.json`
- ABCI reward integration: `xian-abci/src/xian/rewards.py`
- ABCI validator updates: `xian-abci/src/xian/validators.py`

The current contract now covers:

- Phase 1 reward split and delegation primitives
- Phase 2 automatic selection and policy controls
- validator-exit forced unbond sweeps with owner-indexed pending unbond lookup
- governance-controlled jailing and unjailing
- governance-controlled slashing on live stake and prior-infraction pending
  unbonds
- ABCI-driven evidence penalties for duplicate vote and light-client attack
- persistent validator-address resolution for evidence even after validator exit
- ABCI-driven epoch rebalances without requiring a user-submitted `rebalance()`

The main remaining gaps are:

- governance confirmation of the default evidence penalty table
