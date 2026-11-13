from decimal import Decimal, ROUND_DOWN, localcontext
from pathlib import Path

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.time import Datetime


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
NODE1 = "a1" * 32
NODE2 = "b2" * 32
NODE3 = "c3" * 32
CANDIDATE = "d4" * 32
MAX_VALIDATOR_POWER = 10**12
MAX_TOTAL_VOTING_POWER = (2**63 - 1) // 8


@pytest.fixture
def client(tmp_path):
    storage_home = tmp_path / "xian"
    storage_home.mkdir(parents=True, exist_ok=True)

    client = ContractingClient(storage_home=storage_home)
    client.flush()
    return client


def submit_contract(
    client: ContractingClient,
    name: str,
    file_name: str,
    constructor_args=None,
):
    source = (CONTRACTS_DIR / file_name).read_text(encoding="utf-8")
    client.submit(
        source,
        name=name,
        constructor_args=constructor_args or {},
    )
    return client.get_contract_proxy(name)


def test_dao_payout_requires_validators(client):
    currency = submit_contract(
        client,
        "currency",
        "currency.s.py",
        {"vk": "founder"},
    )
    dao = submit_contract(client, "dao", "dao.s.py")

    with pytest.raises(AssertionError, match="Only validators"):
        dao.transfer_from_dao(
            args={"contract_name": "currency", "amount": 10, "to": "alice"},
            signer="alice",
        )

    assert currency.balance_of(address="alice") == 0
    assert currency.balance_of(address="dao") == Decimal("33333333.3")

    dao.transfer_from_dao(
        args={"contract_name": "currency", "amount": 10, "to": "alice"},
        signer="validators",
    )

    assert currency.balance_of(address="alice") == 10
    assert currency.balance_of(address="dao") == Decimal("33333323.3")


def test_currency_default_seed_preserves_distribution(client):
    currency = submit_contract(
        client,
        "currency",
        "currency.s.py",
        {"vk": "founder"},
    )

    assert currency.balance_of(address="founder") == Decimal("11111111.1")
    assert currency.balance_of(address="team_lock") == Decimal("66666666.6")
    assert currency.balance_of(address="dao") == Decimal("33333333.3")
    assert currency.metadata["total_supply"] == 111111111


def test_currency_seed_accepts_configured_genesis_balances(client):
    currency = submit_contract(
        client,
        "currency",
        "currency.s.py",
        {
            "vk": "founder",
            "initial_balances": {
                "alice": "1.25",
                "bob": "2.50",
                "dao": "3.75",
            },
            "token_metadata": {
                "token_website": "https://xian.org/mainnet",
            },
        },
    )

    assert currency.balance_of(address="founder") == 0
    assert currency.balance_of(address="alice") == Decimal("1.25")
    assert currency.balance_of(address="bob") == Decimal("2.50")
    assert currency.balance_of(address="dao") == Decimal("3.75")
    assert currency.metadata["total_supply"] == Decimal("7.50")
    assert currency.metadata["token_website"] == "https://xian.org/mainnet"


def test_chi_cost_update_requires_validators(client):
    chi_cost = submit_contract(
        client,
        "chi_cost",
        "chi_cost.s.py",
        {"initial_rate": 20},
    )

    with pytest.raises(AssertionError, match="Only validators"):
        chi_cost.set_value(new_value=7, signer="alice")

    assert chi_cost.current_value() == 20

    chi_cost.set_value(new_value=7, signer="validators")

    assert chi_cost.current_value() == 7


def test_rewards_update_requires_validators(client):
    rewards = submit_contract(client, "rewards", "rewards.s.py")
    new_split = [Decimal("0.65"), 0, 0, Decimal("0.35")]

    with pytest.raises(AssertionError, match="Only validators"):
        rewards.set_value(new_value=new_split, signer="alice")

    assert rewards.current_value() == [Decimal("0.7"), 0, 0, Decimal("0.3")]

    rewards.set_value(new_value=new_split, signer="validators")

    assert rewards.current_value() == new_split

    with pytest.raises(AssertionError, match="non-negative"):
        rewards.set_value(
            new_value=[Decimal("0.7"), Decimal("-0.1"), 0, Decimal("0.4")],
            signer="validators",
        )


def test_rewards_seed_validates_the_initial_split(client):
    with pytest.raises(AssertionError, match="non-negative"):
        submit_contract(
            client,
            "rewards",
            "rewards.s.py",
            {"initial_split": [Decimal("0.7"), Decimal("-0.1"), 0, Decimal("0.4")]},
        )


