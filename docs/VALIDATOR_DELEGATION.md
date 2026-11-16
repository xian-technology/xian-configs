# Validator Delegation And Reward Distribution

## Purpose

This note defines the target validator policy model for Xian and the rollout
path from the current manual `validators` governance flow to configurable
validator selection with on-chain delegation and reward splitting.

The canonical contract source remains
`xian-configs/contracts/validators.s.py`, deployed into genesis as
`validators`.

## Current State

- Validator membership is governed manually through `validators`.
- The active validator set is the on-chain list `validators.active_validators`.
- Active validators and pending or approved candidates share a fixed pool of
  64 accounts. `max_validators` is limited to 1–64. Registration refuses a full
  pool before collecting its fee; withdrawing or leaving registration frees a
  slot. Jailed validators retain their slot while registered. Lifting a downtime
  jail after withdrawal or removal clears the jail, but requires a fresh paid
  registration before the account can become a validator again.
- ABCI reads `validators.active_validators` and optional
  `validators.powers:<vk>` to build CometBFT validator updates.
- Fee rewards are computed by the block executor (vm-core `tx_rewards`): each
  active validator's allotment (by `powers`) pays its operator reward key and
  credits its delegation pool; delegators are paid lazily by the contract
  (reward per share, see Reward Distribution).
- Generic staking contracts exist in `xian-contracts`, but they are not the
  consensus validator registry and they do not model validator delegation.

## Goals

- Keep `currency` as the staking token without embedding validator logic into
  the token contract.
- Use `validators.active_validators` and `validators.powers` as the canonical
  validator-set outputs consumed by ABCI.
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

## Operating Modes

The validator policy contract must support the following modes:

- `manual`
  Active validators are changed through governance votes.
- `auto_top_n`
  Active validators are the top `N` eligible validators by total bonded stake.
- `hybrid`
  Governance controls validator eligibility and the active set is chosen as the
  top `N` among approved and eligible validators.

The recommended default for curated public networks is `hybrid`. Mainnet
starts in `manual` mode with a non-zero minimum stake (see Mainnet Prepared
Profile); moving to `hybrid` or `auto_top_n` later is one `update_policy`
vote (see Switching Selection Mode).

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
- `max_new_power_bps`
- `downtime_jail_blocks`
- `downtime_slash_bps`
- `downtime_unjail_cooldown_hours`

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
- active genesis bundles under `xian-configs/contracts/contracts_<bundle>.json`
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
  through an internal `validators.apply_evidence_penalty(...)` call before
  rewards and validator updates are computed

## Validator State Model

The `validators` contract remains the source of truth for:

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

- `active_validators -> list[str]`
- `candidates -> list[str]`
- `registry_count -> int`
- `registry_accounts[index] -> str` (append-only identity history)
- `known_validators[validator] -> bool`
- `consensus_keys[sha256(raw_public_key)[:20].hex()] -> str`
- `statuses[validator] -> str`
- `powers[validator] -> int`
- `requested_power[validator] -> int`
- `reward_keys[validator] -> str`
- `commission_bps[validator] -> int`
- `registration_bonds[validator] -> decimal`
- `self_bond[validator] -> decimal`
- `total_delegated[validator] -> decimal` (tokens of the delegation pool)
- `total_shares[validator] -> decimal` (shares owning those tokens)
- `delegation_shares[delegator, validator] -> decimal`
- `delegator_counts[validator] -> int`
- `delegator_reward_keys[delegator, validator] -> str | None`
- `reward_per_share[validator] -> decimal` (written by the fee path only)
- `reward_debt[delegator, validator] -> decimal`
- `reward_pool[validator] -> decimal` (credited, not yet paid out)
- `pending_unbond_counter -> int`
- `pending_unbond_heads[kind, account] -> int | None`
- `pending_unbond_tails[kind, account] -> int | None`
- `pending_unbond_links[kind, id, "previous" | "next"] -> int | None`
- `pending_unbonds[id] -> dict`
- `jailed[validator] -> bool`
- `jail_reasons[validator] -> str | None`
- `total_slashed[validator] -> decimal`
- `last_slashed_at[validator] -> datetime | None`
- `processed_evidence[evidence_id] -> bool`
- `last_evidence_ids[validator] -> str | None`
- `last_evidence_types[validator] -> str | None`
- `last_evidence_heights[validator] -> int | None`
- `last_evidence_at[validator] -> datetime | None`
- `last_jailed_at[validator] -> datetime | None`
- `last_unjailed_at[validator] -> datetime | None`
- `config[<name>] -> value`

