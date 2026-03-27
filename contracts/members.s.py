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
PASS_THRESHOLD_NUMERATOR = 4
PASS_THRESHOLD_DENOMINATOR = 5
PROPOSAL_EXPIRY_DAYS = 7
LEAVE_DELAY_DAYS = 7


@construct
def seed(
    genesis_nodes: list,
    genesis_registration_fee: int,
    genesis_powers: dict = None,
    genesis_reward_keys: dict = None,
    default_node_power: int = DEFAULT_VALIDATOR_POWER,
):
    assert default_node_power > 0, "default_node_power must be positive."

    nodes.set([])
    candidates.set([])
    types.set(
        [
            "add_member",
            "remove_member",
            "set_member_power",
            "change_registration_fee",
            "reward_change",
            "dao_payout",
            "stamp_cost_change",
            "change_types",
            "create_stream",
            "change_close_time",
            "finalize_stream",
            "close_balance_finalize",
            "topic_vote",
        ]
    )
    total_votes.set(0)
    registration_fee.set(genesis_registration_fee)

    active_nodes = []
    for node in genesis_nodes:
        if node in active_nodes:
            continue

        active_nodes.append(node)
        statuses[node] = STATUS_ACTIVE
        registered_at[node] = now
        joined_at[node] = now
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

    assert power > 0, "Validator power must be positive."
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


def validator_record(account: str):
    active = account in active_nodes_list()

    return {
        "account": account,
        "status": statuses[account],
        "active": active,
        "power": effective_active_power(account),
        "requested_power": effective_requested_power(account),
        "reward_key": effective_reward_key(account),
        "moniker": monikers[account],
        "network_endpoint": network_endpoints[account],
        "metadata_uri": metadata_uris[account],
        "bond": holdings[account],
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
    assert total_weight > 0, "Validator set must have positive voting weight."
    return ceil_div(
        total_weight * PASS_THRESHOLD_NUMERATOR,
        PASS_THRESHOLD_DENOMINATOR,
    )


def required_yes_votes(member_count: int):
    assert member_count > 0, "Validator set must have members."
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
    moniker: str = None,
    network_endpoint: str = None,
    metadata_uri: str = None,
):
    if reward_key is not None:
        reward_keys[account] = normalize_reward_key(account, reward_key)

    if requested_validator_power is not None:
        assert requested_validator_power > 0, "Validator power must be positive."
        requested_power[account] = requested_validator_power

    if moniker is not None:
        monikers[account] = moniker

    if network_endpoint is not None:
        network_endpoints[account] = network_endpoint

    if metadata_uri is not None:
        metadata_uris[account] = metadata_uri


def activate_member(account: str):
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


def validate_vote_argument(type_of_vote: str, arg: Any):
    if type_of_vote == "add_member":
        assert pending_registrations[arg] == True, "Member must have pending registration."

    if type_of_vote == "remove_member":
        assert arg in active_nodes_list(), "Member must be active."

    if type_of_vote == "set_member_power":
        member = arg["member"]
        power = arg["power"]
        assert member in active_nodes_list(), "Member must be active."
        assert power > 0, "Power must be positive."


@export
def propose_vote(type_of_vote: str, arg: Any):
    assert ctx.caller in active_nodes_list(), "Only nodes can propose new votes."
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
        assert pending_registrations[member] == True, "Member must have pending registration."
        activate_member(member)
    elif current_vote["type"] == "remove_member":
        deactivate_member(current_vote["arg"], STATUS_REMOVED, True)
    elif current_vote["type"] == "set_member_power":
        member = current_vote["arg"]["member"]
        power = current_vote["arg"]["power"]
        requested_power[member] = power
        validator_power[member] = power
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
    elif current_vote["type"] == "create_stream":
        dao.create_stream(args=current_vote["arg"])
    elif current_vote["type"] == "change_close_time":
        dao.change_close_time(args=current_vote["arg"])
    elif current_vote["type"] == "finalize_stream":
        dao.finalize_stream(args=current_vote["arg"])
    elif current_vote["type"] == "close_balance_finalize":
        dao.close_balance_finalize(args=current_vote["arg"])

    current_vote["finalized"] = True
    current_vote["status"] = STATUS_APPROVED
    votes[proposal_id] = current_vote
    return current_vote


