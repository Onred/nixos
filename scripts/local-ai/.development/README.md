# Development checks

These files are excluded from the installed runtime. Run with the module's Python
environment (httpx, mcp, playwright, tomlkit, trafilatura); no system changes needed:

```console
python -B -m unittest discover -s scripts/local-ai/.development -p 'test*.py' -q
python -B scripts/local-ai/.development/evaluate_effectiveness.py --output /tmp/evaluation.json
python -B scripts/local-ai/.development/check_search.py
```

Unit tests use isolated fixtures and mocked services. Set
`LOCAL_GEMMA_LIVE_TESTS=1` for the optional real-Gemma search selection test.
The effectiveness evaluation uses local inference but no public search engine;
`check_search.py` is the separate opt-in live SearXNG check. Do not rerun blocked
upstream engines as part of normal regression testing.

Latest evaluation (2026-09-29): all 12 expected-evidence checks retained the target
evidence. The five primary substantial-output scenarios reduced returned bytes
by 87–99.8%: repeated logs, timestamped logs, a real unittest failure, repository
search with distractors, and report comparison. Short outputs still have wrapper
and schema overhead, so normal direct reads remain preferable. These are bounded
fixture checks, not a statistical production reliability estimate or measured
frontier-token savings. The separate effectiveness tests include different error
messages, a cause in the middle of candidates, long-line paging, clock-only log
changes, and an empty Gemma selection.

Detailed baseline and new results live outside this system repository under
`~/.local/state/local-gemma/evaluations/`. The evaluation's byte accounting includes
capture facts plus the reporting response, or two capture facts for comparisons;
it excludes tool schema, arguments, transport and reasoning. Production runner
summaries return in one call; `--facts-only` supports explicit follow-up filtering.

Packaged integration: all nine MCP call interfaces checked; the default runner
returned a real exception in 756 bytes versus approximately 66 KB raw output.
Serialized tool schemas fell from 6,486 to 5,576 bytes (14%). The full NixOS build
passed. Default suite: 53 passed, one optional live test skipped; the separate
live web-evidence suite passed all 29 tests including real Gemma selection.
