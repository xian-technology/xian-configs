"""Bounded pending-unbond penalty coordinator; validators owns all stake writes."""

pending_head = Variable()
pending_tail = Variable()
job_counter = Variable()
job_count = Variable()
jobs = Hash(default_value=None)
pending_counts = Hash(default_value=0)
self_bonds = ForeignHash(foreign_contract="validators", foreign_name="self_bond")
delegated = ForeignHash(foreign_contract="validators", foreign_name="total_delegated")
unbond_heads = ForeignHash(
    foreign_contract="validators", foreign_name="pending_unbond_heads"
)
unbond_links = ForeignHash(
    foreign_contract="validators", foreign_name="pending_unbond_links"
)
unbonds = ForeignHash(foreign_contract="validators", foreign_name="pending_unbonds")
policy_config = ForeignHash(foreign_contract="validators", foreign_name="config")
unbond_totals = Hash(default_value=0)
unbond_heap_sizes = Hash(default_value=0)
unbond_heap_nodes = Hash(default_value=None)
unbond_heap_positions = Hash(default_value=None)
view_delegator_counts = ForeignHash(
    foreign_contract="validators", foreign_name="delegator_counts"
)
view_eligible_at_epoch = ForeignHash(
    foreign_contract="validators", foreign_name="eligible_at_epoch"
)
view_holdings = ForeignHash(foreign_contract="validators", foreign_name="holdings")
view_jail_reasons = ForeignHash(
    foreign_contract="validators", foreign_name="jail_reasons"
)
view_jailed = ForeignHash(foreign_contract="validators", foreign_name="jailed")
view_joined_at = ForeignHash(foreign_contract="validators", foreign_name="joined_at")
view_last_evidence_at = ForeignHash(
    foreign_contract="validators", foreign_name="last_evidence_at"
)
view_last_evidence_heights = ForeignHash(
    foreign_contract="validators", foreign_name="last_evidence_heights"
)
view_last_evidence_ids = ForeignHash(
    foreign_contract="validators", foreign_name="last_evidence_ids"
)
view_last_evidence_types = ForeignHash(
    foreign_contract="validators", foreign_name="last_evidence_types"
)
view_last_jailed_at = ForeignHash(
    foreign_contract="validators", foreign_name="last_jailed_at"
)
view_last_slashed_at = ForeignHash(
    foreign_contract="validators", foreign_name="last_slashed_at"
)
view_last_unjailed_at = ForeignHash(
    foreign_contract="validators", foreign_name="last_unjailed_at"
)
view_left_at = ForeignHash(foreign_contract="validators", foreign_name="left_at")
view_metadata_uris = ForeignHash(
    foreign_contract="validators", foreign_name="metadata_uris"
)
view_missed_blocks = ForeignHash(
    foreign_contract="validators", foreign_name="missed_blocks"
)
view_monikers = ForeignHash(foreign_contract="validators", foreign_name="monikers")
view_network_endpoints = ForeignHash(
    foreign_contract="validators", foreign_name="network_endpoints"
)
view_pending_leave = ForeignHash(
    foreign_contract="validators", foreign_name="pending_leave"
)
view_pending_registrations = ForeignHash(
    foreign_contract="validators", foreign_name="pending_registrations"
)
view_registered_at = ForeignHash(
    foreign_contract="validators", foreign_name="registered_at"
)
view_reward_per_share = ForeignHash(
    foreign_contract="validators", foreign_name="reward_per_share"
)
view_reward_pool = ForeignHash(
    foreign_contract="validators", foreign_name="reward_pool"
)
view_self_bond = ForeignHash(foreign_contract="validators", foreign_name="self_bond")
view_statuses = ForeignHash(foreign_contract="validators", foreign_name="statuses")
view_total_delegated = ForeignHash(
    foreign_contract="validators", foreign_name="total_delegated"
)
view_total_shares = ForeignHash(
    foreign_contract="validators", foreign_name="total_shares"
)
view_total_slashed = ForeignHash(
    foreign_contract="validators", foreign_name="total_slashed"
)
MAX_SLASH_BATCH_WORK = 32


@construct
def seed():
    job_counter.set(0)
    job_count.set(0)


def membership():
    return importlib.import_module("validators")


