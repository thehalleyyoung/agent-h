# Integration cookbook

Copy-pasteable recipes for using two or three of the agent-h components
together. Each recipe is a complete, runnable Python snippet (or shell
sequence). They assume you have all three packages installed:

```bash
pip install "git+https://github.com/thehalleyyoung/ragdoctor.git"
pip install "git+https://github.com/thehalleyyoung/stepback.git"
pip install "git+https://github.com/thehalleyyoung/flowwarden.git"
```

---

## Recipe 1: Build → record → audit a one-shot RAG agent

You have a small corpus and want to (a) answer a query, (b) keep a
signed trace of how the answer was produced, and (c) get a quality
report on the underlying retrieval pipeline.

```python
from pathlib import Path
import ragdoctor, stepback

# 1) Build the local pipeline.
pipeline = ragdoctor.RagPipeline.from_paths(["docs"], chunk_size=200)

# 2) Record the run.
key = stepback.RecorderKey.fresh()
with stepback.record("run.sb", key=key) as rec:
    query = "How do I rotate keys?"
    rec.tool_call("retrieve", {"query": query, "k": 5},
                  executor=lambda name, args: pipeline.retrieve(args["query"], k=args["k"]))
    rec.llm_call("local-stub", [{"role": "user", "content": query}],
                 executor=lambda model, msgs: {"choices": [{"message": {"content": pipeline.answer(query)}}]})

# 3) Audit the pipeline that produced the trace.
report = ragdoctor.audit(pipeline, queries=[query])
report.open_in_browser()        # writes a self-contained HTML report
print(report.to_markdown())
```

What you get:

- `run.sb` — signed, replayable trace of the answer.
- `report.html` — 8-axis quality report with cited evidence.

---

## Recipe 2: Bisect a quality regression across two snapshots

You have two `.sb` traces from different deploys (`good.sb`, `bad.sb`)
and want to identify the step where they diverged.

```python
import stepback

good = stepback.replay("good.sb")
bad  = stepback.replay("bad.sb")

# Diff first to localize. trace_diff returns step-by-step deltas.
from stepback.trace_diff import trace_diff
print(trace_diff(good, bad).to_markdown())

# Then bisect within the bad trace using a predicate.
result = bad.bisect(
    good="step:1",
    bad="step:12",
    predicate="step.outputs.choices[0].message.content.startswith('I cannot')"
)
print("first failing step:", result.first_bad_step)
```

If you also have a flowwarden run log for the same execution, you can
cross-reference the bad step's `tool_call` against
`flowwarden trace show run.jsonl --explain step:N` to see whether a
policy decision was the cause.

---

## Recipe 3: Counterfactual model swap

"What if we'd used `gpt-4o-mini` for step 1 instead of `gpt-4o`?"

```python
import stepback
from stepback.substitutions import ModelSubstitution

trace = stepback.replay("run.sb", hmac_key=key.hmac_key)
trace.substitute(ModelSubstitution(at_step="step:1", model="gpt-4o-mini-2024-07-18"))

# Replay with substitution. Only step:1 and its downstream dirty set
# actually call the LLM; everything else is served from cache.
result = trace.replay_forward(stepback.Executor(llm=my_llm_callable))
print("dirty:", result.dirty_count, "real LLM calls:", result.real_executions)
```

In a 30-step trace where only steps 1, 4, and 7 transitively depend on
step 1's output, this typically uses 3 real LLM calls instead of 30.

---

## Recipe 4: Enforce PII flow policy on a live agent

You want the agent to refuse to send PII to the email tool.

```python
from flowwarden import FlowViolation, Label, install, tool

PII = Label("pii", level="confidential")
POLICY = "forbid label(pii) flow_to tool(send_email)."

@tool(returns=PII)
def lookup_customer(customer_id: str) -> str:
    return f"Customer {customer_id}: ssn 123-45-6789"

@tool(accepts={"to": "external", "body": "external"})
def send_email(to: str, body: str) -> None:
    print(f"-> would send to {to}: {body[:60]}...")

try:
    with install(POLICY) as run:
        record = lookup_customer("c-42")
        # Even if the LLM paraphrases, the marker sidechannel preserves the label.
        rewritten = run.llm_call(f"Draft an email body using: {record}")
        send_email(to="audit@example.com", body=rewritten)
except FlowViolation as exc:
    print("blocked:", exc)
```

