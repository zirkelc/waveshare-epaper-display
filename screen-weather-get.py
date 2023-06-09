#!/usr/bin/python

import datetime
import sys
import os
import logging
from weather_providers import (
    climacell,
    openweathermap,
    metofficedatahub,
    metno,
    meteireann,
    accuweather,
    visualcrossing,
    weathergov,
    smhi,
)
from alert_providers import metofficerssfeed, weathergovalerts
from alert_providers import meteireann as meteireannalertprovider
from utility import get_formatted_time, update_svg, configure_logging, configure_locale
import textwrap
import html

# from dotenv import load_dotenv

# load_dotenv()
configure_locale()
configure_logging()


def format_weather_description(weather_description):
    if len(weather_description) < 20:
        return {1: weather_description, 2: ""}

    splits = textwrap.fill(
        weather_description, 20, break_long_words=False, max_lines=2, placeholder="..."
    ).split("\n")
    weather_dict = {1: splits[0]}
    weather_dict[2] = splits[1] if len(splits) > 1 else ""
    return weather_dict


def get_weather(location_lat, location_long, units):
    # gather relevant environment configs
    climacell_apikey = os.getenv("CLIMACELL_APIKEY")
    openweathermap_apikey = os.getenv("OPENWEATHERMAP_APIKEY")
    metoffice_clientid = os.getenv("METOFFICEDATAHUB_CLIENT_ID")
    metoffice_clientsecret = os.getenv("METOFFICEDATAHUB_CLIENT_SECRET")
    accuweather_apikey = os.getenv("ACCUWEATHER_APIKEY")
    accuweather_locationkey = os.getenv("ACCUWEATHER_LOCATIONKEY")
    metno_self_id = os.getenv("METNO_SELF_IDENTIFICATION")
    visualcrossing_apikey = os.getenv("VISUALCROSSING_APIKEY")
    use_met_eireann = os.getenv("WEATHER_MET_EIREANN")
    weathergov_self_id = os.getenv("WEATHERGOV_SELF_IDENTIFICATION")
    smhi_self_id = os.getenv("SMHI_SELF_IDENTIFICATION")

    if (
        not climacell_apikey
        and not openweathermap_apikey
        and not metoffice_clientid
        and not accuweather_apikey
        and not metno_self_id
        and not visualcrossing_apikey
        and not use_met_eireann
        and not weathergov_self_id
        and not smhi_self_id
    ):
        logging.error(
            "No weather provider has been configured (Climacell, OpenWeatherMap, Weather.gov, MetOffice, AccuWeather, Met.no, Met Eireann, VisualCrossing...)"
        )
        sys.exit(1)

    if visualcrossing_apikey:
        logging.info("Getting weather from Visual Crossing")
        weather_provider = visualcrossing.VisualCrossing(
            visualcrossing_apikey, location_lat, location_long, units
        )

    elif use_met_eireann:
        logging.info("Getting weather from Met Eireann")
        weather_provider = meteireann.MetEireann(location_lat, location_long, units)

    elif weathergov_self_id:
        logging.info("Getting weather from Weather.gov")
        weather_provider = weathergov.WeatherGov(
            weathergov_self_id, location_lat, location_long, units
        )

    elif metno_self_id:
        logging.info("Getting weather from Met.no")
        weather_provider = metno.MetNo(
            metno_self_id, location_lat, location_long, units
        )

    elif accuweather_apikey:
        logging.info("Getting weather from Accuweather")
        weather_provider = accuweather.AccuWeather(
            accuweather_apikey,
            location_lat,
            location_long,
            accuweather_locationkey,
            units,
        )

    elif metoffice_clientid:
        logging.info("Getting weather from Met Office Weather Datahub")
        weather_provider = metofficedatahub.MetOffice(
            metoffice_clientid,
            metoffice_clientsecret,
            location_lat,
            location_long,
            units,
        )

    elif openweathermap_apikey:
        logging.info("Getting weather from OpenWeatherMap")
        weather_provider = openweathermap.OpenWeatherMap(
            openweathermap_apikey, location_lat, location_long, units
        )

    elif climacell_apikey:
        logging.info("Getting weather from Climacell")
        weather_provider = climacell.Climacell(
            climacell_apikey, location_lat, location_long, units
        )

    elif smhi_self_id:
        logging.info("Getting weather from SMHI")
        weather_provider = smhi.SMHI(smhi_self_id, location_lat, location_long, units)

    weather = weather_provider.get_weather()
    logging.info("weather - {}".format(weather))
    return weather