def is_integer(value: Any):
    return isinstance(value, int) and not isinstance(value, bool)


def slashable_pending_unbond(unbond: dict, height: int):
    return (
        unbond is not None
        and height is not None
        and unbond["claimed"] == False
        and unbond["amount"] > 0
        and height <= unbond["created_block"]
    )


def current_block_number():
    return block_num or 0


def require_validators():
    assert ctx.caller == "validators", "Validators only."


def unbond_precedes(left: int, right: int):
    left_time = unbonds[left]["unlock_at"]
    right_time = unbonds[right]["unlock_at"]
    return left_time < right_time or (left_time == right_time and left < right)


def swap_unbond_heap(validator: str, left: int, right: int):
    left_id = unbond_heap_nodes[validator, left]
    right_id = unbond_heap_nodes[validator, right]
    unbond_heap_nodes[validator, left] = right_id
    unbond_heap_nodes[validator, right] = left_id
    unbond_heap_positions[left_id] = right
    unbond_heap_positions[right_id] = left


def sift_unbond_up(validator: str, position: int):
    while position > 1:
        parent = position // 2
        if not unbond_precedes(
            unbond_heap_nodes[validator, position], unbond_heap_nodes[validator, parent]
        ):
            break
        swap_unbond_heap(validator, position, parent)
        position = parent
    return position


def sift_unbond_down(validator: str, position: int):
    size = unbond_heap_sizes[validator]
    while position * 2 <= size:
        child = position * 2
        if child < size and unbond_precedes(
            unbond_heap_nodes[validator, child + 1], unbond_heap_nodes[validator, child]
        ):
            child += 1
        if not unbond_precedes(
            unbond_heap_nodes[validator, child], unbond_heap_nodes[validator, position]
        ):
            break
        swap_unbond_heap(validator, position, child)
        position = child


@export
def track_unbond(unbond_id: int):
    require_validators()
    assert unbond_heap_positions[unbond_id] is None, "Unbond already indexed."
    record = unbonds[unbond_id]
    validator = record["validator"]
    position = unbond_heap_sizes[validator] + 1
    unbond_heap_sizes[validator] = position
    unbond_heap_nodes[validator, position] = unbond_id
    unbond_heap_positions[unbond_id] = position
    unbond_totals[validator] += record["amount"]
    sift_unbond_up(validator, position)


@export
def release_unbond(unbond_id: int):
    require_validators()
    record = unbonds[unbond_id]
    validator = record["validator"]
    assert pending_counts[validator] == 0, "Validator penalty pending."
    position = unbond_heap_positions[unbond_id]
    assert position is not None, "Unbond is not indexed."
    size = unbond_heap_sizes[validator]
    last_id = unbond_heap_nodes[validator, size]
    unbond_heap_nodes[validator, size] = None
    unbond_heap_positions[unbond_id] = None
    unbond_heap_sizes[validator] = size - 1
    unbond_totals[validator] -= record["amount"]
    if position < size:
        unbond_heap_nodes[validator, position] = last_id
        unbond_heap_positions[last_id] = position
        position = sift_unbond_up(validator, position)
        sift_unbond_down(validator, position)


@export
def get_unbond_summary(validator: str):
    first = unbond_heap_nodes[validator, 1]
    unlock = None
    if first is not None:
        unlock = unbonds[first]["unlock_at"]
    return {
        "pending_unbond_count": unbond_heap_sizes[validator],
        "pending_unbond_total": unbond_totals[validator],
        "next_unbond_unlock_at": unlock,
    }


def pending_cursor(job: dict):
    if job["infraction_height"] is None or unbond_totals[job["member"]] <= 0:
        return None
    return unbond_heads["validator", job["member"]]


def initialize_pending_slash(job: dict):
    account = job["member"]
    job["self_amount"] = self_bonds[account] or 0
    job["pool_amount"] = delegated[account] or 0
    job["total_slashable_bond"] = job["self_amount"] + job["pool_amount"]
    job["cursor"] = pending_cursor(job)
    job["status"] = "collect"


def validate_penalty_request(
    slash_bps: int, reason: str, infraction_height: int = None
):
    assert is_integer(slash_bps) and slash_bps > 0 and slash_bps <= 10000, (
        "Bad slash bps."
    )
    assert infraction_height is None or (
        is_integer(infraction_height) and infraction_height >= 0
    ), "Bad infraction height."
    assert reason is None or (isinstance(reason, str) and len(reason) <= 256), (
        "Penalty reason is too long."
    )