`holdings` in the existing contract represents the registration bond and should
remain distinct from validator self-bond used for delegation math.

## Validator Lifecycle

### Registration

`register(...)` creates a validator candidate entry and locks the registration
bond. Registration does not make a validator active by itself.

The validator account key is the signing account and becomes the CometBFT
consensus key. It must be the canonical lowercase 64-hex public key: hex-case
variants verify with the same key but are distinct account strings, so
`register()` and genesis `genesis_nodes` reject anything else.

Validators provide:

- validator account key
- operator reward key
- requested validator power
- moniker
- network endpoint
- metadata URI
- commission rate in basis points

### Activation

- `manual`: activation happens through governance. An `add_member` proposal
  records the candidate's requested power (default `10`) when it is created as
  `member_power`; activation uses that value even if the candidate edits its
  registration while the vote is open. Later changes go through
  `set_member_power`.
- `auto_top_n`: activation happens through epoch rebalance when the validator is
  eligible and ranked in the top `N`.
- `hybrid`: governance approves eligibility, epoch rebalance chooses top `N`.

### Leaving

Validators announce leave first, then leave after the configured delay. An
announcement preserves active membership and the pending leave deadline during
automatic rebalances; jail, bond eligibility, and stake ranking can still make
the validator inactive. `leave()` removes the validator from the active set, zeroes active voting power, refunds
the registration bond, and starts the self-bond's unbonding. Delegations stay
in the validator's pool (see Validator Exit).

The last active validator cannot leave. Governance cannot remove or jail it, and
a rebalance requested by governance that would select nobody is rejected. Epoch
and evidence-triggered rebalances that would select nobody keep the current set.
An empty set would leave no member able to propose recovery votes.

### Removal

Governance can remove a validator. Removal ejects the validator from the active
set and takes the same exit path.

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

Downtime jailing needs no vote. FinalizeBlock passes the active validators
absent from the decided last commit to `record_liveness(absent)` (a system
transaction that runs only when someone is absent or a count is open); a
signature or nil vote resets a validator's `missed_blocks`, and at
`downtime_jail_blocks` consecutive misses the validator is jailed through the
evidence penalty path (infraction `DOWNTIME`, `downtime_slash_bps`). Nobody is
jailed while more than a third of the active power is absent, nor the last
active validator. The validator lifts a downtime jail itself with `unjail()`
after `downtime_unjail_cooldown_hours`. Downtime is not malicious, so the validator's minimum stake must hold, and if a seat is free it re-enters the
active set at once (in every selection mode, `manual` included) with its
requested power (`manual`) or its selection power (automatic modes) and a
fresh missed-block count. The re-entry counts against the same
`max_new_power_bps` budget as the epoch's rebalance newcomers: when the
newcomers admitted in the current selection epoch (rebalance interval) would
then exceed the cap, `unjail()` is refused ("retry next epoch") and the
validator stays jailed until it calls again in a later epoch. Without a free
seat the jail is lifted and the validator waits as an approved candidate.
Evidence and governance jails keep their path: governance lifts them, and the
validator returns as an approved candidate (re-added by `add_member` in
`manual` mode, re-selected by the next rebalance otherwise). A governance `jail_member` cannot use the reason `downtime`, which marks a
runtime downtime jail.

With equal power and the 20% cap a validator re-enters directly only into a
set of at least four active validators (its 10 of 50 power is the cap); in a
smaller set `unjail()` keeps refusing, and governance lifts the jail with
`unjail_member` and re-adds the validator with `add_member` (governance is
not capped).

