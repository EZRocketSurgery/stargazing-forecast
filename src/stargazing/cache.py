"""
Caches weather API responses on disk for up to an hour.

q is in a lot of places in this module
It represents the query parameter used to differentiate
the requested location.
"""
import json
import logging
import os
import re
import tempfile
import time

from . import weather

logger = logging.getLogger(__name__)

MAX_AGE_SECONDS = 3600

def cache_dir() -> str:
    """STARGAZING_CACHE_DIR if set, otherwise a folder in the system temp directory."""
    return os.getenv("STARGAZING_CACHE_DIR") or os.path.join(tempfile.gettempdir(), "stargazing")

def _cache_path(q: str, endpoint: str, params: dict | None = None) -> str:
    # q is user input; keep it to a single safe folder name under the cache dir
    safe = re.sub(r"[^\w,-]+", "_", q.strip().lower())
    # Extra API params (e.g. days) change the response, so they're part of the cache key
    suffix = "".join(f"_{k}-{v}" for k, v in sorted((params or {}).items()))
    suffix = re.sub(r"[^\w-]+", "_", suffix)
    return os.path.join(cache_dir(), safe, f"{endpoint}{suffix}.json")

def write_tmp_data(endpoint: str, q: str, data: dict, params: dict | None = None) -> None:
    logger.debug("Writing data to file for endpoint '%s' and query '%s'", endpoint, q)
    path = _cache_path(q, endpoint, params)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def check_if_current(epoch: int) -> bool:
    current_epoch = int(time.time())
    return abs(current_epoch - epoch) < MAX_AGE_SECONDS

def check_tmp_data(q: str, endpoint: str, params: dict | None = None) -> dict|None:
    try:
        with open(_cache_path(q, endpoint, params), "r", encoding="utf-8") as f:
            data = json.load(f)
            epoch = data["location"]["localtime_epoch"]
            if check_if_current(epoch):
                logger.debug("Tmp data is current for endpoint '%s' and query '%s'", endpoint, q)
                return data
            else:
                logger.debug("Tmp data is outdated for endpoint '%s' and query '%s'", endpoint, q)
                return None
    except FileNotFoundError:
        logger.debug("Tmp file not found for endpoint '%s' and query '%s'", endpoint, q)
        return None
    except (KeyError, json.JSONDecodeError):
        # e.g. an API error response cached before errors were checked
        logger.debug("Tmp file unusable for endpoint '%s' and query '%s'", endpoint, q)
        return None

def get_weather_data(endpoint: str, q: str, **kwargs) -> dict:
    """Return the cached response if it's under an hour old, otherwise fetch and cache a new one.

    Raises:
        weather.WeatherAPIError: The API returned an error (bad key, unknown location, ...).
    """
    data = check_tmp_data(q, endpoint, kwargs)
    if data is not None:
        return data
    logger.debug("Fetching new weather data for endpoint '%s' and query '%s'", endpoint, q)
    data = weather.weather_api(endpoint, q=q, **kwargs).json()
    if "error" in data:
        raise weather.WeatherAPIError(data["error"].get("message", "Unknown error"))
    write_tmp_data(endpoint, q, data, kwargs)
    return data
