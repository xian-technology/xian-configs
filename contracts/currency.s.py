balances = Hash(default_value=0)
approvals = Hash(default_value=0)
metadata = Hash()

GOVERNANCE_CONTRACT = "governance"

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


def canonical_genesis_amount(value: Any):
    assert not isinstance(value, bool), "Genesis balance must not be boolean."
    amount = decimal(str(value))
    assert amount >= 0, "Genesis balance cannot be negative."
    return amount


def require_genesis_account(account: str):
    assert isinstance(account, str) and account != "", "Genesis account must be non-empty."
    return account


def seed_default_balances(vk: str):
    balances[vk] = 5555555.55  # 5% Team Tokens
    balances["team_lock"] = 16666666.65  # 15% Team allocation
    balances["dao"] = 33333333.3  # Full DAO allocation
    balances["team_lock"] += 49999999.95  # 45% Second batch of public tokens
    balances[vk] += 5555555.55  # 5% Seed participation tokens

    return balances[vk] + balances["team_lock"] + balances["dao"]


def seed_configured_balances(initial_balances: dict):
    assert initial_balances is not None, "initial_balances is required."
    assert len(initial_balances) > 0, "initial_balances must not be empty."

    total_supply = decimal("0")
    for account in initial_balances:
        account = require_genesis_account(account)
        amount = canonical_genesis_amount(initial_balances[account])
        balances[account] = amount
        total_supply += amount

    assert total_supply > 0, "Genesis total supply must be positive."
    return total_supply


def seed_token_metadata(token_metadata: dict = None):
    metadata["token_name"] = "XIAN"
    metadata["token_symbol"] = "XIAN"
    metadata["token_logo_url"] = "https://xian.org/assets/img/logo.svg"
    metadata["token_logo_svg"] = ""
    metadata["token_website"] = "https://xian.org"
    metadata["operator"] = "team_lock"
    metadata["permit_authorizer"] = "permit_authorizer"

    if token_metadata is None:
        return

    for key in token_metadata:
        assert key != "total_supply", "total_supply is managed by the contract."
        assert key != "operator", "operator is managed by governance."
        assert (
            key != "permit_authorizer"
        ), "permit_authorizer is managed by governance."
        metadata[key] = token_metadata[key]


@construct
def seed(
    vk: str,
    initial_balances: dict = None,
    token_metadata: dict = None,
):
    if initial_balances is None:
        total_supply = seed_default_balances(vk)
    else:
        total_supply = seed_configured_balances(initial_balances)

    seed_token_metadata(token_metadata)
    metadata["total_supply"] = total_supply


@export
def change_metadata(key: str, value: Any):
    assert ctx.caller == metadata["operator"], "Only operator can set metadata."
    assert key != "total_supply", "total_supply is managed by the contract."
    assert key != "operator", "operator is managed by governance."
    assert (
        key != "permit_authorizer"
    ), "permit_authorizer is managed by governance."
    metadata[key] = value


def require_governance():
    assert (
        ctx.caller == GOVERNANCE_CONTRACT
    ), "Only governance can change sensitive currency settings."


def require_name(name: str, label: str):
    assert isinstance(name, str) and name != "", label + " must be non-empty."
    return name


def require_contract_name(name: str, label: str):
    name = require_name(name, label)
    assert importlib.exists(name), label + " contract does not exist."
    return name


@export
def set_operator(new_operator: str):
    require_governance()
    metadata["operator"] = require_name(new_operator, "new_operator")
    return metadata["operator"]


@export
def set_permit_authorizer(new_authorizer: str):
    require_governance()
    metadata["permit_authorizer"] = require_contract_name(
        new_authorizer, "new_authorizer"
    )
    return metadata["permit_authorizer"]


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