def _deploy_validators(client, constructor_args=None):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    submit_contract(client, "dao", "dao.s.py")
    submit_contract(client, "rewards", "rewards.s.py")
    submit_contract(client, "chi_cost", "chi_cost.s.py", {"initial_rate": 20})
    validators = submit_contract(
        client,
        "validators",
        "validators.s.py",
        {
            "genesis_nodes": [NODE1],
            "genesis_registration_fee": 1000,
            **(constructor_args or {}),
        },
    )
    return client.get_contract_proxy("currency"), validators


@pytest.mark.parametrize("rate", [Decimal("7.5"), Decimal("7")])
def test_chi_cost_proposal_rejects_values_the_chi_cost_contract_cannot_store(client, rate):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})

    with pytest.raises(AssertionError, match="Chi cost must be an integer"):
        validators.propose_vote(type_of_vote="chi_cost_change", arg=rate, signer=NODE1)

    assert validators.total_votes.get() == 0
    assert client.get_contract_proxy("chi_cost").current_value() == 20


def test_chi_cost_proposal_executes_integer_rates(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})

    validators.propose_vote(type_of_vote="chi_cost_change", arg=7, signer=NODE1)
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert validators.get_vote(proposal_id=1)["status"] == "approved"
    assert client.get_contract_proxy("chi_cost").current_value() == 7


def test_validator_registration_requires_the_signing_account(client):
    currency, validators = _deploy_validators(client)
    client.submit(
        "@export\n"
        "def register():\n"
        "    importlib.import_module('currency').approve(amount=1000, to='validators')\n"
        "    importlib.import_module('validators').register()\n",
        name="con_registrar",
    )
    currency.transfer(amount=1000, to="con_registrar", signer="founder")

    with pytest.raises(AssertionError, match="own account"):
        client.get_contract_proxy("con_registrar").register(signer=CANDIDATE)
    assert not client.raw_driver.get("validators.pending_registrations:con_registrar")
    assert currency.balance_of(address="con_registrar") == 1000

    currency.transfer(amount=1000, to=CANDIDATE, signer="founder")
    currency.approve(amount=1000, to="validators", signer=CANDIDATE)
    validators.register(signer=CANDIDATE)
    assert client.raw_driver.get(f"validators.pending_registrations:{CANDIDATE}") is True


def test_automatic_selection_keeps_announced_validator_until_leave(client):
    _, validators = _deploy_validators(
        client,
        {"genesis_nodes": [NODE1, NODE2], "selection_mode": "auto_top_n"},
    )
    validators.announce_leave(
        signer=NODE1,
        environment={"now": Datetime(2026, 1, 1), "block_num": 1},
    )

    validators.rebalance(
        signer=NODE2,
        environment={"now": Datetime(2026, 1, 2), "block_num": 2},
    )
    assert validators.get_members() == [NODE1, NODE2]
    assert validators.get_validator(account=NODE1)["status"] == "leaving"

    validators.leave(
        signer=NODE1,
        environment={"now": Datetime(2026, 1, 9), "block_num": 3},
    )
    validators.rebalance(
        signer=NODE2,
        environment={"now": Datetime(2026, 1, 9), "block_num": 4},
    )
    assert validators.get_members() == [NODE2]
    assert validators.get_validator(account=NODE1)["status"] == "left"


@pytest.mark.parametrize("required", [0, -1, 3])
def test_vault_seed_requires_attainable_positive_quorum(client, required):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    with pytest.raises(AssertionError, match="Requirement"):
        submit_contract(
            client,
            "team_lock",
            "vault.s.py",
            {"initial_owners": "alice,bob", "initial_required_signatures": required},
        )


def test_vault_cannot_remove_last_owner(client):
    currency = submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    vault = submit_contract(
        client,
        "team_lock",
        "vault.s.py",
        {"initial_owners": "alice", "initial_required_signatures": 1},
    )
    vault.submit_transaction(to="alice", tx_type="removeOwner", signer="alice")
    with pytest.raises(AssertionError, match="last owner"):
        vault.execute_transaction(tx_id=1, signer="alice")

    assert vault.owner_count.get() == 1
    assert vault.required_signatures.get() == 1
    assert vault.owners["alice"] is True
    vault.submit_transaction(to="alice", amount=1, signer="alice")
    vault.execute_transaction(tx_id=2, signer="alice")
    assert currency.balance_of(address="alice") == 1


