# Solutions

Solutions are complete application or operator patterns. They compose network
templates, modules, services, examples, and documentation into a usable flow.

```mermaid
flowchart LR
  Solution["Solution manifest"] --> Templates["Network templates"]
  Solution --> Modules["Installable modules"]
  Solution --> Services["Optional services"]
  Solution --> Examples["SDK examples"]
  Solution --> Docs["User-facing docs"]
  CLI["xian-cli solution commands"] --> Solution
  CLI --> Starter["Generated starter flow"]
```

Current solutions:

- `credits-ledger/`
- `registry-approval/`
- `workflow-backend/`
- `dex-demo/`
- `x402-exact/`

Use `xian solution list`, `xian solution show <name>`, and
`xian solution starter <name>` from `xian-cli`.
