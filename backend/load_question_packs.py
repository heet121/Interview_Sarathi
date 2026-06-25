"""
Question-pack loader.

Imports company interview questions into the `company_question_packs` table from
either a local file/folder or a raw GitHub URL. Run it once after pointing it at
your dataset.

Supported inputs
----------------
1. A single JSON file
2. A folder of JSON files (each file processed)
3. A raw URL to a JSON file (e.g. https://raw.githubusercontent.com/.../packs.json)

Accepted JSON shapes (field names are matched flexibly)
-------------------------------------------------------
A) A flat list of objects:
   [
     {"company": "Google", "round_type": "technical", "difficulty": "hard",
      "question": "Implement an LRU cache.", "answer_guide": "hashmap + DLL",
      "tags": ["dsa"]},
     ...
   ]

B) A dict keyed by company, then by round type:
   {
     "Google": {
       "technical": [{"q": "...", "difficulty": "hard", "hint": "..."}],
       "hr":        [{"question": "...", "difficulty": "easy"}]
     }
   }

Field aliases handled automatically:
  question     ← question | q | text | title
  answer_guide ← answer_guide | answer | hint | guide
  round_type   ← round_type | round | category | type
  difficulty   ← difficulty | level   (default: "medium")
  company      ← company | company_name   (or the dict key in shape B)
  tags         ← tags (list)

Usage
-----
  python load_question_packs.py <path-or-url> [--replace]

  --replace   delete existing packs first (otherwise new rows are appended)

Examples
--------
  python load_question_packs.py dataset/packs/
  python load_question_packs.py https://raw.githubusercontent.com/you/repo/main/packs.json
  python load_question_packs.py dataset/packs.json --replace
"""

import json
import os
import sys
import urllib.request

from database import SessionLocal, engine, Base
from models.models import CompanyQuestionPack

Base.metadata.create_all(bind=engine)


def _first(d: dict, *keys, default=""):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _normalize(entry: dict, company_hint: str = "", round_hint: str = "") -> dict | None:
    """Turn one flexible entry into a CompanyQuestionPack kwargs dict."""
    question = str(_first(entry, "question", "q", "text", "title")).strip()
    if not question or len(question) < 8:
        return None
    company = str(_first(entry, "company", "company_name", default=company_hint)).strip()
    round_type = str(_first(entry, "round_type", "round", "category", "type",
                            default=round_hint or "general")).strip().lower()
    difficulty = str(_first(entry, "difficulty", "level", default="medium")).strip().lower()
    answer_guide = str(_first(entry, "answer_guide", "answer", "hint", "guide")).strip()
    tags = entry.get("tags") or [round_type] + ([company.lower()] if company else [])
    if not company:
        company = "General"
    return dict(
        company=company,
        round_type=round_type,
        difficulty=difficulty,
        question=question,
        answer_guide=answer_guide,
        tags=tags,
        is_active=True,
    )


def _rows_from_data(data) -> list:
    rows = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                r = _normalize(entry)
                if r:
                    rows.append(r)
    elif isinstance(data, dict):
        # Shape B: company -> round_type -> [questions]   OR   company -> [questions]
        for company, value in data.items():
            if isinstance(value, dict):
                for round_type, questions in value.items():
                    for entry in (questions or []):
                        if isinstance(entry, dict):
                            r = _normalize(entry, company_hint=company, round_hint=round_type)
                            if r:
                                rows.append(r)
            elif isinstance(value, list):
                for entry in value:
                    if isinstance(entry, dict):
                        r = _normalize(entry, company_hint=company)
                        if r:
                            rows.append(r)
    return rows


def _load_json_text(text: str) -> list:
    return _rows_from_data(json.loads(text))


def collect_rows(source: str) -> list:
    rows = []
    if source.startswith("http://") or source.startswith("https://"):
        print(f"Fetching {source} ...")
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            rows += _load_json_text(resp.read().decode("utf-8", errors="ignore"))
    elif os.path.isdir(source):
        for name in sorted(os.listdir(source)):
            if name.lower().endswith(".json"):
                path = os.path.join(source, name)
                with open(path, encoding="utf-8") as f:
                    file_rows = _load_json_text(f.read())
                print(f"  {name}: {len(file_rows)} questions")
                rows += file_rows
    elif os.path.isfile(source):
        with open(source, encoding="utf-8") as f:
            rows += _load_json_text(f.read())
    else:
        raise SystemExit(f"Source not found: {source}")
    return rows


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    source  = sys.argv[1]
    replace = "--replace" in sys.argv[2:]

    rows = collect_rows(source)
    if not rows:
        raise SystemExit("No valid questions found in the source.")

    db = SessionLocal()
    try:
        if replace:
            deleted = db.query(CompanyQuestionPack).delete()
            db.commit()
            print(f"Deleted {deleted} existing packs.")
        db.bulk_save_objects([CompanyQuestionPack(**r) for r in rows])
        db.commit()
        companies = sorted({r["company"] for r in rows})
        print(f"\nImported {len(rows)} questions across {len(companies)} companies:")
        print("  " + ", ".join(companies))
    finally:
        db.close()


if __name__ == "__main__":
    main()