@pytest.mark.parametrize("owners", ["", "alice,alice", "alice, ,bob"])
def test_vault_seed_requires_distinct_nonempty_owners(client, owners):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    with pytest.raises(AssertionError, match="owner"):
        submit_contract(
            client,
            "team_lock",
            "vault.s.py",
            {"initial_owners": owners, "initial_required_signatures": 1},
        )


@pytest.mark.parametrize(
    "stake_amounts,slash_bps",
    [
        (["1e-30", "1e-30", "1e-30", "1e-30"], 5000),
        (["1e-30", "2e-30", "3e-30", "1e-30"], 5000),
        (["1e-30", "1e-30", "2e-30", "3e-30"], 10000),
        (["1e-30", "1e-30", "1e-30", "1e-30"], 1),
        (["100", "900", "125", "0.5"], 500),
        (["100", "1e-30", "2e-30", "1"], 3333),
    ],
    ids=["tiny", "uneven", "full-slash", "rounded-zero", "normal", "mixed"],
)
def test_slashing_keeps_nonnegative_balances_and_conserves_value(client, stake_amounts, slash_bps):
    currency, validators = _deploy_validators(client)
    amounts = [Decimal(amount) for amount in stake_amounts]
    for account, amount in zip([NODE1, "alice", "bob", "carol"], amounts):
        currency.transfer(amount=amount, to=account, signer="founder")
        currency.approve(amount=amount, to="validators", signer=account)
        if account == NODE1:
            validators.bond_self(amount=amount, signer=account)
        else:
            validators.delegate(validator=NODE1, amount=amount, signer=account)

    proposal = validators.propose_vote(
        type_of_vote="slash_member",
        arg={"member": NODE1, "slash_bps": slash_bps},
        signer=NODE1,
    )
    assert proposal["status"] == "approved"
    remaining = [validators.get_validator(account=NODE1)["self_bond"]]
    for delegator in ["alice", "bob", "carol"]:
        remaining.append(
            validators.get_delegation(delegator=delegator, validator=NODE1)["amount"]
        )
    assert all(amount >= 0 for amount in remaining)
    assert all(after <= before for before, after in zip(amounts, remaining))
    with localcontext() as context:
        context.prec = 100
        expected_slash = (sum(amounts) * slash_bps / 10000).quantize(
            Decimal("1e-30"), rounding=ROUND_DOWN
        )
        assert proposal["result"]["slash_amount"] == expected_slash
        assert sum(remaining) == sum(amounts) - expected_slash
    assert currency.balance_of(address="validators") == sum(remaining)


def test_state_patch_votes_reject_passed_activation_height(client):
    _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    governance = submit_contract(
        client,
        "governance",
        "governance.s.py",
        {
            "membership_contract_name": "validators",
            "approval_threshold_numerator": 1,
            "approval_threshold_denominator": 1,
            "min_patch_delay_blocks": 2,
        },
    )
    governance.propose_state_patch(
        patch_id="late-patch",
        bundle_hash="abc123",
        activation_height=12,
        signer=NODE1,
        environment={"now": Datetime(2026, 1, 1), "block_num": 10},
    )
    with pytest.raises(AssertionError, match="activation height"):
        governance.vote(
            proposal_id=1,
            support=True,
            signer=NODE2,
            environment={"now": Datetime(2026, 1, 1), "block_num": 13},
        )

    proposal = governance.get_proposal(proposal_id=1)
    assert proposal["status"] == "pending"
    assert proposal["yes_votes"] == 1
    assert governance.get_patch(patch_id="late-patch")["status"] == "proposed"
    assert client.raw_driver.get("governance.scheduled_patches:12:late-patch") is None


@pytest.mark.parametrize("vote_height", [11, 12])
def test_state_patch_can_be_approved_through_activation_height(client, vote_height):
    _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    governance = submit_contract(
        client,
        "governance",
        "governance.s.py",
        {
            "membership_contract_name": "validators",
            "approval_threshold_numerator": 1,
            "approval_threshold_denominator": 1,
            "min_patch_delay_blocks": 2,
        },
    )
    governance.propose_state_patch(
        patch_id="on-time-patch",
        bundle_hash="abc123",
        activation_height=12,
        signer=NODE1,
        environment={"now": Datetime(2026, 1, 1), "block_num": 10},
    )
    proposal = governance.vote(
        proposal_id=1,
        support=True,
        signer=NODE2,
        environment={"now": Datetime(2026, 1, 1), "block_num": vote_height},
    )
    assert proposal["status"] == "approved"
    assert governance.get_patch(patch_id="on-time-patch")["status"] == "approved"
    assert client.raw_driver.get("governance.scheduled_patches:12:on-time-patch") is True


