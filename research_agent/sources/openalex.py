"""OpenAlex fetcher.

OpenAlex is a free, open catalog of scholarly works (no key required). We use
it for cross-domain coverage and for citation counts that help ranking. We
filter by publication date and a free-text search query.

Docs: https://docs.openalex.org/api-entities/works
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from urllib.parse import quote

from ..models import Paper
from .http import get

API_URL = "https://api.openalex.org/works"


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """OpenAlex stores abstracts as an inverted index; rebuild plain text."""
    if not inverted_index:
        return ""
    positions: List[Tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda p: p[0])
    return " ".join(word for _, word in positions)


def _parse_pub_date(w: dict) -> Optional[datetime]:
    if w.get("publication_date"):
        try:
            return datetime.strptime(w["publication_date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    return None


def _paper_from_work(w: dict) -> Optional[Paper]:
    """Convert an OpenAlex work JSON object into a Paper."""
    title = " ".join((w.get("title") or "").split())
    if not title:
        return None
    authors = [
        a.get("author", {}).get("display_name", "")
        for a in w.get("authorships", [])
    ]
    url = w.get("doi") or w.get("id", "")
    loc = w.get("primary_location") or {}
    source = loc.get("source") or {}
    venue = source.get("display_name") or ""
    pub = _parse_pub_date(w)
    year = w.get("publication_year")
    return Paper(
        id=w.get("id", url),
        title=title,
        abstract=_reconstruct_abstract(w.get("abstract_inverted_index")),
        authors=[a for a in authors if a],
        url=url,
        source="OpenAlex",
        published=pub,
        citations=int(w.get("cited_by_count", 0) or 0),
        venue=venue,
        year=int(year) if year else (pub.year if pub else None),
    )


def normalize_doi(doi: str) -> str:
    """Strip URL prefixes and normalize a DOI string."""
    if not doi:
        return ""
    d = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if d.lower().startswith(prefix.lower()):
            d = d[len(prefix):]
            break
    return d.strip().rstrip(".").lower()


def fetch(query: str, lookback_days: int = 2, max_results: int = 25,
          mailto: str = "", venue: Optional[str] = None) -> List[Paper]:
    """Fetch recent works matching a free-text query."""
    if not query:
        return []

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(lookback_days, 1))

    filters = [f"from_publication_date:{start:%Y-%m-%d}"]
    if venue:
        filters.append(f"primary_location.source.display_name.search:{venue}")

    params = {
        "search": query,
        "filter": ",".join(filters),
        "sort": "publication_date:desc",
        "per-page": min(max_results, 50),
    }
    # The "polite pool" just asks for a contact email; entirely optional/free.
    if mailto:
        params["mailto"] = mailto

    resp = get(API_URL, params=params)
    if resp is None:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []

    papers: List[Paper] = []
    for w in data.get("results", []):
        paper = _paper_from_work(w)
        if paper:
            papers.append(paper)
    return papers


def get_work_by_doi(doi: str, mailto: str = "") -> Optional[dict]:
    """Resolve a DOI to a raw OpenAlex work object."""
    clean = normalize_doi(doi)
    if not clean:
        return None
    url = f"{API_URL}/https://doi.org/{quote(clean, safe='')}"
    params = {}
    if mailto:
        params["mailto"] = mailto
    resp = get(url, params=params or None)
    if resp is None:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def fetch_works_by_ids(openalex_ids: List[str], mailto: str = "",
                       max_results: int = 25) -> List[Paper]:
    """Fetch works by OpenAlex IDs (W… or full URLs)."""
    if not openalex_ids:
        return []

    ids: List[str] = []
    for raw in openalex_ids:
        if not raw:
            continue
        wid = raw.rstrip("/").split("/")[-1]
        if wid and wid not in ids:
            ids.append(wid)
    if not ids:
        return []

    # OpenAlex OR filter: openalex_id:W1|W2|…
    chunk = ids[:min(max_results, 50)]
    params = {
        "filter": "openalex_id:" + "|".join(chunk),
        "per-page": len(chunk),
    }
    if mailto:
        params["mailto"] = mailto

    resp = get(API_URL, params=params)
    if resp is None:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []

    papers: List[Paper] = []
    for w in data.get("results", []):
        paper = _paper_from_work(w)
        if paper:
            papers.append(paper)
    return papers


def fetch_citing(openalex_id: str, from_date: Optional[datetime] = None,
                 max_results: int = 15, mailto: str = "") -> List[Paper]:
    """Fetch works that cite a given OpenAlex work, optionally after a date."""
    wid = (openalex_id or "").rstrip("/").split("/")[-1]
    if not wid:
        return []

    filters = [f"cites:{wid}"]
    if from_date is not None:
        filters.append(f"from_publication_date:{from_date:%Y-%m-%d}")

    params = {
        "filter": ",".join(filters),
        "sort": "publication_date:desc",
        "per-page": min(max_results, 50),
    }
    if mailto:
        params["mailto"] = mailto

    resp = get(API_URL, params=params)
    if resp is None:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []

    papers: List[Paper] = []
    for w in data.get("results", []):
        paper = _paper_from_work(w)
        if paper:
            papers.append(paper)
    return papers


def fetch_related_and_citing(
    doi: str,
    newer_than: Optional[datetime] = None,
    max_related: int = 8,
    max_citing: int = 10,
    mailto: str = "",
) -> List[Paper]:
    """Find related + citing works for a DOI, preferring newer literature.

    Uses OpenAlex ``related_works`` and the ``cites:`` filter. Papers older
    than ``newer_than`` are dropped when a date is provided.
    """
    work = get_work_by_doi(doi, mailto=mailto)
    if not work:
        return []

    openalex_id = work.get("id", "")
    related_ids = (work.get("related_works") or [])[:max_related]

    papers: List[Paper] = []
    if related_ids:
        papers.extend(fetch_works_by_ids(related_ids, mailto=mailto,
                                         max_results=max_related))
    if openalex_id:
        # Citing works published after the seed (or after newer_than).
        from_date = newer_than
        if from_date is None:
            from_date = _parse_pub_date(work)
        papers.extend(fetch_citing(
            openalex_id,
            from_date=from_date,
            max_results=max_citing,
            mailto=mailto,
        ))

    if newer_than is not None:
        papers = [
            p for p in papers
            if p.published is None or p.published >= newer_than
        ]

    return papers


def significant_query_terms(title: str, limit: int = 8) -> str:
    """Build a short OpenAlex search string from a paper title."""
    stop = {
        "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with",
        "via", "using", "from", "into", "by", "at", "as", "is", "are", "be",
    }
    words = re.findall(r"[a-zA-Z0-9]{3,}", title or "")
    kept = [w for w in words if w.lower() not in stop][:limit]
    return " ".join(kept)
