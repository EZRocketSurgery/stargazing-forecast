import time
from datetime import datetime, timedelta, timezone

import pytest

from stargazing import brief
from stargazing.weather import ForecastDay

# Tomorrow at midnight, so every generated hour is in the future. UTC keeps hours
# exactly 3600s apart even across a DST change.
START = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
         + timedelta(days=1))


def make_hour(offset: int, cloud: int = 10, vis_miles: float = 6.0, is_day: int = 0) -> dict:
    t = START + timedelta(hours=offset)
    return {"time_epoch": int(t.timestamp()), "time": f"{t:%Y-%m-%d %H:%M}",
            "cloud": cloud, "vis_miles": vis_miles, "is_day": is_day}


def make_day(day_offset: int, hours: list[dict], moon_phase: str = "New Moon",
             moon_illumination: int = 0) -> ForecastDay:
    date = START + timedelta(days=day_offset)
    return ForecastDay({
        "date": f"{date:%Y-%m-%d}",
        "astro": {"moonrise": "06:12 AM", "moonset": "07:30 PM",
                  "moon_phase": moon_phase, "moon_illumination": moon_illumination},
        "hour": hours,
    })


@pytest.mark.parametrize("hour, bad", [
    (make_hour(0), False),
    (make_hour(0, is_day=1), True),
    (make_hour(0, cloud=76), True),
    (make_hour(0, cloud=75), False),
    (make_hour(0, vis_miles=0.5), True),
    ({"time_epoch": 0}, False),  # missing keys aren't held against the hour
])
def test_is_bad_hour(hour, bad):
    assert brief.is_bad_hour(hour) is bad


def test_group_windows_splits_on_gaps():
    hours = [make_hour(i) for i in (0, 1, 2, 5, 6, 9)]
    windows = brief.group_windows(hours)
    assert [len(w) for w in windows] == [3, 2, 1]


def test_good_hours_skips_past_and_bad_hours():
    past = {"time_epoch": int(time.time()) - 7200, "time": "", "cloud": 0, "vis_miles": 10, "is_day": 0}
    day = make_day(0, [past, make_hour(0), make_hour(1, cloud=90), make_hour(2)])
    assert [h["time_epoch"] for h in brief.good_hours([day])] == [make_hour(0)["time_epoch"],
                                                                   make_hour(2)["time_epoch"]]


@pytest.mark.parametrize("cloud, emoji", [(0, "🟢"), (30, "🟡"), (60, "🟠"), (75, "🟠")])
def test_cloud_rating(cloud, emoji):
    assert brief._cloud_rating(cloud) == emoji


def test_moon_too_bright():
    assert brief.moon_too_bright(make_day(0, [], "Full Moon", 99))
    assert brief.moon_too_bright(make_day(0, [], "Waxing Crescent", 60))
    assert not brief.moon_too_bright(make_day(0, [], "Waxing Crescent", 20))


def test_brief_lists_windows_under_their_day(monkeypatch):
    forecast = [make_day(0, [make_hour(i, cloud=10) for i in range(0, 4)]
                         + [make_hour(i, is_day=1) for i in range(4, 24)], "Full Moon", 98),
                make_day(1, [make_hour(i, is_day=1) for i in range(24, 47)] + [make_hour(47, cloud=40)])]
    monkeypatch.setattr(brief, "get_forecast",
                        lambda q, days: ({"name": "Burlington", "region": "Vermont"}, forecast))

    text = brief.stargazing_brief("burlington")

    assert text.startswith("## 🔭 Stargazing · Burlington, Vermont\n")
    assert "🟢 **12:00 AM – 4:00 AM** · ☁️ 10% · 6.0 mi vis" in text
    assert "⚠️ bright moon" in text
    # The last forecast hour can't say when the window really ends
    assert "🟡 **11:00 PM – data ends**" in text
    assert text.index(f"{START + timedelta(days=1):%a %b}") > text.index("4:00 AM")


def test_brief_with_no_good_hours(monkeypatch):
    forecast = [make_day(0, [make_hour(i, cloud=100) for i in range(24)])]
    monkeypatch.setattr(brief, "get_forecast", lambda q, days: ({}, forecast))
    assert brief.stargazing_brief("nowhere") == (
        "## 🔭 Stargazing · nowhere\nNo good stargazing windows in the forecast.\n")


def test_fit_message_trims_to_discord_limit():
    lines = ["## header"]
    for i in range(200):
        lines += [f"### Day {i}", "Moonrise 6:00 AM · Moonset 7:00 PM", "🟢 **1:00 AM – 2:00 AM** · ☁️ 5% · 6 mi vis"]
    fitted = brief._fit_message(lines, ["-# footer"])
    assert len("\n".join(fitted)) + 1 <= brief.MAX_MESSAGE_LENGTH
    assert fitted[-2] == "-# …more windows not shown"
    assert fitted[-3].startswith("🟢")  # no orphaned day header before the note
