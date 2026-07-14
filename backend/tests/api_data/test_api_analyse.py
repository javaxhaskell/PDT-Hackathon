"""POST /api/analyse decision pipeline and fixture-mode determinism."""

from __future__ import annotations

from app.data.provider import PriceHistory

from .conftest import StubPriceProvider, fixture_analyse_payload, make_history


class TestFixtureDeterminism:
    def test_repeated_fixture_request_is_byte_identical(self, client):
        first = client.post("/api/analyse", json=fixture_analyse_payload())
        second = client.post("/api/analyse", json=fixture_analyse_payload())
        assert first.status_code == 200
        assert second.status_code == 200
        # Full byte-identical equality — retrieved_at is deterministic in
        # fixture mode (equal to the fixture capture time), so no field is
        # excluded from the comparison.
        assert first.content == second.content

    def test_fixture_retrieved_at_equals_captured_at(self, client):
        body = client.post("/api/analyse", json=fixture_analyse_payload()).json()
        data = body["data"]
        assert data["is_fixture"] is True
        assert data["fixture_captured_at"] is not None
        assert data["retrieved_at"] == data["fixture_captured_at"]

    def test_fixture_banner_warning_present(self, client):
        body = client.post("/api/analyse", json=fixture_analyse_payload()).json()
        banners = [w for w in body["warnings"] if w.startswith("Recorded market snapshot")]
        assert len(banners) == 1
        assert "fixture data captured 2026-07-13" in banners[0]

    def test_standard_warnings_present(self, client):
        body = client.post("/api/analyse", json=fixture_analyse_payload()).json()
        assert "Past performance doesn't guarantee future results." in body["warnings"]
        assert "Trades are paper examples only, not financial advice." in (
            body["warnings"]
        )

    def test_quant_result_merged(self, client):
        body = client.post("/api/analyse", json=fixture_analyse_payload()).json()
        assert body["state"] == "SELL_A_BUY_B"
        assert body["sizing"]["sized"] is True
        assert body["methodology_version"]
        assert body["data"]["n_common_observations"] >= 400
        assert "fake quant warning" in body["warnings"]


class TestDecisionPipeline:
    def test_missing_fixture_ticker_is_provider_error(self, client):
        body = client.post(
            "/api/analyse", json=fixture_analyse_payload(ticker_b="TSLA")
        ).json()
        assert body["state"] == "PROVIDER_ERROR"
        # The message must be plain English and list the available tickers.
        assert "TSLA" in body["explanation"]
        for available in ("KO", "NVDA", "PEP"):
            assert available in body["explanation"]

    def test_identical_tickers_case_insensitive(self, client):
        body = client.post(
            "/api/analyse", json=fixture_analyse_payload(ticker_a="ko", ticker_b="KO")
        ).json()
        assert body["state"] == "UNSUITABLE_PAIR"
        assert "same stock" in body["explanation"]

    def test_currency_mismatch_is_unsuitable_pair(self, api, client):
        histories = {
            "AAA": make_history("AAA", currency="USD"),
            "BBB": make_history("BBB", currency="EUR"),
        }
        api.app.dependency_overrides[api.get_price_provider_factory] = lambda: (
            lambda mode: StubPriceProvider(histories)
        )
        body = client.post(
            "/api/analyse", json=fixture_analyse_payload(ticker_a="AAA", ticker_b="BBB")
        ).json()
        assert body["state"] == "UNSUITABLE_PAIR"
        assert "USD" in body["explanation"] and "EUR" in body["explanation"]

    def test_short_history_is_insufficient_data(self, api, client):
        histories = {
            "AAA": make_history("AAA", n_days=120),
            "BBB": make_history("BBB", n_days=120),
        }
        api.app.dependency_overrides[api.get_price_provider_factory] = lambda: (
            lambda mode: StubPriceProvider(histories)
        )
        body = client.post(
            "/api/analyse",
            json=fixture_analyse_payload(ticker_a="AAA", ticker_b="BBB", lookback="1y"),
        ).json()
        assert body["state"] == "INSUFFICIENT_DATA"
        assert "120" in body["explanation"]
        assert "252" in body["explanation"]

    def test_stale_data_is_warning_not_error(self, api, client):
        stale = make_history("AAA", end="2026-06-01")
        stale = PriceHistory(
            df=stale.df,
            currency=stale.currency,
            exchange=stale.exchange,
            last_market_date=stale.last_market_date,
            provider=stale.provider,
            retrieved_at="2026-07-10T12:00:00+00:00",  # 39 days after last market date
            is_fixture=False,
            fixture_captured_at=None,
        )
        fresh = make_history("BBB", end="2026-06-01")
        fresh = PriceHistory(
            df=fresh.df,
            currency=fresh.currency,
            exchange=fresh.exchange,
            last_market_date=fresh.last_market_date,
            provider=fresh.provider,
            retrieved_at="2026-06-02T12:00:00+00:00",
            is_fixture=False,
            fixture_captured_at=None,
        )
        api.app.dependency_overrides[api.get_price_provider_factory] = lambda: (
            lambda mode: StubPriceProvider({"AAA": stale, "BBB": fresh})
        )
        body = client.post(
            "/api/analyse", json=fixture_analyse_payload(ticker_a="AAA", ticker_b="BBB")
        ).json()
        assert body["state"] == "SELL_A_BUY_B"  # analysis still ran
        stale_warnings = [w for w in body["warnings"] if "stale" in w]
        assert len(stale_warnings) == 1
        assert "AAA" in stale_warnings[0]

    def test_exchange_mismatch_warning(self, client):
        # KO trades on NYQ and PEP on NMS in the recorded fixtures.
        body = client.post("/api/analyse", json=fixture_analyse_payload()).json()
        assert any("different exchanges" in w for w in body["warnings"])

    def test_validation_error_is_structured(self, client):
        response = client.post("/api/analyse", json={"ticker_a": "KO"})
        assert response.status_code == 422
        body = response.json()
        assert body["error"] == "VALIDATION_ERROR"
        assert "message" in body
