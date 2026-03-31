import dao
import rewards
import stamp_cost
import currency

nodes = Variable()
candidates = Variable()
votes = Hash(default_value=False)
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
total_delegated = Hash(default_value=0)
delegations = Hash(default_value=0)
delegator_reward_keys = Hash(default_value=None)
delegator_lists = Hash(default_value=None)
pending_unbond_counter = Variable()
pending_unbond_owner_ids = Hash(default_value=None)
pending_unbond_validator_ids = Hash(default_value=None)
pending_unbonds = Hash(default_value=None)
jailed = Hash(default_value=False)
jail_reasons = Hash(default_value=None)
total_slashed = Hash(default_value=0)
last_slashed_at = Hash(default_value=None)
processed_evidence = Hash(default_value=False)
validator_registry = Variable()

validator_power = Hash(default_value=0)
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
):
    assert default_node_power > 0, "default_node_power <= 0"
    assert selection_mode in ["manual", "auto_top_n", "hybrid"], "Bad selection mode."
    assert max_validators > 0, "max_validators <= 0"
    assert power_mode in ["equal", "requested", "stake_weighted"], "Bad power mode."
    assert rebalance_interval > 0, "rebalance_interval <= 0"
    assert activation_delay_epochs >= 0, "activation_delay_epochs < 0"
    assert unbonding_period_days >= 0, "unbonding_period_days < 0"
    assert min_self_bond >= 0, "min_self_bond < 0"
    assert min_total_bond >= 0, "min_total_bond < 0"
    assert max_commission_bps >= 0, "max_commission_bps < 0"
    assert max_commission_bps <= MAX_COMMISSION_BPS, "max_commission_bps > 10000"
    assert max_active_set_churn >= 0, "max_active_set_churn < 0"
    assert min_bond_margin_bps >= 0, "min_bond_margin_bps < 0"
    assert slash_destination != "", "slash_destination empty"

    nodes.set([])
    candidates.set([])
    pending_unbond_counter.set(0)
    last_rebalance_epoch.set(None)
    validator_registry.set([])
    types.set(["add_member", "remove_member", "jail_member", "unjail_member", "slash_member", "set_member_power", "change_registration_fee", "reward_change", "dao_payout", "stamp_cost_change", "change_types", "update_policy", "topic_vote"])
    total_votes.set(0)
    registration_fee.set(genesis_registration_fee)
    config["selection_mode"] = selection_mode
    config["max_validators"] = max_validators
    config["power_mode"] = power_mode
    config["rebalance_interval"] = rebalance_interval
    config["activation_delay_epochs"] = activation_delay_epochs
    config["unbonding_period_days"] = unbonding_period_days
    config["min_self_bond"] = min_self_bond
    config["min_total_bond"] = min_total_bond
    config["max_commission_bps"] = max_commission_bps
    config["max_active_set_churn"] = max_active_set_churn
    config["min_bond_margin_bps"] = min_bond_margin_bps
    config["manual_override_enabled"] = manual_override_enabled
    config["slash_destination"] = slash_destination
    config["duplicate_vote_slash_bps"] = duplicate_vote_slash_bps
    config["duplicate_vote_jail"] = duplicate_vote_jail
    config["light_client_attack_slash_bps"] = light_client_attack_slash_bps
    config["light_client_attack_jail"] = light_client_attack_jail

    active_nodes = []
    for node in genesis_nodes:
        if node in active_nodes:
            continue

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
        delegator_lists[node] = []
        requested_power[node] = resolve_requested_power(
            node,
            genesis_powers,
            default_node_power,
        )
        validator_power[node] = requested_power[node]
        reward_keys[node] = resolve_reward_key(node, genesis_reward_keys)

    nodes.set(active_nodes)


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

    assert power > 0, "Validator power <= 0"
    return power


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


def normalize_delegator_reward_key(account: str, reward_key: str = None):
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


def active_nodes_list():
    current_nodes = nodes.get()
    if current_nodes is None:
        return []
    return current_nodes


def candidate_list():
    current_candidates = candidates.get()
    if current_candidates is None:
        return []
    return current_candidates


def delegator_list(validator: str):
    current_delegators = delegator_lists[validator]
    if current_delegators is None:
        return []
    return current_delegators


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
    power = validator_power[account]
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


