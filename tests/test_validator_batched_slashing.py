"""Evidence penalties progress under one hard shared work budget per block."""

from decimal import Decimal

import pytest
from test_validator_unbond_indexes import DELEGATOR, NODE, OTHER
from test_validator_unbond_indexes import chain as chain


def _bond(currency, validators, account=NODE, amount=2):
    currency.transfer(amount=amount, to=account, signer="founder")
    currency.approve(amount=amount, to="validators", signer=account)
    validators.bond_self(amount=amount, signer=account)


def _evidence(
    validators, evidence_id="first", height=0, kind="DUPLICATE_VOTE", member=NODE
):
    return validators.apply_evidence_penalty(
        member=member,
        infraction_type=kind,
        evidence_id=evidence_id,
        evidence_height=height,
        signer="__evidence_penalty_driver__",
        environment={"block_num": 20},
    )


def _drain(client, validators):
    calls = 0
    while client.raw_driver.get("validator_penalties.pending_head") is not None:
        result = client.get_contract_proxy(
            "validator_penalties"
        ).process_pending_slashes(
            signer="__penalty_driver__",
            metering=True,
            chi=200_000,
            return_full_output=True,
            environment={"block_num": 30 + calls},
        )
        assert result["status_code"] == 0, result["result"]
        assert result["result"]["processed"] <= 32
        if result["result"]["head"] is None:
            assert result["result"]["pending_jobs"] == 0
        calls += 1
        assert calls < 100
    return calls


def test_evidence_jails_immediately_and_holds_claims_until_exact_penalty_finishes(
    chain,
):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    first = validators.undelegate(
        validator=NODE, amount=1, signer=DELEGATOR, environment={"block_num": 5}
    )
    second = validators.undelegate(
        validator=NODE, amount=1, signer=DELEGATOR, environment={"block_num": 10}
    )
    dao_before = currency.balance_of(address="dao")

    result = _evidence(validators, height=8)

    assert result["jailed_now"] is True
    assert result["slash_result"]["queued"] is True
    job_id = result["slash_result"]["job_id"]
    assert validators.get_members() == [OTHER]
    with pytest.raises(AssertionError, match="penalty pending"):
        validators.claim_unbond(unbond_id=first["id"], signer=DELEGATOR)
    with pytest.raises(AssertionError, match="penalty pending"):
        validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    with pytest.raises(AssertionError, match="penalty pending"):
        validators.unregister(signer=NODE)
    assert _drain(client, validators) == 1
    job = client.get_contract_proxy("validator_penalties").get_pending_slash_job(
        job_id=job_id
    )
    assert job["status"] == "complete"
    assert job["slash_amount"] == Decimal("0.25")
    assert currency.balance_of(address="dao") == dao_before + Decimal("0.25")
    assert validators.get_pending_unbond(unbond_id=first["id"])["amount"] == 1
    assert validators.get_pending_unbond(unbond_id=second["id"])["amount"] == Decimal(
        "0.95"
    )
    validators.claim_unbond(unbond_id=first["id"], signer=DELEGATOR)
    assert validators.get_pending_unbond(unbond_id=first["id"])["claimed"] is True


def test_repeated_evidence_is_idempotent_and_later_jobs_compound_prior_results(chain):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    before = currency.balance_of(address="dao")
    first = _evidence(validators)
    duplicate = _evidence(validators)
    second = _evidence(validators, evidence_id="second", kind="LIGHT_CLIENT_ATTACK")

    assert duplicate["duplicate"] is True
    assert second["slash_result"]["job_id"] == first["slash_result"]["job_id"] + 1
    _drain(client, validators)

    assert currency.balance_of(address="dao") == before + Decimal("0.87")
    assert validators.get_reward_distribution_info(validator=NODE)[
        "self_bond"
    ] == Decimal("1.71")
    assert validators.get_pending_unbond(unbond_id=1)["amount"] == Decimal("0.855")
    paid = currency.balance_of(address="dao")
    assert (
        client.get_contract_proxy("validator_penalties").process_pending_slashes(
            signer="__penalty_driver__"
        )["processed"]
        == 0
    )
    assert currency.balance_of(address="dao") == paid


