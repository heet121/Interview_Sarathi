"""
Unified answer scoring: DeBERTa judge + NLP (sentiment, keywords, semantic relevance).

The judge model is the primary scorer. NLP supplements keywords/sentiment and
can blend into relevance when SCORING_MODE=hybrid (default).
LLM is optional — used only for short text feedback when available.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional

from config import settings
from nlp_service import score_answer_nlp

logger = logging.getLogger(__name__)


def _judge_path() -> str:
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    rel = getattr(settings, "JUDGE_MODEL_PATH", "models/judge/deberta-v3-base-v1")
    return rel if os.path.isabs(rel) else os.path.join(base, rel)


def _run_judge(question: str, answer: str) -> Dict:
    import os
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("USE_TF", "0")
    os.environ["JUDGE_MODEL_PATH"] = _judge_path()
    from ml.judge_service import score_answer_judge
    return score_answer_judge(question, answer)


def _blend(a: float, b: float, w_a: float = 0.75) -> float:
    return round(a * w_a + b * (1 - w_a), 1)


def score_answer_sync(question: str, answer: str, company: str = "", role: str = "") -> Dict:
    """Synchronous scoring (judge + NLP, no LLM). For report fallbacks."""
    nlp = score_answer_nlp(question, answer)
    judge = _run_judge(question, answer) if settings.JUDGE_ENABLED else None

    if judge and judge.get("engine") == "deberta_judge":
        mode = (settings.SCORING_MODE or "hybrid").lower()
        if mode == "judge":
            relevance, content, communication = judge["relevance"], judge["correctness"], judge["communication"]
        else:
            relevance = _blend(judge["relevance"], nlp["relevance_score"])
            content = _blend(judge["correctness"], nlp["content_score"])
            communication = _blend(judge["communication"], nlp["communication_score"])
        judge_scores = {k: judge[k] for k in DIMS if k in judge}
        engine = judge["engine"]
        judge_overall = judge["overall"]
    else:
        relevance, content, communication = nlp["relevance_score"], nlp["content_score"], nlp["communication_score"]
        judge_scores = {
            "relevance": relevance, "correctness": content,
            "depth": min(100, nlp["word_count"] * 2),
            "communication": communication, "structure": communication,
        }
        engine = "nlp"
        judge_overall = round((relevance + content + communication) / 3, 1)

    overall = round((relevance + content + communication) / 3, 1)
    ai_feedback = _feedback_from_scores(
        {"overall": judge_overall, "relevance": relevance, "depth": judge_scores.get("depth", 0)},
        nlp, question,
    )
    return {
        "content_score": content,
        "communication_score": communication,
        "relevance_score": relevance,
        "bert_label": nlp["bert_label"],
        "bert_score": nlp["bert_score"],
        "keywords": nlp["keywords"],
        "word_count": nlp["word_count"],
        "judge_scores": judge_scores,
        "judge_overall": judge_overall,
        "overall_score": overall,
        "scoring_engine": engine,
        "ai_feedback": ai_feedback,
        "llm_score": None,
    }


DIMS = ["relevance", "correctness", "depth", "communication", "structure"]


def _feedback_from_scores(judge: Dict, nlp: Dict, question: str) -> str:
    overall = judge.get("overall", 0)
    rel = judge.get("relevance", 0)
    depth = judge.get("depth", 0)
    kws = nlp.get("keywords") or []
    kw_hint = f" Terms detected: {', '.join(kws[:4])}." if kws else ""

    if overall >= 80:
        return f"Strong answer — well structured and on-topic.{kw_hint}"
    if rel < 45:
        return (
            f"Your answer drifted off-topic. Re-read the question and focus on: "
            f"\"{question[:90]}…\"{kw_hint}"
        )
    if depth < 40:
        return (
            f"Too brief — aim for 90–150 words with a concrete example (STAR method).{kw_hint}"
        )
    if overall >= 60:
        return f"Solid attempt. Add more specific detail or metrics to score higher.{kw_hint}"
    return f"Needs work — expand with examples and tie back to the question.{kw_hint}"


async def score_answer(
    question: str,
    answer: str,
    company: str = "",
    role: str = "",
    use_llm_feedback: bool = True,
) -> Dict:
    """
    Score one answer. Returns dict compatible with interview router + extras:
      content_score, communication_score, relevance_score,
      bert_label, bert_score, keywords, word_count,
      judge_scores, judge_overall, scoring_engine, ai_feedback, llm_score
    """
    loop = asyncio.get_running_loop()

    nlp_future = loop.run_in_executor(None, score_answer_nlp, question, answer)
    judge_future = None
    if settings.JUDGE_ENABLED:
        judge_future = loop.run_in_executor(None, _run_judge, question, answer)

    nlp = await nlp_future
    judge = await judge_future if judge_future else None

    if judge and judge.get("engine") == "deberta_judge":
        mode = (settings.SCORING_MODE or "hybrid").lower()
        if mode == "judge":
            relevance = judge["relevance"]
            content = judge["correctness"]
            communication = judge["communication"]
        else:
            relevance = _blend(judge["relevance"], nlp["relevance_score"])
            content = _blend(judge["correctness"], nlp["content_score"])
            communication = _blend(judge["communication"], nlp["communication_score"])

        engine = f"hybrid({judge['engine']}+nlp)" if mode == "hybrid" else judge["engine"]
        judge_overall = judge["overall"]
        judge_scores = {k: judge[k] for k in (
            "relevance", "correctness", "depth", "communication", "structure"
        ) if k in judge}
    else:
        relevance = nlp["relevance_score"]
        content = nlp["content_score"]
        communication = nlp["communication_score"]
        engine = nlp.get("relevance_engine", "nlp")
        judge_overall = round((relevance + content + communication) / 3, 1)
        judge_scores = {
            "relevance": relevance,
            "correctness": content,
            "depth": min(100, nlp["word_count"] * 2),
            "communication": communication,
            "structure": communication,
        }

    ai_feedback = _feedback_from_scores(
        {"overall": judge_overall, "relevance": relevance, "depth": judge_scores.get("depth", 0)},
        nlp,
        question,
    )

    llm_score = None
    if use_llm_feedback and settings.LLM_FEEDBACK_ENABLED:
        try:
            from llm_service import score_answer_with_llm
            llm_result = await score_answer_with_llm(question, answer, company, role)
            if llm_result.get("feedback"):
                ai_feedback = llm_result["feedback"]
            llm_score = llm_result.get("score")
        except Exception as e:
            logger.debug(f"LLM feedback skipped: {e}")

    overall = round((relevance + content + communication) / 3, 1)

    return {
        "content_score": content,
        "communication_score": communication,
        "relevance_score": relevance,
        "bert_label": nlp["bert_label"],
        "bert_score": nlp["bert_score"],
        "keywords": nlp["keywords"],
        "word_count": nlp["word_count"],
        "judge_scores": judge_scores,
        "judge_overall": judge_overall,
        "overall_score": overall,
        "scoring_engine": engine,
        "ai_feedback": ai_feedback,
        "llm_score": llm_score,
    }
