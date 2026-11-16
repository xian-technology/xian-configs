import dao
import rewards
import chi_cost
import currency

active_validators = Variable()
candidates = Variable()
votes = Hash(default_value=False)
vote_records = Hash(default_value=None)
vote_weights = Hash(default_value=0)
total_votes = Variable()
types = Variable()

registration_fee = Variable()
pending_registrations = Hash(default_value=False)
pending_leave = Hash(default_value=False)
holdings = Hash(default_value=0)

config = Hash(default_value=None)
commission_bps = Hash(default_value=0)
self_bond = Hash(default_value=0)
# Each validator's delegation pool: total_delegated[V] tokens owned by
# total_shares[V] shares. A slash lowers the tokens, so every share at once.
total_delegated = Hash(default_value=0)
total_shares = Hash(default_value=0)
delegation_shares = Hash(default_value=0)
delegator_counts = Hash(default_value=0)
delegator_reward_keys = Hash(default_value=None)
# Lazy delegator rewards: the fee path adds each paid transaction's pool
# credit to reward_pool[V] and its rate per share to reward_per_share[V];
# a delegator is paid shares * reward_per_share - reward_debt on change.
reward_per_share = Hash(default_value=0)
reward_debt = Hash(default_value=0)
reward_pool = Hash(default_value=0)
# Consecutive blocks a validator's signature was absent from the decided
# last commit (FinalizeBlock, through record_liveness).
missed_blocks = Hash(default_value=0)
pending_unbond_counter = Variable()
pending_unbond_owner_ids = Hash(default_value=None)
pending_unbond_validator_ids = Hash(default_value=None)
pending_unbonds = Hash(default_value=None)
jailed = Hash(default_value=False)
jail_reasons = Hash(default_value=None)
total_slashed = Hash(default_value=0)
last_slashed_at = Hash(default_value=None)
processed_evidence = Hash(default_value=False)
last_evidence_ids = Hash(default_value=None)
last_evidence_types = Hash(default_value=None)
last_evidence_heights = Hash(default_value=None)
last_evidence_at = Hash(default_value=None)
last_jailed_at = Hash(default_value=None)
last_unjailed_at = Hash(default_value=None)
validator_registry = Variable()

powers = Hash(default_value=0)
requested_power = Hash(default_value=0)
reward_keys = Hash(default_value=None)
monikers = Hash(default_value="")
network_endpoints = Hash(default_value="")
metadata_uris = Hash(default_value="")
statuses = Hash(default_value="")
registered_at = Hash(default_value=None)
joined_at = Hash(default_value=None)
left_at = Hash(default_value=None)
eligible_at_epoch = Hash(default_value=0)
last_rebalance_epoch = Variable()
# Newcomer power admitted in admission_epoch (rebalances and re-entries after
# a downtime jail share one max_new_power_bps budget per selection epoch).
admission_epoch = Variable()
admitted_new_power = Variable()

STATUS_NONE = "none"
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_LEAVING = "leaving"
STATUS_LEFT = "left"
STATUS_REMOVED = "removed"
STATUS_WITHDRAWN = "withdrawn"
STATUS_REJECTED = "rejected"
STATUS_APPROVED = "approved"
STATUS_EXPIRED = "expired"

DEFAULT_VALIDATOR_POWER = 10
DEFAULT_COMMISSION_BPS = 0
MAX_COMMISSION_BPS = 10000
# Active validators and candidates share a bounded selection pool. Its worst
# case rebalance and deciding governance vote must fit the chain's chi cap.
MAX_VALIDATOR_ACCOUNTS = 64
PASS_THRESHOLD_NUMERATOR = 4
PASS_THRESHOLD_DENOMINATOR = 5
PROPOSAL_EXPIRY_DAYS = 7
LEAVE_DELAY_DAYS = 7
DEFAULT_SELECTION_MODE = "manual"
DEFAULT_MAX_VALIDATORS = 5
DEFAULT_POWER_MODE = "equal"
DEFAULT_REBALANCE_INTERVAL = 1
DEFAULT_ACTIVATION_DELAY_EPOCHS = 0
DEFAULT_UNBONDING_PERIOD_DAYS = 7
DEFAULT_MIN_SELF_BOND = 0
DEFAULT_MIN_TOTAL_BOND = 0
DEFAULT_MAX_ACTIVE_SET_CHURN = 1
DEFAULT_MIN_BOND_MARGIN_BPS = 0
DEFAULT_SLASH_DESTINATION = "dao"
DEFAULT_DUPLICATE_VOTE_SLASH_BPS = 500
DEFAULT_LIGHT_CLIENT_ATTACK_SLASH_BPS = 1000
SYSTEM_EVIDENCE_CALLER = "__evidence_penalty_driver__"
SYSTEM_LIVENESS_CALLER = "__liveness_driver__"
# Newcomers a rebalance admits may hold at most this share of the new set's
# power, so validators that never come online cannot stall consensus.
DEFAULT_MAX_NEW_POWER_BPS = 2000
DEFAULT_DOWNTIME_JAIL_BLOCKS = 500
DEFAULT_DOWNTIME_SLASH_BPS = 0
DEFAULT_DOWNTIME_UNJAIL_COOLDOWN_HOURS = 24
# A single validator's power stays far below CometBFT's total limit, so even a
# very large set cannot overflow consensus; the total is still checked.
MAX_VALIDATOR_POWER = 1000000000000
# CometBFT MaxTotalVotingPower: MaxInt64 / 8.
MAX_TOTAL_VOTING_POWER = 1152921504606846975
# Added to a reward debt so a holder is never paid a rounding unit it did
# not earn: payouts then never exceed the pool (validators docs, rewards).
REWARD_DEBT_ROUNDING = decimal("0.000000000000000000000000000001")
DECIMAL_SCALE = 1000000000000000000000000000000
EXITED_STATUSES = ["left", "removed", "withdrawn"]
CANONICAL_KEY_LENGTH = 64
CANONICAL_KEY_DIGITS = "0123456789abcdef"

ValidatorProposalSubmittedEvent = LogEvent(
    "ValidatorProposalSubmitted",
    {
        "proposal_id": {"type": int, "idx": True},
        "type_of_vote": {"type": str, "idx": True},
        "proposer": {"type": str, "idx": True},
        "status": {"type": str},
    },
)

ValidatorProposalVotedEvent = LogEvent(
    "ValidatorProposalVoted",
    {
        "proposal_id": {"type": int, "idx": True},
        "voter": {"type": str, "idx": True},
        "vote": {"type": str, "idx": True},
        "weight": {"type": int},
        "yes_votes": {"type": int},
        "no_votes": {"type": int},
        "yes_weight": {"type": int},
        "no_weight": {"type": int},
    },
)

ValidatorProposalApprovedEvent = LogEvent(
    "ValidatorProposalApproved",
    {
        "proposal_id": {"type": int, "idx": True},
        "type_of_vote": {"type": str, "idx": True},
        "approver": {"type": str, "idx": True},
        "status": {"type": str},
    },
)

ValidatorProposalRejectedEvent = LogEvent(
    "ValidatorProposalRejected",
    {
        "proposal_id": {"type": int, "idx": True},
        "type_of_vote": {"type": str, "idx": True},
        "rejector": {"type": str, "idx": True},
        "status": {"type": str},
    },
)

DelegatedEvent = LogEvent(
    "Delegated",
    {
        "delegator": {"type": str, "idx": True},
        "validator": {"type": str, "idx": True},
        "amount": {"type": (int, decimal)},
        "shares": {"type": (int, decimal)},
    },
)

UndelegatedEvent = LogEvent(
    "Undelegated",
    {
        "delegator": {"type": str, "idx": True},
        "validator": {"type": str, "idx": True},
        "amount": {"type": (int, decimal)},
        "shares": {"type": (int, decimal)},
    },
)

DelegatorRewardClaimedEvent = LogEvent(
    "DelegatorRewardClaimed",
    {
        "delegator": {"type": str, "idx": True},
        "validator": {"type": str, "idx": True},
        "recipient": {"type": str, "idx": True},
        "amount": {"type": (int, decimal)},
    },
)

ValidatorProposalExpiredEvent = LogEvent(
    "ValidatorProposalExpired",
    {
        "proposal_id": {"type": int, "idx": True},
        "type_of_vote": {"type": str, "idx": True},
        "expirer": {"type": str, "idx": True},
        "status": {"type": str},
    },
)


def recovery_vote_types():
    return [
        "add_member",
        "remove_member",
        "jail_member",
        "unjail_member",
        "slash_member",
        "set_member_power",
        "change_registration_fee",
        "chi_cost_change",
        "change_types",
        "update_policy",
    ]


def default_vote_types():
    return recovery_vote_types() + [
        "reward_change",
        "dao_payout",
        "topic_vote",
    ]


