"""
Dataset Loader — Fetch interview questions from GitHub & seed PostgreSQL
Source: https://github.com/grg124/Interview-Questions

Usage:  python scripts/load_dataset.py
Run after: ./setup.sh  (tables must already exist)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import json, requests
from database import SessionLocal, engine, Base
from models.models import QuestionBank

GITHUB_RAW = "https://raw.githubusercontent.com/grg124/Interview-Questions/main"

# Known files to attempt (404s are silently skipped)
DATASET_FILES = [
    ("Technical",  "Technical/python_questions.json"),
    ("Technical",  "Technical/javascript_questions.json"),
    ("Technical",  "Technical/java_questions.json"),
    ("Technical",  "Technical/sql_questions.json"),
    ("Technical",  "Technical/data_structures.json"),
    ("Technical",  "Technical/algorithms.json"),
    ("Technical",  "Technical/system_design.json"),
    ("Technical",  "Technical/machine_learning.json"),
    ("Behavioral", "Behavioral/behavioral_questions.json"),
    ("HR",         "HR/hr_questions.json"),
    # Alternate paths (repo may differ)
    ("Technical",  "python.json"),
    ("Technical",  "javascript.json"),
    ("Behavioral", "behavioral.json"),
    ("HR",         "hr.json"),
]

ROLE_MAP = {
    "python": "Python Developer", "javascript": "Frontend Developer",
    "java": "Java Developer", "sql": "Data Analyst",
    "data_structures": "Software Engineer", "algorithms": "Software Engineer",
    "system_design": "Software Engineer", "machine_learning": "Data Scientist",
    "behavioral": "General", "hr": "General",
}

# ── Built-in fallback bank ────────────────────────────────────────
BUILTIN = [
    # Technical — Software Engineering
    dict(category="Technical", role="Software Engineer", difficulty="Intermediate", company=None,
         question="What is the difference between a list and a tuple in Python?",
         answer_hint="Lists are mutable (can be changed), tuples are immutable (fixed). Tuples are faster and hashable."),
    dict(category="Technical", role="Software Engineer", difficulty="Intermediate", company=None,
         question="Explain Object-Oriented Programming and its four pillars.",
         answer_hint="Encapsulation (data hiding), Abstraction (hiding complexity), Inheritance (reuse), Polymorphism (many forms)."),
    dict(category="Technical", role="Software Engineer", difficulty="Advanced", company=None,
         question="What is a RESTful API and how does it differ from GraphQL?",
         answer_hint="REST: multiple endpoints, HTTP verbs, stateless. GraphQL: single endpoint, client-specified queries, avoids over/under-fetching."),
    dict(category="Technical", role="Software Engineer", difficulty="Advanced", company=None,
         question="Explain time and space complexity. What is Big O notation?",
         answer_hint="Big O describes worst-case growth. O(1) constant, O(log n) logarithmic, O(n) linear, O(n²) quadratic."),
    dict(category="Technical", role="Software Engineer", difficulty="Intermediate", company=None,
         question="What is the difference between SQL JOIN types?",
         answer_hint="INNER: matching rows only. LEFT: all from left + matching right. RIGHT: vice versa. FULL: all rows."),
    dict(category="Technical", role="Software Engineer", difficulty="Advanced", company=None,
         question="Design a URL shortening service like bit.ly.",
         answer_hint="Hash URL (base62 MD5), store mapping in DB, handle collisions, add caching (Redis), analytics."),
    dict(category="Technical", role="Software Engineer", difficulty="Intermediate", company=None,
         question="What are the SOLID principles in software design?",
         answer_hint="Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion."),
    dict(category="Technical", role="Software Engineer", difficulty="Advanced", company=None,
         question="Explain the difference between processes and threads.",
         answer_hint="Processes: separate memory space. Threads: share memory in a process. Threads are lighter but need synchronization."),
    # Technical — Data Science / ML
    dict(category="Technical", role="Data Scientist", difficulty="Intermediate", company=None,
         question="What is the difference between supervised and unsupervised learning?",
         answer_hint="Supervised: labeled data (classification, regression). Unsupervised: no labels, finds patterns (clustering, PCA)."),
    dict(category="Technical", role="Data Scientist", difficulty="Advanced", company=None,
         question="Explain overfitting and how to prevent it.",
         answer_hint="Model memorises noise. Prevent: regularisation (L1/L2), dropout, cross-validation, early stopping, more data, simpler model."),
    dict(category="Technical", role="Data Scientist", difficulty="Intermediate", company=None,
         question="What is the bias-variance trade-off?",
         answer_hint="High bias = underfitting. High variance = overfitting. Goal: balanced model that generalises."),
    dict(category="Technical", role="Data Scientist", difficulty="Advanced", company=None,
         question="Explain how a transformer model works (e.g., BERT).",
         answer_hint="Self-attention mechanism, positional encoding, encoder/decoder blocks, pre-training + fine-tuning."),
    # Technical — Frontend
    dict(category="Technical", role="Frontend Developer", difficulty="Intermediate", company=None,
         question="What is the virtual DOM in React and why does it exist?",
         answer_hint="In-memory representation of real DOM. React diffs it and only updates changed parts — much faster than full DOM re-renders."),
    dict(category="Technical", role="Frontend Developer", difficulty="Intermediate", company=None,
         question="Explain the difference between == and === in JavaScript.",
         answer_hint="== does type coercion (1 == '1' is true). === checks type AND value (1 === '1' is false)."),
    # Behavioral
    dict(category="Behavioral", role="General", difficulty="Intermediate", company=None,
         question="Tell me about a time you faced a difficult challenge at work and how you overcame it.",
         answer_hint="Use STAR: Situation, Task, Action (specific steps you took), Result (quantified outcome)."),
    dict(category="Behavioral", role="General", difficulty="Intermediate", company=None,
         question="Describe a situation where you had to work with a difficult team member.",
         answer_hint="Focus on empathy, communication, finding common ground, and the positive outcome."),
    dict(category="Behavioral", role="General", difficulty="Intermediate", company=None,
         question="Give an example of a time you made a mistake. How did you handle it?",
         answer_hint="Own it, explain what you learned, what you changed. Shows maturity and growth mindset."),
    dict(category="Behavioral", role="General", difficulty="Beginner", company=None,
         question="Where do you see yourself in 5 years?",
         answer_hint="Align with company trajectory. Show ambition, commitment, and desire to grow in the domain."),
    dict(category="Behavioral", role="General", difficulty="Intermediate", company=None,
         question="Tell me about your most challenging project.",
         answer_hint="Highlight: scale, complexity, your specific role, technical decisions, team dynamics, outcome and learnings."),
    # HR
    dict(category="HR", role="General", difficulty="Beginner", company=None,
         question="Why do you want to work for our company?",
         answer_hint="Research the company culture, products, mission. Align your values and goals. Be specific."),
    dict(category="HR", role="General", difficulty="Beginner", company=None,
         question="What are your greatest strengths and weaknesses?",
         answer_hint="Strengths: relevant to role. Weakness: real but improving. Show self-awareness."),
    dict(category="HR", role="General", difficulty="Intermediate", company=None,
         question="How do you handle stress and pressure?",
         answer_hint="Specific strategies: task prioritisation, breaking down problems, asking for help, self-care. Give an example."),
    dict(category="HR", role="General", difficulty="Beginner", company=None,
         question="Tell me about yourself.",
         answer_hint="Past (education/experience) → Present (current role/skills) → Future (why this role). 2-3 minutes, structured."),
    # Company-specific
    dict(category="Technical", role="Software Engineer", difficulty="Advanced", company="Google",
         question="How would you improve Google Maps for rural users in India?",
         answer_hint="Offline maps, low-data mode, voice navigation in regional languages, crowdsourced road data."),
    dict(category="Behavioral", role="Software Engineer", difficulty="Advanced", company="Amazon",
         question="Tell me about a time you used data to make a difficult decision. (Leadership Principle: Are Right, A Lot)",
         answer_hint="STAR format. Emphasise data sources, how you validated, what the decision was, outcome."),
    dict(category="Technical", role="Software Engineer", difficulty="Advanced", company="Microsoft",
         question="How would you design a distributed file storage system like OneDrive?",
         answer_hint="Chunking, deduplication, replication, metadata service, CDN, consistency model."),
    dict(category="Behavioral", role="General", difficulty="Intermediate", company="Infosys",
         question="How do you stay updated with the latest trends in technology?",
         answer_hint="Blogs, courses, open source contributions, conferences, communities. Give specific examples."),
]


def fetch_github(path: str) -> list:
    url = f"{GITHUB_RAW}/{path}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("questions", [])
    except Exception as e:
        pass
    return []


def to_row(entry, category: str, filepath: str) -> dict:
    q = (entry.get("question") or entry.get("Question") or
         entry.get("q") or entry.get("text") or str(entry)).strip()
    a = (entry.get("answer") or entry.get("Answer") or
         entry.get("hint") or entry.get("a") or "").strip()
    diff = entry.get("difficulty") or entry.get("level") or "Intermediate"
    role = entry.get("role") or entry.get("domain") or "General"
    fname = filepath.lower().split("/")[-1].replace(".json", "").replace("_questions", "")
    role = ROLE_MAP.get(fname, role)
    if "behavioral" in filepath.lower(): category = "Behavioral"
    if "hr" in filepath.lower():        category = "HR"
    return dict(category=category, role=role, company=None,
                difficulty=str(diff), question=q, answer_hint=a,
                tags=entry.get("tags") or [], source="github")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(QuestionBank).count()
        if existing > 0:
            print(f"ℹ️  {existing} questions already in DB — skipping seed.")
            print("   Delete from question_bank to re-seed.")
            return

        print("📥 Fetching from GitHub…")
        total = 0

        for category, path in DATASET_FILES:
            entries = fetch_github(path)
            count = 0
            for e in entries:
                if not isinstance(e, dict): continue
                row = to_row(e, category, path)
                if not row["question"] or len(row["question"]) < 10: continue
                db.add(QuestionBank(**row, source="github"))
                count += 1
                total += 1
            if count:
                db.commit()
                print(f"   ✅ {path}: {count} questions")
            else:
                print(f"   ⚠️  {path}: not found or empty (skipped)")

        print(f"\n📦 Adding {len(BUILTIN)} built-in questions…")
        for q in BUILTIN:
            db.add(QuestionBank(
                category=q["category"], role=q["role"],
                company=q.get("company"), difficulty=q["difficulty"],
                question=q["question"], answer_hint=q["answer_hint"],
                tags=[], source="builtin"
            ))
            total += 1
        db.commit()
        print(f"\n✅ Dataset ready. Total questions: {total}")

    except Exception as e:
        db.rollback()
        print("❌ Error:", e); raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
