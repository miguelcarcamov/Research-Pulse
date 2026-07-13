"""Recommend newer literature based on a local Zotero library.

Seeds are recent library items (preferring DOIs). For each seed we pull
OpenAlex related works and citing papers, drop anything already in the
library, and rank by recency + topical overlap with the seed.

Usage:
    from research_agent.zotero_recommend import recommend_from_zotero
    recs = recommend_from_zotero(limit=10)
"""

from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from .config import load_secrets
from .models import Paper
from .sources import openalex
from .zotero import (
    ZoteroItem,
    find_zotero_db,
    library_identifiers,
    read_library_items,
)


@dataclass
class LibraryRecommendation:
    """A paper recommended from the user's Zotero bibliography."""

    paper: Paper
    score: float
    reasons: List[str] = field(default_factory=list)
    seed_title: str = ""


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def _paper_doi(paper: Paper) -> str:
    """Extract a normalized DOI from a Paper id/url when present."""
    for raw in (paper.url, paper.id):
        if not raw or "openalex.org" in raw.lower():
            continue
        n = openalex.normalize_doi(raw)
        if re.match(r"^10\.\d{4,9}/", n):
            return n
        m = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", raw, re.I)
        if m:
            return openalex.normalize_doi(m.group(0))
    return ""


def _seed_cutoff(seed: ZoteroItem) -> Optional[datetime]:
    """Earliest publication date we treat as 'newer than this seed'."""
    if seed.year:
        return datetime(seed.year, 1, 1, tzinfo=timezone.utc)
    return None


def _overlap_score(paper: Paper, seed: ZoteroItem) -> float:
    seed_terms = set(re.findall(r"[a-z0-9]{4,}", seed.title.lower()))
    if not seed_terms:
        return 0.0
    text = f"{paper.title} {paper.abstract}".lower()
    hits = sum(1 for t in seed_terms if t in text)
    return min(1.0, hits / max(len(seed_terms), 1))


def _recency_score(paper: Paper) -> float:
    if not paper.published:
        return 0.35
    age_days = (datetime.now(timezone.utc) - paper.published).days
    return max(0.1, 1.0 * (0.5 ** (age_days / 180)))


def _citation_score(paper: Paper) -> float:
    if paper.citations <= 0:
        return 0.0
    return min(1.0, math.log10(paper.citations + 1) / 3.0)


def _already_owned(paper: Paper, dois: Set[str], titles: Set[str]) -> bool:
    doi = _paper_doi(paper)
    if doi and doi in dois:
        return True
    key = _title_key(paper.title)
    return bool(key and key in titles)


def _expand_seed(
    seed: ZoteroItem,
    mailto: str,
    lookback_days: int,
) -> List[Tuple[Paper, str, str]]:
    """Return (paper, reason_kind, seed_title) candidates for one seed.

    reason_kind is ``related``, ``citing``, or ``title_search``.
    """
    out: List[Tuple[Paper, str, str]] = []
    cutoff = _seed_cutoff(seed)

    if seed.doi:
        batch = openalex.fetch_related_and_citing(
            seed.doi,
            newer_than=cutoff,
            max_related=6,
            max_citing=8,
            mailto=mailto,
        )
        # Heuristic: citing filter uses from_date; related may be mixed.
        for p in batch:
            kind = "related"
            if cutoff and p.published and p.published >= cutoff:
                # Citing works are often strictly newer; label when helpful.
                kind = "citing_or_related"
            out.append((p, kind, seed.title))
        return out

    # No DOI: free-text search from significant title terms.
    query = openalex.significant_query_terms(seed.title)
    if not query:
        return out
    days = lookback_days
    if seed.year:
        # Prefer papers from the seed year onward, capped by lookback window.
        year_span = max(datetime.now(timezone.utc).year - seed.year, 1) * 365
        days = min(max(lookback_days, year_span), 3650)
    for p in openalex.fetch(query, lookback_days=days, max_results=12, mailto=mailto):
        out.append((p, "title_search", seed.title))
    return out


