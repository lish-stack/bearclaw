"""
Standalone case-study task -- the Romanch's Law (Intro 943) carriage-horse
opposition testimony item, used for the "BEARCLAW in Action" demo section.

Kept deliberately separate from tasks/commission.py and data/items.json (the
8-item published pilot dataset already on Hugging Face) so running this does
NOT affect the published dataset or leaderboard numbers -- this is a live,
illustrative example, not new pilot data added retroactively.

Run pattern is identical to tasks/commission.py -- see that file's docstring,
and run_pplx.py's docstring, for the full set of per-model/per-judge
invocations. Example:

    inspect eval tasks/case_study.py --model anthropic/claude-sonnet-5 \
        -T judge=openai/gpt-5.6

    python run_pplx.py eval tasks/case_study.py --model pplx_agent/sonar-pro \
        -T judge=anthropic/claude-sonnet-5
    python run_pplx.py eval tasks/case_study.py --model pplx_agent/sonar-pro \
        -T judge=openai/gpt-5.6
"""

from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, json_dataset
from inspect_ai.solver import generate

import providers.perplexity_agent  # noqa: F401 -- registers the pplx_agent provider
from scorers.accountability import accountability_scorer
from scorers.fairness import fairness_scorer
from scorers.transparency import transparency_scorer


@task
def bearclaw_case_study(judge: str = "anthropic/claude-sonnet-5"):
    dataset = json_dataset(
        "../data/case_study_items.json",
        sample_fields=FieldSpec(
            input="input",
            id="id",
            metadata=["arm", "category", "source_doc"],
        ),
    )

    return Task(
        dataset=dataset,
        solver=[generate()],
        scorer=[
            accountability_scorer(judge_model=judge),
            fairness_scorer(judge_model=judge),
            transparency_scorer(judge_model=judge),
        ],
    )
