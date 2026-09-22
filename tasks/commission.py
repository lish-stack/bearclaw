"""
Bearclaw-Commission task. Same run pattern as omission.py -- see that
file's docstring for the full set of inspect eval invocations per the
judge-assignment table.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, json_dataset
from inspect_ai.solver import generate

import providers.perplexity_agent  # noqa: F401 -- registers the pplx_agent provider
from scorers.accountability import accountability_scorer
from scorers.fairness import fairness_scorer
from scorers.transparency import transparency_scorer


def _commission_only(sample):
    return sample.metadata.get("arm") == "commission"


@task
def bearclaw_commission(judge: str = "anthropic/claude-sonnet-5"):
    dataset = json_dataset(
        "../data/items.json",
        sample_fields=FieldSpec(
            input="input",
            id="id",
            metadata=["arm", "category", "source_doc"],
        ),
    )
    dataset = dataset.filter(_commission_only)

    return Task(
        dataset=dataset,
        solver=[generate()],
        scorer=[
            accountability_scorer(judge_model=judge),
            fairness_scorer(judge_model=judge),
            transparency_scorer(judge_model=judge),
        ],
    )
