from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.models import CompanyQuestionPack
from config import settings
from dataset_service import DATASET_COMPANIES, COMPANY_META

router = APIRouter()

# ── Curated company-specific question packs ───────────────────────
CURATED_PACKS = {
    "Google": {
        "technical": [
            {"q": "Implement LRU Cache with O(1) get and put operations.", "difficulty": "hard", "hint": "Use doubly-linked list + hashmap"},
            {"q": "Given an array of integers, find two numbers that add up to a target. Return their indices.", "difficulty": "easy", "hint": "Use a hashmap for O(n) solution"},
            {"q": "Design a system to count the number of unique users visiting a website in the last 24 hours at any given moment.", "difficulty": "hard", "hint": "Sliding window + approximate counting"},
            {"q": "Given a string, find the longest palindromic substring.", "difficulty": "medium", "hint": "Expand around center O(n²) or Manacher's O(n)"},
            {"q": "How would you implement autocomplete for Google Search?", "difficulty": "hard", "hint": "Trie + ranking + real-time updates"},
        ],
        "system_design": [
            {"q": "Design Google Maps — routing, traffic, and real-time updates.", "difficulty": "hard", "hint": "Graph algorithms, CDN, real-time data"},
            {"q": "Design YouTube — video upload, processing, and streaming.", "difficulty": "hard", "hint": "CDN, transcoding pipeline, adaptive bitrate"},
            {"q": "Design Google Docs — real-time collaborative editing.", "difficulty": "hard", "hint": "OT/CRDT, WebSockets, conflict resolution"},
            {"q": "Design a web crawler for Google Search.", "difficulty": "hard", "hint": "BFS/DFS, politeness, deduplication"},
        ],
        "behavioral": [
            {"q": "Tell me about a time you had to make a technical decision with incomplete data.", "difficulty": "medium", "hint": "Use STAR method"},
            {"q": "Describe a time you disagreed with your manager. How did you handle it?", "difficulty": "medium", "hint": "Focus on communication and outcome"},
            {"q": "What's the most impactful project you've worked on? Why was it impactful?", "difficulty": "medium", "hint": "Quantify impact with numbers"},
        ],
        "hr": [
            {"q": "Why do you want to work at Google specifically?", "difficulty": "easy", "hint": "Research Google's products and culture"},
            {"q": "Where do you see yourself in 5 years?", "difficulty": "easy", "hint": "Align with Google's growth opportunities"},
            {"q": "What is your expected salary range?", "difficulty": "easy", "hint": "Research market rates, give a range"},
        ],
    },
    "Amazon": {
        "behavioral": [
            {"q": "Tell me about a time you had to make a decision that was unpopular. (Leadership Principle: Have Backbone; Disagree and Commit)", "difficulty": "medium", "hint": "LP: Have Backbone"},
            {"q": "Describe a situation where you had to deliver a project with tight deadlines and limited resources. (LP: Deliver Results)", "difficulty": "medium", "hint": "LP: Deliver Results"},
            {"q": "Give an example of a time you went above and beyond for a customer. (LP: Customer Obsession)", "difficulty": "medium", "hint": "LP: Customer Obsession"},
            {"q": "Tell me about a time you failed. What did you learn? (LP: Learn and Be Curious)", "difficulty": "medium", "hint": "Own the failure, show learning"},
            {"q": "Describe a time you invented a creative solution to a difficult problem. (LP: Invent and Simplify)", "difficulty": "medium", "hint": "LP: Invent and Simplify"},
        ],
        "technical": [
            {"q": "Design Amazon's recommendation engine — how would you suggest products to users?", "difficulty": "hard", "hint": "Collaborative filtering, content-based, hybrid"},
            {"q": "How would you design a distributed key-value store like DynamoDB?", "difficulty": "hard", "hint": "Consistent hashing, replication, CAP"},
            {"q": "Implement a function to serialize and deserialize a binary tree.", "difficulty": "medium", "hint": "BFS or DFS with null markers"},
        ],
        "system_design": [
            {"q": "Design Amazon's shopping cart system that handles millions of concurrent users.", "difficulty": "hard", "hint": "Session storage, consistency, checkout flow"},
            {"q": "Design Amazon's package delivery tracking system.", "difficulty": "hard", "hint": "IoT, event streaming, real-time updates"},
        ],
    },
    "Microsoft": {
        "technical": [
            {"q": "Reverse a linked list both iteratively and recursively.", "difficulty": "easy", "hint": "Track prev, curr, next pointers"},
            {"q": "How does the .NET CLR handle memory management and garbage collection?", "difficulty": "medium", "hint": "Generations, LOH, GC roots"},
            {"q": "Design a thread-safe singleton class in Java/C#.", "difficulty": "medium", "hint": "Double-checked locking or static initialization"},
            {"q": "How would you detect if a binary tree is balanced?", "difficulty": "medium", "hint": "Post-order traversal, return height"},
        ],
        "system_design": [
            {"q": "Design Microsoft Teams — messaging, video calls, and file sharing.", "difficulty": "hard", "hint": "WebRTC, signaling, CDN for files"},
            {"q": "Design Azure's auto-scaling system for virtual machines.", "difficulty": "hard", "hint": "Metrics collection, thresholds, provisioning"},
        ],
        "behavioral": [
            {"q": "Tell me about a time you had to learn a new technology very quickly.", "difficulty": "medium", "hint": "Show curiosity and process"},
            {"q": "How do you handle working with a difficult team member?", "difficulty": "medium", "hint": "Communication, empathy, escalation"},
        ],
    },
    "Flipkart": {
        "technical": [
            {"q": "How would you design Flipkart's search ranking algorithm?", "difficulty": "hard", "hint": "Relevance, popularity, personalization"},
            {"q": "Design a flash sale system that prevents overselling inventory.", "difficulty": "hard", "hint": "Atomic operations, Redis, distributed locks"},
            {"q": "How would you implement a coupon management system?", "difficulty": "medium", "hint": "Validation, limits, race conditions"},
        ],
        "system_design": [
            {"q": "Design Flipkart's seller dashboard — inventory, orders, and analytics.", "difficulty": "hard", "hint": "Read/write separation, aggregation"},
            {"q": "How would you design the notification system for order updates?", "difficulty": "medium", "hint": "Push, email, SMS — fan-out pattern"},
        ],
        "hr": [
            {"q": "Why e-commerce? Why Flipkart specifically?", "difficulty": "easy", "hint": "Research Flipkart's market position"},
            {"q": "How do you stay motivated when facing repeated failures?", "difficulty": "easy", "hint": "Growth mindset, specific examples"},
        ],
    },
    "Zomato": {
        "technical": [
            {"q": "Design Zomato's real-time delivery tracking system.", "difficulty": "hard", "hint": "GPS polling, WebSockets, ETA calculation"},
            {"q": "How would you handle restaurant search with filters (cuisine, rating, distance, price)?", "difficulty": "medium", "hint": "Elasticsearch, geo-queries, faceted search"},
            {"q": "Design a surge pricing algorithm for delivery partners.", "difficulty": "hard", "hint": "Supply-demand signals, geographic zones"},
        ],
        "behavioral": [
            {"q": "Tell me about a high-pressure situation where you had to deliver quickly.", "difficulty": "medium", "hint": "Crisis management, prioritization"},
            {"q": "How do you handle ambiguity in requirements?", "difficulty": "medium", "hint": "Clarifying questions, assumptions, MVP approach"},
        ],
    },
}


