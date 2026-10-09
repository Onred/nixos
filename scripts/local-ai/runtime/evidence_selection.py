"""Select exact document passages with explicit coverage and source coordinates."""

import json
from tool_config import INPUT_BYTES, MODEL
from gemma_client import gemma_select, selected_ids
from candidate_selection import ranked_candidates


def candidates(
    documents: list[tuple[str, str]], question: str
) -> tuple[list[dict], dict]:
    blocks = []
    split_lines = 0
    for source, text in documents:
        lines = text.splitlines()
        for start in range(0, len(lines), 4):
            excerpt = "\n".join(lines[start : start + 4])
            if not excerpt.strip():
                continue
            if len(excerpt.encode()) <= 1800:
                blocks.append(
                    {
                        "source": source,
                        "start_line": start + 1,
                        "end_line": min(start + 4, len(lines)),
                        "text": excerpt,
                    }
                )
            else:
                for number, line in enumerate(lines[start : start + 4], start + 1):
                    if len(line.encode()) > 1800:
                        split_lines += 1
                    for column in range(0, len(line), 400):
                        blocks.append(
                            {
                                "source": source,
                                "start_line": number,
                                "end_line": number,
                                "start_column": column + 1,
                                "text": line[column : column + 400],
                            }
                        )
    chosen = ranked_candidates(blocks, question, budget=INPUT_BYTES)
    return chosen, {
        "source_count": len(documents),
        "candidate_blocks": len(chosen),
        "total_blocks": len(blocks),
        "long_lines_split": split_lines,
        "partial": len(chosen) < len(blocks),
    }


def selected_evidence(answer: str, blocks: list[dict]) -> list[dict]:
    evidence = []
    used = 0
    for index in selected_ids(answer, len(blocks), 4):
        block = blocks[index]
        if used + len(block["text"].encode()) > 4000:
            continue
        evidence.append({key: value for key, value in block.items() if key != "id"})
        used += len(block["text"].encode())
    return evidence


async def extract(documents: list[tuple[str, str]], question: str) -> dict:
    if not question.strip() or len(question.encode()) > 1000:
        raise ValueError("Provide a focused question of at most 1000 UTF-8 bytes")
    if sum(len(text.encode()) for _, text in documents) <= 1800:
        return {
            "status": "ok",
            "selection": "direct",
            "evidence": [
                {
                    "source": source,
                    "start_line": 1,
                    "end_line": len(text.splitlines()),
                    "text": text,
                }
                for source, text in documents
            ],
            "coverage": {"partial": False},
        }
    blocks, coverage = candidates(documents, question)
    if not blocks:
        return {"status": "insufficient_evidence", "coverage": coverage, "evidence": []}
    payload = [{"id": block["id"], "text": block["text"]} for block in blocks]
    result = await gemma_select(
        payload,
        question,
        "Select up to four passage IDs that directly help answer the focused question. "
        "Prefer explicit statements about the requested identifiers. An example value is not proof of a default. "
        "Do not select merely related passages when explicit evidence is requested.",
        4,
    )
    evidence = selected_evidence(json.dumps({"selected": result["selected"]}), blocks)
    return {
        "status": "ok" if evidence else "insufficient_evidence",
        "model": MODEL,
        "evidence": evidence,
        "coverage": coverage,
        "selection": "gemma",
        "local_usage": result["local_usage"],
    }