@construct
def seed(
    genesis_nodes: list,
    genesis_registration_fee: int,
    genesis_powers: dict = None,
    genesis_reward_keys: dict = None,
    default_node_power: int = DEFAULT_VALIDATOR_POWER,
    selection_mode: str = DEFAULT_SELECTION_MODE,
    max_validators: int = DEFAULT_MAX_VALIDATORS,
    power_mode: str = DEFAULT_POWER_MODE,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    activation_delay_epochs: int = DEFAULT_ACTIVATION_DELAY_EPOCHS,
    unbonding_period_days: int = DEFAULT_UNBONDING_PERIOD_DAYS,
    min_self_bond: int = DEFAULT_MIN_SELF_BOND,
    min_total_bond: int = DEFAULT_MIN_TOTAL_BOND,
    max_commission_bps: int = MAX_COMMISSION_BPS,
    max_active_set_churn: int = DEFAULT_MAX_ACTIVE_SET_CHURN,
    min_bond_margin_bps: int = DEFAULT_MIN_BOND_MARGIN_BPS,
    manual_override_enabled: bool = True,
    slash_destination: str = DEFAULT_SLASH_DESTINATION,
    duplicate_vote_slash_bps: int = DEFAULT_DUPLICATE_VOTE_SLASH_BPS,
    duplicate_vote_jail: bool = True,
    light_client_attack_slash_bps: int = DEFAULT_LIGHT_CLIENT_ATTACK_SLASH_BPS,
    light_client_attack_jail: bool = True,
    max_new_power_bps: int = DEFAULT_MAX_NEW_POWER_BPS,
    downtime_jail_blocks: int = DEFAULT_DOWNTIME_JAIL_BLOCKS,
    downtime_slash_bps: int = DEFAULT_DOWNTIME_SLASH_BPS,
    downtime_unjail_cooldown_hours: int = DEFAULT_DOWNTIME_UNJAIL_COOLDOWN_HOURS,
):
    assert is_number(genesis_registration_fee), "registration_fee must be numeric."
    assert genesis_registration_fee > 0, "registration_fee <= 0"
    assert default_node_power > 0, "default_node_power <= 0"

    active_validators.set([])
    candidates.set([])
    pending_unbond_counter.set(0)
    last_rebalance_epoch.set(None)
    validator_registry.set([])
    types.set(default_vote_types())
    total_votes.set(0)
    registration_fee.set(genesis_registration_fee)
    seeded_policy = {
        "selection_mode": selection_mode,
        "max_validators": max_validators,
        "power_mode": power_mode,
        "rebalance_interval": rebalance_interval,
        "activation_delay_epochs": activation_delay_epochs,
        "unbonding_period_days": unbonding_period_days,
        "min_self_bond": min_self_bond,
        "min_total_bond": min_total_bond,
        "max_commission_bps": max_commission_bps,
        "max_active_set_churn": max_active_set_churn,
        "min_bond_margin_bps": min_bond_margin_bps,
        "manual_override_enabled": manual_override_enabled,
        "slash_destination": slash_destination,
        "duplicate_vote_slash_bps": duplicate_vote_slash_bps,
        "duplicate_vote_jail": duplicate_vote_jail,
        "light_client_attack_slash_bps": light_client_attack_slash_bps,
        "light_client_attack_jail": light_client_attack_jail,
        "max_new_power_bps": max_new_power_bps,
        "downtime_jail_blocks": downtime_jail_blocks,
        "downtime_slash_bps": downtime_slash_bps,
        "downtime_unjail_cooldown_hours": downtime_unjail_cooldown_hours,
    }
    for key in POLICY_KEYS:
        validate_policy_value(key, seeded_policy[key])
        config[key] = seeded_policy[key]

    active_nodes = []
    for node in genesis_nodes:
        require_canonical_validator_key(node)
        if node in active_nodes:
            continue

        require_selection_capacity(node, active_nodes)
        active_nodes.append(node)
        current_registry = validator_registry.get()
        current_registry.append(node)
        validator_registry.set(current_registry)
        statuses[node] = STATUS_ACTIVE
        registered_at[node] = now
        joined_at[node] = now
        eligible_at_epoch[node] = 0
        commission_bps[node] = DEFAULT_COMMISSION_BPS
        self_bond[node] = 0
        total_delegated[node] = 0
        requested_power[node] = resolve_requested_power(
            node,
            genesis_powers,
            default_node_power,
        )
        powers[node] = requested_power[node]
        reward_keys[node] = resolve_reward_key(node, genesis_reward_keys)

    assert len(active_nodes) > 0, "Genesis requires at least one validator."
    active_validators.set(active_nodes)
    require_total_power_within_limit()


def resolve_requested_power(
    account: str,
    configured_powers: dict,
    fallback_power: int = DEFAULT_VALIDATOR_POWER,
):
    power = fallback_power
    if configured_powers is not None:
        configured_power = configured_powers.get(account)
        if configured_power is not None:
            power = configured_power

    return require_validator_power(power)


def resolve_reward_key(account: str, configured_reward_keys: dict = None):
    reward_key = account
    if configured_reward_keys is not None:
        configured_reward_key = configured_reward_keys.get(account)
        if configured_reward_key is not None:
            reward_key = configured_reward_key

    if reward_key is None:
        reward_key = account
    if reward_key == "":
        reward_key = account

    return reward_key


def normalize_reward_key(account: str, reward_key: str = None):
    if reward_key is None:
        return account
    if reward_key == "":
        return account
    return reward_key


def normalize_reason(reason: str = None):
    if reason is None:
        return ""
    return reason


def normalize_jail_reason(reason: str = None):
    return normalize_reason(reason)


def is_integer(value: Any):
    return isinstance(value, int) and isinstance(value, bool) == False


def is_canonical_validator_key(value: Any):
    if not isinstance(value, str) or len(value) != CANONICAL_KEY_LENGTH:
        return False
    for character in value:
        if character not in CANONICAL_KEY_DIGITS:
            return False
    return True


def require_canonical_validator_key(value: Any):
    assert is_canonical_validator_key(
        value
    ), "Validator key must be a canonical lowercase 64-hex key."


def require_validator_power(power: Any):
    assert is_integer(power), "Validator power must be an integer."
    assert power > 0, "Validator power <= 0"
    assert power <= MAX_VALIDATOR_POWER, "Validator power exceeds the maximum."
    return power


def is_number(value: Any):
    return (
        isinstance(value, (int, decimal))
        and isinstance(value, bool) == False
    )


def validate_non_empty_string(value: Any, label: str):
    assert isinstance(value, str), label + " must be a string."
    assert value != "", label + " must be non-empty."


def validate_optional_string(value: Any, label: str):
    if value is not None:
        assert isinstance(value, str), label + " must be a string."


def validate_object_argument(arg: Any, allowed_keys: list, required_keys: list):
    assert isinstance(arg, dict), "Vote argument must be an object."
    for key in arg:
        assert key in allowed_keys, "Unexpected vote argument field."
    for key in required_keys:
        assert arg.get(key) is not None, "Missing vote argument field."


def active_nodes_list():
    current_nodes = active_validators.get()
    if current_nodes is None:
        return []
    return current_nodes


def candidate_list():
    current_candidates = candidates.get()
    if current_candidates is None:
        return []
    return current_candidates


def owner_pending_unbond_ids(owner: str):
    current_unbond_ids = pending_unbond_owner_ids[owner]
    if current_unbond_ids is None:
        return []
    return current_unbond_ids


def validator_pending_unbond_ids(validator: str):
    current_unbond_ids = pending_unbond_validator_ids[validator]
    if current_unbond_ids is None:
        return []
    return current_unbond_ids


def validator_registry_list():
    current_registry = validator_registry.get()
    if current_registry is None:
        return []
    return current_registry


def without_item(items: list, item: str):
    next_items = []
    for current_item in items:
        if current_item != item:
            next_items.append(current_item)
    return next_items


def effective_requested_power(account: str):
    power = requested_power[account]
    if power is None:
        return DEFAULT_VALIDATOR_POWER
    if power <= 0:
        return DEFAULT_VALIDATOR_POWER
    return power


def effective_active_power(account: str):
    power = powers[account]
    if power is None:
        if account in active_nodes_list():
            return effective_requested_power(account)
        return 0
    if power <= 0:
        if account in active_nodes_list():
            return effective_requested_power(account)
        return 0
    return power


def effective_reward_key(account: str):
    reward_key = reward_keys[account]
    if reward_key is None:
        return account
    if reward_key == "":
        return account
    return reward_key


def effective_max_commission_bps():
    max_commission = config["max_commission_bps"]
    if max_commission is None:
        return MAX_COMMISSION_BPS
    return min(max(max_commission, 0), MAX_COMMISSION_BPS)


def effective_commission_bps(account: str):
    # The fee path (vm-core tx_rewards) pays exactly this rate.
    configured_bps = commission_bps[account]
    if configured_bps is None:
        return DEFAULT_COMMISSION_BPS
    if configured_bps < 0:
        return DEFAULT_COMMISSION_BPS

    max_commission = effective_max_commission_bps()
    if configured_bps > max_commission:
        return max_commission

    return configured_bps


POLICY_KEYS = [
    "selection_mode",
    "max_validators",
    "power_mode",
    "rebalance_interval",
    "activation_delay_epochs",
    "unbonding_period_days",
    "min_self_bond",
    "min_total_bond",
    "max_commission_bps",
    "max_active_set_churn",
    "min_bond_margin_bps",
    "manual_override_enabled",
    "slash_destination",
    "duplicate_vote_slash_bps",
    "duplicate_vote_jail",
    "light_client_attack_slash_bps",
    "light_client_attack_jail",
    "max_new_power_bps",
    "downtime_jail_blocks",
    "downtime_slash_bps",
    "downtime_unjail_cooldown_hours",
]
POLICY_DEFAULTS = {
    "selection_mode": DEFAULT_SELECTION_MODE,
    "max_validators": DEFAULT_MAX_VALIDATORS,
    "power_mode": DEFAULT_POWER_MODE,
    "rebalance_interval": DEFAULT_REBALANCE_INTERVAL,
    "activation_delay_epochs": DEFAULT_ACTIVATION_DELAY_EPOCHS,
    "unbonding_period_days": DEFAULT_UNBONDING_PERIOD_DAYS,
    "min_self_bond": DEFAULT_MIN_SELF_BOND,
    "min_total_bond": DEFAULT_MIN_TOTAL_BOND,
    "max_commission_bps": MAX_COMMISSION_BPS,
    "max_active_set_churn": DEFAULT_MAX_ACTIVE_SET_CHURN,
    "min_bond_margin_bps": DEFAULT_MIN_BOND_MARGIN_BPS,
    "manual_override_enabled": True,
    "slash_destination": DEFAULT_SLASH_DESTINATION,
    "duplicate_vote_slash_bps": DEFAULT_DUPLICATE_VOTE_SLASH_BPS,
    "duplicate_vote_jail": True,
    "light_client_attack_slash_bps": DEFAULT_LIGHT_CLIENT_ATTACK_SLASH_BPS,
    "light_client_attack_jail": True,
    "max_new_power_bps": DEFAULT_MAX_NEW_POWER_BPS,
    "downtime_jail_blocks": DEFAULT_DOWNTIME_JAIL_BLOCKS,
    "downtime_slash_bps": DEFAULT_DOWNTIME_SLASH_BPS,
    "downtime_unjail_cooldown_hours": DEFAULT_DOWNTIME_UNJAIL_COOLDOWN_HOURS,
}
# [minimum, maximum or None] of each integer policy value.
POLICY_INT_BOUNDS = {
    "max_validators": [1, MAX_VALIDATOR_ACCOUNTS],
    "rebalance_interval": [1, None],
    "activation_delay_epochs": [0, None],
    "unbonding_period_days": [0, None],
    "min_self_bond": [0, None],
    "min_total_bond": [0, None],
    "max_commission_bps": [0, MAX_COMMISSION_BPS],
    "max_active_set_churn": [0, None],
    "min_bond_margin_bps": [0, None],
    "duplicate_vote_slash_bps": [0, 10000],
    "light_client_attack_slash_bps": [0, 10000],
    "max_new_power_bps": [0, 10000],
    "downtime_jail_blocks": [1, None],
    "downtime_slash_bps": [0, 10000],
    "downtime_unjail_cooldown_hours": [0, None],
}
POLICY_CHOICES = {
    "selection_mode": ["manual", "auto_top_n", "hybrid"],
    "power_mode": ["equal", "requested", "stake_weighted"],
}


