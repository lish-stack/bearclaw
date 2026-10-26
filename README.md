# BEARCLAW Harness

Evaluation harness for **BEARCLAW**, a pilot benchmark testing whether AI models surface animal-welfare considerations in civic and legal tasks (omission) and how they respond when asked to draft one-sided content with a welfare cost (commission). Built on [Inspect AI](https://inspect.aisi.org.uk/).

## Where things live

| | |
|---|---|
| **This repo** | Task definitions, scorers, rubrics, items, and run logs: everything needed to generate and score model responses |
| [Dataset](https://huggingface.co/datasets/considersentience/bearclaw-benchmark) | The published results: items, model responses, and judge scores |
| [Results site](https://bearclawpilot.considersentience.ai/) · [source](https://github.com/lish-stack/bearclaw-pilot) | Interactive presentation of the dataset |

Scored on the FACTS dimensions: Fairness, Accountability, Consideration, Transparency, Scope. The full construct, rubrics, and design decisions are in [`BEARCLAW_project_doc.md`](BEARCLAW_project_doc.md).

Pilot scale: 8 items (4 omission, 4 commission), 4 evaluated models, 2 judges.

## Layout

```
data/items.json          the 8 pilot items
data/case_study_items.json   standalone illustrative case study (not part of the dataset)
tasks/                   Inspect tasks: omission.py, commission.py, case_study.py
scorers/                 one scorer per FACTS dimension
providers/               custom Perplexity Agent API provider
run_pplx.py              wrapper for running Perplexity through that provider
logs/                    Inspect run logs (.eval)
```

## Setup

```bash
pip install -r requirements.txt
```

Set API keys as environment variables (never commit them):

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GOOGLE_API_KEY="..."
export PERPLEXITY_API_KEY="..."
```

Perplexity runs through the custom `pplx_agent` provider in this repo, which targets Perplexity's Agent API (`/v1/agent`). Use `pplx_agent/sonar-pro`, not the built-in `perplexity/` provider, which targets the retired Sonar Chat Completions endpoint. The provider is imported automatically by the task files.

## Running

Each evaluated model needs its own `inspect eval` run for each judge. A model is never judged by its own family: Claude is judged by GPT-5.6 only, GPT-5.6 by Claude only, and Gemini and Perplexity by both.

```bash
# Claude as evaluated model, GPT-5.6 as judge
inspect eval tasks/omission.py   --model anthropic/claude-sonnet-5 -T judge=openai/gpt-5.6
inspect eval tasks/commission.py --model anthropic/claude-sonnet-5 -T judge=openai/gpt-5.6

# GPT-5.6 as evaluated model, Claude as judge
inspect eval tasks/omission.py   --model openai/gpt-5.6 -T judge=anthropic/claude-sonnet-5
inspect eval tasks/commission.py --model openai/gpt-5.6 -T judge=anthropic/claude-sonnet-5

# Gemini: both judges
inspect eval tasks/omission.py   --model google/gemini-3.1-pro-preview -T judge=anthropic/claude-sonnet-5
inspect eval tasks/omission.py   --model google/gemini-3.1-pro-preview -T judge=openai/gpt-5.6
inspect eval tasks/commission.py --model google/gemini-3.1-pro-preview -T judge=anthropic/claude-sonnet-5
inspect eval tasks/commission.py --model google/gemini-3.1-pro-preview -T judge=openai/gpt-5.6

# Perplexity: both judges, via the custom provider
python run_pplx.py eval tasks/omission.py   --model pplx_agent/sonar-pro -T judge=anthropic/claude-sonnet-5
python run_pplx.py eval tasks/omission.py   --model pplx_agent/sonar-pro -T judge=openai/gpt-5.6
python run_pplx.py eval tasks/commission.py --model pplx_agent/sonar-pro -T judge=anthropic/claude-sonnet-5
python run_pplx.py eval tasks/commission.py --model pplx_agent/sonar-pro -T judge=openai/gpt-5.6
```

Model identifiers change quickly, especially Gemini's. Check each provider's current model list before running.

View results with `inspect view`.

## Scorers

- `consideration.py`, `scope.py`: binary, using Inspect's `model_graded_qa()`.
- `accountability.py`, `fairness.py`: custom 0/1/2 ordinal scorers.
- `transparency.py`: custom conditional scorer. It returns N/A when a response cites nothing to check, and reports accuracy over applicable items alongside the applicable rate, so N/A is never counted as a failure.

## Extending the dataset

Add items to `data/items.json` with `id`, `arm`, `category`, `input`, and `source_doc`. The task files load every item and filter by `arm`, so no code changes are needed. The planned next stage is 15–30 items per arm.
