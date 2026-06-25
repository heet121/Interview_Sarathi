"""
Generate reference answers for interview questions.
Uses rule-based templates by round_type; optional Gemini enrichment via --use-llm.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _detect_round(question: str, round_type: str) -> str:
    rt = (round_type or "general").lower()
    if rt != "general":
        return rt
    q = question.lower()
    if any(w in q for w in ("design a", "design an", "design the")):
        return "system_design"
    if any(w in q for w in ("implement", "given an array", "given a", "linked list", "binary tree")):
        return "coding"
    if "complexity" in q or "algorithm" in q or "data structure" in q:
        return "dsa"
    if any(w in q for w in ("acid", "sql", "database", "index", "transaction")):
        return "dbms"
    if any(w in q for w in ("process", "thread", "memory", "scheduling", "deadlock")):
        return "operating_system"
    if any(w in q for w in ("tell me about", "describe a time", "why do you", "weakness")):
        return "hr"
    return "technical"


def generate_template_answer(question: str, company: str, round_type: str) -> str:
    """Deterministic reference answer — good enough for training bootstrap."""
    rt = _detect_round(question, round_type)
    co = company or "the company"

    if rt == "coding":
        return (
            f"Approach: clarify constraints and edge cases first. "
            f"Use the optimal data structure (often hash map, two pointers, or heap depending on the problem). "
            f"Walk through a small example, then state time and space complexity. "
            f"Mention trade-offs and how you would test the solution in a {co} interview."
        )
    if rt == "system_design":
        return (
            f"Start with functional and non-functional requirements, estimate scale (QPS, storage). "
            f"Draw high-level components: API gateway, services, databases, cache, message queue. "
            f"Discuss data model, sharding, replication, and failure handling. "
            f"Close with bottlenecks and how {co}-scale systems typically optimize latency and availability."
        )
    if rt == "dsa":
        return (
            f"Give a clear definition, then explain with a concrete example. "
            f"State time/space complexity where relevant. "
            f"Compare with alternatives and mention when interviewers at {co} expect deeper follow-ups."
        )
    if rt == "dbms":
        return (
            f"Define the concept precisely (e.g. ACID, indexing, isolation). "
            f"Explain why it matters in production databases. "
            f"Give a short example and mention common pitfalls or optimizations."
        )
    if rt == "operating_system":
        return (
            f"Explain the core mechanism, then relate it to real systems behavior. "
            f"Cover trade-offs, failure modes, and one practical example from systems programming."
        )
    if rt == "hr":
        return (
            f"Use STAR: Situation (set context in 1 sentence), Task (your responsibility), "
            f"Action (specific steps you took), Result (measurable outcome). "
            f"Keep it honest, 90–120 seconds spoken, and tie the lesson to why you fit {co}."
        )
    if rt == "telephonic":
        return (
            f"State the direct answer first, then one-line reasoning. "
            f"If numeric, show quick calculation steps. "
            f"Confirm assumptions before solving."
        )
    if rt == "networking":
        return (
            f"Explain layer-by-layer or step-by-step flow. "
            f"Mention protocols involved, failure points, and latency/security implications."
        )
    return (
        f"Structure: direct answer → supporting detail → short example. "
        f"Keep it concise, accurate, and aligned with what {co} interviewers expect for this topic."
    )


async def generate_llm_answer(question: str, company: str, round_type: str) -> Optional[str]:
    """Optional Gemini enrichment for higher-quality reference answers."""
    try:
        from llm_service import _call_gemini
        prompt = (
            f"You are an expert interview coach. Company: {company}. Round: {round_type}.\n"
            f"Question: {question}\n\n"
            "Write a strong reference answer (150–250 words) that a candidate could study. "
            "Be specific and technically accurate. No markdown headers."
        )
        text = await _call_gemini(prompt, temperature=0.3, max_retries=1)
        return text.strip() if text else None
    except Exception as e:
        logger.warning(f"LLM answer failed: {e}")
        return None


def enrich_answers_batch(records: list, use_llm: bool = False) -> None:
    """Fill missing answers in-place on list of dicts with keys question, company, round_type, answer."""
    for rec in records:
        if rec.get("answer"):
            continue
        rec["answer"] = generate_template_answer(
            rec["question"], rec.get("company", ""), rec.get("round_type", "general")
        )
        rec["answer_source"] = "template"

    if not use_llm:
        return

    async def _run():
        sem = asyncio.Semaphore(3)
        for rec in records:
            if rec.get("answer_source") == "llm":
                continue
            async with sem:
                ans = await generate_llm_answer(
                    rec["question"], rec.get("company", ""), rec.get("round_type", "")
                )
                if ans:
                    rec["answer"] = ans
                    rec["answer_source"] = "llm"

    asyncio.run(_run())