def test_large_pending_set_needs_multiple_bounded_steps_and_locks_stake(chain):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(40):
        validators.undelegate(validator=NODE, amount=Decimal("0.01"), signer=DELEGATOR)
    result = _evidence(validators)
    job_id = result["slash_result"]["job_id"]

    first = client.get_contract_proxy("validator_penalties").process_pending_slashes(
        max_work=7, signer="__penalty_driver__"
    )

    assert first["processed"] == 7
    progress = client.get_contract_proxy("validator_penalties").get_pending_slash_job(
        job_id=job_id
    )
    assert progress["status"] == "collect"
    assert progress["cursor"] == 8
    client.raw_driver.commit()
    # Another invocation reads only committed job progress, not process-local state.
    second = client.get_contract_proxy("validator_penalties").process_pending_slashes(
        max_work=7, signer="__penalty_driver__"
    )
    assert second["processed"] == 7
    assert (
        client.get_contract_proxy("validator_penalties").get_pending_slash_job(
            job_id=job_id
        )["cursor"]
        == 15
    )
    assert _drain(client, validators) > 1
    assert client.get_contract_proxy("validator_penalties").get_pending_slash_job(
        job_id=job_id
    )["slash_amount"] == Decimal("0.3")


@pytest.mark.parametrize("max_work", [0, 33])
def test_system_work_budget_is_strictly_bounded(chain, max_work):
    client, _, validators = chain
    with pytest.raises(AssertionError, match="batch work"):
        client.get_contract_proxy("validator_penalties").process_pending_slashes(
            max_work=max_work, signer="__penalty_driver__"
        )


def test_only_the_node_can_progress_penalties(chain):
    client, _, validators = chain
    with pytest.raises(AssertionError, match="Driver only"):
        client.get_contract_proxy("validator_penalties").process_pending_slashes(
            signer=DELEGATOR
        )


@pytest.mark.parametrize("destination", ["AB" * 32, "r" * 494])
def test_policy_refuses_a_slash_destination_that_would_stall_the_job(
    chain, destination
):
    _, _, validators = chain
    with pytest.raises(AssertionError, match="canonical lowercase|storage key limit"):
        validators.propose_vote(
            type_of_vote="update_policy",
            arg={"slash_destination": destination},
            signer=NODE,
        )
    assert validators.total_votes.get() == 0


@pytest.mark.parametrize(
    "method,kwargs",
    [
        (
            "apply_pending_slash_part",
            {"account": NODE, "kind": "self_bond", "amount": 1},
        ),
        (
            "finish_pending_slash",
            {"account": NODE, "amount": 1, "destination": DELEGATOR},
        ),
        ("rebalance_after_penalties", {}),
    ],
)
def test_untrusted_account_cannot_invoke_stake_writer_callbacks(chain, method, kwargs):
    _, currency, validators = chain
    _bond(currency, validators)
    before = currency.balance_of(address="validators")
    with pytest.raises(AssertionError, match="coordinator only"):
        getattr(validators, method)(signer=DELEGATOR, **kwargs)
    assert currency.balance_of(address="validators") == before
    assert validators.get_reward_distribution_info(validator=NODE)["self_bond"] == 2


@pytest.mark.parametrize(
    "method,kwargs",
    [
        (
            "enqueue",
            {
                "account": NODE,
                "slash_bps": 500,
                "reason": "attack",
                "infraction_height": 0,
            },
        ),
        ("track_unbond", {"unbond_id": 1}),
        ("release_unbond", {"unbond_id": 1}),
    ],
)
def test_untrusted_account_cannot_mutate_coordinator_metadata(chain, method, kwargs):
    client, currency, _ = chain
    before = currency.balance_of(address="validators")
    with pytest.raises(AssertionError, match="Validators only"):
        getattr(client.get_contract_proxy("validator_penalties"), method)(
            signer=DELEGATOR, **kwargs
        )
    assert currency.balance_of(address="validators") == before
    assert client.raw_driver.get("validator_penalties.pending_head") is None


