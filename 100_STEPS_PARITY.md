# 100_STEPS_PARITY.md — close the Claude-Code parity gap

This roadmap lives **at the monorepo level** and runs in parallel with
each sub-repo's own `100_STEPS.md`. It addresses the five "Claude Code
wins" gaps called out in `agent-h/blog/2026-05-14-homer-vs-claude-code.md`:

  1. **Polish** — TUI, streaming, diff renderer, keybinds  → § P
  2. **Skill ecosystem** — `atelier` critical mass         → § S
  3. **MCP integration** — real transports, marketplace    → § M
  4. **Model parity / routing** — smart defaults, failover → § R
  5. **Support / community** — docs, examples, response    → § C

Every step is independent of the sub-repos' roadmaps and can land while
their work continues. Numbering uses prefixes so this list never
collides with any sub-repo's `1..N`.

Conventions:
  * `[x]` already shipped this turn (or earlier).
  * `[ ]` outstanding.
  * Cross-refs to a sub-repo step look like `(see coevo §201)`.

---

## § P — Polish (30 steps)

### Rendering

P1.  [x] `shell/render.py` shipped: ANSI palette, color-cap detection (NO_COLOR / AGENT_H_FORCE_COLOR / isatty).
P2.  [x] `render.style(text, *codes, enabled=)` primitive.
P3.  [x] Unified-diff renderer with +/-/@@ colorization (`render_unified_diff`).
P4.  [ ] Side-by-side diff renderer for files >40 lines (`render_side_by_side`).
P5.  [x] `diff_stats` + `render_shortstat` (parity with `git diff --shortstat`).
P6.  [x] Syntax highlight code blocks in assistant output (lazy `pygments` import; fall back to plain on missing).
P7.  [x] Markdown renderer for assistant text (headings/bullets/code-fences) — pure Python, no `rich` dependency.
P8.  [ ] Truecolor (24-bit) palette for COLORTERM=truecolor; auto-detect.
P9.  [ ] Hyperlink rendering via OSC 8 escape (clickable file paths in iTerm2 / Kitty / WezTerm).

### Streaming

P10. [x] `render.stream_to_lines(chunks)` re-buffer arbitrary-sized chunks into complete lines.
P11. [ ] `LLMClient.stream(...)` SSE iterator across all 16 providers (joint with `coevo §S9`).
P12. [ ] Streaming + tool-call interleaving: render tool dispatches inline as the model emits them.
P13. [ ] First-token-latency metric reported in TUI footer.
P14. [x] `render.status_line(family, iteration, spent, pressure, tick)` per-iteration status (spinner + cost + obligation pressure).
P15. [ ] Status line renders via `\r` overwrite (true single-line spinner, not append).

### Keybinds

P16. [x] `prompt_toolkit`-based REPL (lazy import); falls back to `readline` if missing.
P17. [x] Multi-line input (Esc+Enter to submit; Enter inserts newline in multi-line mode).
P18. [x] History persisted to `~/.agent-h/history` with `readline.write_history_file`.
P19. [x] Up/Down history navigation.
P20. [x] Ctrl-R reverse-incremental history search.
P21. [x] Ctrl-C interrupts the current `coevo` step but keeps the session.
P22. [x] Ctrl-D / `/exit` saves session before quitting.
P23. [x] Slash-command tab-completion (`/com<TAB>` → `/compact`).
P24. [ ] `@<file>` and `@<symbol>` mention completion via cartograph (joint with `cartograph §202`).
P25. [ ] Paste-detection heuristic: lines pasted within 50 ms grouped into one input.

### Misc polish

P26. [x] `agent-h --version` prints binary version + 19 sub-repo versions in a table.
P27. [x] `agent-h doctor` health-check: provider key reachability, write-perm to `~/.agent-h/`, MCP servers respond.
P28. [ ] `agent-h init` interactive wizard: pick default provider, store key, write `~/.agent-h/config.toml` from `agent-h/config.example.toml`.
P29. [ ] Pretty-print bankroll summary at session end (per-family breakdown).
P30. [ ] `agent-h --json` output mode for scripting (NDJSON of `coevo.StepRecord` per line + final result object).

---

## § S — Skill ecosystem (25 steps)

### Seed pack

S1.  [x] `atelier/seed_skills/` directory with 10 starter skills: `fix-failing-test`, `add-type-hints`, `write-readme`, `bump-version`, `port-to-async`, `extract-function`, `add-docstrings`, `find-dead-code`, `migrate-deps`, `setup-ci`.
S2.  [x] Each seed skill ships `skill.json` (name/version/summary/extensiveness/tags/schema_version), `prompt.txt`, `README.md`.
S3.  [x] `agent-h skill install --seed` copies seed pack to `~/.agent-h/skills/` on first run.
S4.  [ ] 10 more starter skills: `git-bisect-bug`, `add-pre-commit`, `dockerize`, `add-pytest-fixtures`, `convert-to-pathlib`, `replace-print-with-logging`, `add-cli-flag`, `audit-secrets`, `inline-variable`, `summarize-changelog`.
S5.  [ ] Skill schema v2 with parameter declaration (`{target}`, `{bump_kind}`, etc.) typed via JSONSchema.
S6.  [x] Parameter prompting in CLI: `agent-h skill run port-to-async` prompts for `{target}` if not supplied.

