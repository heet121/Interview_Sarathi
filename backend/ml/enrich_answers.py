"""
Resumable LLM answer enrichment for the research dataset.
Supports Gemini or Claude. Saves checkpoint every N rows so a 2500+ run
can be stopped and continued.

Usage (from backend/):
  python -m ml.enrich_answers --provider gemini --limit 5    # smoke test
  python -m ml.enrich_answers --provider gemini              # full run
  python -m ml.enrich_answers --provider claude              # use Claude instead
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.answer_generator import generate_template_answer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DIR = os.path.join("data", "research", "v1")
JSONL = "interview_qa.jsonl"
CHECKPOINT = "enrich_checkpoint.json"


async def _llm_answer(provider: str, question: str, company: str, round_type: str) -> Optional[str]:
    prompt = (
        f"You are an expert interview coach. Company: {company}. Round: {round_type}.\n"
        f"Question: {question}\n\n"
        "Write a strong reference answer (150–250 words) that a candidate could study. "
        "Be specific and technically accurate. Plain text only, no markdown headers."
    )
    try:
        if provider == "claude":
            from llm_service import _call_claude
            text = await _call_claude(prompt, max_retries=2)
        else:
            from llm_service import _call_gemini
            text = await _call_gemini(prompt, temperature=0.3, max_retries=2)
        return text.strip() if text else None
    except Exception as e:
        logger.warning(f"LLM failed ({provider}): {e}")
        return None


async def test_provider(provider: str) -> bool:
    ans = await _llm_answer(provider, "What is a hash map?", "Google", "dsa")
    if ans and len(ans) > 40:
        logger.info(f"Provider {provider} OK — sample length {len(ans)} chars")
        return True
    logger.error(f"Provider {provider} failed smoke test")
    return False


def load_records(path: str) -> List[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_jsonl(records: List[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def rewrite_by_company(records: List[dict], out_dir: str) -> None:
    """Sync by_company/*.json from flat records."""
    from ml.build_research_dataset import _group_by_company, _write_outputs
    # _write_outputs rewrites everything; call internal group only
    by_co_dir = os.path.join(out_dir, "by_company")
    os.makedirs(by_co_dir, exist_ok=True)
    grouped = _group_by_company(records)
    for company, sections in grouped.items():
        safe = company.replace(" ", "_").replace(".", "")
        path = os.path.join(by_co_dir, f"{safe}.json")
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
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def load_checkpoint(out_dir: str) -> set:
    cp = os.path.join(out_dir, CHECKPOINT)
    if not os.path.exists(cp):
        return set()
    with open(cp, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("done_ids", []))


def save_checkpoint(out_dir: str, done_ids: set, provider: str) -> None:
    cp = os.path.join(out_dir, CHECKPOINT)
    with open(cp, "w", encoding="utf-8") as f:
        json.dump({
            "provider": provider,
            "done_ids": sorted(done_ids),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(done_ids),
        }, f, indent=2)


async def enrich(
    out_dir: str,
    provider: str,
    limit: Optional[int],
    skip_test: bool,
    save_every: int = 25,
) -> None:
    from config import settings

    if provider == "gemini":
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
            raise SystemExit("GEMINI_API_KEY missing in backend/.env — add or replace your key.")
    elif provider == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise SystemExit("ANTHROPIC_API_KEY missing in backend/.env — add your Claude key.")
    else:
        raise SystemExit(f"Unknown provider: {provider}")

    if not skip_test:
        ok = await test_provider(provider)
        if not ok:
            raise SystemExit(
                f"\n{provider.upper()} is not working (quota/rate limit or bad key).\n"
                "Replace the key in backend/.env and run again.\n"
                "  Gemini: https://aistudio.google.com/app/apikey\n"
                "  Claude: https://console.anthropic.com/\n"
            )

    jsonl_path = os.path.join(out_dir, JSONL)
    if not os.path.exists(jsonl_path):
        raise SystemExit(f"Missing {jsonl_path} — run: python -m ml.build_research_dataset")

    records = load_records(jsonl_path)
    done = load_checkpoint(out_dir)
    sem = asyncio.Semaphore(2)  # gentle on free-tier rate limits

    todo = [r for r in records if r["id"] not in done and r.get("answer_source") != "llm"]
    if limit:
        todo = todo[:limit]

    logger.info(f"Enriching {len(todo)} rows with {provider} ({len(done)} already done)")

    processed = 0
    for rec in records:
        if rec["id"] in done or rec.get("answer_source") == "llm":
            continue
        if limit is not None and processed >= limit:
            break

        async with sem:
            ans = await _llm_answer(
                provider, rec["question"], rec.get("company", ""), rec.get("round_type", "")
            )
        if ans:
            rec["answer"] = ans
            rec["answer_source"] = "llm"
            done.add(rec["id"])
            processed += 1
            if processed % 10 == 0:
                logger.info(f"  enriched {processed}/{len(todo)}…")
        else:
            # keep template, don't mark done — retry next run
            if not rec.get("answer"):
                rec["answer"] = generate_template_answer(
                    rec["question"], rec.get("company", ""), rec.get("round_type", "")
                )
                rec["answer_source"] = "template"

        if processed and processed % save_every == 0:
            save_jsonl(records, jsonl_path)
            save_checkpoint(out_dir, done, provider)
            rewrite_by_company(records, out_dir)

    save_jsonl(records, jsonl_path)
    save_checkpoint(out_dir, done, provider)
    rewrite_by_company(records, out_dir)

    llm_count = sum(1 for r in records if r.get("answer_source") == "llm")
    logger.info(f"Done. {llm_count}/{len(records)} rows now have LLM answers.")


def main():
    p = argparse.ArgumentParser(description="Enrich research dataset answers with LLM")
    p.add_argument("--dir", default=DEFAULT_DIR)
    p.add_argument("--provider", choices=["gemini", "claude"], default="gemini")
    p.add_argument("--limit", type=int, default=None, help="Only enrich N rows (for testing)")
    p.add_argument("--skip-test", action="store_true")
    args = p.parse_args()
    asyncio.run(enrich(args.dir, args.provider, args.limit, args.skip_test))


if __name__ == "__main__":
    main()