def test_completed_partial_work_is_restartable_and_failed_final_payment_is_atomic(
    chain,
):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    result = _evidence(validators)
    job_id = result["slash_result"]["job_id"]
    penalties = client.get_contract_proxy("validator_penalties")
    while penalties.get_pending_slash_job(job_id=job_id)["status"] != "finish":
        penalties.process_pending_slashes(max_work=1, signer="__penalty_driver__")
    client.raw_driver.commit()
    home = client.raw_driver.storage_home
    before = currency.balance_of(address="dao")
    # Corrupt only the tail link so the VM fails AFTER the outgoing transfer.
    # Atomic rollback must restore that transfer, counters and pending cursor.
    job = client.raw_driver.get(f"validator_penalties.jobs:{job_id}")
    saved_next = job.pop("next_job")
    client.raw_driver.set(f"validator_penalties.jobs:{job_id}", job)
    failed = penalties.process_pending_slashes(
        signer="__penalty_driver__", return_full_output=True
    )
    assert failed["status_code"] == 1
    assert currency.balance_of(address="dao") == before
    assert client.raw_driver.get("validator_penalties.pending_head") == job_id
    assert client.raw_driver.get(f"validator_penalties.pending_counts:{NODE}") == 1
    job["next_job"] = saved_next
    client.raw_driver.set(f"validator_penalties.jobs:{job_id}", job)
    client.raw_driver.commit()
    # Close every owner before opening the durable store, as a process restart does.
    client.close()
    from contracting.local import ContractingClient

    reopened = ContractingClient(storage_home=home)
    validator = reopened.get_contract_proxy("validators")
    coordinator = reopened.get_contract_proxy("validator_penalties")
    _drain(reopened, validator)
    assert reopened.get_contract_proxy("currency").balance_of(
        address="dao"
    ) == before + Decimal("0.3")
    assert (
        coordinator.process_pending_slashes(signer="__penalty_driver__")["processed"]
        == 0
    )
    reopened.close()


def test_one_work_budget_is_shared_by_multiple_jobs(chain):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(10):
        validators.undelegate(validator=NODE, amount=Decimal("0.01"), signer=DELEGATOR)
    first = _evidence(validators)
    second = _evidence(validators, evidence_id="second", kind="LIGHT_CLIENT_ATTACK")
    penalties = client.get_contract_proxy("validator_penalties")

    progress = penalties.process_pending_slashes(signer="__penalty_driver__")

    assert progress["processed"] == 32
    assert progress["completed"] == 1
    assert progress["head"] == second["slash_result"]["job_id"]
    assert (
        penalties.get_pending_slash_job(job_id=first["slash_result"]["job_id"])[
            "status"
        ]
        == "complete"
    )
    remaining = penalties.get_pending_slash_job(job_id=progress["head"])
    assert remaining["status"] == "collect" and remaining["cursor"] == 8
    _drain(client, validators)


@pytest.mark.parametrize("bps", [1, 3333, 10000])
def test_tiny_and_fully_slashed_positions_preserve_exact_cumulative_rounding(
    chain, bps
):
    from decimal import ROUND_DOWN, localcontext

    client, currency, validators = chain
    unit = Decimal("1e-30")
    _bond(currency, validators, amount=unit)
    validators.delegate(validator=NODE, amount=3 * unit, signer=DELEGATOR)
    validators.undelegate(validator=NODE, amount=unit, signer=DELEGATOR)
    validators.undelegate(validator=NODE, amount=unit, signer=DELEGATOR)
    validators.propose_vote(
        type_of_vote="slash_member",
        arg={"member": NODE, "slash_bps": bps, "infraction_height": 0},
        signer=NODE,
    )
    queued = validators.vote(proposal_id=1, vote="yes", signer=OTHER)["result"]
    _drain(client, validators)
    job = client.get_contract_proxy("validator_penalties").get_pending_slash_job(
        job_id=queued["job_id"]
    )
    with localcontext() as context:
        context.prec = 100
        expected = (4 * unit * bps / 10000).quantize(unit, rounding=ROUND_DOWN)
        stake = validators.get_reward_distribution_info(validator=NODE)
        pending = [
            validators.get_pending_unbond(unbond_id=identifier)["amount"]
            for identifier in [1, 2]
        ]
        assert all(amount >= 0 for amount in pending)
        assert stake["self_bond"] >= 0 and stake["total_delegated"] >= 0
        assert (
            stake["self_bond"] + stake["total_delegated"] + sum(pending)
            == 4 * unit - expected
        )
        assert job["slash_amount"] == expected
        assert (
            stake["self_bond"] + stake["total_delegated"]
            == 2 * unit - job["self_bond_slashed"] - job["delegated_slashed"]
        )
    summary = validators.get_validator(account=NODE)
    assert summary["pending_unbond_total"] == sum(pending)


