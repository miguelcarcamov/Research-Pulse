"""Read the subscriber list.

Priority:
  1. DIGEST_EMAIL (+ optional DIGEST_TOPICS) for a personal single-recipient setup
  2. Published Google Sheet CSV (SUBSCRIBERS_CSV_URL)
  3. config/subscribers.sample.csv for local testing

Expected CSV columns (header row, case-insensitive):
    email, topics, confirmed, token
`topics` is a ';'-separated list of topic ids; `confirmed` is true/yes/1.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import List

from .config import CONFIG_DIR, Secrets
from .log import get as _log
from .sources.http import get

log = _log("subscribers")

# Used when DIGEST_EMAIL is set but DIGEST_TOPICS is empty.
_DEFAULT_DIGEST_TOPICS = ["ai-ml", "nlp", "bioinformatics", "medicine"]


@dataclass
class Subscriber:
    email: str
    topics: List[str] = field(default_factory=list)
    token: str = ""


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1", "y", "confirmed"}


def _split_topics(value: str) -> List[str]:
    raw = (value or "").replace(",", ";")
    return [t.strip().lower() for t in raw.split(";") if t.strip()]


def _parse_csv(text: str) -> List[Subscriber]:
    reader = csv.DictReader(io.StringIO(text))
    subs: List[Subscriber] = []
    for row in reader:
        # Normalize header keys to lowercase for resilience.
        row = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
        email = row.get("email", "").strip()
        if not email or "@" not in email:
            continue
        if not _truthy(row.get("confirmed", "")):
            continue
        subs.append(
            Subscriber(
                email=email,
                topics=_split_topics(row.get("topics", "")),
                token=row.get("token", "").strip(),
            )
        )
    return subs


def load_subscribers(secrets: Secrets) -> List[Subscriber]:
    """Load confirmed subscribers from DIGEST_EMAIL, CSV URL, or the local sample."""
    if secrets.digest_email and "@" in secrets.digest_email:
        topics = _split_topics(secrets.digest_topics) or list(_DEFAULT_DIGEST_TOPICS)
        log.info("personal digest mode -> %s (%d topic(s))", secrets.digest_email, len(topics))
        return [Subscriber(email=secrets.digest_email, topics=topics, token="digest-email")]

    if secrets.subscribers_csv_url:
        resp = get(secrets.subscribers_csv_url)
        if resp is not None and resp.text.strip():
            return _parse_csv(resp.text)
        log.warning("CSV URL set but fetch failed; using local sample.")

    sample = CONFIG_DIR / "subscribers.sample.csv"
    if sample.exists():
        return _parse_csv(sample.read_text(encoding="utf-8"))
    return []
