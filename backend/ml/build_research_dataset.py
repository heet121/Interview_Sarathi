#!/usr/bin/env python3
"""
Build the research dataset: 2500+ company interview Q&A pairs.

Sorting matches grg124/Interview-Questions:
  company → round_type (telephonic, coding, dsa, system_design, …) → [{question, answer, …}]

Outputs (default: backend/data/research/v1/):
  manifest.json          — stats + version
  by_company/<Co>.json   — same section structure as GitHub READMEs
  interview_qa.jsonl     — flat file for ML training (one JSON object per line)
  index.json             — quick lookup: company → round_type → count

Usage:
  cd backend
  python -m ml.build_research_dataset
  python -m ml.build_research_dataset --min-rows 2500 --use-llm   # slower, richer answers
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List

# Allow running as script from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.github_parser import COMPANIES, fetch_all_github_questions
from ml.topic_banks import expansion_for_company
from ml.answer_generator import enrich_answers_batch

DEFAULT_OUT = os.path.join("data", "research", "v1")
MIN_ROWS_DEFAULT = 2500


def _norm_q(q: str) -> str:
    return " ".join((q or "").split()).strip().lower()


def _make_id(company: str, round_type: str, question: str) -> str:
    raw = f"{company}|{round_type}|{_norm_q(question)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _github_to_records(github_data: Dict[str, List[dict]]) -> List[dict]:
    records = []
    for company, sections in github_data.items():
        for sec in sections:
            rt = sec.get("round_type", "general")
            for q in sec.get("questions", []):
                records.append({
                    "id": _make_id(company, rt, q),
                    "company": company,
                    "round_type": rt,
                    "section_title": sec.get("section_title", ""),
                    "question": q.strip(),
                    "answer": "",
                    "answer_source": "",
                    "source": sec.get("source", "grg124/Interview-Questions"),
                    "difficulty": "medium",
                })
    return records


def _expand_to_minimum(records: List[dict], min_rows: int) -> List[dict]:
    seen = {(r["company"], _norm_q(r["question"])) for r in records}
    per_co = defaultdict(int)
    for r in records:
        per_co[r["company"]] += 1

    target_per_co = max(min_rows // len(COMPANIES), 80)
    for company in COMPANIES:
        have = per_co[company]
        need = max(0, target_per_co - have)
        if len(records) >= min_rows and need == 0:
            continue
        # Global gap fill
        global_need = min_rows - len(records)
        if global_need <= 0 and need <= 0:
            break
        take = max(need, 0)
        if len(records) < min_rows:
            take = max(take, (min_rows - len(records) + len(COMPANIES) - 1) // len(COMPANIES))
        pairs = expansion_for_company(company, take, seen)
        for rt, q in pairs:
            records.append({
                "id": _make_id(company, rt, q),
                "company": company,
                "round_type": rt,
                "section_title": rt.replace("_", " ").title(),
                "question": q,
                "answer": "",
                "answer_source": "",
                "source": "interview_sarathi/topic_banks",
                "difficulty": "medium",
            })
            if len(records) >= min_rows and per_co[company] + sum(
                1 for x in pairs if x[0] == rt
            ) >= target_per_co:
                break
        per_co[company] = sum(1 for r in records if r["company"] == company)

    # Final top-up if still short
    idx = 0
    while len(records) < min_rows:
        company = COMPANIES[idx % len(COMPANIES)]
        extra = expansion_for_company(company, 1, seen)
        if not extra:
            idx += 1
            if idx > len(COMPANIES) * 50:
                break
            continue
        rt, q = extra[0]
        records.append({
            "id": _make_id(company, rt, q),
            "company": company,
            "round_type": rt,
            "section_title": rt.replace("_", " ").title(),
            "question": q,
            "answer": "",
            "answer_source": "",
            "source": "interview_sarathi/topic_banks",
            "difficulty": "medium",
        })
        idx += 1
    return records


def _group_by_company(records: List[dict]) -> Dict[str, Dict[str, List[dict]]]:
    out: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    round_order = [
        "telephonic", "coding", "dsa", "technical", "system_design",
        "dbms", "operating_system", "networking", "hr", "managerial",
        "aptitude", "miscellaneous", "general",
    ]
    for r in records:
        out[r["company"]][r["round_type"]].append(r)

    # Stable sort sections
    sorted_out = {}
    for company in sorted(out.keys()):
        sections = {}
        for rt in round_order:
            if rt in out[company]:
                sections[rt] = out[company][rt]
        for rt in sorted(out[company].keys()):
            if rt not in sections:
                sections[rt] = out[company][rt]
        sorted_out[company] = sections
    return sorted_out


def _write_outputs(records: List[dict], out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    by_co_dir = os.path.join(out_dir, "by_company")
    os.makedirs(by_co_dir, exist_ok=True)

    grouped = _group_by_company(records)
    index = {}

    for company, sections in grouped.items():
        safe = company.replace(" ", "_").replace(".", "")
        path = os.path.join(by_co_dir, f"{safe}.json")
        payload = {
            "company": company,
            "sections": {
                rt: [{"id": x["id"], "question": x["question"], "answer": x["answer"],
                      "difficulty": x["difficulty"], "source": x["source"],
                      "answer_source": x.get("answer_source", "template")}
                     for x in items]
                for rt, items in sections.items()
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        index[company] = {rt: len(items) for rt, items in sections.items()}

    jsonl_path = os.path.join(out_dir, "interview_qa.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    stats = {
        "version": "v1",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(records),
        "companies": len(grouped),
        "with_answers": sum(1 for r in records if r.get("answer")),
        "sources": {},
        "by_round_type": defaultdict(int),
    }
    for r in records:
        stats["sources"][r["source"]] = stats["sources"].get(r["source"], 0) + 1
        stats["by_round_type"][r["round_type"]] += 1
    stats["by_round_type"] = dict(stats["by_round_type"])

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Build research interview Q&A dataset")
    parser.add_argument("--min-rows", type=int, default=MIN_ROWS_DEFAULT)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--use-llm", action="store_true", help="Enrich answers with Gemini (slow)")
    parser.add_argument("--skip-github", action="store_true")
    args = parser.parse_args()

    print(f"Building research dataset (target >= {args.min_rows} rows)...")

    if args.skip_github:
        github_data = {c: [] for c in COMPANIES}
    else:
        print("Fetching grg124/Interview-Questions from GitHub...")
        github_data = fetch_all_github_questions()

    records = _github_to_records(github_data)
    print(f"  GitHub base: {len(records)} questions")

    records = _expand_to_minimum(records, args.min_rows)
    print(f"  After expansion: {len(records)} questions")

    print("Generating answers...")
    enrich_answers_batch(records, use_llm=args.use_llm)

    stats = _write_outputs(records, args.out)
    print(f"\nDone. Wrote {stats['total_rows']} rows to {args.out}/")
    print(f"  Companies: {stats['companies']}")
    print(f"  With answers: {stats['with_answers']}")
    print(f"  Sources: {stats['sources']}")
    if stats["total_rows"] < args.min_rows:
        print(f"  WARNING: below target {args.min_rows}")
        sys.exit(1)


if __name__ == "__main__":
    main()
