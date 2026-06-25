"""
Parse grg124/Interview-Questions README files with the same company → section
structure used in the original dataset (telephonic, coding, dsa, dbms, etc.).
"""

from __future__ import annotations

import re
import urllib.request
from typing import Dict, List, Optional

GITHUB_BASE = "https://raw.githubusercontent.com/grg124/Interview-Questions/master"

# Same company list as dataset_service.py
COMPANIES = [
    "Adobe", "AirAsia", "Amazon", "AmericanExpress", "Atlassian",
    "BookMyShow", "Box", "Expedia", "Facebook", "Flipkart",
    "Google", "Grab", "Groupon", "Intuit", "LinkedIn",
    "Microsoft", "MobiKwik", "NEC Technologies", "Netflix", "Ola Cabs",
    "Palantir", "PayPal", "Samsung", "Thoughtworks", "Twitter",
    "Uber", "Walmart Labs", "Yatra.com", "Zomato",
]

# Alternate folder names when the canonical name 404s on GitHub
COMPANY_PATH_ALIASES = {
    "Thoughtworks": ["Thoughtworks", "ThoughtWorks"],
}


def _round_type_from_heading(title: str) -> str:
    t = title.lower().strip()
    if "telephonic" in t or "quiz" in t or "phone" in t:
        return "telephonic"
    if "coding" in t or "code" in t:
        return "coding"
    if "system design" in t or t.endswith("design") or "design" in t:
        return "system_design"
    if "dbms" in t or "database" in t:
        return "dbms"
    if "operating" in t or t == "os" or "operating system" in t:
        return "operating_system"
    if "behavior" in t or "hr" in t or "behaviour" in t:
        return "hr"
    if "data structure" in t or "algorithm" in t or "dsalg" in t or "dsa" in t:
        return "dsa"
    if "network" in t or "cn" in t:
        return "networking"
    if "misc" in t:
        return "miscellaneous"
    if "technical" in t:
        return "technical"
    if "aptitude" in t:
        return "aptitude"
    if "manager" in t:
        return "managerial"
    return "general"


def _clean_question(line: str) -> Optional[str]:
    line = line.strip()
    if not line or line.startswith("|") or line.startswith("---"):
        return None
    for prefix in ("- ", "* ", "• "):
        if line.startswith(prefix):
            line = line[len(prefix):]
            break
    line = re.sub(r"^\d+\.\s+", "", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line).strip()
    if len(line) < 12:
        return None
    lower = line.lower()
    looks_like_q = (
        "?" in line
        or any(lower.startswith(w) for w in (
            "what", "how", "why", "when", "which", "explain", "describe",
            "design", "implement", "write", "find", "given", "you are",
            "tell", "discuss", "mention", "create", "we have", "the average",
            "can you", "define", "compare", "walk", "reverse", "given an",
            "given a", "you're", "you are", "suppose", "consider", "prove",
        ))
        or any(k in lower for k in ("linked list", "array", "tree", "graph", "sort", "complexity"))
    )
    return line if looks_like_q else None


def _is_section_title(line: str) -> Optional[str]:
    """Detect section titles that are NOT markdown headers (grg124 style)."""
    s = line.strip().strip("_").strip()
    if not s or len(s) > 80 or s.startswith(("-", "*", "|")):
        return None
    if s.startswith("#"):
        return re.sub(r"^#+\s*", "", s).strip()
    lower = s.lower()
    markers = (
        "questions", "round", "interview", "coding", "technical",
        "telephonic", "system design", "data structures", "dbms",
        "operating system", "miscellaneous",
    )
    if any(m in lower for m in markers) and not s.endswith("?"):
        # Avoid treating long question lines as titles
        if len(s.split()) <= 8:
            return s
    return None


def parse_readme_sections(content: str) -> List[dict]:
    """Return [{round_type, section_title, questions: [str]}]."""
    sections: List[dict] = []
    current = {"round_type": "general", "section_title": "General", "questions": []}

    for raw in content.split("\n"):
        line = raw.strip()
        if line in ("____", "---", "----"):
            continue

        if line.startswith("#"):
            title = re.sub(r"^#+\s*", "", line).strip()
            if current["questions"]:
                sections.append(current)
            current = {
                "round_type": _round_type_from_heading(title),
                "section_title": title,
                "questions": [],
            }
            continue

        title = _is_section_title(line)
        if title and not line.startswith("-"):
            if current["questions"]:
                sections.append(current)
            current = {
                "round_type": _round_type_from_heading(title),
                "section_title": title,
                "questions": [],
            }
            continue

        q = _clean_question(line)
        if q:
            current["questions"].append(q)

    if current["questions"]:
        sections.append(current)
    return sections


def fetch_company_readme(company: str, timeout: int = 12) -> Optional[str]:
    paths = COMPANY_PATH_ALIASES.get(company, [company])
    for path in paths:
        encoded = path.replace(" ", "%20")
        url = f"{GITHUB_BASE}/{encoded}/README.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            continue
    return None


def fetch_all_github_questions(companies: Optional[List[str]] = None) -> Dict[str, List[dict]]:
    """
    Returns {company: [{round_type, section_title, questions, source}]}.
    """
    target = companies or COMPANIES
    out: Dict[str, List[dict]] = {}
    for company in target:
        content = fetch_company_readme(company)
        if not content:
            out[company] = []
            continue
        sections = parse_readme_sections(content)
        for sec in sections:
            sec["source"] = "grg124/Interview-Questions"
        out[company] = sections
    return out