To prove to an auditor that no policy violation occurred during a run:

```bash
flowwarden attest run.jsonl --algo ed25519 --key signer.json --output run.attestation.json
flowwarden verify run.attestation.json --algo ed25519
```

The attestation is a CycloneDX 1.6 AI BOM with `flowwarden:*`
properties. Any CycloneDX-aware tool can ingest it; the signature is
checked offline against `signer.json`'s public half.

---

## Recipe 5: Wire all three together (the full stack)

This is the canonical "agent-h" composition. Inner-to-outer:

```python
import flowwarden, stepback, ragdoctor

# (a) Build a pipeline ragdoctor will later audit.
pipeline = ragdoctor.RagPipeline.from_paths(["docs"], chunk_size=200)

# (b) Define labelled tools (flowwarden).
PII = flowwarden.Label("pii", level="confidential")

@flowwarden.tool(returns=PII)
def lookup_customer(customer_id: str) -> str:
    return f"Customer {customer_id}: ssn 123-45-6789"

@flowwarden.tool(accepts={"body": "external"})
def send_email(to: str, body: str) -> None:
    print(f"would email {to}: {body[:60]}")

POLICY = "forbid label(pii) flow_to tool(send_email)."

# (c) Run inside flowwarden + stepback.
key = stepback.RecorderKey.fresh()
with flowwarden.install(POLICY) as fw:
    with stepback.record("run.sb", key=key) as rec:
        # Tool calls go through fw (policy) then through rec (trace).
        cust = rec.tool_call(
            "lookup_customer", {"customer_id": "c-42"},
            executor=lambda n, a: fw.invoke_tool(n, a),
        )
        # RAG step.
        retrieved = rec.tool_call(
            "retrieve", {"query": "rotate keys", "k": 5},
            executor=lambda n, a: pipeline.retrieve(a["query"], k=a["k"]),
        )
        # Email step — will raise FlowViolation if PII reaches it.
        try:
            rec.tool_call(
                "send_email", {"to": "audit@x", "body": str(cust)[:200]},
                executor=lambda n, a: fw.invoke_tool(n, a),
            )
        except flowwarden.FlowViolation as e:
            rec.exception("FlowViolation", str(e))

# (d) Offline: audit the pipeline you used.
report = ragdoctor.audit(pipeline, queries=["How do I rotate keys?"])
print(report.to_markdown())
```

After this single run you have:

- `run.sb` — signed trace, replayable, branchable, bisect-able.
- `run.jsonl` (flowwarden's run log) and an optional
  `run.attestation.json` proving no PII reached `send_email`.
- A `ragdoctor` report scoring the underlying RAG pipeline on 8 axes.

---

## Recipe 6: Use ragdoctor's red team to test flowwarden's policy

If the question is "is my policy actually catching the attacks I claim?",
use ragdoctor as the attacker and flowwarden as the defender:

```python
import ragdoctor, flowwarden

cases = ragdoctor.red_team.generate(
    pipeline=pipeline,
    suite="owasp-llm-top-10",
    limit=20,
)

with flowwarden.install(POLICY) as fw:
    blocked = passed = 0
    for case in cases:
        try:
            my_agent.run(case.query)   # uses fw-wrapped tools internally
            passed += 1
        except flowwarden.FlowViolation:
            blocked += 1
    print(f"blocked {blocked}/{blocked+passed} adversarial cases")
```

A high block rate is good only if the corresponding `passed` cases
weren't supposed to be blocked. Cross-reference each blocked case
against your policy intent before claiming victory.

---

## Common pitfalls

1. **Marker leakage in user-visible output.** flowwarden's default
   marker dialect is XML-like (`<fw:span ...>`). If your final response
   path doesn't `strip_markers()`, end users will see them. Use the
   stealth dialect for end-user-facing surfaces.
2. **stepback caching across substitution scopes.** A
   `tool_output` substitution with `cache=False` will re-execute every
   time. Default behaviour caches by `(step_kind, inputs_hash)`; if the
   substitution didn't change the recorded inputs, you'll get a stale
   cached output.
3. **ragdoctor's `audit()` runs probes that may make embedding calls.**
   For fully offline operation, pass an embedding implementation from
   `ragdoctor.embedding` rather than relying on a network-backed
   default.
4. **flowwarden static analysis is intra-procedural.** Cross-function
   flows of unlabelled values won't be caught statically — that's what
   the runtime middleware is for.
