# Changelog

All notable changes to ResearchPulse are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Conda/micromamba/mamba environment files: `environment.yml` (runtime) and `environment-dev.yml` (dev/packaging/tests)
- `research-pulse zotero recommend` (alias: `research-pulse recommend`) — suggest newer papers related to the local Zotero library via OpenAlex related/citing works
- Chat agent support: `recommend zotero`
- OpenAlex helpers for DOI lookup, related works, and citing papers (`sources/openalex.py`)
- Zotero library seed reading (title, DOI, authors, year) and owned DOI/title sets for dedup
- Pytest unit and integration suite under `tests/` (132+ tests), with fixtures including a fake Zotero SQLite DB
- GitHub Actions workflow `.github/workflows/test.yml` (unit + integration on push/PR)
- Optional extras: `pip install -e ".[test]"` and expanded `[dev]` with pytest/coverage

### Changed
- `search_by_topic` fetches non-arXiv sources in parallel
- Zotero summary no longer re-queries tags/collections twice
- Zotero SQLite opens with a lock-tolerant read path (`immutable=1` fallback when Zotero is running)
- `SeenCache` resolves its default path at construction time (test-friendly)
- README: reproducible env install, Zotero recommend docs, and testing section
- Test CI workflow: Python 3.10–3.12 matrix, concurrency, coverage artifact, status badge

### Fixed
- Silent empty Zotero reads when the database is locked by a running Zotero process

## [0.4.7] - 2026-07-13

### Notes
- Baseline release prior to the Unreleased work above (digest, multi-source search, Zotero topic detection, interactive agent).