def policy(key: str):
    # A missing or out-of-range value (a state patch) reads as the default.
    value = config[key]
    bounds = POLICY_INT_BOUNDS.get(key)
    if value is None or value == "":
        return POLICY_DEFAULTS[key]
    if bounds is not None and value < bounds[0]:
        return POLICY_DEFAULTS[key]
    return value


def validate_policy_value(key: str, value: Any):
    if key in POLICY_CHOICES:
        assert value in POLICY_CHOICES[key], "Bad " + key + "."
        return
    if key == "slash_destination":
        validate_non_empty_string(value, key)
        return
    bounds = POLICY_INT_BOUNDS.get(key)
    if bounds is None:
        assert isinstance(value, bool), key + " must be boolean."
        return
    assert is_integer(value), key + " must be an integer."
    assert value >= bounds[0], key + " is below its minimum."
    assert bounds[1] is None or value <= bounds[1], key + " is above its maximum."


def evidence_slash_bps(infraction_type: str):
    if infraction_type == "DUPLICATE_VOTE":
        return policy("duplicate_vote_slash_bps")
    if infraction_type == "LIGHT_CLIENT_ATTACK":
        return policy("light_client_attack_slash_bps")
    if infraction_type == "DOWNTIME":
        return policy("downtime_slash_bps")
    return 0


def evidence_should_jail(infraction_type: str):
    if infraction_type == "DOWNTIME":
        return True
    if infraction_type == "DUPLICATE_VOTE":
        return policy("duplicate_vote_jail")
    if infraction_type == "LIGHT_CLIENT_ATTACK":
        return policy("light_client_attack_jail")
    return False


def is_jailed(account: str):
    return jailed[account] == True


def current_block_number():
    current_height = block_num
    if current_height is None or current_height < 0:
        return 0
    return current_height


def current_selection_epoch():
    return current_block_number() // policy("rebalance_interval")


def total_bonded(account: str):
    return self_bond[account] + total_delegated[account]


def can_accept_delegation(account: str):
    if is_jailed(account):
        return False
    status = statuses[account]
    return status == STATUS_PENDING or status == STATUS_ACTIVE or status == STATUS_APPROVED


def scaled_units(value: Any):
    # A non-negative amount in units of 10**-30 (exact).
    return int(value * DECIMAL_SCALE)


def mul_div(value: Any, numerator: Any, denominator: Any):
    # value * numerator / denominator, truncated once (not after each step).
    units = scaled_units(value) * scaled_units(numerator) // scaled_units(denominator)
    return decimal(units) / DECIMAL_SCALE


def delegation_value(delegator: str, validator: str):
    shares = delegation_shares[delegator, validator]
    pool_shares = total_shares[validator]
    # The sole holder (or nobody: an empty pool holds nothing) owns it all.
    if shares == pool_shares:
        return total_delegated[validator]
    return mul_div(shares, total_delegated[validator], pool_shares)


def shares_for_amount(validator: str, amount: decimal):
    pool_shares = total_shares[validator]
    if pool_shares <= 0:
        return amount
    pool_tokens = total_delegated[validator]
    assert pool_tokens > 0, "Delegation pool fully slashed."
    # Slashes only lower the tokens, so a share is worth at most one token
    # and any positive amount buys a positive number of shares.
    return mul_div(amount, pool_shares, pool_tokens)


def released_stake(delegator: str, validator: str, amount: decimal, value: decimal):
    # A leaver never takes more than its shares are worth.
    if amount == value:
        return delegation_shares[delegator, validator], value
    burned = mul_div(amount, total_shares[validator], total_delegated[validator])
    released = mul_div(burned, total_delegated[validator], total_shares[validator])
    assert released > 0, "Undelegation too small."
    return burned, released


def add_pool_shares(delegator: str, validator: str, shares: decimal, amount: decimal):
    current_shares = delegation_shares[delegator, validator]
    if current_shares == 0:
        delegator_counts[validator] = delegator_counts[validator] + 1
    delegation_shares[delegator, validator] = current_shares + shares
    total_shares[validator] = total_shares[validator] + shares
    total_delegated[validator] = total_delegated[validator] + amount


def remove_pool_shares(delegator: str, validator: str, shares: decimal, amount: decimal):
    remaining_shares = delegation_shares[delegator, validator] - shares
    delegation_shares[delegator, validator] = remaining_shares
    total_shares[validator] = total_shares[validator] - shares
    total_delegated[validator] = total_delegated[validator] - amount
    if remaining_shares == 0:
        delegator_counts[validator] = delegator_counts[validator] - 1


def delegation_reward_key(delegator: str, validator: str):
    return normalize_reward_key(
        delegator, delegator_reward_keys[delegator, validator]
    )


def pending_delegator_reward(delegator: str, validator: str):
    shares = delegation_shares[delegator, validator]
    # The debt's extra unit makes an untouched position's difference -1 unit.
    return max(shares * reward_per_share[validator] - reward_debt[delegator, validator], 0)


def settle_delegator_reward(delegator: str, validator: str):
    pending = pending_delegator_reward(delegator, validator)
    if pending <= 0:
        return 0
    assert reward_pool[validator] >= pending, "Reward pool short."
    reward_pool[validator] = reward_pool[validator] - pending
    recipient = delegation_reward_key(delegator, validator)
    currency.transfer(pending, recipient)
    DelegatorRewardClaimedEvent(
        {
            "delegator": delegator,
            "validator": validator,
            "recipient": recipient,
            "amount": pending,
        }
    )
    return pending


def reset_reward_debt(delegator: str, validator: str):
    reward_debt[delegator, validator] = (
        delegation_shares[delegator, validator] * reward_per_share[validator]
        + REWARD_DEBT_ROUNDING
    )


def unbond_unlock_at(validator: str, unbonding_period_days: int):
    # Leaving an exited validator unlocks when its exit's unbonding ends.
    start = now
    if statuses[validator] in EXITED_STATUSES and left_at[validator] is not None:
        start = left_at[validator]
    return start + datetime.timedelta(days=unbonding_period_days)


def next_unbond_id():
    unbond_id = pending_unbond_counter.get() + 1
    pending_unbond_counter.set(unbond_id)
    return unbond_id


def track_validator(account: str):
    current_registry = validator_registry_list()
    if account in current_registry:
        return
    current_registry.append(account)
    validator_registry.set(current_registry)


def create_pending_unbond(
    owner: str,
    validator: str,
    amount: decimal,
    kind: str,
    reason: str = None,
):
    assert amount > 0, "Unbond amount <= 0"

    unbonding_period_days = config["unbonding_period_days"]
    if unbonding_period_days is None:
        unbonding_period_days = DEFAULT_UNBONDING_PERIOD_DAYS
    unlock_at = unbond_unlock_at(validator, unbonding_period_days)
    unbond_id = next_unbond_id()
    pending_unbond = {
        "id": unbond_id,
        "owner": owner,
        "validator": validator,
        "amount": amount,
        "kind": kind,
        "created_block": current_block_number(),
        "created_at": now,
        "unlock_at": unlock_at,
        "claimed": False,
    }
    if reason is not None:
        pending_unbond["reason"] = reason

    pending_unbonds[unbond_id] = pending_unbond
    current_unbond_ids = owner_pending_unbond_ids(owner)
    current_unbond_ids.append(unbond_id)
    pending_unbond_owner_ids[owner] = current_unbond_ids
    current_validator_unbond_ids = validator_pending_unbond_ids(validator)
    current_validator_unbond_ids.append(unbond_id)
    pending_unbond_validator_ids[validator] = current_validator_unbond_ids
    return pending_unbonds[unbond_id]


def ensure_candidate(account: str):
    current_candidates = candidate_list()
    if account not in current_candidates:
        require_selection_capacity(account, all_validator_accounts())
        current_candidates.append(account)
        candidates.set(current_candidates)


def is_known_validator(account: str):
    return (
        account in active_nodes_list()
        or account in candidate_list()
        or pending_registrations[account] == True
        or statuses[account] == STATUS_APPROVED
        or statuses[account] == STATUS_PENDING
        or statuses[account] == STATUS_LEAVING
    )


def has_validator_history(account: str):
    return account in validator_registry_list()


def sweep_validator_bonding_state(account: str, reason: str):
    current_self_bond = self_bond[account]
    if current_self_bond > 0:
        self_bond[account] = 0
        create_pending_unbond(
            owner=account,
            validator=account,
            amount=current_self_bond,
            kind="self_bond",
            reason=reason,
        )

    # Delegations stay in the validator's pool, which earns nothing once it
    # is inactive; each delegator undelegates when it chooses.


def all_validator_accounts():
    known_accounts = []
    for account in active_nodes_list():
        if account not in known_accounts:
            known_accounts.append(account)
    for account in candidate_list():
        if account not in known_accounts:
            known_accounts.append(account)
    return known_accounts


def require_selection_capacity(account: str, known_accounts: list):
    assert (
        account in known_accounts or len(known_accounts) < MAX_VALIDATOR_ACCOUNTS
    ), "Validator selection pool full."


def ready_for_selection(account: str, selection_epoch: int):
    return selection_epoch >= eligible_at_epoch[account]


def meets_min_bonds(account: str):
    return (
        self_bond[account] >= policy("min_self_bond")
        and total_bonded(account) >= policy("min_total_bond")
    )


def require_min_bonds(account: str):
    assert self_bond[account] >= policy("min_self_bond"), "Below the minimum self bond."
    assert total_bonded(account) >= policy("min_total_bond"), "Below the minimum total bond."


def can_be_selected(account: str, selection_mode: str, selection_epoch: int):
    if is_jailed(account):
        return False
    if meets_min_bonds(account) == False:
        return False
    return status_allows_selection(account, selection_mode, selection_epoch)