def test_returned_job_metadata_cannot_mutate_the_pending_job(chain):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=2, signer=DELEGATOR)
    validators.undelegate(validator=NODE, amount=1, signer=DELEGATOR)
    queued = _evidence(validators)["slash_result"]
    client.submit(
        "@export\ndef tamper(job_id: int):\n"
        '    job = importlib.import_module("validator_penalties").get_pending_slash_job(job_id=job_id)\n'
        '    job["member"] = ctx.caller\n'
        '    job["destination"] = ctx.caller\n'
        '    job["slash_bps"] = 10000\n'
        "    return job\n",
        name="con_job_tamper",
    )
    client.get_contract_proxy("con_job_tamper").tamper(
        job_id=queued["job_id"], signer=DELEGATOR
    )
    stored = client.get_contract_proxy("validator_penalties").get_pending_slash_job(
        job_id=queued["job_id"]
    )
    assert (
        stored["member"] == NODE
        and stored["destination"] == "dao"
        and stored["slash_bps"] == 500
    )
    _drain(client, validators)


def test_later_penalty_skips_a_fully_slashed_pending_pool(chain):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(40):
        validators.undelegate(validator=NODE, amount=Decimal("0.01"), signer=DELEGATOR)
    job_ids = []
    for proposal_id in [1, 2]:
        validators.propose_vote(
            type_of_vote="slash_member",
            arg={"member": NODE, "slash_bps": 10000, "infraction_height": 0},
            signer=NODE,
        )
        job_ids.append(
            validators.vote(proposal_id=proposal_id, vote="yes", signer=OTHER)[
                "result"
            ]["job_id"]
        )
    penalties = client.get_contract_proxy("validator_penalties")
    while client.raw_driver.get("validator_penalties.pending_head") == job_ids[0]:
        penalties.process_pending_slashes(max_work=1, signer="__penalty_driver__")
    progress = penalties.process_pending_slashes(signer="__penalty_driver__")
    assert progress["processed"] < 10 and progress["completed"] == 1
    assert penalties.get_pending_slash_job(job_id=job_ids[1])["slash_amount"] == 0
    assert validators.get_validator(account=NODE)["total_slashed"] == 6


def test_a_budget_boundary_never_exposes_only_one_live_stake_part_slashed(chain):
    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(3):
        validators.undelegate(validator=NODE, amount=Decimal("0.01"), signer=DELEGATOR)
    validators.propose_vote(
        type_of_vote="slash_member",
        arg={"member": NODE, "slash_bps": 500, "infraction_height": 0},
        signer=NODE,
    )
    validators.vote(proposal_id=1, vote="yes", signer=OTHER)
    penalties = client.get_contract_proxy("validator_penalties")
    penalties.process_pending_slashes(max_work=4, signer="__penalty_driver__")
    penalties.process_pending_slashes(max_work=1, signer="__penalty_driver__")
    stake = validators.get_reward_distribution_info(validator=NODE)
    assert stake["self_bond"] == Decimal("1.9")
    assert stake["total_delegated"] == Decimal("3.7715")
    _drain(client, validators)