def effective_commission_bps(account: str):
    configured_bps = commission_bps[account]
    if configured_bps is None:
        return DEFAULT_COMMISSION_BPS
    if configured_bps < 0:
        return DEFAULT_COMMISSION_BPS

    max_commission = config["max_commission_bps"]
    if max_commission is None:
        max_commission = MAX_COMMISSION_BPS
    if configured_bps > max_commission:
        return max_commission

    return configured_bps


def effective_selection_mode():
    selection_mode = config["selection_mode"]
    if selection_mode is None:
        return DEFAULT_SELECTION_MODE
    return selection_mode


def effective_max_validators():
    max_validators = config["max_validators"]
    if max_validators is None:
        return DEFAULT_MAX_VALIDATORS
    if max_validators <= 0:
        return DEFAULT_MAX_VALIDATORS
    return max_validators


def effective_power_mode():
    power_mode = config["power_mode"]
    if power_mode is None:
        return DEFAULT_POWER_MODE
    return power_mode


def effective_min_self_bond():
    min_self_bond = config["min_self_bond"]
    if min_self_bond is None:
        return DEFAULT_MIN_SELF_BOND
    if min_self_bond < 0:
        return DEFAULT_MIN_SELF_BOND
    return min_self_bond


def effective_min_total_bond():
    min_total_bond = config["min_total_bond"]
    if min_total_bond is None:
        return DEFAULT_MIN_TOTAL_BOND
    if min_total_bond < 0:
        return DEFAULT_MIN_TOTAL_BOND
    return min_total_bond


def effective_rebalance_interval():
    rebalance_interval = config["rebalance_interval"]
    if rebalance_interval is None:
        return DEFAULT_REBALANCE_INTERVAL
    if rebalance_interval <= 0:
        return DEFAULT_REBALANCE_INTERVAL
    return rebalance_interval


def effective_activation_delay_epochs():
    activation_delay_epochs = config["activation_delay_epochs"]
    if activation_delay_epochs is None:
        return DEFAULT_ACTIVATION_DELAY_EPOCHS
    if activation_delay_epochs < 0:
        return DEFAULT_ACTIVATION_DELAY_EPOCHS
    return activation_delay_epochs


def effective_max_active_set_churn():
    max_active_set_churn = config["max_active_set_churn"]
    if max_active_set_churn is None:
        return DEFAULT_MAX_ACTIVE_SET_CHURN
    if max_active_set_churn < 0:
        return DEFAULT_MAX_ACTIVE_SET_CHURN
    return max_active_set_churn


def effective_min_bond_margin_bps():
    min_bond_margin_bps = config["min_bond_margin_bps"]
    if min_bond_margin_bps is None:
        return DEFAULT_MIN_BOND_MARGIN_BPS
    if min_bond_margin_bps < 0:
        return DEFAULT_MIN_BOND_MARGIN_BPS
    return min_bond_margin_bps


def effective_manual_override_enabled():
    manual_override_enabled = config["manual_override_enabled"]
    if manual_override_enabled is None:
        return True
    return manual_override_enabled


def effective_slash_destination():
    slash_destination = config["slash_destination"]
    if slash_destination is None:
        return DEFAULT_SLASH_DESTINATION
    if slash_destination == "":
        return DEFAULT_SLASH_DESTINATION
    return slash_destination


def effective_duplicate_vote_slash_bps():
    slash_bps = config["duplicate_vote_slash_bps"]
    if slash_bps is None:
        return DEFAULT_DUPLICATE_VOTE_SLASH_BPS
    if slash_bps < 0:
        return DEFAULT_DUPLICATE_VOTE_SLASH_BPS
    return slash_bps


def effective_duplicate_vote_jail():
    should_jail = config["duplicate_vote_jail"]
    if should_jail is None:
        return True
    return should_jail


def effective_light_client_attack_slash_bps():
    slash_bps = config["light_client_attack_slash_bps"]
    if slash_bps is None:
        return DEFAULT_LIGHT_CLIENT_ATTACK_SLASH_BPS
    if slash_bps < 0:
        return DEFAULT_LIGHT_CLIENT_ATTACK_SLASH_BPS
    return slash_bps


def effective_light_client_attack_jail():
    should_jail = config["light_client_attack_jail"]
    if should_jail is None:
        return True
    return should_jail


