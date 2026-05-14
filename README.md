# agent-h

> A reference stack for building, running, debugging, and **conducting research
> with** production LLM agents. Twelve independent open-source projects, each
> owning one concern, designed so they can be composed end-to-end on a single
> agent run.

This repository is the **meta-repo**: it doesn't ship code itself. It points
at the component projects, explains how they fit together, and shows
how to use them in combination.

---

## Components

The stack is organised in two tiers. The **production tier** is what you
need to run, observe, and audit a deployed agent. The **research-software
tier** adds the controller and evidence substrate needed to drive
*research* repositories — codebases where the thesis itself is under
construction and theory, code, claims, and evidence must co-evolve.

### Production tier

| Component | Concern | Repository |
|---|---|---|
| 🩺 **ragdoctor** | quality — diagnose RAG/agent regressions and prescribe fixes | <https://github.com/thehalleyyoung/ragdoctor> |
| 🐛 **stepback** | debugging — record, replay, and counterfactually re-execute an agent run | <https://github.com/thehalleyyoung/stepback> |
| 🛡️ **flowwarden** | security/audit — taint-track data across tool/LLM calls and emit signed attestations | <https://github.com/thehalleyyoung/flowwarden> |
| 🔁 **looper** | durable agent control loop primitive (idempotent, resumable, exactly-once side effects) | <https://github.com/thehalleyyoung/looper> |
| 🧠 **mnemos** | content-addressed agent memory store with time-travel and labels | <https://github.com/thehalleyyoung/mnemos> |
| 💸 **bankroll** | per-step token / dollar accounting and budget enforcement | <https://github.com/thehalleyyoung/bankroll> |
| 🔧 **toolforge** | typed tool-contract layer for LLM toolchains | <https://github.com/thehalleyyoung/toolforge> |
| ⚔️ **adversary** | adversarial-input synthesis for LLM agents | <https://github.com/thehalleyyoung/adversary> |
| 🧪 **rerun** | CI regression harness for agent traces | <https://github.com/thehalleyyoung/rerun> |
| 🤖 **homer** | conversational AI agent framework wiring all the above into a single Agent | <https://github.com/thehalleyyoung/homer> |
| 🗺️ **cartograph** | repo-scale code intelligence — symbol/call/type graph + ranked context selection for large coding tasks | <https://github.com/thehalleyyoung/cartograph> |
| 🌌 **manyworlds** | speculative parallel agent search — fork into N branches, prune by signal stack, collapse to the winner | <https://github.com/thehalleyyoung/manyworlds> |
| 💧 **distill** | hierarchical context compaction — decision-preserving loss bounds, retrieval-aware policies, streaming compaction | <https://github.com/thehalleyyoung/distill> |
| 🎨 **atelier** | skills + sub-agent delegation + slash commands + hooks — the agent-extensibility framework | <https://github.com/thehalleyyoung/atelier> |
| 🔥 **kiln** | capability-based sandboxed execution — deny-by-default, pluggable backends, signed attestations | <https://github.com/thehalleyyoung/kiln> |
| ⚗️ **crucible** | agent eval & regression harness — paired bootstrap, MDE, mutation-based suite synthesis, CI gating | <https://github.com/thehalleyyoung/crucible> |

### Research-software tier (Comet-H)

| Component | Concern | Repository |
|---|---|---|
| 🧭 **coevo** | co-evolution state-machine controller — workspace `W=(T,R,P,E,U,Q)`, decaying obligations, reactive grounding trigger, adjacency constraints | <https://github.com/thehalleyyoung/coevo> |
| 📑 **groundwork** | typed signed grounding ledger binding public claims to runnable evidence | <https://github.com/thehalleyyoung/groundwork> |

All components are Apache-2.0, Python-first (Rust core layers in progress
for some), and intentionally **decoupled**: you can adopt any one in
isolation, or any subset. They share design DNA (canonical encoding,
signed append-only artifacts, duck-typed adapters) which makes
composition natural.

---

## Why two tiers, not one

Production agent platforms answer a different set of operational
questions than research-software workflows.

**Production tier** answers:
1. *"Are my answers good?"* → `ragdoctor`
2. *"Why did step 17 do that, and what would have happened if step 12
   had returned X instead?"* → `stepback`
3. *"Did sensitive data leak from tool A to tool B?"* → `flowwarden`
4. *"How do I keep an agent run going through transient failures?"* → `looper`
5. *"What did this agent know at turn N, and how do I share that across
   sessions?"* → `mnemos`
6. *"Am I about to spend $40 on a single chat?"* → `bankroll`
7. *"Is this tool actually safe to expose to the LLM?"* → `toolforge`
8. *"Will this agent break under adversarial input?"* → `adversary`
9. *"Did my last commit regress trace quality?"* → `rerun`
10. *"How do I assemble all of the above into one Agent I can talk to?"* → `homer`

**Research-software tier** answers two further questions whose data
structures are fundamentally different:

11. *"What should the agent do **next** to keep my paper, code, theory, and
    benchmarks consistent with each other?"* → `coevo`
12. *"Which empirical claim in this paper is actually supported by a
    runnable command, and which is a hallucination that drifted in?"* → `groundwork`

