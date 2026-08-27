import re


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "job"


def job_url(base_url: str, outcome_id: str, title: str) -> str:
    return f"{base_url.rstrip('/')}/jobs/{outcome_id}/{slugify(title)}"
