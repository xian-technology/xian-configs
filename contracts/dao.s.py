CONTROL_CONTRACT = "masternodes"


def require_control_contract():
    assert ctx.caller == CONTROL_CONTRACT, "Only masternodes can transfer DAO funds."


@export
def transfer_from_dao(args: dict):
    require_control_contract()
    contract_name = args.get('contract_name')
    amount = args.get('amount')
    to = args.get('to')
    
    assert contract_name is not None, 'Contract name is required'
    assert amount > 0, 'Amount must be greater than 0'
    assert to is not None, 'To is required'
    
    contract = importlib.import_module(contract_name)
    contract.transfer(amount=amount, to=to)
