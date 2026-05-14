# agent-h

> A reference stack for building, running, debugging, **conducting research with**,
> and **finetuning per task** production LLM agents. Nineteen independent
> open-source projects, each owning one concern, designed so they compose
> end-to-end on a single agent run — and so the per-task settings that
> tie them together live in a typed, Pareto-tuned, preference-constrained,
> taint-tracked, deterministically replayable contract instead of a Markdown file.

This repository is the **meta-repo**: it doesn't ship code itself. It points at
the component projects, explains how they fit together, and shows how to use
them in combination. Every component is Apache-2.0, Python-first (some have
Rust cores in progress), and **intentionally decoupled**: you can adopt any one
in isolation or any subset, because they share design DNA (canonical encoding,
signed append-only artifacts, duck-typed adapters).

---

## One-sentence thesis

> **Per-task agent settings — model, temperature, prompts, tool whitelist, search
> knobs, distilled skills — belong in a typed, Pareto-tuned, preference-constrained,
> taint-tracked, deterministically replayable contract, not in a Markdown file;
> tuning that contract under a real cost ceiling is the unit of *finetuning an
> agent for a task*.**

The contract is the [`lapidary`](https://github.com/thehalleyyoung/lapidary)
subsystem. The other 18 subsystems each own one named role at finetune time
(see [§ Integration](#integration)).

---

## The 19 subsystems

The stack is organised in three tiers. **Production** is what you need to run,
observe, and audit a deployed agent. **Research-software (Comet-H)** adds the
controller and evidence substrate needed for codebases where theory, code,
claims, and evidence must co-evolve. **Finetuning** is the crowning loop that
tunes the per-task contract and learns task-local skills.

### Production tier

| Component | Concern | Repository |
|---|---|---|
| 🐚 **shell** | LLM substrate — multi-provider client (OpenAI / Anthropic / Ollama / fakes), token accounting, fallback, replay-cached transcripts | <https://github.com/thehalleyyoung/shell> |
| 🤖 **homer** | conversational agent framework wiring the rest into a single `Agent` (the default thing you tune with `lapidary`) | <https://github.com/thehalleyyoung/homer> |
| 🔁 **looper** | durable agent control loop (idempotent, resumable, exactly-once side effects) | <https://github.com/thehalleyyoung/looper> |
| 💸 **bankroll** | per-step token / dollar accounting and budget enforcement | <https://github.com/thehalleyyoung/bankroll> |
| 🧠 **mnemos** | content-addressed cross-session memory keyed by `(cwd, intent_hash)` | <https://github.com/thehalleyyoung/mnemos> |
| 🐛 **stepback** | record, replay, and counterfactually re-execute an agent run; deterministic recipe per trial | <https://github.com/thehalleyyoung/stepback> |
| 🛡️ **flowwarden** | taint-track data across tool/LLM calls; emit signed attestations; gate promotion | <https://github.com/thehalleyyoung/flowwarden> |
| 🔧 **toolforge** | typed tool-contract registry; the substrate for per-task tool whitelists | <https://github.com/thehalleyyoung/toolforge> |
| ⚔️ **adversary** | adversarial-input synthesis; the curriculum's robustness stage | <https://github.com/thehalleyyoung/adversary> |
| 🧪 **rerun** | CI regression harness for agent traces; gates every defaults bump | <https://github.com/thehalleyyoung/rerun> |
| 🩺 **ragdoctor** | diagnose RAG/agent regressions and prescribe fixes; per-rollout retrieval QC signal | <https://github.com/thehalleyyoung/ragdoctor> |
| 🗺️ **cartograph** | repo-scale code intelligence — symbol/call/type graph + ranked context selection; powers `FilenameParam.candidates()` | <https://github.com/thehalleyyoung/cartograph> |
| 🌌 **manyworlds** | speculative parallel agent search — fork into N branches, prune by signal stack, collapse to winner | <https://github.com/thehalleyyoung/manyworlds> |
| 💧 **distill** | hierarchical context compaction — decision-preserving loss bounds, retrieval-aware policies, streaming | <https://github.com/thehalleyyoung/distill> |
| 🎨 **atelier** | skills + sub-agent delegation + slash commands + hooks; receives skills minted by `lapidary` | <https://github.com/thehalleyyoung/atelier> |
| 🔥 **kiln** | capability-based sandboxed execution — deny-by-default, pluggable backends, signed attestations | <https://github.com/thehalleyyoung/kiln> |
| ⚗️ **crucible** | agent eval & regression harness — paired bootstrap, MDE, mutation-based suite synthesis, CI gating | <https://github.com/thehalleyyoung/crucible> |

### Research-software tier (Comet-H)

| Component | Concern | Repository |
|---|---|---|
| 🧭 **coevo** | co-evolution state-machine controller — workspace `W=(T,R,P,E,U,Q)`, decaying obligations, reactive grounding trigger, open-alphabet skills | <https://github.com/thehalleyyoung/coevo> |
| 📑 **groundwork** | typed signed grounding ledger binding public claims to runnable evidence; signs every `D → D'` transition | <https://github.com/thehalleyyoung/groundwork> |

### Finetuning tier

| Component | Concern | Repository |
|---|---|---|
| 💎 **lapidary** | the **per-task preference contract**; agent-policy finetuning loop (warm-start → curriculum → reasoner → distill); strictly subsumes `CLAUDE.md` along nine measurable axes | <https://github.com/thehalleyyoung/lapidary> |

---

## What `lapidary` does that `CLAUDE.md` cannot

A flat `CLAUDE.md` (or `AGENTS.md`, or `.cursorrules`, or `instructions.md`) is
five things at once: a parameter store, a preference store, a default-value
store, a memory store, and a constraint store. None of those five jobs is done
well, because the data structure is wrong. `lapidary` replaces it with a typed
contract:

| Axis | `CLAUDE.md` | `lapidary` |
|---|---|---|
| **Enforcement** | suggestion in prose | `AVOID` literally removes the value from the searched schema |
| **Quantification** | none | every preference is a typed range / set / boost |
| **Provenance** | edit history at best | every default cites the trial(s) that justify it; signed in `groundwork` |
| **Learning** | manual edits | Pareto search over (quality × cost) updates defaults under preference constraints |
| **Cross-session** | one file per repo | `mnemos.recall(intent_hash)` warm-starts neighbouring tasks |
| **Planner visibility** | LLM may ignore it | the schema *physically shrinks* before the LLM sees it |
| **Replayability** | none | every trial recorded by `stepback`; `lapidary replay` re-executes bit-identically |
| **Taint** | none | `flowwarden` taint gates promotion; tainted trials cannot become defaults |
| **Cost** | unaccounted | every trial charges the per-task `bankroll` ledger |

The full articulation is in
[lapidary/README.md](https://github.com/thehalleyyoung/lapidary#what-stored-preferences-let-you-do-that-claudemd-cannot)
and the formal subsumption theorem is in
[`papers/agent-h-arch/main.tex`](papers/agent-h-arch/main.tex).

---

## <a name="integration"></a>How they all fit together: agent finetuning

`lapidary finetune <task>` is the **single command** that exercises every
sibling. It is also the most honest demonstration of what the stack is for.

```
                              [lapidary finetune]
                                       │
                       ┌───────────────┴───────────────┐
                       │                               │
                  warm-start                      curriculum
                  (mnemos +                       (4 stages:
                   intent_hash                     scalars →
                   neighbours)                     controller →
                       │                           text → joint)
                       │                               │
                       └───────────────┬───────────────┘
                                       │
                            durable session (looper)
                            cost ceiling (bankroll)
                                       │
                       ┌───────────────┴───────────────┐
                       │      per-trial rollout         │
                       │   ┌──────────────────────┐     │
                       │   │ shell.LLMClient      │     │
                       │   │ homer.Agent          │     │
                       │   │ toolforge whitelist  │     │
                       │   │ kiln sandbox         │     │
                       │   │ manyworlds n-fork    │     │
                       │   │ distill compaction   │     │
                       │   │ ragdoctor QC signal  │     │
                       │   │ cartograph file ctx  │     │
                       │   │ stepback recorder    │     │
                       │   │ flowwarden taint     │     │
                       │   └──────────────────────┘     │
                       └───────────────┬───────────────┘
                                       │
                       Reasoner (D → D')  ⟶ rerun regression
                                       │           │
                          groundwork-signed   adversary stage
                                       │
                                  auto_distill
                              (mints task-local
                               coevo PromptFamilies
                               + atelier skills)
                                       │
                                FinetuneReport
                            mirrored to mnemos
```

The full per-sibling integration contract is in `papers/agent-h-arch/main.tex`
Table 2 and `lapidary/100_STEPS.md` § Integration.

### Concrete example

The two things that matter most about a finetune run are (1) **what LLM is
allowed**, and (2) **how a candidate output artifact is scored**. Both are
explicit in the Task — the model is a `ChoiceParam` in the user schema (so
the search picks among allowed providers / sizes), and the score function
inspects the produced artifact (codebase, HTML+gif sequence, mp4, JSON
report) and returns a number.

```python
from pathlib import Path
from lapidary import (
    Task, ChoiceParam, NumberParam, TextParam,
    finetune_agent, cometh_rollout, join_schemas,
    cometh_policy_schema, TrajectoryOutcome,
)
from shell import LLMClient
from homer import Agent
from crucible import grade_codebase   # eval harness from the stack

# 1. Declare the user-facing knobs INCLUDING which LLMs are allowed.
#    `lapidary` will Pareto-search over (model × temperature × prompt × ...).
user_schema = {
    "model":       ChoiceParam(choices=("anthropic/claude-sonnet-4.6",
                                        "openai/gpt-5-mini",
                                        "ollama/qwen3-coder:30b"),
                               default="openai/gpt-5-mini"),
    "temperature": NumberParam(min=0.0, max=1.5, default=0.4),
    "system_prompt": TextParam(default="You are a careful refactoring agent."),
    "max_steps":   NumberParam(min=4, max=40, default=16, integer=True),
}

# 2. Add the comet-h controller knobs (alphabet bias, signal weights, tool
#    whitelist, lambda_obl, epsilon_fork, grounding_k, ...).
policy_schema = cometh_policy_schema(
    alphabet_names=("Generate", "Harden", "Settle", "Refactor"),
    signal_names=("Bankroll", "Mnemos", "Crucible"),
    tool_names=("grep", "edit", "run_tests", "git_diff"),
)

# 3. The agent_step USES the params lapidary picks. The provider routing,
#    token accounting, fallbacks, and replay caching all live in `shell`.
def my_agent_step(state, family, *, params, work_dir):
    llm = LLMClient(model=params["model"], temperature=params["temperature"])
    agent = Agent.from_state(
        state,
        llm=llm,
        system_prompt=params["system_prompt"],
        tools=params["enabled_tools"],          # <- toolforge whitelist
        work_dir=work_dir,
    )
    return agent.step(family)   # (new_state, obs, cost_usd, reward, done, tool_calls)

# 4. The score function GRADES THE PRODUCED ARTIFACT. This is what the
#    Pareto search is optimising. For a codebase task we run the eval suite
#    via `crucible`; for an mp4 task it would diff frames; for an HTML+gif
#    task it would run a rubric LLM against the rendered sequence.
def score_artifact(trajectory) -> float:
    final_state = trajectory.steps[-1].state_summary
    artifact_dir = Path(final_state["work_dir"])
    grade = grade_codebase(
        artifact_dir,
        suite_id="refactor-auth-module/v1",      # crucible suite
        rubric=[
            ("tests_pass",    1.0),              # weight 1.0
            ("type_check",    0.5),
            ("api_unchanged", 0.8),              # public API stability
            ("loc_delta",    -0.001),            # small penalty per LOC churn
        ],
    )
    return grade.score          # in [0, 1]; crucible writes last_grade.json

# 5. Wire it up. `bankroll_usd` is the HARD cost ceiling for the whole tune.
task = Task(
    name="refactor-auth-module",
    prompt="Refactor src/auth/ to remove session state without changing the public API.",
    schema=join_schemas(user_schema, policy_schema),
    work_root=Path("~/.lapidary/refactor-auth-module").expanduser(),
)

report = finetune_agent(
    task,
    rollout=cometh_rollout(
        my_agent_step,
        success_pred=lambda s: s.get("tests_pass") is True,
    ),
    outcome=TrajectoryOutcome(score_fn=score_artifact, n=3),  # 3 rollouts/trial
    bankroll_usd=2.50,
)

print(report.final_defaults)        # the new typed defaults (incl. chosen model)
print(report.distilled_skills)      # task-local PromptFamilies minted
print(report.transferred_from)      # neighbour tasks that warm-started this one
print(report.cost_usd)              # what the whole tune cost (≤ 2.50)
```

Two things to notice:

* **`model` is a parameter, not a fixed string.** `lapidary` may discover
  that `gpt-5-mini` at `temperature=0.2` Pareto-dominates `claude-sonnet-4.6`
  at `temperature=0.7` for *this specific task*, and write that into
  `final_defaults`. A flat `CLAUDE.md` cannot do this.
* **The score function inspects the artifact, not the trajectory text.**
  Whether the artifact is a codebase, a sequence of HTML pages and gifs, or
  a generated mp4, the score is whatever `score_artifact(trajectory)`
  returns. `crucible` is the recommended grader for codebases; for media
  artifacts you supply your own (frame diff, rubric LLM, perceptual hash,
  human-in-the-loop via `lapidary review`).

---

## Two-tier rationale

Production agent platforms answer a different set of operational questions
than research-software platforms. The **production tier** answers *"is this
agent safe, fast, cheap, observable, restartable?"* The **Comet-H tier**
answers *"can I make and ground a research claim from this run?"* The
**finetuning tier** answers *"can I make this agent better at this specific
task without drifting on the others?"*

We keep the tiers separate because they have different consumers and
different failure modes. We keep them in one stack because the contract
(`lapidary`) is the shared object that lets them all speak about the same
per-task knobs.

---

## Get started

```bash
# Clone the meta-repo
git clone https://github.com/thehalleyyoung/agent-h
cd agent-h

# Install any subset (each is independently `pip install`-able from git+https)
pip install git+https://github.com/thehalleyyoung/lapidary
pip install git+https://github.com/thehalleyyoung/homer
pip install git+https://github.com/thehalleyyoung/shell
# ...

# Or pull the whole stack
make install-all       # installs all 19 subsystems in editable mode
```

Then either:

* **Build an agent** with `homer` + `shell` + `toolforge` + `bankroll`
  (production tier).
* **Conduct research** in `coevo` + `groundwork` (Comet-H tier).
* **Finetune any agent for any task** with `lapidary finetune <task>`
  (finetuning tier).

The blog post [*Homer is not Claude Code — and that's the point*](blog/2026-05-14-homer-vs-claude-code.md)
walks through the design choices that make this composition work where flat
agent loops don't.

---

## Documentation

* [`papers/agent-h-arch/main.tex`](papers/agent-h-arch/main.tex) — the
  contract paper, with the soundness theorem, the nine-axis subsumption
  theorem, and the per-sibling integration table.
* [`100_STEPS_PARITY.md`](100_STEPS_PARITY.md) — the meta-roadmap closing
  the Claude-Code feature-parity gap.
* [`docs/PROVIDERS.md`](docs/PROVIDERS.md) — canonical multi-provider LLM
  strategy across the stack.
* Each subsystem has its own `100_STEPS.md` roadmap and per-feature docs.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Issues and discussions are
welcome on each subsystem's repository; meta-issues (cross-cutting concerns,
new subsystems, integration contracts) belong here.

---

## License

Apache-2.0 across the entire stack.