def test_each_committed_batch_conserves_principal_and_reserved_slash(chain):
    from decimal import localcontext

    client, currency, validators = chain
    _bond(currency, validators)
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(7):
        validators.undelegate(validator=NODE, amount=Decimal("0.01"), signer=DELEGATOR)
    first = _evidence(validators)["slash_result"]["job_id"]
    second = _evidence(validators, evidence_id="second", kind="LIGHT_CLIENT_ATTACK")[
        "slash_result"
    ]["job_id"]
    penalties = client.get_contract_proxy("validator_penalties")
    while client.raw_driver.get("validator_penalties.pending_head") is not None:
        penalties.process_pending_slashes(max_work=3, signer="__penalty_driver__")
        client.raw_driver.commit()
        info = validators.get_reward_distribution_info(validator=NODE)
        with localcontext() as context:
            context.prec = 100
            pending = sum(
                Decimal(str(validators.get_pending_unbond(unbond_id=i)["amount"]))
                for i in range(1, 8)
            )
            reserved = sum(
                Decimal(str(job["allocated_slash"]))
                for job in [
                    penalties.get_pending_slash_job(job_id=i) for i in [first, second]
                ]
                if job["status"] != "complete"
            )
            principal = (
                Decimal(str(info["self_bond"]))
                + Decimal(str(info["total_delegated"]))
                + pending
            )
            assert principal + reserved == Decimal(
                str(currency.balance_of(address="validators"))
            )
            assert (
                validators.get_validator(account=NODE)["pending_unbond_total"]
                == pending
            )


def test_an_exited_validator_cannot_register_again_during_its_pending_penalty(chain):
    from xian_runtime_types.time import Datetime

    client, currency, validators = chain
    _bond(currency, validators)
    validators.announce_leave(
        signer=NODE, environment={"now": Datetime(2026, 12, 1), "block_num": 1}
    )
    validators.leave(
        signer=NODE, environment={"now": Datetime(2026, 12, 9), "block_num": 2}
    )
    validators.apply_evidence_penalty(
        member=NODE,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="late",
        evidence_height=0,
        signer="__evidence_penalty_driver__",
        environment={"now": Datetime(2026, 12, 10), "block_num": 3},
    )
    currency.transfer(amount=1000, to=NODE, signer="founder")
    currency.approve(amount=1000, to="validators", signer=NODE)
    with pytest.raises(AssertionError, match="penalty pending"):
        validators.register(signer=NODE)
    assert validators.get_validator(account=NODE)["status"] == "left"
    _drain(client, validators)
    validators.register(signer=NODE)
    assert validators.get_validator(account=NODE)["status"] == "pending"


def test_full_pool_batched_penalty_and_final_rebalance_fit_the_chi_cap(chain):
    from test_validator_launch_policy import _fill_selection_pool

    client, currency, validators = chain
    _bond(currency, validators)
    _fill_selection_pool(client, currency, validators)
    validators.propose_vote(
        type_of_vote="update_policy",
        arg={
            "selection_mode": "auto_top_n",
            "max_validators": 64,
            "max_active_set_churn": 64,
            "max_new_power_bps": 10000,
        },
        signer=NODE,
    )
    validators.vote(proposal_id=1, vote="yes", signer=OTHER)
    assert len(validators.get_members()) == 64
    validators.delegate(validator=NODE, amount=4, signer=DELEGATOR)
    for _ in range(128):
        validators.undelegate(validator=NODE, amount=Decimal("0.01"), signer=DELEGATOR)
    _evidence(validators)
    coordinator = client.get_contract_proxy("validator_penalties")
    costs = []
    while client.raw_driver.get("validator_penalties.pending_head") is not None:
        result = coordinator.process_pending_slashes(
            signer="__penalty_driver__",
            metering=True,
            chi=200_000,
            return_full_output=True,
        )
        assert result["status_code"] == 0, result["result"]
        assert result["result"]["processed"] <= 32
        assert result["chi_used"] < 180_000
        costs.append(result["chi_used"])
        assert len(costs) < 20
    assert len(costs) > 1
    assert coordinator.get_pending_slash_job(job_id=1)["slash_amount"] == Decimal("0.3")
    print(f"full-pool penalty batches={len(costs)} chi={costs}")
