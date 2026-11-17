"""Delegator rewards are paid lazily (reward per share).

Every action here is a paid transaction through the node's block executor,
so the Rust fee path credits the validators' pools on each one, as on a
chain. The property tests run random operation sequences against the
reference model in `staking_model.py` and check the conservation invariants
after every step.
"""

from __future__ import annotations

import random
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from contracting.local import ContractingClient
from staking_model import Model, Pool
from xian.fee_policy import TxFeePolicy
from xian.processor import TxProcessor
from xian.utils.tx import transaction_bytes
from xian_runtime_types.decimal import ContractingDecimal
from xian_runtime_types.time import Timedelta

CONTRACTS_DIR = Path(__file__).absolute().parents[1] / "contracts"
NODE1 = "a1" * 32
NODE2 = "b2" * 32
NODE3 = "c3" * 32
RATE = 20
FUNDS = Decimal(10**9)


def _operator(node: str) -> str:
    return f"operator_{node[:4]}"


class Chain:
    """A validators deployment whose every action is a paid transaction."""

    def __init__(
        self, tmp_path, nodes, powers=None, commissions=None, max_commission_bps=10_000
    ):
        self.client = ContractingClient(vm_profile="xian_vm_v2", storage_home=tmp_path)
        self.client.flush()
        self.nodes = nodes
        self.height = 1
        self._submit("currency", {"vk": "founder"})
        self._submit("dao", {})
        self._submit("rewards", {"initial_split": [1, 0, 0, 0]})
        self._submit("chi_cost", {"initial_rate": RATE})
        self._submit("foundation", {"vk": "foundation"})
        self._submit(
            "validators",
            {
                "genesis_nodes": nodes,
                "genesis_registration_fee": 1000,
                "genesis_powers": powers or {node: 10 for node in nodes},
                "genesis_reward_keys": {node: _operator(node) for node in nodes},
                "max_commission_bps": max_commission_bps,
                "unbonding_period_days": 7,
            },
        )
        driver = self.client.raw_driver
        for node, bps in (commissions or {}).items():
            driver.set(f"validators.commission_bps:{node}", bps)
        driver.commit()

    def _submit(self, name, args):
        if name == "validators":
            self.client.submit(
                (CONTRACTS_DIR / "validator_penalties.s.py").read_text(),
                name="validator_penalties",
            )
        source = (CONTRACTS_DIR / f"{name}.s.py").read_text(encoding="utf-8")
        self.client.submit(source, name=name, constructor_args=args)

    def fund(self, account, amount=FUNDS):
        driver = self.client.raw_driver
        driver.set(f"currency.balances:{account}", ContractingDecimal(str(amount)))
        driver.set(
            f"currency.approvals:{account}:validators", ContractingDecimal(str(amount))
        )
        driver.commit()

    def send(self, sender, contract, function, **kwargs):
        tx = {
            "payload": {
                "sender": sender,
                "contract": contract,
                "function": function,
                "kwargs": kwargs,
                "nonce": 0,
                "chi_supplied": 100_000,
            },
            "metadata": {"signature": "sig"},
            "b_meta": {
                "nanos": self.height * 1_000_000_000,
                "height": self.height,
                "hash": "ab",
                "chain_id": "local",
            },
        }
        self.height += 1
        [response] = TxProcessor(client=self.client).process_block(
            [tx], [transaction_bytes(tx)], fee_policy=TxFeePolicy.paid_metered()
        )
        self.client.raw_driver.commit()
        return response["tx_result"]

    def call(self, sender, function, **kwargs):
        return self.send(sender, "validators", function, **kwargs)

    def get(self, key, default=0):
        value = self.client.raw_driver.get(key)
        return default if value is None else value

    def view(self, function, **kwargs):
        return getattr(self.client.get_contract_proxy("validators"), function)(**kwargs)

    def balance(self, account):
        return Decimal(str(self.get(f"currency.balances:{account}")))