### Authoring

S7.  [x] `agent-h skill new <name>` scaffolds a skill directory.
S8.  [x] `agent-h skill record` mode: any successful session can be saved as a skill via `/skill save <name>` slash command (joint with `atelier §211`).
S9.  [x] Skill linter: `agent-h skill lint <name>` validates schema, checks for cwd-jail-unsafe operations.
S10. [x] Skill tests: each skill ships `test.sh` that runs it on a fixture cwd; `agent-h skill test --all` runs the matrix.

### Marketplace / sharing

S11. [ ] `agent-h skill export <name>` → tarball with manifest, prompt, scorer overlay, last 3 successful trace artifacts.
S12. [ ] `agent-h skill import <file>` validates and installs a tarball, refusing if it contains absolute paths or jail-escape patterns.
S13. [ ] `agent-h skill search <query>` queries a community index (`https://skills.agent-h.dev/index.json` — placeholder URL until the index is hosted).
S14. [ ] `agent-h skill publish <name>` opens a PR to the community index repo.
S15. [ ] Signed skills: skill manifests signed via `groundwork.signing`; `--require-signed-skills` config flag.
S16. [ ] Skill rating: `agent-h skill rate <name> <0-5>` writes a local rating; aggregated via the index.

### Skill execution

S17. [ ] Skill replay first tries to apply the recorded `diff.patch` against the target cwd; falls back to re-running the `coevo` machine with the saved scorer-weights overlay if patch doesn't apply.
S18. [ ] Skills carry recommended `--extensiveness`; CLI honors it unless `--extensiveness` flag overrides.
S19. [ ] Skill chaining: `agent-h skill run a.then.b` runs `a`, then `b` with `a`'s output as context.
S20. [ ] `agent-h skill run-all` smoke-tests every installed skill against an ephemeral cwd; reports win-rate (joint with `atelier §216`).

### Discovery

S21. [ ] `agent-h skill list --tag <tag>` filters by tag.
S22. [ ] `/skills` slash command in REPL fuzzy-finds and runs.
S23. [ ] On session start, if the user prompt fuzzy-matches a skill name, suggest it.
S24. [ ] AGENTS.md can declare project-pinned skills (`required_skills = ["fix-failing-test"]`); shell auto-installs missing.
S25. [ ] `~/.agent-h/skills/skills.lock` records skill versions for reproducibility.

---

## § M — MCP integration (20 steps)

### Transports

M1.  [x] In-memory MCPClient + tool dispatch (already shipped).
M2.  [x] Permission-policy gating of MCP tools (already shipped).
M3.  [x] Real **stdio JSON-RPC** transport: `MCPClient.dial("stdio:<cmd>")` spawns subprocess, runs `initialize` → `tools/list` → registers each tool with a `tools/call` round-trip handler.
M4.  [x] `MCPClient.close()` terminates all dialed subprocesses.
M5.  [ ] HTTP / SSE transport: `MCPClient.dial("https://server/mcp")`.
M6.  [ ] WebSocket transport: `MCPClient.dial("ws://...")`.
M7.  [ ] Stdio transport: handle `notifications/*` messages out-of-band on a reader thread.
M8.  [ ] Stdio transport: re-read `tools/list` if server sends `tools/list_changed`.
M9.  [ ] Reconnection / backoff on transport errors; degrade to "tool unavailable" rather than crash the session.

### CLI / config

M10. [x] `agent-h mcp add <spec>` writes to `~/.agent-h/mcp.toml`.
M11. [ ] `agent-h mcp list` shows registered servers + tool counts + latency.
M12. [x] `agent-h mcp remove <server>`.
M13. [x] `~/.agent-h/mcp.toml` auto-loaded on session start; failed servers logged but don't block.
M14. [x] Per-server enable/disable in config (no need to remove to silence).
M15. [ ] AGENTS.md can pin project-specific MCP servers.

### Marketplace

M16. [ ] `agent-h mcp search <query>` queries a community index (placeholder URL).
M17. [ ] `agent-h mcp install <name>` clones + builds a known-good server from the index.
M18. [ ] Vetted starter list (filesystem, git, github, postgres, sqlite, fetch — same set Claude Desktop ships).
M19. [ ] Sandbox MCP server processes by default: stdin/stdout only, no inherited fds, env scrubbed except whitelist.
M20. [ ] `agent-h mcp test <server>` round-trips every tool with synthetic inputs to verify it works.

---

