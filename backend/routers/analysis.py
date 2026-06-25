from datetime import datetime, timezone
from typing import List, Dict
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, InterviewSession, SessionAnalysis, Resume
from models.schemas import AnalysisResult
from utils.auth import get_current_user
from llm_service import run_deep_analysis
from posture_service import compute_posture_session_score
from gamification_service import process_completed_interview

router = APIRouter()


# ── Topic recommendation engine ───────────────────────────────────────────────

_TOPIC_MAP = [
    # Data Structures & Algorithms
    (r"array|list|tuple|vector|sequence",        ["Arrays & Lists", "Indexing & Slicing", "Time Complexity O(n)"]),
    (r"hash|dict|map|lookup|key.value",           ["Hash Maps / Dictionaries", "Collision Handling", "O(1) Lookups"]),
    (r"tree|bst|binary|heap|trie",                ["Binary Trees", "Tree Traversal (BFS/DFS)", "Balanced BSTs"]),
    (r"graph|node|edge|network|path",             ["Graph Theory", "DFS & BFS", "Shortest Path Algorithms"]),
    (r"sort|order|rank|quicksort|mergesort",      ["Sorting Algorithms", "QuickSort vs MergeSort", "Stability in Sorting"]),
    (r"stack|queue|deque|lifo|fifo",              ["Stacks & Queues", "Use Cases", "Implementation in Python"]),
    (r"dynamic|dp|memoiz|tabulation|optimal",    ["Dynamic Programming", "Memoization", "Bottom-Up vs Top-Down"]),
    (r"recursion|recursive|base case",            ["Recursion & Base Cases", "Call Stack", "Tail Recursion"]),
    (r"big.o|complexity|time.space|optimize",     ["Big-O Notation", "Time vs Space Complexity", "Algorithm Optimization"]),
    (r"link|linked list|pointer|node.next",       ["Linked Lists", "Singly vs Doubly Linked", "Fast/Slow Pointer Technique"]),

    # System Design
    (r"design|architect|system|scale|distribut",  ["System Design Fundamentals", "Scalability Patterns", "Load Balancing"]),
    (r"database|sql|nosql|postgres|mysql|mongo",  ["SQL vs NoSQL", "Database Indexing", "ACID Properties"]),
    (r"cache|redis|memcache|cdn|invalidat",       ["Caching Strategies", "Redis Basics", "Cache Invalidation"]),
    (r"api|rest|graphql|endpoint|http|request",   ["REST API Design", "HTTP Methods", "API Versioning"]),
    (r"microservice|monolith|service|docker",     ["Microservices Architecture", "Docker & Containers", "Service Communication"]),
    (r"message|queue|kafka|rabbit|async|event",   ["Message Queues", "Event-Driven Architecture", "Kafka Basics"]),
    (r"auth|jwt|oauth|session|token|login",       ["JWT Authentication", "OAuth 2.0", "Session vs Token Auth"]),
    (r"cloud|aws|azure|gcp|serverless|lambda",    ["Cloud Computing Basics", "AWS Core Services", "Serverless Architecture"]),

    # Object-Oriented & Software Design
    (r"oop|class|object|inherit|polymorphi",      ["OOP Principles", "Inheritance & Composition", "Polymorphism"]),
    (r"solid|principle|design.pattern|pattern",   ["SOLID Principles", "Common Design Patterns", "Gang of Four"]),
    (r"interface|abstract|encapsul|modulari",     ["Abstraction & Encapsulation", "Interface Design", "Modular Code"]),
    (r"test|unit.test|tdd|mock|coverage",         ["Unit Testing", "Test-Driven Development", "Mocking & Stubs"]),
    (r"agile|scrum|sprint|kanban|standup",        ["Agile Methodology", "Scrum Framework", "Sprint Planning"]),
    (r"git|version|commit|branch|merge|pr",       ["Git Workflow", "Branching Strategies", "Code Reviews"]),

    # Language-Specific
    (r"python|decorator|generator|comprehension", ["Python Advanced Concepts", "Decorators & Generators", "List Comprehensions"]),
    (r"javascript|async.await|promise|closure",   ["JavaScript Async/Await", "Closures & Scope", "Event Loop"]),
    (r"java|jvm|garbage|spring|thread",           ["Java Memory Management", "Concurrency in Java", "Spring Framework"]),
    (r"concurrent|thread|async|race condition",   ["Concurrency & Parallelism", "Thread Safety", "Race Conditions"]),

    # Behavioral / STAR
    (r"challeng|difficult|fail|mistake|learn",    ["STAR Method (Situation, Task, Action, Result)", "Storytelling in Interviews", "Quantifying Impact"]),
    (r"conflict|disagree|team|collaborat",        ["Conflict Resolution", "Team Collaboration", "Communication Skills"]),
    (r"leader|mentor|initiative|owner",           ["Leadership Principles", "Taking Ownership", "Mentoring Others"]),
    (r"prioriti|deadline|pressure|time.manag",    ["Time Management", "Prioritization Frameworks", "Working Under Pressure"]),
    (r"why.*company|motivat|goal|career",         ["Company Research", "Career Goal Articulation", "Cultural Fit"]),

    # ML / Data Science
    (r"machine.learn|model|train|predict|classif",["ML Fundamentals", "Supervised vs Unsupervised", "Model Evaluation Metrics"]),
    (r"neural|deep.learn|cnn|rnn|transformer",    ["Neural Network Basics", "Deep Learning Architecture", "Transformers & Attention"]),
    (r"overfit|underfit|regulariz|bias.variance", ["Bias-Variance Tradeoff", "Regularization (L1/L2)", "Cross-Validation"]),
]

