S = Hash()
CONTROL_CONTRACT = "validators"


def require_control_contract():
    assert ctx.caller == CONTROL_CONTRACT, "Only validators can change rewards."


def is_number(value: Any):
    return (
        isinstance(value, (int, float, decimal))
        and isinstance(value, bool) == False
    )


def validate_split(value: list):
    assert isinstance(value, list), "Reward split must be a list."
    assert len(value) == 4, "Reward split must have 4 values."
    for item in value:
        assert is_number(item), "Reward split values must be numeric."
        assert item >= 0, "Reward split values must be non-negative."
    assert sum(value) == 1, "Reward split must sum to 1."


@construct
def seed(initial_split: list = [0.70, 0, 0, 0.30]):
    validate_split(initial_split)
    S['value'] = initial_split

@export
def current_value():
    return S['value']

@export
def set_value(new_value: list):
    require_control_contract()
    validate_split(new_value)
    S['value'] = new_value
