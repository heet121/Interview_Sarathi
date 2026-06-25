"""
NLP scoring service.

Real, model-backed analysis with a safe heuristic fallback:

  • Semantic relevance  → sentence-transformers `all-MiniLM-L6-v2`
                          (cosine similarity between question and answer)
  • Sentiment           → HuggingFace DistilBERT `sst-2` (real transformer)
  • Keyword extraction  → curated tech vocabulary + capitalised-phrase regex

Both models are lazy-loaded once and cached. If the models cannot be
loaded (e.g. no internet on first run, or torch missing) the service
degrades gracefully to deterministic heuristics so the app never breaks.

`score_answer_nlp()` always returns the same dict shape regardless of
which path was taken, so callers (interview / analysis routers) are stable.
"""

import re
import logging
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Lazy model singletons ─────────────────────────────────────────
_embedder = None
_embedder_failed = False
_embedder_lock = threading.Lock()

_sentiment = None
_sentiment_failed = False
_sentiment_lock = threading.Lock()


def _get_embedder():
    """Load the sentence-transformer once. Returns None if unavailable."""
    global _embedder, _embedder_failed
    if _embedder is not None or _embedder_failed:
        return _embedder
    with _embedder_lock:
        if _embedder is None and not _embedder_failed:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading sentence-transformer 'all-MiniLM-L6-v2'…")
                _embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Sentence-transformer ready ✓")
            except Exception as e:
                logger.warning(f"Embedder unavailable — using heuristic relevance: {e}")
                _embedder_failed = True
    return _embedder


def _get_sentiment():
    """Load the DistilBERT sentiment pipeline once. Returns None if unavailable."""
    global _sentiment, _sentiment_failed
    if _sentiment is not None or _sentiment_failed:
        return _sentiment
    with _sentiment_lock:
        if _sentiment is None and not _sentiment_failed:
            try:
                from transformers import pipeline
                logger.info("Loading DistilBERT sentiment model…")
                _sentiment = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    truncation=True,
                )
                logger.info("Sentiment model ready ✓")
            except Exception as e:
                logger.warning(f"Sentiment model unavailable — using lexicon fallback: {e}")
                _sentiment_failed = True
    return _sentiment


def warm_up() -> None:
    """Optional: preload both models (call in a background thread at startup)."""
    _get_embedder()
    _get_sentiment()


# ── Keyword extraction ────────────────────────────────────────────
TECH_KEYWORDS = {
    "algorithms", "data structures", "complexity", "big-o", "optimization",
    "scalability", "distributed", "microservices", "api", "rest", "graphql",
    "database", "sql", "nosql", "cache", "redis", "kafka", "queue",
    "concurrency", "multithreading", "async", "performance", "latency",
    "design pattern", "solid", "oop", "functional", "recursion", "dynamic programming",
    "binary search", "tree", "graph", "hash", "linked list", "stack",
    "machine learning", "neural network", "deep learning", "python", "java",
    "javascript", "typescript", "react", "node", "docker", "kubernetes",
    "ci/cd", "devops", "testing", "unit test", "tdd", "agile", "scrum",
}


def _extract_keywords(text: str) -> List[str]:
    text_lower = text.lower()
    found: List[str] = []
    for kw in TECH_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    for p in re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", text)[:5]:
        if len(p) > 3 and p not in found:
            found.append(p)
    return found[:10]


def _word_count(text: str) -> int:
    return len(text.split())


def _sentence_count(text: str) -> int:
    return max(1, len([s for s in re.split(r"[.!?]+", text.strip()) if s.strip()]))


# ── Relevance ─────────────────────────────────────────────────────
def _semantic_relevance(question: str, answer: str) -> Optional[float]:
    """Cosine similarity (0–1) between question and answer. None if model unavailable."""
    model = _get_embedder()
    if model is None:
        return None
    try:
        import numpy as np
        emb = model.encode([question, answer], normalize_embeddings=True)
        sim = float(np.dot(emb[0], emb[1]))
        return max(0.0, min(1.0, sim))
    except Exception as e:
        logger.warning(f"Semantic relevance failed: {e}")
        return None


_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "what", "how", "why",
    "can", "you", "i", "we", "to", "of", "in", "for", "with", "that", "this",
}


def _keyword_overlap(question: str, answer: str) -> float:
    q_words = set(question.lower().split()) - _STOP
    a_words = set(answer.lower().split()) - _STOP
    if not q_words:
        return 0.0
    return len(q_words & a_words) / len(q_words)


# ── Sentiment ─────────────────────────────────────────────────────
_POS_WORDS = {"great", "good", "excellent", "strong", "efficient", "optimal",
              "best", "clear", "improved", "solved", "confident", "successful"}