def format_alert_description(alert_message):
    return html.escape(alert_message)


def get_alert_message(location_lat, location_long):
    alert_message = ""
    alert_metoffice_feed_url = os.getenv("ALERT_METOFFICE_FEED_URL")
    alert_weathergov_self_id = os.getenv("ALERT_WEATHERGOV_SELF_IDENTIFICATION")
    alert_meteireann_feed_url = os.getenv("ALERT_MET_EIREANN_FEED_URL")

    if alert_weathergov_self_id:
        logging.info("Getting weather alert from Weather.gov API")
        alert_provider = weathergovalerts.WeatherGovAlerts(
            location_lat, location_long, alert_weathergov_self_id
        )
        alert_message = alert_provider.get_alert()

    elif alert_metoffice_feed_url:
        logging.info("Getting weather alert from Met Office RSS Feed")
        alert_provider = metofficerssfeed.MetOfficeRssFeed(alert_metoffice_feed_url)
        alert_message = alert_provider.get_alert()

    elif alert_meteireann_feed_url:
        logging.info("Getting weather alert from Met Eireann")
        alert_provider = meteireannalertprovider.MetEireannAlertProvider(
            alert_meteireann_feed_url
        )
        alert_message = alert_provider.get_alert()

    logging.info("alert - {}".format(alert_message))
    return alert_message


def main():
    # template_name = os.getenv("SCREEN_LAYOUT", "1")
    location_lat = os.getenv("WEATHER_LATITUDE", "51.5077")
    location_long = os.getenv("WEATHER_LONGITUDE", "-0.1277")
    weather_format = os.getenv("WEATHER_FORMAT", "CELSIUS")

    if weather_format == "CELSIUS":
        units = "metric"
        degrees = "°C"
    else:
        units = "imperial"
        degrees = "°F"

    weather = get_weather(location_lat, location_long, units)

    if not weather:
        logging.error("Unable to fetch weather payload. SVG will not be updated.")
        return

    weather_dict = {}
    weather = list(weather) if type(weather) == dict else weather

    for i, w in enumerate(weather):
        logging.info(w)

        weather_temp = "{} / {} {}".format(
            str(round(w["temperatureMin"])), str(round(w["temperatureMax"])), degrees
        )
        weather_icon = w["icon"]
        weather_desc = format_weather_description(w["description"])

        weather_dict["WEATHER_TEMP_" + str(i)] = weather_temp
        weather_dict["WEATHER_ICON_" + str(i)] = weather_icon
        weather_dict["WEATHER_DESC_" + str(i)] = weather_desc[1]

    # alert_message = get_alert_message(location_lat, location_long)
    # alert_message = format_alert_description(alert_message)

    time_now = get_formatted_time(datetime.datetime.now())
    # time_now_font_size = "40px"

    # if len(time_now) > 6:
    #     time_now_font_size = str(100 - (len(time_now)-5) * 5) + "px"

    output_dict = {
        # "LOW_ONE": "{}{}".format(str(round(weather["temperatureMin"])), degrees),
        # "HIGH_ONE": "{}{}".format(str(round(weather["temperatureMax"])), degrees),
        # "ICON_ONE": weather["icon"],
        # "WEATHER_DESC_1": weather_desc[1],
        # "WEATHER_DESC_2": weather_desc[2],
        # "TIME_NOW_FONT_SIZE": time_now_font_size,
        "WEATHER_ICON_NOW": weather_dict["WEATHER_ICON_0"],
        "WEATHER_NOW": "{} {}".format(
            weather_dict["WEATHER_TEMP_0"], weather_dict["WEATHER_DESC_0"]
        ),
        "TIME_NOW": time_now,
        "HOUR_NOW": datetime.datetime.now().strftime("%H:%M"),
        "DAY_ONE": datetime.datetime.now().strftime("%d.%m.%Y"),
        "DAY_NAME": datetime.datetime.now().strftime("%A"),
        # "ALERT_MESSAGE_VISIBILITY": "visible" if alert_message else "hidden",
        # "ALERT_MESSAGE": alert_message,
    }
    output_dict.update(weather_dict)

    logging.info(output_dict)

    logging.info("Updating SVG")

    # template_svg_filename = f"screen-template.{template_name}.svg"
    # output_svg_filename = "screen-output-weather.svg"
    # update_svg(template_svg_filename, output_svg_filename, output_dict)
    output_svg_filename = "screen-output-weather.svg"
    update_svg(output_svg_filename, output_svg_filename, output_dict)


if __name__ == "__main__":
    main()
