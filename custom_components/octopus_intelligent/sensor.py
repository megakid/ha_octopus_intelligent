"""Support for UK train data provided by api.rtt.io."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import aiohttp
import pytz

import voluptuous as vol
from typing import cast

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import TIME_MINUTES, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOFFSET = timedelta(minutes=0)

ATTR_ATCOCODE = "atcocode"
ATTR_LOCALITY = "locality"
ATTR_REQUEST_TIME = "request_time"
ATTR_JOURNEY_START = "journey_start"
ATTR_JOURNEY_END = "journey_end"
ATTR_NEXT_TRAINS = "next_trains"

CONF_API_USERNAME = "username"
CONF_API_PASSWORD = "password"
CONF_QUERIES = "queries"
CONF_AUTOADJUSTSCANS = "auto_adjust_scans"

CONF_START = "origin"
CONF_END = "destination"
CONF_JOURNEYDATA = "journey_data_for_next_X_trains"
CONF_SENSORNAME = "sensor_name"
CONF_TIMEOFFSET = "time_offset"
CONF_STOPS_OF_INTEREST = "stops_of_interest"

TIMEZONE = pytz.timezone('Europe/London')
STRFFORMAT = "%d-%m-%Y %H:%M"

_QUERY_SCHEME = vol.Schema(
    {
        vol.Optional(CONF_SENSORNAME): cv.string,
        vol.Required(CONF_START): cv.string,
        vol.Required(CONF_END): cv.string,
        vol.Optional(CONF_JOURNEYDATA, default=0): cv.positive_int,
        vol.Optional(CONF_TIMEOFFSET, default=DEFAULT_TIMEOFFSET): 
            vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_STOPS_OF_INTEREST): [cv.string],
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_AUTOADJUSTSCANS, default=False): cv.boolean,
        vol.Required(CONF_API_USERNAME): cv.string,
        vol.Required(CONF_API_PASSWORD): cv.string,
        vol.Required(CONF_QUERIES): [_QUERY_SCHEME],
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Get the realtime_train sensor."""
    sensors = { }
    interval = config[CONF_SCAN_INTERVAL]
    autoadjustscans = config[CONF_AUTOADJUSTSCANS]
    username = config[CONF_API_USERNAME]
    password = config[CONF_API_PASSWORD]
    queries = config[CONF_QUERIES]
    

    client = async_get_clientsession(hass)

    for query in queries:
        sensor_name = query.get(CONF_SENSORNAME, None)
        journey_start = query.get(CONF_START)
        journey_end = query.get(CONF_END)
        journey_data_for_next_X_trains = query.get(CONF_JOURNEYDATA)
        timeoffset = query.get(CONF_TIMEOFFSET)
        stops_of_interest = query.get(CONF_STOPS_OF_INTEREST, [])
        sensor = RealtimeTrainLiveTrainTimeSensor(
                sensor_name,
                username,
                password,
                journey_start,
                journey_end,
                journey_data_for_next_X_trains,
                timeoffset,
                autoadjustscans,
                stops_of_interest,
                interval,
                client
            )
        sensors[sensor.name] = sensor

    async_add_entities(sensors.values(), True)