def evidence_slash_bps(infraction_type: str):
    if infraction_type == "DUPLICATE_VOTE":
        return effective_duplicate_vote_slash_bps()
    if infraction_type == "LIGHT_CLIENT_ATTACK":
        return effective_light_client_attack_slash_bps()
    return 0


def evidence_should_jail(infraction_type: str):
    if infraction_type == "DUPLICATE_VOTE":
        return effective_duplicate_vote_jail()
    if infraction_type == "LIGHT_CLIENT_ATTACK":
        return effective_light_client_attack_jail()
    return False


def is_jailed(account: str):
    return jailed[account] == True


def current_block_number():
    current_height = block_num
    if current_height is None or current_height < 0:
        return 0
    return current_height


def current_selection_epoch():
    return current_block_number() // effective_rebalance_interval()


def total_bonded(account: str):
    return self_bond[account] + total_delegated[account]


def can_accept_delegation(account: str):
    if is_jailed(account):
        return False
    status = statuses[account]
    return status == STATUS_PENDING or status == STATUS_ACTIVE or status == STATUS_APPROVED


def add_delegator(validator: str, delegator: str):
    current_delegators = delegator_list(validator)
    if delegator in current_delegators:
        return
    current_delegators.append(delegator)
    delegator_lists[validator] = current_delegators


def remove_delegator(validator: str, delegator: str):
    current_delegators = delegator_list(validator)
    if delegator not in current_delegators:
        return
    delegator_lists[validator] = without_item(current_delegators, delegator)


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
    amount: float,
    kind: str,
    reason: str = None,
):
    assert amount > 0, "Unbond amount <= 0"

    unbonding_period_days = config["unbonding_period_days"]
    if unbonding_period_days is None:
        unbonding_period_days = DEFAULT_UNBONDING_PERIOD_DAYS
    unlock_at = now + datetime.timedelta(days=unbonding_period_days)
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

    current_delegators = delegator_list(account)
    for delegator in current_delegators:
        current_delegation = delegations[delegator, account]
        if current_delegation > 0:
            create_pending_unbond(
                owner=delegator,
                validator=account,
                amount=current_delegation,
                kind="delegation",
                reason=reason,
            )
        delegations[delegator, account] = 0

    total_delegated[account] = 0
    delegator_lists[account] = []


def all_validator_accounts():
    known_accounts = []
    for account in active_nodes_list():
        if account not in known_accounts:
            known_accounts.append(account)
    for account in candidate_list():
        if account not in known_accounts:
            known_accounts.append(account)
    return known_accounts


def ready_for_selection(account: str, selection_epoch: int):
    return selection_epoch >= eligible_at_epoch[account]


def can_be_selected(account: str, selection_mode: str, selection_epoch: int):
    if is_jailed(account):
        return False
    if pending_leave[account]:
        return False
    if self_bond[account] < effective_min_self_bond():
        return False
    if total_bonded(account) < effective_min_total_bond():
        return False

    status = statuses[account]
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
    margin_bps = effective_min_bond_margin_bps()
    challenger_bond = total_bonded(challenger)
    incumbent_bond = total_bonded(incumbent)
    return challenger_bond * 10000 > incumbent_bond * (10000 + margin_bps)


def selected_validator_power(account: str):
    power_mode = effective_power_mode()
    if power_mode == "requested":
        return effective_requested_power(account)
    if power_mode == "stake_weighted":
        weighted_power = int(total_bonded(account))
        if weighted_power <= 0:
            return 1
        return weighted_power
    return DEFAULT_VALIDATOR_POWER


def approve_candidate(account: str):
    assert pending_registrations[account] == True, "Member must have pending registration."
    assert is_jailed(account) == False, "Jailed."

    track_validator(account)
    pending_registrations[account] = False
    pending_leave[account] = False
    statuses[account] = STATUS_APPROVED
    left_at[account] = None
    eligible_at_epoch[account] = (
        current_selection_epoch() + effective_activation_delay_epochs()
    )
    if delegator_lists[account] is None:
        delegator_lists[account] = []

    ensure_candidate(account)

    requested_power[account] = effective_requested_power(account)
    reward_keys[account] = effective_reward_key(account)
    return validator_record(account)


