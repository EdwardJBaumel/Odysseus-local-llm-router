# Maintainer accept / deny patterns (Odysseus)

From [CONTRIBUTING.md](https://github.com/pewdiepie-archdaemon/odysseus/blob/main/CONTRIBUTING.md) and recent closed PRs.

## Will close without review

- Agent/bulk PR **without an issue** (#3073 covers us if we link it).
- **UI changes without screenshots** (desktop + mobile).
- **Unfilled PR template** (summary, test steps, checkboxes).

## Will close after skim

- **>500 lines / new deps / vendored libs** without prior issue alignment (#3073 first).
- **Multi-concern bundles** (router + UI + agent in one PR).
- **Visual style violations** (emoji, new colors, parallel widgets).
- **Duplicate** of already-merged fix on `dev`.

## Gets merged

- **Small**, issue-linked, one concern per PR.
- **Filled template** + pytest output + **manual Docker steps**.
- **Backwards compat** table when settings change.
- **Matches patterns** (markitdown optional dep, teacher settings UI, etc.).
- **Follow-up PRs** that address review comments (#1273 style).

## Per our series

| PR | Risk | Mitigation |
|----|------|------------|
| PR1 | Low | Explicit “no runtime hooks” |
| PR2 | Medium | Stack-only fallbacks; excluded modes listed |
| PR3 | High | Minimal `agent_loop` diff; reuse tool-support tests |
| PR4 | Visual gate | Screenshots from full branch only; copy Teacher card |

Wait for maintainer answers on #3073 Q1–Q3 before PR2 if possible.
