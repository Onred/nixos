"""Opt-in live SearXNG retrieval checks; no model inference or paid providers."""

import argparse
import json
import time
from urllib.parse import urlsplit

import httpx

CASES = [
    ("site:docs.python.org asyncio TaskGroup", "docs.python.org", "asyncio-task"),
    (
        "site:download.nvidia.com NVIDIA Linux suspend",
        "download.nvidia.com",
        "powermanagement",
    ),
    ("site:docs.searxng.org search API", "docs.searxng.org", "search_api"),
    ("site:wiki.nixos.org NVIDIA", "wiki.nixos.org", "NVIDIA"),
    ("site:docs.kernel.org runtime power management", "docs.kernel.org", "runtime_pm"),
    ("Python asyncio documentation", "docs.python.org", "asyncio"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8888/search")
    args = parser.parse_args()
    report = []
    with httpx.Client(timeout=25, trust_env=False) as client:
        for query, domain, expected_path in CASES:
            started = time.monotonic()
            try:
                response = client.get(
                    args.url,
                    params={"q": query, "format": "json", "categories": "general"},
                )
                response.raise_for_status()
                data = response.json()
                failures = data.get("unresponsive_engines", [])
                results = data.get("results", [])
                matches = [
                    item["url"]
                    for item in results
                    if urlsplit(item["url"]).hostname == domain
                    and expected_path.lower() in urlsplit(item["url"]).path.lower()
                ]
                entry = {
                    "query": query,
                    "seconds": round(time.monotonic() - started, 2),
                    "results": len(results),
                    "matches": matches[:2],
                    "failed_engines": failures,
                    "passed": bool(matches) and not failures,
                }
            except (httpx.HTTPError, ValueError) as error:
                entry = {"query": query, "passed": False, "error": str(error)}
                failures = ["retrieval failure"]
            report.append(entry)
            print(json.dumps(entry), flush=True)
            # Do not repeatedly probe blocked or broken providers.
            if failures:
                break
            time.sleep(1)
    passed = len(report) == len(CASES) and all(item["passed"] for item in report)
    print(
        json.dumps({"passed": passed, "completed": len(report), "planned": len(CASES)})
    )
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