def rebalance_validator_set(force: bool = False):
    selection_mode = effective_selection_mode()
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
    max_validators = effective_max_validators()
    replacement_budget = effective_max_active_set_churn()

    for account in previous_active:
        if account in ranked_accounts:
            selected_accounts = insert_ranked_account(selected_accounts, account)
        else:
            deactivated.append(account)

    while len(selected_accounts) > max_validators:
        weakest_active = weakest_ranked_account(selected_accounts)
        selected_accounts = without_item(selected_accounts, weakest_active)
        if weakest_active not in deactivated:
            deactivated.append(weakest_active)

    for account in ranked_accounts:
        if account in previous_active:
            continue
        if len(selected_accounts) >= max_validators:
            break
        selected_accounts = insert_ranked_account(selected_accounts, account)

    if len(selected_accounts) >= max_validators and replacement_budget > 0:
        for challenger in ranked_accounts:
            if challenger in previous_active:
                continue
            if challenger in selected_accounts:
                continue
            weakest_incumbent = weakest_selected_incumbent(
                selected_accounts,
                previous_active,
            )
            if weakest_incumbent is None:
                break
            if beats_margin(challenger, weakest_incumbent) == False:
                continue

            selected_accounts = without_item(selected_accounts, weakest_incumbent)
            if weakest_incumbent not in deactivated:
                deactivated.append(weakest_incumbent)
            selected_accounts = insert_ranked_account(selected_accounts, challenger)
            replacement_budget -= 1
            if replacement_budget <= 0:
                break

    activated = []
    for account in known_accounts:
        if account in selected_accounts:
            if account not in previous_active:
                activated.append(account)
                joined_at[account] = now
            pending_registrations[account] = False
            pending_leave[account] = False
            statuses[account] = STATUS_ACTIVE
            left_at[account] = None
            eligible_at_epoch[account] = selection_epoch
            reward_keys[account] = effective_reward_key(account)
            requested_power[account] = effective_requested_power(account)
            validator_power[account] = selected_validator_power(account)
        else:
            if statuses[account] == STATUS_ACTIVE:
                statuses[account] = STATUS_APPROVED

            if pending_registrations[account] == True:
                next_candidates.append(account)
            elif statuses[account] == STATUS_APPROVED:
                next_candidates.append(account)

            if account in previous_active or statuses[account] == STATUS_APPROVED:
                validator_power[account] = 0

    nodes.set(selected_accounts)
    candidates.set(next_candidates)
    last_rebalance_epoch.set(selection_epoch)

    return {
        "mode": selection_mode,
        "epoch": selection_epoch,
        "previous_active": previous_active,
        "selected": selected_accounts,
        "ranked_candidates": ranked_accounts,
        "activated": activated,
        "deactivated": deactivated,
    }