def _amount(value):
    """A decimal transaction argument in wire form."""
    return {"__fixed__": format(Decimal(value).normalize(), "f")}


@pytest.fixture
def chain(tmp_path):
    chain = Chain(tmp_path, [NODE1], commissions={NODE1: 1000})
    for account in (NODE1, "alice", "bob", "carol", "sender"):
        chain.fund(account)
    return chain


def _ok(result):
    assert result["status"] == 0, result["result"]
    return result


def test_paid_transactions_credit_the_pool_not_each_delegator(chain):
    for delegator in ("alice", "bob", "carol"):
        _ok(
            chain.call(
                delegator,
                "delegate",
                validator=NODE1,
                amount=100,
                reward_key=f"rk_{delegator}",
            )
        )

    result = _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))

    records = result["reward_records"]
    assert [record["type"] for record in records] == [
        "validator_reward",
        "delegator_pool_reward",
    ]
    assert records[1]["recipient_key"] == "validators"
    assert records[1]["validator_key"] == NODE1
    assert set(result["rewards"]["delegator_pool_reward"]) == {"validators"}
    pool = Decimal(str(records[1]["value"]))
    assert Decimal(str(chain.get(f"validators.reward_pool:{NODE1}"))) >= pool > 0
    assert chain.balance("rk_alice") == 0


def test_receipt_size_does_not_grow_with_delegators(tmp_path):
    sizes = []
    for count in (1, 60):
        chain = Chain(tmp_path / str(count), [NODE1])
        chain.fund("sender")
        for index in range(count):
            delegator = f"d{index}"
            chain.fund(delegator)
            _ok(chain.call(delegator, "delegate", validator=NODE1, amount=10))
        result = _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
        sizes.append((len(result["state"]), len(result["reward_records"])))
    assert sizes[0] == sizes[1]


def test_claim_pays_the_pending_reward_to_the_reward_key(chain):
    _ok(
        chain.call(
            "alice", "delegate", validator=NODE1, amount=100, reward_key="rk_alice"
        )
    )
    _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    pending = chain.view("get_pending_rewards", delegator="alice", validator=NODE1)
    assert pending > 0

    result = _ok(chain.call("alice", "claim_rewards", validator=NODE1))

    # The claim's own fee is credited after the payout.
    assert chain.balance("rk_alice") == pending
    assert Decimal(result["result"]["__fixed__"]) == pending
    assert _ok(chain.call("bob", "claim_rewards", validator=NODE1))["result"] == 0
    assert [event["event"] for event in result["events"]][
        -1
    ] == "DelegatorRewardClaimed"
    assert chain.view("get_pending_rewards", delegator="alice", validator=NODE1) > 0


def test_delegation_changes_settle_the_pending_reward_first(chain):
    _ok(
        chain.call(
            "alice", "delegate", validator=NODE1, amount=100, reward_key="rk_alice"
        )
    )
    _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    pending = chain.view("get_pending_rewards", delegator="alice", validator=NODE1)

    _ok(
        chain.call("alice", "delegate", validator=NODE1, amount=50, reward_key="rk_new")
    )
    assert chain.balance("rk_alice") == pending
    _ok(chain.call("bob", "delegate", validator=NODE1, amount=10))
    assert chain.view("get_validator", account=NODE1)["delegator_count"] == 2

    pending = chain.view("get_pending_rewards", delegator="alice", validator=NODE1)
    _ok(chain.call("alice", "undelegate", validator=NODE1, amount=150))
    assert chain.balance("rk_new") == pending
    assert (
        chain.view("get_delegation", delegator="alice", validator=NODE1)["amount"] == 0
    )
    assert chain.view("get_validator", account=NODE1)["delegator_count"] == 1


