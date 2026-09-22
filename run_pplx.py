"""
Wrapper for running `inspect eval` with the custom pplx_agent provider
available.

WHY THIS EXISTS: Inspect resolves the --model argument BEFORE it loads
your task file (tasks/omission.py, tasks/commission.py). That means the
`import providers.perplexity_agent` line inside those files -- which
registers the custom pplx_agent provider -- runs too late to help; by the
time it would execute, Inspect has already tried and failed to find
"pplx_agent" and raised ValueError: Model API pplx_agent ... not recognized.

Inspect does have a plugin-discovery fallback for unrecognized providers,
but it only finds providers packaged as a properly *installed* Python
distribution declaring an "inspect_ai" entry point -- not a loose file in
this repo. Making providers/ a real installable package is the "proper"
long-term fix; this wrapper is the fast path that needs no packaging.

USAGE: identical to the `inspect` command, just run this file with python
instead of calling `inspect` directly:

    python run_pplx.py eval tasks/omission.py --model pplx_agent/sonar-pro \
        -T judge=anthropic/claude-sonnet-5

Only needed for pplx_agent. Claude, GPT-5.6, and Gemini all use Inspect's
own built-in providers and work fine with the normal `inspect eval ...`
command -- no need to use this wrapper for those.
"""

import sys

import providers.perplexity_agent  # noqa: F401 -- registers pplx_agent FIRST,
# before Inspect's CLI (imported below) gets anywhere near resolving --model

from inspect_ai._cli.main import main

if __name__ == "__main__":
    sys.exit(main())
