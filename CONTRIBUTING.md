# Contributing to agent-h

Thanks for helping close the Claude-Code parity gap.

## Where to work

| Area | Repo |
| --- | --- |
| CLI, REPL, permissions, MCP wiring | `shell/` |
| Skills and seed packs | `atelier/` |
| Cost/budget behavior | `bankroll/` |
| Evaluation and benchmarks | `crucible/` |
| Repo maps and summaries | `cartograph/` |
| Context compaction | `distill/` |
| Determinism/replay | `stepback/`, `rerun/` |
| Docs/blog/config | `agent-h/` |

## Before opening a PR

1. Keep changes surgical and update the relevant `100_STEPS*.md` item.
2. Run that sub-repo's tests (`python3 -m pytest` for Python repos).
3. Do not weaken `shell.permissions.PermissionPolicy` cwd-jail checks.
4. Treat `shell/shell/llm_provider.py` as canonical; propagate structural changes to sibling mirrors or avoid them.

## Issues

File CLI bugs against `shell/`, skill bugs against `atelier/`, docs issues against `agent-h/`, and cross-repo orchestration issues against the monorepo root.
