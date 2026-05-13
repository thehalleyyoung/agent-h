"""Integrated agent-h demo.

Runs a tiny agent that:
  1. is wrapped in a flowwarden policy (PII may not flow to send_email),
  2. is recorded by stepback into a signed .sb trace,
  3. answers a query against a small ragdoctor RagPipeline,
  4. is then audited by ragdoctor for quality regressions.

This file is intentionally short and dependency-light. It uses
in-memory toy data so it runs without any network calls.

Install (the three components aren't on PyPI yet):
    pip install git+https://github.com/thehalleyyoung/ragdoctor.git
    pip install git+https://github.com/thehalleyyoung/stepback.git
    pip install git+https://github.com/thehalleyyoung/flowwarden.git

Run:
    python examples/integrated_demo.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def main() -> None:
    import flowwarden
    import ragdoctor
    import stepback

    # ---------- 1. Tiny corpus + ragdoctor pipeline ----------
    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp) / "docs"
        corpus.mkdir()
        (corpus / "rotation.md").write_text(
            "# Key rotation\n\n"
            "Rotate keys via `cli rotate --kid <id>`. New keys are valid "
            "immediately; old keys expire after 24h.\n"
        )
        (corpus / "billing.md").write_text(
            "# Billing\n\nInvoices are sent monthly to the account owner.\n"
        )
        pipeline = ragdoctor.RagPipeline.from_paths([str(corpus)], chunk_size=200)

        # ---------- 2. flowwarden labels + policy ----------
        PII = flowwarden.Label("pii", level="confidential")
        flowwarden.tools.clear_registry()  # idempotent for repeated runs

        @flowwarden.tool(returns=PII)
        def lookup_customer(customer_id: str) -> str:
            return f"Customer {customer_id}: ssn 123-45-6789, email c@x.test"

        @flowwarden.tool(accepts={"to": "external", "body": "external"})
        def send_email(to: str, body: str) -> None:
            # In a real system this would call SendGrid/SES/etc.
            print(f"  send_email -> to={to} body={body[:60]!r}")

        POLICY = "forbid label(pii) flow_to tool(send_email).\n"

        # ---------- 3. stepback recorder + nested flowwarden run ----------
        trace_path = Path(tmp) / "run.sb"
        key = stepback.RecorderKey.fresh()

        def llm_stub(model: str, messages: list[dict]) -> dict:
            # Deterministic stand-in for a real LLM. In the real composition
            # this would be `openai.chat.completions.create` or similar.
            user = messages[-1]["content"]
            return {
                "id": "stub-1",
                "model": model,
                "choices": [
                    {"index": 0, "message": {"role": "assistant",
                                             "content": f"(answer to: {user[:40]}...)"}}
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 4, "total_tokens": 8},
            }

        with flowwarden.install(POLICY) as fw, \
             stepback.record(str(trace_path), key=key) as rec:

            # 3a. RAG retrieval step (no PII; flowwarden lets it through).
            query = "How do I rotate keys?"
            hits = rec.tool_call(
                "retrieve", {"query": query, "k": 3},
                executor=lambda n, a: [
                    {"id": h.chunk_id, "text": h.text[:120]}
                    for h in pipeline.retrieve(a["query"], k=a["k"])
                ],
            )
            print(f"retrieve: {len(hits)} hits")

            # 3b. LLM answer step.
            answer = rec.llm_call(
                "stub-llm-v1",
                [{"role": "user", "content": f"{query}\n\nContext: {hits}"}],
                executor=llm_stub,
            )
            print(f"answer: {answer['choices'][0]['message']['content']}")

            # 3c. PII flow attempt — should be blocked by the policy.
            customer = rec.tool_call(
                "lookup_customer", {"customer_id": "c-42"},
                executor=lambda n, a: fw.invoke_tool(n, a),
            )
            try:
                rec.tool_call(
                    "send_email", {"to": "audit@x.test",
                                   "body": f"Customer record: {customer}"},
                    executor=lambda n, a: fw.invoke_tool(n, a),
                )
                print("⚠️  send_email was NOT blocked — policy bug.")
            except flowwarden.FlowViolation as e:
                print(f"flowwarden BLOCKED send_email: {e}")
                rec.exception("FlowViolation", str(e))

        # ---------- 4. Verify the trace and replay it ----------
        trace = stepback.replay(str(trace_path), hmac_key=key.hmac_key)
        result = trace.replay_forward()  # uses recorded outputs only
        print(f"\nstepback replay: {result.dirty_count} dirty, "
              f"{result.real_executions} real executions")

        # ---------- 5. Audit the underlying pipeline ----------
        report = ragdoctor.audit(pipeline, queries=[query])
        print("\nragdoctor audit (markdown):\n")
        print(report.to_markdown())


if __name__ == "__main__":
    main()
