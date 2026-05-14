# Research-software tier (Comet-H)

The **research-software tier** of agent-h adds two components that turn the
production agent stack into an orchestrator for *research code* — repositories
where the specification itself is under construction.

It is the reference implementation of the controller architecture in
*"Theory Under Construction: Orchestrating Language Models for Research
Software Where the Specification Evolves"* (Young & Bjørner).

## What problem it solves

Production loops assume a fixed specification. Research loops do not. Two
characteristic failure modes appear when LMs are asked to evolve research
software, and the production tier alone has no defense against either:

- **Hallucination accumulation** — a fabricated number enters `paper.tex`,
  later steps treat it as ground truth, the lie compounds.
- **Desynchronization** — code drifts ahead of theory, theory ahead of code,
  or the LM's internal world model drifts from disk.

Comet-H frames the workspace as a typed state `W = (T, R, P, E, U, Q)` —
theory, repository forest, public projection (paper + README), evidence
surface, utility hypothesis, decaying obligations — and selects the next
prompt based on **workspace deficits read from disk**, not on the LM's
stale recollection.

## The two components

### `coevo` — the co-evolution state machine

- Re-reads `W` from disk every step (anti-staleness).
- Selects the next of 17 prompt families via a hand-set linear scorer
  `⟨w_p, feat(W_t, o_t)⟩ + b_p` over current workspace deficits.
- Carries unfinished follow-ups in a decaying obligation vector
  `o_{t+1} = λ · o_t + α(p_t)` with half-life 8 steps (`λ = 2^{−1/8}`).
- A selection kernel applies mode guards (S/G/H/T), a forced-follow-up
  queue, a tail-budget override, and a recency penalty.
- Five-rule **adjacency check** gates expansion prompts: capability
  preservation, single conceptual step, paper-describable, strengthens
  existing evidence, backable claim.
- Repository: <https://github.com/thehalleyyoung/coevo>

### `groundwork` — the typed signed grounding ledger

- Static extractor finds claim spans in `paper.tex` and `README.md`
  (numeric, comparator, or explicit `\groundedclaim{ID}{TEXT}`).
- Recorder runs a command, hashes its stdout, signs an append-only
  JSONL entry binding the claim to the command + cwd + env hash + exit
  code + Ed25519 signature.
- Auditor returns four buckets: **grounded**, **ungrounded**, **stale**,
  **orphaned**. The `--as-prompt` flag emits a SkepticalAudit prompt
  payload that `coevo` consumes directly.
- Repository: <https://github.com/thehalleyyoung/groundwork>

## How they bolt onto homer

Homer is the consumer-facing assembly. The research tier slots in via three
new homer surfaces, all opt-in (existing chat / serve / eval modes are
unchanged):

- `homer.adapters.coevo.HomerExecutor` — implements coevo's
  `Callable[[PromptFamily, Summary], None]` executor protocol by dispatching
  the chosen prompt to `Agent.chat()`.
- `homer.evidence.GroundingSubsystem` — hashes the watched files
  (`paper.tex`, `README.md`) before each step, calls `groundwork.audit`
  after each step, and reports the outcome. This is what implements the
  reactive grounding trigger inside a homer Agent run.
- `homer.research.ResearchMode` — wires `CoEvoMachine` + `HomerExecutor` +
  `GroundingSubsystem` together into a single `.run()` callable.

New CLI subcommands:

```bash
homer research --workspace ./repo --budget 200
homer ground "F1=0.768 on bench-90" --source-file paper.tex -- pytest -k bench_90
homer audit paper.tex README.md --strict
```

## Reactive grounding trigger (Comet-H Prop. 4.2)

After every step, the trigger compares pre/post hashes of `paper.tex` and
`README.md`. If either changed, it pushes `(GroundingCreation, SkepticalAudit)`
onto coevo's forced-follow-up queue, which the kernel then forces in priority
over scorer choice. This bounds the propagation depth of any single
hallucination to at most one step.

## Bandit framing

The selection step is a small contextual bandit: the 17 prompt families are
arms, `feat(W_t, o_t)` is the context, the linear score is the action value.
We never **learn** the scorer — weights are hand-set, every choice is
auditable from a short feature vector. The bandit framing is invoked only
to read off two design choices: (a) decay handles non-stationary rewards,
(b) the kernel + obligation vector supply enough variety to make a
stochastic exploration term unnecessary.

## License

Apache-2.0.
