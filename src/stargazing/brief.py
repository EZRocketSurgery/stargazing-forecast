"""
Uses weather forecast data to determine if the conditions are right for stargazing,
and builds a short brief of the upcoming windows.

Future planned features include:
- Alerting users when conditions are favorable for stargazing
- Integrating with astronomical data to provide notifications about celestial events
"""
import logging
import time
from datetime import datetime, timedelta

from . import cache, weather
from .weather import ForecastDay

logger = logging.getLogger(__name__)

# key: (value, and if higher(+), lower(-) or exact(=) is bad)
BAD_HOUR_THRESHOLDS = {
    "is_day": (1, "="),
    "cloud": (75, "+"),
    "vis_miles": (1, "-"),
}
BRIGHT_MOON_PHASES = ("full moon", "waxing gibbous", "waning gibbous")
BRIGHT_MOON_ILLUMINATION = 50
MOON_EMOJI = {
    "new moon": "🌑",
    "waxing crescent": "🌒",
    "first quarter": "🌓",
    "waxing gibbous": "🌔",
    "full moon": "🌕",
    "waning gibbous": "🌖",
    "last quarter": "🌗",
    "third quarter": "🌗",
    "waning crescent": "🌘",
}
# (max avg cloud %, emoji), checked in order; anything worse than the last is already filtered out
CLOUD_RATINGS = ((25, "🟢"), (50, "🟡"), (75, "🟠"))
MAX_MESSAGE_LENGTH = 2000  # Discord's limit for a regular message


def get_forecast(q: str, days: int = 3) -> tuple[dict, list[ForecastDay]]:
    """Get the weather forecast for the given location.

    Args:
        q (str): The location query.
        days (int): How many days to forecast.

    Returns:
        tuple[dict, list[ForecastDay]]: The resolved location and the forecast for each day.
    """
    response = cache.get_weather_data(endpoint="forecast", q=q, days=days)
    return response.get("location", {}), ForecastDay.from_response(response)

def is_bad_hour(hour: dict) -> bool:
    """Check an hour of forecast data against BAD_HOUR_THRESHOLDS."""
    for key, (value, condition) in BAD_HOUR_THRESHOLDS.items():
        if key not in hour:
            continue
        if condition == "=" and hour[key] == value:
            return True
        if condition == "+" and hour[key] > value:
            return True
        if condition == "-" and hour[key] < value:
            return True
    return False

def moon_too_bright(day: ForecastDay) -> bool:
    return (day.moon_phase.lower() in BRIGHT_MOON_PHASES
            or day.moon_illumination > BRIGHT_MOON_ILLUMINATION)

def good_hours(forecast: list[ForecastDay]) -> list[dict]:
    """Collect every hour still to come in the forecast that is good for stargazing, in time order."""
    now = time.time()
    # Keep the hour in progress; it isn't over yet.
    return [hour for day in forecast for hour in day.hours
            if hour["time_epoch"] + 3600 > now and not is_bad_hour(hour)]

def group_windows(hours: list[dict]) -> list[list[dict]]:
    """Group hours into windows of consecutive hours.

    Args:
        hours (list[dict]): The list of good stargazing hours, in time order.

    Returns:
        list[list[dict]]: A list of windows, each a list of consecutive hours.
    """
    windows = []
    for hour in hours:
        if windows and hour["time_epoch"] - windows[-1][-1]["time_epoch"] == 3600:
            windows[-1].append(hour)
        else:
            windows.append([hour])
    return windows

def _format_time(dt: datetime) -> str:
    return f"{dt:%I:%M %p}".lstrip("0")

def _cloud_rating(avg_cloud: int) -> str:
    for max_cloud, emoji in CLOUD_RATINGS:
        if avg_cloud < max_cloud:
            return emoji
    return CLOUD_RATINGS[-1][1]

def _format_day_header(date: str, day: ForecastDay | None) -> list[str]:
    d = datetime.strptime(date, "%Y-%m-%d")
    header = f"### {d:%a %b} {d.day}"
    if day is None:
        return [header]
    moon = MOON_EMOJI.get(day.moon_phase.lower(), "")
    lines = [f"{header} · {day.moon_phase} {day.moon_illumination}% {moon}".rstrip(),
             f"{weather.ASTRONOMY_KEYS['moonrise']} {day.moonrise.lstrip('0')} · "
             f"{weather.ASTRONOMY_KEYS['moonset']} {day.moonset.lstrip('0')}"]
    if moon_too_bright(day):
        lines[-1] += " · ⚠️ bright moon"
    return lines

def _format_window(window: list[dict], data_ends: bool = False) -> str:
    # "time" is in the location's local time, unlike time_epoch
    start = datetime.strptime(window[0]["time"], "%Y-%m-%d %H:%M")
    end = datetime.strptime(window[-1]["time"], "%Y-%m-%d %H:%M") + timedelta(hours=1)
    avg_cloud = round(sum(hour["cloud"] for hour in window) / len(window))
    min_vis = min(hour["vis_miles"] for hour in window)
    end_text = "data ends" if data_ends else _format_time(end)
    return (f"{_cloud_rating(avg_cloud)} **{_format_time(start)} – {end_text}** · "
            f"☁️ {avg_cloud}% · {min_vis} mi vis")

def stargazing_brief(q: str, days: int = 3) -> str:
    """Build a brief of the upcoming stargazing windows for the given location.

    Args:
        q (str): The location query.
        days (int): How many days to forecast.

    Returns:
        str: The stargazing brief, formatted with Discord markdown.
    """
    logger.debug("Generating stargazing brief for query '%s'", q)
    location, forecast = get_forecast(q, days)
    place = ", ".join(part for part in (location.get("name"), location.get("region")) if part) or q
    lines = [f"## 🔭 Stargazing · {place}"]
    hours = good_hours(forecast)
    if not hours:
        logger.debug("No good stargazing hours found in the forecast for query '%s'", q)
        return "\n".join(lines + ["No good stargazing windows in the forecast."]) + "\n"

    days_by_date = {day.date: day for day in forecast}
    last_epoch = forecast[-1].hours[-1]["time_epoch"]
    current_date = None
    # Windows can run past midnight; they're listed under the day they start.
    for window in group_windows(hours):
        date = window[0]["time"].split(" ")[0]
        if date != current_date:
            current_date = date
            lines += _format_day_header(date, days_by_date.get(date))
        lines.append(_format_window(window, window[-1]["time_epoch"] == last_epoch))
    legend = " ".join(f"{emoji} <{max_cloud}%" for max_cloud, emoji in CLOUD_RATINGS)
    footer = [f"-# Avg cloud cover: {legend} · Forecast via WeatherAPI"]
    return "\n".join(_fit_message(lines, footer)) + "\n"

def _fit_message(lines: list[str], footer: list[str]) -> list[str]:
    """Drop windows from the end until the message fits in MAX_MESSAGE_LENGTH."""
    note = "-# …more windows not shown"
    if len("\n".join(lines + footer)) + 1 <= MAX_MESSAGE_LENGTH:
        return lines + footer
    lines = lines[:]
    while len("\n".join(lines + [note] + footer)) + 1 > MAX_MESSAGE_LENGTH:
        lines.pop()
    # Don't leave a day header (and its moon line) with no windows under it
    while len(lines) > 1 and not lines[-1].startswith(tuple(emoji for _, emoji in CLOUD_RATINGS)):
        lines.pop()
    return lines + [note] + footer
