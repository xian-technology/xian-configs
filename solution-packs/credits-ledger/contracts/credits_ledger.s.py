balances = Hash(default_value=0)
metadata = Hash()
issuers = Hash(default_value=False)

TransferEvent = LogEvent(
    event="Transfer",
    params={
        "from": {"type": str, "idx": True},
        "to": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
    },
)

IssueEvent = LogEvent(
    event="Issue",
    params={
        "to": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
        "issuer": {"type": str, "idx": True},
    },
)

BurnEvent = LogEvent(
    event="Burn",
    params={
        "from": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
        "actor": {"type": str, "idx": True},
    },
)

IssuerAddedEvent = LogEvent(
    event="IssuerAdded",
    params={
        "account": {"type": str, "idx": True},
        "actor": {"type": str, "idx": True},
    },
)

IssuerRemovedEvent = LogEvent(
    event="IssuerRemoved",
    params={
        "account": {"type": str, "idx": True},
        "actor": {"type": str, "idx": True},
    },
)


@construct
def seed(
    name: str = "Credits Ledger",
    symbol: str = "CRED",
    operator: str = None,
):
    operator = operator or ctx.caller
    metadata["name"] = name
    metadata["symbol"] = symbol
    metadata["operator"] = operator
    metadata["total_supply"] = 0
    issuers[operator] = True


def _require_operator():
    assert ctx.caller == metadata["operator"], "Only operator can manage issuers."


def _require_issuer():
    assert issuers[ctx.caller], "Only issuer can mint or burn on behalf of others."


@export
def set_operator(account: str):
    _require_operator()
    metadata["operator"] = account
    issuers[account] = True


@export
def add_issuer(account: str):
    _require_operator()
    issuers[account] = True
    IssuerAddedEvent({"account": account, "actor": ctx.caller})


@export
def remove_issuer(account: str):
    _require_operator()
    assert account != metadata["operator"], "Operator must remain an issuer."
    issuers[account] = False
    IssuerRemovedEvent({"account": account, "actor": ctx.caller})


@export
def issue(to: str, amount: float):
    _require_issuer()
    assert amount > 0, "Amount must be positive."
    balances[to] += amount
    metadata["total_supply"] += amount
    IssueEvent({"to": to, "amount": amount, "issuer": ctx.caller})


@export
def transfer(amount: float, to: str):
    assert amount > 0, "Amount must be positive."
    assert balances[ctx.caller] >= amount, "Insufficient balance."
    balances[ctx.caller] -= amount
    balances[to] += amount
    TransferEvent({"from": ctx.caller, "to": to, "amount": amount})


@export
def burn(amount: float):
    assert amount > 0, "Amount must be positive."
    assert balances[ctx.caller] >= amount, "Insufficient balance."
    balances[ctx.caller] -= amount
    metadata["total_supply"] -= amount
    BurnEvent({"from": ctx.caller, "amount": amount, "actor": ctx.caller})


@export
def burn_from(account: str, amount: float):
    _require_issuer()
    assert amount > 0, "Amount must be positive."
    assert balances[account] >= amount, "Insufficient balance."
    balances[account] -= amount
    metadata["total_supply"] -= amount
    BurnEvent({"from": account, "amount": amount, "actor": ctx.caller})


@export
def balance_of(account: str):
    return balances[account]


@export
def total_supply():
    return metadata["total_supply"]


@export
def is_issuer(account: str):
    return issuers[account]
