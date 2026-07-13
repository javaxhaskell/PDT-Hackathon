"""Health, methodology and symbol-search endpoints."""

from __future__ import annotations

from app import config


class TestHealth:
    def test_health_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == config.METHODOLOGY_VERSION
        assert isinstance(body["deepseek_configured"], bool)


class TestMethodology:
    def test_exposes_frozen_thresholds(self, client):
        body = client.get("/api/methodology").json()
        assert body["methodology_version"] == config.METHODOLOGY_VERSION
        assert body["correlation"]["min_correlation"] == config.MIN_CORRELATION
        assert body["signal"]["entry_z"] == config.ENTRY_Z
        assert body["signal"]["stop_z"] == config.STOP_Z
        assert body["backtest_gate"]["min_trades"] == config.MIN_TRADES
        assert body["sizing"]["risk_profiles"]["balanced"]["max_gross_fraction"] == 0.75
        assert body["data"]["stale_calendar_days"] == config.STALE_CALENDAR_DAYS


class TestSymbolSearch:
    def test_empty_query_returns_empty_results(self, client):
        body = client.get("/api/symbols/search", params={"q": "  "}).json()
        assert body == {"results": []}

    def test_provider_failure_falls_back_to_empty(self, api, client, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr(api.yfinance, "Search", boom)
        response = client.get("/api/symbols/search", params={"q": "coca"})
        assert response.status_code == 200
        assert response.json() == {"results": []}

    def test_results_mapped(self, api, client, monkeypatch):
        class FakeSearch:
            def __init__(self, *args, **kwargs):
                self.quotes = [
                    {"symbol": "KO", "shortname": "Coca-Cola", "exchDisp": "NYSE"},
                    {"noSymbol": True},
                ]

        monkeypatch.setattr(api.yfinance, "Search", FakeSearch)
        body = client.get("/api/symbols/search", params={"q": "coca"}).json()
        assert body["results"] == [
            {"symbol": "KO", "name": "Coca-Cola", "exchange": "NYSE", "currency": None}
        ]
