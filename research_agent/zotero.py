"""Zotero integration: detect local Zotero library and infer research domains.

Zotero stores its library in a SQLite database (zotero.sqlite). This module
finds that database on the user's machine, reads the user's collections and
item tags, and maps them to ResearchPulse topic IDs.

This is entirely local and read-only -- it never modifies the Zotero DB.

Usage:
    python -m research_agent zotero
    # or programmatically:
    from research_agent.zotero import detect_topics
    topics = detect_topics()  # -> ['ai-ml', 'nlp', ...]

Supported platforms: Windows, macOS, Linux.
"""

from __future__ import annotations

import os
import platform
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import load_topics


@dataclass
class ZoteroItem:
    """A library item used as a recommendation seed."""

    item_id: int
    title: str
    doi: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    date_raw: str = ""


def _connect_ro(db_path: Path) -> Optional[sqlite3.Connection]:
    """Open zotero.sqlite read-only, tolerating a live Zotero lock.

    Prefer a normal read-only URI; if the DB is locked (Zotero running),
    fall back to ``immutable=1`` so we can still read without waiting.
    """
    attempts = (
        f"file:{db_path}?mode=ro",
        f"file:{db_path}?mode=ro&immutable=1",
    )
    for uri in attempts:
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=2.0)
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
            return conn
        except sqlite3.Error:
            continue
    return None


# ── Locate the Zotero database ──────────────────────────────────────────

def _default_zotero_paths() -> List[Path]:
    """Return candidate paths for zotero.sqlite, platform-aware."""
    home = Path.home()
    system = platform.system()
    candidates: List[Path] = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(Path(appdata) / "Zotero" / "Zotero" / "Profiles")
        candidates.append(home / "Zotero")
    elif system == "Darwin":
        candidates.append(home / "Library" / "Application Support" / "Zotero" / "Profiles")
        candidates.append(home / "Zotero")
    else:
        candidates.append(home / ".zotero" / "zotero")
        candidates.append(home / "Zotero")

    # Also check ZOTERO_DATA_DIR env var for custom installations.
    custom = os.environ.get("ZOTERO_DATA_DIR")
    if custom:
        candidates.insert(0, Path(custom))

    return candidates


def find_zotero_db() -> Optional[Path]:
    """Locate the user's zotero.sqlite file. Returns None if not found."""
    for base in _default_zotero_paths():
        if not base.exists():
            continue
        # Direct path
        direct = base / "zotero.sqlite"
        if direct.exists():
            return direct
        # Inside a profile directory (e.g. Profiles/<hash>.default/zotero/zotero.sqlite)
        for db in base.rglob("zotero.sqlite"):
            return db
    return None


# ── Extract data from Zotero SQLite ─────────────────────────────────────

def _read_tags(db_path: Path) -> List[str]:
    """Read all item tags from the Zotero database."""
    conn = _connect_ro(db_path)
    if conn is None:
        return []
    try:
        cursor = conn.execute(
            "SELECT t.name FROM tags t "
            "JOIN itemTags it ON t.tagID = it.tagID "
            "GROUP BY t.name ORDER BY COUNT(*) DESC"
        )
        tags = [row[0] for row in cursor.fetchall() if row[0]]
        return tags
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _read_collections(db_path: Path) -> List[str]:
    """Read all collection names from the Zotero database."""
    conn = _connect_ro(db_path)
    if conn is None:
        return []
    try:
        cursor = conn.execute(
            "SELECT collectionName FROM collections ORDER BY collectionName"
        )
        names = [row[0] for row in cursor.fetchall() if row[0]]
        return names
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _read_titles(db_path: Path, limit: int = 200) -> List[str]:
    """Read recent item titles to supplement tag-based detection."""
    conn = _connect_ro(db_path)
    if conn is None:
        return []
    try:
        cursor = conn.execute(
            "SELECT iv.value FROM itemDataValues iv "
            "JOIN itemData id ON iv.valueID = id.valueID "
            "JOIN fields f ON id.fieldID = f.fieldID "
            "WHERE f.fieldName = 'title' "
            "ORDER BY id.itemID DESC LIMIT ?",
            (limit,)
        )
        titles = [row[0] for row in cursor.fetchall() if row[0]]
        return titles
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _read_item_count(db_path: Path) -> int:
    """Count the total number of items in the library."""
    conn = _connect_ro(db_path)
    if conn is None:
        return 0
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM items WHERE itemTypeID != 1")
        return cursor.fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def _normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    d = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "DOI:"):
        if d.lower().startswith(prefix.lower()):
            d = d[len(prefix):]
            break
    return d.strip().rstrip(".").lower()


def _parse_year(date_raw: str) -> Optional[int]:
    if not date_raw:
        return None
    m = re.search(r"(19|20)\d{2}", date_raw)
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def _field_map(conn: sqlite3.Connection) -> Dict[str, int]:
    """Map fieldName -> fieldID for title/DOI/date."""
    rows = conn.execute(
        "SELECT fieldName, fieldID FROM fields "
        "WHERE fieldName IN ('title', 'DOI', 'date')"
    ).fetchall()
    return {name: fid for name, fid in rows}