class RealtimeTrainLiveTrainTimeSensor(SensorEntity):
    """
    Sensor that reads the rtt API.

    api.rtt.io provides free comprehensive train data for UK trains
    across the UK via simple JSON API. Subclasses of this
    base class can be used to access specific types of information.
    """



    TRANSPORT_API_URL_BASE = "https://api.rtt.io/api/v1/json/"
    _attr_icon = "mdi:train"
    _attr_native_unit_of_measurement = TIME_MINUTES

    def __init__(self, sensor_name, username, password, journey_start, journey_end,
                journey_data_for_next_X_trains, timeoffset, autoadjustscans, stops_of_interest, interval, client):
        """Construct a live train time sensor."""

        default_sensor_name = (
            f"Next train from {journey_start} to {journey_end} ({timeoffset})" if (timeoffset.total_seconds() > 0) 
            else f"Next train from {journey_start} to {journey_end}")

        self._journey_start = journey_start
        self._journey_end = journey_end
        self._journey_data_for_next_X_trains = journey_data_for_next_X_trains
        self._next_trains = []
        self._data = {}
        self._username = username
        self._password = password
        self._timeoffset = timeoffset
        self._autoadjustscans = autoadjustscans
        self._stops_of_interest = stops_of_interest
        self._interval = interval
        self._client = client

        self._name = default_sensor_name if sensor_name is None else sensor_name
        self._state = None

        self.async_update = self._async_update

    async def _async_update(self):
        """Get the latest live departure data for the specified stop."""
        await self._getdepartures_api_request()
        self._next_trains = []
        departureCount = 0
        now = cast(datetime, dt_util.now()).astimezone(TIMEZONE)

        nextDepartureEstimatedTs : (datetime | None) = None

        departures = [] if self._data == {} or self._data["services"] == None else self._data["services"]

        for departure in departures:
            if not departure["isPassenger"] :
                continue
            
            departuredate = TIMEZONE.localize(datetime.fromisoformat(departure["runDate"]))
            
            scheduled = _to_colonseparatedtime(departure["locationDetail"]["gbttBookedDeparture"])
            scheduledTs = _timestamp(scheduled, departuredate)
            
            if _delta_secs(scheduledTs, now) < self._timeoffset.total_seconds():
                continue
            
            estimated = _to_colonseparatedtime(departure["locationDetail"]["realtimeDeparture"])
            estimatedTs = _timestamp(estimated, departuredate)
            
            if nextDepartureEstimatedTs is None:
                nextDepartureEstimatedTs = estimatedTs
            else:
                nextDepartureEstimatedTs = min(nextDepartureEstimatedTs, estimatedTs)

            departureCount += 1
            
            train = {
                    "origin_name": departure["locationDetail"]["origin"][0]["description"],
                    "destination_name": departure["locationDetail"]["destination"][0]["description"],
                    #"service_date": departure["runDate"],
                    "service_uid": departure["serviceUid"],
                    "scheduled": scheduledTs.strftime(STRFFORMAT),
                    "estimated": estimatedTs.strftime(STRFFORMAT),
                    "minutes": _delta_secs(estimatedTs, now) // 60,
                    "platform": departure["locationDetail"].get("platform", None),
                    "operator_name": departure["atocName"],
                }
            if departureCount <= self._journey_data_for_next_X_trains:
                await self._add_journey_data(train, scheduledTs, estimatedTs)
            self._next_trains.append(train)

        if nextDepartureEstimatedTs is None:
            self._state = "No Departures"
        else:
            self._state = _delta_secs(nextDepartureEstimatedTs, now) // 60
        
        if self._autoadjustscans:
            if nextDepartureEstimatedTs is None:
                self.async_update = Throttle(timedelta(minutes=30))(self._async_update)
            else:
                self.async_update = self._async_update


    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    async def _getdepartures_api_request(self):
        """Perform an API request."""
        depsUrl = self.TRANSPORT_API_URL_BASE + f"search/{self._journey_start}/to/{self._journey_end}"
        async with self._client.get(depsUrl, auth=aiohttp.BasicAuth(login=self._username, password=self._password, encoding='utf-8')) as response:
            if response.status == 200:
                self._data = await response.json()
            elif response.status == 403:
                self._state = "Credentials invalid"
            else:
                _LOGGER.warning("Invalid response from API")

    async def _add_journey_data(self, train, scheduled_departure, estimated_departure):
        """Perform an API request."""
        trainUrl = self.TRANSPORT_API_URL_BASE + f"service/{train['service_uid']}/{scheduled_departure.strftime('%Y/%m/%d')}"
        async with self._client.get(trainUrl, auth=aiohttp.BasicAuth(login=self._username, password=self._password, encoding='utf-8')) as response:
            if response.status == 200:
                data = await response.json()
                stopsOfInterest = []
                stopCount = -1 # origin counts as first stop in the returned json
                found = False
                for stop in data['locations']:
                    if stop['crs'] == self._journey_end:
                        scheduled_arrival = _timestamp(_to_colonseparatedtime(stop['gbttBookedArrival']), scheduled_departure)
                        estimated_arrival = _timestamp(_to_colonseparatedtime(stop['realtimeArrival']), scheduled_departure)
                        newtrain = {
                            "stops_of_interest": stopsOfInterest,
                            "scheduled_arrival": scheduled_arrival.strftime(STRFFORMAT),
                            "estimate_arrival": estimated_arrival.strftime(STRFFORMAT),
                            "journey_time_mins": _delta_secs(estimated_arrival, estimated_departure) // 60,
                            "stops": stopCount
                        }
                        train.update(newtrain)
                        found = True
                        break
                    elif stop['crs'] in self._stops_of_interest and stop['isPublicCall']:
                        scheduled_stop = _timestamp(_to_colonseparatedtime(stop['gbttBookedArrival']), scheduled_departure)
                        estimated_stop = _timestamp(_to_colonseparatedtime(stop['realtimeArrival']), scheduled_departure)
                        stopsOfInterest.append(
                            {
                                "stop": stop['crs'],
                                "name": stop['description'],
                                "scheduled_stop": scheduled_stop.strftime(STRFFORMAT),
                                "estimate_stop": estimated_stop.strftime(STRFFORMAT),
                                "journey_time_mins": _delta_secs(estimated_stop, estimated_departure) // 60,
                                "stops": stopCount
                            }
                        )
                    stopCount += 1
                if not found:
                    _LOGGER.warning(f"Could not find {self._journey_end} in stops for service {train['service_uid']}.")    
            else:
                _LOGGER.warning(f"Could not populate arrival times: Invalid response from API (HTTP code {response.status})")

    @property
    def extra_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}
        if self._data is not None:
            attrs[ATTR_JOURNEY_START] = self._journey_start
            attrs[ATTR_JOURNEY_END] = self._journey_end
            if self._next_trains:
                attrs[ATTR_NEXT_TRAINS] = self._next_trains
            return attrs

def _to_colonseparatedtime(hhmm_time_str : str) -> str:
    return hhmm_time_str[:2] + ":" + hhmm_time_str[2:]

def _timestamp(hhmm_time_str : str, date : datetime=None) -> datetime:
    now = cast(datetime, dt_util.now()).astimezone(TIMEZONE) if date is None else date
    hhmm_time_a = datetime.strptime(hhmm_time_str, "%H:%M")
    hhmm_datetime = now.replace(hour=hhmm_time_a.hour, minute=hhmm_time_a.minute, second=0, microsecond=0)
    if hhmm_datetime < now:
        hhmm_datetime += timedelta(days=1)
    return hhmm_datetime

def _delta_secs(hhmm_datetime_a : datetime, hhmm_datetime_b : datetime) -> float:
    """Calculate time delta in minutes to a time in hh:mm format."""
    return (hhmm_datetime_a - hhmm_datetime_b).total_seconds()

