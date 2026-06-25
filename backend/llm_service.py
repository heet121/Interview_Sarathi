"""
LLM Service — Anthropic Claude (Sonnet 4.6) with optional Gemini fallback
- Generates interview questions (seeded from real company dataset)
- Scores answers with AI
- Deep post-interview analysis
- Retry logic on 429 / 5xx
- Question difficulty progression (easy → medium → hard)

Provider is chosen by settings.LLM_PROVIDER:
  "auto"     → Claude if ANTHROPIC_API_KEY is set, otherwise Gemini
  "claude"   → always Claude
  "gemini"   → always Gemini
  "offline"  → no cloud LLM; dataset questions + DeBERTa judge scoring only
Either way, every call degrades gracefully to local dataset / heuristic
fallbacks so an interview never breaks.
"""

import asyncio
import json
import logging
import random
import httpx
from config import settings

logger = logging.getLogger(__name__)

GEMINI_URL = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent"


def _has_claude_key() -> bool:
    k = (settings.ANTHROPIC_API_KEY or "").strip()
    return bool(k) and not k.lower().startswith("your-")


def llm_enabled() -> bool:
    """True when cloud LLM (Claude/Gemini) may be called."""
    p = (settings.LLM_PROVIDER or "auto").lower()
    return p not in ("offline", "none", "disabled")


def _provider() -> str:
    """Resolve which LLM provider to use."""
    if not llm_enabled():
        return "offline"
    p = (settings.LLM_PROVIDER or "auto").lower()
    if p == "claude":
        return "claude"
    if p == "gemini":
        return "gemini"
    # auto
    return "claude" if _has_claude_key() else "gemini"


async def _call_llm(
    prompt: str,
    system: str = "",
    temperature: float = 0.7,
    max_retries: int = 2,
) -> str:
    """Dispatch to the configured LLM provider."""
    if not llm_enabled():
        raise RuntimeError("LLM disabled (LLM_PROVIDER=offline)")
    if _provider() == "claude":
        return await _call_claude(prompt, system, max_retries=max_retries)
    return await _call_gemini(prompt, system, temperature=temperature, max_retries=max_retries)


