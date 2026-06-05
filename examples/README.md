# Examples

Examples are complete application or operator patterns. They compose network
templates, contract packs, services, app code, and documentation into a usable flow.

```mermaid
flowchart LR
  Example["Example manifest"] --> Templates["Network templates"]
  Example --> ContractPacks["Installable contract packs"]
  Example --> Services["Optional services"]
  Example --> AppCode["SDK app code"]
  Example --> Docs["User-facing docs"]
  CLI["xian-cli example commands"] --> Example
  CLI --> Starter["Generated starter flow"]
```

Current examples:

- `credits-ledger/`
- `registry-approval/`
- `workflow-backend/`
- `dex-demo/`
- `nft-marketplace/`
- `x402-exact/`

Use `xian example list`, `xian example show <name>`, and
`xian example starter <name>` from `xian-cli`.
