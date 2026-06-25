#!/usr/bin/env python3
"""Apply local (non-LLM) enrichment to all rows in interview_qa.jsonl."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.enrich_local import enrich_answer_local
from ml.build_research_dataset import _group_by_company

DEFAULT_DIR = os.path.join("data", "research", "v1")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    jsonl = os.path.join(out_dir, "interview_qa.jsonl")
    records = []
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    for rec in records:
        rec["answer"] = enrich_answer_local(
            rec["question"], rec.get("company", ""), rec.get("round_type", "general")
        )
        rec["answer_source"] = "local_enriched"

    with open(jsonl, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    grouped = _group_by_company(records)
    by_co = os.path.join(out_dir, "by_company")
    os.makedirs(by_co, exist_ok=True)
    for company, sections in grouped.items():
        safe = company.replace(" ", "_").replace(".", "")
        payload = {
            "company": company,
            "sections": {
                rt: [{"id": x["id"], "question": x["question"], "answer": x["answer"],
                      "difficulty": x.get("difficulty", "medium"), "source": x.get("source", ""),
                      "answer_source": x.get("answer_source", "")}
                     for x in items]
                for rt, items in sections.items()
            },
        }
        with open(os.path.join(by_co, f"{safe}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Local enrichment complete: {len(records)} rows (answer_source=local_enriched)")


if __name__ == "__main__":
    main()