@export
def enqueue(account: str, slash_bps: int, reason: str, infraction_height: int = None):
    require_validators()
    validate_penalty_request(slash_bps, reason, infraction_height)
    job_id = job_counter.get() + 1
    job_counter.set(job_id)
    job = {
        "id": job_id,
        "member": account,
        "slash_bps": slash_bps,
        "reason": reason or "",
        "destination": policy_config["slash_destination"] or "dao",
        "infraction_height": infraction_height,
        "requested_at": now,
        "requested_block": current_block_number(),
        "status": "queued",
        "next_job": None,
        "cursor": None,
        "processed_bond": 0,
        "allocated_slash": 0,
        "self_bond_slashed": 0,
        "delegated_slashed": 0,
        "pending_unbond_slashed": 0,
        "slash_amount": None,
    }
    if pending_counts[account] == 0:
        initialize_pending_slash(job)
    previous = pending_tail.get()
    if previous is None:
        pending_head.set(job_id)
    else:
        previous_job = jobs[previous]
        previous_job["next_job"] = job_id
        jobs[previous] = previous_job
    pending_tail.set(job_id)
    jobs[job_id] = job
    pending_counts[account] += 1
    job_count.set(job_count.get() + 1)
    return {
        "queued": True,
        "job_id": job_id,
        "status": "pending",
        "member": account,
        "slash_bps": slash_bps,
    }


def collect_pending_slash(job: dict):
    unbond_id = job["cursor"]
    if unbond_id is None:
        job["status"] = "live_stake"
        return
    unbond = unbonds[unbond_id]
    if slashable_pending_unbond(unbond, job["infraction_height"]):
        job["total_slashable_bond"] += unbond["amount"]
    job["cursor"] = unbond_links["validator", unbond_id, "next"]


def pending_participant_slash(job: dict, amount: decimal):
    job["processed_bond"] += amount
    target = job["processed_bond"] * (job["slash_bps"] / 10000)
    part = target - job["allocated_slash"]
    job["allocated_slash"] = target
    return part


LIVE_SLASH_PHASES = {
    "self_bond": ["self_amount", "self_bond_slashed"],
    "delegation_pool": ["pool_amount", "delegated_slashed"],
}


def apply_pending_live_part(job: dict, kind: str):
    phase = LIVE_SLASH_PHASES[kind]
    part = pending_participant_slash(job, job[phase[0]])
    membership().apply_pending_slash_part(account=job["member"], kind=kind, amount=part)
    job[phase[1]] = part


def apply_pending_live_slash(job: dict):
    # Reward splitting can observe live stake after this system call. Keep
    # the self/pool ratio on one side of the penalty at every block boundary.
    apply_pending_live_part(job, "self_bond")
    apply_pending_live_part(job, "delegation_pool")
    job["cursor"] = pending_cursor(job)
    job["status"] = "pending_unbonds"


def apply_pending_unbond_slash(job: dict):
    unbond_id = job["cursor"]
    if unbond_id is None:
        job["status"] = "finish"
        return
    unbond = unbonds[unbond_id]
    if slashable_pending_unbond(unbond, job["infraction_height"]):
        part = pending_participant_slash(job, unbond["amount"])
        membership().apply_pending_slash_part(
            account=job["member"],
            kind="pending_unbond",
            amount=part,
            unbond_id=unbond_id,
        )
        unbond_totals[job["member"]] -= part
        job["pending_unbond_slashed"] += part
    job["cursor"] = unbond_links["validator", unbond_id, "next"]


def finish_pending_slash(job: dict):
    account = job["member"]
    amount = job["total_slashable_bond"] * (job["slash_bps"] / 10000)
    assert job["processed_bond"] == job["total_slashable_bond"], (
        "Penalty principal changed."
    )
    assert job["allocated_slash"] == amount, "Penalty allocation mismatch."
    membership().finish_pending_slash(
        account=account, amount=amount, destination=job["destination"]
    )
    job["slash_amount"] = amount
    job["status"] = "complete"
    job["completed_at"] = now
    job["completed_block"] = current_block_number()
    pending_counts[account] -= 1
    job_count.set(job_count.get() - 1)
    pending_head.set(job["next_job"])
    if job["next_job"] is None:
        pending_tail.set(None)


