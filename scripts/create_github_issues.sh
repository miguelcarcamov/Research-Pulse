#!/usr/bin/env bash
# Create tracked GitHub issues for ResearchPulse.
# Requires: gh auth login (repo scope)
set -euo pipefail

REPO="${REPO:-miguelcarcamov/Research-Pulse}"

ensure_label() {
  local name="$1" color="$2" desc="$3"
  if ! gh label list --repo "$REPO" --limit 200 | awk '{print $1}' | grep -qx "$name"; then
    gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" 2>/dev/null || true
  fi
}

echo "Ensuring labels…"
ensure_label "enhancement" "a2eeef" "New feature or request"
ensure_label "bug" "d73a4a" "Something isn't working"
ensure_label "performance" "fbca04" "Performance / efficiency"
ensure_label "ci" "5319e7" "Continuous integration"
ensure_label "testing" "0e8a16" "Test suite / coverage"
ensure_label "docs" "0075ca" "Documentation"

create_issue() {
  local title="$1"
  local labels="$2"
  local body="$3"
  echo "→ $title"
  gh issue create --repo "$REPO" --title "$title" --label "$labels" --body "$body"
}

create_issue "CI: Expand and harden GitHub Actions (tests, lint, status checks)" "ci,enhancement" "$(cat <<'EOF'
## Summary
We now have `.github/workflows/test.yml`, but CI should be a first-class gate: multi-Python matrix, lint, coverage awareness, and required checks on `master`.

Existing workflows also include `daily.yml` (newsletter) and `publish-pypi.yml` (releases) — those are ops/release, not PR CI.

## Acceptance criteria
- [ ] Test workflow runs on push + PR with a clear job name
- [ ] Python version matrix (at least 3.10–3.12)
- [ ] Optional lint job (e.g. `ruff check`)
- [ ] Coverage reported in CI; consider a soft floor (not necessarily hard fail at first)
- [ ] README badge for test workflow status
- [ ] Confirm Actions are enabled for the repo; consider required status checks on `master`
- [ ] Document secrets needed only for `daily` / `publish-pypi` (not for PR tests)

## Notes
PR unit/integration tests must stay offline (mocked HTTP) — no API keys required for CI green.
EOF
)"

create_issue "perf: Parallelize multi-topic digest fetching" "performance,enhancement" "$(cat <<'EOF'
## Summary
`pipeline.run` fetches topics sequentially. Each topic pays its own arXiv polite delay, so N topics ≈ N × (network + arXiv sleep).

## Proposal
- Fetch independent topics concurrently (bounded thread pool), keeping arXiv rate limits in mind (global lock / shared delay).
- Preserve progress callbacks for the CLI spinner.

## Acceptance criteria
- [ ] Multi-topic dry-run digest is faster for ≥3 topics without hammering arXiv
- [ ] Source failures remain isolated per topic
- [ ] Unit/integration coverage for concurrency + delay behavior
EOF
)"

create_issue "perf: Add HTTP response caching for scholarly APIs" "performance,enhancement" "$(cat <<'EOF'
## Summary
`sources/http.py` retries but does not cache. Repeated digests/searches re-hit OpenAlex, Crossref, Europe PMC, etc.

## Proposal
- Disk cache keyed by URL+params (TTL, e.g. 6–24h)
- Respect `Cache-Control` / `ETag` when present
- Clear env flag to bypass (`RESEARCHPULSE_HTTP_CACHE=0`)

## Acceptance criteria
- [ ] Identical GETs within TTL reuse cache
- [ ] No behavior change for callers
- [ ] Tests with mocked filesystem / temp cache dir
EOF
)"

create_issue "perf: Batch or cache LLM paper summaries" "performance,enhancement" "$(cat <<'EOF'
## Summary
`summarize.annotate` calls the LLM once per paper (timeouts 40–120s). Digests with LLM keys become very slow.

## Proposal
- Short-circuit if a paper id already has a cached summary (`data/summary_cache.json` or similar)
- Optional batch prompt when the backend supports it
- Keep abstract-trim fallback when no LLM / cache miss timeout