_FALLBACK_TOPICS = [
    "Core Computer Science Fundamentals",
    "Data Structures & Algorithms",
    "Problem-Solving & Whiteboard Practice",
    "Technical Communication Skills",
]


def get_study_topics(question_text: str) -> List[str]:
    """
    Analyse the question text and return relevant study topics
    the candidate should focus on to answer this type of question.
    """
    q = question_text.lower()
    matched: List[str] = []
    for pattern, topics in _TOPIC_MAP:
        if re.search(pattern, q):
            for t in topics:
                if t not in matched:
                    matched.append(t)
        if len(matched) >= 6:
            break

    if not matched:
        return _FALLBACK_TOPICS[:4]

    # Return up to 5 focused topics
    return matched[:5]


def _is_skipped(answer_text: str) -> bool:
    """Return True if the answer was skipped or effectively empty."""
    if not answer_text:
        return True
    norm = answer_text.strip().lower()
    return norm in {"", "[no answer provided]", "[skipped]", "skipped", "n/a", "-"}


# ── Main analysis endpoint ────────────────────────────────────────────────────

@router.post("/{session_id}")
async def generate_analysis(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id      == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    questions = sorted(session.questions, key=lambda q: q.question_index or 0)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions recorded for this session")

    # ── Separate answered vs skipped ─────────────────────────────
    answered_log = []
    skipped_log  = []

    for q in questions:
        if _is_skipped(q.answer_text):
            skipped_log.append(q)
        else:
            answered_log.append({
                "question": q.question_text or "",
                "answer":   q.answer_text or "",
                "judge_scores": q.judge_scores,
                "content_score": q.content_score,
                "communication_score": q.communication_score,
                "relevance_score": getattr(q, "relevance_score", None),
            })

    if not answered_log and skipped_log:
        # All questions were skipped — return a study plan only
        study_plan = [
            {
                "question":       q.question_text or f"Question {q.question_index + 1}",
                "skipped":        True,
                "study_topics":   get_study_topics(q.question_text or ""),
                "study_message":  "You skipped this question. Focus on these topics to build confidence answering it.",
            }
            for q in skipped_log
        ]
        return {
            "overall_score":   0,
            "verdict":         "Incomplete",
            "overall_summary": "No answers were recorded. Review the study topics for each skipped question.",
            "strengths":       [],
            "improvements":    ["Complete at least one answer to receive a full analysis."],
            "dimensions":      {},
            "qa_breakdown":    study_plan,
            "roadmap":         [t for sq in skipped_log for t in get_study_topics(sq.question_text or "")][:8],
            "posture_score":   None,
            "gamification":    {},
        }

    # ── Posture score ─────────────────────────────────────────────
    posture_data = [
        {
            "posture_label":    p.posture_label,
            "eye_contact":      p.eye_contact,
            "confidence_level": p.confidence_level,
            "deepface_emotion": p.deepface_emotion,
        }
        for p in session.posture_logs
    ]
    posture_score, posture_summary = compute_posture_session_score(posture_data)

    # ── LLM deep analysis (answered questions only) ───────────────
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    resume_text = (resume.text_content if resume else "") or ""
    from resume_service import extract_candidate_name
    candidate_name = extract_candidate_name(resume_text) or current_user.full_name or current_user.email

    cfg = {
        "name":           candidate_name,
        "company":        session.company,
        "role":           session.role,
        "interview_type": session.interview_type,
        "difficulty":     session.difficulty,
        "num_questions":  session.num_questions,
        "skills":         session.skills_focus,
    }

    try:
        raw = await run_deep_analysis(cfg, answered_log, posture_summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Override posture score from real data
    if "dimensions" in raw and "Posture & Presence" in raw["dimensions"]:
        raw["dimensions"]["Posture & Presence"]["score"] = int(posture_score)

    # ── Inject per-question judge + NLP scores into qaBreakdown ──
    answered_questions = [q for q in questions if not _is_skipped(q.answer_text)]
    for i, item in enumerate(raw.get("qaBreakdown", [])):
        sq = answered_questions[i] if i < len(answered_questions) else None
        if sq:
            item["content_score"]       = item.get("contentScore")       or sq.content_score       or 60
            item["communication_score"] = item.get("communicationScore") or sq.communication_score or 60
            item["keywords"]            = sq.nlp_keywords or item.get("keywords") or []
            js = sq.judge_scores or item.get("judgeScores") or item.get("judge_scores")
            if js:
                item["judge_scores"] = js
                item["judge_overall"] = item.get("judgeOverall") or round(
                    sum(js.get(k, 0) for k in ("relevance", "correctness", "depth", "communication", "structure")) / 5, 1
                )
            item["scoring_engine"] = item.get("scoringEngine") or item.get("scoring_engine")

    # ── Final score ───────────────────────────────────────────────
    dim_scores = [
        v.get("score", 0) for v in raw.get("dimensions", {}).values()
        if v.get("score") is not None
    ]
    final_score = round(sum(dim_scores) / len(dim_scores), 1) if dim_scores else raw.get("overallScore", 60)
    raw["overallScore"] = final_score

    verdict = (
        "Excellent" if final_score >= 85 else
        "Good"      if final_score >= 70 else
        "Average"   if final_score >= 55 else
        "Needs Work"
    )
    raw["verdict"] = verdict

    # ── Persist analysis ──────────────────────────────────────────
    existing = db.query(SessionAnalysis).filter(SessionAnalysis.session_id == session_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    dims = raw.get("dimensions", {})
    analysis = SessionAnalysis(
        session_id=session_id,
        overall_score=final_score,
        verdict=verdict,
        content_score=dims.get("Content & Knowledge", {}).get("score"),
        communication_score=dims.get("Communication", {}).get("score"),
        confidence_score=dims.get("Confidence", {}).get("score"),
        relevance_score=dims.get("Relevance", {}).get("score"),
        star_score=dims.get("STAR Structure", {}).get("score"),
        posture_score=posture_score,
        overall_summary=raw.get("overallSummary", ""),
        strengths=raw.get("strengths", []),
        improvements=raw.get("improvements", []),
        roadmap=raw.get("roadmap", []),
        full_analysis_json=raw,
    )
    db.add(analysis)
    session.overall_score = final_score
    session.status        = "completed"
    session.completed_at  = datetime.now(timezone.utc)
    db.commit()

    # ── Gamification ──────────────────────────────────────────────
    gamification = {}
    try:
        gamification = process_completed_interview(session, db)
    except Exception:
        pass

    # ── Build final qa_breakdown with skipped topics injected ─────
    answered_items = [
        {
            "question":            item.get("question", ""),
            "answer":              item.get("answer", ""),
            "feedback":            item.get("feedback", ""),
            "content_score":       item.get("contentScore") or item.get("content_score", 60),
            "communication_score": item.get("communicationScore") or item.get("communication_score", 60),
            "relevance_score":     item.get("relevanceScore") or item.get("relevance_score"),
            "judge_scores":        item.get("judge_scores") or item.get("judgeScores"),
            "judge_overall":       item.get("judge_overall") or item.get("judgeOverall"),
            "scoring_engine":      item.get("scoring_engine") or item.get("scoringEngine"),
            "sentiment":           item.get("sentiment", "neutral"),
            "keywords":            item.get("keywords", []),
            "skipped":             False,
            "study_topics":        [],
        }
        for item in raw.get("qaBreakdown", [])
    ]

    # Insert skipped questions back at their original index positions
    skipped_items_by_index = {
        q.question_index: {
            "question":       q.question_text or f"Question {q.question_index + 1}",
            "answer":         "",
            "feedback":       "",
            "content_score":  0,
            "communication_score": 0,
            "sentiment":      "neutral",
            "keywords":       [],
            "skipped":        True,
            "study_topics":   get_study_topics(q.question_text or ""),
            "study_message":  "You skipped this question. Study these topics to answer it confidently next time.",
        }
        for q in skipped_log
    }

    # Reconstruct qa_breakdown in original question order
    total_q = session.num_questions or len(questions)
    final_qa = []
    answered_ptr = 0
    for idx in range(total_q):
        if idx in skipped_items_by_index:
            final_qa.append(skipped_items_by_index[idx])
        elif answered_ptr < len(answered_items):
            final_qa.append(answered_items[answered_ptr])
            answered_ptr += 1

    # Build roadmap — always include skipped topics at the end
    roadmap = raw.get("roadmap", [])
    for sq in skipped_log:
        for topic in get_study_topics(sq.question_text or ""):
            if topic not in roadmap:
                roadmap.append(topic)

    result = AnalysisResult(
        overall_score=final_score,
        verdict=verdict,
        overall_summary=raw.get("overallSummary", ""),
        strengths=raw.get("strengths", []),
        improvements=raw.get("improvements", []),
        dimensions={
            k: {"score": v.get("score"), "comment": v.get("comment", "")}
            for k, v in dims.items()
        },
        qa_breakdown=final_qa,
        roadmap=roadmap,
        posture_score=posture_score,
        posture_summary=posture_summary,
    )
    result_dict = result.model_dump()
    result_dict["gamification"] = gamification
    result_dict["skipped_count"] = len(skipped_log)
    return result_dict


@router.get("/{session_id}")
def get_analysis(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = (
        db.query(SessionAnalysis)
        .join(InterviewSession)
        .filter(
            SessionAnalysis.session_id == session_id,
            InterviewSession.user_id   == current_user.id,
        )
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found — run POST first")
    return analysis.full_analysis_json