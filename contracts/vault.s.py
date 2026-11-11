import currency

owners = Hash()
required_signatures = Variable()
owner_count = Variable()
transaction_count = Variable()
transactions = Hash()

def normalize_owner(owner: str):
    assert isinstance(owner, str), 'An owner must be a string.'
    owner = owner.strip()
    assert owner != '', 'An owner must be non-empty.'
    return owner


@construct
def seed(initial_owners: str, initial_required_signatures: int):
    """
    Initializes the multisig contract.
    - initial_owners: Comma-separated string of owner addresses.
    - initial_required_signatures: Number of required signatures to execute a transaction.
    """
    owner_list = []
    for owner in initial_owners.split(','):
        owner = normalize_owner(owner)
        assert owner not in owner_list, 'Duplicate owner.'
        owner_list.append(owner)

    assert initial_required_signatures > 0, 'Requirement must be greater than zero.'
    assert initial_required_signatures <= len(owner_list), 'Requirement cannot be greater than number of owners.'
    for owner in owner_list:
        owners[owner] = True

    required_signatures.set(initial_required_signatures)
    owner_count.set(len(owner_list))
    transaction_count.set(0)

@export
def submit_transaction(to: str = None, amount: decimal = None, tx_type: str = 'transfer'):
    """
    Submits a new transaction to the multisig wallet.
    - to: Recipient address.
    - amount: Amount of tokens to transfer.
    - tx_type: Type of transaction ('transfer', 'addOwner', 'removeOwner', 'changeRequirement').
    """
    assert owners[ctx.caller], 'Only owners can submit transactions.'

    tx_id = transaction_count.get() + 1
    transaction_count.set(tx_id)

    transactions[tx_id, 'type'] = tx_type
    transactions[tx_id, 'to'] = to
    transactions[tx_id, 'amount'] = amount
    transactions[tx_id, 'executed'] = False
    transactions[tx_id, 'approvals'] = 0
    transactions[tx_id, 'approver_list'] = []

    # The submitter approves the transaction by default
    approve_transaction(tx_id)

    return f"Transaction {tx_id} submitted."

@export
def approve_transaction(tx_id: int):
    """
    Approves a pending transaction.
    - tx_id: The ID of the transaction to approve.
    """
    assert owners[ctx.caller], 'Only owners can approve transactions.'
    assert not transactions[tx_id, 'executed'], 'Transaction already executed.'
    assert transactions[tx_id, 'type'] is not None, 'Transaction does not exist.'
    assert not transactions[tx_id, 'approvers', ctx.caller], 'Already approved.'

    transactions[tx_id, 'approvers', ctx.caller] = True
    approvers = transactions[tx_id, 'approver_list']
    approvers.append(ctx.caller)
    transactions[tx_id, 'approver_list'] = approvers
    transactions[tx_id, 'approvals'] += 1

    return f"Transaction {tx_id} approved by {ctx.caller}."

@export
def execute_transaction(tx_id: int):
    """
    Executes a transaction if enough approvals are collected.
    - tx_id: The ID of the transaction to execute.
    """
    assert owners[ctx.caller], 'Only owners can execute transactions.'
    assert not transactions[tx_id, 'executed'], 'Transaction already executed.'
    assert transactions[tx_id, 'type'] is not None, 'Transaction does not exist.'
    approvals = 0
    for approver in transactions[tx_id, 'approver_list']:
        if owners[approver]:
            approvals += 1
    required = required_signatures.get()
    assert approvals >= required, 'Not enough approvals.'

    tx_type = transactions[tx_id, 'type']
    to = transactions[tx_id, 'to']
    amount = transactions[tx_id, 'amount']
    
    if tx_type == 'transfer':
        currency.transfer(amount=amount, to=to)
    elif tx_type == 'addOwner':
        to = normalize_owner(to)
        assert not owners[to], 'Address is already an owner.'
        owners[to] = True
        owner_count.set(owner_count.get() + 1)
    elif tx_type == 'removeOwner':
        to = normalize_owner(to)
        assert owners[to], 'Address is not an owner.'
        assert owner_count.get() > 1, 'Cannot remove the last owner.'
        owners[to] = False
        owner_count.set(owner_count.get() - 1)
        required_signatures.set(min(required_signatures.get(), owner_count.get()))
    elif tx_type == 'changeRequirement':
        assert amount is not None, 'No new requirement specified.'
        new_requirement = int(amount)
        assert new_requirement > 0, 'Requirement must be greater than zero.'
        total_owners = owner_count.get()
        assert new_requirement <= total_owners, 'Requirement cannot be greater than number of owners.'
        required_signatures.set(new_requirement)
    else:
        return 'Invalid transaction type.'

    transactions[tx_id, 'executed'] = True

    return f"Transaction {tx_id} executed."

@export
def change_currency_metadata(key: str, value: str):
    """
    Changes the metadata of the currency contract
    """
    assert owners[ctx.caller], 'Only owners can change metadata.'
    currency.change_metadata(key, value)
