"""SearXNG-only search with local Gemma result selection."""

import asyncio
import hashlib
import json
import re
from urllib.parse import urlsplit
import httpx
from mcp.types import ToolAnnotations
from tool_config import (
    mcp,
    SEARX,
    INPUT_BYTES,
    MODEL,
    now,
    cache_get,
    cache_put,
    exclusive,
    bounded,
)
from gemma_client import gemma_select


def search_scope(query: str, domains: list[str] | None) -> tuple[str, list[str]]:
    if not query.strip() or len(query) > 500:
        raise ValueError("Query must contain 1–500 characters")
    if re.search(r"(?<!\S)site[.]\S+", query, re.IGNORECASE):
        raise ValueError(
            "Malformed site operator: use site:example.com or the domains argument, not site.example.com"
        )
    sites = re.findall(r"(?<!\S)site:([^\s]+)", query, re.IGNORECASE)
    if domains and sites:
        raise ValueError("Use domains or site: operators, not both")
    scope = domains or sites
    if len(scope) > 5:
        raise ValueError("Supply at most five domains")
    normalized = []
    for domain in scope:
        host = domain.lower().rstrip(".").encode("idna").decode("ascii")
        if len(host) > 253 or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+",
            host,
        ):
            raise ValueError(
                "Domains must be hostnames, not URLs, paths, ports, or wildcards"
            )
        normalized.append(host)
    normalized = sorted(set(normalized))
    if domains:
        restriction = " OR ".join(f"site:{host}" for host in normalized)
        query = (
            f"({restriction}) {query}"
            if len(normalized) > 1
            else f"{restriction} {query}"
        )
    return query, normalized


def search_candidates(items: list[dict], domains: list[str]) -> tuple[list[dict], dict]:
    selected, seen = [], set()
    used = rejected = eligible = 0
    for item in items:
        url = item.get("url", "")
        try:
            parsed = urlsplit(url)
            host = (
                (parsed.hostname or "")
                .lower()
                .rstrip(".")
                .encode("idna")
                .decode("ascii")
            )
        except ValueError:
            continue
        if (
            not host
            or parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or len(url) > 2000
            or url in seen
        ):
            continue
        seen.add(url)
        if domains and not any(
            host == domain or host.endswith("." + domain) for domain in domains
        ):
            rejected += 1
            continue
        eligible += 1
        candidate = {
            "id": len(selected),
            "title": item.get("title", "")[:200],
            "url": url,
            "snippet": item.get("content", "")[:450],
            "engines": [str(engine)[:40] for engine in item.get("engines", [])[:8]],
        }
        size = len(json.dumps(candidate, ensure_ascii=False).encode())
        if len(selected) < 20 and used + size <= INPUT_BYTES:
            selected.append(candidate)
            used += size
    return selected, {
        "received": len(items),
        "domain_rejected": rejected,
        "eligible": eligible,
        "considered": len(selected),
        "partial": len(selected) < eligible,
        "candidate_bytes": used,
    }


async def select_results(
    items: list[dict],
    query: str,
    scope: list[str],
    failures: list,
    retrieval: str,
    retrieved_at: str,
) -> dict:
    candidates, coverage = search_candidates(items, scope)
    selection = None
    if candidates:
        selection = await gemma_select(
            candidates,
            query,
            "Select up to five search-result IDs most useful for the specific query, best first. "
            "Prefer primary sources and complementary results over duplicates. Reject unrelated results "
            "even if they share a generic keyword. Select fewer results when sufficient; do not fill a quota. "
            "Snippets are discovery leads, not verified facts.",
            5,
        )
    results = (
        [
            {key: value for key, value in candidates[index].items() if key != "id"}
            for index in selection["selected"]
        ]
        if selection
        else []
    )
    coverage["returned"] = len(results)
    coverage["result_bytes"] = len(json.dumps(results, ensure_ascii=False).encode())
    status = (
        "ok" if results else ("no_relevant_results" if candidates else "no_results")
    )
    if not candidates and failures:
        status = "upstream_unavailable"
    output = {
        "status": status,
        "results": results,
        "retrieved_at": retrieved_at,
        "domains": scope,
        "retrieval": retrieval,
        "degraded": bool(failures),
        "failed_engines": failures,
        "coverage": coverage,
        "model": MODEL if selection else None,
        "local_usage": selection["local_usage"] if selection else None,
        "warning": "Discovery leads; fetch pages before citing.",
    }
    if not results:
        output["next_step"] = (
            "SearXNG did not supply useful candidates. Report the retrieval limitation; "
            "do not infer that no matching sources exist. Do not retry blocked engines or use a paid or host search fallback."
        )
    return output


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=True
    )
)
async def search_web(
    query: str, fresh: bool = False, domains: list[str] | None = None
) -> dict:
    """Search SearXNG; Gemma selects up to five links. domains enforces host restrictions; fresh bypasses cached selections. Check degraded/coverage; snippets are unverified leads. No host-search fallback."""

    async def work():
        effective_query, scope = search_scope(query, domains)
        key = (
            "search-gemma-v5:"
            + hashlib.sha256(json.dumps([effective_query, scope]).encode()).hexdigest()
        )
        cached = None if fresh else cache_get(key, 300)
        if cached:
            return {**cached, "cached": True}
        try:
            async with exclusive("web"):
                await asyncio.sleep(1)
                async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
                    response = await client.get(
                        SEARX,
                        params={
                            "q": effective_query,
                            "format": "json",
                            "categories": "general",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            output = await select_results(
                [],
                query,
                scope,
                [["searxng", str(error)[:200] or type(error).__name__]],
                "searxng",
                now(),
            )
            return {**output, "cached": False}
        output = await select_results(
            data.get("results", []),
            query,
            scope,
            data.get("unresponsive_engines", [])[:8],
            "searxng",
            now(),
        )
        if output["results"]:
            cache_put(key, output)
        return {**output, "cached": False}

    return await bounded(work())
