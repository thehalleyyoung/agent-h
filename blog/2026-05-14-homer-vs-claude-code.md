# Homer is not Claude Code — and that's the point

*An opinionated tour of what `agent-h` does differently, for researchers and practitioners.*

---

Claude Code is great. We use it. This post is not "Claude Code is bad."

It is: **Claude Code is a closed, polished, single-vendor product. Homer is a substrate.** The first one is what you reach for to ship a feature on Tuesday. The second is what you reach for when you want to *study* coding agents, *budget* coding agents, *reproduce* coding agents, or *route around* a coding-agent vendor.

Below: nine concrete things `agent-h` (the CLI, with `homer` as its orchestrator core, sitting on 18 sibling sub-repos) does that Claude Code either doesn't, can't, or actively chooses not to. Then a fair section on what Claude Code does better.

## TL;DR

| Capability | Claude Code | `agent-h` |
| --- | --- | --- |
| Provider lock-in | Anthropic only | 16 OpenAI-compatible providers + litellm passthrough |
| Hard budget cap | Soft warnings | `--max-spend $5` enforced in-loop by `bankroll.Ledger` |
| Cache-hit accounting | Hidden | First-class `ChatResponse.cached`, `prompt_cache_hit_tokens`, `kind=cache_hit` ledger entries |
| Determinism | None advertised | `--seed N` via `stepback` + `rerun`; bit-identical replay |
| Conversation branching | Linear with rewind | Full DAG via `manyworlds`; explore N plans in parallel |
| Pre-flight safety probe | None | `--probe` runs `adversary` against the plan before tools fire |
| Self-improving skills | Manual | `coevo` mutates and benchmarks prompt templates between sessions |
| Reproducibility manifest | None | `groundwork` exports a manifest for every session |
| Source you can read & fork | No | Yes (MIT, 19 sub-repos) |

---

## 1. Multi-provider, not Anthropic-only

Claude Code calls Claude. That's the product.

`agent-h` ships `shell/llm_provider.py` (≈600 lines, dependency-free) that speaks the OpenAI Chat Completions wire format to **16 providers**: openai, openrouter, deepseek, groq, together, fireworks, mistral, perplexity, deepinfra, anyscale, cerebras, xai, nvidia, ollama, vllm, tgi — plus `azure_openai` and a `litellm` passthrough for native Anthropic / Gemini / Bedrock / Vertex.

```bash
agent-h --provider deepseek --model deepseek-chat -p "fix the failing test"
agent-h --provider openrouter --model anthropic/claude-3.5-sonnet -p ...
agent-h --provider ollama --model qwen2.5-coder:14b -p ...   # fully local
```

