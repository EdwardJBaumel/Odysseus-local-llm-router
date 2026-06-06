# Odysseus-local-llm-router — agent guide

Read [README.md](README.md) first.

## Scope

- **This repo:** integration docs, scripts, PR planning.
- **`odysseus/`:** nested clone — all code changes for upstream PRs.
- **`../local-llm-router`** (or legacy `../split-stack`): routing library — release/version bumps happen there, not here.

Do not mix unrelated Odysseus fixes into Auto stack PRs.

## Branches

| Branch | Where | Purpose |
|--------|-------|---------|
| `feature/auto-stack-full` | `odysseus/` | Working integration + screenshots |
| `feature/auto-stack-pr1` … `pr4` | `odysseus/` | Cherry-picked slices for upstream |

## Before opening an upstream PR

1. Fill [Odysseus PR template](odysseus/.github/PULL_REQUEST_TEMPLATE.md) completely.
2. Link **Part of #3073** (or Fixes when the series is done).
3. Target **`dev`**, not `main`.
4. PR4 only: desktop + mobile screenshots from `feature/auto-stack-full`.
5. See [docs/maintainer-gates.md](docs/maintainer-gates.md).

## Local verify

```powershell
cd odysseus
..\scripts\setup-local.ps1
python -m pytest tests/test_*auto_stack* tests/test_split_stack_runtime.py -q
..\scripts\start-local.ps1
```

Anchor endpoint URL must be `http://127.0.0.1:11434/v1` (not bare `:11434`).
