# Architecture

This document explains the *shared* design that makes the three components
of agent-h compose cleanly. Each project's own `README.md` is the source
of truth for that project's internals; this document covers the seams.

## Shared design principles

All three components were designed with the same four primitives, which
is what lets them interoperate without a bespoke integration layer:

### 1. Canonical encoding everywhere

Every public artifact (a `.sb` trace frame, a ragdoctor `AttributionBundle`,
a flowwarden `ProvenanceGraph` or `ProvenanceAttestation`) is serialized
through a deterministic JSON encoder that produces identical bytes for
identical logical values:

- sorted object keys,
- no extra whitespace,
- normalized Unicode,
- explicit handling of bytes / non-finite floats / large numbers.

This is what lets all three tools hash content with `sha256:<hex>` and
treat hashes as semantic identity (not just byte identity).

### 2. Signed, append-only artifacts

- **stepback**: `.sb` files are length-prefixed canonical-JSON frames
  with HMAC-SHA256 chaining (`hmac = HMAC(key, prev_hmac || canonical(body))`)
  and per-frame Ed25519 signatures.
- **flowwarden**: `ProvenanceAttestation` supports both HMAC-SHA256
  (symmetric) and Ed25519 (asymmetric) signing, and serializes as either
  native JSON or a CycloneDX 1.6 AI BOM.
- **ragdoctor**: `ledger`, `ledger_signing`, and `transparency_log`
  modules implement local append-only audit records.

This means any of these artifacts can be handed to a third party with
a public key for offline verification. No hosted service is required to
trust the bytes.

### 3. Content-addressed storage

Step caches (stepback), pipeline configs (ragdoctor), and provenance
nodes (flowwarden) are all keyed by the SHA-256 of their canonical form.
That makes:

- deduplication free,
- reproducibility easy to test (recompute the hash, compare),
- cross-tool references stable (a ragdoctor finding can cite a stepback
  step by `step_id` *and* by `inputs_hash`; both will point at the same
  thing forever).

### 4. Duck-typed framework adapters

None of the three projects hard-imports LangChain / LlamaIndex / DSPy /
CrewAI / MCP at module-import time. Each adapter is duck-typed:
"give me anything that has a `.invoke()` / `.call_tool()` / etc."

This matters for composition: if you wire flowwarden around a LangChain
tool and then hand the same wrapped tool to stepback's recorder, both
adapters introspect the same object and you don't pay the dependency
cost twice.

---

## Where the components hand data to each other

There are three integration seams in practice. Each one is intentionally
small.

### Seam 1: flowwarden → stepback (runtime data flow)

`flowwarden.AgentRun` intercepts a tool call, applies policy, and (if
allowed) executes the tool. `stepback.Recorder.tool_call(name, args,
executor=...)` records the call and its result.

The clean composition is:

```python
import flowwarden, stepback

with flowwarden.install("forbid label(pii) flow_to tool(send_email).") as fw:
    with stepback.record("run.sb", key=key) as rec:
        # Pass a `record`-aware executor so that flowwarden's wrapper
        # is what actually executes (giving us policy enforcement) but
        # stepback's recorder still sees the call.
        result = rec.tool_call(
            "lookup_customer",
            {"customer_id": "c-42"},
            executor=lambda name, args: fw.invoke_tool(name, args),
        )
```

Three things to notice:

1. **flowwarden's wrapper is the executor stepback sees.** That means
   the recorded output is the post-policy output (which may have been
   `redact`-ed). If a `forbid` rule fires, `FlowViolation` is raised
   and stepback records the exception step.
2. **The marker sidechannel is invisible to stepback's hashing** because
   markers are stripped from the output before stepback canonicalizes
   it. So a substitution in stepback won't clobber flowwarden's labels.
3. **Both signed artifacts are preserved**: the `.sb` trace and the
   `ProvenanceAttestation` are independent files an auditor can verify
   separately.

### Seam 2: ragdoctor → stepback (offline analysis of a recorded run)

`stepback.replay("run.sb").to_ragdoctor_pipeline()` is *not* a built-in
method (yet) — but the pattern works manually. A `.sb` trace contains
all the inputs and outputs of every retrieval/LLM step, so you can:

1. Replay the trace with `executor=Executor(fallback_recorded=True)` to
   get a deterministic re-run with no live calls.
2. Pull out each retrieval step's inputs/outputs.
3. Build a `ragdoctor.RagPipeline` from the same documents and run
   `Doctor(pipeline).diagnose([query])` to score it on the 8 axes.
4. Compare the two: any axis whose score regressed between the recording
   and now is a candidate root cause.

This pattern is what lets you do **post-mortem RCA on a single bad run**
rather than the more common "compare aggregate metrics across two
deployments" workflow.

### Seam 3: ragdoctor → flowwarden (taint-aware test generation)

`ragdoctor.synth` generates synthetic test queries from your corpus.
`ragdoctor.red_team` generates adversarial ones (jailbreaks, indirect
injection, etc.). Both can be wired into a flowwarden-protected agent:

```python
import ragdoctor, flowwarden

cases = ragdoctor.synth.generate(pipeline, dimension="injection_resistance")
with flowwarden.install(POLICY) as fw:
    for case in cases:
        try:
            answer = my_agent.run(case.query)
            print(case.expected_id, "ok")
        except flowwarden.FlowViolation as e:
            # The injection attempt actually triggered a flow violation,
            # which is the *correct* outcome and a credit to the policy.
            print(case.expected_id, "blocked by policy:", e)
```

This catches a real failure mode: a model that "doesn't follow" an
injection often still leaks the injected payload into a downstream tool
call, which a quality-only test wouldn't notice.

---

## What is *not* shared

Things that are deliberately **not** unified across the three:

- **Configuration formats.** stepback uses CLI flags and env vars,
  ragdoctor uses YAML pipelines, flowwarden uses `.fw` files. Forcing
  a common config format would couple their release cycles.
- **Step / probe / label vocabularies.** `step_kind` (stepback),
  `axis` (ragdoctor), and `label` (flowwarden) are different
  ontologies. They reference each other by hash, not by enum.
- **Process model.** stepback can run as a sidecar proxy. ragdoctor
  can run as a local HTTP server. flowwarden runs in-process. Each
  reflects what its workload actually demands.

---

## Versioning and stability

Each component has its own SemVer line. Cross-tool integration relies on
the **schema version** fields in each artifact, not the package version:

- stepback's frame header contains `format_version`,
  `recorder_version`, `canonicalisation_version`, `price_list_version`.
- ragdoctor's bundles have `schema_version`.
- flowwarden's attestations have `schema` and `policy_version`.

A best practice when wiring multiple components is to log all of these
versions at agent start-up so a future investigation can reproduce the
exact stack.