Together the research tier prevents the two LM-specific failure modes
identified by Comet-H: **hallucination accumulation** (claims exceed
what code or theory supports, then propagate) and **desynchronization**
(theory, code, claims, and the LM's world model fall out of alignment).

---

## How the components compose at runtime

The intended layering, from the agent loop outward (production stack only;
research mode adds `coevo` as the planner and `groundwork` as a peer of
the recorder):

```
┌──────────────────────────────────────────────────────────────────────┐
│  Your agent code (LangChain / LlamaIndex / CrewAI / MCP / bare      │
│  OpenAI tool calls / your own loop / homer.Agent / coevo machine)   │
│                                                                      │
│   ┌────────────────── flowwarden.install(policy) ──────────────────┐ │
│   │   @flowwarden.tool(returns=PII)                                │ │
│   │   def lookup_customer(...): ...                                │ │
│   │                                                                │ │
│   │     ┌─────────── stepback.record("run.sb") ──────────────┐    │ │
│   │     │   rec.tool_call("lookup_customer", {...})           │    │ │
│   │     │   rec.llm_call("gpt-4o-mini", [...])                │    │ │
│   │     │                                                     │    │ │
│   │     │     ┌── pipeline = ragdoctor.RagPipeline.from(...) │    │ │
│   │     │     │   answer = pipeline.answer(query)            │    │ │
│   │     │     └────────────────────────────────────────────  │    │ │
│   │     └──────────────────────────────────────────────────  │    │ │
│   │                                                                │ │
│   └─ FlowViolation? signed attestation? provenance graph emitted ─┘ │
└──────────────────────────────────────────────────────────────────────┘
```

For the integrated example, see `examples/integrated_demo.py`.

---

## When to reach for which

| Situation | Reach for |
|---|---|
| Answer quality dropped after a deploy | `ragdoctor audit` |
| You want to know if a different model/prompt would have helped on yesterday's run | `stepback replay` |
| Bisect which step in a 30-step run introduced a cost spike or wrong answer | `stepback bisect` |
| Compliance asks "prove this PII never reached the email tool" | `flowwarden attest` |
| Your CI needs a security check on each PR for new agent code | `flowwarden static --sarif` |
| Adversarial / OWASP-LLM-Top-10 coverage of your agent | `adversary` + `ragdoctor red-team` |
| You want a durable, resumable control loop primitive | `looper` |
| You need cross-session memory for an agent | `mnemos` |
| You're spending too much per chat | `bankroll` |
| You're exposing a new tool to an LLM and want type safety | `toolforge` |
| You want a CI regression harness over agent traces | `rerun` |
| You want a chat / serve / eval Agent that wires it all up | `homer` |
| You're driving a *research* repo where theory, code, paper, and benchmarks must mature together | `coevo` + `groundwork` (via `homer research`) |
| Your paper claims a number; you want to bind it to a runnable command | `groundwork record` |
| You want to know which claims in your paper are unsupported | `groundwork audit` |

---

## Quick install

The components aren't on PyPI yet. Install each from its GitHub repo:

```bash
# Production tier
pip install "git+https://github.com/thehalleyyoung/ragdoctor.git"
pip install "git+https://github.com/thehalleyyoung/stepback.git"
pip install "git+https://github.com/thehalleyyoung/flowwarden.git"
pip install "git+https://github.com/thehalleyyoung/looper.git"
pip install "git+https://github.com/thehalleyyoung/mnemos.git"
pip install "git+https://github.com/thehalleyyoung/bankroll.git"
pip install "git+https://github.com/thehalleyyoung/toolforge.git"
pip install "git+https://github.com/thehalleyyoung/adversary.git"
pip install "git+https://github.com/thehalleyyoung/rerun.git"
pip install "git+https://github.com/thehalleyyoung/homer.git"

# Research-software tier (Comet-H)
pip install "git+https://github.com/thehalleyyoung/coevo.git"
pip install "git+https://github.com/thehalleyyoung/groundwork.git"
```

The `Makefile` in this repo has `make clone`, `make install`, `make test`,
and `make demo` targets that automate the clone-and-editable-install flow
for all twelve components.

---

## Documentation in this repo

- [`README.md`](README.md) — this file.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — shared design choices
  (canonical encoding, signed append-only artifacts, content-addressed
  storage, duck-typed adapters) and how the component schemas
  interoperate.
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md) — concrete cookbook:
  every place where two components hand data to each other, with code
  snippets and pitfalls.
- [`docs/RESEARCH_TIER.md`](docs/RESEARCH_TIER.md) — how `coevo` and
  `groundwork` turn the production stack into a Comet-H research-software
  orchestrator.
- [`examples/integrated_demo.py`](examples/integrated_demo.py) — a
  ~80-line runnable example using the production tier on one fake agent run.

---

## Status of each component

- **stepback** — alpha. Python recorder/replay/minimization stack is
  the reference implementation with broad in-repo test coverage; Rust
  core, WASM verifier, and language bindings exist as parallel work.
- **ragdoctor** — usable today as a local diagnostic + repair toolkit.
  Stable 8-axis audit, 4 preview axes, prescription/repair, framework
  adapters, conformance tests, local HTTP server. No hosted service.
- **flowwarden** — Python package is the public surface (labels, tool
  annotations, static analysis, runtime `AgentRun`, marker sidechannel,
  `.fw` policy, provenance graph, attestations, adapters, CLI). Rust
  workspace and proxy are partial.
- **looper, mnemos, bankroll, toolforge, adversary, rerun, homer** — alpha,
  initial public release.
- **coevo, groundwork** — alpha, initial public release. Reference
  implementations of the Comet-H controller and evidence surface from
  *"Theory Under Construction: Orchestrating Language Models for Research
  Software Where the Specification Evolves"* (Young & Bjørner).

---

## License

Each component is Apache-2.0. This meta-repo is also Apache-2.0. See
each component's `LICENSE` file for the canonical text.
