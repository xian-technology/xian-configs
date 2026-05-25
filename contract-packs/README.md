# Contract packs

Contract packs are reusable on-chain contract or protocol units that can be
installed onto a running Xian network.

They are lower-level than examples:

- a contract pack owns deployable contract assets and install recipes
- an example composes templates, contract packs, services, app code, and docs into a
  full application or operator workflow

```mermaid
flowchart LR
  ContractPack["Contract pack"] --> Assets["Contract assets"]
  ContractPack --> Recipes["Install recipes"]
  ContractPack --> Manifest["contract-pack.json"]
  CLI["xian-cli contract-pack commands"] --> Manifest
  Manifest --> Network["Running Xian network"]
  Example["Example"] --> ContractPack
  Example --> Templates["Network templates"]
  Example --> Services["Optional services"]
  Example --> AppCode["App code and docs"]
```

Current contract packs:

- `dex/`: canonical Xian AMM contracts
- `stable-protocol/`: governance-owned stable-asset protocol contracts

Use `xian contract-pack list`, `xian contract-pack show <name>`, and
`xian contract-pack validate <name>` from `xian-cli`.