def test_vault_counts_only_current_owners_toward_transaction_quorum(client):
    currency = submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    vault = submit_contract(
        client,
        "team_lock",
        "vault.s.py",
        {"initial_owners": "alice,bob,carol", "initial_required_signatures": 2},
    )
    vault.submit_transaction(to="recipient", amount=100, signer="alice")
    vault.approve_transaction(tx_id=1, signer="bob")
    vault.submit_transaction(to="bob", tx_type="removeOwner", signer="alice")
    vault.approve_transaction(tx_id=2, signer="carol")
    vault.execute_transaction(tx_id=2, signer="alice")

    with pytest.raises(AssertionError, match="Not enough approvals"):
        vault.execute_transaction(tx_id=1, signer="alice")
    assert currency.balance_of(address="recipient") == 0
    assert vault.transactions[1, "executed"] is False

    vault.approve_transaction(tx_id=1, signer="carol")
    vault.execute_transaction(tx_id=1, signer="alice")
    assert currency.balance_of(address="recipient") == 100


def test_vault_approvals_and_execution_are_single_use(client):
    currency = submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    vault = submit_contract(
        client,
        "team_lock",
        "vault.s.py",
        {"initial_owners": "alice,bob", "initial_required_signatures": 2},
    )
    vault.submit_transaction(to="recipient", amount=100, signer="alice")
    vault.approve_transaction(tx_id=1, signer="bob")
    assert vault.transactions[1, "approvals"] == 2
    assert vault.transactions[1, "approvers", "alice"] is True
    assert vault.transactions[1, "approvers", "bob"] is True
    with pytest.raises(AssertionError, match="Already approved"):
        vault.approve_transaction(tx_id=1, signer="bob")
    vault.execute_transaction(tx_id=1, signer="alice")
    assert vault.transactions[1, "executed"] is True
    with pytest.raises(AssertionError, match="already executed"):
        vault.execute_transaction(tx_id=1, signer="alice")
    assert currency.balance_of(address="recipient") == 100


def test_vault_owner_changes_keep_count_and_quorum_consistent(client):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    vault = submit_contract(
        client,
        "team_lock",
        "vault.s.py",
        {"initial_owners": "alice,bob", "initial_required_signatures": 2},
    )
    vault.submit_transaction(to="carol", tx_type="addOwner", signer="alice")
    vault.approve_transaction(tx_id=1, signer="bob")
    vault.execute_transaction(tx_id=1, signer="alice")
    assert vault.owners["carol"] is True
    assert vault.owner_count.get() == 3
    vault.submit_transaction(to="carol", tx_type="addOwner", signer="alice")
    vault.approve_transaction(tx_id=2, signer="bob")
    with pytest.raises(AssertionError, match="already an owner"):
        vault.execute_transaction(tx_id=2, signer="alice")

    vault.submit_transaction(to="bob", tx_type="removeOwner", signer="alice")
    vault.approve_transaction(tx_id=3, signer="carol")
    vault.execute_transaction(tx_id=3, signer="alice")
    assert vault.owner_count.get() == 2
    vault.submit_transaction(to="carol", tx_type="removeOwner", signer="alice")
    vault.approve_transaction(tx_id=4, signer="carol")
    vault.execute_transaction(tx_id=4, signer="alice")
    assert vault.owner_count.get() == 1
    assert vault.required_signatures.get() == 1
    with pytest.raises(AssertionError, match="Only owners"):
        vault.submit_transaction(to="bob", amount=1, signer="carol")


@pytest.mark.parametrize("requirement,allowed", [(0, False), (1, True), (2, True), (3, False)])
def test_vault_quorum_changes_require_positive_attainable_value(client, requirement, allowed):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    vault = submit_contract(
        client,
        "team_lock",
        "vault.s.py",
        {"initial_owners": "alice,bob", "initial_required_signatures": 2},
    )
    vault.submit_transaction(amount=requirement, tx_type="changeRequirement", signer="alice")
    vault.approve_transaction(tx_id=1, signer="bob")
    if allowed:
        vault.execute_transaction(tx_id=1, signer="alice")
        assert vault.required_signatures.get() == requirement
    else:
        with pytest.raises(AssertionError, match="Requirement"):
            vault.execute_transaction(tx_id=1, signer="alice")
        assert vault.required_signatures.get() == 2