def status_allows_selection(account: str, selection_mode: str, selection_epoch: int):
    status = statuses[account]
    if pending_leave[account]:
        return status == STATUS_LEAVING and account in active_nodes_list()
    if status == STATUS_ACTIVE or status == STATUS_APPROVED:
        if status == STATUS_ACTIVE:
            return True
        return ready_for_selection(account, selection_epoch)

    if (
        selection_mode == "auto_top_n"
        and pending_registrations[account] == True
        and ready_for_selection(account, selection_epoch)
    ):
        return True

    return False


def insert_ranked_account(ranked_accounts: list, account: str):
    account_bond = total_bonded(account)
    next_ranked_accounts = []
    inserted = False

    for ranked_account in ranked_accounts:
        ranked_bond = total_bonded(ranked_account)
        if inserted == False:
            if account_bond > ranked_bond:
                next_ranked_accounts.append(account)
                inserted = True
            elif account_bond == ranked_bond and account < ranked_account:
                next_ranked_accounts.append(account)
                inserted = True

        next_ranked_accounts.append(ranked_account)

    if inserted == False:
        next_ranked_accounts.append(account)

    return next_ranked_accounts


def ranked_selection_candidates(selection_mode: str, selection_epoch: int):
    ranked_accounts = []
    for account in all_validator_accounts():
        if can_be_selected(account, selection_mode, selection_epoch):
            ranked_accounts = insert_ranked_account(ranked_accounts, account)
    return ranked_accounts


def weakest_ranked_account(accounts: list):
    weakest_account = None
    for account in accounts:
        if weakest_account is None:
            weakest_account = account
        elif total_bonded(account) < total_bonded(weakest_account):
            weakest_account = account
        elif (
            total_bonded(account) == total_bonded(weakest_account)
            and account > weakest_account
        ):
            weakest_account = account
    return weakest_account


def weakest_selected_incumbent(accounts: list, previous_active: list):
    incumbent_accounts = []
    for account in accounts:
        if account in previous_active:
            incumbent_accounts.append(account)
    return weakest_ranked_account(incumbent_accounts)


def beats_margin(challenger: str, incumbent: str):
    margin_bps = policy("min_bond_margin_bps")
    challenger_bond = total_bonded(challenger)
    incumbent_bond = total_bonded(incumbent)
    return challenger_bond * 10000 > incumbent_bond * (10000 + margin_bps)


def selected_validator_power(account: str):
    power_mode = policy("power_mode")
    if power_mode == "requested":
        return effective_requested_power(account)
    if power_mode == "stake_weighted":
        weighted_power = int(total_bonded(account))
        if weighted_power <= 0:
            return 1
        if weighted_power > MAX_VALIDATOR_POWER:
            return MAX_VALIDATOR_POWER
        return weighted_power
    return DEFAULT_VALIDATOR_POWER


def approve_candidate(account: str, power: int):
    assert pending_registrations[account] == True, "Member must have pending registration."
    assert is_jailed(account) == False, "Jailed."

    track_validator(account)
    pending_registrations[account] = False
    pending_leave[account] = False
    statuses[account] = STATUS_APPROVED
    left_at[account] = None
    eligible_at_epoch[account] = (
        current_selection_epoch() + policy("activation_delay_epochs")
    )
    ensure_candidate(account)

    requested_power[account] = power
    reward_keys[account] = effective_reward_key(account)
    return validator_record(account)


def newcomer_power_admitted():
    if admission_epoch.get() != current_selection_epoch():
        return 0
    return admitted_new_power.get()


def record_admitted_power(power: int):
    admitted = newcomer_power_admitted()
    admission_epoch.set(current_selection_epoch())
    admitted_new_power.set(admitted + power)


def within_new_power_cap(accounts: list, previous_active: list):
    # Newcomers' share of the set's power, with those admitted earlier this
    # epoch, stays within max_new_power_bps.
    total_power = 0
    new_power = newcomer_power_admitted()
    for account in accounts:
        power = selected_validator_power(account)
        total_power += power
        if account not in previous_active:
            new_power += power
    return new_power * 10000 <= policy("max_new_power_bps") * total_power


def fill_empty_seats(
    selected_accounts: list,
    ranked_accounts: list,
    previous_active: list,
    max_validators: int,
    churn_budget: int,
):
    # Newcomers fill empty seats and replace incumbents within one churn
    # budget, so no rebalance can hand most of the set to fresh accounts.
    for account in ranked_accounts:
        if churn_budget <= 0 or len(selected_accounts) >= max_validators:
            break
        if account in previous_active:
            continue
        candidate_set = insert_ranked_account(selected_accounts, account)
        if within_new_power_cap(candidate_set, previous_active) == False:
            continue
        selected_accounts = candidate_set
        churn_budget -= 1
    return selected_accounts, churn_budget


def replace_incumbents(
    selected_accounts: list,
    ranked_accounts: list,
    previous_active: list,
    deactivated: list,
    churn_budget: int,
):
    # A challenger replaces the weakest incumbent when it beats it by the
    # margin, within the churn budget and the newcomer power cap.
    for challenger in ranked_accounts:
        if churn_budget <= 0:
            break
        if challenger in previous_active or challenger in selected_accounts:
            continue
        weakest_incumbent = weakest_selected_incumbent(selected_accounts, previous_active)
        if weakest_incumbent is None:
            break
        if beats_margin(challenger, weakest_incumbent) == False:
            continue
        candidate_set = insert_ranked_account(
            without_item(selected_accounts, weakest_incumbent), challenger
        )
        if within_new_power_cap(candidate_set, previous_active) == False:
            continue
        selected_accounts = candidate_set
        if weakest_incumbent not in deactivated:
            deactivated.append(weakest_incumbent)
        churn_budget -= 1
    return selected_accounts


def rebalance_validator_set(force: bool = False, require_selection: bool = True):
    selection_mode = policy("selection_mode")
    assert selection_mode != "manual", "Auto selection disabled."
    selection_epoch = current_selection_epoch()
    previous_rebalance_epoch = last_rebalance_epoch.get()

    if force == False and previous_rebalance_epoch is not None:
        assert selection_epoch > previous_rebalance_epoch, "Already rebalanced."

    known_accounts = all_validator_accounts()
    ranked_accounts = ranked_selection_candidates(selection_mode, selection_epoch)
    selected_accounts = []
    deactivated = []
    previous_active = active_nodes_list()
    next_candidates = []
    max_validators = policy("max_validators")
    replacement_budget = policy("max_active_set_churn")

    for account in previous_active:
        if account in ranked_accounts:
            selected_accounts = insert_ranked_account(selected_accounts, account)
        else:
            deactivated.append(account)

    overflow = len(selected_accounts) - max_validators
    if overflow > 0:
        for trim_index in range(overflow):
            weakest_active = weakest_ranked_account(selected_accounts)
            selected_accounts = without_item(selected_accounts, weakest_active)
            if weakest_active not in deactivated:
                deactivated.append(weakest_active)

    selected_accounts, replacement_budget = fill_empty_seats(
        selected_accounts, ranked_accounts, previous_active, max_validators, replacement_budget
    )

    if len(selected_accounts) >= max_validators and replacement_budget > 0:
        selected_accounts = replace_incumbents(
            selected_accounts, ranked_accounts, previous_active, deactivated, replacement_budget
        )

    if len(selected_accounts) == 0:
        # An empty set would leave no members able to govern recovery.
        assert require_selection == False, "Rebalance would leave no active validators."
        last_rebalance_epoch.set(selection_epoch)
        return {
            "mode": selection_mode,
            "epoch": selection_epoch,
            "previous_active": previous_active,
            "selected": previous_active,
            "ranked_candidates": ranked_accounts,
            "activated": [],
            "deactivated": [],
            "retained": True,
        }

    activated = []
    new_power = 0
    for account in known_accounts:
        if account in selected_accounts:
            if account not in previous_active:
                activated.append(account)
                start_active_stint(account)
                new_power += selected_validator_power(account)
            pending_registrations[account] = False
            if not pending_leave[account]:
                statuses[account] = STATUS_ACTIVE
            left_at[account] = None
            eligible_at_epoch[account] = selection_epoch
            reward_keys[account] = effective_reward_key(account)
            requested_power[account] = effective_requested_power(account)
            powers[account] = selected_validator_power(account)
        else:
            if statuses[account] == STATUS_ACTIVE:
                statuses[account] = STATUS_APPROVED

            if pending_registrations[account] == True:
                next_candidates.append(account)
            elif statuses[account] == STATUS_APPROVED:
                next_candidates.append(account)

            if account in previous_active or statuses[account] == STATUS_APPROVED:
                powers[account] = 0

    active_validators.set(selected_accounts)
    candidates.set(next_candidates)
    last_rebalance_epoch.set(selection_epoch)
    if new_power > 0:
        record_admitted_power(new_power)
    require_total_power_within_limit()

    return {
        "mode": selection_mode,
        "epoch": selection_epoch,
        "previous_active": previous_active,
        "selected": selected_accounts,
        "ranked_candidates": ranked_accounts,
        "activated": activated,
        "deactivated": deactivated,
        "retained": False,
    }


