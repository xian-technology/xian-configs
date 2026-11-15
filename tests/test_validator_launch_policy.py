"""The validator-set launch policy: manual start, minimum stake, bounded churn."""

import json
from pathlib import Path

import pytest
from contracting.local import ContractingClient

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
NODE1 = "a1" * 32
NODE2 = "b2" * 32
CANDIDATES = [f"{index:02x}" * 32 for index in range(16, 22)]


@pytest.fixture
def client(tmp_path):
    client = ContractingClient(storage_home=tmp_path)
    client.flush()
    return client


def _submit(client, name, args=None):
    source = (CONTRACTS_DIR / f"{name}.s.py").read_text(encoding="utf-8")
    client.submit(source, name=name, constructor_args=args or {})
    return client.get_contract_proxy(name)


def _deploy(client, **policy):
    currency = _submit(client, "currency", {"vk": "founder"})
    for name in ("dao", "rewards"):
        _submit(client, name)
    _submit(client, "chi_cost", {"initial_rate": 20})
    validators = _submit(
        client,
        "validators",
        {"genesis_nodes": [NODE1, NODE2], "genesis_registration_fee": 1000, **policy},
    )
    return currency, validators


def _register(client, currency, validators, account, bond=0, delegated=0):
    currency.transfer(amount=1000 + bond + delegated + 1, to=account, signer="founder")
    currency.approve(amount=1000 + bond, to="validators", signer=account)
    validators.register(signer=account)
    if bond:
        validators.bond_self(amount=bond, signer=account)
    if delegated:
        currency.transfer(amount=delegated, to="delegator", signer="founder")
        currency.approve(amount=delegated, to="validators", signer="delegator")
        validators.delegate(validator=account, amount=delegated, signer="delegator")


def test_filling_empty_slots_counts_against_the_churn_limit(client):
    currency, validators = _deploy(
        client,
        selection_mode="auto_top_n",
        max_validators=7,
        max_active_set_churn=2,
        max_new_power_bps=10000,
    )
    for account in CANDIDATES[:5]:
        _register(client, currency, validators, account, bond=10)

    result = validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert len(result["activated"]) == 2
    assert len(validators.get_members()) == 4
    validators.rebalance(signer=NODE1, environment={"block_num": 2})
    assert len(validators.get_members()) == 6


def test_a_zero_churn_limit_admits_no_one_automatically(client):
    currency, validators = _deploy(client, selection_mode="auto_top_n", max_active_set_churn=0)
    _register(client, currency, validators, CANDIDATES[0], bond=10)

    validators.rebalance(signer=NODE1, environment={"block_num": 1})

    assert validators.get_members() == [NODE1, NODE2]


def test_manual_add_member_requires_the_minimum_stake(client):
    currency, validators = _deploy(client, min_self_bond=100, min_total_bond=300)
    candidate = CANDIDATES[0]
    _register(client, currency, validators, candidate, bond=99, delegated=500)
    with pytest.raises(AssertionError, match="minimum self bond"):
        validators.propose_vote(type_of_vote="add_member", arg=candidate, signer=NODE1)

    currency.transfer(amount=1, to=candidate, signer="founder")
    currency.approve(amount=1, to="validators", signer=candidate)
    validators.bond_self(amount=1, signer=candidate)
    validators.propose_vote(type_of_vote="add_member", arg=candidate, signer=NODE1)
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert candidate in validators.get_members()


def test_manual_add_member_requires_the_minimum_total_bond(client):
    currency, validators = _deploy(client, min_self_bond=100, min_total_bond=300)
    _register(client, currency, validators, CANDIDATES[0], bond=100, delegated=199)

    with pytest.raises(AssertionError, match="minimum total bond"):
        validators.propose_vote(type_of_vote="add_member", arg=CANDIDATES[0], signer=NODE1)


def test_an_add_member_vote_is_rejected_when_the_stake_fell_below_the_minimum(client):
    currency, validators = _deploy(client, min_self_bond=100)
    candidate = CANDIDATES[0]
    _register(client, currency, validators, candidate, bond=100)
    validators.propose_vote(type_of_vote="add_member", arg=candidate, signer=NODE1)
    validators.unbond_self(amount=1, signer=candidate)

    result = validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    assert result["status"] == "rejected"
    assert candidate not in validators.get_members()


def _mainnet_validator_args():
    bundle = json.loads((CONTRACTS_DIR / "contracts_mainnet.json").read_text())
    [validators] = [c for c in bundle["contracts"] if c["name"] == "validators"]
    return validators["constructor_args"]


def test_mainnet_starts_manual_with_a_minimum_stake():
    args = _mainnet_validator_args()

    assert args["selection_mode"] == "manual"
    assert args["min_self_bond"] > 0
    assert args["min_total_bond"] >= args["min_self_bond"]
    assert args["max_active_set_churn"] >= 1


def test_mainnet_registrants_cannot_take_the_set(client):
    """rv-genesis' sybil scenario: twelve fresh registrants with a token of bond."""
    args = _mainnet_validator_args()
    currency = _submit(client, "currency", {"vk": "founder"})
    for name in ("dao", "rewards"):
        _submit(client, name)
    _submit(client, "chi_cost", {"initial_rate": 20})
    validators = _submit(client, "validators", args)
    boot = args["genesis_nodes"][0]
    fee = args["genesis_registration_fee"]
    for index in range(1, 13):
        attacker = f"{index:02x}" * 32
        currency.transfer(amount=fee + 1, to=attacker, signer="founder")
        currency.approve(amount=fee + 1, to="validators", signer=attacker)
        validators.register(signer=attacker, environment={"block_num": 10})
        validators.bond_self(amount=1, signer=attacker, environment={"block_num": 10})

    with pytest.raises(AssertionError, match="Auto selection disabled"):
        validators.rebalance(signer="sys", environment={"block_num": 1440})
    with pytest.raises(AssertionError, match="Validators only"):
        validators.propose_vote(type_of_vote="add_member", arg="01" * 32, signer="01" * 32)
    with pytest.raises(AssertionError, match="minimum self bond"):
        validators.propose_vote(type_of_vote="add_member", arg="01" * 32, signer=boot)
    assert validators.get_members() == [boot]


def test_switching_from_manual_to_automatic_selection_is_one_policy_vote(client):
    currency, validators = _deploy(
        client, min_self_bond=100, max_validators=5, max_new_power_bps=10000
    )
    for node in (NODE1, NODE2):
        currency.transfer(amount=100, to=node, signer="founder")
        currency.approve(amount=100, to="validators", signer=node)
        validators.bond_self(amount=100, signer=node)
    for account in CANDIDATES[:3]:
        _register(client, currency, validators, account, bond=100)

    validators.propose_vote(
        type_of_vote="update_policy", arg={"selection_mode": "auto_top_n"}, signer=NODE1
    )
    validators.vote(proposal_id=1, vote="yes", signer=NODE2)

    members = validators.get_members()
    assert NODE1 in members and NODE2 in members
    # The switch's own rebalance admits at most the churn limit (1).
    assert len(members) == 3