def test_a_new_delegator_earns_nothing_from_earlier_fees(chain):
    _ok(chain.call("alice", "delegate", validator=NODE1, amount=100))
    for _ in range(3):
        _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    rate_before = Decimal(str(chain.get(f"validators.reward_per_share:{NODE1}")))

    _ok(chain.call("bob", "delegate", validator=NODE1, amount=100))

    rate_after = Decimal(str(chain.get(f"validators.reward_per_share:{NODE1}")))
    shares = Decimal(str(chain.get(f"validators.delegation_shares:bob:{NODE1}")))
    # Bob shares only the fee of his own delegation transaction.
    assert chain.view(
        "get_pending_rewards", delegator="bob", validator=NODE1
    ) <= shares * (rate_after - rate_before)


def test_slash_lowers_the_pool_and_keeps_earned_rewards_claimable(chain):
    _ok(chain.call(NODE1, "bond_self", amount=100))
    _ok(
        chain.call(
            "alice", "delegate", validator=NODE1, amount=300, reward_key="rk_alice"
        )
    )
    _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    earned = chain.view("get_pending_rewards", delegator="alice", validator=NODE1)
    shares = chain.get(f"validators.delegation_shares:alice:{NODE1}")

    result = _ok(
        chain.call(
            NODE1,
            "propose_vote",
            type_of_vote="slash_member",
            arg={"member": NODE1, "slash_bps": 5000},
        )
    )

    assert result["result"]["status"] == "approved"
    assert chain.get(f"validators.total_delegated:{NODE1}") == 150
    assert chain.get(f"validators.self_bond:{NODE1}") == 50
    assert chain.get(f"validators.delegation_shares:alice:{NODE1}") == shares
    assert (
        chain.view("get_delegation", delegator="alice", validator=NODE1)["amount"]
        == 150
    )
    assert (
        chain.view("get_pending_rewards", delegator="alice", validator=NODE1) >= earned
    )


def _slash_alone(chain, node, slash_bps):
    return _ok(
        chain.call(
            node,
            "propose_vote",
            type_of_vote="slash_member",
            arg={"member": node, "slash_bps": slash_bps},
        )
    )


def test_after_a_slash_a_delegation_buys_more_shares(chain):
    _ok(chain.call("alice", "delegate", validator=NODE1, amount=1))
    _slash_alone(chain, NODE1, 5000)

    _ok(chain.call("bob", "delegate", validator=NODE1, amount=1))

    assert chain.get(f"validators.delegation_shares:bob:{NODE1}") == 2
    assert chain.view("get_delegation", delegator="bob", validator=NODE1)["amount"] == 1
    assert chain.view("get_delegation", delegator="alice", validator=NODE1)[
        "amount"
    ] == Decimal("0.5")


def test_an_undelegation_worth_less_than_a_unit_is_refused(chain):
    _ok(chain.call("alice", "delegate", validator=NODE1, amount=3))
    _slash_alone(chain, NODE1, 3333)  # 2.0001 tokens for 3 shares

    refused = chain.call(
        "alice", "undelegate", validator=NODE1, amount=_amount("1e-30")
    )

    assert refused["status"] == 1 and "too small" in refused["result"]
    assert chain.get(f"validators.delegation_shares:alice:{NODE1}") == 3


def test_a_fully_slashed_pool_earns_nothing_and_its_holders_can_leave(chain):
    _ok(chain.call("alice", "delegate", validator=NODE1, amount=100))
    _ok(
        chain.call(
            NODE1,
            "propose_vote",
            type_of_vote="slash_member",
            arg={"member": NODE1, "slash_bps": 10000},
        )
    )
    rate = chain.get(f"validators.reward_per_share:{NODE1}")
    _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    assert chain.get(f"validators.reward_per_share:{NODE1}") == rate

    refused = chain.call("bob", "delegate", validator=NODE1, amount=100)
    assert refused["status"] == 1 and "fully slashed" in refused["result"]

    _ok(chain.call("alice", "undelegate", validator=NODE1, amount=0))
    assert chain.get(f"validators.total_shares:{NODE1}") == 0
    _ok(chain.call("bob", "delegate", validator=NODE1, amount=100))