def validator_record(account: str):
    active = account in active_nodes_list()

    return {
        "account": account,
        "status": statuses[account],
        "active": active,
        "jailed": is_jailed(account),
        "jail_reason": normalize_jail_reason(jail_reasons[account]),
        "total_slashed": total_slashed[account],
        "last_slashed_at": last_slashed_at[account],
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
        "delegator_count": len(delegator_list(account)),
        "pending_registration": pending_registrations[account] == True,
        "pending_leave_at": pending_leave[account],
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
        assert requested_validator_power > 0, "Validator power <= 0"
        requested_power[account] = requested_validator_power

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


def activate_member(account: str):
    track_validator(account)
    current_nodes = active_nodes_list()
    if account not in current_nodes:
        current_nodes.append(account)
        nodes.set(current_nodes)

    current_candidates = candidate_list()
    if account in current_candidates:
        candidates.set(without_item(current_candidates, account))

    pending_registrations[account] = False
    pending_leave[account] = False
    statuses[account] = STATUS_ACTIVE
    joined_at[account] = now
    left_at[account] = None
    eligible_at_epoch[account] = 0
    if delegator_lists[account] is None:
        delegator_lists[account] = []

    power = effective_requested_power(account)
    requested_power[account] = power
    validator_power[account] = power
    reward_keys[account] = effective_reward_key(account)


def refund_validator_bond(account: str):
    held_balance = holdings[account]
    if held_balance > 0:
        currency.transfer(held_balance, effective_reward_key(account))
        holdings[account] = 0


def deactivate_member(account: str, status: str, refund_bond: bool):
    nodes.set(without_item(active_nodes_list(), account))
    pending_leave[account] = False
    statuses[account] = status
    left_at[account] = now
    validator_power[account] = 0

    if refund_bond:
        refund_validator_bond(account)


def exit_validator(account: str, status: str, refund_bond: bool):
    if account in active_nodes_list():
        deactivate_member(account, status, refund_bond)
    else:
        pending_leave[account] = False
        statuses[account] = status
        left_at[account] = now
        validator_power[account] = 0
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
    pending_leave[account] = False
    validator_power[account] = 0

    if account in active_nodes_list():
        nodes.set(without_item(active_nodes_list(), account))
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

    for delegator in delegator_list(account):
        current_delegation = delegations[delegator, account]
        if current_delegation <= 0:
            continue
        total_slashable_bond += current_delegation
        slash_participants.append(
            {"kind": "delegation", "owner": delegator, "amount": current_delegation}
        )

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

    slash_amount = (total_slashable_bond * slash_bps) / 10000
    remaining_slash = slash_amount
    self_bond_slashed = 0
    delegated_slashed = 0
    pending_unbond_slashed = 0

    slash_participant_count = len(slash_participants)
    slash_participant_index = 0

    for participant in slash_participants:
        if slash_participant_index == slash_participant_count - 1:
            participant_slash = remaining_slash
        else:
            participant_slash = (
                slash_amount * participant["amount"]
            ) / total_slashable_bond
            remaining_slash = remaining_slash - participant_slash

        if participant["kind"] == "self_bond":
            self_bond[account] = self_bond[account] - participant_slash
            self_bond_slashed = participant_slash
            slash_participant_index += 1
            continue

        if participant["kind"] == "pending_unbond":
            unbond_id = participant["unbond_id"]
            pending_unbond = pending_unbonds[unbond_id]
            pending_unbond["amount"] = pending_unbond["amount"] - participant_slash
            pending_unbonds[unbond_id] = pending_unbond
            pending_unbond_slashed += participant_slash
            slash_participant_index += 1
            continue

        delegator = participant["owner"]
        delegations[delegator, account] = (
            delegations[delegator, account] - participant_slash
        )
        total_delegated[account] = total_delegated[account] - participant_slash
        delegated_slashed += participant_slash
        if delegations[delegator, account] == 0:
            remove_delegator(account, delegator)

        slash_participant_index += 1

    total_slashed[account] = total_slashed[account] + slash_amount
    last_slashed_at[account] = now

    slash_destination = effective_slash_destination()
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

    if should_jail and is_jailed(account) == False and is_known_validator(account):
        jail_validator(account, reason)
        jailed_now = True
        state_changed = True

    if state_changed and effective_selection_mode() != "manual":
        rebalance_validator_set(force=True)

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
    selection_mode = effective_selection_mode()
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
            effective_manual_override_enabled() == True
        ), "Overrides off."


def validate_vote_argument(type_of_vote: str, arg: Any):
    if type_of_vote == "add_member":
        validate_manual_override_policy(type_of_vote)
        if effective_selection_mode() == "manual":
            assert (
                pending_registrations[arg] == True or statuses[arg] == STATUS_APPROVED
            ), "Member must have pending registration."
        else:
            assert pending_registrations[arg] == True, "Member must have pending registration."
        assert is_jailed(arg) == False, "Jailed."

    if type_of_vote == "remove_member":
        validate_manual_override_policy(type_of_vote)
        assert arg in active_nodes_list(), "Active only."

    if type_of_vote == "jail_member":
        validate_manual_override_policy(type_of_vote)
        member = arg["member"]
        assert is_known_validator(member), "Unknown validator."
        assert is_jailed(member) == False, "Already jailed."

    if type_of_vote == "unjail_member":
        validate_manual_override_policy(type_of_vote)
        assert is_jailed(arg) == True, "Not jailed."

    if type_of_vote == "slash_member":
        member = arg["member"]
        slash_bps = arg["slash_bps"]
        infraction_height = arg.get("infraction_height")
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
        validate_manual_override_policy(type_of_vote)
        member = arg["member"]
        power = arg["power"]
        assert member in active_nodes_list(), "Active only."
        assert power > 0, "Power <= 0"

    if type_of_vote == "update_policy":
        validate_policy_update(arg)


