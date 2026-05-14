# Skills

Skills are reusable prompt workflows installed under `~/.agent-h/skills/`.

```bash
agent-h skill install --seed
agent-h skill list
agent-h skill new my-skill
agent-h skill lint my-skill
agent-h skill run my-skill target=src/app.py
agent-h skill test --all
```

Inside the REPL, `/skill save <name>` scaffolds a saved workflow.