def test_exit_keeps_delegations_and_stops_their_rewards(tmp_path):
    chain = Chain(tmp_path, [NODE1, NODE2])
    for account in (NODE1, NODE2, "alice", "sender"):
        chain.fund(account)
    _ok(chain.call(NODE2, "bond_self", amount=10))
    _ok(chain.call("alice", "delegate", validator=NODE2, amount=100))
    _ok(chain.call(NODE1, "propose_vote", type_of_vote="remove_member", arg=NODE2))
    _ok(chain.call(NODE2, "vote", proposal_id=1, vote="yes"))
    assert chain.view("get_validator", account=NODE2)["status"] == "removed"
    assert (
        chain.view("get_delegation", delegator="alice", validator=NODE2)["amount"]
        == 100
    )
    rate = chain.get(f"validators.reward_per_share:{NODE2}")

    _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    assert chain.get(f"validators.reward_per_share:{NODE2}") == rate

    # The exit moved the self bond into unbonding; a later undelegation
    # unlocks with it, as the old exit sweep did.
    _ok(chain.call("alice", "undelegate", validator=NODE2, amount=100))
    self_bond_unbond, delegation_unbond = (
        chain.get(f"validators.pending_unbonds:{unbond_id}") for unbond_id in (1, 2)
    )
    assert self_bond_unbond["owner"] == NODE2 and delegation_unbond["owner"] == "alice"
    assert delegation_unbond["created_block"] > self_bond_unbond["created_block"]
    assert delegation_unbond["unlock_at"] == self_bond_unbond["unlock_at"]


@pytest.mark.parametrize(
    "cap,configured,effective",
    [(-5, 9000, 0), (20000, 15000, 10000), (20000, 9000, 9000)],
)
def test_a_patched_policy_maximum_is_clamped_to_the_bps_range(
    tmp_path, cap, configured, effective
):
    chain = Chain(tmp_path, [NODE1], commissions={NODE1: configured})
    for account in ("alice", "sender"):
        chain.fund(account)
    driver = chain.client.raw_driver
    driver.set("validators.config:max_commission_bps", cap)  # a state patch
    driver.commit()
    _ok(chain.call("alice", "delegate", validator=NODE1, amount=100))

    result = _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))

    assert chain.view("get_validator", account=NODE1)["commission_bps"] == effective
    paid = {
        record["type"]: Decimal(str(record["value"]))
        for record in result["reward_records"]
    }
    total = sum(paid.values())
    # No self bond: the operator earns exactly its commission.
    assert paid.get("validator_reward", 0) == total * effective / 10000


def test_undelegating_from_a_jailed_validator_unbonds_on_the_usual_clock(tmp_path):
    chain = Chain(tmp_path, [NODE1, NODE2])
    for account in (NODE1, NODE2, "alice", "sender"):
        chain.fund(account)
    _ok(chain.call("alice", "delegate", validator=NODE2, amount=100))
    _ok(
        chain.call(
            NODE1, "propose_vote", type_of_vote="jail_member", arg={"member": NODE2}
        )
    )
    _ok(chain.call(NODE2, "vote", proposal_id=1, vote="yes"))
    assert chain.view("get_validator", account=NODE2)["jailed"] is True

    _ok(chain.call("alice", "undelegate", validator=NODE2, amount=100))

    # A jailed validator has a left_at too; only an exit moves the clock.
    unbond = chain.get("validators.pending_unbonds:1")
    assert unbond["unlock_at"] is None
    anchor_time = unbond["created_at"] + Timedelta(seconds=1)
    chain.client.get_contract_proxy("validator_penalties").process_time_anchors(
        signer="__stake_time_driver__",
        environment={"block_num": unbond["created_block"] + 1, "now": anchor_time},
    )
    assert chain.get("validators.pending_unbonds:1")[
        "unlock_at"
    ] == anchor_time + Timedelta(days=7)