Newcomers admitted by an automatic rebalance (empty seats and replacements)
hold at most `max_new_power_bps` of the new set's power together, so even a
rebalance whose newcomers never come online leaves the incumbents above the
2/3 quorum. `add_member` is governance's deliberate act and is not capped.

Validator state can change while a vote is open. `add_member`, `remove_member`
and `jail_member` proposals are re-checked at finalization; a proposal whose
target is no longer eligible (jailed candidate, already removed member, already
jailed member, or the last active validator) is finalized as `rejected` without
side effects. Evidence still slashes the last active validator but does not
jail it.

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
  `self_bond + total_delegated`; the delegation pool is one participant, so a
  slash lowers `total_delegated` (every share's value at once) and never
  touches individual delegations, shares, or earned rewards
- rewards a delegator earned before the slash stay claimable; live self bond
  and delegation principal change together, so a block boundary never exposes
  only one of those two participants as slashed
- a 100% slash leaves a pool with shares but no tokens: it earns nothing,
  refuses new delegations, and its holders can still claim rewards and leave
  with `undelegate(validator, 0)`
- if `infraction_height` is provided, slashable stake also includes unclaimed
  pending unbonds for the same validator whose `created_block` is greater than
  or equal to that infraction height
- registration bonds are not slashable
- slash application is pro-rata across all slashable stake in scope for that
  call, using cumulative proportional targets at the VM's 30-place fixed
  precision; each participant pays the difference between successive targets
  so debits conserve the total and never exceed the participant's stake
- a total slash that rounds to zero records the penalty without a zero-value
  currency transfer
- the slashed amount is transferred to the slash destination accepted when
  the penalty was requested; policy updates cannot redirect an unfinished job

Because the current `currency` contract has no native burn entrypoint, the
default slash destination is `dao`. Networks can override this destination
through policy config if they want slashed value to flow somewhere else.

Live-only penalties execute synchronously. Pending-unbond penalties use
`validator_penalties`, which collects eligible amounts and applies the same
ordered cumulative arithmetic over multiple blocks. The internal
`process_pending_slashes` call has one shared maximum of 32 work units across
all jobs and phases per block. A live-stake work unit applies the self/pool
pair atomically. Each pending-unbond visit takes one unit. Jobs contain a
cursor and scalar totals rather than a copy of the pending set.

The configured evidence jail policy takes effect immediately, except for the
last active validator. While a validator has unfinished jobs, claims against
its unbonds and changes to its stake, registration, exit or jail status are
held. Earned reward claims remain available. Progress and already allocated
slash escrow are committed atomically; a restart resumes the stored cursor.
The final currency transfer and removal from the live job queue commit
together, so a replay cannot pay twice. Later jobs compound the results of
earlier jobs. Automatic selection rebalances after completed work.

Observability:

- `validator_record` exposes `total_slashed` and `last_slashed_at`
- a synchronous governance vote stores the exact `slash_amount`; an asynchronous
  result identifies its queued job
- `validator_penalties.get_pending_slash_job(job_id)` reports the phase, cursor,
  processed principal, allocated escrow, and completed slash amount
- `validator_record` includes `pending_slash_count`

### Evidence-Driven Penalties

ABCI can now turn CometBFT `FinalizeBlock.misbehavior` entries into internal
penalty calls.

Current supported evidence types:

- `DUPLICATE_VOTE`
- `LIGHT_CLIENT_ATTACK`

Current runtime flow:

1. `finalize_block` receives `misbehavior` entries from CometBFT.
2. ABCI resolves the misbehaving validator through the persistent consensus
   address-to-key mapping, including validators that have left the active set.
3. ABCI computes a deterministic `evidence_id` and calls
   `validators.apply_evidence_penalty(...)` as an internal system sender.
4. The contract deduplicates repeated evidence with `processed_evidence`.
5. The configured jail policy is applied and the slash is performed or queued.
   Evidence slashing uses `evidence_height`, so only pending unbonds created at
   or after that infraction are included.
6. Once per block, the node advances the shared bounded penalty queue before
   epoch selection. In automatic modes, changes to selection state and completed
   penalties trigger a rebalance.

Current policy controls:

- `duplicate_vote_slash_bps`
- `duplicate_vote_jail`
- `light_client_attack_slash_bps`
- `light_client_attack_jail`

The current defaults are intentionally conservative placeholders, not final
governance recommendations.

### Candidate Withdrawal

`unregister()` takes the same exit path for pending or approved validators.

### Validator Exit

An exit (leave, governance removal, withdrawal) refunds the registration bond
and moves the operator's self bond into a pending unbond (with `reason`
`left`, `removed` or `withdrawn`). It does not touch delegations: they stay in
the validator's pool, which earns nothing once the validator is inactive, and
each delegator undelegates when it chooses. The exit's cost does not grow with
delegators, so a validator with any number of delegators can leave or be
removed. Undelegating from an exited validator unlocks at `left_at` plus the
unbonding period (at once if that has passed), as the old forced sweep did,
and the pending unbond stays slashable for infractions at or before its
creation. A validator that registers again keeps the delegations it still
has.

