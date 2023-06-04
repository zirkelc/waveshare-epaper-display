import codecs
import logging
import os
import time
from http.client import HTTPConnection
import requests
import datetime
import pytz
import json
import xml.etree.ElementTree as ET
from astral import LocationInfo
from astral.sun import sun
import humanize
import locale
from babel.dates import format_time


def configure_locale():
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        logging.debug("Could not set locale")


def configure_logging():
    """
    Sets up logging with a specific logging format.
    Call this at the beginning of a script.
    Then using logging methods as normal
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
    log_dateformat = "%Y-%m-%d:%H:%M:%S"
    logging.basicConfig(level=log_level, format=log_format, datefmt=log_dateformat)
    logger = logging.getLogger()
    logger.setLevel(level=log_level)

    # Adds debug logging to python requests
    # https://stackoverflow.com/a/24588289/974369
    HTTPConnection.debuglevel = 1 if log_level == "DEBUG" else 0
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(level=log_level)
    requests_log.propagate = True

    formatter = logging.Formatter(fmt=log_format, datefmt=log_dateformat)
    handler = logger.handlers[0]
    handler.setFormatter(formatter)


# utilize a template svg as a base for output of values
def update_svg(template_svg_filename, output_svg_filename, output_dict):
    """
    Update the `template_svg_filename` SVG.
    Replaces keys with values from `output_dict`
    Writes the output to `output_svg_filename`
    """
    # replace tags with values in SVG
    output = codecs.open(template_svg_filename, "r", encoding="utf-8").read()

    for output_key in output_dict:
        logging.debug(
            "update_svg() - {} -> {}".format(output_key, output_dict[output_key])
        )
        output = output.replace(output_key, output_dict[output_key])

    logging.debug("update_svg() - Write to SVG {}".format(output_svg_filename))

    codecs.open(output_svg_filename, "w", encoding="utf-8").write(output)


def is_stale(filepath, ttl):
    """
    Checks if the specified `filepath` is older than the `ttl` in seconds
    Returns true if the file doesn't exist.
    """

    verdict = True
    if os.path.isfile(filepath):
        verdict = time.time() - os.path.getmtime(filepath) > ttl

    logging.debug("is_stale({}) - {}".format(filepath, str(verdict)))

    return verdict


def get_json_from_url(url, headers, cache_file_name, ttl):
    """
    Perform an HTTP GET for a `url` with optional `headers`.
    Caches the response in `cache_file_name` for `ttl` seconds.
    Returns the response as JSON
    """
    response_json = False

    if is_stale(cache_file_name, ttl):
        logging.info("Cache file is stale. Fetching from source.")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response_data = response.text
            response_json = json.loads(response_data)
            with open(cache_file_name, "w") as text_file:
                json.dump(response_json, text_file, indent=4)
        except Exception as error:
            logging.error(error)
            logging.error(response.text)
            logging.error(response.headers)
            raise
    else:
        logging.info("Found in cache.")
        with open(cache_file_name, "r") as file:
            return json.loads(file.read())
    return response_json


def get_xml_from_url(url, headers, cache_file_name, ttl):
    """
    Perform an HTTP GET for a `url` with optional `headers`.
    Caches the response in `cache_file_name` for `ttl` seconds.
    Returns the response as an XML ElementTree object
    """
    logging.info(url)

    if is_stale(cache_file_name, ttl):
        logging.info("Cache file is stale. Fetching from source.")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response_data = response.text

            with open(cache_file_name, "w") as text_file:
                text_file.write(response_data)
        except Exception as error:
            logging.error(error)
            logging.error(response.text)
            logging.error(response.headers)
            raise
    else:
        logging.info("Found in cache.")
        with open(cache_file_name, "r") as file:
            response_data = file.read()
    response_xml = ET.fromstring(response_data)
    return response_xml


def get_formatted_time(dt):
    try:
        # formatted_time = format_time(dt, format='short', locale=locale.getlocale()[0])
        formatted_time = format_time(dt, format="short", locale="de_DE")
    except Exception:
        logging.debug("Locale not found for Babel library.")
        formatted_time = dt.strftime("%-I:%M %p")
    return formatted_time


def get_formatted_date(dt, include_time=True):
    # today = datetime.datetime.today()
    # yesterday = today - datetime.timedelta(days=1)
    # tomorrow = today + datetime.timedelta(days=1)
    # next_week = today + datetime.timedelta(days=7)
    formatter_day = "%a %b %-d"

    # Display the time in the locale format, if possible
    if include_time:
        formatted_time = get_formatted_time(dt)
    else:
        formatted_time = " "

    try:
        short_locale = locale.getlocale()[0]  # en_GB
        short_locale = short_locale.split("_")[0]  # en
        if not short_locale == "en":
            humanize.activate(short_locale)
        # has_locale = True
    except Exception:
        logging.debug("Locale not found for humanize")
        # has_locale = False

    # if has_locale and (
    #     dt.date() == today.date()
    #     or dt.date() == tomorrow.date()
    #     or dt.date() == yesterday.date()
    # ):
    #     # Show today/tomorrow/yesterday if available
    #     formatter_day = humanize.naturalday(dt.date(), "%A").title()
    # elif dt.date() < next_week.date():

    # Just show the day name if it's in the next few days
    formatter_day = "%A"
    return dt.strftime(formatter_day + " " + formatted_time)


def get_sunset_time():
    """
    Return the time at which darkness begins, aka 'tonight'
    """
    location_lat = os.getenv("WEATHER_LATITUDE", "51.5077")
    location_long = os.getenv("WEATHER_LONGITUDE", "-0.1277")
    dt = datetime.datetime.now(pytz.utc)
    city = LocationInfo(location_lat, location_long)
    s = sun(city.observer, date=dt)
    return s["sunset"]