def _seed_packs(db: Session):
    """Insert curated packs if not already seeded."""
    existing = db.query(func.count(CompanyQuestionPack.id)).scalar()
    if existing and existing > 0:
        return existing

    rows = []
    for company, rounds in CURATED_PACKS.items():
        for round_type, questions in rounds.items():
            for q in questions:
                rows.append(CompanyQuestionPack(
                    company=company,
                    round_type=round_type,
                    difficulty=q.get("difficulty", "medium"),
                    question=q["q"],
                    answer_guide=q.get("hint", ""),
                    tags=[round_type, company.lower()],
                    is_active=True,
                ))
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)




@router.get("/")
def list_packs(db: Session = Depends(get_db)):
    """List all companies with curated question packs and counts."""
    counts = (
        db.query(CompanyQuestionPack.company, func.count(CompanyQuestionPack.id))
        .filter(CompanyQuestionPack.is_active == True)
        .group_by(CompanyQuestionPack.company)
        .all()
    )
    count_map = {c: n for c, n in counts}

    result = []
    for company in DATASET_COMPANIES:
        meta = COMPANY_META.get(company, {})
        n    = count_map.get(company, 0)
        if n > 0:
            result.append({
                "company": company,
                "emoji":   meta.get("emoji", "🏢"),
                "color":   meta.get("color", "#6366f1"),
                "sector":  meta.get("sector", "Tech"),
                "question_count": n,
                "has_curated_pack": True,
            })
    # Companies in dataset but no curated pack
    for company in DATASET_COMPANIES:
        if company not in count_map:
            meta = COMPANY_META.get(company, {})
            result.append({
                "company": company,
                "emoji":   meta.get("emoji", "🏢"),
                "color":   meta.get("color", "#6366f1"),
                "sector":  meta.get("sector", "Tech"),
                "question_count": 0,
                "has_curated_pack": False,
            })
    return {"packs": result, "total_curated_companies": len(count_map)}