def validator_record(account: str):
    active = account in active_nodes_list()
    unbond_count = 0
    unbond_total = 0
    next_unbond_unlock_at = None
    for unbond_id in validator_pending_unbond_ids(account):
        pending_unbond = pending_unbonds[unbond_id]
        if pending_unbond is None or pending_unbond["claimed"] == True:
            continue
        unbond_count += 1
        unbond_total += pending_unbond["amount"]
        unlock_at = pending_unbond["unlock_at"]
        if next_unbond_unlock_at is None or unlock_at < next_unbond_unlock_at:
            next_unbond_unlock_at = unlock_at

    previous_rebalance_epoch = last_rebalance_epoch.get()
    selection_epoch = previous_rebalance_epoch
    if selection_epoch is None:
        selection_epoch = 0

    return {
        "account": account,
        "status": statuses[account],
        "active": active,
        "jailed": is_jailed(account),
        "jail_reason": normalize_jail_reason(jail_reasons[account]),
        "last_jailed_at": last_jailed_at[account],
        "last_unjailed_at": last_unjailed_at[account],
        "total_slashed": total_slashed[account],
        "last_slashed_at": last_slashed_at[account],
        "last_evidence_id": last_evidence_ids[account],
        "last_evidence_type": last_evidence_types[account],
        "last_evidence_height": last_evidence_heights[account],
        "last_evidence_at": last_evidence_at[account],
        "power": effective_active_power(account),
        "requested_power": effective_requested_power(account),
        "reward_key": effective_reward_key(account),
        "moniker": monikers[account],
        "network_endpoint": network_endpoints[account],
        "metadata_uri": metadata_uris[account],
        "bond": holdings[account],
        "registration_bond": holdings[account],
        "self_bond": self_bond[account],
        "total_delegated": total_delegated[account],
        "total_bond": total_bonded(account),
        "commission_bps": effective_commission_bps(account),
        "total_shares": total_shares[account],
        "delegator_count": delegator_counts[account],
        "reward_per_share": reward_per_share[account],
        "reward_pool": reward_pool[account],
        "missed_blocks": missed_blocks[account],
        "pending_unbond_count": unbond_count,
        "pending_unbond_total": unbond_total,
        "next_unbond_unlock_at": next_unbond_unlock_at,
        "pending_registration": pending_registrations[account] == True,
        "pending_leave_at": pending_leave[account],
        "last_rebalance_epoch": previous_rebalance_epoch,
        "eligible_at_epoch": eligible_at_epoch[account],
        "selection_eligible_at_last_rebalance": can_be_selected(
            account,
            policy("selection_mode"),
            selection_epoch,
        ),
        "registered_at": registered_at[account],
        "joined_at": joined_at[account],
        "left_at": left_at[account],
    }


def ceil_div(value: int, divisor: int):
    return (value + divisor - 1) // divisor


def total_member_weight_internal():
    total = 0
    for node in active_nodes_list():
        total += effective_active_power(node)
    return total


def require_total_power_within_limit():
    assert (
        total_member_weight_internal() <= MAX_TOTAL_VOTING_POWER
    ), "Total validator power exceeds the consensus maximum."


def is_last_active_validator(account: str):
    current_nodes = active_nodes_list()
    return len(current_nodes) == 1 and account in current_nodes


def require_not_last_active_validator(account: str):
    assert (
        is_last_active_validator(account) == False
    ), "Cannot remove the last active validator."


def required_yes_weight(total_weight: int):
    assert total_weight > 0, "No voting weight."
    return ceil_div(
        total_weight * PASS_THRESHOLD_NUMERATOR,
        PASS_THRESHOLD_DENOMINATOR,
    )


def required_yes_votes(member_count: int):
    assert member_count > 0, "No validators."
    return ceil_div(
        member_count * PASS_THRESHOLD_NUMERATOR,
        PASS_THRESHOLD_DENOMINATOR,
    )


def snapshot_vote_weights(proposal_id: int):
    total_weight = 0
    for node in active_nodes_list():
        weight = effective_active_power(node)
        vote_weights[proposal_id, node] = weight
        total_weight += weight
    return total_weight


def active_member_snapshot():
    snapshot = []
    for node in active_nodes_list():
        snapshot.append(node)
    return snapshot


def store_vote_record(proposal_id: int, voter: str, vote: str, weight: int):
    vote_records[proposal_id, voter] = vote
    current_vote = votes[proposal_id]
    ValidatorProposalVotedEvent(
        {
            "proposal_id": proposal_id,
            "voter": voter,
            "vote": vote,
            "weight": weight,
            "yes_votes": current_vote["yes"],
            "no_votes": current_vote["no"],
            "yes_weight": current_vote["yes_weight"],
            "no_weight": current_vote["no_weight"],
        }
    )


def update_profile_fields(
    account: str,
    reward_key: str = None,
    requested_validator_power: int = None,
    commission_bps_value: int = None,
    moniker: str = None,
    network_endpoint: str = None,
    metadata_uri: str = None,
):
    if reward_key is not None:
        reward_keys[account] = normalize_reward_key(account, reward_key)

    if requested_validator_power is not None:
        requested_power[account] = require_validator_power(requested_validator_power)

    if commission_bps_value is not None:
        assert commission_bps_value >= 0, "Commission < 0"
        max_commission = config["max_commission_bps"]
        if max_commission is None:
            max_commission = MAX_COMMISSION_BPS
        assert commission_bps_value <= max_commission, "Commission too high."
        commission_bps[account] = commission_bps_value

    if moniker is not None:
        monikers[account] = moniker

    if network_endpoint is not None:
        network_endpoints[account] = network_endpoint

    if metadata_uri is not None:
        metadata_uris[account] = metadata_uri


def start_active_stint(account: str):
    # A missed-block count from an earlier stint (an evidence or governance
    # jail keeps it) must not shorten the downtime window of this one.
    joined_at[account] = now
    missed_blocks[account] = 0


def activate_member(account: str, power: int):
    require_selection_capacity(account, all_validator_accounts())
    track_validator(account)
    current_nodes = active_nodes_list()
    if account not in current_nodes:
        current_nodes.append(account)
        active_validators.set(current_nodes)

    current_candidates = candidate_list()
    if account in current_candidates:
        candidates.set(without_item(current_candidates, account))

    pending_registrations[account] = False
    pending_leave[account] = False
    statuses[account] = STATUS_ACTIVE
    start_active_stint(account)
    left_at[account] = None
    eligible_at_epoch[account] = 0

    requested_power[account] = power
    powers[account] = power
    reward_keys[account] = effective_reward_key(account)
    require_total_power_within_limit()


def refund_validator_bond(account: str):
    held_balance = holdings[account]
    if held_balance > 0:
        currency.transfer(held_balance, effective_reward_key(account))
        holdings[account] = 0


def deactivate_member(account: str, status: str, refund_bond: bool):
    active_validators.set(without_item(active_nodes_list(), account))
    pending_leave[account] = False
    statuses[account] = status
    left_at[account] = now
    powers[account] = 0

    if refund_bond:
        refund_validator_bond(account)


def exit_validator(account: str, status: str, refund_bond: bool):
    if account in active_nodes_list():
        deactivate_member(account, status, refund_bond)
    else:
        pending_leave[account] = False
        statuses[account] = status
        left_at[account] = now
        powers[account] = 0
        if refund_bond:
            refund_validator_bond(account)

    pending_registrations[account] = False
    candidates.set(without_item(candidate_list(), account))
    sweep_validator_bonding_state(account, status)


def jail_validator(account: str, reason: str = None):
    assert is_known_validator(account), "Unknown validator."
    assert is_jailed(account) == False, "Already jailed."

    jailed[account] = True
    jail_reasons[account] = normalize_jail_reason(reason)
    last_jailed_at[account] = now
    pending_leave[account] = False
    powers[account] = 0

    if account in active_nodes_list():
        active_validators.set(without_item(active_nodes_list(), account))
        statuses[account] = STATUS_APPROVED
        left_at[account] = now
        ensure_candidate(account)
        return

    if statuses[account] == STATUS_LEAVING:
        statuses[account] = STATUS_APPROVED
        left_at[account] = now
        ensure_candidate(account)
        return

    if statuses[account] == STATUS_APPROVED or pending_registrations[account] == True:
        ensure_candidate(account)


def unjail_validator(account: str):
    assert is_jailed(account) == True, "Not jailed."

    jailed[account] = False
    jail_reasons[account] = None
    last_unjailed_at[account] = now

    if account in active_nodes_list():
        return

    if pending_registrations[account] == True or statuses[account] == STATUS_APPROVED:
        ensure_candidate(account)


def slashable_pending_unbond(unbond: dict, infraction_height: int):
    if unbond is None:
        return False
    if infraction_height is None:
        return False
    if unbond["claimed"] == True:
        return False
    if unbond["amount"] <= 0:
        return False

    created_block = unbond.get("created_block")
    if created_block is None:
        return False
    return infraction_height <= created_block


def slashable_bond_participants(account: str, infraction_height: int = None):
    current_self_bond = self_bond[account]
    total_slashable_bond = current_self_bond
    slash_participants = []

    if current_self_bond > 0:
        slash_participants.append(
            {"kind": "self_bond", "owner": account, "amount": current_self_bond}
        )

    pool_tokens = total_delegated[account]
    if pool_tokens > 0:
        total_slashable_bond += pool_tokens
        slash_participants.append({"kind": "delegation_pool", "amount": pool_tokens})

    for unbond_id in validator_pending_unbond_ids(account):
        pending_unbond = pending_unbonds[unbond_id]
        if slashable_pending_unbond(pending_unbond, infraction_height) == False:
            continue

        total_slashable_bond += pending_unbond["amount"]
        slash_participants.append(
            {
                "kind": "pending_unbond",
                "amount": pending_unbond["amount"],
                "unbond_id": unbond_id,
            }
        )

    return slash_participants, total_slashable_bond


def slash_validator(
    account: str,
    slash_bps: int,
    reason: str = None,
    infraction_height: int = None,
):
    assert has_validator_history(account), "Unknown validator."
    assert slash_bps > 0, "Slash bps <= 0"
    assert slash_bps <= 10000, "Slash bps > 10000"

    slash_participants, total_slashable_bond = slashable_bond_participants(
        account, infraction_height
    )
    assert total_slashable_bond > 0, "No slashable stake."

    slash_rate = slash_bps / 10000
    slash_amount = total_slashable_bond * slash_rate
    processed_bond = 0
    allocated_slash = 0
    self_bond_slashed = 0
    delegated_slashed = 0
    pending_unbond_slashed = 0

    # Differences of cumulative targets conserve the slash without charging
    # a final participant more than their stake when tiny products round to zero.
    for participant in slash_participants:
        processed_bond += participant["amount"]
        cumulative_slash = processed_bond * slash_rate
        participant_slash = cumulative_slash - allocated_slash
        allocated_slash = cumulative_slash

        if participant["kind"] == "self_bond":
            self_bond[account] = self_bond[account] - participant_slash
            self_bond_slashed = participant_slash
            continue

        if participant["kind"] == "pending_unbond":
            unbond_id = participant["unbond_id"]
            pending_unbond = pending_unbonds[unbond_id]
            pending_unbond["amount"] = pending_unbond["amount"] - participant_slash
            pending_unbonds[unbond_id] = pending_unbond
            pending_unbond_slashed += participant_slash
            continue

        # Lowers every share's value; shares and earned rewards are untouched.
        total_delegated[account] = total_delegated[account] - participant_slash
        delegated_slashed += participant_slash

    total_slashed[account] = total_slashed[account] + slash_amount
    last_slashed_at[account] = now

    slash_destination = policy("slash_destination")
    if slash_amount > 0:
        currency.transfer(slash_amount, slash_destination)

    return {
        "member": account,
        "slash_bps": slash_bps,
        "slash_amount": slash_amount,
        "self_bond_slashed": self_bond_slashed,
        "delegated_slashed": delegated_slashed,
        "pending_unbond_slashed": pending_unbond_slashed,
        "destination": slash_destination,
        "reason": normalize_reason(reason),
        "slashed_at": now,
        "remaining_self_bond": self_bond[account],
        "remaining_total_delegated": total_delegated[account],
        "remaining_total_bond": total_bonded(account),
    }


