# Extensiveness

`--extensiveness` controls how much effort agent-h spends on a task.

- `1`: small, single-pass patch
- `5`: normal coding loop with tests
- `10`: research-grade run with branching and scoring
- `ask`: prompt interactively
- `cheapest`: choose the highest level under `--max-spend`
