import json
import os
import random
import re
import logging
from typing import List, Optional, Dict
import urllib.request

from config import settings

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(settings.DATASET_DIR, "questions_cache.json")

# ── Company list ──────────────────────────────────────────────────
DATASET_COMPANIES = [
    "Adobe", "AirAsia", "Amazon", "AmericanExpress", "Atlassian",
    "BookMyShow", "Box", "Expedia", "Facebook", "Flipkart",
    "Google", "Grab", "Groupon", "Intuit", "LinkedIn",
    "Microsoft", "MobiKwik", "NEC Technologies", "Netflix", "Ola Cabs",
    "Palantir", "PayPal", "Samsung", "Thoughtworks", "Twitter",
    "Uber", "Walmart Labs", "Yatra.com", "Zomato",
]

COMPANY_META = {
    "Adobe":           {"color": "#FF0000", "emoji": "🎨", "sector": "Software"},
    "AirAsia":         {"color": "#FF0000", "emoji": "✈️",  "sector": "Aviation"},
    "Amazon":          {"color": "#FF9900", "emoji": "📦", "sector": "E-Commerce/Cloud"},
    "AmericanExpress": {"color": "#006FCF", "emoji": "💳", "sector": "FinTech"},
    "Atlassian":       {"color": "#0052CC", "emoji": "🔧", "sector": "DevTools"},
    "BookMyShow":      {"color": "#E84545", "emoji": "🎬", "sector": "Entertainment"},
    "Box":             {"color": "#0061D5", "emoji": "📁", "sector": "Cloud Storage"},
    "Expedia":         {"color": "#FFC72C", "emoji": "🌍", "sector": "Travel"},
    "Facebook":        {"color": "#1877F2", "emoji": "📘", "sector": "Social Media"},
    "Flipkart":        {"color": "#F74D0A", "emoji": "🛒", "sector": "E-Commerce"},
    "Google":          {"color": "#4285F4", "emoji": "🔍", "sector": "Tech/Cloud"},
    "Grab":            {"color": "#00B14F", "emoji": "🚗", "sector": "Super App"},
    "Groupon":         {"color": "#53A318", "emoji": "🎁", "sector": "Deals"},
    "Intuit":          {"color": "#236CFF", "emoji": "💰", "sector": "FinTech"},
    "LinkedIn":        {"color": "#0A66C2", "emoji": "💼", "sector": "Professional Network"},
    "Microsoft":       {"color": "#00A4EF", "emoji": "🖥️", "sector": "Tech/Cloud"},
    "MobiKwik":        {"color": "#00BAF2", "emoji": "📱", "sector": "FinTech"},
    "NEC Technologies":{"color": "#003087", "emoji": "⚡", "sector": "Tech"},
    "Netflix":         {"color": "#E50914", "emoji": "🎥", "sector": "Streaming"},
    "Ola Cabs":        {"color": "#FFC21A", "emoji": "🚕", "sector": "Ride-Hailing"},
    "Palantir":        {"color": "#101113", "emoji": "🔮", "sector": "Data/Analytics"},
    "PayPal":          {"color": "#003087", "emoji": "💸", "sector": "FinTech"},
    "Samsung":         {"color": "#1428A0", "emoji": "📱", "sector": "Electronics"},
    "Thoughtworks":    {"color": "#EC1B23", "emoji": "💡", "sector": "Consulting"},
    "Twitter":         {"color": "#1DA1F2", "emoji": "🐦", "sector": "Social Media"},
    "Uber":            {"color": "#000000", "emoji": "🚘", "sector": "Ride-Hailing"},
    "Walmart Labs":    {"color": "#0071CE", "emoji": "🛍️", "sector": "Retail/Tech"},
    "Yatra.com":       {"color": "#FF6600", "emoji": "🏖️", "sector": "Travel"},
    "Zomato":          {"color": "#E23744", "emoji": "🍕", "sector": "Food Delivery"},
}

# In-memory cache: {company_name: [question, ...]}
_question_cache: Dict[str, List[str]] = {}
_cache_loaded = False


# ── Cache persistence ─────────────────────────────────────────────

def _save_cache_to_disk():
    """Persist the in-memory cache to a JSON file for fast future startups."""
    try:
        os.makedirs(settings.DATASET_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_question_cache, f, ensure_ascii=False, indent=2)
        logger.info(f"Dataset cache saved to {CACHE_FILE}")
    except Exception as e:
        logger.warning(f"Could not save dataset cache: {e}")