def recommend_from_zotero(
    limit: int = 10,
    seeds: int = 12,
    lookback_days: int = 730,
    max_workers: int = 4,
) -> List[LibraryRecommendation]:
    """Recommend newer papers of interest based on the local Zotero library.

    Args:
        limit: Max recommendations to return.
        seeds: How many library items to expand (prefer DOI-backed).
        lookback_days: Fallback window for title-search seeds without DOI.
        max_workers: Parallel OpenAlex expansions.
    """
    db = find_zotero_db()
    if db is None:
        return []

    seed_items = read_library_items(db, limit=seeds, prefer_doi=True)
    if not seed_items:
        return []

    owned_dois, owned_titles = library_identifiers(db)
    # Also treat seed DOIs/titles as owned (belt and suspenders).
    for s in seed_items:
        if s.doi:
            owned_dois.add(s.doi)
        key = _title_key(s.title)
        if key:
            owned_titles.add(key)

    secrets = load_secrets()
    mailto = secrets.sender_email or ""

    # paper_key -> (best Paper, best score parts, reasons, seed_title)
    best: Dict[str, Tuple[Paper, float, List[str], str]] = {}

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(seed_items)))) as pool:
        futures = {
            pool.submit(_expand_seed, seed, mailto, lookback_days): seed
            for seed in seed_items
        }
        for fut in as_completed(futures):
            try:
                batch = fut.result()
            except Exception:
                continue
            for paper, kind, seed_title in batch:
                if not paper.title or _already_owned(paper, owned_dois, owned_titles):
                    continue
                key = _paper_doi(paper) or _title_key(paper.title)
                if not key:
                    continue

                overlap = _overlap_score(paper, futures[fut])
                recency = _recency_score(paper)
                cites = _citation_score(paper)
                score = overlap * 0.45 + recency * 0.35 + cites * 0.20

                reasons = []
                short = seed_title if len(seed_title) <= 70 else seed_title[:67] + "..."
                if kind == "title_search":
                    reasons.append(f"Similar to library item: {short}")
                elif kind == "citing_or_related":
                    reasons.append(f"Related to / cites work in your library: {short}")
                else:
                    reasons.append(f"Related to your library item: {short}")
                if paper.published:
                    reasons.append(f"Published {paper.published:%Y-%m-%d}")
                if paper.citations > 0:
                    reasons.append(f"{paper.citations} citations")

                paper.score = score
                prev = best.get(key)
                if prev is None or score > prev[1]:
                    best[key] = (paper, score, reasons, seed_title)

    recommendations = [
        LibraryRecommendation(
            paper=paper,
            score=score,
            reasons=reasons,
            seed_title=seed_title,
        )
        for paper, score, reasons, seed_title in best.values()
    ]
    recommendations.sort(key=lambda r: r.score, reverse=True)

    # Attach score onto papers for display helpers that read paper.score
    for rec in recommendations[:limit]:
        rec.paper.score = rec.score

    return recommendations[:limit]


def format_library_recommendations(recs: List[LibraryRecommendation]) -> str:
    """Plain-text formatting for CLI / agent display."""
    if not recs:
        return (
            "No new recommendations found. "
            "Add DOIs to Zotero items or try again later."
        )

    lines = [
        "=" * 60,
        "NEWER PAPERS FROM YOUR ZOTERO LIBRARY",
        "=" * 60,
    ]
    for i, rec in enumerate(recs, 1):
        p = rec.paper
        lines.append(f"\n{i}. [{p.source}] {p.title}")
        lines.append(f"   Score: {rec.score:.2f}")
        if p.authors:
            authors = ", ".join(p.authors[:3])
            if len(p.authors) > 3:
                authors += " et al."
            lines.append(f"   Authors: {authors}")
        if p.venue_line():
            lines.append(f"   Venue: {p.venue_line()}")
        for reason in rec.reasons:
            lines.append(f"   · {reason}")
        lines.append(f"   URL: {p.url}")
    lines.append("\n" + "=" * 60)
    lines.append(f"Showing {len(recs)} papers not already in your library")
    lines.append("=" * 60)
    return "\n".join(lines)