def read_library_items(db_path: Optional[Path] = None,
                       limit: int = 50,
                       prefer_doi: bool = True) -> List[ZoteroItem]:
    """Read recent library items (title, DOI, authors, year) as seeds.

    Skips attachments and notes. Prefers items that have a DOI when
    ``prefer_doi`` is True (DOI-backed seeds yield better related/citing hits).
    """
    if db_path is None:
        db_path = find_zotero_db()
    if db_path is None:
        return []

    conn = _connect_ro(db_path)
    if conn is None:
        return []

    try:
        fields = _field_map(conn)
        title_fid = fields.get("title")
        doi_fid = fields.get("DOI")
        date_fid = fields.get("date")
        if title_fid is None:
            return []

        # itemTypeID 1 = note in classic schemas; also exclude by typeName.
        rows = conn.execute(
            """
            SELECT i.itemID,
                   title_v.value AS title,
                   doi_v.value AS doi,
                   date_v.value AS date_raw
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            LEFT JOIN itemData title_d
                   ON i.itemID = title_d.itemID AND title_d.fieldID = ?
            LEFT JOIN itemDataValues title_v ON title_d.valueID = title_v.valueID
            LEFT JOIN itemData doi_d
                   ON i.itemID = doi_d.itemID AND doi_d.fieldID = ?
            LEFT JOIN itemDataValues doi_v ON doi_d.valueID = doi_v.valueID
            LEFT JOIN itemData date_d
                   ON i.itemID = date_d.itemID AND date_d.fieldID = ?
            LEFT JOIN itemDataValues date_v ON date_d.valueID = date_v.valueID
            WHERE it.typeName NOT IN ('attachment', 'note', 'annotation')
              AND title_v.value IS NOT NULL
              AND TRIM(title_v.value) != ''
            ORDER BY i.itemID DESC
            LIMIT ?
            """,
            (title_fid, doi_fid or -1, date_fid or -1, max(limit * 3, limit)),
        ).fetchall()

        items: List[ZoteroItem] = []
        item_ids: List[int] = []
        for item_id, title, doi, date_raw in rows:
            doi_n = _normalize_doi(doi or "")
            items.append(ZoteroItem(
                item_id=int(item_id),
                title=" ".join((title or "").split()),
                doi=doi_n,
                year=_parse_year(date_raw or ""),
                date_raw=date_raw or "",
            ))
            item_ids.append(int(item_id))

        # Authors in one query
        if item_ids:
            placeholders = ",".join("?" * len(item_ids))
            creator_rows = conn.execute(
                f"""
                SELECT ic.itemID, c.firstName, c.lastName
                FROM itemCreators ic
                JOIN creators c ON ic.creatorID = c.creatorID
                WHERE ic.itemID IN ({placeholders})
                ORDER BY ic.itemID, ic.orderIndex
                """,
                item_ids,
            ).fetchall()
            authors_by_id: Dict[int, List[str]] = {}
            for iid, first, last in creator_rows:
                name = " ".join(p for p in (first or "", last or "") if p).strip()
                if name:
                    authors_by_id.setdefault(int(iid), []).append(name)
            for item in items:
                item.authors = authors_by_id.get(item.item_id, [])
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    if prefer_doi:
        with_doi = [i for i in items if i.doi]
        without = [i for i in items if not i.doi]
        items = with_doi + without

    return items[:limit]


def library_identifiers(db_path: Optional[Path] = None,
                        limit: int = 5000) -> Tuple[Set[str], Set[str]]:
    """Return (dois, normalized_titles) already present in the library."""
    if db_path is None:
        db_path = find_zotero_db()
    if db_path is None:
        return set(), set()

    dois: Set[str] = set()
    titles: Set[str] = set()
    conn = _connect_ro(db_path)
    if conn is None:
        return dois, titles
    try:
        fields = _field_map(conn)
        title_fid = fields.get("title")
        doi_fid = fields.get("DOI")
        if title_fid is not None:
            for (title,) in conn.execute(
                """
                SELECT v.value FROM itemData d
                JOIN itemDataValues v ON d.valueID = v.valueID
                WHERE d.fieldID = ?
                LIMIT ?
                """,
                (title_fid, limit),
            ):
                key = re.sub(r"[^a-z0-9]", "", (title or "").lower())
                if key:
                    titles.add(key)
        if doi_fid is not None:
            for (doi,) in conn.execute(
                """
                SELECT v.value FROM itemData d
                JOIN itemDataValues v ON d.valueID = v.valueID
                WHERE d.fieldID = ?
                LIMIT ?
                """,
                (doi_fid, limit),
            ):
                n = _normalize_doi(doi or "")
                if n:
                    dois.add(n)
    except sqlite3.Error:
        return dois, titles
    finally:
        conn.close()
    return dois, titles