def apply_evidence_penalty_internal(
    account: str,
    infraction_type: str,
    evidence_id: str,
    evidence_height: int = None,
):
    assert evidence_id is not None, "Missing evidence_id."
    assert evidence_id != "", "Missing evidence_id."

    if processed_evidence[evidence_id] == True:
        return {
            "applied": False,
            "duplicate": True,
            "member": account,
            "infraction_type": infraction_type,
            "evidence_id": evidence_id,
        }

    processed_evidence[evidence_id] = True
    last_evidence_ids[account] = evidence_id
    last_evidence_types[account] = infraction_type
    last_evidence_heights[account] = evidence_height
    last_evidence_at[account] = now

    slash_bps = evidence_slash_bps(infraction_type)
    should_jail = evidence_should_jail(infraction_type)
    slash_result = None
    jailed_now = False
    state_changed = False
    reason = infraction_type.lower()

    if slash_bps > 0:
        slash_participants, total_slashable_bond = slashable_bond_participants(
            account,
            evidence_height,
        )
        if len(slash_participants) > 0 and total_slashable_bond > 0:
            slash_result = slash_validator(
                account,
                slash_bps,
                reason,
                evidence_height,
            )
            state_changed = True

    if (
        should_jail
        and is_jailed(account) == False
        and is_known_validator(account)
        and is_last_active_validator(account) == False
    ):
        jail_validator(account, reason)
        jailed_now = True
        state_changed = True

    if state_changed and policy("selection_mode") != "manual":
        rebalance_validator_set(force=True, require_selection=False)

    return {
        "applied": state_changed,
        "duplicate": False,
        "member": account,
        "infraction_type": infraction_type,
        "evidence_id": evidence_id,
        "evidence_height": evidence_height,
        "slash_bps": slash_bps,
        "jail": should_jail,
        "jailed_now": jailed_now,
        "slash_result": slash_result,
    }


def validate_manual_override_policy(type_of_vote: str):
    selection_mode = policy("selection_mode")
    if selection_mode == "manual":
        return

    if type_of_vote == "add_member":
        assert selection_mode == "hybrid", "Hybrid only."
        return

    if (
        type_of_vote == "remove_member"
        or type_of_vote == "set_member_power"
        or type_of_vote == "jail_member"
        or type_of_vote == "unjail_member"
    ):
        assert (
            policy("manual_override_enabled") == True
        ), "Overrides off."


def validate_vote_argument(type_of_vote: str, arg: Any):
    if type_of_vote == "add_member":
        validate_non_empty_string(arg, "Member")
        validate_manual_override_policy(type_of_vote)
        if policy("selection_mode") == "manual":
            assert (
                pending_registrations[arg] == True or statuses[arg] == STATUS_APPROVED
            ), "Member must have pending registration."
        else:
            assert pending_registrations[arg] == True, "Member must have pending registration."
        assert is_jailed(arg) == False, "Jailed."
        require_min_bonds(arg)

    if type_of_vote == "remove_member":
        validate_non_empty_string(arg, "Member")
        validate_manual_override_policy(type_of_vote)
        assert arg in active_nodes_list(), "Active only."
        require_not_last_active_validator(arg)

    if type_of_vote == "jail_member":
        validate_object_argument(arg, ["member", "reason"], ["member"])
        validate_manual_override_policy(type_of_vote)
        member = arg["member"]
        validate_non_empty_string(member, "Member")
        validate_optional_string(arg.get("reason"), "Reason")
        assert arg.get("reason") != "downtime", "The downtime reason is reserved."
        assert is_known_validator(member), "Unknown validator."
        assert is_jailed(member) == False, "Already jailed."
        require_not_last_active_validator(member)

    if type_of_vote == "unjail_member":
        validate_non_empty_string(arg, "Member")
        validate_manual_override_policy(type_of_vote)
        assert is_jailed(arg) == True, "Not jailed."

    if type_of_vote == "slash_member":
        validate_object_argument(
            arg,
            ["member", "slash_bps", "reason", "infraction_height"],
            ["member", "slash_bps"],
        )
        member = arg["member"]
        slash_bps = arg["slash_bps"]
        infraction_height = arg.get("infraction_height")
        validate_non_empty_string(member, "Member")
        assert is_integer(slash_bps), "Slash bps must be an integer."
        validate_optional_string(arg.get("reason"), "Reason")
        if infraction_height is not None:
            assert is_integer(infraction_height), "Infraction height must be an integer."
            assert infraction_height >= 0, "Infraction height < 0"
        assert has_validator_history(member), "Unknown validator."
        assert slash_bps > 0, "Slash bps <= 0"
        assert slash_bps <= 10000, "Slash bps > 10000"
        slash_participants, total_slashable_bond = slashable_bond_participants(
            member,
            infraction_height,
        )
        assert len(slash_participants) > 0, "No slashable stake."
        assert total_slashable_bond > 0, "No slashable stake."

    if type_of_vote == "set_member_power":
        validate_object_argument(arg, ["member", "power"], ["member", "power"])
        validate_manual_override_policy(type_of_vote)
        member = arg["member"]
        power = arg["power"]
        validate_non_empty_string(member, "Member")
        assert is_integer(power), "Power must be an integer."
        assert member in active_nodes_list(), "Active only."
        assert power > 0, "Power <= 0"
        require_validator_power(power)

    if type_of_vote == "update_policy":
        validate_policy_update(arg)

    if type_of_vote == "change_registration_fee":
        assert is_number(arg), "Registration fee must be numeric."
        assert arg > 0, "Registration fee <= 0"

    if type_of_vote == "reward_change":
        assert isinstance(arg, list), "Reward split must be a list."
        assert len(arg) == 4, "Reward split must have 4 values."
        for value in arg:
            assert is_number(value), "Reward split values must be numeric."
            assert value >= 0, "Reward split values must be non-negative."
        assert sum(arg) == 1, "Reward split must sum to 1."

    if type_of_vote == "dao_payout":
        validate_object_argument(
            arg,
            ["contract_name", "amount", "to"],
            ["contract_name", "amount", "to"],
        )
        validate_non_empty_string(arg["contract_name"], "Contract name")
        assert importlib.exists(arg["contract_name"]), "DAO contract does not exist."
        assert is_number(arg["amount"]), "DAO amount must be numeric."
        assert arg["amount"] > 0, "DAO amount must be positive."
        validate_non_empty_string(arg["to"], "DAO recipient")

    if type_of_vote == "chi_cost_change":
        assert is_integer(arg), "Chi cost must be an integer."
        assert arg > 0, "Chi cost must be positive."
        assert arg <= chi_cost.max_value(), (
            "Chi cost exceeds the largest rate the node can price with."
        )

    if type_of_vote == "change_types":
        assert isinstance(arg, list), "Vote types must be a list."
        assert len(arg) > 0, "Vote types must not be empty."
        seen_types = []
        for vote_type in arg:
            validate_non_empty_string(vote_type, "Vote type")
            assert vote_type not in seen_types, "Duplicate vote type."
            seen_types.append(vote_type)
        for recovery_vote_type in recovery_vote_types():
            assert recovery_vote_type in seen_types, (
                "Missing recovery vote type: " + recovery_vote_type
            )

    if type_of_vote == "topic_vote":
        validate_object_argument(arg, ["topic"], ["topic"])
        validate_non_empty_string(arg["topic"], "Topic")


def validate_policy_update(arg: Any):
    validate_object_argument(arg, POLICY_KEYS, [])
    assert len(arg) > 0, "Policy update must not be empty."
    for key in POLICY_KEYS:
        if arg.get(key) is not None:
            validate_policy_value(key, arg[key])


def apply_policy_update(arg: Any):
    for key in POLICY_KEYS:
        if arg.get(key) is not None:
            config[key] = arg[key]


@export
def propose_vote(type_of_vote: str, arg: Any):
    assert ctx.caller in active_nodes_list(), "Validators only."
    assert type_of_vote in types.get(), "Invalid type."
    validate_vote_argument(type_of_vote, arg)

    proposal_id = total_votes.get() + 1
    total_votes.set(proposal_id)

    total_weight_snapshot = snapshot_vote_weights(proposal_id)
    proposer_weight = vote_weights[proposal_id, ctx.caller]
    member_snapshot = active_member_snapshot()

    votes[proposal_id] = {
        "yes": 1,
        "no": 0,
        "yes_weight": proposer_weight,
        "no_weight": 0,
        "type": type_of_vote,
        "arg": arg,
        "voters": [ctx.caller],
        "finalized": False,
        "status": STATUS_PENDING,
        "created_at": now,
        "expiry": now + datetime.timedelta(days=PROPOSAL_EXPIRY_DAYS),
        "member_snapshot": member_snapshot,
        "member_count_snapshot": len(member_snapshot),
        "total_weight_snapshot": total_weight_snapshot,
        "required_yes_votes": required_yes_votes(len(member_snapshot)),
        "required_yes_weight": required_yes_weight(total_weight_snapshot),
    }

    ValidatorProposalSubmittedEvent(
        {
            "proposal_id": proposal_id,
            "type_of_vote": type_of_vote,
            "proposer": ctx.caller,
            "status": STATUS_PENDING,
        }
    )
    if type_of_vote == "add_member":
        # Voters approve this power; later registration edits cannot change it.
        current_vote = votes[proposal_id]
        current_vote["member_power"] = effective_requested_power(arg)
        votes[proposal_id] = current_vote

    store_vote_record(proposal_id, ctx.caller, "yes", proposer_weight)
    decide_finalize(proposal_id)
    return votes[proposal_id]