@pytest.mark.parametrize("new_owner", ["", " ", "\t"])
def test_vault_cannot_add_empty_owner(client, new_owner):
    submit_contract(client, "currency", "currency.s.py", {"vk": "founder"})
    vault = submit_contract(
        client,
        "team_lock",
        "vault.s.py",
        {"initial_owners": "alice", "initial_required_signatures": 1},
    )
    vault.submit_transaction(to=new_owner, tx_type="addOwner", signer="alice")
    with pytest.raises(AssertionError, match="owner"):
        vault.execute_transaction(tx_id=1, signer="alice")
    assert vault.owner_count.get() == 1
    assert vault.required_signatures.get() == 1


def _fund_candidate(client, account=CANDIDATE, amount=5000):
    currency = client.get_contract_proxy("currency")
    currency.transfer(amount=amount, to=account, signer="founder")
    currency.approve(amount=amount, to="validators", signer=account)


def _validator_power(client, account):
    return client.raw_driver.get(f"validators.powers:{account}")


@pytest.mark.parametrize("account", [CANDIDATE.upper(), "D4" + "d4" * 31, "alice", "d4" * 31])
def test_registration_requires_a_canonical_lowercase_key(client, account):
    _deploy_validators(client)
    _fund_candidate(client, account)
    validators = client.get_contract_proxy("validators")

    with pytest.raises(AssertionError, match="canonical"):
        validators.register(signer=account)

    assert not client.raw_driver.get(f"validators.pending_registrations:{account}")


def test_case_variant_cannot_take_a_second_validator_seat(client):
    _, validators = _deploy_validators(
        client,
        {"genesis_nodes": [NODE1, NODE2], "selection_mode": "auto_top_n"},
    )
    _fund_candidate(client, NODE1.upper())

    with pytest.raises(AssertionError, match="canonical"):
        validators.register(signer=NODE1.upper(), environment={"block_num": 1})
    validators.rebalance(signer=NODE1, environment={"block_num": 2})

    assert validators.get_members() == [NODE1, NODE2]


@pytest.mark.parametrize("genesis_nodes", [[NODE1.upper()], ["node1"], [NODE1, ""]])
def test_seed_requires_canonical_genesis_validator_keys(client, genesis_nodes):
    with pytest.raises(AssertionError, match="canonical"):
        _deploy_validators(client, {"genesis_nodes": genesis_nodes})


def test_add_member_activates_with_the_power_fixed_at_proposal(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2, NODE3]})
    _fund_candidate(client)
    validators.register(requested_validator_power=10, signer=CANDIDATE)
    proposal = validators.propose_vote(type_of_vote="add_member", arg=CANDIDATE, signer=NODE1)
    assert proposal["member_power"] == 10
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    validators.update_registration(requested_validator_power=1000, signer=CANDIDATE)
    validators.vote(proposal_id=1, vote="yes", signer=NODE3)

    assert CANDIDATE in validators.get_members()
    assert _validator_power(client, CANDIDATE) == 10


@pytest.mark.parametrize(
    "power,allowed",
    [
        (1, True),
        (MAX_VALIDATOR_POWER, True),
        (0, False),
        (MAX_VALIDATOR_POWER + 1, False),
        (2**70, False),
    ],
)
def test_requested_validator_power_is_capped(client, power, allowed):
    _, validators = _deploy_validators(client)
    _fund_candidate(client)
    if allowed:
        validators.register(requested_validator_power=power, signer=CANDIDATE)
        validators.update_registration(requested_validator_power=power, signer=CANDIDATE)
        assert validators.get_validator(account=CANDIDATE)["requested_power"] == power
        return

    with pytest.raises(AssertionError, match="Validator power"):
        validators.register(requested_validator_power=power, signer=CANDIDATE)
    validators.register(signer=CANDIDATE)
    with pytest.raises(AssertionError, match="Validator power"):
        validators.update_registration(requested_validator_power=power, signer=CANDIDATE)
    assert validators.get_validator(account=CANDIDATE)["requested_power"] == 10


def test_governance_cannot_set_power_above_the_cap(client):
    _, validators = _deploy_validators(client)

    with pytest.raises(AssertionError, match="Validator power"):
        validators.propose_vote(
            type_of_vote="set_member_power",
            arg={"member": NODE1, "power": MAX_VALIDATOR_POWER + 1},
            signer=NODE1,
        )
    validators.propose_vote(
        type_of_vote="set_member_power",
        arg={"member": NODE1, "power": MAX_VALIDATOR_POWER},
        signer=NODE1,
    )
    assert _validator_power(client, NODE1) == MAX_VALIDATOR_POWER