## Acceptance criteria
- [ ] Second digest of same papers skips LLM when cached
- [ ] Clear docs for Groq/Gemini/Ollama behavior
- [ ] Tests for cache hit/miss without live APIs
EOF
)"

create_issue "feat: Enrich Zotero recommend (collections, tags, Semantic Scholar)" "enhancement" "$(cat <<'EOF'
## Summary
`zotero recommend` uses recent DOI seeds + OpenAlex related/citing. Power users need collection/tag filters and optional Semantic Scholar when `S2_API_KEY` is set.

## Acceptance criteria
- [ ] `--collection` / `--tag` filters for seed selection
- [ ] Optional S2 related-paper expansion when key present (graceful skip otherwise)
- [ ] Better reason strings (citing vs related when distinguishable)
- [ ] Tests with fake Zotero DB + mocked APIs
EOF
)"

create_issue "feat: Export recommendations to BibTeX / RIS for Zotero import" "enhancement" "$(cat <<'EOF'
## Summary
Recommendations are CLI/HTML only. Researchers want a one-click path back into Zotero.

## Acceptance criteria
- [ ] `research-pulse zotero recommend --export recommendations.bib`
- [ ] Support BibTeX and optionally RIS
- [ ] Fields: title, authors, year, DOI, URL, abstract when available
- [ ] Unit tests for exporters
EOF
)"

create_issue "bug: Digests are slow under multi-topic arXiv polite delay" "bug,performance" "$(cat <<'EOF'
## Summary
arXiv politely sleeps after every request (`arxiv_request_delay`, default ~3s). Combined with sequential topics, digests become painfully slow.

## Related
Topic parallelism issue; may share a rate-limiter design.

## Acceptance criteria
- [ ] Shared arXiv rate limiter across topics/threads
- [ ] Document expected runtime for N topics
- [ ] Tests that delay is applied once per actual request, not spuriously
EOF
)"

create_issue "bug: memory.json rewritten on every chat mutation" "bug,performance" "$(cat <<'EOF'
## Summary
`ResearchMemory.save()` rewrites the full JSON after each `record_*` / interest change. Large histories make interactive chat I/O-heavy.

## Acceptance criteria
- [ ] Debounced / batched saves (e.g. flush on quit + periodic)
- [ ] Atomic write (temp file + replace)
- [ ] Tests for persistence across quit without data loss
EOF
)"

create_issue "testing: Raise coverage on CLI and interactive agent paths" "testing,enhancement" "$(cat <<'EOF'
## Summary
Overall coverage is ~50%. `cli.py` and `agent.py` remain thinly covered (smoke only).

## Acceptance criteria
- [ ] Parametrized CLI tests for main commands (`today` mocked, `search`, `topics`, `follow`, `config`)
- [ ] Agent command handlers tested with mocked search/LLM
- [ ] Aim for ≥70% package coverage without live network
EOF
)"

create_issue "chore: Sync CHANGELOG on release and bump version for Zotero recommend" "docs,enhancement" "$(cat <<'EOF'
## Summary
`CHANGELOG.md` tracks `[Unreleased]` work (Zotero recommend, tests, conda envs). Cut a `0.4.8` (or `0.5.0`) release: move Unreleased → dated section, bump `pyproject.toml` / `__version__`, tag, publish.

## Acceptance criteria
- [ ] Version bump in package metadata
- [ ] Changelog section with date
- [ ] Git tag + GitHub Release notes from changelog
- [ ] Optional PyPI publish via existing workflow
EOF
)"

create_issue "docs: Architecture overview for contributors" "docs,enhancement" "$(cat <<'EOF'
## Summary
README covers usage. Contributors need a short architecture map (CLI → pipeline → sources → rank/summarize → render/mail).

## Acceptance criteria
- [ ] `docs/architecture.md` (or README section) with module responsibilities + mermaid diagram
- [ ] Link from README
- [ ] Note config roots (clone vs pip install / `RESEARCHPULSE_HOME`)
EOF
)"

echo "Done. Open issues: gh issue list --repo $REPO"