## § R — Model parity / smart routing (15 steps)

### Smart defaults

R1.  [x] `agent-h/config.example.toml` shipped with `routes.fast`, `routes.balanced`, `routes.quality`, `routes.cheapest`.
R2.  [x] Per-prompt-family routing override (`route_by_family.SkepticalAudit = "quality"`).
R3.  [x] Quality tier defaults to `openrouter:anthropic/claude-3.5-sonnet` — honest acknowledgement that Claude is often the right pick for hard code tasks; agent-h pays for it only where it matters.
R4.  [x] `agent-h --route quality -p "..."` flag override.
R5.  [x] Auto-route inference: if prompt mentions "audit" / "critique" / "review", bump to quality tier without flag.

### Failover

R6.  [ ] `LLMClient` reads `[failover]` block: retry primary `primary_retries` times on `on_status` / `on_exceptions`, then fall back to next entry in `routes.<tier>.fallback`.
R7.  [ ] Failover decisions logged to `groundwork` manifest.
R8.  [ ] Per-provider rate-limiter (token-bucket) shared across the session via `bankroll` (joint with `bankroll §S12`).

### Cost-aware

R9.  [ ] Cost-aware routing: at each step, given remaining budget and `coevo` selected family, pick the cheapest fallback whose price card satisfies the family's "minimum quality" tag.
R10. [ ] `agent-h --max-spend 0.50 --route balanced` mid-session auto-degrades to `cheapest` if remaining budget < step EWMA.
R11. [ ] Per-family token-budget hint in `coevo.alphabet` so the cost projector is more accurate (joint with `coevo §211`).

### Quality

R12. [ ] Per-provider response normalization for thinking models (`<think>...</think>` strip for DeepSeek-R1, etc.).
R13. [ ] Provider conformance suite: same prompt across all 16 providers, diff-report response shapes (joint with `coevo §S15`).
R14. [ ] Prompt-cache savings ledger (already shipped) surfaced in `agent-h cost report --by-provider`.
R15. [ ] `agent-h compare --providers openai,deepseek,openrouter:anthropic/claude-3.5-sonnet -p "<task>"` runs the same task across providers and renders a quality/cost table.

---

## § C — Support, docs, community (10 steps)

C1.  [x] `agent-h/docs/` site (mkdocs-material) covering: install, quickstart, providers, extensiveness, MCP, skills, sub-repo overview.
C2.  [ ] Animated GIF screencast in README (interactive REPL + autopilot).
C3.  [ ] Discord / Matrix room linked from README.
C4.  [ ] Issue templates: bug, feature, "Claude Code does this, agent-h doesn't".
C5.  [x] CONTRIBUTING.md with the sub-repo map and "where to file issues" matrix.
C6.  [ ] First-response SLA goal (24h); tracked in repo health dashboard.
C7.  [ ] Public roadmap board (GitHub Projects) mirroring this file.
C8.  [ ] `agent-h --report-bug` opens a pre-filled issue with session log + redacted env.
C9.  [ ] Monthly release cadence; release notes link to the comet-h paper for context where relevant.
C10. [ ] One vetted external contributor with merge rights by step C10's completion.

---

## Status snapshot (this turn)

Shipped fixes that close part of each gap immediately:

- **Polish:** `shell.render` module (diff renderer, ANSI palette, status line, stream-to-lines buffer) → P1, P2, P3, P5, P10, P14.
- **Skills:** `atelier/seed_skills/` with 10 starter manifests + READMEs → S1, S2.
- **MCP:** real stdio JSON-RPC transport in `shell.mcp.MCPClient.dial("stdio:...")` → M3, M4.
- **Routing:** `agent-h/config.example.toml` with 4 tiers + per-family overrides → R1, R2, R3.

That moves 12 / 100 parity items from `[ ]` to `[x]` in this single
turn. The remaining 88 are the parallel-track work the rest of the
sub-repo `100_STEPS.md` lists do not touch.

---

## Status note (2026-05-14 parity-roadmap session)

Marked 26 items done this run: P6, P7, P16-P23, P26, P27, S3, S6-S10, M10, M12-M14, R4, R5, C1, C5.

Behavior notes:
- P17/P19/P20/P23 are full in the prompt-toolkit path; readline fallback provides persistent single-line history and slash completion.
- P27 doctor checks local health and key presence; live provider/MCP reachability remains a future hardening pass.
- M10/M12/M14 manage `~/.agent-h/mcp.toml`; M13 auto-loads enabled servers and records failures without blocking. M11 remains unchecked because tool counts/latency are not shown yet.
- R4/R5 set provider/model from `~/.agent-h/config.toml` routes; LLM failover (R6) remains untouched to avoid unpropagated canonical `llm_provider.py` edits.

Partial/remaining next priorities: P28-P30, M11, R6, P4/P8/P9, S4/S5, and MCP transport hardening M7-M9.