@pytest.mark.parametrize("power,allowed", [(5, True), (6, False)])
def test_power_changes_keep_total_within_consensus_limit(client, power, allowed):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    client.raw_driver.set(f"validators.powers:{NODE2}", MAX_TOTAL_VOTING_POWER - 5)
    arg = {"member": NODE1, "power": power}
    validators.propose_vote(type_of_vote="set_member_power", arg=arg, signer=NODE1)

    if allowed:
        validators.vote(proposal_id=1, vote="yes", signer=NODE2)
        assert _validator_power(client, NODE1) == power
        return
    with pytest.raises(AssertionError, match="consensus maximum"):
        validators.vote(proposal_id=1, vote="yes", signer=NODE2)
    assert _validator_power(client, NODE1) == 10


def test_genesis_power_is_capped(client):
    with pytest.raises(AssertionError, match="Validator power"):
        _deploy_validators(client, {"genesis_powers": {NODE1: MAX_VALIDATOR_POWER + 1}})


def test_stake_weighted_power_is_capped(client):
    submit_contract(
        client,
        "currency",
        "currency.s.py",
        {"vk": "founder", "initial_balances": {NODE1: MAX_VALIDATOR_POWER * 2}},
    )
    submit_contract(client, "dao", "dao.s.py")
    submit_contract(client, "rewards", "rewards.s.py")
    submit_contract(client, "chi_cost", "chi_cost.s.py", {"initial_rate": 20})
    validators = submit_contract(
        client,
        "validators",
        "validators.s.py",
        {
            "genesis_nodes": [NODE1],
            "genesis_registration_fee": 1000,
            "selection_mode": "auto_top_n",
            "power_mode": "stake_weighted",
        },
    )
    client.get_contract_proxy("currency").approve(
        amount=MAX_VALIDATOR_POWER * 2, to="validators", signer=NODE1
    )
    validators.bond_self(amount=MAX_VALIDATOR_POWER * 2, signer=NODE1)
    validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert _validator_power(client, NODE1) == MAX_VALIDATOR_POWER


def test_last_active_validator_cannot_leave(client):
    _, validators = _deploy_validators(client)
    validators.announce_leave(signer=NODE1, environment={"now": Datetime(2026, 1, 1)})

    with pytest.raises(AssertionError, match="last active validator"):
        validators.leave(signer=NODE1, environment={"now": Datetime(2026, 1, 9)})

    assert validators.get_members() == [NODE1]


@pytest.mark.parametrize(
    "type_of_vote,arg",
    [("remove_member", NODE1), ("jail_member", {"member": NODE1})],
)
def test_governance_cannot_remove_or_jail_the_last_active_validator(client, type_of_vote, arg):
    _, validators = _deploy_validators(client)

    with pytest.raises(AssertionError, match="last active validator"):
        validators.propose_vote(type_of_vote=type_of_vote, arg=arg, signer=NODE1)

    assert validators.get_members() == [NODE1]
    assert validators.get_validator(account=NODE1)["jailed"] is False


def test_evidence_slashes_but_does_not_jail_the_last_active_validator(client):
    currency, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    currency.transfer(amount=100, to=NODE2, signer="founder")
    currency.approve(amount=100, to="validators", signer=NODE2)
    validators.bond_self(amount=100, signer=NODE2)

    for evidence_id, member in enumerate([NODE1, NODE2]):
        result = validators.apply_evidence_penalty(
            member=member,
            infraction_type="DUPLICATE_VOTE",
            evidence_id=f"ev-{evidence_id}",
            evidence_height=5,
            signer="__evidence_penalty_driver__",
        )

    assert result["jailed_now"] is False
    assert result["slash_result"]["slash_amount"] == 5
    assert validators.get_members() == [NODE2]
    assert validators.get_validator(account=NODE2)["jailed"] is False


