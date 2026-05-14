# Install

From the monorepo root:

```bash
cd shell
python3 -m pip install -e .
agent-h --version
```

Optional dependencies such as `prompt_toolkit`, `pygments`, and `mkdocs-material` are lazy-loaded. Missing optional packages degrade gracefully.
