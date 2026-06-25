"""
Interview answer judge — DeBERTa multi-head regression scorer.

Scores (question, answer) on: relevance, correctness, depth, communication, structure.
Falls back to nlp_service heuristics if model not loaded.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Dict

logger = logging.getLogger(__name__)

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

DIMS = ["relevance", "correctness", "depth", "communication", "structure"]

_model = None
_tokenizer = None
_model_failed = False
_lock = threading.Lock()
_device = "cpu"


def _resolve_path() -> str:
    rel = os.environ.get("JUDGE_MODEL_PATH", "")
    if rel and os.path.isdir(rel):
        return rel
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default = os.path.join(base, "models", "judge", "deberta-v3-base-v1")
    return default


def _load():
    global _model, _tokenizer, _model_failed, _device
    if _model is not None or _model_failed:
        return _model
    with _lock:
        if _model is None and not _model_failed:
            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                path = _resolve_path()
                if not os.path.isdir(path):
                    logger.warning(f"Judge model not found at {path}")
                    _model_failed = True
                    return None

                _device = "cuda" if torch.cuda.is_available() else "cpu"
                _tokenizer = AutoTokenizer.from_pretrained(path)
                _model = AutoModelForSequenceClassification.from_pretrained(path)
                _model.to(_device)
                _model.eval()
                logger.info(f"Judge model loaded from {path} on {_device}")
            except Exception as e:
                logger.warning(f"Judge model load failed: {e}")
                _model_failed = True
    return _model


def _calibrate(logits) -> Dict[str, float]:
    """Map raw regression outputs to 0–100 scores."""
    import torch
    out = {}
    for dim, v in zip(DIMS, logits):
        # Training targets were 0–1; apply sigmoid for stable 0–100 display
        s = torch.sigmoid(torch.tensor(float(v))).item() * 100.0
        out[dim] = round(max(0.0, min(100.0, s)), 1)
    return out


def score_answer_judge(question: str, answer: str) -> Dict:
    """Returns dim scores 0–100, overall, and engine tag."""
    model = _load()
    if model is None:
        from nlp_service import score_answer_nlp
        nlp = score_answer_nlp(question, answer)
        rel = nlp.get("relevance_score", 50)
        comm = nlp.get("communication_score", 50)
        content = nlp.get("content_score", 50)
        return {
            "relevance": rel,
            "correctness": content,
            "depth": min(100, len(answer.split()) * 2),
            "communication": comm,
            "structure": comm,
            "overall": round((rel + content + comm) / 3, 1),
            "engine": "nlp_fallback",
        }

    import torch
    tok = _tokenizer
    text = f"Question: {question} Answer: {answer}"
    enc = tok(text, truncation=True, padding=True, max_length=256, return_tensors="pt")
    enc = {k: v.to(_device) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits.squeeze(0).tolist()

    scores = _calibrate(logits)
    overall = round(sum(scores.values()) / len(DIMS), 1)
    return {**scores, "overall": overall, "engine": "deberta_judge"}


def warm_up() -> None:
    _load()