def test_policy_update_cannot_select_an_empty_validator_set(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    validators.propose_vote(
        type_of_vote="update_policy",
        arg={"selection_mode": "auto_top_n", "min_self_bond": 1},
        signer=NODE1,
    )

    with pytest.raises(AssertionError, match="no active validators"):
        validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert validators.get_members() == [NODE1, NODE2]
    assert validators.get_policy_config()["selection_mode"] == "manual"


def test_epoch_rebalance_retains_the_set_when_nobody_is_eligible(client):
    _, validators = _deploy_validators(
        client,
        {"genesis_nodes": [NODE1, NODE2], "selection_mode": "auto_top_n", "min_self_bond": 1},
    )

    result = validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert result["retained"] is True
    assert validators.get_members() == [NODE1, NODE2]
    with pytest.raises(AssertionError, match="Already rebalanced"):
        validators.rebalance(signer=NODE1, environment={"block_num": 1})


def test_vote_returns_the_finalized_proposal_record(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    validators.propose_vote(type_of_vote="topic_vote", arg={"topic": "x"}, signer=NODE1)

    result = validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert result["status"] == "approved"
    assert result["finalized"] is True


def test_add_member_proposal_is_rejected_when_candidate_was_jailed(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    _fund_candidate(client)
    validators.register(signer=CANDIDATE)
    validators.propose_vote(type_of_vote="add_member", arg=CANDIDATE, signer=NODE1)
    validators.propose_vote(type_of_vote="jail_member", arg={"member": CANDIDATE}, signer=NODE1)
    validators.vote(proposal_id=2, vote="yes", signer=NODE2)

    result = validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert result["status"] == "rejected"
    assert result["finalized"] is True
    assert CANDIDATE not in validators.get_members()


def test_remove_member_proposal_is_rejected_when_member_was_already_removed(client):
    currency, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2, NODE3]})
    validators.propose_vote(type_of_vote="remove_member", arg=NODE3, signer=NODE1)
    validators.propose_vote(type_of_vote="remove_member", arg=NODE3, signer=NODE1)
    for voter in [NODE2, NODE3]:
        validators.vote(proposal_id=1, vote="yes", signer=voter)
    validators.vote(proposal_id=2, vote="yes", signer=NODE2)
    balance_before = currency.balance_of(address="validators")

    result = validators.vote(proposal_id=2, vote="yes", signer=NODE3)

    assert result["status"] == "rejected"
    assert validators.get_vote(proposal_id=1)["status"] == "approved"
    assert validators.get_members() == [NODE1, NODE2]
    assert currency.balance_of(address="validators") == balance_before


def test_jail_member_proposal_is_rejected_when_member_is_already_jailed(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2, NODE3]})
    validators.propose_vote(type_of_vote="jail_member", arg={"member": NODE3}, signer=NODE1)
    validators.apply_evidence_penalty(
        member=NODE3,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        signer="__evidence_penalty_driver__",
    )

    validators.vote(proposal_id=1, vote="yes", signer=NODE2)
    result = validators.vote(proposal_id=1, vote="yes", signer=NODE3)

    assert result["status"] == "rejected"
    assert validators.get_validator(account=NODE3)["jailed"] is True


def test_token_factory_defaults_controllers_to_the_calling_contract(client):
    token_factory = submit_contract(client, "token_factory", "token_factory.s.py")
    client.submit(
        "@export\n"
        "def launch():\n"
        "    importlib.import_module('token_factory').create_token(\n"
        "        token_contract='con_launched', token_name='L', token_symbol='L',\n"
        "        initial_supply=100)\n",
        name="con_launchpad",
    )

    client.get_contract_proxy("con_launchpad").launch(signer="relayer")

    token = client.get_contract_proxy("con_launched")
    assert token.balance_of(address="con_launchpad") == 100
    assert token.balance_of(address="relayer") == 0
    assert token.operator_of() == "con_launchpad"
    assert token_factory is not None


def test_seed_requires_at_least_one_genesis_validator(client):
    with pytest.raises(AssertionError, match="at least one validator"):
        _deploy_validators(client, {"genesis_nodes": []})


def test_evidence_rebalance_retains_the_set_when_nobody_remains_eligible(client):
    currency, validators = _deploy_validators(
        client, {"selection_mode": "auto_top_n", "min_self_bond": 1}
    )
    currency.transfer(amount=1, to=NODE1, signer="founder")
    currency.approve(amount=1, to="validators", signer=NODE1)
    validators.bond_self(amount=1, signer=NODE1)

    result = validators.apply_evidence_penalty(
        member=NODE1,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        evidence_height=0,
        signer="__evidence_penalty_driver__",
        environment={"block_num": 1},
    )

    assert result["slash_result"]["slash_amount"] == Decimal("0.05")
    assert validators.get_members() == [NODE1]


def test_second_hybrid_add_member_proposal_is_rejected_after_approval(client):
    _, validators = _deploy_validators(
        client,
        {"genesis_nodes": [NODE1, NODE2], "selection_mode": "hybrid", "max_validators": 2},
    )
    _fund_candidate(client)
    validators.register(signer=CANDIDATE)
    for _ in range(2):
        validators.propose_vote(type_of_vote="add_member", arg=CANDIDATE, signer=NODE1)
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    result = validators.vote(proposal_id=2, vote="yes", signer=NODE2)

    assert validators.get_vote(proposal_id=1)["status"] == "approved"
    assert validators.get_validator(account=CANDIDATE)["status"] == "approved"
    assert result["status"] == "rejected"


