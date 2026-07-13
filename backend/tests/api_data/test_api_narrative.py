"""POST /api/narrative: grounding, failure modes and quant independence."""

from __future__ import annotations

import json

from app import config
from app.ai.deepseek import FakeNarrativeProvider, NarrativeError
from app.data.provider import canonical_content_hash

from .conftest import StubNewsProvider, fixture_analyse_payload, make_news_item


def narrative_payload(**overrides) -> dict:
    payload = {"ticker_a": "KO", "ticker_b": "PEP", "data_mode": "fixture"}
    payload.update(overrides)
    return payload


def stub_news(api, news: dict):
    provider = StubNewsProvider(news)
    api.app.dependency_overrides[api.get_news_provider_factory] = lambda: (
        lambda mode: provider
    )


def use_provider(api, provider):
    api.app.dependency_overrides[api.get_narrative_selector] = lambda: (
        lambda request: provider
    )


def valid_reply(**overrides) -> dict:
    reply = {
        "summary_a": "Company A had routine coverage.",
        "summary_b": "Company B had routine coverage.",
        "shared_story": None,
        "classification": "NO_OBVIOUS_NEWS_EXPLANATION",
        "confidence": "MEDIUM",
        "risk_flags": [],
        "evidence": [],
        "explanation": "Nothing in the supplied headlines stands out.",
    }
    reply.update(overrides)
    return reply


class TestNarrativeHappyPath:
    def test_fixture_news_with_fake_provider(self, api, client):
        use_provider(api, FakeNarrativeProvider())
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "ok"
        assert body["classification"] == "NO_OBVIOUS_NEWS_EXPLANATION"
        assert body["model"] == "fake-narrative"
        assert len(body["news_items"]) >= 4
        # Every news item supplied to the model is echoed with a stable id.
        assert all(item["source_id"].startswith("yf-") for item in body["news_items"])
        # Evidence cites only supplied ids.
        supplied = {item["source_id"] for item in body["news_items"]}
        for claim in body["evidence"]:
            assert set(claim["source_ids"]) <= supplied

    def test_not_configured_without_key(self, api, client, monkeypatch):
        monkeypatch.setattr(config, "DEEPSEEK_API_KEY", "")
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "not_configured"
        assert body["classification"] == "AI_UNAVAILABLE"
        # News is still returned so the UI can show headlines.
        assert len(body["news_items"]) >= 4


class TestNarrativeGrounding:
    def test_invalid_deepseek_json_is_handled_safely(self, api, client):
        use_provider(api, FakeNarrativeProvider(reply={"garbage": True}))
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "unavailable"
        assert body["classification"] == "AI_UNAVAILABLE"

    def test_invented_source_ids_are_stripped(self, api, client):
        news = {
            "KO": [make_news_item("KO", i) for i in range(3)],
            "PEP": [make_news_item("PEP", i) for i in range(3)],
        }
        stub_news(api, news)
        reply = valid_reply(
            evidence=[
                {"claim": "Invented claim.", "source_ids": ["yf-ko-0", "yf-invented-99"]},
                {"claim": "Grounded claim.", "source_ids": ["yf-pep-1"]},
            ]
        )
        use_provider(api, FakeNarrativeProvider(reply=reply))
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "ok"
        claims = [entry["claim"] for entry in body["evidence"]]
        assert claims == ["Grounded claim."]

    def test_explanation_truncated_to_word_cap(self, api, client):
        long_explanation = "word " * (config.MAX_EXPLANATION_WORDS + 40)
        use_provider(api, FakeNarrativeProvider(reply=valid_reply(explanation=long_explanation)))
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "ok"
        assert len(body["explanation"].split()) <= config.MAX_EXPLANATION_WORDS

    def test_elevated_news_risk_flag(self, api, client):
        reply = valid_reply(classification="POSSIBLE_COMPANY_SPECIFIC_EXPLANATION")
        use_provider(api, FakeNarrativeProvider(reply=reply))
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["elevated_news_risk"] is True

    def test_insufficient_news(self, api, client):
        news = {
            "KO": [make_news_item("KO", 0)],  # only one usable item
            "PEP": [make_news_item("PEP", i) for i in range(3)],
        }
        stub_news(api, news)
        use_provider(api, FakeNarrativeProvider())
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "insufficient_news"
        assert body["classification"] == "INSUFFICIENT_NEWS"


class TestQuantIndependence:
    def test_deepseek_timeout_leaves_quant_result_intact(self, api, client):
        analyse_before = client.post("/api/analyse", json=fixture_analyse_payload())
        use_provider(
            api, FakeNarrativeProvider(error=NarrativeError("DeepSeek request failed (Timeout)."))
        )
        narrative_response = client.post("/api/narrative", json=narrative_payload()).json()
        assert narrative_response["ai_status"] == "unavailable"
        assert narrative_response["classification"] == "AI_UNAVAILABLE"
        analyse_after = client.post("/api/analyse", json=fixture_analyse_payload())
        assert analyse_before.status_code == analyse_after.status_code == 200
        assert analyse_before.content == analyse_after.content

    def test_narrative_classification_never_changes_sizing(self, api, client):
        first = client.post("/api/analyse", json=fixture_analyse_payload())
        reply = valid_reply(classification="POSSIBLE_COMPANY_SPECIFIC_EXPLANATION")
        use_provider(api, FakeNarrativeProvider(reply=reply))
        narrative_body = client.post("/api/narrative", json=narrative_payload()).json()
        assert narrative_body["elevated_news_risk"] is True
        second = client.post("/api/analyse", json=fixture_analyse_payload())
        assert first.content == second.content
        assert first.json()["sizing"] == second.json()["sizing"]


class TestRecordedNarrative:
    def test_recorded_fixture_replayed_with_recorded_status(
        self, api, client, tmp_path, monkeypatch
    ):
        reply = valid_reply()
        fixture = {
            "metadata": {
                "pair": ["KO", "PEP"],
                "model": "deepseek-v4-flash",
                "captured_at": "2026-07-13T14:00:00+00:00",
                "content_hash": canonical_content_hash(reply),
            },
            "reply": reply,
        }
        (tmp_path / "narrative_KO_PEP.json").write_text(json.dumps(fixture))
        monkeypatch.setattr(api, "DEFAULT_FIXTURES_DIR", tmp_path)
        body = client.post("/api/narrative", json=narrative_payload()).json()
        assert body["ai_status"] == "recorded"
        assert body["model"] == "deepseek-v4-flash"
        assert body["recorded_at"] == "2026-07-13T14:00:00+00:00"
