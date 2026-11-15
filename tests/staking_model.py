"""A pure-Python reference model of validator delegation rewards.

It restates the rules of `docs/VALIDATOR_DELEGATION.md` (reward per share)
independently of the contract and of the fee path: plain `decimal` numbers,
every product and quotient truncated to 30 places as `ContractingDecimal`
does. The property tests run random operation sequences on the real chain
(contract + Rust fee path) and on this model, and compare them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal, localcontext

PLACES = Decimal("1e-30")
UNIT = Decimal("1e-30")
MAX_COMMISSION_BPS = 10_000


def trunc(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 200
        return value.quantize(PLACES, rounding=ROUND_DOWN)


def mul(left, right) -> Decimal:
    with localcontext() as context:
        context.prec = 200
        return trunc(Decimal(left) * Decimal(right))


def div(left, right) -> Decimal:
    with localcontext() as context:
        context.prec = 200
        return trunc(Decimal(left) / Decimal(right))


def proportional(amount, weight, base) -> Decimal:
    """`amount * weight / base` with one truncation (the fee path's rule)."""
    with localcontext() as context:
        context.prec = 200
        return trunc(Decimal(amount) * Decimal(weight) / Decimal(base))


@dataclass
class Pool:
    operator_key: str
    power: int
    commission_bps: int
    self_bond: Decimal = Decimal(0)
    delegated: Decimal = Decimal(0)
    shares: Decimal = Decimal(0)
    reward_per_share: Decimal = Decimal(0)
    reward_pool: Decimal = Decimal(0)


@dataclass
class Model:
    pools: dict[str, Pool]
    rate: int
    max_commission_bps: int = MAX_COMMISSION_BPS
    shares: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    debt: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    reward_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    paid: dict[str, Decimal] = field(default_factory=dict)
    unbonds: list[Decimal] = field(default_factory=list)
    slashed: Decimal = Decimal(0)

    # --- the fee path -------------------------------------------------

    def credit_fee(self, chi: int) -> None:
        """A paid transaction's validator total (the whole fee) split by power."""
        total = Decimal(chi)
        names = list(self.pools)
        weights = [Decimal(self.pools[name].power) for name in names]
        base = sum(weights)
        allocated = Decimal(0)
        for index, name in enumerate(names):
            if index + 1 == len(names):
                share = total - allocated
            else:
                share = proportional(total, weights[index], base)
                allocated += share
            self._credit_validator(name, share)

    def _credit_validator(self, name: str, allotment: Decimal) -> None:
        pool = self.pools[name]
        bps = min(max(pool.commission_bps, 0), self.max_commission_bps)
        pool_chi = Decimal(0)
        if pool.delegated > 0 and pool.shares > 0:
            commission = proportional(allotment, bps, MAX_COMMISSION_BPS)
            pool_chi = proportional(allotment - commission, pool.delegated, pool.self_bond + pool.delegated)
        operator = div(allotment - pool_chi, self.rate)
        tokens = div(pool_chi, self.rate)
        per_share = div(tokens, pool.shares) if tokens > 0 else Decimal(0)
        if per_share == 0:
            operator += tokens
            tokens = Decimal(0)
        self._pay(pool.operator_key, operator)
        pool.reward_per_share += per_share
        pool.reward_pool += tokens

    # --- the contract ---------------------------------------------------

    def value(self, delegator: str, validator: str) -> Decimal:
        pool = self.pools[validator]
        shares = self.shares.get((delegator, validator), Decimal(0))
        if shares <= 0 or pool.shares <= 0:
            return Decimal(0)
        if shares == pool.shares:
            return pool.delegated
        return proportional(shares, pool.delegated, pool.shares)

    def pending(self, delegator: str, validator: str) -> Decimal:
        shares = self.shares.get((delegator, validator), Decimal(0))
        if shares <= 0:
            return Decimal(0)
        owed = mul(shares, self.pools[validator].reward_per_share) - self.debt.get(
            (delegator, validator), Decimal(0)
        )
        return max(owed, Decimal(0))

    def _settle(self, delegator: str, validator: str) -> None:
        owed = self.pending(delegator, validator)
        if owed > 0:
            pool = self.pools[validator]
            assert pool.reward_pool >= owed, "Reward pool short."
            pool.reward_pool -= owed
            self._pay(self.reward_keys[(delegator, validator)], owed)

    def _reset_debt(self, delegator: str, validator: str) -> None:
        shares = self.shares.get((delegator, validator), Decimal(0))
        rate = self.pools[validator].reward_per_share
        self.debt[(delegator, validator)] = mul(shares, rate) + UNIT if shares > 0 else Decimal(0)

    def _pay(self, account: str, amount: Decimal) -> None:
        self.paid[account] = self.paid.get(account, Decimal(0)) + amount

    def delegate(self, delegator: str, validator: str, amount: Decimal, reward_key: str) -> None:
        assert amount > 0
        pool = self.pools[validator]
        if pool.shares <= 0:
            new_shares = amount
        else:
            assert pool.delegated > 0, "Delegation pool fully slashed."
            new_shares = proportional(amount, pool.shares, pool.delegated)
            assert new_shares > 0, "Delegation too small."
        self._settle(delegator, validator)
        key = (delegator, validator)
        self.shares[key] = self.shares.get(key, Decimal(0)) + new_shares
        pool.shares += new_shares
        pool.delegated += amount
        self.reward_keys[key] = reward_key
        self._reset_debt(delegator, validator)

    def undelegate(self, delegator: str, validator: str, amount: Decimal) -> None:
        value = self.value(delegator, validator)
        held = self.shares.get((delegator, validator), Decimal(0)) > 0
        assert amount > 0 or (amount == 0 and value == 0 and held), "Delegation amount <= 0"
        assert value >= amount, "Not enough delegated stake."
        pool = self.pools[validator]
        key = (delegator, validator)
        self._settle(delegator, validator)
        if amount == value:
            burned, released = self.shares.get(key, Decimal(0)), value
        else:
            burned = proportional(amount, pool.shares, pool.delegated)
            released = proportional(burned, pool.delegated, pool.shares)
            assert burned > 0 and released > 0, "Undelegation too small."
        self.shares[key] = self.shares.get(key, Decimal(0)) - burned
        pool.shares -= burned
        pool.delegated -= released
        self._reset_debt(delegator, validator)
        if released > 0:
            self.unbonds.append(released)

    def claim(self, delegator: str, validator: str) -> None:
        self._settle(delegator, validator)
        self._reset_debt(delegator, validator)

    def bond_self(self, validator: str, amount: Decimal) -> None:
        assert amount > 0
        self.pools[validator].self_bond += amount

    def slash(self, validator: str, slash_bps: int) -> None:
        """Pro rata over the self bond and the pool (no pending unbonds are in scope)."""
        pool = self.pools[validator]
        participants = [part for part in ("self_bond", "delegated") if getattr(pool, part) > 0]
        total = pool.self_bond + pool.delegated
        assert total > 0, "No slashable stake."
        rate = div(slash_bps, 10000)
        processed = allocated = Decimal(0)
        for part in participants:
            processed += getattr(pool, part)
            target = mul(processed, rate)
            setattr(pool, part, getattr(pool, part) - (target - allocated))
            allocated = target
        self.slashed += mul(total, rate)
