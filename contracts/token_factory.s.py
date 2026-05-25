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
# Source of truth: contract-templates/token_factory_xsc001_token_template.s.py. Regenerate via `uv run --project ../xian-cli python ./scripts/generate_token_factory_artifacts.py --write`.
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

XSC001_TOKEN_VM_IR_TEMPLATE = (
    '{"docstring": null, "functions": [{"body": [{"message": {"node": "constant", "span": {"c'
    'ol": 61, "end_col": 92, "end_line": 10, "line": 10}, "value": "token_name must be non-em'
    'pty.", "value_type": "str"}, "node": "assert", "span": {"col": 4, "end_col": 92, "end_li'
    'ne": 10, "line": 10}, "test": {"node": "bool_op", "operator": "and", "span": {"col": 11,'
    ' "end_col": 59, "end_line": 10, "line": 10}, "values": [{"args": [{"host_binding_id": nu'
    'll, "id": "token_name", "node": "name", "span": {"col": 22, "end_col": 32, "end_line": 1'
    '0, "line": 10}}, {"host_binding_id": null, "id": "str", "node": "name", "span": {"col": '
    '34, "end_col": 37, "end_line": 10, "line": 10}}], "event_binding": null, "func": {"host_'
    'binding_id": null, "id": "isinstance", "node": "name", "span": {"col": 11, "end_col": 21'
    ', "end_line": 10, "line": 10}}, "keywords": [], "node": "call", "span": {"col": 11, "end'
    '_col": 38, "end_line": 10, "line": 10}, "syscall_id": null}, {"comparators": [{"node": "'
    'constant", "span": {"col": 57, "end_col": 59, "end_line": 10, "line": 10}, "value": "", '
    '"value_type": "str"}], "left": {"host_binding_id": null, "id": "token_name", "node": "na'
    'me", "span": {"col": 43, "end_col": 53, "end_line": 10, "line": 10}}, "node": "compare",'
    ' "operators": ["not_eq"], "span": {"col": 43, "end_col": 59, "end_line": 10, "line": 10}'
    '}]}}, {"message": {"node": "constant", "span": {"col": 65, "end_col": 98, "end_line": 11'
    ', "line": 11}, "value": "token_symbol must be non-empty.", "value_type": "str"}, "node":'
    ' "assert", "span": {"col": 4, "end_col": 98, "end_line": 11, "line": 11}, "test": {"node'
    '": "bool_op", "operator": "and", "span": {"col": 11, "end_col": 63, "end_line": 11, "lin'
    'e": 11}, "values": [{"args": [{"host_binding_id": null, "id": "token_symbol", "node": "n'
    'ame", "span": {"col": 22, "end_col": 34, "end_line": 11, "line": 11}}, {"host_binding_id'
    '": null, "id": "str", "node": "name", "span": {"col": 36, "end_col": 39, "end_line": 11,'
    ' "line": 11}}], "event_binding": null, "func": {"host_binding_id": null, "id": "isinstan'
    'ce", "node": "name", "span": {"col": 11, "end_col": 21, "end_line": 11, "line": 11}}, "k'
    'eywords": [], "node": "call", "span": {"col": 11, "end_col": 40, "end_line": 11, "line":'
    ' 11}, "syscall_id": null}, {"comparators": [{"node": "constant", "span": {"col": 61, "en'
    'd_col": 63, "end_line": 11, "line": 11}, "value": "", "value_type": "str"}], "left": {"h'
    'ost_binding_id": null, "id": "token_symbol", "node": "name", "span": {"col": 45, "end_co'
    'l": 57, "end_line": 11, "line": 11}}, "node": "compare", "operators": ["not_eq"], "span"'
    ': {"col": 45, "end_col": 63, "end_line": 11, "line": 11}}]}}, {"message": {"node": "cons'
    'tant", "span": {"col": 44, "end_col": 78, "end_line": 12, "line": 12}, "value": "token_l'
    'ogo_url must be a string.", "value_type": "str"}, "node": "assert", "span": {"col": 4, "'
    'end_col": 78, "end_line": 12, "line": 12}, "test": {"args": [{"host_binding_id": null, "'
    'id": "token_logo_url", "node": "name", "span": {"col": 22, "end_col": 36, "end_line": 12'
    ', "line": 12}}, {"host_binding_id": null, "id": "str", "node": "name", "span": {"col": 3'
    '8, "end_col": 41, "end_line": 12, "line": 12}}], "event_binding": null, "func": {"host_b'
    'inding_id": null, "id": "isinstance", "node": "name", "span": {"col": 11, "end_col": 21,'
    ' "end_line": 12, "line": 12}}, "keywords": [], "node": "call", "span": {"col": 11, "end_'
    'col": 42, "end_line": 12, "line": 12}, "syscall_id": null}}, {"message": {"node": "const'
    'ant", "span": {"col": 44, "end_col": 78, "end_line": 13, "line": 13}, "value": "token_lo'
    'go_svg must be a string.", "value_type": "str"}, "node": "assert", "span": {"col": 4, "e'
    'nd_col": 78, "end_line": 13, "line": 13}, "test": {"args": [{"host_binding_id": null, "i'
    'd": "token_logo_svg", "node": "name", "span": {"col": 22, "end_col": 36, "end_line": 13,'
    ' "line": 13}}, {"host_binding_id": null, "id": "str", "node": "name", "span": {"col": 38'
    ', "end_col": 41, "end_line": 13, "line": 13}}], "event_binding": null, "func": {"host_bi'
    'nding_id": null, "id": "isinstance", "node": "name", "span": {"col": 11, "end_col": 21, '
    '"end_line": 13, "line": 13}}, "keywords": [], "node": "call", "span": {"col": 11, "end_c'
    'ol": 42, "end_line": 13, "line": 13}, "syscall_id": null}}, {"message": {"node": "consta'
    'nt", "span": {"col": 43, "end_col": 76, "end_line": 14, "line": 14}, "value": "token_web'
    'site must be a string.", "value_type": "str"}, "node": "assert", "span": {"col": 4, "end'
    '_col": 76, "end_line": 14, "line": 14}, "test": {"args": [{"host_binding_id": null, "id"'
    ': "token_website", "node": "name", "span": {"col": 22, "end_col": 35, "end_line": 14, "l'
    'ine": 14}}, {"host_binding_id": null, "id": "str", "node": "name", "span": {"col": 37, "'
    'end_col": 40, "end_line": 14, "line": 14}}], "event_binding": null, "func": {"host_bindi'
    'ng_id": null, "id": "isinstance", "node": "name", "span": {"col": 11, "end_col": 21, "en'
    'd_line": 14, "line": 14}}, "keywords": [], "node": "call", "span": {"col": 11, "end_col"'
    ': 41, "end_line": 14, "line": 14}, "syscall_id": null}}, {"message": {"node": "constant"'
    ', "span": {"col": 62, "end_col": 95, "end_line": 15, "line": 15}, "value": "initial_supp'
    'ly must be numeric.", "value_type": "str"}, "node": "assert", "span": {"col": 4, "end_co'
    'l": 95, "end_line": 15, "line": 15}, "test": {"args": [{"host_binding_id": null, "id": "'
    'initial_supply", "node": "name", "span": {"col": 22, "end_col": 36, "end_line": 15, "lin'
    'e": 15}}, {"elements": [{"host_binding_id": null, "id": "int", "node": "name", "span": {'
    '"col": 39, "end_col": 42, "end_line": 15, "line": 15}}, {"host_binding_id": null, "id": '
    '"float", "node": "name", "span": {"col": 44, "end_col": 49, "end_line": 15, "line": 15}}'
    ', {"host_binding_id": "numeric.decimal.new", "id": "decimal", "node": "name", "span": {"'
    'col": 51, "end_col": 58, "end_line": 15, "line": 15}}], "node": "tuple", "span": {"col":'
    ' 38, "end_col": 59, "end_line": 15, "line": 15}}], "event_binding": null, "func": {"host'
    '_binding_id": null, "id": "isinstance", "node": "name", "span": {"col": 11, "end_col": 2'
    '1, "end_line": 15, "line": 15}}, "keywords": [], "node": "call", "span": {"col": 11, "en'
    'd_col": 60, "end_line": 15, "line": 15}, "syscall_id": null}}, {"message": {"node": "con'
    'stant", "span": {"col": 32, "end_col": 70, "end_line": 16, "line": 16}, "value": "initia'
    'l_supply must be non-negative.", "value_type": "str"}, "node": "assert", "span": {"col":'
    ' 4, "end_col": 70, "end_line": 16, "line": 16}, "test": {"comparators": [{"node": "const'
    'ant", "span": {"col": 29, "end_col": 30, "end_line": 16, "line": 16}, "value": 0, "value'
    '_type": "int"}], "left": {"host_binding_id": null, "id": "initial_supply", "node": "name'
    '", "span": {"col": 11, "end_col": 25, "end_line": 16, "line": 16}}, "node": "compare", "'
    'operators": ["gt_e"], "span": {"col": 11, "end_col": 30, "end_line": 16, "line": 16}}}, '
    '{"message": {"node": "constant", "span": {"col": 69, "end_col": 104, "end_line": 17, "li'
    'ne": 17}, "value": "initial_holder must be non-empty.", "value_type": "str"}, "node": "a'
    'ssert", "span": {"col": 4, "end_col": 104, "end_line": 17, "line": 17}, "test": {"node":'
    ' "bool_op", "operator": "and", "span": {"col": 11, "end_col": 67, "end_line": 17, "line"'
    ': 17}, "values": [{"args": [{"host_binding_id": null, "id": "initial_holder", "node": "n'
    'ame", "span": {"col": 22, "end_col": 36, "end_line": 17, "line": 17}}, {"host_binding_id'
    '": null, "id": "str", "node": "name", "span": {"col": 38, "end_col": 41, "end_line": 17,'
    ' "line": 17}}], "event_binding": null, "func": {"host_binding_id": null, "id": "isinstan'
    'ce", "node": "name", "span": {"col": 11, "end_col": 21, "end_line": 17, "line": 17}}, "k'
    'eywords": [], "node": "call", "span": {"col": 11, "end_col": 42, "end_line": 17, "line":'
    ' 17}, "syscall_id": null}, {"comparators": [{"node": "constant", "span": {"col": 65, "en'
    'd_col": 67, "end_line": 17, "line": 17}, "value": "", "value_type": "str"}], "left": {"h'
    'ost_binding_id": null, "id": "initial_holder", "node": "name", "span": {"col": 47, "end_'
    'col": 61, "end_line": 17, "line": 17}}, "node": "compare", "operators": ["not_eq"], "spa'
    'n": {"col": 47, "end_col": 67, "end_line": 17, "line": 17}}]}}, {"message": {"node": "co'
    'nstant", "span": {"col": 73, "end_col": 110, "end_line": 18, "line": 18}, "value": "oper'
    'ator_address must be non-empty.", "value_type": "str"}, "node": "assert", "span": {"col"'
    ': 4, "end_col": 110, "end_line": 18, "line": 18}, "test": {"node": "bool_op", "operator"'
    ': "and", "span": {"col": 11, "end_col": 71, "end_line": 18, "line": 18}, "values": [{"ar'
    'gs": [{"host_binding_id": null, "id": "operator_address", "node": "name", "span": {"col"'
    ': 22, "end_col": 38, "end_line": 18, "line": 18}}, {"host_binding_id": null, "id": "str"'
    ', "node": "name", "span": {"col": 40, "end_col": 43, "end_line": 18, "line": 18}}], "eve'
    'nt_binding": null, "func": {"host_binding_id": null, "id": "isinstance", "node": "name",'
    ' "span": {"col": 11, "end_col": 21, "end_line": 18, "line": 18}}, "keywords": [], "node"'
    ': "call", "span": {"col": 11, "end_col": 44, "end_line": 18, "line": 18}, "syscall_id": '
    'null}, {"comparators": [{"node": "constant", "span": {"col": 69, "end_col": 71, "end_lin'
    'e": 18, "line": 18}, "value": "", "value_type": "str"}], "left": {"host_binding_id": nul'
    'l, "id": "operator_address", "node": "name", "span": {"col": 49, "end_col": 65, "end_lin'
    'e": 18, "line": 18}}, "node": "compare", "operators": ["not_eq"], "span": {"col": 49, "e'
    'nd_col": 71, "end_line": 18, "line": 18}}]}}, {"binding": "balances", "key": {"host_bind'
    'ing_id": null, "id": "initial_holder", "node": "name", "span": {"col": 13, "end_col": 27'
    ', "end_line": 19, "line": 19}}, "node": "storage_set", "span": {"col": 4, "end_col": 45,'
    ' "end_line": 19, "line": 19}, "storage_type": "Hash", "syscall_id": "storage.hash.set", '
    '"value": {"host_binding_id": null, "id": "initial_supply", "node": "name", "span": {"col'
    '": 31, "end_col": 45, "end_line": 19, "line": 19}}}, {"binding": "metadata", "key": {"no'
    'de": "constant", "span": {"col": 13, "end_col": 25, "end_line": 20, "line": 20}, "value"'
    ': "token_name", "value_type": "str"}, "node": "storage_set", "span": {"col": 4, "end_col'
    '": 39, "end_line": 20, "line": 20}, "storage_type": "Hash", "syscall_id": "storage.hash.'
    'set", "value": {"host_binding_id": null, "id": "token_name", "node": "name", "span": {"c'
    'ol": 29, "end_col": 39, "end_line": 20, "line": 20}}}, {"binding": "metadata", "key": {"'
    'node": "constant", "span": {"col": 13, "end_col": 27, "end_line": 21, "line": 21}, "valu'
    'e": "token_symbol", "value_type": "str"}, "node": "storage_set", "span": {"col": 4, "end'
    '_col": 43, "end_line": 21, "line": 21}, "storage_type": "Hash", "syscall_id": "storage.h'
    'ash.set", "value": {"host_binding_id": null, "id": "token_symbol", "node": "name", "span'
    '": {"col": 31, "end_col": 43, "end_line": 21, "line": 21}}}, {"binding": "metadata", "ke'
    'y": {"node": "constant", "span": {"col": 13, "end_col": 29, "end_line": 22, "line": 22},'
    ' "value": "token_logo_url", "value_type": "str"}, "node": "storage_set", "span": {"col":'
    ' 4, "end_col": 47, "end_line": 22, "line": 22}, "storage_type": "Hash", "syscall_id": "s'
    'torage.hash.set", "value": {"host_binding_id": null, "id": "token_logo_url", "node": "na'
    'me", "span": {"col": 33, "end_col": 47, "end_line": 22, "line": 22}}}, {"binding": "meta'
    'data", "key": {"node": "constant", "span": {"col": 13, "end_col": 29, "end_line": 23, "l'
    'ine": 23}, "value": "token_logo_svg", "value_type": "str"}, "node": "storage_set", "span'
    '": {"col": 4, "end_col": 47, "end_line": 23, "line": 23}, "storage_type": "Hash", "sysca'
    'll_id": "storage.hash.set", "value": {"host_binding_id": null, "id": "token_logo_svg", "'
    'node": "name", "span": {"col": 33, "end_col": 47, "end_line": 23, "line": 23}}}, {"bindi'
    'ng": "metadata", "key": {"node": "constant", "span": {"col": 13, "end_col": 28, "end_lin'
    'e": 24, "line": 24}, "value": "token_website", "value_type": "str"}, "node": "storage_se'
    't", "span": {"col": 4, "end_col": 45, "end_line": 24, "line": 24}, "storage_type": "Hash'
    '", "syscall_id": "storage.hash.set", "value": {"host_binding_id": null, "id": "token_web'
    'site", "node": "name", "span": {"col": 32, "end_col": 45, "end_line": 24, "line": 24}}},'
    ' {"binding": "metadata", "key": {"node": "constant", "span": {"col": 13, "end_col": 27, '
    '"end_line": 25, "line": 25}, "value": "total_supply", "value_type": "str"}, "node": "sto'
    'rage_set", "span": {"col": 4, "end_col": 45, "end_line": 25, "line": 25}, "storage_type"'
    ': "Hash", "syscall_id": "storage.hash.set", "value": {"host_binding_id": null, "id": "in'
    'itial_supply", "node": "name", "span": {"col": 31, "end_col": 45, "end_line": 25, "line"'
    ': 25}}}, {"node": "expr", "span": {"col": 4, "end_col": 34, "end_line": 26, "line": 26},'
    ' "value": {"args": [{"host_binding_id": null, "id": "operator_address", "node": "name", '
    '"span": {"col": 17, "end_col": 33, "end_line": 26, "line": 26}}], "func": {"attr": "set"'
    ', "host_binding_id": null, "node": "attribute", "path": "operator.set", "span": {"col": '
    '4, "end_col": 16, "end_line": 26, "line": 26}, "value": {"host_binding_id": null, "id": '
    '"operator", "node": "name", "span": {"col": 4, "end_col": 12, "end_line": 26, "line": 26'
    '}}}, "keywords": [], "method": "set", "node": "call", "receiver_binding": "operator", "r'
    'eceiver_type": "Variable", "span": {"col": 4, "end_col": 34, "end_line": 26, "line": 26}'
    ', "syscall_id": "storage.variable.set"}}], "decorator": {"args": [], "keywords": [], "na'
    'me": "construct", "node": "decorator", "span": {"col": 1, "end_col": 10, "end_line": 8, '
    '"line": 8}}, "docstring": null, "name": "seed", "node": "function", "parameters": [{"ann'
    'otation": "str", "default": null, "kind": "positional_or_keyword", "name": "token_name",'
    ' "span": {"col": 9, "end_col": 24, "end_line": 9, "line": 9}}, {"annotation": "str", "de'
    'fault": null, "kind": "positional_or_keyword", "name": "token_symbol", "span": {"col": 2'
    '6, "end_col": 43, "end_line": 9, "line": 9}}, {"annotation": "str", "default": null, "ki'
    'nd": "positional_or_keyword", "name": "token_logo_url", "span": {"col": 45, "end_col": 6'
    '4, "end_line": 9, "line": 9}}, {"annotation": "str", "default": null, "kind": "positiona'
    'l_or_keyword", "name": "token_logo_svg", "span": {"col": 66, "end_col": 85, "end_line": '
    '9, "line": 9}}, {"annotation": "str", "default": null, "kind": "positional_or_keyword", '
    '"name": "token_website", "span": {"col": 87, "end_col": 105, "end_line": 9, "line": 9}},'
    ' {"annotation": "Any", "default": null, "kind": "positional_or_keyword", "name": "initia'
    'l_supply", "span": {"col": 107, "end_col": 126, "end_line": 9, "line": 9}}, {"annotation'
    '": "str", "default": null, "kind": "positional_or_keyword", "name": "initial_holder", "s'
    'pan": {"col": 128, "end_col": 147, "end_line": 9, "line": 9}}, {"annotation": "str", "de'
    'fault": null, "kind": "positional_or_keyword", "name": "operator_address", "span": {"col'
    '": 149, "end_col": 170, "end_line": 9, "line": 9}}], "returns": null, "span": {"col": 0,'
    ' "end_col": 34, "end_line": 26, "line": 9}, "visibility": "construct"}, {"body": [{"mess'
    'age": {"node": "constant", "span": {"col": 41, "end_col": 74, "end_line": 30, "line": 30'
    '}, "value": "Only operator can set metadata!", "value_type": "str"}, "node": "assert", "'
    'span": {"col": 4, "end_col": 74, "end_line": 30, "line": 30}, "test": {"comparators": [{'
    '"args": [], "func": {"attr": "get", "host_binding_id": null, "node": "attribute", "path"'
    ': "operator.get", "span": {"col": 25, "end_col": 37, "end_line": 30, "line": 30}, "value'
    '": {"host_binding_id": null, "id": "operator", "node": "name", "span": {"col": 25, "end_'
    'col": 33, "end_line": 30, "line": 30}}}, "keywords": [], "method": "get", "node": "call"'
    ', "receiver_binding": "operator", "receiver_type": "Variable", "span": {"col": 25, "end_'
    'col": 39, "end_line": 30, "line": 30}, "syscall_id": "storage.variable.get"}], "left": {'
    '"attr": "caller", "host_binding_id": "context.caller", "node": "attribute", "path": "ctx'
    '.caller", "span": {"col": 11, "end_col": 21, "end_line": 30, "line": 30}, "value": {"hos'
    't_binding_id": null, "id": "ctx", "node": "name", "span": {"col": 11, "end_col": 14, "en'
    'd_line": 30, "line": 30}}}, "node": "compare", "operators": ["eq"], "span": {"col": 11, '
    '"end_col": 39, "end_line": 30, "line": 30}}}, {"binding": "metadata", "key": {"host_bind'
    'ing_id": null, "id": "key", "node": "name", "span": {"col": 13, "end_col": 16, "end_line'
    '": 31, "line": 31}}, "node": "storage_set", "span": {"col": 4, "end_col": 25, "end_line"'
    ': 31, "line": 31}, "storage_type": "Hash", "syscall_id": "storage.hash.set", "value": {"'
    'host_binding_id": null, "id": "value", "node": "name", "span": {"col": 20, "end_col": 25'
    ', "end_line": 31, "line": 31}}}], "decorator": {"args": [], "keywords": [], "name": "exp'
    'ort", "node": "decorator", "span": {"col": 1, "end_col": 7, "end_line": 28, "line": 28}}'
    ', "docstring": null, "name": "change_metadata", "node": "function", "parameters": [{"ann'
    'otation": "str", "default": null, "kind": "positional_or_keyword", "name": "key", "span"'
    ': {"col": 20, "end_col": 28, "end_line": 29, "line": 29}}, {"annotation": "Any", "defaul'
    't": null, "kind": "positional_or_keyword", "name": "value", "span": {"col": 30, "end_col'
    '": 40, "end_line": 29, "line": 29}}], "returns": null, "span": {"col": 0, "end_col": 25,'
    ' "end_line": 31, "line": 29}, "visibility": "export"}, {"body": [{"message": {"node": "c'
    'onstant", "span": {"col": 41, "end_col": 77, "end_line": 35, "line": 35}, "value": "Only'
    ' operator can change operator!", "value_type": "str"}, "node": "assert", "span": {"col":'
    ' 4, "end_col": 77, "end_line": 35, "line": 35}, "test": {"comparators": [{"args": [], "f'
    'unc": {"attr": "get", "host_binding_id": null, "node": "attribute", "path": "operator.ge'
    't", "span": {"col": 25, "end_col": 37, "end_line": 35, "line": 35}, "value": {"host_bind'
    'ing_id": null, "id": "operator", "node": "name", "span": {"col": 25, "end_col": 33, "end'
    '_line": 35, "line": 35}}}, "keywords": [], "method": "get", "node": "call", "receiver_bi'
    'nding": "operator", "receiver_type": "Variable", "span": {"col": 25, "end_col": 39, "end'
    '_line": 35, "line": 35}, "syscall_id": "storage.variable.get"}], "left": {"attr": "calle'
    'r", "host_binding_id": "context.caller", "node": "attribute", "path": "ctx.caller", "spa'
    'n": {"col": 11, "end_col": 21, "end_line": 35, "line": 35}, "value": {"host_binding_id":'
    ' null, "id": "ctx", "node": "name", "span": {"col": 11, "end_col": 14, "end_line": 35, "'
    'line": 35}}}, "node": "compare", "operators": ["eq"], "span": {"col": 11, "end_col": 39,'
    ' "end_line": 35, "line": 35}}}, {"message": {"node": "constant", "span": {"col": 65, "en'
    'd_col": 98, "end_line": 36, "line": 36}, "value": "new_operator must be non-empty.", "va'
    'lue_type": "str"}, "node": "assert", "span": {"col": 4, "end_col": 98, "end_line": 36, "'
    'line": 36}, "test": {"node": "bool_op", "operator": "and", "span": {"col": 11, "end_col"'
    ': 63, "end_line": 36, "line": 36}, "values": [{"args": [{"host_binding_id": null, "id": '
    '"new_operator", "node": "name", "span": {"col": 22, "end_col": 34, "end_line": 36, "line'
    '": 36}}, {"host_binding_id": null, "id": "str", "node": "name", "span": {"col": 36, "end'
    '_col": 39, "end_line": 36, "line": 36}}], "event_binding": null, "func": {"host_binding_'
    'id": null, "id": "isinstance", "node": "name", "span": {"col": 11, "end_col": 21, "end_l'
    'ine": 36, "line": 36}}, "keywords": [], "node": "call", "span": {"col": 11, "end_col": 4'
    '0, "end_line": 36, "line": 36}, "syscall_id": null}, {"comparators": [{"node": "constant'
    '", "span": {"col": 61, "end_col": 63, "end_line": 36, "line": 36}, "value": "", "value_t'
    'ype": "str"}], "left": {"host_binding_id": null, "id": "new_operator", "node": "name", "'
    'span": {"col": 45, "end_col": 57, "end_line": 36, "line": 36}}, "node": "compare", "oper'
    'ators": ["not_eq"], "span": {"col": 45, "end_col": 63, "end_line": 36, "line": 36}}]}}, '
    '{"node": "expr", "span": {"col": 4, "end_col": 30, "end_line": 37, "line": 37}, "value":'
    ' {"args": [{"host_binding_id": null, "id": "new_operator", "node": "name", "span": {"col'
    '": 17, "end_col": 29, "end_line": 37, "line": 37}}], "func": {"attr": "set", "host_bindi'
    'ng_id": null, "node": "attribute", "path": "operator.set", "span": {"col": 4, "end_col":'
    ' 16, "end_line": 37, "line": 37}, "value": {"host_binding_id": null, "id": "operator", "'
    'node": "name", "span": {"col": 4, "end_col": 12, "end_line": 37, "line": 37}}}, "keyword'
    's": [], "method": "set", "node": "call", "receiver_binding": "operator", "receiver_type"'
    ': "Variable", "span": {"col": 4, "end_col": 30, "end_line": 37, "line": 37}, "syscall_id'
    '": "storage.variable.set"}}], "decorator": {"args": [], "keywords": [], "name": "export"'
    ', "node": "decorator", "span": {"col": 1, "end_col": 7, "end_line": 33, "line": 33}}, "d'
    'ocstring": null, "name": "change_operator", "node": "function", "parameters": [{"annotat'
    'ion": "str", "default": null, "kind": "positional_or_keyword", "name": "new_operator", "'
    'span": {"col": 20, "end_col": 37, "end_line": 34, "line": 34}}], "returns": null, "span"'
    ': {"col": 0, "end_col": 30, "end_line": 37, "line": 34}, "visibility": "export"}, {"body'
    '": [{"node": "return", "span": {"col": 4, "end_col": 25, "end_line": 41, "line": 41}, "v'
    'alue": {"args": [], "func": {"attr": "get", "host_binding_id": null, "node": "attribute"'
    ', "path": "operator.get", "span": {"col": 11, "end_col": 23, "end_line": 41, "line": 41}'
    ', "value": {"host_binding_id": null, "id": "operator", "node": "name", "span": {"col": 1'
    '1, "end_col": 19, "end_line": 41, "line": 41}}}, "keywords": [], "method": "get", "node"'
    ': "call", "receiver_binding": "operator", "receiver_type": "Variable", "span": {"col": 1'
    '1, "end_col": 25, "end_line": 41, "line": 41}, "syscall_id": "storage.variable.get"}}], '
    '"decorator": {"args": [], "keywords": [], "name": "export", "node": "decorator", "span":'
    ' {"col": 1, "end_col": 7, "end_line": 39, "line": 39}}, "docstring": null, "name": "oper'
    'ator_of", "node": "function", "parameters": [], "returns": null, "span": {"col": 0, "end'
    '_col": 25, "end_line": 41, "line": 40}, "visibility": "export"}, {"body": [{"node": "ret'
    'urn", "span": {"col": 4, "end_col": 28, "end_line": 45, "line": 45}, "value": {"binding"'
    ': "balances", "key": {"host_binding_id": null, "id": "address", "node": "name", "span": '
    '{"col": 20, "end_col": 27, "end_line": 45, "line": 45}}, "node": "storage_get", "span": '
    '{"col": 11, "end_col": 28, "end_line": 45, "line": 45}, "storage_type": "Hash", "syscall'
    '_id": "storage.hash.get"}}], "decorator": {"args": [], "keywords": [], "name": "export",'
    ' "node": "decorator", "span": {"col": 1, "end_col": 7, "end_line": 43, "line": 43}}, "do'
    'cstring": null, "name": "balance_of", "node": "function", "parameters": [{"annotation": '
    '"str", "default": null, "kind": "positional_or_keyword", "name": "address", "span": {"co'
    'l": 15, "end_col": 27, "end_line": 44, "line": 44}}], "returns": null, "span": {"col": 0'
    ', "end_col": 28, "end_line": 45, "line": 44}, "visibility": "export"}, {"body": [{"messa'
    'ge": {"node": "constant", "span": {"col": 23, "end_col": 55, "end_line": 49, "line": 49}'
    ', "value": "Cannot send negative balances!", "value_type": "str"}, "node": "assert", "sp'
    'an": {"col": 4, "end_col": 55, "end_line": 49, "line": 49}, "test": {"comparators": [{"n'
    'ode": "constant", "span": {"col": 20, "end_col": 21, "end_line": 49, "line": 49}, "value'
    '": 0, "value_type": "int"}], "left": {"host_binding_id": null, "id": "amount", "node": "'
    'name", "span": {"col": 11, "end_col": 17, "end_line": 49, "line": 49}}, "node": "compare'
    '", "operators": ["gt"], "span": {"col": 11, "end_col": 21, "end_line": 49, "line": 49}}}'
    ', {"message": {"node": "constant", "span": {"col": 43, "end_col": 70, "end_line": 50, "l'
    'ine": 50}, "value": "Not enough coins to send!", "value_type": "str"}, "node": "assert",'
    ' "span": {"col": 4, "end_col": 70, "end_line": 50, "line": 50}, "test": {"comparators": '
    '[{"host_binding_id": null, "id": "amount", "node": "name", "span": {"col": 35, "end_col"'
    ': 41, "end_line": 50, "line": 50}}], "left": {"binding": "balances", "key": {"attr": "ca'
    'ller", "host_binding_id": "context.caller", "node": "attribute", "path": "ctx.caller", "'
    'span": {"col": 20, "end_col": 30, "end_line": 50, "line": 50}, "value": {"host_binding_i'
    'd": null, "id": "ctx", "node": "name", "span": {"col": 20, "end_col": 23, "end_line": 50'
    ', "line": 50}}}, "node": "storage_get", "span": {"col": 11, "end_col": 31, "end_line": 5'
    '0, "line": 50}, "storage_type": "Hash", "syscall_id": "storage.hash.get"}, "node": "comp'
    'are", "operators": ["gt_e"], "span": {"col": 11, "end_col": 41, "end_line": 50, "line": '
    '50}}}, {"binding": "balances", "key": {"attr": "caller", "host_binding_id": "context.cal'
    'ler", "node": "attribute", "path": "ctx.caller", "span": {"col": 13, "end_col": 23, "end'
    '_line": 51, "line": 51}, "value": {"host_binding_id": null, "id": "ctx", "node": "name",'
    ' "span": {"col": 13, "end_col": 16, "end_line": 51, "line": 51}}}, "node": "storage_muta'
    'te", "operator": "sub", "read_syscall_id": "storage.hash.get", "span": {"col": 4, "end_c'
    'ol": 34, "end_line": 51, "line": 51}, "storage_type": "Hash", "value": {"host_binding_id'
    '": null, "id": "amount", "node": "name", "span": {"col": 28, "end_col": 34, "end_line": '
    '51, "line": 51}}, "write_syscall_id": "storage.hash.set"}, {"binding": "balances", "key"'
    ': {"host_binding_id": null, "id": "to", "node": "name", "span": {"col": 13, "end_col": 1'
    '5, "end_line": 52, "line": 52}}, "node": "storage_mutate", "operator": "add", "read_sysc'
    'all_id": "storage.hash.get", "span": {"col": 4, "end_col": 26, "end_line": 52, "line": 5'
    '2}, "storage_type": "Hash", "value": {"host_binding_id": null, "id": "amount", "node": "'
    'name", "span": {"col": 20, "end_col": 26, "end_line": 52, "line": 52}}, "write_syscall_i'
    'd": "storage.hash.set"}, {"node": "expr", "span": {"col": 4, "end_col": 67, "end_line": '
    '53, "line": 53}, "value": {"args": [{"entries": [{"key": {"node": "constant", "span": {"'
    'col": 19, "end_col": 25, "end_line": 53, "line": 53}, "value": "from", "value_type": "st'
    'r"}, "value": {"attr": "caller", "host_binding_id": "context.caller", "node": "attribute'
    '", "path": "ctx.caller", "span": {"col": 27, "end_col": 37, "end_line": 53, "line": 53},'
    ' "value": {"host_binding_id": null, "id": "ctx", "node": "name", "span": {"col": 27, "en'
    'd_col": 30, "end_line": 53, "line": 53}}}}, {"key": {"node": "constant", "span": {"col":'
    ' 39, "end_col": 43, "end_line": 53, "line": 53}, "value": "to", "value_type": "str"}, "v'
    'alue": {"host_binding_id": null, "id": "to", "node": "name", "span": {"col": 45, "end_co'
    'l": 47, "end_line": 53, "line": 53}}}, {"key": {"node": "constant", "span": {"col": 49, '
    '"end_col": 57, "end_line": 53, "line": 53}, "value": "amount", "value_type": "str"}, "va'
    'lue": {"host_binding_id": null, "id": "amount", "node": "name", "span": {"col": 59, "end'
    '_col": 65, "end_line": 53, "line": 53}}}], "node": "dict", "span": {"col": 18, "end_col"'
    ': 66, "end_line": 53, "line": 53}}], "event_binding": "TransferEvent", "func": {"host_bi'
    'nding_id": null, "id": "TransferEvent", "node": "name", "span": {"col": 4, "end_col": 17'
    ', "end_line": 53, "line": 53}}, "keywords": [], "node": "call", "span": {"col": 4, "end_'
    'col": 67, "end_line": 53, "line": 53}, "syscall_id": "event.log.emit"}}], "decorator": {'
    '"args": [], "keywords": [], "name": "export", "node": "decorator", "span": {"col": 1, "e'
    'nd_col": 7, "end_line": 47, "line": 47}}, "docstring": null, "name": "transfer", "node":'
    ' "function", "parameters": [{"annotation": "float", "default": null, "kind": "positional'
    '_or_keyword", "name": "amount", "span": {"col": 13, "end_col": 26, "end_line": 48, "line'
    '": 48}}, {"annotation": "str", "default": null, "kind": "positional_or_keyword", "name":'
    ' "to", "span": {"col": 28, "end_col": 35, "end_line": 48, "line": 48}}], "returns": null'
    ', "span": {"col": 0, "end_col": 67, "end_line": 53, "line": 48}, "visibility": "export"}'
    ', {"body": [{"message": {"node": "constant", "span": {"col": 24, "end_col": 59, "end_lin'
    'e": 57, "line": 57}, "value": "Cannot approve negative balances!", "value_type": "str"},'
    ' "node": "assert", "span": {"col": 4, "end_col": 59, "end_line": 57, "line": 57}, "test"'
    ': {"comparators": [{"node": "constant", "span": {"col": 21, "end_col": 22, "end_line": 5'
    '7, "line": 57}, "value": 0, "value_type": "int"}], "left": {"host_binding_id": null, "id'
    '": "amount", "node": "name", "span": {"col": 11, "end_col": 17, "end_line": 57, "line": '
    '57}}, "node": "compare", "operators": ["gt_e"], "span": {"col": 11, "end_col": 22, "end_'
    'line": 57, "line": 57}}}, {"binding": "approvals", "key": {"elements": [{"attr": "caller'
    '", "host_binding_id": "context.caller", "node": "attribute", "path": "ctx.caller", "span'
    '": {"col": 14, "end_col": 24, "end_line": 58, "line": 58}, "value": {"host_binding_id": '
    'null, "id": "ctx", "node": "name", "span": {"col": 14, "end_col": 17, "end_line": 58, "l'
    'ine": 58}}}, {"host_binding_id": null, "id": "to", "node": "name", "span": {"col": 26, "'
    'end_col": 28, "end_line": 58, "line": 58}}], "node": "tuple", "span": {"col": 14, "end_c'
    'ol": 28, "end_line": 58, "line": 58}}, "node": "storage_set", "span": {"col": 4, "end_co'
    'l": 38, "end_line": 58, "line": 58}, "storage_type": "Hash", "syscall_id": "storage.hash'
    '.set", "value": {"host_binding_id": null, "id": "amount", "node": "name", "span": {"col"'
    ': 32, "end_col": 38, "end_line": 58, "line": 58}}}, {"node": "expr", "span": {"col": 4, '
    '"end_col": 66, "end_line": 59, "line": 59}, "value": {"args": [{"entries": [{"key": {"no'
    'de": "constant", "span": {"col": 18, "end_col": 24, "end_line": 59, "line": 59}, "value"'
    ': "from", "value_type": "str"}, "value": {"attr": "caller", "host_binding_id": "context.'
    'caller", "node": "attribute", "path": "ctx.caller", "span": {"col": 26, "end_col": 36, "'
    'end_line": 59, "line": 59}, "value": {"host_binding_id": null, "id": "ctx", "node": "nam'
    'e", "span": {"col": 26, "end_col": 29, "end_line": 59, "line": 59}}}}, {"key": {"node": '
    '"constant", "span": {"col": 38, "end_col": 42, "end_line": 59, "line": 59}, "value": "to'
    '", "value_type": "str"}, "value": {"host_binding_id": null, "id": "to", "node": "name", '
    '"span": {"col": 44, "end_col": 46, "end_line": 59, "line": 59}}}, {"key": {"node": "cons'
    'tant", "span": {"col": 48, "end_col": 56, "end_line": 59, "line": 59}, "value": "amount"'
    ', "value_type": "str"}, "value": {"host_binding_id": null, "id": "amount", "node": "name'
    '", "span": {"col": 58, "end_col": 64, "end_line": 59, "line": 59}}}], "node": "dict", "s'
    'pan": {"col": 17, "end_col": 65, "end_line": 59, "line": 59}}], "event_binding": "Approv'
    'eEvent", "func": {"host_binding_id": null, "id": "ApproveEvent", "node": "name", "span":'
    ' {"col": 4, "end_col": 16, "end_line": 59, "line": 59}}, "keywords": [], "node": "call",'
    ' "span": {"col": 4, "end_col": 66, "end_line": 59, "line": 59}, "syscall_id": "event.log'
    '.emit"}}], "decorator": {"args": [], "keywords": [], "name": "export", "node": "decorato'
    'r", "span": {"col": 1, "end_col": 7, "end_line": 55, "line": 55}}, "docstring": null, "n'
    'ame": "approve", "node": "function", "parameters": [{"annotation": "float", "default": n'
    'ull, "kind": "positional_or_keyword", "name": "amount", "span": {"col": 12, "end_col": 2'
    '5, "end_line": 56, "line": 56}}, {"annotation": "str", "default": null, "kind": "positio'
    'nal_or_keyword", "name": "to", "span": {"col": 27, "end_col": 34, "end_line": 56, "line"'
    ': 56}}], "returns": null, "span": {"col": 0, "end_col": 66, "end_line": 59, "line": 56},'
    ' "visibility": "export"}, {"body": [{"message": {"node": "constant", "span": {"col": 23,'
    ' "end_col": 55, "end_line": 63, "line": 63}, "value": "Cannot send negative balances!", '
    '"value_type": "str"}, "node": "assert", "span": {"col": 4, "end_col": 55, "end_line": 63'
    ', "line": 63}, "test": {"comparators": [{"node": "constant", "span": {"col": 20, "end_co'
    'l": 21, "end_line": 63, "line": 63}, "value": 0, "value_type": "int"}], "left": {"host_b'
    'inding_id": null, "id": "amount", "node": "name", "span": {"col": 11, "end_col": 17, "en'
    'd_line": 63, "line": 63}}, "node": "compare", "operators": ["gt"], "span": {"col": 11, "'
    'end_col": 21, "end_line": 63, "line": 63}}}, {"message": {"node": "f_string", "span": {"'
    'col": 58, "end_col": 175, "end_line": 64, "line": 64}, "values": [{"node": "constant", "'
    'span": {"col": 60, "end_col": 104, "end_line": 64, "line": 64}, "value": "Not enough coi'
    'ns approved to send! You have ", "value_type": "str"}, {"conversion": null, "format_spec'
    '": null, "node": "formatted_value", "span": {"col": 104, "end_col": 141, "end_line": 64,'
    ' "line": 64}, "value": {"binding": "approvals", "key": {"elements": [{"host_binding_id":'
    ' null, "id": "main_account", "node": "name", "span": {"col": 115, "end_col": 127, "end_l'
    'ine": 64, "line": 64}}, {"attr": "caller", "host_binding_id": "context.caller", "node": '
    '"attribute", "path": "ctx.caller", "span": {"col": 129, "end_col": 139, "end_line": 64, '
    '"line": 64}, "value": {"host_binding_id": null, "id": "ctx", "node": "name", "span": {"c'
    'ol": 129, "end_col": 132, "end_line": 64, "line": 64}}}], "node": "tuple", "span": {"col'
    '": 115, "end_col": 139, "end_line": 64, "line": 64}}, "node": "storage_get", "span": {"c'
    'ol": 105, "end_col": 140, "end_line": 64, "line": 64}, "storage_type": "Hash", "syscall_'
    'id": "storage.hash.get"}}, {"node": "constant", "span": {"col": 141, "end_col": 166, "en'
    'd_line": 64, "line": 64}, "value": " and are trying to spend ", "value_type": "str"}, {"'
    'conversion": null, "format_spec": null, "node": "formatted_value", "span": {"col": 166, '
    '"end_col": 174, "end_line": 64, "line": 64}, "value": {"host_binding_id": null, "id": "a'
    'mount", "node": "name", "span": {"col": 167, "end_col": 173, "end_line": 64, "line": 64}'
    '}}]}, "node": "assert", "span": {"col": 4, "end_col": 175, "end_line": 64, "line": 64}, '
    '"test": {"comparators": [{"host_binding_id": null, "id": "amount", "node": "name", "span'
    '": {"col": 50, "end_col": 56, "end_line": 64, "line": 64}}], "left": {"binding": "approv'
    'als", "key": {"elements": [{"host_binding_id": null, "id": "main_account", "node": "name'
    '", "span": {"col": 21, "end_col": 33, "end_line": 64, "line": 64}}, {"attr": "caller", "'
    'host_binding_id": "context.caller", "node": "attribute", "path": "ctx.caller", "span": {'
    '"col": 35, "end_col": 45, "end_line": 64, "line": 64}, "value": {"host_binding_id": null'
    ', "id": "ctx", "node": "name", "span": {"col": 35, "end_col": 38, "end_line": 64, "line"'
    ': 64}}}], "node": "tuple", "span": {"col": 21, "end_col": 45, "end_line": 64, "line": 64'
    '}}, "node": "storage_get", "span": {"col": 11, "end_col": 46, "end_line": 64, "line": 64'
    '}, "storage_type": "Hash", "syscall_id": "storage.hash.get"}, "node": "compare", "operat'
    'ors": ["gt_e"], "span": {"col": 11, "end_col": 56, "end_line": 64, "line": 64}}}, {"mess'
    'age": {"node": "constant", "span": {"col": 45, "end_col": 72, "end_line": 65, "line": 65'
    '}, "value": "Not enough coins to send!", "value_type": "str"}, "node": "assert", "span":'
    ' {"col": 4, "end_col": 72, "end_line": 65, "line": 65}, "test": {"comparators": [{"host_'
    'binding_id": null, "id": "amount", "node": "name", "span": {"col": 37, "end_col": 43, "e'
    'nd_line": 65, "line": 65}}], "left": {"binding": "balances", "key": {"host_binding_id": '
    'null, "id": "main_account", "node": "name", "span": {"col": 20, "end_col": 32, "end_line'
    '": 65, "line": 65}}, "node": "storage_get", "span": {"col": 11, "end_col": 33, "end_line'
    '": 65, "line": 65}, "storage_type": "Hash", "syscall_id": "storage.hash.get"}, "node": "'
    'compare", "operators": ["gt_e"], "span": {"col": 11, "end_col": 43, "end_line": 65, "lin'
    'e": 65}}}, {"binding": "approvals", "key": {"elements": [{"host_binding_id": null, "id":'
    ' "main_account", "node": "name", "span": {"col": 14, "end_col": 26, "end_line": 66, "lin'
    'e": 66}}, {"attr": "caller", "host_binding_id": "context.caller", "node": "attribute", "'
    'path": "ctx.caller", "span": {"col": 28, "end_col": 38, "end_line": 66, "line": 66}, "va'
    'lue": {"host_binding_id": null, "id": "ctx", "node": "name", "span": {"col": 28, "end_co'
    'l": 31, "end_line": 66, "line": 66}}}], "node": "tuple", "span": {"col": 14, "end_col": '
    '38, "end_line": 66, "line": 66}}, "node": "storage_mutate", "operator": "sub", "read_sys'
    'call_id": "storage.hash.get", "span": {"col": 4, "end_col": 49, "end_line": 66, "line": '
    '66}, "storage_type": "Hash", "value": {"host_binding_id": null, "id": "amount", "node": '
    '"name", "span": {"col": 43, "end_col": 49, "end_line": 66, "line": 66}}, "write_syscall_'
    'id": "storage.hash.set"}, {"binding": "balances", "key": {"host_binding_id": null, "id":'
    ' "main_account", "node": "name", "span": {"col": 13, "end_col": 25, "end_line": 67, "lin'
    'e": 67}}, "node": "storage_mutate", "operator": "sub", "read_syscall_id": "storage.hash.'
    'get", "span": {"col": 4, "end_col": 36, "end_line": 67, "line": 67}, "storage_type": "Ha'
    'sh", "value": {"host_binding_id": null, "id": "amount", "node": "name", "span": {"col": '
    '30, "end_col": 36, "end_line": 67, "line": 67}}, "write_syscall_id": "storage.hash.set"}'
    ', {"binding": "balances", "key": {"host_binding_id": null, "id": "to", "node": "name", "'
    'span": {"col": 13, "end_col": 15, "end_line": 68, "line": 68}}, "node": "storage_mutate"'
    ', "operator": "add", "read_syscall_id": "storage.hash.get", "span": {"col": 4, "end_col"'
    ': 26, "end_line": 68, "line": 68}, "storage_type": "Hash", "value": {"host_binding_id": '
    'null, "id": "amount", "node": "name", "span": {"col": 20, "end_col": 26, "end_line": 68,'
    ' "line": 68}}, "write_syscall_id": "storage.hash.set"}, {"node": "expr", "span": {"col":'
    ' 4, "end_col": 69, "end_line": 69, "line": 69}, "value": {"args": [{"entries": [{"key": '
    '{"node": "constant", "span": {"col": 19, "end_col": 25, "end_line": 69, "line": 69}, "va'
    'lue": "from", "value_type": "str"}, "value": {"host_binding_id": null, "id": "main_accou'
    'nt", "node": "name", "span": {"col": 27, "end_col": 39, "end_line": 69, "line": 69}}}, {'
    '"key": {"node": "constant", "span": {"col": 41, "end_col": 45, "end_line": 69, "line": 6'
    '9}, "value": "to", "value_type": "str"}, "value": {"host_binding_id": null, "id": "to", '
    '"node": "name", "span": {"col": 47, "end_col": 49, "end_line": 69, "line": 69}}}, {"key"'
    ': {"node": "constant", "span": {"col": 51, "end_col": 59, "end_line": 69, "line": 69}, "'
    'value": "amount", "value_type": "str"}, "value": {"host_binding_id": null, "id": "amount'
    '", "node": "name", "span": {"col": 61, "end_col": 67, "end_line": 69, "line": 69}}}], "n'
    'ode": "dict", "span": {"col": 18, "end_col": 68, "end_line": 69, "line": 69}}], "event_b'
    'inding": "TransferEvent", "func": {"host_binding_id": null, "id": "TransferEvent", "node'
    '": "name", "span": {"col": 4, "end_col": 17, "end_line": 69, "line": 69}}, "keywords": ['
    '], "node": "call", "span": {"col": 4, "end_col": 69, "end_line": 69, "line": 69}, "sysca'
    'll_id": "event.log.emit"}}], "decorator": {"args": [], "keywords": [], "name": "export",'
    ' "node": "decorator", "span": {"col": 1, "end_col": 7, "end_line": 61, "line": 61}}, "do'
    'cstring": null, "name": "transfer_from", "node": "function", "parameters": [{"annotation'
    '": "float", "default": null, "kind": "positional_or_keyword", "name": "amount", "span": '
    '{"col": 18, "end_col": 31, "end_line": 62, "line": 62}}, {"annotation": "str", "default"'
    ': null, "kind": "positional_or_keyword", "name": "to", "span": {"col": 33, "end_col": 40'
    ', "end_line": 62, "line": 62}}, {"annotation": "str", "default": null, "kind": "position'
    'al_or_keyword", "name": "main_account", "span": {"col": 42, "end_col": 59, "end_line": 6'
    '2, "line": 62}}], "returns": null, "span": {"col": 0, "end_col": 69, "end_line": 69, "li'
    'ne": 62}, "visibility": "export"}], "global_declarations": [{"args": [], "keywords": [{"'
    'arg": "default_value", "node": "keyword", "span": {"col": 16, "end_col": 31, "end_line":'
    ' 1, "line": 1}, "value": {"node": "constant", "span": {"col": 30, "end_col": 31, "end_li'
    'ne": 1, "line": 1}, "value": 0, "value_type": "int"}}], "name": "balances", "node": "sto'
    'rage_decl", "span": {"col": 0, "end_col": 32, "end_line": 1, "line": 1}, "storage_type":'
    ' "Hash", "syscall_id": "storage.hash.new"}, {"args": [], "keywords": [{"arg": "default_v'
    'alue", "node": "keyword", "span": {"col": 17, "end_col": 32, "end_line": 2, "line": 2}, '
    '"value": {"node": "constant", "span": {"col": 31, "end_col": 32, "end_line": 2, "line": '
    '2}, "value": 0, "value_type": "int"}}], "name": "approvals", "node": "storage_decl", "sp'
    'an": {"col": 0, "end_col": 33, "end_line": 2, "line": 2}, "storage_type": "Hash", "sysca'
    'll_id": "storage.hash.new"}, {"args": [], "keywords": [], "name": "metadata", "node": "s'
    'torage_decl", "span": {"col": 0, "end_col": 17, "end_line": 3, "line": 3}, "storage_type'
    '": "Hash", "syscall_id": "storage.hash.new"}, {"args": [], "keywords": [], "name": "oper'
    'ator", "node": "storage_decl", "span": {"col": 0, "end_col": 21, "end_line": 4, "line": '
    '4}, "storage_type": "Variable", "syscall_id": "storage.variable.new"}, {"event_name": "T'
    'ransfer", "name": "TransferEvent", "node": "event_decl", "params": {"entries": [{"key": '
    '{"node": "constant", "span": {"col": 38, "end_col": 44, "end_line": 5, "line": 5}, "valu'
    'e": "from", "value_type": "str"}, "value": {"args": [{"host_binding_id": null, "id": "st'
    'r", "node": "name", "span": {"col": 54, "end_col": 57, "end_line": 5, "line": 5}}], "eve'
    'nt_binding": null, "func": {"host_binding_id": "event.indexed", "id": "indexed", "node":'
    ' "name", "span": {"col": 46, "end_col": 53, "end_line": 5, "line": 5}}, "keywords": [], '
    '"node": "call", "span": {"col": 46, "end_col": 58, "end_line": 5, "line": 5}, "syscall_i'
    'd": "event.indexed"}}, {"key": {"node": "constant", "span": {"col": 60, "end_col": 64, "'
    'end_line": 5, "line": 5}, "value": "to", "value_type": "str"}, "value": {"args": [{"host'
    '_binding_id": null, "id": "str", "node": "name", "span": {"col": 74, "end_col": 77, "end'
    '_line": 5, "line": 5}}], "event_binding": null, "func": {"host_binding_id": "event.index'
    'ed", "id": "indexed", "node": "name", "span": {"col": 66, "end_col": 73, "end_line": 5, '
    '"line": 5}}, "keywords": [], "node": "call", "span": {"col": 66, "end_col": 78, "end_lin'
    'e": 5, "line": 5}, "syscall_id": "event.indexed"}}, {"key": {"node": "constant", "span":'
    ' {"col": 80, "end_col": 88, "end_line": 5, "line": 5}, "value": "amount", "value_type": '
    '"str"}, "value": {"elements": [{"host_binding_id": null, "id": "int", "node": "name", "s'
    'pan": {"col": 91, "end_col": 94, "end_line": 5, "line": 5}}, {"host_binding_id": null, "'
    'id": "float", "node": "name", "span": {"col": 96, "end_col": 101, "end_line": 5, "line":'
    ' 5}}, {"host_binding_id": "numeric.decimal.new", "id": "decimal", "node": "name", "span"'
    ': {"col": 103, "end_col": 110, "end_line": 5, "line": 5}}], "node": "tuple", "span": {"c'
    'ol": 90, "end_col": 111, "end_line": 5, "line": 5}}}], "node": "dict", "span": {"col": 3'
    '7, "end_col": 112, "end_line": 5, "line": 5}}, "span": {"col": 0, "end_col": 113, "end_l'
    'ine": 5, "line": 5}, "syscall_id": "event.log.new"}, {"event_name": "Approve", "name": "'
    'ApproveEvent", "node": "event_decl", "params": {"entries": [{"key": {"node": "constant",'
    ' "span": {"col": 36, "end_col": 42, "end_line": 6, "line": 6}, "value": "from", "value_t'
    'ype": "str"}, "value": {"args": [{"host_binding_id": null, "id": "str", "node": "name", '
    '"span": {"col": 52, "end_col": 55, "end_line": 6, "line": 6}}], "event_binding": null, "'
    'func": {"host_binding_id": "event.indexed", "id": "indexed", "node": "name", "span": {"c'
    'ol": 44, "end_col": 51, "end_line": 6, "line": 6}}, "keywords": [], "node": "call", "spa'
    'n": {"col": 44, "end_col": 56, "end_line": 6, "line": 6}, "syscall_id": "event.indexed"}'
    '}, {"key": {"node": "constant", "span": {"col": 58, "end_col": 62, "end_line": 6, "line"'
    ': 6}, "value": "to", "value_type": "str"}, "value": {"args": [{"host_binding_id": null, '
    '"id": "str", "node": "name", "span": {"col": 72, "end_col": 75, "end_line": 6, "line": 6'
    '}}], "event_binding": null, "func": {"host_binding_id": "event.indexed", "id": "indexed"'
    ', "node": "name", "span": {"col": 64, "end_col": 71, "end_line": 6, "line": 6}}, "keywor'
    'ds": [], "node": "call", "span": {"col": 64, "end_col": 76, "end_line": 6, "line": 6}, "'
    'syscall_id": "event.indexed"}}, {"key": {"node": "constant", "span": {"col": 78, "end_co'
    'l": 86, "end_line": 6, "line": 6}, "value": "amount", "value_type": "str"}, "value": {"e'
    'lements": [{"host_binding_id": null, "id": "int", "node": "name", "span": {"col": 89, "e'
    'nd_col": 92, "end_line": 6, "line": 6}}, {"host_binding_id": null, "id": "float", "node"'
    ': "name", "span": {"col": 94, "end_col": 99, "end_line": 6, "line": 6}}, {"host_binding_'
    'id": "numeric.decimal.new", "id": "decimal", "node": "name", "span": {"col": 101, "end_c'
    'ol": 108, "end_line": 6, "line": 6}}], "node": "tuple", "span": {"col": 88, "end_col": 1'
    '09, "end_line": 6, "line": 6}}}], "node": "dict", "span": {"col": 35, "end_col": 110, "e'
    'nd_line": 6, "line": 6}}, "span": {"col": 0, "end_col": 111, "end_line": 6, "line": 6}, '
    '"syscall_id": "event.log.new"}], "host_catalog_version": "xian_vm_v1_host_v1", "host_dep'
    'endencies": [{"binding": "ctx.caller", "category": "context", "id": "context.caller", "k'
    'ind": "context_field"}, {"binding": "indexed", "category": "event", "id": "event.indexed'
    '", "kind": "syscall"}, {"binding": "LogEvent.__call__", "category": "event", "id": "even'
    't.log.emit", "kind": "syscall"}, {"binding": "LogEvent", "category": "event", "id": "eve'
    'nt.log.new", "kind": "syscall"}, {"binding": "decimal", "category": "numeric", "id": "nu'
    'meric.decimal.new", "kind": "syscall"}, {"binding": "Hash.__getitem__", "category": "sto'
    'rage", "id": "storage.hash.get", "kind": "syscall"}, {"binding": "Hash", "category": "st'
    'orage", "id": "storage.hash.new", "kind": "syscall"}, {"binding": "Hash.__setitem__", "c'
    'ategory": "storage", "id": "storage.hash.set", "kind": "syscall"}, {"binding": "Variable'
    '.get", "category": "storage", "id": "storage.variable.get", "kind": "syscall"}, {"bindin'
    'g": "Variable", "category": "storage", "id": "storage.variable.new", "kind": "syscall"},'
    ' {"binding": "Variable.set", "category": "storage", "id": "storage.variable.set", "kind"'
    ': "syscall"}, {"binding": "Any", "category": "typing", "id": "typing.any", "kind": "type'
    '_marker"}], "imports": [], "ir_version": "xian_ir_v1", "module_body": [], "module_name":'
    ' "__TEMPLATE__", "source_hash": "2fb3e276c1fae67986d16ab980daa98e8c740b42fb0e8e8831d3dbb'
    'd6c7c3866", "vm_profile": "xian_vm_v1"}'
)

XSC001_TOKEN_ARTIFACT_FORMAT = "xian_contract_artifact_v1"
XSC001_TOKEN_VM_PROFILE = "xian_vm_v1"
XSC001_TOKEN_TEMPLATE_MODULE = "__TEMPLATE__"
XSC001_TOKEN_SOURCE_SHA256 = "2fb3e276c1fae67986d16ab980daa98e8c740b42fb0e8e8831d3dbbd6c7c3866"
XSC001_TOKEN_INPUT_SOURCE_SHA256 = "d87cc2b3865c835d4c752df229c52147d7a684afd7b633b0e5130f083efe5f37"
# GENERATED TOKEN FACTORY ARTIFACTS END

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