def validate_policy_update(arg: Any):
    assert arg is not None, "Missing policy."

    selection_mode = arg.get("selection_mode")
    if selection_mode is not None:
        assert selection_mode in ["manual", "auto_top_n", "hybrid"], "Bad selection mode."

    max_validators = arg.get("max_validators")
    if max_validators is not None:
        assert max_validators > 0, "max_validators <= 0"

    power_mode = arg.get("power_mode")
    if power_mode is not None:
        assert power_mode in ["equal", "requested", "stake_weighted"], "Bad power mode."

    rebalance_interval = arg.get("rebalance_interval")
    if rebalance_interval is not None:
        assert rebalance_interval > 0, "rebalance_interval <= 0"

    activation_delay_epochs = arg.get("activation_delay_epochs")
    if activation_delay_epochs is not None:
        assert activation_delay_epochs >= 0, "activation_delay_epochs < 0"

    unbonding_period_days = arg.get("unbonding_period_days")
    if unbonding_period_days is not None:
        assert unbonding_period_days >= 0, "unbonding_period_days < 0"

    min_self_bond = arg.get("min_self_bond")
    if min_self_bond is not None:
        assert min_self_bond >= 0, "min_self_bond < 0"

    min_total_bond = arg.get("min_total_bond")
    if min_total_bond is not None:
        assert min_total_bond >= 0, "min_total_bond < 0"

    max_commission_bps = arg.get("max_commission_bps")
    if max_commission_bps is not None:
        assert max_commission_bps >= 0, "max_comm < 0"
        assert max_commission_bps <= MAX_COMMISSION_BPS, "max_comm high"

    max_active_set_churn = arg.get("max_active_set_churn")
    if max_active_set_churn is not None:
        assert max_active_set_churn >= 0, "max_churn < 0"

    min_bond_margin_bps = arg.get("min_bond_margin_bps")
    if min_bond_margin_bps is not None:
        assert min_bond_margin_bps >= 0, "margin_bps < 0"

    slash_destination = arg.get("slash_destination")
    if slash_destination is not None:
        assert slash_destination != "", "empty slash dst"

    duplicate_vote_slash_bps = arg.get("duplicate_vote_slash_bps")
    if duplicate_vote_slash_bps is not None:
        assert duplicate_vote_slash_bps >= 0, "dv bps < 0"
        assert duplicate_vote_slash_bps <= 10000, "dv bps > 10000"

    light_client_attack_slash_bps = arg.get("light_client_attack_slash_bps")
    if light_client_attack_slash_bps is not None:
        assert light_client_attack_slash_bps >= 0, "lca bps < 0"
        assert light_client_attack_slash_bps <= 10000, "lca bps > 10000"


def apply_policy_update(arg: Any):
    selection_mode = arg.get("selection_mode")
    if selection_mode is not None:
        config["selection_mode"] = selection_mode

    max_validators = arg.get("max_validators")
    if max_validators is not None:
        config["max_validators"] = max_validators

    power_mode = arg.get("power_mode")
    if power_mode is not None:
        config["power_mode"] = power_mode

    rebalance_interval = arg.get("rebalance_interval")
    if rebalance_interval is not None:
        config["rebalance_interval"] = rebalance_interval

    activation_delay_epochs = arg.get("activation_delay_epochs")
    if activation_delay_epochs is not None:
        config["activation_delay_epochs"] = activation_delay_epochs

    unbonding_period_days = arg.get("unbonding_period_days")
    if unbonding_period_days is not None:
        config["unbonding_period_days"] = unbonding_period_days

    min_self_bond = arg.get("min_self_bond")
    if min_self_bond is not None:
        config["min_self_bond"] = min_self_bond

    min_total_bond = arg.get("min_total_bond")
    if min_total_bond is not None:
        config["min_total_bond"] = min_total_bond

    max_commission_bps = arg.get("max_commission_bps")
    if max_commission_bps is not None:
        config["max_commission_bps"] = max_commission_bps

    max_active_set_churn = arg.get("max_active_set_churn")
    if max_active_set_churn is not None:
        config["max_active_set_churn"] = max_active_set_churn

    min_bond_margin_bps = arg.get("min_bond_margin_bps")
    if min_bond_margin_bps is not None:
        config["min_bond_margin_bps"] = min_bond_margin_bps

    manual_override_enabled = arg.get("manual_override_enabled")
    if manual_override_enabled is not None:
        config["manual_override_enabled"] = manual_override_enabled

    slash_destination = arg.get("slash_destination")
    if slash_destination is not None:
        config["slash_destination"] = slash_destination

    duplicate_vote_slash_bps = arg.get("duplicate_vote_slash_bps")
    if duplicate_vote_slash_bps is not None:
        config["duplicate_vote_slash_bps"] = duplicate_vote_slash_bps

    duplicate_vote_jail = arg.get("duplicate_vote_jail")
    if duplicate_vote_jail is not None:
        config["duplicate_vote_jail"] = duplicate_vote_jail

    light_client_attack_slash_bps = arg.get("light_client_attack_slash_bps")
    if light_client_attack_slash_bps is not None:
        config["light_client_attack_slash_bps"] = light_client_attack_slash_bps

    light_client_attack_jail = arg.get("light_client_attack_jail")
    if light_client_attack_jail is not None:
        config["light_client_attack_jail"] = light_client_attack_jail


