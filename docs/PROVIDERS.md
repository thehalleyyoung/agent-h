# Multi-provider LLM strategy for agent-h

agent-h is **provider-agnostic** by design. Every component that calls an
LLM works against the OpenAI Chat Completions wire format (which is the
de-facto lingua franca of cheap reasoning-model providers in 2025) and
falls back to [LiteLLM] for the few providers that aren't OpenAI-shaped
(native Anthropic, Google Gemini, Bedrock, Vertex).

[LiteLLM]: https://github.com/BerriAI/litellm

## Supported providers (out of the box)

| Provider | Default `base_url` | API key env var | Notes |
|---|---|---|---|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | reference impl |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | gateway to ~300 models incl. cheap reasoning |
| `deepseek` | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` | DeepSeek-V3 / R1 — cheapest top-tier reasoning |
| `groq` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | fastest cheap inference (Llama, Qwen, Kimi) |
| `together` | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` | open-weight zoo |
| `fireworks` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | open-weight zoo, fast |
| `mistral` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | Mistral Large/Codestral |
| `perplexity` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | Sonar (web-grounded) |
| `deepinfra` | `https://api.deepinfra.com/v1/openai` | `DEEPINFRA_API_TOKEN` | open-weight zoo, very cheap |
| `anyscale` | `https://api.endpoints.anyscale.com/v1` | `ANYSCALE_API_KEY` | open-weight zoo |
| `cerebras` | `https://api.cerebras.ai/v1` | `CEREBRAS_API_KEY` | wafer-scale Llama, very fast |
| `xai` | `https://api.x.ai/v1` | `XAI_API_KEY` | Grok |
| `nvidia` | `https://integrate.api.nvidia.com/v1` | `NVIDIA_API_KEY` | NIM-hosted open weights |
| `ollama` | `http://localhost:11434/v1` | `OLLAMA_API_KEY` (dummy ok) | local |
| `vllm` | `http://localhost:8000/v1` | `VLLM_API_KEY` | self-hosted |
| `tgi` | `http://localhost:8080/v1` | `TGI_API_KEY` | self-hosted |
| `azure_openai` | (user-supplied) | `AZURE_OPENAI_API_KEY` | per-deployment URL |
| `litellm` | (delegated) | (per provider) | passthrough for native Anthropic / Gemini / Bedrock / Vertex |

## Canonical env-var convention

Every agent-h component honours these in priority order:

1. **Explicit constructor argument** — `LLMClient(provider="...", model="...", api_key="...", base_url="...")`.
2. **Unified `AGENT_H_LLM_*` env vars** — `AGENT_H_LLM_PROVIDER`, `AGENT_H_LLM_MODEL`, `AGENT_H_LLM_API_BASE`, `AGENT_H_LLM_API_KEY`.
3. **Per-provider env vars** — `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, etc. (table above).

This means switching the entire monorepo from OpenAI to OpenRouter on a
DeepSeek-R1 backend is one line in your shell:

```bash
export AGENT_H_LLM_PROVIDER=openrouter
export AGENT_H_LLM_MODEL=deepseek/deepseek-r1
export OPENROUTER_API_KEY=sk-or-...
```

…or to Groq's free Llama-3.3-70b for prototyping:

```bash
export AGENT_H_LLM_PROVIDER=groq
export AGENT_H_LLM_MODEL=llama-3.3-70b-versatile
export GROQ_API_KEY=gsk_...
```

…or to a local Ollama instance for offline work:

```bash
export AGENT_H_LLM_PROVIDER=ollama
export AGENT_H_LLM_MODEL=qwen2.5-coder:32b
```

## Reference implementation

A 200-LoC, dependency-free (`httpx`-only) reference implementation lives
in every scaffolded sub-repo as `<repo>/llm_provider.py`. It is
deliberately small enough to copy/paste; sub-repos that need richer
behaviour are free to depend on `litellm` directly.

The reference implementation is **wire-compatible** across every
provider in the table above. A single `LLMClient.chat(...)` call routes
to the right base URL, attaches the right auth header, and returns a
normalized `ChatResponse` with `text`, `model`, `provider`, raw payload,
and token counts.

## Provider-specific notes

- **OpenRouter** — auto-attaches the `HTTP-Referer` and `X-Title` headers
  it expects for attribution; harmless on other providers.
- **DeepSeek** — `deepseek-reasoner` is a thinking model; allocate
  `max_tokens` generously (≥4096) and expect `<think>...</think>` blocks.
- **Groq** — extremely fast but lower context windows on free tier;
  ideal for `cartograph` ranking and `crucible` validators.
- **Anthropic / Gemini / Bedrock / Vertex** — set
  `AGENT_H_LLM_PROVIDER=litellm` and use a fully-qualified model
  identifier like `anthropic/claude-3-5-sonnet-latest` or
  `gemini/gemini-2.0-flash`. Requires `pip install litellm`.
- **Ollama / vLLM / TGI** — set `AGENT_H_LLM_API_BASE` if you're not
  using the default localhost ports. The `OLLAMA_API_KEY` env is just a
  dummy to satisfy the auth-header check; Ollama ignores it.

## Cost-aware routing

For cost-aware routing across providers (e.g., "use Groq Llama for
ranking, DeepSeek-R1 for hard reasoning, OpenAI for tool-calling"), see
the [`bankroll`](https://github.com/thehalleyyoung/bankroll) component:
its price cards already cover every provider in the table above
(`bankroll/prices/v1/{openrouter,deepseek,groq,together_ai,fireworks_ai,
mistral,perplexity,...}.json`).

## Determinism caveats

Per [`stepback`](https://github.com/thehalleyyoung/stepback)'s
`PROVIDER_SEED_SUPPORT` registry: only OpenAI honours `seed=` deterministically.
Every other provider is `BEST_EFFORT` (the seed parameter is accepted
but the backend may not honour it). For determinism-sensitive workflows,
prefer OpenAI; for everything else, the cheap providers are fine.

## Per-component status

Status as of agent-h public-release prep (see each repo's `100_STEPS.md`
for detail):

| Component | Provider abstraction | Status |
|---|---|---|
| `bankroll` | price cards for 17 providers including openrouter | shipped |
| `stepback` | `PROVIDER_SEED_SUPPORT` registry covering openai/anthropic/groq/together/fireworks/cerebras/deepseek/xai/openrouter/mistral/perplexity/deepinfra/anyscale | extended in this release |
| `cartograph`, `manyworlds`, `distill`, `atelier`, `kiln`, `crucible`, `coevo`, `groundwork` | `<repo>/llm_provider.py` (this release) | shipped |
| `homer`, `adversary`, `toolforge`, `ragdoctor`, `flowwarden`, `mnemos` | inherit shared module (planned migration) | tracked in 100_STEPS |

## Token-saving caches

The shared `<repo>/llm_provider.py` ships with two opt-in cache layers,
both producing direct token (and dollar) savings:

### Local response cache

SQLite-backed, content-addressed by `sha256(provider, canonical_request)`;
hits return immediately without touching the network. Activate with:

```bash
export AGENT_H_LLM_CACHE=1
export AGENT_H_LLM_CACHE_PATH=~/.cache/agent-h/llm_cache.db   # optional
export AGENT_H_LLM_CACHE_TTL=86400                            # optional, seconds
```

…or programmatically: `LLMClient(..., cache=True)`. `ChatResponse.cached`
is `True` for cached responses so `bankroll` and dashboards can attribute
savings.

### Provider-side prompt caching

Many providers serve cached prompt prefixes at a 50–90 % input-token
discount. The shared client knows about every popular variant and
applies the right marker automatically:

| Provider | Mechanism | Annotation |
|---|---|---|
| anthropic (via litellm) | `cache_control={"type":"ephemeral"}` on last system+user | up to 90 % input-token discount |
| openai / azure_openai | stable `prompt_cache_key` derived from prefix | hit-rate boost on automatic ≥1024-token caching |
| gemini (via litellm) | `cache_control={"type":"cached_content"}` on system | per Google's spec |
| deepseek | automatic | reported via `usage.prompt_cache_hit_tokens` |
| openrouter | passthrough to upstream | as upstream supports |
| groq, together, fireworks, mistral, perplexity, … | n/a | local response cache only |

Activate: `LLMClient(..., prompt_cache=True)` or
`AGENT_H_LLM_PROMPT_CACHE=1`. `ChatResponse.prompt_cache_hit_tokens`
returns the cached token count from the provider's `usage` block (works
across OpenAI, DeepSeek, and Anthropic shapes).

### Pre-existing repo-specific caches

Several sibling repos have purpose-built caches that long predate the
shared `llm_provider.py`. They remain authoritative for their domain:

| Repo | Module | Purpose |
|---|---|---|
| `homer` | `homer/cache.py` | LLM response cache (SHA-256 model+prompt → response, SQLite, LRU + TTL) |
| `homer` | `homer/planner/memoize.py`, `homer/corpus/embedding_cache.py` | planner / embedding memoization |
| `adversary` | `adversary/cache.py` | candidate-prompt result cache (SQLite) |
| `ragdoctor` | `ragdoctor/caching.py` | embedding cache + query cache |
| `ragdoctor` | `ragdoctor/cache.py` | audit-report disk LRU |
| `stepback` | `stepback/step_cache.py` | sharded content-addressed step cache (dedup across traces) |
| `toolforge` | `toolforge/cache_store.py` | tool-result memoization (Dict/File/Shelve, sync + async) |
| `mnemos` | `mnemos/cache.py` | store-query LRU with namespace-aware invalidation |

These will be brought into composition with the monorepo-wide
`ResponseCache` over time; see each repo's `100_STEPS.md` for the
migration roadmap.