async def _call_claude(
    prompt: str,
    system: str = "",
    max_retries: int = 2,
) -> str:
    """
    Call Anthropic Claude (Sonnet 4.6) via the Messages API using adaptive
    thinking + the effort parameter (settings.ANTHROPIC_EFFORT, default "high").
    Note: temperature is intentionally not sent — extended thinking requires
    the default sampling temperature.
    """
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": settings.ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": settings.ANTHROPIC_MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": settings.ANTHROPIC_EFFORT},
    }
    if system:
        body["system"] = system

    url = f"{settings.ANTHROPIC_BASE_URL}/messages"
    last_error = None
    for attempt in range(max_retries):
        try:
            # High-effort thinking can take a while — allow a generous timeout.
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, headers=headers, json=body)

            if resp.status_code == 429 or resp.status_code >= 500:
                wait = attempt + 1
                logger.warning(
                    f"Claude returned {resp.status_code}, "
                    f"retrying in {wait}s (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(wait)
                last_error = f"HTTP {resp.status_code}"
                continue

            if resp.status_code >= 400:
                # 4xx (bad key / bad request) won't fix on retry — fail fast to fallback.
                logger.error(f"Claude error {resp.status_code}: {resp.text[:300]}")
                raise RuntimeError(f"Claude HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            # content is a list of blocks; thinking blocks are separate from text.
            text = "".join(
                b.get("text", "") for b in data.get("content", [])
                if b.get("type") == "text"
            )
            return text.strip()

        except httpx.TimeoutException:
            wait = attempt + 1
            logger.warning(f"Claude timeout, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait)
            last_error = "timeout"
        except RuntimeError:
            raise
        except Exception as e:
            last_error = str(e)
            logger.error(f"Claude call failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(attempt + 1)

    raise RuntimeError(f"Claude API unavailable after {max_retries} attempts: {last_error}")

# Difficulty ladder used for question progression
_DIFFICULTY_LADDER = ["easy", "easy", "medium", "medium", "hard"]


def _question_difficulty(question_index: int, num_questions: int, base_difficulty: str) -> str:
    """
    Return a per-question difficulty label that ramps up through the interview.
    e.g. for 5 questions: easy, easy, medium, medium, hard
    """
    if base_difficulty == "easy":
        ladder = ["easy", "easy", "easy", "medium", "medium"]
    elif base_difficulty == "hard":
        ladder = ["medium", "hard", "hard", "hard", "hard"]
    else:  # medium (default)
        ladder = _DIFFICULTY_LADDER

    n = max(1, num_questions)
    # Map question_index into the 5-step ladder regardless of total questions
    step = min(4, int(question_index / n * 5))
    return ladder[step]


def _strip_markdown_json(raw: str) -> str:
    """Strip ```json ... ``` fences that Gemini sometimes wraps around JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw[raw.index("\n") + 1:] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
    return raw.strip()


async def _call_gemini(
    prompt: str,
    system: str = "",
    temperature: float = 0.7,
    max_retries: int = 2,
) -> str:
    """
    Call Gemini API with exponential backoff retry on rate-limit (429)
    or server errors (5xx).
    """
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.GEMINI_API_KEY,
    }
    contents = []
    if system:
        contents.append({"role": "user",  "parts": [{"text": f"[System]: {system}"}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    body = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 1500,
        },
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(GEMINI_URL, headers=headers, json=body)

            if resp.status_code == 429 or resp.status_code >= 500:
                wait = attempt + 1           # 1s, 2s — fail fast, fallback is good
                logger.warning(
                    f"Gemini returned {resp.status_code}, "
                    f"retrying in {wait}s (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(wait)
                last_error = f"HTTP {resp.status_code}"
                continue

            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except httpx.TimeoutException:
            wait = 2 ** attempt
            logger.warning(f"Gemini timeout, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(wait)
            last_error = "timeout"
        except Exception as e:
            last_error = str(e)
            logger.error(f"Gemini call failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

    raise RuntimeError(f"Gemini API unavailable after {max_retries} attempts: {last_error}")


def _offline_first_question(cfg: dict, dataset_questions: list | None = None) -> str:
    """Opening greeting + first question from the local dataset (no cloud LLM)."""
    name = cfg.get("name", "there")
    company = cfg.get("company", "the company")
    role = cfg.get("role", "Software Engineer")
    if dataset_questions:
        q = dataset_questions[0]
    else:
        openers = [
            f"Tell me about yourself and what draws you to the {role} role.",
            f"Walk me through your background and why you applied for this {role} position.",
            f"Start by introducing yourself and your relevant experience for this {role} role.",
        ]
        q = random.choice(openers)
    return (
        f"Welcome {name}! I am your AI interviewer for the {role} position at {company}. "
        f"Let us get started. {q}"
    )


def _offline_followup(
    cfg: dict,
    history: list,
    is_last: bool,
    dataset_questions: list | None = None,
    question_index: int = 1,
) -> str:
    """Next question or closing line from the local dataset (no cloud LLM)."""
    if is_last:
        closers = [
            "Thank you for completing this interview! Your responses have been recorded and feedback will follow.",
            "That wraps up our interview. Well done for completing all questions — your analysis will be ready shortly.",
            "Great effort! You have answered all questions. Your detailed feedback report is being prepared.",
        ]
        return random.choice(closers)

    fallback_questions = [
        "Can you describe a challenging technical problem you solved and how you approached it?",
        "Tell me about a time you had to learn a new technology quickly. How did you handle it?",
        "How do you ensure code quality in your projects?",
        "Describe a situation where you had to work under pressure to meet a deadline.",
        "What is your approach to debugging a complex issue in production?",
        "How do you handle disagreements with teammates on technical decisions?",
        "Walk me through how you would design a scalable REST API.",
        "Tell me about a project you are most proud of and your specific contribution.",
    ]
    asked_norm = {
        " ".join((m["content"] or "").split()).strip().lower()
        for m in history if m.get("role") == "assistant"
    }

    def _is_new(text: str) -> bool:
        return " ".join((text or "").split()).strip().lower() not in asked_norm

    q = None
    if dataset_questions:
        if question_index < len(dataset_questions) and _is_new(dataset_questions[question_index]):
            q = dataset_questions[question_index]
        else:
            q = next((c for c in dataset_questions if _is_new(c)), None)
    if not q:
        q = next((c for c in fallback_questions if _is_new(c)), None)
    if not q:
        q = fallback_questions[question_index % len(fallback_questions)]

    transitions = [
        "Good effort. Next question: ",
        "Alright, moving on: ",
        "Thank you. Here is your next question: ",
        "Noted. Let us continue: ",
    ]
    return random.choice(transitions) + q


def _build_judge_analysis(cfg: dict, qa_log: list, posture_summary: str = "") -> dict:
    """Post-interview report built entirely from DeBERTa judge + NLP (no cloud LLM)."""
    from scoring_service import score_answer_sync

    qa_breakdown = []
    scores = []
    dim_relevance, dim_correctness, dim_depth, dim_comm, dim_structure = [], [], [], [], []
    for item in qa_log:
        scored = score_answer_sync(item["question"], item["answer"])
        content_s = scored["content_score"]
        comm_s = scored["communication_score"]
        rel_s = scored["relevance_score"]
        js = scored.get("judge_scores") or {}
        avg_score = scored["overall_score"]
        scores.append(avg_score)
        if js:
            dim_relevance.append(js.get("relevance", rel_s))
            dim_correctness.append(js.get("correctness", content_s))
            dim_depth.append(js.get("depth", 50))
            dim_comm.append(js.get("communication", comm_s))
            dim_structure.append(js.get("structure", comm_s))
        wc = scored["word_count"]
        kws = scored["keywords"]
        nlp = {"bert_label": scored["bert_label"], "word_count": wc}
        answer_lower = item["answer"].lower().strip()
        is_skipped = "[skipped]" in answer_lower

        if is_skipped:
            feedback = "Question was skipped. Make sure to attempt every question — even a partial answer scores better than skipping."
        elif wc < 5:
            feedback = "Answer was too short to evaluate. Aim for at least 50-100 words with specific examples."
        elif rel_s < 30:
            feedback = f"Your answer did not clearly address the question asked. Re-read the question carefully and focus your response on the specific topic. Keywords expected: {', '.join(kws[:3]) if kws else 'none detected'}."
        elif avg_score < 40:
            feedback = f"Weak answer. You need more depth and relevance. The question was about: '{item['question'][:80]}'. Try to include concrete examples and technical terms."
        elif avg_score < 60:
            if kws:
                feedback = f"Decent attempt. You mentioned {len(kws)} relevant keyword(s): {', '.join(kws[:4])}. Expand with a real example using the STAR method (Situation, Task, Action, Result)."
            else:
                feedback = "Partial answer. Add technical keywords and a concrete example from your experience to improve your score."
        elif avg_score < 75:
            feedback = f"Good answer with {wc} words. You covered the basics well. To score higher, add more specific implementation details or quantify your impact (e.g., 'reduced latency by 30%')."
        else:
            feedback = f"Strong answer! You used {len(kws)} relevant technical terms and gave a clear response. Well structured and on-point."

        qa_breakdown.append({
            "question": item["question"],
            "answer": item["answer"],
            "feedback": feedback,
            "contentScore": content_s,
            "communicationScore": comm_s,
            "relevanceScore": rel_s,
            "judgeOverall": scored.get("judge_overall"),
            "judgeScores": js,
            "scoringEngine": scored.get("scoring_engine"),
            "sentiment": nlp["bert_label"].lower(),
            "keywords": kws,
        })
    overall = round(sum(scores) / len(scores), 1) if scores else 40
    verdict = "Excellent" if overall >= 85 else "Good" if overall >= 70 else "Average" if overall >= 55 else "Needs Work"
    n = max(1, len(qa_breakdown))
    rel_avg = round(sum(dim_relevance) / len(dim_relevance), 1) if dim_relevance else overall
    corr_avg = round(sum(dim_correctness) / len(dim_correctness), 1) if dim_correctness else overall
    depth_avg = round(sum(dim_depth) / len(dim_depth), 1) if dim_depth else max(10, overall - 10)
    comm_avg = round(sum(dim_comm) / len(dim_comm), 1) if dim_comm else round(sum(x["communicationScore"] for x in qa_breakdown) / n, 1)
    struct_avg = round(sum(dim_structure) / len(dim_structure), 1) if dim_structure else depth_avg
    posture_comment = posture_summary or "Camera not used or no posture data."
    return {
        "overallScore": overall,
        "verdict": verdict,
        "overallSummary": (
            f"Interview completed with {len(qa_log)} questions. "
            f"DeBERTa judge score: {overall}/100. Focus on detailed, relevant answers with specific examples."
        ),
        "strengths": ["Completed the full interview"] if overall >= 50 else ["Attempted the interview"],
        "improvements": [
            "Give longer, more detailed answers (aim for 100+ words)",
            "Use specific examples from your experience",
            "Make sure answers are relevant to the question asked",
        ],
        "dimensions": {
            "Content & Knowledge": {"score": corr_avg, "comment": "DeBERTa judge: correctness & technical depth."},
            "Communication": {"score": comm_avg, "comment": "Clarity and articulation from judge model."},
            "Confidence": {"score": min(85, overall + 5), "comment": "Estimated from answer quality."},
            "Relevance": {"score": rel_avg, "comment": "How well answers addressed the questions."},
            "STAR Structure": {"score": struct_avg, "comment": "Answer structure and organization."},
            "Posture & Presence": {"score": 50, "comment": posture_comment},
        },
        "qaBreakdown": qa_breakdown,
        "roadmap": [
            "Practice answering questions with the STAR method",
            "Record yourself answering common interview questions",
            "Research the company and role before each interview",
        ],
    }


async def generate_first_question(cfg: dict, dataset_questions: list = None) -> str:
    """
    Generate the opening greeting + first interview question (always 'easy' difficulty).
    Uses real company dataset questions as inspiration when available.
    """
    dataset_hint = ""
    if dataset_questions:
        sample = dataset_questions[:3]
        dataset_hint = (
            f"\nUse these REAL interview questions from "
            f"{cfg.get('company', 'the company')} as inspiration (pick or adapt one):\n"
            + "\n".join(f"- {q}" for q in sample) + "\n"
        )

    resume_section = ""
    if cfg.get("resume_text"):
        resume_section = (
            f"\nCandidate's resume highlights:\n{cfg['resume_text'][:800]}\n"
            "Reference their actual experience/projects when asking the first question.\n"
        )

    skills_section = ""
    if cfg.get("resume_skills"):
        skills_section = f"Detected skills from resume: {', '.join(cfg['resume_skills'][:10])}\n"

    system = (
        f"You are a professional AI interviewer at {cfg.get('company', 'a top tech company')} "
        f"conducting a {cfg.get('interview_type', 'technical')} interview for a "
        f"{cfg.get('role', 'Software Engineer')} position. "
        "Be professional, warm, and concise. Ask ONE question at a time."
    )

    prompt = (
        f"Greet the candidate {cfg.get('name', 'there')} warmly (1-2 sentences), "
        "then ask your first interview question.\n\n"
        f"Interview context:\n"
        f"- Company: {cfg.get('company', 'N/A')}\n"
        f"- Role: {cfg.get('role', 'Software Engineer')}\n"
        f"- Type: {cfg.get('interview_type', 'technical')}\n"
        f"- This is question 1 of {cfg.get('num_questions', 5)} — start EASY to warm up the candidate.\n"
        f"- Skills focus: {cfg.get('skills', 'General')}\n"
        f"{skills_section}"
        f"{dataset_hint}"
        f"{resume_section}"
        "Keep your response under 100 words. Ask ONE clear, easy warm-up question."
    )

    if not llm_enabled():
        logger.info("LLM offline — using dataset for first question")
        return _offline_first_question(cfg, dataset_questions)

    try:
        return await _call_llm(prompt, system)
    except Exception as e:
        logger.warning(f"LLM first-question failed, using fallback: {e}")
        return _offline_first_question(cfg, dataset_questions)


async def generate_followup(
    cfg: dict,
    history: list,
    last_answer: str,
    is_last: bool,
    dataset_questions: list = None,
    question_index: int = 1,
) -> str:
    """
    Generate a follow-up question with progressive difficulty, or closing remarks.
    difficulty ramps: easy → easy → medium → medium → hard
    """
    num_questions = cfg.get("num_questions", 5) or 5
    base_difficulty = cfg.get("difficulty", "medium") or "medium"
    current_difficulty = _question_difficulty(question_index, num_questions, base_difficulty)

    dataset_hint = ""
    if dataset_questions and not is_last:
        already_used = len(history) // 2
        remaining = dataset_questions[already_used: already_used + 3]
        if remaining:
            dataset_hint = (
                f"\nConsider using or adapting one of these real "
                f"{cfg.get('company', 'company')} questions:\n"
                + "\n".join(f"- {q}" for q in remaining)
            )

    system = (
        f"You are an AI interviewer at {cfg.get('company', 'a tech company')} for a "
        f"{cfg.get('role', 'Software Engineer')} position. Be concise, professional."
    )

    if is_last:
        prompt = (
            f'The candidate just answered the final question.\n'
            f'Their answer: "{last_answer[:300]}"\n\n'
            "Give brief positive closing remarks (2-3 sentences). "
            "Thank them, say the interview is complete, and mention feedback will be shared. "
            "Be warm but professional."
        )
        history_str = "\n".join(
            f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content'][:200]}"
            for m in history[-6:]
        )
        asked = [m["content"] for m in history if m.get("role") == "assistant"]
        avoid_block = ""
        if asked:
            avoid_block = (
                "\nQuestions ALREADY asked — do NOT repeat or rephrase any of these, "
                "ask something clearly different:\n"
                + "\n".join(f"- {a[:140]}" for a in asked[-10:]) + "\n"
            )
        prompt = (
            f"Interview history:\n{history_str}\n\n"
            f'Candidate\'s latest answer: "{last_answer[:300]}"\n'
            f"{avoid_block}"
            f"{dataset_hint}\n\n"
            f"This is question {question_index + 1} of {num_questions}.\n"
            f"Difficulty for this question: {current_difficulty.upper()} "
            f"({'increase complexity' if current_difficulty in ('medium','hard') else 'keep it approachable'}).\n\n"
            "Acknowledge their answer briefly (1 sentence), then ask ONE NEW question "
            "that has not been asked yet.\n"
            "Keep total response under 80 words."
        )

    if not llm_enabled():
        logger.info("LLM offline — using dataset for follow-up")
        return _offline_followup(cfg, history, is_last, dataset_questions, question_index)

    try:
        return await _call_llm(prompt, system)
    except Exception as e:
        logger.warning(f"LLM follow-up failed, using fallback: {e}")
        return _offline_followup(cfg, history, is_last, dataset_questions, question_index)


async def score_answer_with_llm(
    question: str, answer: str, company: str = "", role: str = ""
) -> dict:
    """
    Use Gemini to score and evaluate a candidate's answer.
    Returns: score, verdict, feedback, strengths, improvements, keywords_mentioned, keywords_missing
    """
    prompt = (
        f"You are an expert technical interviewer at {company or 'a top tech company'} "
        f"evaluating a candidate for {role or 'Software Engineer'}.\n\n"
        f"Question: {question}\n\n"
        f"Candidate's Answer: {answer}\n\n"
        "Evaluate and respond ONLY with valid JSON (no markdown, no backticks):\n"
        "{\n"
        '  "score": <0-100 integer>,\n'
        '  "verdict": "<Excellent|Good|Average|Needs Work>",\n'
        '  "feedback": "<2-3 sentence honest assessment>",\n'
        '  "strengths": ["<strength 1>", "<strength 2>"],\n'
        '  "improvements": ["<improvement 1>", "<improvement 2>"],\n'
        '  "keywords_mentioned": ["<keyword>"],\n'
        '  "keywords_missing": ["<important keyword not mentioned>"]\n'
        "}\n\n"
        "Score based on: technical accuracy (40%), completeness (30%), clarity (30%)."
    )

    try:
        raw = await _call_llm(prompt, temperature=0.3)
        return json.loads(_strip_markdown_json(raw))
    except Exception as e:
        logger.error(f"LLM scoring failed: {e}")
        return {
            "score": 60,
            "verdict": "Average",
            "feedback": "Unable to generate detailed feedback at this time.",
            "strengths": [],
            "improvements": ["Provide more detail in your answer"],
            "keywords_mentioned": [],
            "keywords_missing": [],
        }


async def run_deep_analysis(cfg: dict, qa_log: list, posture_summary: str = "") -> dict:
    """Full post-interview analysis via Gemini."""
    qa_text = "\n\n".join(
        f"Q{i+1}: {item['question']}\nA: {item['answer']}"
        for i, item in enumerate(qa_log)
    )
    posture_line = f"Posture/Body Language: {posture_summary}" if posture_summary else ""

    prompt = (
        "You are an expert interview coach analyzing a completed interview.\n\n"
        f"Candidate: {cfg.get('name', 'Candidate')}\n"
        f"Company: {cfg.get('company', 'N/A')} | Role: {cfg.get('role', 'N/A')}\n"
        f"Type: {cfg.get('interview_type', 'technical')} | Difficulty: {cfg.get('difficulty', 'medium')}\n\n"
        f"Interview Q&A:\n{qa_text}\n\n"
        f"{posture_line}\n\n"
        "Respond ONLY with valid JSON (no markdown backticks):\n"
        "{\n"
        '  "overallScore": <0-100>,\n'
        '  "verdict": "<Excellent|Good|Average|Needs Work>",\n'
        '  "overallSummary": "<3-4 sentence comprehensive summary>",\n'
        '  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],\n'
        '  "improvements": ["<area 1>", "<area 2>", "<area 3>"],\n'
        '  "dimensions": {\n'
        '    "Content & Knowledge": {"score": <0-100>, "comment": "<brief>"},\n'
        '    "Communication":       {"score": <0-100>, "comment": "<brief>"},\n'
        '    "Confidence":          {"score": <0-100>, "comment": "<brief>"},\n'
        '    "Relevance":           {"score": <0-100>, "comment": "<brief>"},\n'
        '    "STAR Structure":      {"score": <0-100>, "comment": "<brief>"},\n'
        '    "Posture & Presence":  {"score": <0-100>, "comment": "<brief>"}\n'
        '  },\n'
        '  "qaBreakdown": [\n'
        '    {\n'
        '      "question": "<question>",\n'
        '      "answer": "<answer summary>",\n'
        '      "feedback": "<specific feedback>",\n'
        '      "contentScore": <0-100>,\n'
        '      "communicationScore": <0-100>,\n'
        '      "sentiment": "<positive|neutral|negative>"\n'
        '    }\n'
        '  ],\n'
        '  "roadmap": ["<action item 1>", "<action item 2>", "<action item 3>"]\n'
        "}"
    )

    if not llm_enabled():
        logger.info("LLM offline — using DeBERTa judge for session analysis")
        return _build_judge_analysis(cfg, qa_log, posture_summary)

    try:
        raw = await _call_llm(prompt, temperature=0.4)
        return json.loads(_strip_markdown_json(raw))
    except Exception as e:
        logger.error(f"Deep analysis failed: {e}")
        return _build_judge_analysis(cfg, qa_log, posture_summary)