_NEG_WORDS = {"bad", "poor", "slow", "wrong", "fail", "unable", "broken",
              "issue", "problem", "bug", "difficult", "confused"}


def _analyze_sentiment(text: str) -> Tuple[str, float]:
    """Real DistilBERT sentiment, with lexicon fallback. Returns (LABEL, score)."""
    clf = _get_sentiment()
    if clf is not None:
        try:
            r = clf(text[:512])[0]
            return r["label"].upper(), round(float(r["score"]), 3)
        except Exception as e:
            logger.warning(f"Sentiment inference failed: {e}")

    low = text.lower()
    pos = sum(1 for w in _POS_WORDS if w in low)
    neg = sum(1 for w in _NEG_WORDS if w in low)
    if pos > neg:
        return "POSITIVE", round(min(0.95, 0.55 + pos * 0.05), 3)
    if neg > pos:
        return "NEGATIVE", round(min(0.90, 0.55 + neg * 0.05), 3)
    return "NEUTRAL", 0.60


# ── Garbage / non-answer detection ────────────────────────────────
_GARBAGE_EXACT = {
    "[skipped]", "skip", "idk", "nothing", "n/a", "na", "test", "asdf",
    "qwerty", "hello", "hi", "bye", "ok", "okay", "yes", "no", "abc",
    "xyz", "blah", "random", "anything", "something",
}
_GARBAGE_PHRASES = ["i dont know", "i do not know", "no idea", "i have no",
                    "dont know", "don t know", "don't know"]


def _is_garbage(answer: str, wc: int) -> bool:
    low = answer.lower().strip()
    if wc < 4:
        return True
    if low in _GARBAGE_EXACT:
        return True
    if any(p in low for p in _GARBAGE_PHRASES):
        return True
    if len(set(low.split())) < 3:   # same word repeated
        return True
    return False


# ── Core scoring ──────────────────────────────────────────────────
def _compute_scores(question: str, answer: str) -> Dict:
    wc = _word_count(answer)
    sc = _sentence_count(answer)
    keywords = _extract_keywords(answer)

    if _is_garbage(answer, wc):
        return {
            "content_score": 5.0,
            "communication_score": 5.0,
            "relevance_score": 5.0,
            "bert_label": "NEGATIVE",
            "bert_score": 0.1,
            "keywords": [],
            "word_count": wc,
            "relevance_engine": "rule",
        }

    # ── Relevance: prefer semantic model, blend with keyword overlap ──
    sem = _semantic_relevance(question, answer)
    overlap = _keyword_overlap(question, answer)
    if sem is not None:
        # MiniLM Q↔A cosine: ~0.6+ is very on-topic, <0.2 is off-topic.
        sem_scaled = min(95.0, max(5.0, sem * 135.0))
        relevance = round(0.75 * sem_scaled + 0.25 * min(95.0, overlap * 100), 1)
        engine = "minilm"
    else:
        relevance = round(min(95.0, max(8.0, 35.0 + overlap * 65)), 1)
        engine = "heuristic"

    rel_ratio = relevance / 100.0
    keyword_bonus = len(keywords) * 4

    # ── Content: depth (length) + keywords + relevance ──
    if wc < 15:
        content = 25.0 + keyword_bonus + rel_ratio * 20
    elif wc < 50:
        content = 40.0 + keyword_bonus + rel_ratio * 25
    elif wc < 150:
        content = 52.0 + keyword_bonus + rel_ratio * 25
    else:
        content = 58.0 + keyword_bonus + rel_ratio * 20

    # ── Communication: sentence structure + length sweet-spot ──
    avg_sent_len = wc / sc
    if wc < 15:
        comm = 30.0 + rel_ratio * 20
    elif 8 <= avg_sent_len <= 25:
        comm = 50.0 + wc / 6 + rel_ratio * 15
    else:
        comm = 42.0 + wc / 8 + rel_ratio * 10

    bert_label, bert_score = _analyze_sentiment(answer)

    return {
        "content_score": round(min(92, max(5, content)), 1),
        "communication_score": round(min(92, max(5, comm)), 1),
        "relevance_score": round(min(95, max(5, relevance)), 1),
        "bert_label": bert_label,
        "bert_score": bert_score,
        "keywords": keywords,
        "word_count": wc,
        "relevance_engine": engine,
    }


def score_answer_nlp(question: str, answer: str) -> Dict:
    try:
        return _compute_scores(question, answer)
    except Exception as e:
        logger.error(f"NLP scoring error: {e}")
        return {
            "content_score": 60.0,
            "communication_score": 60.0,
            "relevance_score": 60.0,
            "bert_label": "NEUTRAL",
            "bert_score": 0.65,
            "keywords": [],
            "word_count": len(answer.split()),
            "relevance_engine": "error-fallback",
        }
