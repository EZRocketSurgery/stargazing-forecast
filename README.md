# 🔭 Stargazing Forecast

Tells you **when the sky will be dark and clear enough for stargazing** over the next few days, for any location.

It pulls an hourly forecast from [WeatherAPI](https://www.weatherapi.com/), throws out hours that are daylight, cloudy, or hazy, groups what's left into viewing windows, and flags nights when a bright moon will wash out faint objects. The output is a short Markdown brief, originally built for a `/stargazing_brief` command in my Discord bot.

```
## 🔭 Stargazing · Burlington, Vermont
### Tue Oct 27 · Waxing Gibbous 78% 🌔
Moonrise 3:41 PM · Moonset 4:02 AM · ⚠️ bright moon
🟢 **12:00 AM – 7:00 AM** · ☁️ 19% · 6.0 mi vis
🟡 **8:00 PM – 12:00 AM** · ☁️ 35% · 6.0 mi vis
### Wed Oct 28 · Waxing Gibbous 86% 🌔
Moonrise 4:05 PM · Moonset 5:10 AM · ⚠️ bright moon
🟢 **7:00 PM – 7:00 AM** · ☁️ 12% · 6.0 mi vis
### Thu Oct 29 · Full Moon 94% 🌕
Moonrise 4:31 PM · Moonset 6:20 AM · ⚠️ bright moon
🟢 **6:00 PM – data ends** · ☁️ 5% · 6.0 mi vis
-# Avg cloud cover: 🟢 <25% 🟡 <50% 🟠 <75% · Forecast via WeatherAPI
```

## How it works

1. **Fetch:** request an hourly forecast (3 days by default). Responses are cached on disk for an hour, keyed by location and request parameters, so repeated lookups don't spend API quota.
2. **Filter:** drop any hour that's still in the past or fails a threshold in [`BAD_HOUR_THRESHOLDS`](src/stargazing/brief.py): daytime, more than 75% cloud cover, or under 1 mile of visibility.
3. **Group:** merge consecutive good hours into windows. A window that crosses midnight stays listed under the night it started.
4. **Rate:** color each window by its average cloud cover, report its worst visibility, and warn when the moon is gibbous/full or more than 50% illuminated.
5. **Fit:** trim windows from the end if needed to stay under Discord's 2,000-character message limit, never leaving an empty day heading behind.

## Usage

Requires Python 3.10+ and a free [WeatherAPI key](https://www.weatherapi.com/signup.aspx).

```sh
git clone https://github.com/EZRocketSurgery/stargazing-forecast.git
cd stargazing-forecast
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env             # then put your key in .env
```

```sh
stargazing "Burlington, VT"
stargazing 05401 --days 2
stargazing "44.48,-73.21" --verbose
```

Or from Python:

```python
from stargazing import stargazing_brief, WeatherAPIError

print(stargazing_brief("Burlington, VT"))
```

### Configuration

| Variable | Required | Default |
| --- | --- | --- |
| `WEATHER_API_KEY` | yes | none |
| `WEATHER_API_URL` | no | `https://api.weatherapi.com/v1` |
| `STARGAZING_CACHE_DIR` | no | `stargazing/` in the system temp directory |

## Project layout

```
src/stargazing/
  weather.py    WeatherAPI client and ForecastDay model
  cache.py      one-hour on-disk response cache
  brief.py      filtering, windowing, and formatting
  __main__.py   command line interface
tests/          pytest suite with synthetic forecasts, no network needed
```

## Tests

```sh
pip install -e ".[dev]"
pytest
```

## Ideas for later

- Alerts when a good window is coming up
- Notifications for celestial events (meteor showers, planets, ISS passes)
- Use moonrise/moonset to flag only the hours the moon is actually up

## License

[MIT](LICENSE)
