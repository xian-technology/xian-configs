balances = Hash(default_value=0)
approvals = Hash(default_value=0)
metadata = Hash()
operator = Variable()

TransferEvent = LogEvent(
    "Transfer",
    {
        "from": indexed(str),
        "to": indexed(str),
        "amount": (int, float, decimal),
    },
)
ApproveEvent = LogEvent(
    "Approve",
    {
        "from": indexed(str),
        "to": indexed(str),
        "amount": (int, float, decimal),
    },
)


@construct
def seed(
    token_name: str,
    token_symbol: str,
    token_logo_url: str,
    token_logo_svg: str,
    token_website: str,
    initial_supply: Any,
    initial_holder: str,
    operator_address: str,
):
    assert isinstance(token_name, str) and token_name != "", (
        "token_name must be non-empty."
    )
    assert isinstance(token_symbol, str) and token_symbol != "", (
        "token_symbol must be non-empty."
    )
    assert isinstance(token_logo_url, str), "token_logo_url must be a string."
    assert isinstance(token_logo_svg, str), "token_logo_svg must be a string."
    assert isinstance(token_website, str), "token_website must be a string."
    assert isinstance(initial_supply, (int, float, decimal)), (
        "initial_supply must be numeric."
    )
    assert initial_supply >= 0, "initial_supply must be non-negative."
    assert isinstance(initial_holder, str) and initial_holder != "", (
        "initial_holder must be non-empty."
    )
    assert isinstance(operator_address, str) and operator_address != "", (
        "operator_address must be non-empty."
    )
    balances[initial_holder] = initial_supply
    metadata["token_name"] = token_name
    metadata["token_symbol"] = token_symbol
    metadata["token_logo_url"] = token_logo_url
    metadata["token_logo_svg"] = token_logo_svg
    metadata["token_website"] = token_website
    metadata["total_supply"] = initial_supply
    operator.set(operator_address)


@export
def change_metadata(key: str, value: Any):
    assert ctx.caller == operator.get(), "Only operator can set metadata!"
    metadata[key] = value


@export
def change_operator(new_operator: str):
    assert ctx.caller == operator.get(), "Only operator can change operator!"
    assert isinstance(new_operator, str) and new_operator != "", (
        "new_operator must be non-empty."
    )
    operator.set(new_operator)


@export
def operator_of():
    return operator.get()


@export
def balance_of(address: str):
    return balances[address]


@export
def transfer(amount: float, to: str):
    assert amount > 0, "Cannot send negative balances!"
    assert balances[ctx.caller] >= amount, "Not enough coins to send!"
    balances[ctx.caller] -= amount
    balances[to] += amount
    TransferEvent({"from": ctx.caller, "to": to, "amount": amount})


@export
def approve(amount: float, to: str):
    assert amount >= 0, "Cannot approve negative balances!"
    approvals[ctx.caller, to] = amount
    ApproveEvent({"from": ctx.caller, "to": to, "amount": amount})


@export
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, "Cannot send negative balances!"
    assert approvals[main_account, ctx.caller] >= amount, (
        f"Not enough coins approved to send! "
        f"You have {approvals[main_account, ctx.caller]} and are trying to spend {amount}"
    )
    assert balances[main_account] >= amount, "Not enough coins to send!"
    approvals[main_account, ctx.caller] -= amount
    balances[main_account] -= amount
    balances[to] += amount
    TransferEvent({"from": main_account, "to": to, "amount": amount})