@export
def propose_vote(type_of_vote: str, arg: Any):
    assert ctx.caller in active_nodes_list(), "Validators only."
    assert type_of_vote in types.get(), "Invalid type."
    validate_vote_argument(type_of_vote, arg)

    proposal_id = total_votes.get() + 1
    total_votes.set(proposal_id)

    total_weight_snapshot = snapshot_vote_weights(proposal_id)
    proposer_weight = vote_weights[proposal_id, ctx.caller]

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
        "member_count_snapshot": len(active_nodes_list()),
        "total_weight_snapshot": total_weight_snapshot,
        "required_yes_votes": required_yes_votes(len(active_nodes_list())),
        "required_yes_weight": required_yes_weight(total_weight_snapshot),
    }

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

    decide_finalize(proposal_id)
    return current_vote


@export
def expire_vote(proposal_id: int):
    assert votes[proposal_id], "Invalid proposal."
    assert votes[proposal_id]["finalized"] == False, "Proposal already finalized."
    assert now >= votes[proposal_id]["expiry"], "Proposal has not expired."

    current_vote = votes[proposal_id]
    current_vote["finalized"] = True
    current_vote["status"] = STATUS_EXPIRED
    votes[proposal_id] = current_vote
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
        current_vote["finalized"] = True
        current_vote["status"] = STATUS_REJECTED
        votes[proposal_id] = current_vote


def finalize_vote(proposal_id: int):
    current_vote = votes[proposal_id]

    if current_vote["type"] == "add_member":
        member = current_vote["arg"]
        if effective_selection_mode() == "manual":
            assert (
                pending_registrations[member] == True or statuses[member] == STATUS_APPROVED
            ), "Member must have pending registration."
        else:
            assert pending_registrations[member] == True, "Member must have pending registration."
        if effective_selection_mode() == "manual":
            activate_member(member)
        else:
            approve_candidate(member)
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "remove_member":
        exit_validator(current_vote["arg"], STATUS_REMOVED, True)
        if effective_selection_mode() != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "jail_member":
        jail_validator(
            current_vote["arg"]["member"],
            current_vote["arg"].get("reason"),
        )
        if effective_selection_mode() != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "unjail_member":
        unjail_validator(current_vote["arg"])
        if effective_selection_mode() != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "slash_member":
        current_vote["result"] = slash_validator(
            current_vote["arg"]["member"],
            current_vote["arg"]["slash_bps"],
            current_vote["arg"].get("reason"),
            current_vote["arg"].get("infraction_height"),
        )
        if effective_selection_mode() != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "set_member_power":
        member = current_vote["arg"]["member"]
        power = current_vote["arg"]["power"]
        requested_power[member] = power
        if effective_selection_mode() == "manual":
            validator_power[member] = power
        elif effective_power_mode() == "requested":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "update_policy":
        apply_policy_update(current_vote["arg"])
        if effective_selection_mode() != "manual":
            rebalance_validator_set(force=True)
    elif current_vote["type"] == "reward_change":
        rewards.set_value(new_value=current_vote["arg"])
    elif current_vote["type"] == "dao_payout":
        dao.transfer_from_dao(args=current_vote["arg"])
    elif current_vote["type"] == "stamp_cost_change":
        stamp_cost.set_value(new_value=current_vote["arg"])
    elif current_vote["type"] == "change_registration_fee":
        registration_fee.set(current_vote["arg"])
    elif current_vote["type"] == "change_types":
        types.set(current_vote["arg"])

    current_vote["finalized"] = True
    current_vote["status"] = STATUS_APPROVED
    votes[proposal_id] = current_vote
    return current_vote


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
def get_validator(account: str):
    return validator_record(account)