@export
def balance_stream(stream_id: str):
    return dao.balance_stream(stream_id=stream_id)


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
def update_profile(
    reward_key: str = None,
    moniker: str = None,
    network_endpoint: str = None,
    metadata_uri: str = None,
):
    account = ctx.caller
    assert (
        account in active_nodes_list() or pending_registrations[account] == True
    ), "Only validators and pending candidates can update their profile."

    update_profile_fields(
        account,
        reward_key=reward_key,
        requested_validator_power=None,
        moniker=moniker,
        network_endpoint=network_endpoint,
        metadata_uri=metadata_uri,
    )
    return validator_record(account)


@export
def update_registration(
    requested_validator_power: int,
    reward_key: str = None,
    moniker: str = None,
    network_endpoint: str = None,
    metadata_uri: str = None,
):
    account = ctx.caller
    assert pending_registrations[account] == True, "No pending registration."

    update_profile_fields(
        account,
        reward_key=reward_key,
        requested_validator_power=requested_validator_power,
        moniker=moniker,
        network_endpoint=network_endpoint,
        metadata_uri=metadata_uri,
    )
    return validator_record(account)


@export
def announce_leave():
    assert ctx.caller in active_nodes_list(), "Not a node."
    assert pending_leave[ctx.caller] == False, "Already pending leave."

    pending_leave[ctx.caller] = now + datetime.timedelta(days=LEAVE_DELAY_DAYS)
    statuses[ctx.caller] = STATUS_LEAVING
    return validator_record(ctx.caller)


@export
def leave():
    assert pending_leave[ctx.caller], "Not pending leave."
    assert pending_leave[ctx.caller] < now, "Leave announcement period not over."

    if ctx.caller in active_nodes_list():
        deactivate_member(ctx.caller, STATUS_LEFT, True)
    pending_leave[ctx.caller] = False
    return validator_record(ctx.caller)


@export
def register(
    reward_key: str = None,
    requested_validator_power: int = DEFAULT_VALIDATOR_POWER,
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
    assert pending_registrations[ctx.caller] == False, "Already pending registration."
    assert requested_validator_power > 0, "Validator power must be positive."

    currency.transfer_from(
        amount=registration_fee.get(),
        to=ctx.this,
        main_account=ctx.caller,
    )

    holdings[ctx.caller] = holdings[ctx.caller] + registration_fee.get()
    pending_registrations[ctx.caller] = True
    statuses[ctx.caller] = STATUS_PENDING
    registered_at[ctx.caller] = now
    joined_at[ctx.caller] = None
    left_at[ctx.caller] = None
    pending_leave[ctx.caller] = False

    update_profile_fields(
        ctx.caller,
        reward_key=normalize_reward_key(ctx.caller, reward_key),
        requested_validator_power=requested_validator_power,
        moniker=moniker,
        network_endpoint=network_endpoint,
        metadata_uri=metadata_uri,
    )

    current_candidates = candidate_list()
    if ctx.caller not in current_candidates:
        current_candidates.append(ctx.caller)
        candidates.set(current_candidates)

    return validator_record(ctx.caller)


@export
def unregister():
    assert ctx.caller not in active_nodes_list(), "If you're a node already, you can't unregister. You need to leave or be removed."
    assert pending_registrations[ctx.caller] == True, "No pending registration."

    refund_validator_bond(ctx.caller)
    pending_registrations[ctx.caller] = False
    pending_leave[ctx.caller] = False
    statuses[ctx.caller] = STATUS_WITHDRAWN
    validator_power[ctx.caller] = 0
    candidates.set(without_item(candidate_list(), ctx.caller))
    return validator_record(ctx.caller)
