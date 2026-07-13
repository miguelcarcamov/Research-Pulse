"""Unit tests for remaining modules not covered by the first pass."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from research_agent import __version__
from research_agent.cache import SeenCache
from research_agent.config import Secrets, Topic, load_settings
from research_agent.models import NewsItem, Paper
from research_agent.subscribers import Subscriber


pytestmark = pytest.mark.unit


def _empty_secrets(**overrides) -> Secrets:
    base = dict(
        subscribers_csv_url="",
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_key="",
        sender_email="",
        sender_name="",
        site_url="",
        groq_api_key="",
        gemini_api_key="",
        ollama_host="",
        ollama_model="llama3.2",
    )
    base.update(overrides)
    return Secrets(**base)


def test_package_version():
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 1


def test_main_module_imports():
    from research_agent.__main__ import main
    assert callable(main)


def test_sources_package_exports():
    from research_agent import sources
    assert sources is not None


def test_bundled_package():
    import research_agent.bundled as bundled
    assert bundled is not None


# ── render ──────────────────────────────────────────────────────────────


def test_render_digest_html(sample_paper):
    from research_agent.render import render_digest, _unsubscribe_url

    settings = load_settings()
    secrets = _empty_secrets(site_url="https://example.com")
    sub = Subscriber(email="a@b.com", topics=["ai-ml"], token="tok123")
    html = render_digest(
        sub,
        papers_by_topic={"ai-ml": [sample_paper]},
        topic_labels={"ai-ml": "AI / ML"},
        news=[NewsItem(title="News", url="https://n.example", source="Test")],
        settings=settings,
        secrets=secrets,
    )
    assert isinstance(html, str)
    assert len(html) > 50
    assert _unsubscribe_url(secrets, sub)


def test_unsubscribe_url_requires_site_and_token():
    from research_agent.render import _unsubscribe_url

    secrets = _empty_secrets()
    sub = Subscriber(email="a@b.com", topics=[], token="")
    assert _unsubscribe_url(secrets, sub) is None


# ── mailer ──────────────────────────────────────────────────────────────


def test_mailer_configured_false():
    from research_agent.mailer import Mailer

    m = Mailer(_empty_secrets())
    assert m.configured is False


def test_mailer_send_without_connect_raises():
    from research_agent.mailer import Mailer

    secrets = _empty_secrets(
        smtp_host="smtp.example",
        smtp_user="u",
        smtp_key="k",
        sender_email="from@example.com",
        sender_name="RP",
    )
    m = Mailer(secrets)
    assert m.configured is True
    with pytest.raises(RuntimeError, match="not connected"):
        m.send("to@example.com", "subj", "<p>hi</p>")


# ── chat ────────────────────────────────────────────────────────────────


def test_ask_about_paper_without_llm(sample_paper, monkeypatch):
    from research_agent import chat as chat_mod

    monkeypatch.setattr(chat_mod, "_generate", lambda prompt: None)
    assert chat_mod.ask_about_paper(sample_paper, "What?") is None
    assert chat_mod.ask_about_paper(sample_paper, "  ") is None


def test_get_llm_backend_none_without_keys(monkeypatch):
    from research_agent import chat as chat_mod

    monkeypatch.setattr(chat_mod, "load_secrets", lambda: _empty_secrets())
    assert chat_mod.is_llm_available() is False
    assert chat_mod.get_llm_backend() == "none"


# ── critique ────────────────────────────────────────────────────────────


def test_challenge_hypothesis_without_llm(sample_papers, monkeypatch):
    from research_agent import critique as critique_mod

    monkeypatch.setattr(critique_mod, "is_llm_available", lambda: False)
    monkeypatch.setattr(critique_mod, "challenge_hypothesis_llm", lambda *a, **k: None)
    text = critique_mod.challenge_hypothesis(
        "Attention mechanisms improve NLP models significantly",
        sample_papers,
        use_llm=False,
    )
    assert isinstance(text, str)
    assert "HYPOTHESIS" in text.upper() or "Attention" in text


def test_extract_claims():
    from research_agent.critique import _extract_claims

    claims = _extract_claims("This method shows strong results. Short.")
    assert any("shows" in c.lower() for c in claims)


# ── ui ──────────────────────────────────────────────────────────────────


def test_ui_messages_dont_crash(capsys):
    from research_agent import ui

    ui.info("hello")
    ui.warn("careful")
    ui.success("ok")
    ui.error("boom")
    ui.rule("title")
    ui.banner("subtitle")


def test_ui_show_help():
    from research_agent import ui
    ui.show_help()


def test_ui_quiet_logs():
    from research_agent import ui
    with ui.quiet_logs():
        pass


# ── pipeline helpers ────────────────────────────────────────────────────


def test_pipeline_normalize_and_active_topics(tmp_path):
    from research_agent.pipeline import _normalize_title, _active_topic_ids, _dedup

    assert _normalize_title("Hello, World!") == "helloworld"
    active = _active_topic_ids(
        [Subscriber(email="a@b.c", topics=["ai-ml", "nope"])],
        {"ai-ml", "nlp"},
    )
    assert active == {"ai-ml"}

    cache = SeenCache(path=tmp_path / "seen.json")
    cache.mark(["dup-id"])
    papers = [
        Paper(id="dup-id", title="A", abstract="", authors=[], url="", source="x"),
        Paper(id="new", title="Unique Title", abstract="", authors=[], url="", source="x"),
        Paper(id="new2", title="Unique Title", abstract="", authors=[], url="", source="x"),
    ]
    out = _dedup(papers, cache)
    assert len(out) == 1
    assert out[0].id == "new"


def test_fetch_topic_parallel_mocked():
    from research_agent import pipeline

    topic = Topic(
        id="t",
        label="T",
        keywords=["k"],
        arxiv=[],
        biorxiv=["biorxiv"],
        openalex="query",
        semanticscholar="",
        europepmc="",
    )
    fake = [Paper(id="1", title="P", abstract="k", authors=[], url="", source="bioRxiv")]

    with patch.object(pipeline.biorxiv, "fetch", return_value=fake), \
         patch.object(pipeline.openalex, "fetch", return_value=[]), \
         patch.object(pipeline.semanticscholar, "fetch", return_value=[]), \
         patch.object(pipeline.europepmc, "fetch", return_value=[]), \
         patch.object(pipeline.arxiv, "fetch", return_value=[]):
        papers = pipeline._fetch_topic(topic, load_settings(), _empty_secrets())
    assert papers


# ── agent helpers ───────────────────────────────────────────────────────


def test_agent_display_papers_plain(sample_papers, capsys):
    from research_agent.agent import display_papers

    display_papers(sample_papers, "Test Results")
    out = capsys.readouterr().out
    assert "Test Results" in out or sample_papers[0].title[:10] in out


def test_agent_cmd_recommend_zotero_missing(monkeypatch, capsys, tmp_path):
    from research_agent.agent import cmd_recommend
    from research_agent.memory import ResearchMemory

    monkeypatch.setattr("research_agent.zotero.find_zotero_db", lambda: None)
    cmd_recommend([], ResearchMemory(path=tmp_path / "mem.json"), "zotero")
    out = capsys.readouterr().out
    assert "Zotero" in out


# ── setup module ────────────────────────────────────────────────────────


def test_setup_module_importable():
    import research_agent.setup as setup_mod
    assert callable(setup_mod.run_setup)
