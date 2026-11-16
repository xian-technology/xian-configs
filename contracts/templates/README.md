# Token Factory Templates

`token_factory_xsc001_token_template.s.py` owns the source of tokens created by
the factory. `token_factory_contract_template.s.py` owns the factory wrapper.
The generator embeds the canonical child source into `../token_factory.s.py`;
edit the templates rather than the generated contract.

Hex public-key initial holders, operators, transfer recipients and approval
targets must use canonical lowercase spelling. A mixed-case hex key cannot
sign transactions as that account. Named contract targets retain their exact
spelling. The contract rejects invalid spellings rather than rewriting signed
arguments.

Regenerate and verify from the repository root:

```bash
uv run --project ../xian-cli python scripts/generate_token_factory_artifacts.py --write
uv run --project ../xian-cli python scripts/generate_token_factory_artifacts.py --check
uv run --project ../xian-cli --group dev python -m pytest -q tests/test_token_factory_canonical_accounts.py
```