def _load_cache_from_disk() -> bool:
    """
    Load questions from the local JSON cache file.
    Returns True if the cache was loaded successfully, False otherwise.
    """
    global _question_cache, _cache_loaded
    if not os.path.exists(CACHE_FILE):
        return False
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            _question_cache = data
            _cache_loaded = True
            total = sum(len(v) for v in data.values())
            logger.info(f"Loaded {total} questions for {len(data)} companies from disk cache")
            return True
    except Exception as e:
        logger.warning(f"Could not read disk cache: {e}")
    return False


# ── GitHub fetching ───────────────────────────────────────────────

def _fetch_company_questions(company: str) -> List[str]:
    """Fetch README.md from GitHub for a company and extract questions."""
    encoded = company.replace(" ", "%20")
    url = f"https://raw.githubusercontent.com/grg124/Interview-Questions/master/{encoded}/README.md"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
        questions = _parse_readme_questions(content)
        logger.info(f"Fetched {len(questions)} questions for {company} from GitHub")
        return questions
    except Exception as e:
        logger.warning(f"Could not fetch questions for {company}: {e}")
        return []


def _parse_readme_questions(content: str) -> List[str]:
    """Extract question lines from a README.md file."""
    questions = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("---"):
            continue
        for prefix in ["- ", "* ", "1. ", "2. ", "3. "]:
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        line = line.strip()
        if len(line) > 15 and ("?" in line or any(
            line.lower().startswith(w) for w in [
                "what", "how", "why", "when", "which", "explain",
                "describe", "design", "implement", "write", "find",
                "given", "you are", "a company", "tell", "discuss",
            ]
        )):
            line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
            if len(line) > 15:
                questions.append(line)
    return questions


# ── Question Bank seeding ─────────────────────────────────────────

# Fallback questions used when GitHub is unreachable AND no disk cache exists.
# Organised by company so the most important ones always have coverage.
_SEED_QUESTIONS: Dict[str, List[str]] = {
    "Google": [
        "Design a URL shortening service like bit.ly. Walk me through the system design.",
        "How would you find the median from a data stream in real time?",
        "Explain the difference between a process and a thread.",
        "What is consistent hashing and when would you use it?",
        "How does Google Search index billions of web pages efficiently?",
    ],
    "Amazon": [
        "Design Amazon's product recommendation system.",
        "Tell me about a time you dealt with a difficult customer. What did you do?",
        "How would you design a distributed rate limiter?",
        "Describe a situation where you had to make a decision with incomplete information.",
        "How would you design Amazon's order fulfilment system?",
    ],
    "Microsoft": [
        "Design a collaborative document editing system like Google Docs.",
        "What is the difference between abstract classes and interfaces in OOP?",
        "How would you detect a cycle in a linked list?",
        "Explain how garbage collection works in modern programming languages.",
        "Design a parking lot system — what are the key classes and relationships?",
    ],
    "Facebook": [
        "Design Facebook's News Feed ranking system.",
        "How would you store and query a social graph efficiently?",
        "Design a real-time messaging system for 1 billion users.",
        "What are the trade-offs between SQL and NoSQL databases?",
        "How would you detect fake accounts on a social network?",
    ],
    "Netflix": [
        "How would you design Netflix's video streaming and CDN architecture?",
        "Explain how you would build a recommendation engine for movies.",
        "How does Netflix achieve 99.99% uptime across global regions?",
        "Design a system to handle video encoding for millions of uploads per day.",
        "What is chaos engineering and why does Netflix use it?",
    ],
    "Uber": [
        "Design Uber's real-time ride matching system.",
        "How would you implement surge pricing based on supply and demand?",
        "Design a GPS tracking system that handles millions of drivers simultaneously.",
        "How would you handle payment failures gracefully in a distributed system?",
        "Explain the CAP theorem and how it applies to Uber's architecture.",
    ],
    "LinkedIn": [
        "Design LinkedIn's 'People You May Know' feature.",
        "How would you implement full-text search across millions of profiles?",
        "Design a notification system that sends emails, push and in-app alerts.",
        "How would you scale LinkedIn's job recommendation algorithm?",
        "What data structures would you use to model a professional network graph?",
    ],
    "Twitter": [
        "Design Twitter's tweet delivery system for 300M users.",
        "How would you implement Twitter's trending topics feature?",
        "Design a system to detect and remove abusive content in real time.",
        "How would you handle the celebrity problem (e.g. Obama tweets to 50M followers)?",
        "Explain eventual consistency with a real-world Twitter example.",
    ],
    "Adobe": [
        "How would you design a collaborative image editing tool in the cloud?",
        "Explain how rasterization works in graphics rendering pipelines.",
        "Design a system for versioning large creative files (PSD, AI, etc.).",
        "What is the difference between lossy and lossless image compression?",
        "How would you build a plugin architecture for a creative application?",
    ],
    "Flipkart": [
        "Design Flipkart's flash sale system to handle 10M concurrent users.",
        "How would you prevent overselling inventory during a high-traffic sale?",
        "Design a search autocomplete system for an e-commerce platform.",
        "How would you implement a fraud detection system for online payments?",
        "Design Flipkart's logistics and delivery tracking system.",
    ],
}

