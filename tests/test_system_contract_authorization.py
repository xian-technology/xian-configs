from decimal import Decimal, ROUND_DOWN, localcontext
from pathlib import Path

import pytest
from contracting.local import ContractingClient
from xian_runtime_types.time import Datetime


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"


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
            "genesis_nodes": ["node1"],
            "genesis_registration_fee": 1000,
            **(constructor_args or {}),
        },
    )
    return client.get_contract_proxy("currency"), validators


@pytest.mark.parametrize("rate", [Decimal("7.5"), Decimal("7")])
def test_chi_cost_proposal_rejects_values_the_chi_cost_contract_cannot_store(client, rate):
    _, validators = _deploy_validators(client, {"genesis_nodes": ["node1", "node2"]})

    with pytest.raises(AssertionError, match="Chi cost must be an integer"):
        validators.propose_vote(type_of_vote="chi_cost_change", arg=rate, signer="node1")

    assert validators.total_votes.get() == 0
    assert client.get_contract_proxy("chi_cost").current_value() == 20


def test_chi_cost_proposal_executes_integer_rates(client):
    _, validators = _deploy_validators(client, {"genesis_nodes": ["node1", "node2"]})

    validators.propose_vote(type_of_vote="chi_cost_change", arg=7, signer="node1")
    validators.vote(proposal_id=1, vote="yes", signer="node2")

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
        client.get_contract_proxy("con_registrar").register(signer="alice")
    assert not client.raw_driver.get("validators.pending_registrations:con_registrar")
    assert currency.balance_of(address="con_registrar") == 1000

    currency.transfer(amount=1000, to="alice", signer="founder")
    currency.approve(amount=1000, to="validators", signer="alice")
    validators.register(signer="alice")
    assert client.raw_driver.get("validators.pending_registrations:alice") is True


def test_automatic_selection_keeps_announced_validator_until_leave(client):
    _, validators = _deploy_validators(
        client,
        {"genesis_nodes": ["node1", "node2"], "selection_mode": "auto_top_n"},
    )
    validators.announce_leave(
        signer="node1",
        environment={"now": Datetime(2026, 1, 1), "block_num": 1},
    )

    validators.rebalance(
        signer="node2",
        environment={"now": Datetime(2026, 1, 2), "block_num": 2},
    )
    assert validators.get_members() == ["node1", "node2"]
    assert validators.get_validator(account="node1")["status"] == "leaving"

    validators.leave(
        signer="node1",
        environment={"now": Datetime(2026, 1, 9), "block_num": 3},
    )
    validators.rebalance(
        signer="node2",
        environment={"now": Datetime(2026, 1, 9), "block_num": 4},
    )
    assert validators.get_members() == ["node2"]
    assert validators.get_validator(account="node1")["status"] == "left"


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
    for account, amount in zip(["node1", "alice", "bob", "carol"], amounts):
        currency.transfer(amount=amount, to=account, signer="founder")
        currency.approve(amount=amount, to="validators", signer=account)
        if account == "node1":
            validators.bond_self(amount=amount, signer=account)
        else:
            validators.delegate(validator="node1", amount=amount, signer=account)

    proposal = validators.propose_vote(
        type_of_vote="slash_member",
        arg={"member": "node1", "slash_bps": slash_bps},
        signer="node1",
    )
    assert proposal["status"] == "approved"
    remaining = [validators.get_validator(account="node1")["self_bond"]]
    for delegator in ["alice", "bob", "carol"]:
        remaining.append(
            validators.get_delegation(delegator=delegator, validator="node1")["amount"]
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
    _deploy_validators(client, {"genesis_nodes": ["node1", "node2"]})
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
        signer="node1",
        environment={"now": Datetime(2026, 1, 1), "block_num": 10},
    )
    with pytest.raises(AssertionError, match="activation height"):
        governance.vote(
            proposal_id=1,
            support=True,
            signer="node2",
            environment={"now": Datetime(2026, 1, 1), "block_num": 13},
        )

    proposal = governance.get_proposal(proposal_id=1)
    assert proposal["status"] == "pending"
    assert proposal["yes_votes"] == 1
    assert governance.get_patch(patch_id="late-patch")["status"] == "proposed"
    assert client.raw_driver.get("governance.scheduled_patches:12:late-patch") is None


@pytest.mark.parametrize("vote_height", [11, 12])
def test_state_patch_can_be_approved_through_activation_height(client, vote_height):
    _deploy_validators(client, {"genesis_nodes": ["node1", "node2"]})
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
        signer="node1",
        environment={"now": Datetime(2026, 1, 1), "block_num": 10},
    )
    proposal = governance.vote(
        proposal_id=1,
        support=True,
        signer="node2",
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
