# agent-h

> A reference stack for building, running, and diagnosing production LLM
> agents. Three independent open-source projects, each owning one concern,
> designed so they can be composed end-to-end on a single agent run.

This repository is the **meta-repo**: it doesn't ship code itself. It points
at the three component projects, explains how they fit together, and shows
how to use them in combination.

| Component | Concern | Repository |
|---|---|---|
| 🩺 **ragdoctor** | quality — diagnose RAG/agent regressions and prescribe fixes | <https://github.com/thehalleyyoung/ragdoctor> |
| 🐛 **stepback** | debugging — record, replay, and counterfactually re-execute an agent run | <https://github.com/thehalleyyoung/stepback> |
| 🛡️ **flowwarden** | security/audit — taint-track data across tool/LLM calls and emit signed attestations | <https://github.com/thehalleyyoung/flowwarden> |

All three are Apache-2.0, Python-first (Rust core layers in progress for
some), and intentionally **decoupled**: you can adopt any one in isolation,
or any subset. They share design DNA (canonical encoding, signed
append-only artifacts, duck-typed adapters) which makes composition
natural.

---

## Why three tools, not one

Production agent platforms have to answer three different operational
questions, and the right data structures for each are different:

1. **"Are my answers good?"** — needs a probe-and-prescribe loop over
   the RAG/agent pipeline. → `ragdoctor`.
2. **"Why did step 17 do that, and what would have happened if step 12
   had returned X instead?"** — needs a recorded, replayable trace with
   counterfactual re-execution. → `stepback`.
3. **"Did sensitive data leak from tool A to tool B (after an LLM
   paraphrased it)?"** — needs cross-tool information-flow control with
   semantic taint propagation and signed attestations. → `flowwarden`.

Trying to put all three behind one API forces you to either (a) overload
one tool's primitives until they're confused, or (b) build a god-object
SDK. The agent-h split keeps each tool's surface focused and lets each
evolve at its own pace.

---

## How the three compose at runtime

The intended layering, from the agent loop outward:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Your agent code (LangChain / LlamaIndex / CrewAI / MCP / bare      │
│  OpenAI tool calls / your own loop)                                  │
│                                                                      │
│   ┌────────────────── flowwarden.install(policy) ──────────────────┐ │
│   │   @flowwarden.tool(returns=PII)                                │ │
│   │   def lookup_customer(...): ...                                │ │
│   │                                                                │ │
│   │     ┌──────────── stepback.record("run.sb") ──────────────┐    │ │
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

The order matters:

- **flowwarden is the outermost layer** because it intercepts tool
  invocations before they execute and may *block* them based on policy.
  Its `AgentRun` context manager wraps the entire run.
- **stepback is the recorder** sitting between flowwarden and the real
  executor. It sees every tool/LLM call that flowwarden allows through,
  hashes the canonical inputs, and writes a signed `.sb` frame.
- **ragdoctor** typically runs **offline** against the same pipeline
  configuration — it's the diagnostic suite you reach for when quality
  metrics regress, *not* an inline interceptor on every request.

For a one-process worked example, see `examples/integrated_demo.py`
in this repo.

---

## When to reach for which

| Situation | Reach for |
|---|---|
| Answer quality dropped after a deploy | `ragdoctor audit` to localize the failing axis, then `ragdoctor prescribe` |
| You want to know if a different model/prompt would have helped on yesterday's run | `stepback replay` with `model@step:N=...` substitution |
| Bisect which step in a 30-step run introduced a cost spike or wrong answer | `stepback bisect --predicate '...'` |
| Compliance team asks "prove this PII never reached the email tool" | `flowwarden attest run.jsonl` and hand them the signed CycloneDX-AI BOM |
| Your CI needs a security check on each PR for new agent code | `flowwarden static --sarif` (uploaded to GitHub Security tab) |
| You want adversarial / OWASP-LLM-Top-10 coverage of your agent | `ragdoctor red-team` |
| You want to ship a fix as a PR | `ragdoctor fix --as-pr pipeline.yml --pr-format diff` |

---

## Quick install

The components aren't on PyPI yet. Install each from its GitHub repo:

```bash
pip install "git+https://github.com/thehalleyyoung/ragdoctor.git"
pip install "git+https://github.com/thehalleyyoung/stepback.git"
pip install "git+https://github.com/thehalleyyoung/flowwarden.git"
```

…or clone for development:

```bash
git clone https://github.com/thehalleyyoung/ragdoctor && pip install -e ./ragdoctor
git clone https://github.com/thehalleyyoung/stepback  && pip install -e ./stepback
git clone https://github.com/thehalleyyoung/flowwarden && pip install -e ./flowwarden
```

The `Makefile` in this repo has `make clone`, `make install`, `make test`,
and `make demo` targets that automate the clone-and-editable-install flow.

---

## Documentation in this repo

- [`README.md`](README.md) — this file.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — shared design choices
  (canonical encoding, signed append-only artifacts, content-addressed
  storage, duck-typed adapters) and how the three component schemas
  interoperate.
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md) — concrete cookbook:
  every place where two components hand data to each other, with code
  snippets and pitfalls.
- [`examples/integrated_demo.py`](examples/integrated_demo.py) — a
  ~80-line runnable example that uses all three on one fake agent run.

---

## Status of each component

Quoted from each repo's `README.md`:

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

---

## License

Each component is Apache-2.0. This meta-repo is also Apache-2.0. See
each component's `LICENSE` file for the canonical text.