def test_hybrid_approval_keeps_the_power_fixed_at_proposal(client):
    _, validators = _deploy_validators(
        client,
        {
            "genesis_nodes": [NODE1, NODE2],
            "selection_mode": "hybrid",
            "power_mode": "requested",
        },
    )
    _fund_candidate(client)
    validators.register(requested_validator_power=10, signer=CANDIDATE)
    validators.propose_vote(type_of_vote="add_member", arg=CANDIDATE, signer=NODE1)
    validators.update_registration(requested_validator_power=1000, signer=CANDIDATE)

    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert CANDIDATE in validators.get_members()
    assert _validator_power(client, CANDIDATE) == 10


@pytest.mark.parametrize(
    "type_of_vote,arg",
    [("remove_member", NODE2), ("jail_member", {"member": NODE2})],
)
def test_open_proposal_is_rejected_when_target_became_last_active_validator(
    client, type_of_vote, arg
):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2]})
    validators.propose_vote(type_of_vote=type_of_vote, arg=arg, signer=NODE1)
    validators.apply_evidence_penalty(
        member=NODE1,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        signer="__evidence_penalty_driver__",
    )

    result = validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert result["status"] == "rejected"
    assert validators.get_members() == [NODE2]
    assert validators.get_validator(account=NODE2)["jailed"] is False


def _bond(client, validators, account, amount):
    currency = client.get_contract_proxy("currency")
    currency.transfer(amount=amount, to=account, signer="founder")
    currency.approve(amount=amount, to="validators", signer=account)
    validators.bond_self(amount=amount, signer=account)


def test_epoch_rebalance_reports_a_changed_set_as_not_retained(client):
    _, validators = _deploy_validators(
        client, {"selection_mode": "auto_top_n", "min_self_bond": 1}
    )
    _bond(client, validators, NODE1, 10)
    _fund_candidate(client)
    validators.register(signer=CANDIDATE)
    validators.bond_self(amount=10, signer=CANDIDATE)

    result = validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert result["retained"] is False
    assert result["activated"] == [CANDIDATE]
    assert sorted(validators.get_members()) == sorted([NODE1, CANDIDATE])


def test_jailing_evidence_rebalances_an_automatic_set(client):
    _, validators = _deploy_validators(
        client,
        {
            "genesis_nodes": [NODE1, NODE2],
            "selection_mode": "auto_top_n",
            "min_self_bond": 1,
            "max_validators": 2,
        },
    )
    _bond(client, validators, NODE2, 10)
    _fund_candidate(client)
    validators.register(signer=CANDIDATE)
    validators.bond_self(amount=10, signer=CANDIDATE)

    result = validators.apply_evidence_penalty(
        member=NODE1,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        signer="__evidence_penalty_driver__",
    )

    assert result["applied"] is True
    assert result["jailed_now"] is True
    assert result["slash_result"] is None
    assert sorted(validators.get_members()) == sorted([NODE2, CANDIDATE])


def test_add_member_is_rejected_after_the_candidate_unregisters(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": [NODE1, NODE2, NODE3]})
    _fund_candidate(client)
    validators.register(signer=CANDIDATE)
    validators.propose_vote(type_of_vote="add_member", arg=CANDIDATE, signer=NODE1)
    validators.unregister(signer=CANDIDATE)

    validators.vote(proposal_id=1, vote="yes", signer=NODE2)
    result = validators.vote(proposal_id=1, vote="yes", signer=NODE3)

    assert result["status"] == "rejected"
    assert CANDIDATE not in validators.get_members()


def test_jailing_evidence_rebalances_even_after_this_epochs_rebalance(client):
    _, validators = _deploy_validators(
        client,
        {"genesis_nodes": [NODE1, NODE2], "selection_mode": "auto_top_n", "min_self_bond": 1},
    )
    _bond(client, validators, NODE1, 10)
    _bond(client, validators, NODE2, 10)
    validators.rebalance(signer=NODE1, environment={"block_num": 1})

    result = validators.apply_evidence_penalty(
        member=NODE1,
        infraction_type="DUPLICATE_VOTE",
        evidence_id="ev-1",
        signer="__evidence_penalty_driver__",
        environment={"block_num": 1},
    )

    assert result["jailed_now"] is True
    assert validators.get_members() == [NODE2]