# Generic questions used for any company without specific seeds
_GENERIC_QUESTIONS = [
    "Tell me about yourself and your most significant technical achievement.",
    "Describe a challenging technical problem you solved and how you approached it.",
    "How do you ensure code quality in a fast-moving team?",
    "What is your approach to debugging a production issue at 3 AM?",
    "Explain the SOLID principles with an example from your own experience.",
    "How would you design a system to handle 1 million requests per second?",
    "Describe a time you had a technical disagreement with a colleague. How did you resolve it?",
    "What is your experience with microservices vs monolith architectures?",
    "How do you keep yourself up to date with new technologies?",
    "Walk me through your approach to system design from requirements to deployment.",
]


def _seed_question_bank(db_session=None):
    """
    Seed the QuestionBank table in the database with the built-in fallback questions.
    Safe to call multiple times — skips if already seeded.
    """
    if db_session is None:
        return
    try:
        from models.models import QuestionBank
        existing = db_session.query(QuestionBank).count()
        if existing > 0:
            return  # Already seeded

        rows = []
        for company, qs in _SEED_QUESTIONS.items():
            for q in qs:
                rows.append(QuestionBank(
                    category="system_design",
                    role="Software Engineer",
                    company=company,
                    difficulty="medium",
                    question=q,
                    source="seed",
                    tags=["system design"],
                ))
        for q in _GENERIC_QUESTIONS:
            rows.append(QuestionBank(
                category="general",
                role="Software Engineer",
                company=None,
                difficulty="medium",
                question=q,
                source="seed",
                tags=["general"],
            ))
        db_session.bulk_save_objects(rows)
        db_session.commit()
        logger.info(f"Seeded {len(rows)} questions into QuestionBank")
    except Exception as e:
        logger.error(f"Question bank seeding failed: {e}")


def load_all_questions(companies: Optional[List[str]] = None, db_session=None):
    """
    Load questions for all companies.
    Order of preference:
      1. Disk cache (instant, no network)
      2. GitHub fetch (network, then saves to disk)
      3. Built-in seed questions (always available)
    """
    global _cache_loaded

    # Step 1: try disk cache first
    if _load_cache_from_disk():
        _seed_question_bank(db_session)
        return

    # Step 2: fetch from GitHub
    target = companies or DATASET_COMPANIES
    fetched_any = False
    for company in target:
        if company not in _question_cache:
            qs = _fetch_company_questions(company)
            _question_cache[company] = qs
            if qs:
                fetched_any = True

    _cache_loaded = True

    if fetched_any:
        _save_cache_to_disk()
    else:
        logger.warning("GitHub fetch returned nothing — using built-in seed questions")

    # Step 3: fill gaps with seed questions
    for company, qs in _SEED_QUESTIONS.items():
        if not _question_cache.get(company):
            _question_cache[company] = qs

    _seed_question_bank(db_session)


def get_question_pool(company: str) -> List[str]:
    """
    Return the FULL question pool for a company (stable order, not sampled).
    Use this when you need a deterministic list for a whole interview session.
    """
    key = _normalize_company(company)
    if key not in _question_cache:
        qs = _fetch_company_questions(key)
        _question_cache[key] = qs if qs else _SEED_QUESTIONS.get(key, _GENERIC_QUESTIONS)
    pool = _question_cache.get(key) or _GENERIC_QUESTIONS
    return list(pool)


def get_questions_for_company(company: str, n: int = 5) -> List[str]:
    """Get up to n RANDOM questions for a company from cache, with seed fallback."""
    pool = get_question_pool(company)
    return random.sample(pool, min(n, len(pool)))


def _normalize_company(name: str) -> str:
    """Find closest matching company name from dataset list."""
    name_lower = name.lower().strip()
    for company in DATASET_COMPANIES:
        if company.lower() == name_lower:
            return company
        if name_lower in company.lower() or company.lower() in name_lower:
            return company
    return name


def get_company_list() -> List[Dict]:
    """Return full company list with metadata for UI."""
    return [
        {
            "name": company,
            **COMPANY_META.get(company, {"color": "#6366f1", "emoji": "🏢", "sector": "Tech"}),
        }
        for company in DATASET_COMPANIES
    ]
