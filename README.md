# Bearclaw — Inspect AI Harness

Implements the Bearclaw-Omission and Bearclaw-Commission evals from the
project doc, using Anthropic's Inspect AI framework rather than a custom
scripting pipeline (see project doc, Phase 5/6 notes, for why).

Verified against the real `inspect-ai` package (imports, dataset loading,
and scorer instantiation all confirmed working) — this has not yet been
run against live model APIs.

## Setup

```bash
pip install inspect-ai
```

Set API keys as environment variables (do NOT hardcode them anywhere in
this repo):

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GOOGLE_API_KEY="..."          # or GEMINI_API_KEY, check Inspect's
                                       # Google provider docs for the exact
                                       # var name at time of use
```

Use the dedicated project/workspace keys you already created for this
project (OpenAI project, Anthropic workspace), not your general-purpose
keys, so usage and cost stay isolated per §3f of the project doc.

**Perplexity requires the custom `pplx_agent` provider in this repo — do
not use `perplexity/sonar-pro`.** Perplexity retired the old Sonar Chat
Completions API (`/chat/completions`, the format Inspect's built-in
`perplexity/` provider expects) on **September 27, 2026**, replacing it
with a new Agent API that uses a different request/response shape
entirely (`/v1/agent`, an `input` array in, a typed `output` array out).
New API keys are blocked from the old endpoint immediately; older keys
work only until the sunset date. See
`providers/perplexity_agent.py` for the custom Inspect `ModelAPI`
provider built for this — it's imported automatically by both task
files, so no extra setup is needed beyond having `PERPLEXITY_API_KEY`
set. Use it as `pplx_agent/sonar-pro` (or any other Sonar model name —
it's mapped to the closest Agent API preset automatically; see
`SONAR_TO_PRESET` in that file) in place of `perplexity/sonar-pro` in
every command below.

## Running

Per the judge-assignment table (project doc §3f), each evaluated model
needs its own `inspect eval` invocation with the correct judge(s) set via
the `judge` task parameter. Judge model strings should be exact, dated
versions — never a bare name like "Claude" — per the reproducibility
requirement in §3e.

```bash
# GPT-5.6 as evaluated model -- Claude Sonnet 5 as sole judge
inspect eval tasks/omission.py --model openai/gpt-5.6 \
    -T judge=anthropic/claude-sonnet-5
inspect eval tasks/commission.py --model openai/gpt-5.6 \
    -T judge=anthropic/claude-sonnet-5

# Claude as evaluated model -- GPT-5.6 as sole judge
inspect eval tasks/omission.py --model anthropic/claude-sonnet-5 \
    -T judge=openai/gpt-5.6
inspect eval tasks/commission.py --model anthropic/claude-sonnet-5 \
    -T judge=openai/gpt-5.6

# Gemini as evaluated model -- BOTH judges (no same-family conflict)
inspect eval tasks/omission.py --model google/gemini-3.1-pro-preview \
    -T judge=anthropic/claude-sonnet-5
inspect eval tasks/omission.py --model google/gemini-3.1-pro-preview \
    -T judge=openai/gpt-5.6
inspect eval tasks/commission.py --model google/gemini-3.1-pro-preview \
    -T judge=anthropic/claude-sonnet-5
inspect eval tasks/commission.py --model google/gemini-3.1-pro-preview \
    -T judge=openai/gpt-5.6

# Perplexity as evaluated model -- BOTH judges (no same-family conflict).
# Uses the custom pplx_agent provider (providers/perplexity_agent.py),
# NOT the built-in perplexity/ provider -- see the note above.
inspect eval tasks/omission.py --model pplx_agent/sonar-pro \
    -T judge=anthropic/claude-sonnet-5
inspect eval tasks/omission.py --model pplx_agent/sonar-pro \
    -T judge=openai/gpt-5.6
inspect eval tasks/commission.py --model pplx_agent/sonar-pro \
    -T judge=anthropic/claude-sonnet-5
inspect eval tasks/commission.py --model pplx_agent/sonar-pro \
    -T judge=openai/gpt-5.6
```

**Confirmed current model strings (verified via web search, Sept 2026):**
- `anthropic/claude-sonnet-5` — Claude Sonnet 5's API model ID has no
  date suffix (unlike earlier Claude generations) — confirmed across
  Anthropic's own Bedrock docs and multiple third-party API references.
- `openai/gpt-5.6` — confirmed as a currently valid, directly-usable
  model string in OpenAI's own developer documentation examples.
- `pplx_agent/sonar-pro` — NOT `perplexity/sonar-pro`. Perplexity's
  Sonar Chat Completions API sunsets September 27, 2026; see the custom
  provider note above. The `sonar-pro` name is mapped internally to the
  Agent API's `low` preset, per Perplexity's own suggested mapping.
- `google/gemini-3.1-pro-preview` — Gemini's pro-tier naming has
  churned fast: `gemini-3-pro-preview` was deprecated March 9, 2026,
  replaced by `gemini-3.1-pro-preview`. Given this pace of change,
  **check Google's current model list immediately before running** --
  this string may already be stale by the time you run the eval, more
  so than the other three providers.

## Viewing results

```bash
inspect view
```

Opens Inspect's built-in results viewer — shows per-item scores,
judge reasoning traces, and aggregate accuracy/stderr per scorer.

## Extending the dataset

Add new items to `data/items.json` following the existing schema
(`id`, `arm`, `category`, `input`, `source_doc`). No code changes needed
— both task files load the full dataset and filter by `arm`
automatically. Current count: 4 omission + 4 commission items (the
Phase 2 pilot batch). Target for the full pilot is 15-30 per arm per
the project doc.

## Notes on the two scorer types

- `consideration.py` and `scope.py` use Inspect's built-in
  `model_graded_qa()`, since both dimensions are binary and map onto
  Inspect's CORRECT/INCORRECT grading pattern.
- `accountability.py` and `fairness.py` are custom scorers (Inspect
  supports this natively), since both are 0/1/2 ordinal scales with
  qualitatively distinct levels, not "more or less correct" — a shape
  `model_graded_qa()` isn't built for.
- `transparency` (cross-cutting, per the project doc) is not yet
  implemented here — it applies conditionally (only when a citation is
  present) and needs a scorer that can emit "N/A" distinct from a 0/1
  score. Build this the same way as accountability/fairness once the
  first two arms are validated.
