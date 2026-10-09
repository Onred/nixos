# Local evidence tools

This NixOS module provides a command-output wrapper and nine read-only Codex MCP
tools. The frontier chooses commands, permissions, diagnosis and edits. Local
`gemma4:12b-it-qat` only selects exact source excerpts; it never executes commands
or generates replacement evidence.

## Use

Use normal shell/rg reads for short output and exact lookups. For verbose commands:

```console
local-run-report --cwd /absolute/project --timeout 120 -- COMMAND ARG...
local-run-report --cwd /absolute/project --report results.xml -- pytest --junitxml=results.xml
```

The runner returns status plus small output, diagnostic context, or recognized
validation results **in one response**. The artifact ID is `process.id`. Inspect
again only when the returned evidence is insufficient. Use `--facts-only` when you
already intend to call `filter_log` or `compare_reports`, avoiding duplicate output.
Shell syntax requires an explicitly chosen shell (`-- bash -c '...'`), through the
normal approval path. Interactive commands should use the normal terminal.

| Tool / source file in `runtime/` | When useful |
| --- | --- |
| `run_report.py` (`local-run-report`) | Capture verbose command output and immediately summarize it |
| `inspect_run.py` | Recover status, error context and tails from an existing run |
| `validation_report.py` | Test/lint counts and actual failure details |
| `filter_log.py` | Repeated logs, literal filtering, focused evidence selection |
| `search_repository.py` | Many project matches; optional focused question |
| `compare_reports.py` | Before/after outcomes and diagnostic occurrence counts |
| `read_artifact.py` | Omitted lines or bytes without rerunning a command |
| `search_web.py` | Public discovery through SearXNG and Gemma |
| `read_web.py` | Focused passages from a public HTML/text page |
| `extract_evidence.py` | Focused passages from 1–5 explicit project files |

Small documents/results bypass inference. Larger candidate sets reserve space for
errors, different sources and distributed source locations as well as lexical
matches. Model selection remains incomplete. Log/repository tools retain a small
number of high-priority diagnostics independently of Gemma. Coverage, omitted
counts and truncation flags describe what was left out.

Log grouping and comparisons ignore leading ISO timestamps and ANSI formatting;
other values are preserved. Grouped excerpts retain original text and first/last
line references. Validation supports JUnit, pytest-json-report, Ruff JSON, and
standard pytest/unittest console summaries. Unknown formats remain unknown;
zero tests and all-skipped are distinct outcomes. Explicit report snapshots can
be stale, so their outcomes remain provisional until provenance is checked.

`read_artifact` accepts `contains`, `start_line`, and `line_count`. Long excerpts
include byte offsets: use `byte_offset=next_byte` to recover the remainder.
Repository matches retain full text in the `matches` artifact stream; response
paths are relative to the returned `root`. Document excerpts can include
`start_column` for long source lines. Do not treat missing selections as absence.

## Limits and storage

Commands default to 120 seconds and 32 MiB combined output. A timeout/output cap
kills the command's process group and reports incomplete capture. The wrapper
preserves child exit codes; timeout/cap/capture errors use 124/125/126, with JSON
fields distinguishing them from child codes. Deliberately detached children are
outside its process group; use this for finite commands, not starting services.

Private run artifacts live in `~/.cache/local-gemma/artifacts` (or under
`XDG_CACHE_HOME`). They persist until their run-ID directories are removed. Avoid
capturing secrets. Inspection scans at most 8 MiB per stream; artifact paging can
read beyond that window. Runner and MCP must share the same cache directory.
Repository search uses fixed rg options, no user rg config, no symlink following,
and excludes ignored/hidden files and common credential paths. Allowed project
roots are configured in the Nix module. These are read restrictions, not an OS
sandbox for the MCP process.

Search retrieval stays entirely in SearXNG; there is no paid or host-search
fallback. Use a few distinctive terms and `domains=["example.com"]` when needed.
Check degraded/failed engines and fetch pages before citing search snippets.
`fresh=true` bypasses five-minute search or fifteen-minute page caches. Challenges
and upstream failures are reported, not interpreted as no matching sources.
The module backports the pinned upstream Google CSE web adapter. Public search
providers can still rate-limit or change behavior.

Web fetches check public destinations and redirects, limit HTTP retrieval to
2 MB, and permit one isolated Chromium fallback for eligible page failures.
They do not solve CAPTCHAs or sign in. Only HTML/text is supported. Busy inference
fails promptly; another loaded Ollama model is never evicted. Web cache writes
retain at most 100 entries for a day. These controls do not prevent hostile DNS
rebinding or isolate other GPU clients.

## Activation and layout

Build/apply the NixOS configuration and restart Codex. The registration service
merges only `mcp_servers.local_gemma` and its marked guidance block, preserving
other settings and backing up the first originals. Future activation restores
managed settings from this directory. The user-level runner, when registered
before a system switch, is at
`~/.local/state/local-gemma/runner/bin/local-run-report`.

`runtime/` contains the installed code, with one file per public tool and explicit
shared helpers. `server.py` registers the MCP tools. `register_codex.py` and
`codex-guidance.md` manage integration. Development tests and checks are tucked
under `.development/` and are **not included in the runtime package**. Detailed
benchmark outputs are kept outside the repository in the user's local state.
