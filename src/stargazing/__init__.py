"""Find the best upcoming hours for stargazing at a location, using WeatherAPI forecasts."""
from .brief import stargazing_brief
from .weather import WeatherAPIError

__all__ = ["stargazing_brief", "WeatherAPIError"]
