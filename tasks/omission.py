"""
Bearclaw-Omission task.

Run per evaluated model, with the judge model set via -T judge=..., per
the judge-assignment table in the project doc (§3f):

    inspect eval tasks/omission.py --model openai/gpt-5.6 \
        -T judge=anthropic/claude-sonnet-5

    inspect eval tasks/omission.py --model anthropic/claude-sonnet-5 \
        -T judge=openai/gpt-5.6

    inspect eval tasks/omission.py --model google/gemini-3.1-pro-preview \
        -T judge=anthropic/claude-sonnet-5
    inspect eval tasks/omission.py --model google/gemini-3.1-pro-preview \
        -T judge=openai/gpt-5.6

    (repeat both judge runs for the Perplexity model once its provider
    wrapper is set up -- see README)
"""

from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, json_dataset
from inspect_ai.solver import generate

import providers.perplexity_agent  # noqa: F401 -- registers the pplx_agent provider
from scorers.consideration import consideration_scorer
from scorers.scope import scope_scorer
from scorers.transparency import transparency_scorer


def _omission_only(sample):
    return sample.metadata.get("arm") == "omission"


@task
def bearclaw_omission(judge: str = "anthropic/claude-sonnet-5"):
    dataset = json_dataset(
        "../data/items.json",
        sample_fields=FieldSpec(
            input="input",
            id="id",
            metadata=["arm", "category", "source_doc"],
        ),
    )
    dataset = dataset.filter(_omission_only)

    return Task(
        dataset=dataset,
        solver=[generate()],
        scorer=[
            consideration_scorer(judge_model=judge),
            scope_scorer(judge_model=judge),
            transparency_scorer(judge_model=judge),
        ],
    )
