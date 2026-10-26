"""Command line entry point: `stargazing "Burlington, VT"` or `python -m stargazing ...`."""
import argparse
import logging
import sys

from dotenv import load_dotenv

from .brief import stargazing_brief
from .weather import WeatherAPIError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stargazing",
        description="Show the upcoming hours that are good for stargazing at a location.",
    )
    parser.add_argument("location", help='City, zip/postcode, or "lat,lon" (anything WeatherAPI accepts)')
    parser.add_argument("-d", "--days", type=int, default=3, help="Days to forecast (default: 3)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log API and cache activity")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    load_dotenv()
    # The brief is full of emoji; don't let a legacy Windows console encoding crash on them
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        print(stargazing_brief(args.location, args.days), end="")
    except WeatherAPIError as e:
        print(f"Couldn't get a forecast for {args.location}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
