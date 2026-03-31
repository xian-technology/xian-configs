balances = Hash(default_value=0)
metadata = Hash()
permits = Hash()

TransferEvent = LogEvent(
    event="Transfer",
    params={
        "from": {"type": str, "idx": True},
        "to": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
    },
)
ApproveEvent = LogEvent(
    event="Approve",
    params={
        "from": {"type": str, "idx": True},
        "to": {"type": str, "idx": True},
        "amount": {"type": (int, float, decimal)},
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
    metadata["token_website"] = "https://xian.org"
    metadata["operator"] = "team_lock"


@export
def change_metadata(key: str, value: Any):
    assert ctx.caller == metadata["operator"], "Only operator can set metadata."
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
    balances[ctx.caller, to] = amount

    ApproveEvent({"from": ctx.caller, "to": to, "amount": amount})


@export
def transfer_from(amount: float, to: str, main_account: str):
    assert amount > 0, "Cannot send negative balances."
    assert (
        balances[main_account, ctx.caller] >= amount
    ), f"Not enough coins approved to send. You have {balances[main_account, ctx.caller]} approved and are trying to spend {amount}"
    assert balances[main_account] >= amount, "Not enough coins to send."

    balances[main_account, ctx.caller] -= amount
    balances[main_account] -= amount
    balances[to] += amount

    TransferEvent({"from": main_account, "to": to, "amount": amount})


@export
def balance_of(address: str):
    return balances[address]


@export
def permit(owner: str, spender: str, value: float, deadline: str, signature: str):
    deadline = strptime_ymdhms(deadline)
    permit_msg = construct_permit_msg(owner, spender, value, str(deadline))
    permit_hash = hashlib.sha3(permit_msg)

    assert permits[permit_hash] is None, "Permit can only be used once."
    assert now < deadline, "Permit has expired."
    assert value >= 0, "Cannot approve negative balances!"
    assert crypto.verify(owner, permit_msg, signature), "Invalid signature."

    balances[owner, spender] = value
    permits[permit_hash] = True

    ApproveEvent({"from": owner, "to": spender, "amount": value})

    return permit_hash


def construct_permit_msg(owner: str, spender: str, value: float, deadline: str):
    return f"{owner}:{spender}:{value}:{deadline}:{ctx.this}:{chain_id}"


def strptime_ymdhms(date_string: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