Per-provider keys (`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, …) are honoured automatically; the unified `AGENT_H_LLM_API_KEY` overrides them. OpenRouter attribution headers (`HTTP-Referer`, `X-Title`) are auto-attached. Provider seed support is tabulated in `stepback.PROVIDER_SEED_SUPPORT` so you know where determinism breaks down.

**Why a researcher cares:** you can run the same agent loop across 16 providers and compare. You can ablate the model without ablating everything else.

**Why a practitioner cares:** when Anthropic rate-limits you, you switch to DeepSeek and keep shipping.

## 2. A hard budget cap that actually fires

Most agents track spend. `agent-h` *enforces* it.

```bash
agent-h --max-spend 5.00 -p "refactor the auth module" --autopilot
```

Under the hood, `bankroll.Ledger` (its own sub-repo) holds `hard_limit`, `soft_limit`, EWMA-predicted next-step cost, and per-charge events. Every LLM and tool call goes through `ledger.charge(estimate)` which raises `BankrollExceeded` the moment `realised + predicted > hard_limit`. The agent winds down gracefully — saves session, prints state — instead of dying with a half-applied refactor.

Cache-hit savings flow into the same ledger as **zero-cost entries tagged `kind=cache_hit`** (a helper we shipped this week: `bankroll.integrations.cache_accounting.charge_cache_hit`). Provider-side prompt-cache hits become `kind=prompt_cache_hit` entries with `tags["hit_savings_usd"]` so a dashboard can sum what you'd otherwise have spent.

That last bit is meaningful: most agents print `cache_hit_tokens` at the end and call it a day. `agent-h` records the **counterfactual cost** in a structured ledger you can query.

## 3. Caches that are visible all the way up

Two layers, both addressable:

```python
from shell.llm_provider import LLMClient
client = LLMClient(cache=True, prompt_cache=True)
resp = client.chat(messages)
print(resp.cached, resp.prompt_cache_hit_tokens)
```

* **`cache=True`** — content-addressed SQLite/WAL response cache. A repeat call with identical `messages + model + temperature + …` returns the prior `ChatResponse` with `.cached=True`. Free, deterministic, no provider hit at all.
* **`prompt_cache=True`** — annotates the request for **provider-side** prefix caching. Anthropic gets `cache_control` blocks. OpenAI/Azure get a stable `prompt_cache_key` derived from the system+leading-user prefix hash. Gemini gets `cached_content`. DeepSeek/OpenRouter get a no-op (their caching is implicit). The response object normalizes the various provider shapes into one `prompt_cache_hit_tokens` accessor.

Claude Code does prompt caching internally. `agent-h` does it across **eight cache layers** (the eight pre-existing per-repo caches in `homer`, `adversary`, `ragdoctor`, `stepback`, `toolforge`, `mnemos` — plus the new `ResponseCache`), and exposes every hit to the ledger and the `/cost` slash command.

## 4. Determinism with `--seed`

```bash
agent-h --seed 42 -p "add a /healthz endpoint"
```

Two pieces:

* `stepback` keeps a curated `PROVIDER_SEED_SUPPORT` table — seed param name, supported temperature ranges, known non-determinism quirks (DeepSeek-R1's `<think>` blocks, OpenAI's `system_fingerprint` drift, Together's `seed` semantics).
* `rerun` records every tool call (args, env, exit code, stdout) into a per-session jsonl trace. `agent-h replay <id>` walks that trace deterministically — same inputs, same outputs, no network.

For research: this turns "agent run" into a **first-class scientific artifact**. You can publish a benchmark and people can re-execute your exact session.

For practice: this is how you write an integration test for an LLM agent at all.

## 5. Branch the conversation tree

Claude Code is linear. You can rewind, but you walk *back* to a single trunk.

`manyworlds` makes the conversation a DAG.

```
agent-h               # session abc123
> /branch fast-path
agent-h fork abc123   # sibling: session def456
agent-h fork abc123   # sibling: session ghi789
```

Now run three different plans against the same starting state in parallel, score each with `crucible`, keep the cheapest one that passes the kiln pipeline. This is the core of `manyworlds`'s "many-worlds planning" — it's a research surface (Mealy-style coevolution of prompt and plan) and a practical surface ("which of these three approaches actually works?").

## 6. Adversarial pre-flight (`--probe`)

```bash
agent-h --probe -p "rewrite the deploy script" --autopilot
```

Before any destructive tool fires, `adversary` synthesizes attack patterns against the *plan* (not the code yet): "what if the file doesn't exist?", "what if the env var is empty?", "what command would this expand to under `set -u`?", "is there a path that exfiltrates `.env`?". The agent only proceeds with `bash`/`edit`/`create` after the probe report is reviewed (interactively) or auto-greenlit (in autopilot).

This is something you'd build *yourself* on top of Claude Code with hooks and prompt engineering. We made it a sub-repo with its own SQLite candidate→trace cache.

## 7. Self-improving skills (`coevo` + `atelier`)

Skills in Claude Code are static prompt templates you author and ship.

In `agent-h`:

1. `atelier` is the skill registry. `/skill save fix-flaky-test` promotes the current prompt+context into a named skill.
2. `coevo` (coevolution of prompts and benchmarks) maintains a population of variants of every skill, mutates them between sessions, and tracks per-variant win rate against `crucible` benchmarks.
3. After N sessions the skill that ships is the one that empirically wins, not the one you wrote on Tuesday.

This is **directly the Mealy-draft research line** in our `comet-h` paper: agents whose policy is itself the output of a search loop, with prompt + benchmark co-evolved.

## 8. A reproducibility manifest in every session

`groundwork` writes, per session:

* exact provider + model + seed + temperature
* full env-var snapshot (sanitized — no keys)
* git SHA + dirty-file list at `session_start`
* every tool invocation with args + exit code (also in `rerun`)
* every cache hit (local + provider) with token savings
* total cost broken out per provider

It's a single jsonl file you can attach to a PR, a paper, a bug report. **Claude Code emits no comparable artifact.** This is a blocker for academic publication.

## 9. The orchestrator is its own readable program

`homer` is the actual decision loop:

* Sub-agent dispatch (the `Task` tool that fans out explore / rubber-duck / code-review subagents in their own context windows — Claude Code calls this "agents", we call them sub-agents and you can read the dispatcher in 400 lines).
* Loop detection (when the agent edits the same file 3+ times in a row with no test progress, `looper` interrupts).
* Long-running supervision (`flowwarden` watches autopilot sessions, kills runaway loops, escalates on cost thresholds).
* RAG and symbol-map context (`ragdoctor` + `cartograph`) injected on demand instead of reflexively.
* Context compaction (`distill` — same idea as Claude Code's "compact", with a published algorithm).

You can fork `homer` and change the loop. We mean that literally — the loop is not behind an API.

---

## Researcher sidebar

If you publish on coding agents and want your work to be reproducible **and** deployable:

* `--seed` + `rerun` + `groundwork` give you bit-identical reruns and a manifest you can ship with the paper.
* `manyworlds` lets you study the policy *distribution* under fixed inputs: branch the same starting state N ways, measure the variance of outcomes.
* `coevo` is a research artifact in its own right: a substrate for **co-evolutionary prompt search** with a benchmark loop (`crucible`) and a skill registry (`atelier`) to land winners.
* `adversary` formalizes red-team probing of plans (not just generated code) — there's a paper to be written here on attack surfaces specific to plan-time agents.
* The 16-provider matrix gives you cheap ablation: same agent loop, swap the model, run the suite. We use this for `comet-h`'s research-tier benchmarks.

## Practitioner sidebar

If you ship code with an agent five days a week:

* `--max-spend 5.00 --autopilot` is the killer feature. Hard cap, in-loop, with graceful wind-down. No more "I left it running overnight and it cost $87."
* The 16-provider escape hatch means a Claude rate-limit doesn't block your release.
* Eight cache layers on by default, `bankroll.cache_accounting` showing you the dollars saved.
* `--probe` before destructive autopilot work. Saves at least one production incident per quarter.
* `agent-h init` writes `.agent-h/permissions.toml` with `bash`/`edit`/`create` on the prompt list — you opt into destructiveness, you don't opt out.
* `cwd_jail` blocks file writes outside the project, even in autopilot.
* `.agent-h/hooks/pre_tool.sh` lets you reject any tool call from your repo (we use this to block edits to `vendor/`).

## Where Claude Code wins (be honest)

* **Polish.** The TUI, the streaming, the diff renderer, the keybinds — Claude Code is years ahead. Our 100_STEPS.md lists the gap explicitly.
* **Skill ecosystem.** Claude Skills has critical mass. `atelier` doesn't — yet.
* **MCP integration is mature on Claude.** We have a registry and a stub transport; real stdio JSON-RPC is on the roadmap.
* **Anthropic's models are very, very good at code.** Routing to them via `--provider openrouter --model anthropic/claude-3.5-sonnet` is honestly the right default for many tasks.
* **First-party support.** When Claude Code breaks, Anthropic fixes it. When `agent-h` breaks, you fix it (or we do, in public, on GitHub).

We are not trying to win at polish. We are trying to give you the substrate to build the agent *you* need, with the **research properties** (determinism, branching, adversarial probing, evolutionary skill search, reproducibility) that closed products structurally cannot offer.

## Get started

```bash
pipx install agent-h-shell
agent-h init                                    # bootstrap .agent-h/
agent-h login                                   # store an API key
agent-h --max-spend 1.00 -p "fix the build" --autopilot
```

Source: <https://github.com/thehalleyyoung/agent-h>. MIT.

If you read one sub-repo first, read `homer/` (the orchestrator) or `bankroll/` (the budget enforcement). If you write one extension first, write a hook in `.agent-h/hooks/pre_tool.sh` that rejects any `bash` containing `rm -rf`. You'll feel the substrate immediately.

---

*`agent-h` is research software. It will move fast and occasionally break. Every breaking change goes through `crucible` benchmarks before it ships, and every release carries a `groundwork` reproducibility manifest. If you'd rather not deal with that — use Claude Code. We do too, sometimes. The point is that **you should have the choice**.*
