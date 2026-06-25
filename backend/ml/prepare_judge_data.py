"""
Build judge-model training data from enriched Q&A.

Creates (question, answer) → 5 scores in [0, 1]:
  relevance, correctness, depth, communication, structure

Uses pseudo-labels: reference answers score high; synthetic weak answers score low.
Also adds MiniLM semantic relevance when available.
"""

from __future__ import annotations

import json
import os
import random
import re
from typing import Dict, List

DIMS = ["relevance", "correctness", "depth", "communication", "structure"]


def _word_overlap(q: str, a: str) -> float:
    qw = set(re.findall(r"[a-z0-9]+", q.lower()))
    aw = set(re.findall(r"[a-z0-9]+", a.lower()))
    if not qw:
        return 0.5
    return len(qw & aw) / len(qw)


def _semantic_relevance(q: str, a: str) -> float:
    try:
        from nlp_service import _semantic_relevance
        s = _semantic_relevance(q, a)
        if s is not None:
            return max(0.0, min(1.0, float(s)))
    except Exception:
        pass
    return _word_overlap(q, a)


def _score_answer(question: str, answer: str, round_type: str) -> Dict[str, float]:
    rel = _semantic_relevance(question, answer)
    wc = len(answer.split())
    depth = min(1.0, wc / 120.0)
    if wc < 15:
        depth = min(depth, 0.35)
    sents = max(1, len(re.split(r"[.!?]+", answer)))
    communication = min(1.0, 0.4 + 0.15 * min(sents, 4))
    if wc < 8:
        communication = 0.15

    structure = 0.5
    al = answer.lower()
    if round_type == "hr" and any(k in al for k in ("situation", "task", "action", "result", "star")):
        structure = 0.9
    elif any(k in al for k in ("time o(", "space o(", "approach", "step", "first", "then")):
        structure = 0.85
    elif "requirements" in al and ("scale" in al or "api" in al):
        structure = 0.88

    correctness = min(1.0, 0.35 * rel + 0.35 * depth + 0.3 * structure)
    if wc < 5:
        correctness = 0.1

    return {
        "relevance": round(rel, 4),
        "correctness": round(correctness, 4),
        "depth": round(depth, 4),
        "communication": round(communication, 4),
        "structure": round(structure, 4),
    }


def _weak_answer(question: str, kind: str) -> str:
    if kind == "empty":
        return "I don't know."
    if kind == "short":
        return "Yes, maybe using a hash map."
    if kind == "offtopic":
        return "I enjoy playing cricket and watching movies on weekends with friends."
    return question[:40] + " — not sure."


def build_training_rows(records: List[dict], seed: int = 42) -> List[dict]:
    rng = random.Random(seed)
    rows: List[dict] = []

    for rec in records:
        q = rec["question"]
        rt = rec.get("round_type", "general")
        ref = rec.get("answer", "")
        if not ref:
            continue

        scores = _score_answer(q, ref, rt)
        rows.append({
            "question": q,
            "answer": ref,
            "company": rec.get("company", ""),
            "round_type": rt,
            "labels": scores,
            "quality": "reference",
        })

        for kind in ("short", "offtopic", "empty"):
            if rng.random() < 0.35:
                weak = _weak_answer(q, kind)
                ws = _score_answer(q, weak, rt)
                for k in ws:
                    ws[k] = round(ws[k] * 0.45, 4)
                rows.append({
                    "question": q,
                    "answer": weak,
                    "company": rec.get("company", ""),
                    "round_type": rt,
                    "labels": ws,
                    "quality": f"weak_{kind}",
                })

    rng.shuffle(rows)
    return rows


def split_and_save(rows: List[dict], out_dir: str, val_ratio: float = 0.1) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    n_val = max(200, int(len(rows) * val_ratio))
    val = rows[:n_val]
    train = rows[n_val:]

    for name, data in [("train", train), ("val", val)]:
        path = os.path.join(out_dir, f"judge_{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {"train": len(train), "val": len(val), "total": len(rows), "dims": DIMS}
    with open(os.path.join(out_dir, "judge_data_manifest.json"), "w") as f:
        json.dump(stats, f, indent=2)
    return stats


def main(jsonl_path: str, out_dir: str):
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    rows = build_training_rows(records)
    stats = split_and_save(rows, out_dir)
    print(f"Judge training data: {stats['train']} train, {stats['val']} val ({stats['total']} total)")
