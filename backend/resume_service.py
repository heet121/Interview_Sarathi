import io
import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


# ── Known skills vocabulary for fast keyword matching ─────────────
KNOWN_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "ruby", "php", "scala", "r", "matlab",
    # Web
    "react", "angular", "vue", "next.js", "node.js", "express", "django",
    "fastapi", "flask", "spring", "asp.net", "graphql", "rest", "html", "css",
    # Data / ML
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "scikit-learn", "pandas", "numpy", "spark", "hadoop",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
    "jenkins", "github actions", "linux", "bash",
    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "cassandra", "sqlite",
    # Concepts
    "algorithms", "data structures", "system design", "microservices",
    "distributed systems", "agile", "scrum", "tdd", "oop", "solid",
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams
        import io
        output = io.StringIO()
        extract_text_to_fp(
            io.BytesIO(file_bytes), output,
            laparams=LAParams(), output_type="text", codec="utf-8",
        )
        return output.getvalue().strip()
    except ImportError:
        logger.warning("pdfminer.six not installed — trying pypdf fallback")
        return _extract_pdf_pypdf(file_bytes)
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}")


def _extract_pdf_pypdf(file_bytes: bytes) -> str:
    """Fallback PDF extractor using pypdf."""
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except ImportError:
        raise ValueError(
            "No PDF library found. Install pdfminer.six:  pip install pdfminer.six"
        )
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        import docx
        import io
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise ValueError(
            "python-docx not installed. Run:  pip install python-docx"
        )
    except Exception as e:
        raise ValueError(f"Could not read DOCX: {e}")


def extract_candidate_name(text: str) -> str | None:
    """
    Best-effort name from resume text (first meaningful line).
    Used so the interviewer greets the candidate on the resume, not the account.
    """
    if not text or not text.strip():
        return None
    skip_words = {"resume", "curriculum", "vitae", "cv", "profile", "objective", "summary"}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) > 55:
            continue
        low = line.lower()
        if "@" in line or "http" in low or any(w in low for w in ("phone", "email", "linkedin", "github")):
            continue
        if low in skip_words or any(low.startswith(w) for w in skip_words):
            continue
        if re.match(r"^[A-Za-z][A-Za-z.'\-]*(?:\s+[A-Za-z][A-Za-z.'\-]*){1,4}$", line):
            return line.strip().title() if line.isupper() else line.strip()
    return None


def extract_skills_from_text(text: str) -> List[str]:
    """
    Fast keyword-based skill extraction.
    Returns a deduplicated, sorted list of recognised skills.
    """
    text_lower = text.lower()
    found = set()
    for skill in KNOWN_SKILLS:
        # Word-boundary aware match (handles "C++" and multi-word skills)
        pattern = re.escape(skill)
        if re.search(r'(?<!\w)' + pattern + r'(?!\w)', text_lower):
            found.add(skill)
    return sorted(found)


def extract_text_from_file(filename: str, file_bytes: bytes) -> Tuple[str, List[str]]:
    """
    Dispatch to the correct extractor based on file extension.
    Returns (text_content, skills_list).
    """
    fname = filename.lower()
    if fname.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif fname.endswith((".docx", ".doc")):
        text = extract_text_from_docx(file_bytes)
    elif fname.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore").strip()
    else:
        raise ValueError(f"Unsupported file type: {filename}. Upload PDF, DOCX, or TXT.")

    skills = extract_skills_from_text(text)
    return text, skills
