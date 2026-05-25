# Stable Protocol Contract Pack

This contract pack contains the pinned stable-protocol contract assets. Active
development and deployment bootstrap scripts live in `xian-stable-protocol`.

The contract pack exists so tooling can discover and validate the protocol
contract set separately from example starter flows.

```mermaid
flowchart LR
  StableRepo["xian-stable-protocol"] --> Assets["Pinned contract assets"]
  Assets --> ContractPack["stable-protocol contract pack"]
  ContractPack --> CLI["xian-cli contract-pack validate or install"]
  CLI --> Bootstrap["Delegated bootstrap command"]
  Bootstrap --> Network["Target Xian network"]
```

Use `xian contract-pack validate stable-protocol` to validate the pinned bundle.

Use `xian contract-pack install stable-protocol --dry-run` to resolve the delegated
bootstrap command in `xian-stable-protocol`. For a real install, prepare the
owning repo's bootstrap environment variables and rerun without `--dry-run`.
