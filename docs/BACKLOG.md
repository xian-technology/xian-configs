# Backlog

This is the stable backlog entrypoint for `xian-configs`.

Current themes:

- keeping canonical manifests and contract fixtures aligned with the live stack
- growing the canonical network-template catalog in step with `xian-cli`,
  `xian-stack`, and `xian-docs-web`

## Genesis And Launch Blockers

The draft mainnet allocation assigns `66,666,666.60` XIAN (60% of the
`111,111,111` total supply) to `team_lock`, but `contracts_mainnet.json` does
not deploy a contract at that address. The local, devnet, and testnet bundles
use the same balance through `currency.s.py` defaults and also omit a
`team_lock` deployment.

`team_lock` is not a signing public key. The normal submission contract only
permits names beginning with `con_`, so ordinary post-genesis deployment cannot
create the missing wallet under that name. The source asset `vault.s.py` alone
does not make the allocated balance spendable.

Before final mainnet genesis, choose and review the custody design: either
include the wallet contract with accepted owners and quorum in the genesis
bundle, or replace the draft allocation with an accepted spendable custody
address. Do not treat the draft allocation as launch-ready until that decision
and a real custody spend rehearsal are complete.
