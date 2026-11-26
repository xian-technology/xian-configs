import currency

owner = Variable()
pending_owner = Variable()

@construct
def seed(vk: str):
    owner.set(currency.validate_account(vk))

@export
def withdraw(amount: decimal):
    assert amount > 0, 'Cannot send negative balances!'
    assert ctx.caller == owner.get(), 'Not owner!'
    currency.transfer(amount, ctx.caller)

@export
def change_owner(vk: str):
    assert ctx.caller == owner.get(), 'Not owner!'
    vk = currency.validate_account(vk)
    assert vk != owner.get(), 'New owner must differ from the current owner.'
    pending_owner.set(vk)
    return vk

@export
def get_pending_owner():
    return pending_owner.get()

@export
def cancel_ownership_transfer():
    assert ctx.caller == owner.get(), 'Not owner!'
    pending_owner.set(None)

@export
def accept_ownership():
    nominee = pending_owner.get()
    assert nominee is not None, 'No pending ownership transfer.'
    assert ctx.caller == nominee, 'Only the pending owner can accept.'
    owner.set(nominee)
    pending_owner.set(None)
    return nominee