@export
def vote(proposal_id: int, vote: str):
    assert votes[proposal_id], "Invalid proposal."
    assert votes[proposal_id]["finalized"] == False, "Proposal already finalized."
    assert now < votes[proposal_id]["expiry"], "Proposal expired."
    assert vote in ["yes", "no"], "Invalid vote."
    assert ctx.caller not in votes[proposal_id]["voters"], "Already voted."

    voter_weight = vote_weights[proposal_id, ctx.caller]
    assert voter_weight > 0, "Not eligible to vote on this proposal."

    current_vote = votes[proposal_id]
    current_vote[vote] += 1

    if vote == "yes":
        current_vote["yes_weight"] += voter_weight
    else:
        current_vote["no_weight"] += voter_weight

    current_vote["voters"].append(ctx.caller)
    votes[proposal_id] = current_vote

    store_vote_record(proposal_id, ctx.caller, vote, voter_weight)
    decide_finalize(proposal_id)
    return votes[proposal_id]


@export
def expire_vote(proposal_id: int):
    assert votes[proposal_id], "Invalid proposal."
    assert votes[proposal_id]["finalized"] == False, "Proposal already finalized."
    assert now >= votes[proposal_id]["expiry"], "Proposal has not expired."

    current_vote = votes[proposal_id]
    current_vote["finalized"] = True
    current_vote["status"] = STATUS_EXPIRED
    votes[proposal_id] = current_vote
    ValidatorProposalExpiredEvent(
        {
            "proposal_id": proposal_id,
            "type_of_vote": current_vote["type"],
            "expirer": ctx.caller,
            "status": STATUS_EXPIRED,
        }
    )
    return current_vote


def decide_finalize(proposal_id: int):
    current_vote = votes[proposal_id]
    if current_vote["yes_weight"] >= current_vote["required_yes_weight"]:
        finalize_vote(proposal_id)
        return

    remaining_weight = (
        current_vote["total_weight_snapshot"]
        - current_vote["yes_weight"]
        - current_vote["no_weight"]
    )
    if current_vote["yes_weight"] + remaining_weight < current_vote["required_yes_weight"]:
        reject_vote(proposal_id)


def reject_vote(proposal_id: int):
    current_vote = votes[proposal_id]
    current_vote["finalized"] = True
    current_vote["status"] = STATUS_REJECTED
    votes[proposal_id] = current_vote
    ValidatorProposalRejectedEvent(
        {
            "proposal_id": proposal_id,
            "type_of_vote": current_vote["type"],
            "rejector": ctx.caller,
            "status": STATUS_REJECTED,
        }
    )


def can_add_member(member: str):
    if is_jailed(member):
        return False
    if meets_min_bonds(member) == False:
        return False
    if pending_registrations[member] == True:
        return True
    return policy("selection_mode") == "manual" and statuses[member] == STATUS_APPROVED


def can_jail_member(member: str):
    return (
        is_known_validator(member)
        and is_jailed(member) == False
        and is_last_active_validator(member) == False
    )


def can_remove_member(member: str):
    return member in active_nodes_list() and is_last_active_validator(member) == False


def proposal_still_applies(current_vote: dict):
    # Validator state may change between proposal and finalization.
    vote_type = current_vote["type"]
    if vote_type == "add_member":
        return can_add_member(current_vote["arg"])
    if vote_type == "remove_member":
        return can_remove_member(current_vote["arg"])
    if vote_type == "jail_member":
        return can_jail_member(current_vote["arg"]["member"])
    return True


def finalize_vote(proposal_id: int):
    current_vote = votes[proposal_id]
    if proposal_still_applies(current_vote) == False:
        reject_vote(proposal_id)
        return votes[proposal_id]

    if current_vote["type"] == "add_member":
        member = current_vote["arg"]
        member_power = current_vote["member_power"]
        if policy("selection_mode") == "manual":
            activate_member(member, member_power)
        else:
            approve_candidate(member, member_power)
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "remove_member":
        exit_validator(current_vote["arg"], STATUS_REMOVED, True)
        if policy("selection_mode") != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "jail_member":
        jail_validator(
            current_vote["arg"]["member"],
            current_vote["arg"].get("reason"),
        )
        if policy("selection_mode") != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "unjail_member":
        unjail_validator(current_vote["arg"])
        if policy("selection_mode") != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "slash_member":
        current_vote["result"] = slash_validator(
            current_vote["arg"]["member"],
            current_vote["arg"]["slash_bps"],
            current_vote["arg"].get("reason"),
            current_vote["arg"].get("infraction_height"),
        )
        if policy("selection_mode") != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "set_member_power":
        member = current_vote["arg"]["member"]
        power = current_vote["arg"]["power"]
        requested_power[member] = power
        if policy("selection_mode") == "manual":
            powers[member] = power
            require_total_power_within_limit()
        elif policy("power_mode") == "requested":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "update_policy":
        apply_policy_update(current_vote["arg"])
        if policy("selection_mode") != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "reward_change":
        rewards.set_value(new_value=current_vote["arg"])
    elif current_vote["type"] == "dao_payout":
        dao.transfer_from_dao(args=current_vote["arg"])
    elif current_vote["type"] == "chi_cost_change":
        chi_cost.set_value(new_value=current_vote["arg"])
    elif current_vote["type"] == "change_registration_fee":
        registration_fee.set(current_vote["arg"])
    elif current_vote["type"] == "change_types":
        types.set(current_vote["arg"])

    current_vote["finalized"] = True
    current_vote["status"] = STATUS_APPROVED
    votes[proposal_id] = current_vote
    ValidatorProposalApprovedEvent(
        {
            "proposal_id": proposal_id,
            "type_of_vote": current_vote["type"],
            "approver": ctx.caller,
            "status": STATUS_APPROVED,
        }
    )
    return current_vote


@export
def get_vote(proposal_id: int):
    assert votes[proposal_id], "Invalid proposal."
    return votes[proposal_id]


@export
def get_vote_record(proposal_id: int, voter: str):
    assert votes[proposal_id], "Invalid proposal."
    return {
        "proposal_id": proposal_id,
        "voter": voter,
        "vote": vote_records[proposal_id, voter],
        "weight": vote_weights[proposal_id, voter],
    }


@export
def get_vote_weight(proposal_id: int, voter: str):
    assert votes[proposal_id], "Invalid proposal."
    return vote_weights[proposal_id, voter]


@export
def get_vote_voter_snapshot(proposal_id: int):
    assert votes[proposal_id], "Invalid proposal."
    snapshot = votes[proposal_id].get("member_snapshot")
    if snapshot is None:
        return []
    return snapshot


@export
def get_vote_records(proposal_id: int):
    assert votes[proposal_id], "Invalid proposal."
    records = []
    for voter in get_vote_voter_snapshot(proposal_id):
        records.append(
            {
                "proposal_id": proposal_id,
                "voter": voter,
                "vote": vote_records[proposal_id, voter],
                "weight": vote_weights[proposal_id, voter],
            }
        )
    return records


@export
def get_members():
    return active_nodes_list()


@export
def get_active_validators():
    validators = []
    for node in active_nodes_list():
        validators.append(validator_record(node))
    return validators


@export
def get_pending_candidates():
    current_candidates = []
    for account in candidate_list():
        current_candidates.append(validator_record(account))
    return current_candidates


@export
def get_validators():
    current_validators = []
    for account in validator_registry_list():
        current_validators.append(validator_record(account))
    return current_validators


@export
def get_validator(account: str):
    return validator_record(account)


@export
def get_policy_config():
    policy_config = {}
    for key in POLICY_KEYS:
        policy_config[key] = config[key]
    return policy_config


@export
def get_recovery_vote_types():
    return recovery_vote_types()


@export
def is_member(account: str):
    return account in active_nodes_list()


@export
def member_count():
    return len(active_nodes_list())


@export
def member_weight(account: str):
    if account not in active_nodes_list():
        return 0
    return effective_active_power(account)


@export
def total_member_weight():
    return total_member_weight_internal()


@export
def rebalance():
    return rebalance_validator_set(require_selection=False)


@export
def apply_evidence_penalty(
    member: str,
    infraction_type: str,
    evidence_id: str,
    evidence_height: int = None,
):
    assert ctx.caller == SYSTEM_EVIDENCE_CALLER, "Driver only."
    assert infraction_type == "DUPLICATE_VOTE" or infraction_type == "LIGHT_CLIENT_ATTACK", "Bad infraction."
    assert has_validator_history(member), "Unknown validator."

    return apply_evidence_penalty_internal(
        account=member,
        infraction_type=infraction_type,
        evidence_id=evidence_id,
        evidence_height=evidence_height,
    )


def active_power(accounts: list):
    total = 0
    for account in accounts:
        total += effective_active_power(account)
    return total


def jail_for_downtime(account: str):
    missed_blocks[account] = 0
    apply_evidence_penalty_internal(
        account=account,
        infraction_type="DOWNTIME",
        evidence_id="downtime-" + account + "-" + str(current_block_number()),
        evidence_height=current_block_number(),
    )


@export
def record_liveness(absent: list):
    # Called by FinalizeBlock with the validators whose signature is absent
    # from the decided last commit (when any is, or a count is open).
    assert ctx.caller == SYSTEM_LIVENESS_CALLER, "Driver only."
    members = active_nodes_list()
    absent_members = []
    for account in members:
        if account in absent:
            absent_members.append(account)
        elif missed_blocks[account] != 0:
            missed_blocks[account] = 0
    # More than a third absent is a partition, not one validator's downtime.
    partition = active_power(absent_members) * 3 > active_power(members)
    jailed_now = []
    for account in absent_members:
        missed_blocks[account] = missed_blocks[account] + 1
        if partition == False and missed_blocks[account] >= policy("downtime_jail_blocks"):
            jail_for_downtime(account)
            jailed_now.append(account)
    return {"absent": absent_members, "partition": partition, "jailed": jailed_now}


def re_enter_after_downtime(account: str):
    # Downtime is not malicious: the validator returns to the active set in
    # every mode, within the minimum stake and the epoch's newcomer budget.
    # Without a free seat it stays an approved candidate.
    require_min_bonds(account)
    members = active_nodes_list()
    if len(members) >= policy("max_validators"):
        return
    if policy("selection_mode") == "manual":
        power = effective_requested_power(account)
    else:
        power = selected_validator_power(account)
    admitted = newcomer_power_admitted() + power
    assert (
        admitted * 10000 <= policy("max_new_power_bps") * (active_power(members) + power)
    ), "Newcomer power cap reached; retry next epoch."
    record_admitted_power(power)
    activate_member(account, power)