def pending_slash_step(job: dict):
    status = job["status"]
    if status == "queued":
        initialize_pending_slash(job)
    elif status == "collect":
        collect_pending_slash(job)
    elif status == "live_stake":
        apply_pending_live_slash(job)
    elif status == "pending_unbonds":
        apply_pending_unbond_slash(job)
    else:
        assert status == "finish", "Invalid penalty phase."
        finish_pending_slash(job)


@export
def process_pending_slashes(max_work: int = MAX_SLASH_BATCH_WORK):
    assert ctx.caller == "__penalty_driver__", "Driver only."
    assert is_integer(max_work) and max_work > 0 and max_work <= MAX_SLASH_BATCH_WORK, (
        "Invalid batch work."
    )
    processed = 0
    completed = 0
    while processed < max_work and pending_head.get() is not None:
        job_id = pending_head.get()
        job = jobs[job_id]
        pending_slash_step(job)
        jobs[job_id] = job
        if job["status"] == "complete":
            completed += 1
        processed += 1
    if completed > 0:
        membership().rebalance_after_penalties()
    return {
        "processed": processed,
        "completed": completed,
        "head": pending_head.get(),
        "pending_jobs": job_count.get(),
    }


@export
def get_pending_slash_job(job_id: int):
    return jobs[job_id]


def stored_value(value: Any, fallback: Any):
    if value is None:
        return fallback
    return value


@export
def describe_validator(account: str, derived: dict):
    require_validators()
    summary = get_unbond_summary(account)
    return {
        "account": account,
        "status": stored_value(view_statuses[account], ""),
        "active": derived["active"],
        "jailed": view_jailed[account] == True,
        "jail_reason": stored_value(view_jail_reasons[account], ""),
        "last_jailed_at": view_last_jailed_at[account],
        "last_unjailed_at": view_last_unjailed_at[account],
        "total_slashed": stored_value(view_total_slashed[account], 0),
        "last_slashed_at": view_last_slashed_at[account],
        "last_evidence_id": view_last_evidence_ids[account],
        "last_evidence_type": view_last_evidence_types[account],
        "last_evidence_height": view_last_evidence_heights[account],
        "last_evidence_at": view_last_evidence_at[account],
        "power": derived["power"],
        "requested_power": derived["requested_power"],
        "reward_key": derived["reward_key"],
        "moniker": stored_value(view_monikers[account], ""),
        "network_endpoint": stored_value(view_network_endpoints[account], ""),
        "metadata_uri": stored_value(view_metadata_uris[account], ""),
        "bond": stored_value(view_holdings[account], 0),
        "registration_bond": stored_value(view_holdings[account], 0),
        "self_bond": stored_value(view_self_bond[account], 0),
        "total_delegated": stored_value(view_total_delegated[account], 0),
        "total_bond": stored_value(self_bonds[account], 0)
        + stored_value(delegated[account], 0),
        "commission_bps": derived["commission_bps"],
        "total_shares": stored_value(view_total_shares[account], 0),
        "delegator_count": stored_value(view_delegator_counts[account], 0),
        "reward_per_share": stored_value(view_reward_per_share[account], 0),
        "reward_pool": stored_value(view_reward_pool[account], 0),
        "missed_blocks": stored_value(view_missed_blocks[account], 0),
        "pending_slash_count": pending_counts[account],
        "pending_unbond_count": summary["pending_unbond_count"],
        "pending_unbond_total": summary["pending_unbond_total"],
        "next_unbond_unlock_at": summary["next_unbond_unlock_at"],
        "pending_registration": view_pending_registrations[account] == True,
        "pending_leave_at": stored_value(view_pending_leave[account], False),
        "last_rebalance_epoch": derived["last_rebalance_epoch"],
        "eligible_at_epoch": stored_value(view_eligible_at_epoch[account], 0),
        "selection_eligible_at_last_rebalance": derived[
            "selection_eligible_at_last_rebalance"
        ],
        "registered_at": view_registered_at[account],
        "joined_at": view_joined_at[account],
        "left_at": view_left_at[account],
    }
