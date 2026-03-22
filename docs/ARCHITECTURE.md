# Architecture

`xian-configs` is the canonical home for committed network assets and shared contract fixtures.

Main areas:

- `contracts/`: canonical contract sources used by the stack
- `networks/`: committed network manifests and related assets
- `legacy/`: older chain assets kept only where still required
- `scripts/`: validation helpers for repo content

Dependency direction:

- is consumed by `xian-cli`, `xian-abci`, `xian-stack`, and deployment workflows
- should stay data-oriented and avoid growing runtime logic