@export
def unjail():
    account = ctx.caller
    assert is_jailed(account), "Not jailed."
    assert jail_reasons[account] == "downtime", "Only a downtime jail can be lifted by the validator."
    cooldown = datetime.timedelta(hours=policy("downtime_unjail_cooldown_hours"))
    assert now >= last_jailed_at[account] + cooldown, "Unjail cooldown not over."
    unjail_validator(account)
    # Exiting registration refunds its fee and frees its slot. Lifting a
    # downtime jail must not undo that exit or bypass fresh registration.
    if statuses[account] == STATUS_APPROVED:
        re_enter_after_downtime(account)
    return validator_record(account)


@export
def update_profile(
    reward_key: str = None,
    commission_bps_value: int = None,
    moniker: str = None,
    network_endpoint: str = None,
    metadata_uri: str = None,
):
    account = ctx.caller
    assert (
        account in active_nodes_list()
        or pending_registrations[account] == True
        or statuses[account] == STATUS_APPROVED
    ), "Profile only."

    update_profile_fields(
        account,
        reward_key=reward_key,
        requested_validator_power=None,
        commission_bps_value=commission_bps_value,
        moniker=moniker,
        network_endpoint=network_endpoint,
        metadata_uri=metadata_uri,
    )
    return validator_record(account)


@export
def update_registration(
    requested_validator_power: int,
    reward_key: str = None,
    commission_bps_value: int = None,
    moniker: str = None,
    network_endpoint: str = None,
    metadata_uri: str = None,
):
    account = ctx.caller
    assert (
        pending_registrations[account] == True
        or statuses[account] == STATUS_APPROVED
    ), "No pending registration."

    update_profile_fields(
        account,
        reward_key=reward_key,
        requested_validator_power=requested_validator_power,
        commission_bps_value=commission_bps_value,
        moniker=moniker,
        network_endpoint=network_endpoint,
        metadata_uri=metadata_uri,
    )
    return validator_record(account)


@export
def announce_leave():
    assert ctx.caller in active_nodes_list(), "Not a node."
    assert not pending_leave[ctx.caller], "Pending leave."

    pending_leave[ctx.caller] = now + datetime.timedelta(days=LEAVE_DELAY_DAYS)
    statuses[ctx.caller] = STATUS_LEAVING
    return validator_record(ctx.caller)


@export
def leave():
    pending_leave_at = pending_leave[ctx.caller]
    assert pending_leave_at, "Not pending."
    assert pending_leave_at < now, "Leave announcement period not over."
    require_not_last_active_validator(ctx.caller)

    exit_validator(ctx.caller, STATUS_LEFT, True)
    return validator_record(ctx.caller)


@export
def register(
    reward_key: str = None,
    requested_validator_power: int = DEFAULT_VALIDATOR_POWER,
    commission_bps_value: int = DEFAULT_COMMISSION_BPS,
    moniker: str = "",
    network_endpoint: str = "",
    metadata_uri: str = "",
):
    if requested_validator_power is None:
        requested_validator_power = DEFAULT_VALIDATOR_POWER
    if moniker is None:
        moniker = ""
    if network_endpoint is None:
        network_endpoint = ""
    if metadata_uri is None:
        metadata_uri = ""

    # The registering identity becomes the validator's consensus key, so it
    # must be the signing account itself, never a contract acting for it.
    assert ctx.caller == ctx.signer, "Validators must register from their own account."
    # Hex case variants verify with the same key; only one spelling may register.
    require_canonical_validator_key(ctx.caller)
    assert ctx.caller not in active_nodes_list(), "Already a node."
    assert pending_registrations[ctx.caller] == False, "Already pending."
    assert requested_validator_power > 0, "Validator power <= 0"
    assert is_jailed(ctx.caller) == False, "Jailed."

    require_selection_capacity(ctx.caller, all_validator_accounts())

    currency.transfer_from(
        amount=registration_fee.get(),
        to=ctx.this,
        main_account=ctx.caller,
    )

    track_validator(ctx.caller)
    holdings[ctx.caller] = holdings[ctx.caller] + registration_fee.get()
    pending_registrations[ctx.caller] = True
    statuses[ctx.caller] = STATUS_PENDING
    registered_at[ctx.caller] = now
    joined_at[ctx.caller] = None
    left_at[ctx.caller] = None
    if policy("selection_mode") == "manual":
        eligible_at_epoch[ctx.caller] = 0
    else:
        eligible_at_epoch[ctx.caller] = (
            current_selection_epoch() + policy("activation_delay_epochs")
        )
    pending_leave[ctx.caller] = False
    self_bond[ctx.caller] = self_bond[ctx.caller]
    total_delegated[ctx.caller] = total_delegated[ctx.caller]

    update_profile_fields(
        ctx.caller,
        reward_key=normalize_reward_key(ctx.caller, reward_key),
        requested_validator_power=requested_validator_power,
        commission_bps_value=commission_bps_value,
        moniker=moniker,
        network_endpoint=network_endpoint,
        metadata_uri=metadata_uri,
    )
    if commission_bps[ctx.caller] is None:
        commission_bps[ctx.caller] = DEFAULT_COMMISSION_BPS

    ensure_candidate(ctx.caller)

    return validator_record(ctx.caller)


@export
def unregister():
    assert ctx.caller not in active_nodes_list(), "Leave first."
    assert (
        pending_registrations[ctx.caller] == True
        or statuses[ctx.caller] == STATUS_APPROVED
    ), "No pending registration."

    exit_validator(ctx.caller, STATUS_WITHDRAWN, True)
    return validator_record(ctx.caller)


@export
def bond_self(amount: decimal):
    assert amount > 0, "Bond amount <= 0"
    # A validator jailed for downtime may top up its own bond to re-enter.
    assert (
        can_accept_delegation(ctx.caller) or jail_reasons[ctx.caller] == "downtime"
    ), "Bonding closed."

    currency.transfer_from(
        amount=amount,
        to=ctx.this,
        main_account=ctx.caller,
    )
    self_bond[ctx.caller] = self_bond[ctx.caller] + amount
    return validator_record(ctx.caller)


@export
def unbond_self(amount: decimal):
    assert amount > 0, "Bond amount <= 0"
    assert self_bond[ctx.caller] >= amount, "Not enough self bond."

    self_bond[ctx.caller] = self_bond[ctx.caller] - amount
    return create_pending_unbond(
        owner=ctx.caller,
        validator=ctx.caller,
        amount=amount,
        kind="self_bond",
    )


@export
def delegate(validator: str, amount: decimal, reward_key: str = None):
    delegator = ctx.caller
    assert amount > 0, "Delegation amount <= 0"
    assert validator != delegator, "Use bond_self."
    assert can_accept_delegation(validator), "Closed."
    shares = shares_for_amount(validator, amount)

    settle_delegator_reward(delegator, validator)
    currency.transfer_from(
        amount=amount,
        to=ctx.this,
        main_account=delegator,
    )
    add_pool_shares(delegator, validator, shares, amount)
    reset_reward_debt(delegator, validator)

    if reward_key is not None:
        delegator_reward_keys[delegator, validator] = normalize_reward_key(
            delegator, reward_key
        )
    elif delegator_reward_keys[delegator, validator] is None:
        delegator_reward_keys[delegator, validator] = delegator

    DelegatedEvent(
        {"delegator": delegator, "validator": validator, "amount": amount, "shares": shares}
    )
    return get_delegation(delegator, validator)


@export
def undelegate(validator: str, amount: decimal):
    delegator = ctx.caller
    value = delegation_value(delegator, validator)
    # A position worth nothing (a fully slashed pool) leaves with amount 0.
    assert amount > 0 or (amount == 0 and value == 0 and delegation_shares[delegator, validator] > 0), "Delegation amount <= 0"
    assert value >= amount, "Not enough delegated stake."

    settle_delegator_reward(delegator, validator)
    shares, released = released_stake(delegator, validator, amount, value)
    remove_pool_shares(delegator, validator, shares, released)
    reset_reward_debt(delegator, validator)

    UndelegatedEvent(
        {"delegator": delegator, "validator": validator, "amount": released, "shares": shares}
    )
    if released <= 0:
        return get_delegation(delegator, validator)
    return create_pending_unbond(
        owner=delegator,
        validator=validator,
        amount=released,
        kind="delegation",
    )


@export
def claim_rewards(validator: str):
    paid = settle_delegator_reward(ctx.caller, validator)
    reset_reward_debt(ctx.caller, validator)
    return paid


@export
def claim_unbond(unbond_id: int):
    unbond = pending_unbonds[unbond_id]
    assert unbond is not None, "Unknown unbond."
    assert unbond["owner"] == ctx.caller, "Not your unbond."
    assert unbond["claimed"] == False, "Unbond already claimed."
    assert now >= unbond["unlock_at"], "Unbond is still locked."

    if unbond["amount"] > 0:
        currency.transfer(unbond["amount"], ctx.caller)
    unbond["claimed"] = True
    pending_unbonds[unbond_id] = unbond
    return unbond


@export
def get_delegation(delegator: str, validator: str):
    return {
        "delegator": delegator,
        "validator": validator,
        "amount": delegation_value(delegator, validator),
        "shares": delegation_shares[delegator, validator],
        "pending_rewards": pending_delegator_reward(delegator, validator),
        "reward_key": delegation_reward_key(delegator, validator),
    }


@export
def get_pending_rewards(delegator: str, validator: str):
    return pending_delegator_reward(delegator, validator)


@export
def get_pending_unbond(unbond_id: int):
    return pending_unbonds[unbond_id]


@export
def get_pending_unbond_ids(owner: str):
    return owner_pending_unbond_ids(owner)


@export
def get_reward_distribution_info(validator: str):
    return {
        "validator": validator,
        "reward_key": effective_reward_key(validator),
        "commission_bps": effective_commission_bps(validator),
        "self_bond": self_bond[validator],
        "total_delegated": total_delegated[validator],
        "total_shares": total_shares[validator],
        "total_bond": total_bonded(validator),
        "delegator_count": delegator_counts[validator],
        "reward_per_share": reward_per_share[validator],
        "reward_pool": reward_pool[validator],
    }