## Delegator Lifecycle

### Delegate

`delegate(validator, amount, reward_key=None)` transfers `currency` into the
contract and buys pool shares: `amount` while the pool is empty, else
`amount * total_shares / total_delegated` (rounded down). It first pays out
the delegator's pending reward from that validator. A pool whose tokens were
fully slashed refuses new delegations.

### Undelegate

`undelegate(validator, amount)` pays out the pending reward, burns the shares
worth `amount` (all of them when `amount` is the delegation's full value) and
creates a pending unbond for the released tokens. `get_delegation` returns the
current value as `amount`.

### Claim Rewards

`claim_rewards(validator)` pays the delegator's pending reward from that
validator to its reward key (`DelegatorRewardClaimed` event). Every
delegation change claims first, so a reward key change never redirects
rewards already earned. `get_pending_rewards(delegator, validator)` (and
`get_delegation(...)["pending_rewards"]`) report what a claim would pay.

### Claim Unbond

`claim_unbond(unbond_id)` releases funds after the unbonding period.
It removes the record from both live ordered indexes while retaining the
archival record and the double-claim guard. Counts, amounts and earliest unlock
are maintained as scalar summaries with an indexed minimum heap, so another
delegator's queue does not make validator lifecycle calls scan that queue.

`get_pending_unbond_page(owner, cursor=None, limit=100)` returns up to 100 live
records and a `next_cursor`; a stale or foreign cursor fails without a scan.
`get_validators_page(cursor=None, limit=25)` pages the append-only identity
history. `get_validator_count()` is constant work. Legacy full-list contract
functions remain available; network queries use the bounded page interfaces
and explicitly reject oversized legacy list responses.

Indexers list a validator's delegators from the `Delegated` and `Undelegated`
events (delegator, validator, amount, shares); the contract keeps only
`delegator_counts`.

## Reward Distribution

The block executor (vm-core `tx_rewards`) computes every paid transaction's
rewards. Its work and writes grow with the active validators, never with
delegators.

For each active validator's allotment `R` (its share of the validator total
by power, in chi):

1. `bps = effective_commission_bps(validator)`: `commission_bps` clamped to
   `[0, max_commission_bps]` (the policy maximum, itself within `[0, 10000]`).
   The contract's views and the fee path apply this one rule.
2. `commission = R * bps / 10000`, `remainder = R - commission`.
3. `stake_base = self_bond + total_delegated`.
4. If the pool has tokens and shares:
   `pool = remainder * total_delegated / stake_base`, else `pool = 0`.
5. The operator gets `R - pool` (its commission, its self bond's part, and the
   rounding), paid to `reward_keys[validator]`.
6. The pool's tokens (`pool / chi rate`) are credited to the `validators`
   balance and `reward_pool[validator]`, and `reward_per_share[validator]`
   grows by `tokens / total_shares`. A credit too small for any share goes to
   the operator.

