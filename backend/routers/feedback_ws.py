import json
import re
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Target word counts for pacing guidance
WORD_TARGET_MIN = 60
WORD_TARGET_MAX = 200

FILLER_WORDS = {
    "um", "uh", "like", "you know", "basically", "literally",
    "actually", "honestly", "right", "so", "kind of", "sort of",
}

TECH_KEYWORDS = {
    "algorithm", "complexity", "scalability", "database", "api", "cache",
    "microservice", "docker", "kubernetes", "python", "java", "javascript",
    "machine learning", "neural network", "sql", "nosql", "redis", "kafka",
    "design pattern", "solid", "oop", "async", "distributed", "latency",
    "throughput", "consistency", "availability", "partition", "load balancer",
    "authentication", "authorization", "encryption", "hash", "tree", "graph",
}


def _count_fillers(text: str) -> tuple[int, List[str]]:
    text_lower = text.lower()
    found = []
    count = 0
    for fw in FILLER_WORDS:
        hits = len(re.findall(r'\b' + re.escape(fw) + r'\b', text_lower))
        if hits:
            found.append(fw)
            count += hits
    return count, found


def _keywords_hit(text: str, question: str) -> List[str]:
    text_lower = text.lower()
    hits = [kw for kw in TECH_KEYWORDS if kw in text_lower]
    # Also check question-specific words
    q_words = set(re.findall(r'\b[a-z]{4,}\b', question.lower())) - \
              {"what", "when", "where", "which", "would", "could", "should", "have", "your", "that", "this", "with"}
    hits += [w for w in q_words if w in text_lower and w not in hits]
    return list(set(hits))[:8]


def _pacing_label(word_count: int) -> str:
    if word_count < WORD_TARGET_MIN:
        return "too_short"
    if word_count > WORD_TARGET_MAX:
        return "too_long"
    return "good"


def _make_tip(word_count: int, filler_count: int, filler_words: List[str], pacing: str, question: str = "") -> str:
    q = (question or "").lower()
    if pacing == "too_short":
        remaining = max(5, WORD_TARGET_MIN - word_count)
        if "tell me about yourself" in q or "introduce" in q:
            return f"Keep going — add your background, one project, and why this role (~{remaining} more words)."
        if "design" in q or "system" in q or "scale" in q:
            return f"Expand with requirements, trade-offs, and one concrete component (~{remaining} more words)."
        return f"Keep going — aim for ~{remaining} more words with a concrete example (STAR helps)."
    if pacing == "too_long":
        return "You're very detailed — start wrapping up with your key takeaway."
    if filler_count > 3:
        examples = ", ".join(f'"{w}"' for w in filler_words[:2])
        return f"Pause instead of filler words ({examples}) — interviewers notice both."
    if filler_count > 0:
        return "Good pace. Swap filler words for a half-second pause before the next point."
    if "star" in q or "experience" in q or "challenge" in q:
        return "Strong flow — make sure you hit Result: what changed because of your action?"
    if word_count >= WORD_TARGET_MIN:
        return "Excellent clarity and length. Land the answer by tying back to the role."
    return "Good start — add one specific example from your resume or project."


def _verify_token(token: str) -> int | None:
    """Return user_id from JWT, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        uid = payload.get("sub")
        return int(uid) if uid else None
    except (JWTError, ValueError):
        return None


@router.websocket("/ws/{session_id}")
async def feedback_websocket(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...),
):
    """
    Real-time coaching WebSocket.
    Authenticate via ?token=<jwt> query parameter.
    """
    user_id = _verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    logger.info(f"Feedback WS opened: session={session_id} user={user_id}")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            text     = msg.get("text", "").strip()
            question = msg.get("question", "")

            if not text:
                await websocket.send_json({"word_count": 0, "tip": "Start speaking..."})
                continue

            word_count              = len(text.split())
            filler_count, fillers   = _count_fillers(text)
            kw_hits                 = _keywords_hit(text, question)
            pacing                  = _pacing_label(word_count)
            tip                     = _make_tip(word_count, filler_count, fillers, pacing, question)
            progress                = min(1.0, word_count / WORD_TARGET_MAX)

            await websocket.send_json({
                "word_count":    word_count,
                "filler_count":  filler_count,
                "filler_words":  fillers,
                "pacing":        pacing,
                "keywords_hit":  kw_hits,
                "tip":           tip,
                "progress":      round(progress, 2),
            })

    except WebSocketDisconnect:
        logger.info(f"Feedback WS closed: session={session_id}")
    except Exception as e:
        logger.error(f"Feedback WS error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
