"""Deterministic error priorities, exact excerpts, and failure context."""

import re

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ERROR = re.compile(
    r"\b(?:error|fatal|panic|fail(?:ed|ure)?|exception|traceback|segmentation fault|permission denied|connection refused|ECONN\w*|ENOENT|ENOSPC|OOM)\b|\b\w+(?:Error|Exception):|^E\s+",
    re.I,
)
WARNING = re.compile(r"\bwarn(?:ing)?\b", re.I)
DIAGNOSTIC = re.compile(ERROR.pattern + "|" + WARNING.pattern, re.I)
TIMESTAMP = re.compile(
    r"^\[?\d{4}-\d\d-\d\d[T ]\d\d:\d{2,3}:\d\d(?:[.,]\d+)?(?:Z|[+-]\d\d:\d\d)?\]?\s+"
)


def severity(text):
    text = ANSI.sub("", text)
    return 2 if ERROR.search(text) else 1 if WARNING.search(text) else 0


def excerpt(line, width=900):
    if len(line) <= width:
        return {"text": line}
    # Keep the most diagnostic part and its exact column; never synthesize a quote.
    match = ERROR.search(line)
    start = max(0, match.start() - 100) if match and match.start() >= width else 0
    return {"text": line[start : start + width], "column": start + 1, "clipped": True}


def diagnostic_lines(text, limit=6):
    lines = text.splitlines()
    hits = [(i, severity(line)) for i, line in enumerate(lines) if severity(line)]
    # Recent errors outrank early warning floods; references retain original order.
    chosen = sorted(
        sorted(hits, key=lambda pair: (pair[1], pair[0]), reverse=True)[:limit]
    )
    return {
        "matched_lines": len(hits),
        "excerpts": [{"line": i + 1, **excerpt(lines[i])} for i, _ in chosen],
        "omitted_matches": max(0, len(hits) - limit),
        "scanned_lines": len(lines),
    }


def failure_context(text, limit=6, budget=3500):
    lines = text.splitlines()
    anchors = [i for i, line in enumerate(lines) if severity(line) == 2]
    selected = []
    used = 0
    for i in reversed(anchors):
        # A final exception needs the preceding source/stack lines; test headers need following detail.
        start = max(0, i - 3)
        end = min(len(lines), i + 3)
        if any(
            start <= item["end_line"] - 1 and end > item["start_line"] - 1
            for item in selected
        ):
            continue
        pieces = []
        clipped = False
        for line in lines[start:end]:
            part = excerpt(line, 600)
            pieces.append(part["text"])
            clipped |= part.get("clipped", False)
        value = "\n".join(pieces)
        if used + len(value.encode()) > budget:
            continue
        selected.append(
            {
                "start_line": start + 1,
                "end_line": end,
                "text": value,
                **({"clipped": True} if clipped else {}),
            }
        )
        used += len(value.encode())
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda x: x["start_line"])
