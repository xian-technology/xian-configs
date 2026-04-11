balances = Hash(default_value=0)
approvals = Hash(default_value=0)
metadata = Hash()

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
def seed(vk: str):
    balances[vk] = 5555555.55  # 5% Team Tokens
    balances["team_lock"] = 16666666.65  # 15% Team allocation
    balances["dao"] = 33333333.3  # Full DAO allocation
    balances["team_lock"] += 49999999.95  # 45% Second batch of public tokens
    balances[vk] += 5555555.55  # 5% Seed participation tokens

    metadata["token_name"] = "XIAN"
    metadata["token_symbol"] = "XIAN"
    metadata["token_logo_url"] = "https://xian.org/assets/img/logo.svg"
    metadata["token_logo_svg"] = ""
    metadata["token_website"] = "https://xian.org"
    metadata["total_supply"] = (
        balances[vk] + balances["team_lock"] + balances["dao"]
    )
    metadata["operator"] = "team_lock"
    metadata["permit_authorizer"] = "permit_authorizer"


@export
def change_metadata(key: str, value: Any):
    assert ctx.caller == metadata["operator"], "Only operator can set metadata."
    assert key != "total_supply", "total_supply is managed by the contract."
    metadata[key] = value


@export
def transfer(amount: float, to: str):
    assert amount > 0, "Cannot send negative balances."
    assert balances[ctx.caller] >= amount, "Not enough coins to send."

    balances[ctx.caller] -= amount
    balances[to] += amount

    TransferEvent({"from": ctx.caller, "to": to, "amount": amount})


@export
def approve(amount: float, to: str):
    assert amount >= 0, "Cannot approve negative balances."
    approvals[ctx.caller, to] = amount

    ApproveEvent({"from": ctx.caller, "to": to, "amount": amount})


@export
def approve_from_authorizer(owner: str, spender: str, amount: float):
    authorizer = metadata["permit_authorizer"] or "permit_authorizer"

    assert (
        ctx.caller == authorizer
    ), "Only permit authorizer can approve on behalf of others."
    assert amount >= 0, "Cannot approve negative balances."

    approvals[owner, spender] = amount

    ApproveEvent({"from": owner, "to": spender, "amount": amount})


@export
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, "Cannot send negative balances."
    assert (
        approvals[main_account, ctx.caller] >= amount
    ), f"Not enough coins approved to send. You have {approvals[main_account, ctx.caller]} approved and are trying to spend {amount}"
    assert balances[main_account] >= amount, "Not enough coins to send."

    approvals[main_account, ctx.caller] -= amount
    balances[main_account] -= amount
    balances[to] += amount

    TransferEvent({"from": main_account, "to": to, "amount": amount})


@export
def balance_of(address: str):
    return balances[address]