@router.get("/{company}")
def get_company_pack(
    company: str,
    round_type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all curated questions for a company, with optional filters."""
    q = db.query(CompanyQuestionPack).filter(
        CompanyQuestionPack.company.ilike(f"%{company}%"),
        CompanyQuestionPack.is_active == True,
    )
    if round_type: q = q.filter(CompanyQuestionPack.round_type == round_type)
    if difficulty: q = q.filter(CompanyQuestionPack.difficulty == difficulty)
    packs = q.order_by(CompanyQuestionPack.round_type, CompanyQuestionPack.difficulty).all()

    if not packs:
        raise HTTPException(status_code=404, detail=f"No curated pack found for '{company}'")

    # Group by round type
    by_round = {}
    for p in packs:
        rt = p.round_type or "general"
        by_round.setdefault(rt, []).append({
            "id":          p.id,
            "question":    p.question,
            "answer_guide":p.answer_guide,
            "difficulty":  p.difficulty,
            "tags":        p.tags or [],
            "upvotes":     p.upvotes,
        })

    meta = COMPANY_META.get(company, {})
    return {
        "company":      company,
        "emoji":        meta.get("emoji", "🏢"),
        "color":        meta.get("color", "#6366f1"),
        "total":        len(packs),
        "rounds":       by_round,
        "round_types":  list(by_round.keys()),
    }


@router.get("/{company}/rounds")
def get_rounds(company: str, db: Session = Depends(get_db)):
    """List available round types for a company."""
    rounds = (
        db.query(CompanyQuestionPack.round_type, func.count(CompanyQuestionPack.id))
        .filter(
            CompanyQuestionPack.company.ilike(f"%{company}%"),
            CompanyQuestionPack.is_active == True,
        )
        .group_by(CompanyQuestionPack.round_type)
        .all()
    )
    if not rounds:
        raise HTTPException(status_code=404, detail=f"No pack found for '{company}'")
    return {
        "company": company,
        "rounds": [{"type": r, "count": n} for r, n in rounds],
    }


@router.post("/seed")
def seed_packs(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: Session = Depends(get_db),
):
    """Admin: seed the database with curated question packs."""
    if not settings.ADMIN_SECRET_KEY or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    n = _seed_packs(db)
    return {"message": f"Seeded {n} curated questions"}
