# PR plan — work backwards from `feature/auto-stack-full`

## Integration branch (this project)

All phases live on `odysseus/feature/auto-stack-full` until split.

**Prove here first:** chat routing, agent `model_resolved`, settings toggle, picker Auto stack row, screenshots.

## Upstream slices (to `pewdiepie-archdaemon/odysseus` `dev`)

| PR | Files (approx) | Screenshots? | Merge gate |
|----|----------------|--------------|------------|
| **PR1** | `split_stack_runtime`, `auto_stack_router`, `constants`, `settings`, `requirements-optional`, tests, ACKNOWLEDGMENTS | No | Zero behavior change |
| **PR2** | `chat_helpers`, `chat_routes`, `tool_implementations` aliases | No | Docker manual + SSE log paste |
| **PR3** | `agent_model_mode`, `agent_loop` | No | Multi-round agent test notes |
| **PR4** | `index.html`, `settings.js`, `modelPicker.js` | **Required** | From full branch demo |

Create each slice:

```powershell
cd odysseus
git checkout dev
git checkout -b feature/auto-stack-pr1
# cherry-pick or copy only PR1 files from feature/auto-stack-full
```

## Order to **open** upstream

PR1 → wait for review → PR2 → PR3 → PR4 last (screenshots).

## Order we **build/test** locally

PR1+2+3+4 together on `feature/auto-stack-full`, then split backwards for upload.