def test_commission_is_capped_by_the_policy_maximum(tmp_path):
    chain = Chain(tmp_path, [NODE1], commissions={NODE1: 9000}, max_commission_bps=1000)
    for account in ("alice", "sender"):
        chain.fund(account)
    _ok(chain.call("alice", "delegate", validator=NODE1, amount=100))
    result = _ok(chain.send("sender", "currency", "transfer", amount=1, to="bob"))
    operator, pool = (
        Decimal(str(record["value"])) for record in result["reward_records"]
    )
    # No self bond: the operator gets the 10% commission, the pool the rest.
    assert pool == operator * 9
    assert chain.view("get_validator", account=NODE1)["commission_bps"] == 1000


# --- property tests ----------------------------------------------------------

DELEGATORS = ["alice", "bob", "carol", "dave"]
AMOUNTS = ["1e-30", "0.000001", "1", "3.3", "100", "12345.678901234567890123456789"]


def _reward_key(delegator):
    return f"rk_{delegator}"


def _model_for(chain, powers, commissions):
    return Model(
        pools={
            node: Pool(
                operator_key=_operator(node),
                power=powers[node],
                commission_bps=commissions[node],
            )
            for node in chain.nodes
        },
        rate=RATE,
    )


def _random_op(rng, chain, model):
    kind = rng.choice(
        ["delegate", "delegate", "undelegate", "claim", "fee", "fee", "slash", "bond"]
    )
    node = rng.choice(chain.nodes)
    delegator = rng.choice(DELEGATORS)
    if kind == "delegate":
        return kind, node, delegator, Decimal(rng.choice(AMOUNTS))
    if kind == "undelegate":
        value = model.value(delegator, node)
        amount = (
            value if rng.random() < 0.4 else min(value, Decimal(rng.choice(AMOUNTS)))
        )
        return kind, node, delegator, amount
    if kind == "slash":
        return kind, node, None, rng.choice([1, 500, 3333, 10000])
    if kind == "bond":
        return kind, node, None, Decimal(rng.choice(AMOUNTS))
    return kind, node, delegator, None


def _fee_chi(result):
    """The chi whose fee a paid transaction paid out: the chi it used.

    The receipt's ``chi_used`` is the chi charged, which includes the
    burned unused-chi charge; rewards are paid on the chi used. The test
    chain splits fees 1/0/0/0, so the validator and delegator-pool records
    pay that chi out whole."""
    records = result["reward_records"]
    assert {record["type"] for record in records} <= {
        "validator_reward",
        "delegator_pool_reward",
    }
    paid = sum(Decimal(str(record["value"])) for record in records)
    return int((paid * RATE).to_integral_value())


def _apply(chain, model, op):
    """Runs `op` on the chain and on the model; returns whether the chain accepted it."""
    kind, node, delegator, amount = op
    if kind == "delegate":
        result = chain.call(
            delegator,
            "delegate",
            validator=node,
            amount=_amount(amount),
            reward_key=_reward_key(delegator),
        )
        action = lambda: model.delegate(delegator, node, amount, _reward_key(delegator))
    elif kind == "undelegate":
        result = chain.call(
            delegator, "undelegate", validator=node, amount=_amount(amount)
        )
        action = lambda: model.undelegate(delegator, node, amount)
    elif kind == "claim":
        result = chain.call(delegator, "claim_rewards", validator=node)
        action = lambda: model.claim(delegator, node)
    elif kind == "slash":
        return _slash(chain, model, node, amount)
    elif kind == "bond":
        result = chain.call(node, "bond_self", amount=_amount(amount))
        action = lambda: model.bond_self(node, amount)
    else:
        result = chain.send("sender", "currency", "transfer", amount=1, to="bob")
        action = lambda: None
    accepted = result["status"] == 0
    if accepted:
        action()
    else:
        with pytest.raises(AssertionError):
            action()
    model.credit_fee(_fee_chi(result))
    return result


