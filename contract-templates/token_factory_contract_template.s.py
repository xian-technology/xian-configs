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

{{ GENERATED_TOKEN_ARTIFACTS }}

def resolve_controller(address: Any, field_name: str):
    if address is None or address == "":
        return ctx.signer

    assert isinstance(address, str), field_name + " must be a string."
    assert address != "", field_name + " must be non-empty."
    return address


def materialize_token_artifact_value(value: str, token_contract: str):
    return value.replace(XSC001_TOKEN_TEMPLATE_MODULE, token_contract)


def build_token_deployment_artifacts(token_contract: str):
    vm_ir_json = materialize_token_artifact_value(
        XSC001_TOKEN_VM_IR_TEMPLATE, token_contract
    )
    return {
        "format": XSC001_TOKEN_ARTIFACT_FORMAT,
        "module_name": token_contract,
        "vm_profile": XSC001_TOKEN_VM_PROFILE,
        "source": XSC001_TOKEN_SOURCE,
        "vm_ir_json": vm_ir_json,
        "hashes": {
            "input_source_sha256": XSC001_TOKEN_INPUT_SOURCE_SHA256,
            "source_sha256": XSC001_TOKEN_SOURCE_SHA256,
            "vm_ir_sha256": hashlib.sha256_text(vm_ir_json),
        },
    }


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
        deployment_artifacts=build_token_deployment_artifacts(token_contract),
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