Each validator's stake (`self_bond`, `total_delegated`, `total_shares`) is
read as the transaction leaves it (a delegation in the same transaction is
already in the pool, a slash already applied); everything else (split, chi
rate, foundation, developers, active set, powers, commission) as the
transaction found it.

A delegator's pending reward is
`shares * reward_per_share - reward_debt`, at least 0; after each change the
debt is reset to `shares * reward_per_share` plus one 10^-30 unit. All
products and quotients are `ContractingDecimal` (30 places) rounded down, so
no holder is ever paid more than its exact share and `reward_pool` never goes
negative.

Conservation, exactly: the fee splits into operators, pools, foundation,
developers and the burned rest; per validator, everything credited to the
pool equals what was paid out plus `reward_pool`; `reward_pool` is the sum of
the pending rewards plus the rounding dust, which stays in the pool.

Receipts carry one `validator_reward` record per active validator and one
`delegator_pool_reward` record (recipient `validators`, with `validator_key`)
per credited pool; there are no per-delegator records.

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

- top `max_validators` eligible validators become `active_validators`
- all selected validators receive active power according to `power_mode`

`power_mode` values:

- `equal`
  Every active validator receives the same CometBFT power.
- `requested`
  Each active validator receives its configured `requested_power`.
- `stake_weighted`
  Each active validator receives its integer total bond as power.

A single validator's power is capped at `10^12` (`MAX_VALIDATOR_POWER`):
requested power at registration, `update_registration`, genesis powers and
`set_member_power` reject larger values, and stake-weighted power is clamped.
Every power change also checks that the active total stays within CometBFT's
`MaxTotalVotingPower` (`MaxInt64 / 8`), so no selection can produce a validator
update that consensus rejects.

The recommended rollout mode is `equal`.

## Mainnet Prepared Profile

`contracts/contracts_mainnet.json` pins the launch policy:

- `selection_mode = "manual"`: the active set changes only through
  governance votes
- `max_validators = 13`
- `power_mode = "equal"`
- `rebalance_interval = 720`
- `activation_delay_epochs = 1`
- `unbonding_period_days = 14`
- `min_self_bond = 100000` and `min_total_bond = 500000` (XIAN)
- `max_commission_bps = 2000`
- `max_active_set_churn = 1`
- `min_bond_margin_bps = 500`
- `max_new_power_bps = 2000`, `downtime_jail_blocks = 500`,
  `downtime_slash_bps = 0`, `downtime_unjail_cooldown_hours = 24`

The minimum stake applies in every mode: an `add_member` proposal (manual or
hybrid) is refused, and an open one rejected at finalization, when the
candidate's self bond or total bond is below the minimum; automatic selection
skips such accounts. The genesis validator starts without a bond; the
minimum applies to it only once selection becomes automatic.

The churn limit counts every newcomer a rebalance admits, whether it fills an
empty seat or replaces an incumbent, so no rebalance can hand most of the set
to fresh accounts. `max_active_set_churn = 0` admits no one automatically.

### Switching Selection Mode

Moving from `manual` to `hybrid` or `auto_top_n` is one governance action:

1. Every validator that should stay bonds at least `min_self_bond` and
   reaches `min_total_bond`; candidates register and bond.
2. A validator proposes `update_policy` with the new `selection_mode` (and any
   other policy fields), and the members vote it through.
3. Finalizing the vote applies the policy and rebalances at once: incumbents
   below the minimum leave the set, at most `max_active_set_churn` newcomers
   enter, and from then on ABCI rebalances every `rebalance_interval` blocks.

Switch only once the active set is full of bonded validators (add them in
`manual` mode first). Automatic selection admits newcomers into empty seats
one per rebalance with no stake comparison: from a one-validator set, twelve
fresh accounts holding the minimum stake (7.2M XIAN with the registration
fees) hold 12 of 13 seats after 12 epochs. Into a full set they must outbond
an incumbent by `min_bond_margin_bps`, one per rebalance.

