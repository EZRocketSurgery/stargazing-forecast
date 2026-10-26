"""Thin client for WeatherAPI (https://www.weatherapi.com/) plus the forecast model."""
import logging
import os

import requests

logger = logging.getLogger(__name__)

# --- API Endpoints & json key mappings ---

DEFAULT_API_URL = "https://api.weatherapi.com/v1"

API_ENDPOINTS = {
    "alerts": "alerts.json",
    "astronomy": "astronomy.json",
    "current": "current.json",
    "forecast": "forecast.json",
    "future": "future.json",
    "history": "history.json",
    "ip lookup": "ip.json",
    "marine": "marine.json",
    "search": "search.json",
    "sports": "sports.json",
    "timezone": "timezone.json",
}

LOCATION_KEYS = {
    'country' : "Country",
    'lat' : "Latitude",
    'localtime_epoch' : "Localtime Epoch",
    'localtime' : "Localtime",
    'lon' : "Longitude",
    'name' : "Name",
    'region' : "Region",
    'tz_id' : "Time Zone ID",
}

CURRENT_KEYS = {
    'chance_of_rain' : "Chance of Rain",
    'chance_of_snow' : "Chance of Snow",
    'cloud' : "Cloud",
    'condition' : "Condition",
    'dewpoint_c' : "Dewpoint (C)",
    'dewpoint_f' : "Dewpoint (F)",
    'diff_rad' : "Diffuse Radiation",
    'dni' : "Direct Normal Irradiance",
    'feelslike_c' : "Feels Like (C)",
    'feelslike_f' : "Feels Like (F)",
    'gti' : "Global Tilted Irradiance",
    'gust_kph' : "Gust (KPH)",
    'gust_mph' : "Gust (MPH)",
    'heatindex_c' : "Heat Index (C)",
    'heatindex_f' : "Heat Index (F)",
    'humidity' : "Humidity",
    'is_day' : "Is Day",
    'last_updated' : "Last Updated",
    'last_updated_epoch' : "Last Updated Epoch",
    'precip_in' : "Precipitation (in)",
    'precip_mm' : "Precipitation (mm)",
    'pressure_in' : "Pressure (in)",
    'pressure_mb' : "Pressure (mb)",
    'short_rad' : "Shortwave Radiation",
    'temp_c' : "Temperature (C)",
    'temp_f' : "Temperature (F)",
    'uv' : "UV Index",
    'vis_km' : "Visibility (km)",
    'vis_miles' : "Visibility (miles)",
    'wetbulb_c' : "Wetbulb (C)",
    'wetbulb_f' : "Wetbulb (F)",
    'will_it_rain' : "Will it Rain",
    'will_it_snow' : "Will it Snow",
    'wind_degree' : "Wind Degree",
    'wind_dir' : "Wind Direction",
    'wind_kph' : "Wind (KPH)",
    'wind_mph' : "Wind (MPH)",
    'windchill_c' : "Windchill (C)",
    'windchill_f' : "Windchill (F)",
}

ASTRONOMY_KEYS = {
    'sunrise' : "Sunrise",
    'sunset' : "Sunset",
    'moonrise' : "Moonrise",
    'moonset' : "Moonset",
    'moon_phase' : "Moon Phase",
    'moon_illumination' : "Moon Illumination",
    'is_moon_up' : "Is Moon Up",
    'is_sun_up' : "Is Sun Up",
}

# --- Forecast models ---

class WeatherAPIError(Exception):
    """The weather API returned an error response."""

class ForecastDay:
    """A single day from the forecast endpoint.

    Args:
        forecast_day (dict): One entry of response["forecast"]["forecastday"].
    """
    def __init__(self, forecast_day: dict):
        astro = forecast_day.get("astro", {})
        self.date = forecast_day.get("date")
        self.date_epoch = forecast_day.get("date_epoch")
        self.day = forecast_day.get("day", {})
        self.hours = forecast_day.get("hour", [])

        self.sunrise = astro.get("sunrise")
        self.sunset = astro.get("sunset")
        self.moonrise = astro.get("moonrise", "")
        self.moonset = astro.get("moonset", "")
        self.moon_phase = astro.get("moon_phase", "")
        self.moon_illumination = astro.get("moon_illumination", 0)

    @classmethod
    def from_response(cls, response: dict) -> list["ForecastDay"]:
        """Build a ForecastDay for each day in a forecast API response."""
        return [cls(day) for day in response["forecast"]["forecastday"]]

def weather_api(endpoint : str, q: str, **params) -> requests.Response:
    """Fetch data from the weather API.

    Reads WEATHER_API_KEY (and optionally WEATHER_API_URL) from the environment.

    Args:
        endpoint (str): The API endpoint to query, a key of API_ENDPOINTS.
        q (str): The location query.
        **params: Additional query parameters for the API request.

    Returns:
        requests.Response: The response object from the API request.
    """
    logger.info("Weather API called with endpoint='%s' and query='%s'", endpoint, q)
    if endpoint not in API_ENDPOINTS:
        raise ValueError(f"Invalid endpoint: {endpoint}")
    base_url = os.getenv("WEATHER_API_URL") or DEFAULT_API_URL
    url = f"{base_url.rstrip('/')}/{API_ENDPOINTS[endpoint]}"
    params["q"] = q
    api_key = os.getenv("WEATHER_API_KEY")
    if api_key:
        params["key"] = api_key
    response = requests.get(url, params=params, timeout=10)
    logger.info("Weather API response received with status_code='%s'", response.status_code)
    return response
