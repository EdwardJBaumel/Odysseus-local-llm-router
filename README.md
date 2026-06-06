# Odysseus-Split-Stack

Integration workspace for optional **Auto stack** mode in [Odysseus](https://github.com/pewdiepie-archdaemon/odysseus), powered by the sibling [split-stack](../split-stack) library.

This repo is **not** a fork of either upstream project. It holds workflow docs, local dev scripts, and a nested Odysseus clone where feature work and upstream PRs are prepared.

## Three-repo layout

| Repo | Path | Role |
|------|------|------|
| **split-stack** | `../split-stack` | MIT routing library (PyPI / local wheel) |
| **odysseus** (upstream) | `../odysseus` | Clean tracking clone of `pewdiepie-archdaemon/odysseus` `dev` |
| **Odysseus-Split-Stack** | this repo | Integration hub + `odysseus/` working fork |

Design discussion: [Odysseus #3073](https://github.com/pewdiepie-archdaemon/odysseus/issues/3073).

## Quick start (local integration)

```powershell
cd C:\Users\zonka\dev\projects\Odysseus-Split-Stack

# 1. Clone Odysseus if odysseus/ is missing
git clone --branch dev https://github.com/pewdiepie-archdaemon/odysseus.git odysseus
cd odysseus
git checkout -b feature/auto-stack-full
# (apply patches or merge from this project's tracked branch)

# 2. Bootstrap app
..\scripts\setup-local.ps1

# 3. Run
..\scripts\start-local.ps1
# → http://127.0.0.1:7000  (admin / odysseus-dev-local)
```

Requires **Ollama** on `http://127.0.0.1:11434` with 2+ models. Use `scripts/seed-ollama-endpoint.py` after first boot if the model picker is empty.

## PR strategy (backwards from working integration)

1. **`feature/auto-stack-full`** — everything works here (screenshots, manual tests).
2. Split **upstream PRs to `dev`** in reverse order of dependency:
   - **PR4** — UI (`modelPicker`, settings) + screenshots
   - **PR3** — agent per-round routing + `model_resolved` SSE
   - **PR2** — chat hooks + privilege/normalize skips
   - **PR1** — router module, settings keys, optional dep, tests only (no runtime hooks)

See [docs/PR-PLAN.md](docs/PR-PLAN.md) and [docs/MAINTAINER-GATES.md](docs/MAINTAINER-GATES.md).

## Fork remote (when ready)

Point the nested clone at your fork for PRs:

```powershell
cd odysseus
git remote add fork https://github.com/EdwardJBaumel/odysseus.git
git push -u fork feature/auto-stack-full
```

Upstream PRs still target `pewdiepie-archdaemon/odysseus` **`dev`**, linked to #3073.
