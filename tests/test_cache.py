import time

import pytest

from stargazing import cache, weather


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


@pytest.fixture
def api_calls(tmp_path, monkeypatch):
    """Point the cache at a temp dir and record every (fake) API call."""
    monkeypatch.setenv("STARGAZING_CACHE_DIR", str(tmp_path))
    calls = []
    responses = []

    def fake_api(endpoint, q, **params):
        calls.append((endpoint, q, params))
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr(weather, "weather_api", fake_api)
    return calls, responses


def test_fresh_response_is_served_from_cache(api_calls):
    calls, responses = api_calls
    responses.append({"location": {"localtime_epoch": int(time.time())}, "forecast": {}})
    first = cache.get_weather_data("forecast", "Burlington, VT", days=3)
    second = cache.get_weather_data("forecast", "burlington, vt", days=3)
    assert first == second
    assert len(calls) == 1


def test_params_are_part_of_the_cache_key(api_calls):
    calls, responses = api_calls
    now = int(time.time())
    responses += [{"location": {"localtime_epoch": now}}] * 2
    cache.get_weather_data("forecast", "Burlington", days=3)
    cache.get_weather_data("forecast", "Burlington", days=1)
    assert len(calls) == 2


def test_stale_response_is_refetched(api_calls):
    calls, responses = api_calls
    responses += [{"location": {"localtime_epoch": int(time.time()) - 2 * cache.MAX_AGE_SECONDS}},
                  {"location": {"localtime_epoch": int(time.time())}}]
    cache.get_weather_data("forecast", "Burlington")
    cache.get_weather_data("forecast", "Burlington")
    assert len(calls) == 2


def test_api_errors_raise_and_are_not_cached(api_calls):
    calls, responses = api_calls
    responses += [{"error": {"code": 1006, "message": "No matching location found."}}] * 2
    for _ in range(2):
        with pytest.raises(weather.WeatherAPIError, match="No matching location"):
            cache.get_weather_data("forecast", "Atlantis")
    assert len(calls) == 2


def test_cache_path_stays_inside_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STARGAZING_CACHE_DIR", str(tmp_path))
    path = cache._cache_path("../../etc/passwd", "forecast")
    assert path.startswith(str(tmp_path))
    assert ".." not in path[len(str(tmp_path)):]
