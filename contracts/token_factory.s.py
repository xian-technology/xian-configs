import submission

TokenCreatedEvent = LogEvent(
    "TokenCreated",
    {
        "contract": indexed(str),
        "creator": indexed(str),
        "operator": indexed(str),
        "initial_holder": str,
        "token_symbol": str,
        "initial_supply": (int, float, decimal),
    },
)

# GENERATED TOKEN FACTORY ARTIFACTS START
# Source of truth: contracts/templates/token_factory_xsc001_token_template.s.py. Regenerate via `uv run --project ../xian-cli python ./scripts/generate_token_factory_artifacts.py --write`.
XSC001_TOKEN_SOURCE = (
    'balances = Hash(default_value=0)\napprovals = Hash(default_value=0)\nmetadata = Hash()\nope'
    "rator = Variable()\nTransferEvent = LogEvent('Transfer', {'from': indexed(str), 'to': ind"
    "exed(str), 'amount': (int, float, decimal)})\nApproveEvent = LogEvent('Approve', {'from':"
    " indexed(str), 'to': indexed(str), 'amount': (int, float, decimal)})\n\n@construct\ndef see"
    'd(token_name: str, token_symbol: str, token_logo_url: str, token_logo_svg: str, token_we'
    'bsite: str, initial_supply: Any, initial_holder: str, operator_address: str):\n    assert'
    " isinstance(token_name, str) and token_name != '', 'token_name must be non-empty.'\n    a"
    "ssert isinstance(token_symbol, str) and token_symbol != '', 'token_symbol must be non-em"
    "pty.'\n    assert isinstance(token_logo_url, str), 'token_logo_url must be a string.'\n   "
    " assert isinstance(token_logo_svg, str), 'token_logo_svg must be a string.'\n    assert i"
    "sinstance(token_website, str), 'token_website must be a string.'\n    assert isinstance(i"
    "nitial_supply, (int, float, decimal)), 'initial_supply must be numeric.'\n    assert init"
    "ial_supply >= 0, 'initial_supply must be non-negative.'\n    assert isinstance(initial_ho"
    "lder, str) and initial_holder != '', 'initial_holder must be non-empty.'\n    assert isin"
    "stance(operator_address, str) and operator_address != '', 'operator_address must be non-"
    "empty.'\n    balances[initial_holder] = initial_supply\n    metadata['token_name'] = token"
    "_name\n    metadata['token_symbol'] = token_symbol\n    metadata['token_logo_url'] = token"
    "_logo_url\n    metadata['token_logo_svg'] = token_logo_svg\n    metadata['token_website'] "
    "= token_website\n    metadata['total_supply'] = initial_supply\n    operator.set(operator_"
    'address)\n\n@export\ndef change_metadata(key: str, value: Any):\n    assert ctx.caller == op'
    "erator.get(), 'Only operator can set metadata!'\n    metadata[key] = value\n\n@export\ndef c"
    "hange_operator(new_operator: str):\n    assert ctx.caller == operator.get(), 'Only operat"
    "or can change operator!'\n    assert isinstance(new_operator, str) and new_operator != ''"
    ", 'new_operator must be non-empty.'\n    operator.set(new_operator)\n\n@export\ndef operator"
    '_of():\n    return operator.get()\n\n@export\ndef balance_of(address: str):\n    return balan'
    "ces[address]\n\n@export\ndef transfer(amount: float, to: str):\n    assert amount > 0, 'Cann"
    "ot send negative balances!'\n    assert balances[ctx.caller] >= amount, 'Not enough coins"
    " to send!'\n    balances[ctx.caller] -= amount\n    balances[to] += amount\n    TransferEve"
    "nt({'from': ctx.caller, 'to': to, 'amount': amount})\n\n@export\ndef approve(amount: float,"
    " to: str):\n    assert amount >= 0, 'Cannot approve negative balances!'\n    approvals[ctx"
    ".caller, to] = amount\n    ApproveEvent({'from': ctx.caller, 'to': to, 'amount': amount})"
    '\n\n@export\ndef transfer_from(amount: float, to: str, main_account: str):\n    assert amoun'
    "t > 0, 'Cannot send negative balances!'\n    assert approvals[main_account, ctx.caller] >"
    "= amount, f'Not enough coins approved to send! You have {approvals[main_account, ctx.cal"
    "ler]} and are trying to spend {amount}'\n    assert balances[main_account] >= amount, 'No"
    "t enough coins to send!'\n    approvals[main_account, ctx.caller] -= amount\n    balances["
    "main_account] -= amount\n    balances[to] += amount\n    TransferEvent({'from': main_accou"
    "nt, 'to': to, 'amount': amount})"
)
# GENERATED TOKEN FACTORY ARTIFACTS END

def resolve_controller(address: Any, field_name: str):
    if address is None or address == "":
        return ctx.signer

    assert isinstance(address, str), field_name + " must be a string."
    assert address != "", field_name + " must be non-empty."
    return address


def build_token_source():
    return XSC001_TOKEN_SOURCE


@export
def create_token(
    token_contract: str,
    token_name: str,
    token_symbol: str,
    initial_supply: Any,
    token_logo_url: str = "",
    token_logo_svg: str = "",
    token_website: str = "",
    initial_holder: str = None,
    operator_address: str = None,
):
    assert isinstance(token_contract, str) and token_contract != "", "token_contract must be non-empty."
    assert isinstance(token_name, str) and token_name != "", "token_name must be non-empty."
    assert isinstance(token_symbol, str) and token_symbol != "", "token_symbol must be non-empty."
    assert isinstance(initial_supply, (int, float, decimal)), "initial_supply must be numeric."
    assert initial_supply >= 0, "initial_supply must be non-negative."

    if token_logo_url is None:
        token_logo_url = ""
    if token_logo_svg is None:
        token_logo_svg = ""
    if token_website is None:
        token_website = ""

    assert isinstance(token_logo_url, str), "token_logo_url must be a string."
    assert isinstance(token_logo_svg, str), "token_logo_svg must be a string."
    assert isinstance(token_website, str), "token_website must be a string."

    resolved_initial_holder = resolve_controller(
        initial_holder, "initial_holder"
    )
    resolved_operator = resolve_controller(
        operator_address, "operator_address"
    )

    submission.submit_contract(
        name=token_contract,
        code=build_token_source(),
        owner=None,
        constructor_args={
            "token_name": token_name,
            "token_symbol": token_symbol,
            "token_logo_url": token_logo_url,
            "token_logo_svg": token_logo_svg,
            "token_website": token_website,
            "initial_supply": initial_supply,
            "initial_holder": resolved_initial_holder,
            "operator_address": resolved_operator,
        },
    )

    TokenCreatedEvent(
        {
            "contract": token_contract,
            "creator": ctx.signer,
            "initial_holder": resolved_initial_holder,
            "operator": resolved_operator,
            "token_symbol": token_symbol,
            "initial_supply": initial_supply,
        }
    )

    return {
        "contract": token_contract,
        "creator": ctx.signer,
        "initial_holder": resolved_initial_holder,
        "operator": resolved_operator,
    }