@export
def get_policy_config():
    return {
        "selection_mode": config["selection_mode"],
        "max_validators": config["max_validators"],
        "power_mode": config["power_mode"],
        "rebalance_interval": config["rebalance_interval"],
        "activation_delay_epochs": config["activation_delay_epochs"],
        "unbonding_period_days": config["unbonding_period_days"],
        "min_self_bond": config["min_self_bond"],
        "min_total_bond": config["min_total_bond"],
        "max_commission_bps": config["max_commission_bps"],
        "max_active_set_churn": config["max_active_set_churn"],
        "min_bond_margin_bps": config["min_bond_margin_bps"],
        "manual_override_enabled": config["manual_override_enabled"],
        "slash_destination": config["slash_destination"],
        "duplicate_vote_slash_bps": config["duplicate_vote_slash_bps"],
        "duplicate_vote_jail": config["duplicate_vote_jail"],
        "light_client_attack_slash_bps": config["light_client_attack_slash_bps"],
        "light_client_attack_jail": config["light_client_attack_jail"],
    }


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
    return rebalance_validator_set()


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

    if ctx.caller in active_nodes_list():
        exit_validator(ctx.caller, STATUS_LEFT, True)
    pending_leave[ctx.caller] = False
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

    assert ctx.caller not in active_nodes_list(), "Already a node."
    assert pending_registrations[ctx.caller] == False, "Already pending."
    assert requested_validator_power > 0, "Validator power <= 0"
    assert is_jailed(ctx.caller) == False, "Jailed."

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
    if effective_selection_mode() == "manual":
        eligible_at_epoch[ctx.caller] = 0
    else:
        eligible_at_epoch[ctx.caller] = (
            current_selection_epoch() + effective_activation_delay_epochs()
        )
    pending_leave[ctx.caller] = False
    self_bond[ctx.caller] = self_bond[ctx.caller]
    total_delegated[ctx.caller] = total_delegated[ctx.caller]
    if delegator_lists[ctx.caller] is None:
        delegator_lists[ctx.caller] = []

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
def bond_self(amount: float):
    assert amount > 0, "Bond amount <= 0"
    assert can_accept_delegation(ctx.caller), "Bonding closed."

    currency.transfer_from(
        amount=amount,
        to=ctx.this,
        main_account=ctx.caller,
    )
    self_bond[ctx.caller] = self_bond[ctx.caller] + amount
    return validator_record(ctx.caller)


@export
def unbond_self(amount: float):
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
def delegate(validator: str, amount: float, reward_key: str = None):
    assert amount > 0, "Delegation amount <= 0"
    assert validator != ctx.caller, "Use bond_self."
    assert can_accept_delegation(validator), "Closed."

    currency.transfer_from(
        amount=amount,
        to=ctx.this,
        main_account=ctx.caller,
    )

    delegations[ctx.caller, validator] = delegations[ctx.caller, validator] + amount
    total_delegated[validator] = total_delegated[validator] + amount
    add_delegator(validator, ctx.caller)

    if reward_key is not None:
        delegator_reward_keys[ctx.caller, validator] = normalize_delegator_reward_key(
            ctx.caller, reward_key
        )
    elif delegator_reward_keys[ctx.caller, validator] is None:
        delegator_reward_keys[ctx.caller, validator] = ctx.caller

    return get_delegation(ctx.caller, validator)


@export
def undelegate(validator: str, amount: float):
    assert amount > 0, "Delegation amount <= 0"
    assert delegations[ctx.caller, validator] >= amount, "Not enough delegated stake."

    delegations[ctx.caller, validator] = delegations[ctx.caller, validator] - amount
    total_delegated[validator] = total_delegated[validator] - amount

    if delegations[ctx.caller, validator] == 0:
        remove_delegator(validator, ctx.caller)

    return create_pending_unbond(
        owner=ctx.caller,
        validator=validator,
        amount=amount,
        kind="delegation",
    )


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
        "amount": delegations[delegator, validator],
        "reward_key": normalize_delegator_reward_key(
            delegator, delegator_reward_keys[delegator, validator]
        ),
    }


@export
def get_delegators(validator: str):
    return delegator_list(validator)


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
        "total_bond": total_bonded(validator),
        "delegators": delegator_list(validator),
    }
