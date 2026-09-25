# Gemma evidence tools for Codex

`modules/local-ai/local-model-tools.nix` packages this stdio MCP server, runs
SearXNG at `127.0.0.1:8888`, and registers `local_gemma` in the user's Codex config.
There are no paid search APIs, cloud model calls, or additional public ports.
Search queries and page requests do reach the selected public websites.

## Activation

Build and activate the NixOS configuration, then restart Codex. A reboot after
`nixos-rebuild boot --flake .#nixos` also activates it. Merely restarting Codex
without activating the NixOS changes does not install the service.

`local-gemma-codex-setup.service` merges only `mcp_servers.local_gemma` into
`/home/onred/.codex/config.toml` and a marked guidance section into the global
`AGENTS.md`. Other models, providers, MCP entries and instructions are preserved.
The first originals are backed up beside those files with a
`.before-local-gemma` suffix, mode 0600. Symlink-managed configuration is rejected
instead of replaced. Change the module or `codex-guidance.md` to change the
managed settings; future activations restore this managed section.

After activation, check:

```console
systemctl status local-gemma-codex-setup searx ollama-model-loader
codex mcp list
```

In a new Codex session, `/mcp` should list `local_gemma`. Ask it to search for a
public technical topic, extract evidence from one result, and inspect a local
project file. Verify citations, source excerpts, coverage and GPU usage. The
model loader must finish downloading Gemma before evidence selection works.
Live inference, search-engine availability, browser access, and Codex's routing
decisions require this post-activation check; an offline build cannot prove them.

## Tools and limits

| Tool | Behavior |
| --- | --- |
| `search_web(query, fresh=false)` | Up to five SearXNG links/snippets; no inference |
| `read_web(url, question, fresh=false)` | Retrieve a page, then select exact passages using Gemma |
| `extract_evidence(paths, question)` | Select exact passages from 1–5 explicit UTF-8 project files |

Only `gemma4:12b-it-qat` is used. It runs at 16K context, with thinking disabled
and a small output budget because it only selects passage IDs. Python resolves
those IDs to original text; it does not trust model-generated quotations. The
returned lines are literal file lines or lines in the extracted web-page text.
This validates the quotes, not the relevance or completeness of the selection.

The server first ranks four-line blocks against the question, then supplies at
most 30 blocks / 11 KB plus small metadata to Gemma. It returns at most four
excerpts totaling 4 KB. Coverage reports excluded blocks and oversized lines.
Ask focused questions; a missing finding is not evidence that a problem does
not exist. Files larger than 512 KB are rejected, not silently truncated.

Allowed local roots are `/home/onred/nixos` and `/home/onred/Projects`, configured
in the module's MCP arguments. Resolved paths outside them and common credential
paths are rejected. The process runs as the user, not in Codex's shell sandbox;
the allowlist is intentionally narrower than the home directory. Do not send
credentials in otherwise allowed source files. Source content is untrusted data.

Web fetches accept public HTTP(S) URLs on standard ports, check DNS destinations
and redirects, and reject private/reserved addresses. These are application-level
checks, not a hardened network sandbox against hostile DNS rebinding. Requests
are bounded to 2 MB for direct HTTP; rendered HTML is checked after rendering.
Only HTML and plain text are supported; PDF and other document types fail explicitly.

HTTP retrieval comes first. An empty JavaScript page, an access-challenge page,
or HTTP 403 gets at most one isolated Chromium attempt. The browser uses no
personal profile, blocks downloads, service workers, non-GET/HEAD requests and
unneeded media, and limits subrequests. HTTP 401/429 and unresolved challenges
return errors. It does not solve CAPTCHAs, sign in, or bypass paywalls.

Search/page cache lifetimes are five/fifteen minutes. `fresh=true` bypasses them.
The private cache in `~/.cache/local-gemma` retains at most 100 web entries, with
entries older than a day removed during writes. Local file text and Gemma prompts
are not cached. Cross-process locks serialize web retrieval and Gemma inference;
busy calls fail promptly. A different loaded Ollama model is not evicted by the
tool (other clients can still race independently). Gemma expires after two idle
minutes. Active generation can still affect gaming performance.

## Usage policy and verification

`codex-guidance.md` teaches Codex to use these tools for large unread inputs,
prefer deterministic search for small tasks, keep final judgment in the frontier
model, and stop after one failed local attempt. They are not coding subagents.
Automatic tool choice is model behavior guided by these instructions, not a
guarantee that every request will use Gemma. Specialist documentation tools and
higher-priority instructions still take precedence.

`test_model_tools.py` uses temporary files and mocked HTTP/Ollama responses to
check path restrictions, exact references, bounds, cache eviction, request
serialization, redirect checks, browser fallback policy and idempotent Codex
registration. It never calls a live model or website. Run it using the module's
Python environment with `python -B -m unittest discover -s scripts/local-ai -v`.

Before extending delegation, compare representative tasks with and without the
tools. Count all frontier input/output and repair work, missed evidence, and wall
time. `local_usage` reports local inference tokens; it does not measure frontier
subscription savings.

To disable the integration, remove the module import and apply the configuration,
then remove `mcp_servers.local_gemma` and the marked guidance block from Codex.
Do not restore whole backup files over newer unrelated edits.
