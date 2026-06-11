S = Hash()
CONTROL_CONTRACT = "validators"


def require_control_contract():
    assert ctx.caller == CONTROL_CONTRACT, "Only validators can change chi cost."

@construct
def seed(initial_rate: int=100):
    S['value'] = initial_rate

@export
def current_value():
    return S['value']

@export
def set_value(new_value: int):
    require_control_contract()
    assert new_value > 0, 'New value must be greater than 0'
    S['value'] = new_value