def _slash(chain, model, node, slash_bps):
    """A slash vote: every member's vote is a paid transaction; the slash
    applies in the one that finalizes the proposal."""
    result = chain.call(
        chain.nodes[0],
        "propose_vote",
        type_of_vote="slash_member",
        arg={"member": node, "slash_bps": slash_bps},
    )
    voters = iter(chain.nodes[1:])
    while True:
        if result["status"] != 0:
            with pytest.raises(AssertionError):
                model.slash(node, slash_bps)
            model.credit_fee(_fee_chi(result))
            return result
        if not _proposal_open(chain):
            model.slash(node, slash_bps)
            model.credit_fee(_fee_chi(result))
            return result
        model.credit_fee(_fee_chi(result))
        result = chain.call(
            next(voters),
            "vote",
            proposal_id=chain.get("validators.total_votes"),
            vote="yes",
        )


def _proposal_open(chain):
    vote = chain.get(f"validators.votes:{chain.get('validators.total_votes')}", None)
    return vote is not None and not vote["finalized"]


def _contract_holdings(chain):
    """What `validators` must hold: bonds, pools, unclaimed unbonds, rewards."""
    total = Decimal(0)
    for node in chain.nodes:
        for variable in ("holdings", "self_bond", "total_delegated", "reward_pool"):
            total += Decimal(str(chain.get(f"validators.{variable}:{node}")))
    for unbond_id in range(1, chain.get("validators.pending_unbond_counter") + 1):
        unbond = chain.get(f"validators.pending_unbonds:{unbond_id}", None)
        if unbond and not unbond["claimed"]:
            total += Decimal(str(unbond["amount"]))
    return total


def _assert_invariants(chain, model, step):
    assert chain.balance("validators") == _contract_holdings(chain), step
    for node in chain.nodes:
        pool = model.pools[node]
        for variable, expected in (
            ("total_delegated", pool.delegated),
            ("total_shares", pool.shares),
            ("self_bond", pool.self_bond),
            ("reward_per_share", pool.reward_per_share),
            ("reward_pool", pool.reward_pool),
        ):
            assert (
                Decimal(str(chain.get(f"validators.{variable}:{node}"))) == expected
            ), (step, node, variable)
        owed = Decimal(0)
        for delegator in DELEGATORS:
            pending = chain.view(
                "get_pending_rewards", delegator=delegator, validator=node
            )
            assert Decimal(str(pending)) == model.pending(delegator, node), (
                step,
                delegator,
            )
            value = chain.view("get_delegation", delegator=delegator, validator=node)[
                "amount"
            ]
            assert Decimal(str(value)) == model.value(delegator, node) >= 0, (
                step,
                delegator,
            )
            owed += pending
        assert pool.reward_pool >= owed >= 0, step
        assert pool.delegated >= 0 and pool.shares >= 0 and pool.self_bond >= 0, step
    for account, paid in model.paid.items():
        assert chain.balance(account) == paid, (step, account)


@pytest.mark.parametrize("seed", range(6))
def test_random_sequences_match_the_reference_model_and_conserve_value(tmp_path, seed):
    rng = random.Random(20261115 + seed)
    nodes = [NODE1, NODE2, NODE3][: 1 + seed % 3]
    powers = {node: rng.choice([1, 10, 33]) for node in nodes}
    commissions = {node: rng.choice([0, 500, 2000]) for node in nodes}
    chain = Chain(tmp_path, nodes, powers=powers, commissions=commissions)
    for account in nodes + DELEGATORS + ["sender"]:
        chain.fund(account)
    model = _model_for(chain, powers, commissions)
    accepted = Counter()
    with localcontext() as context:
        context.prec = 200
        for step in range(60):
            op = _random_op(rng, chain, model)
            accepted[op[0]] += _apply(chain, model, op)["status"] == 0
            _assert_invariants(chain, model, (step, op))
    # The sequence did real work: rewards were paid out and stake moved.
    assert accepted["delegate"] and accepted["claim"] and accepted["fee"], accepted
    assert sum(model.paid.get(_reward_key(name), 0) for name in DELEGATORS) > 0
