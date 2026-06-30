import re

from dotenv import load_dotenv
import os


load_dotenv()


def clean_text(text: str) -> str:
    """Normalize text from text areas and PDF extraction."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def validate_required_inputs(resume_text: str, job_description: str) -> list[str]:
    errors = []
    if not clean_text(resume_text):
        errors.append("Resume text is required.")
    if not clean_text(job_description):
        errors.append("Job description text is required.")
    return errors


def resolve_api_key() -> str | None:
    env_key = os.getenv("DEEPSEEK_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    return None


def resolve_model() -> str:
    env_model = os.getenv("DEEPSEEK_MODEL")
    if env_model and env_model.strip():
        return env_model.strip()
    return "deepseek-v4-flash"


def extract_match_score(report: str) -> str | None:
    match = re.search(r"(\d{1,3})\s*%", report or "")
    if not match:
        return None
    score = max(0, min(100, int(match.group(1))))
    return f"{score}%"