If that rebalance would leave no active validator the vote cannot finalize,
so a switch can never empty the set. Switching back to `manual` is the same
vote; the active set then stays as it is.

## ABCI Integration

ABCI integration requirements:

- `validators.active_validators` is the active validator list
- `validators.powers:<vk>` is the effective CometBFT power source
- `validators.reward_keys:<vk>` is the operator reward key source

ABCI reward handling should evolve as follows:

- keep reading the active validator list from `validators.active_validators`
- for each validator reward allotment, the block executor reads
  `commission_bps`, `config:max_commission_bps`, `self_bond`,
  `total_delegated` and `total_shares`, and writes the operator's balance,
  `reward_per_share`, `reward_pool` and the `validators` balance
- no delegator state is read or written by the fee path

## Governance Surface

`propose_vote` validates each built-in vote type before a proposal id is
allocated. Scalar amounts/power/basis points, typed objects, policy keys,
reward splits, DAO payouts, vote-type lists, and topic payloads reject empty,
unknown, negative, duplicate, or wrong-type values at proposal creation rather
than deferring failure until finalization. Reward splits contain validator,
burn, foundation, and developer ratios in that order. Individual ratios may be
zero, but all four values must be numeric, non-negative, and sum to one.
`chi_cost_change` requires a positive integer no larger than `chi_cost.max_value()`
(`10**61 - 1`, the largest rate the node prices fees with), matching
`chi_cost.set_value`: a larger stored rate would stop every validator at the
next paid transaction.

The registration fee must remain positive because `register()` transfers that
amount through `currency.transfer_from`, which rejects zero-value transfers.

`change_types` cannot remove the immutable recovery vote types:

- `add_member`
- `remove_member`
- `jail_member`
- `unjail_member`
- `slash_member`
- `set_member_power`
- `change_registration_fee`
- `chi_cost_change`
- `change_types`
- `update_policy`

That fail-closed set preserves validator membership/quorum repair, safety
actions, voting power, candidate fee repair, chi-cost repair, restoration of
the vote surface itself, and selection-policy recovery. `reward_change`,
`dao_payout` and `topic_vote` remain configurable.

Read clients can use `get_validators()` for the full registry, including
`left`, `removed`, and `withdrawn` records. Each validator record includes
pending-unbond aggregates, last-rebalance epoch/eligibility, jail/unjail times,
slash totals, and last evidence metadata.

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

- `active_validators` contains no duplicates and is never empty.
- `0 < powers[v] <= 10^12` for active validators, and their sum stays within
  CometBFT `MaxTotalVotingPower`.
- Every active validator has `status == active`.
- No jailed validator appears in `active_validators`.
- `powers[v] == 0` for inactive validators.
- `self_bond[v] >= 0`.
- `total_delegated[v] >= 0`.
- `total_bond[v] = self_bond[v] + total_delegated[v]`.
- `total_slashed[v] >= 0`.
- processed evidence must not be applied twice.
- every value stored in `types` includes all immutable recovery vote types.
- `total_shares[v]` is the sum of `delegation_shares[*, v]`, and a pool
  without shares has no tokens (a fully slashed pool can have shares and no
  tokens).
- `currency.balances:validators` equals the registration bonds, self bonds,
  pool tokens, unclaimed pending unbonds and `reward_pool`s.
- `reward_pool[v]` is at least the sum of its delegators' pending rewards.
- If `status in {left, removed, withdrawn}`, then `self_bond[v] == 0`.
- Reward distribution must conserve value exactly.
- The canonical fee split is 70% validators, 0% burn, 0% foundation, and 30%
  contract developers.
- A developer share without a claimable developer returns to the validator
  reward pool before operator commission and delegation splitting.
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

- Canonical contract source: `xian-configs/contracts/validators.s.py`
- Canonical network bundle: `xian-configs/contracts/contracts_*.json`
- Fee reward split (block executor, Rust): `xian-contracting/packages/xian-vm-core/src/tx_rewards.rs`
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