# ── Map Zotero data to ResearchPulse topics ──────────────────────────────

def _match_topics(tags: List[str], collections: List[str],
                  titles: List[str]) -> List[Tuple[str, str, float]]:
    """Score each ResearchPulse topic against the user's Zotero data.

    Returns a sorted list of (topic_id, topic_label, confidence) tuples where
    confidence is 0.0-1.0 indicating how well the user's library matches.
    """
    rp_topics, _ = load_topics()

    # Build a combined bag of lowercase terms from the user's Zotero data.
    all_terms = []
    for tag in tags:
        all_terms.extend(tag.lower().split())
    for col in collections:
        all_terms.extend(col.lower().split())
    for title in titles:
        all_terms.extend(title.lower().split())

    term_counts = Counter(all_terms)
    total_terms = max(len(all_terms), 1)

    results: List[Tuple[str, str, float]] = []
    for topic in rp_topics:
        hits = 0
        max_possible = max(len(topic.keywords), 1)
        for kw in topic.keywords:
            kw_parts = kw.lower().split()
            for part in kw_parts:
                if term_counts.get(part, 0) > 0:
                    hits += term_counts[part]
        # Normalize: how many of the topic's keywords were found, weighted by
        # how often they appear.
        score = min(1.0, (hits / max_possible) / 10.0)

        # Boost if a collection name closely matches the topic label.
        for col in collections:
            if topic.id in col.lower() or topic.label.lower() in col.lower():
                score = min(1.0, score + 0.4)

        # Boost if tags directly contain topic keywords.
        tag_set = {t.lower() for t in tags}
        for kw in topic.keywords:
            if kw.lower() in tag_set:
                score = min(1.0, score + 0.25)

        if score > 0.05:
            results.append((topic.id, topic.label, round(score, 2)))

    results.sort(key=lambda x: x[2], reverse=True)
    return results


# ── Public API ───────────────────────────────────────────────────────────

def detect_topics(db_path: Optional[Path] = None) -> List[Tuple[str, str, float]]:
    """Detect the user's research domains from their Zotero library.

    Returns a list of (topic_id, topic_label, confidence) tuples, sorted by
    confidence descending. Returns an empty list if Zotero is not found.
    """
    if db_path is None:
        db_path = find_zotero_db()
    if db_path is None:
        return []

    tags = _read_tags(db_path)
    collections = _read_collections(db_path)
    titles = _read_titles(db_path)

    return _match_topics(tags, collections, titles)


def get_zotero_summary(db_path: Optional[Path] = None) -> Optional[Dict]:
    """Get a summary of the user's Zotero library for display."""
    if db_path is None:
        db_path = find_zotero_db()
    if db_path is None:
        return None

    tags = _read_tags(db_path)
    collections = _read_collections(db_path)
    return {
        "db_path": str(db_path),
        "item_count": _read_item_count(db_path),
        "tag_count": len(tags),
        "collection_count": len(collections),
        "top_tags": tags[:15],
        "collections": collections,
    }


def detect_and_print() -> int:
    """CLI entry point: detect Zotero and print domain suggestions."""
    print("\nSearching for Zotero on your system...")

    db = find_zotero_db()
    if db is None:
        print("\n  Zotero database not found.")
        print("\n  Expected locations:")
        for p in _default_zotero_paths():
            print(f"    {p}")
        print("\n  If Zotero is installed in a custom location, set:")
        print("    ZOTERO_DATA_DIR=/path/to/your/zotero/data")
        print("\n  You can still use ResearchPulse without Zotero.")
        print("  Run: python -m research_agent setup")
        return 1

    summary = get_zotero_summary(db)
    print(f"\n  Found Zotero: {db}")
    print(f"  Items: {summary['item_count']}")
    print(f"  Tags: {summary['tag_count']}")
    print(f"  Collections: {summary['collection_count']}")

    if summary["top_tags"]:
        print(f"\n  Your top tags: {', '.join(summary['top_tags'][:10])}")
    if summary["collections"]:
        print(f"  Your collections: {', '.join(summary['collections'][:10])}")

    topics = detect_topics(db)
    if topics:
        print("\n  Suggested ResearchPulse topics based on your library:\n")
        for tid, label, conf in topics:
            bar = "#" * int(conf * 20)
            pct = int(conf * 100)
            print(f"    {tid:20s}  {label:40s}  [{bar:<20s}] {pct}%")

        suggested = [t[0] for t in topics if t[2] >= 0.15]
        if suggested:
            print(f"\n  Quick start with your domains:")
            print(f"    python -m research_agent digest --topics {' '.join(suggested)} --open\n")
    else:
        print("\n  Could not match your library to specific topics.")
        print("  Your Zotero library may focus on domains not yet in topics.yaml.")
        print("  Add custom topics to config/topics.yaml.\n")

    return 0
