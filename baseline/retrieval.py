"""Question/turn-only BM25. No answer or gold-evidence arguments."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def documents(conversation: dict) -> list[dict]:
    result = []
    session_keys = sorted((k for k, v in conversation.items()
                           if re.fullmatch(r"session_\d+", k) and isinstance(v, list)),
                          key=lambda k: int(k.split("_")[1]))
    for key in session_keys:
        date = conversation.get(key + "_date_time")
        if not date:
            raise ValueError(f"Missing session date: {key}")
        heading = f"=== SESSION {int(key.split('_')[1])} | {date} ==="
        for turn in conversation[key]:
            if not turn.get("dia_id") or not turn.get("speaker"):
                raise ValueError("Missing turn ID or speaker")
            content = str(turn.get("text", "")).strip()
            if turn.get("blip_caption"):
                content += f" [Shared-image caption: {str(turn['blip_caption']).strip()}]"
            text = f"{heading}\n[{turn['dia_id']}] {turn['speaker']}: {content}"
            result.append({"index": len(result), "turn_id": turn["dia_id"],
                           "text": text})
    if len({d['turn_id'] for d in result}) != len(result):
        raise ValueError("Duplicate turn IDs")
    return result


def rank(question: str, docs: list[dict], k1: float = 1.5, b: float = .75) -> list[dict]:
    if not docs:
        raise ValueError("Empty conversation")
    tokenize = lambda text: re.findall(r"[A-Za-z0-9]+", text.lower())
    tokens = [tokenize(d["text"]) for d in docs]
    df = Counter(t for row in tokens for t in set(row))
    avg = sum(map(len, tokens)) / len(tokens)
    query = list(dict.fromkeys(tokenize(question)))
    scored = []
    for doc, ts in zip(docs, tokens):
        counts = Counter(ts)
        value = 0.0
        for term in query:
            f = counts[term]
            if f:
                idf = math.log(1 + (len(docs) - df[term] + .5) / (df[term] + .5))
                value += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(ts) / max(avg, 1)))
        scored.append({**doc, "bm25_score": value})
    return sorted(scored, key=lambda d: (-d['bm25_score'], d['index']))


def canonical(docs: list[dict]) -> str:
    return "\n\n".join(d["text"] for d in sorted(docs, key=lambda d: d['index']))


def select(question: str, docs: list[dict], k: int = 16) -> dict:
    selected = sorted(rank(question, docs)[:k], key=lambda d: d['index'])
    text = canonical(selected)
    return {"selected_turn_ids": [d["turn_id"] for d in selected],
            "evidence": text, "evidence_sha256": sha_text(text),
            "selection_scores": [d["bm25_score"] for d in selected]}


def pack_matched(question: str, docs: list[dict], processed_chat_count, target: int) -> dict:
    """Count the actual complete chat for each candidate, with frozen processor."""
    kept = []
    for doc in rank(question, docs):
        candidate = canonical(kept + [doc])
        if processed_chat_count(candidate) <= target:
            kept.append(doc)
    if not kept:
        raise ValueError("No whole retrieval turn fits the complete-input budget")
    text = canonical(kept)
    return {"evidence": text, "evidence_sha256": sha_text(text),
            "selected_turn_ids": [d['turn_id'] for d in sorted(kept, key=lambda d: d['index'])],
            "total_input_tokens": processed_chat_count(text), "target": target}
