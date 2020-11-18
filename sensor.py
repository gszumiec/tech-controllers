"""Platform for sensor integration."""
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union
import logging
import json
from typing import List, Optional
from homeassistant.const import (
    TEMP_CELSIUS,
    SIGNAL_STRENGTH_DECIBELS,
    PERCENTAGE
)
from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from homeassistant.components import sensor

_LOGGER = logging.getLogger(__name__)

@dataclass
class BlockAttributeDescription:
    """Class to describe a sensor."""

    name: str
    # Callable = lambda attr_info: unit
    icon: Optional[str] = None
    unit: Union[None, str, Callable[[dict], str]] = None
    value: Callable[[Any], Any] = lambda val: val
    device_class: Optional[str] = None
    default_enabled: bool = True
    available: Optional[bool] = None

SENSORS = {
    ("device", "deviceTemp"): BlockAttributeDescription(
        name="Device Temperature",
        unit=TEMP_CELSIUS,
        value=lambda value: round(value, 1),
        device_class=sensor.DEVICE_CLASS_TEMPERATURE,
        default_enabled=False,
    )
}

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    # add_entities([RemoteSensor()])

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up entry."""
    try:
        _LOGGER.info("Setting up entry for sensors, module udid: " + config_entry.data["udid"])
        api = hass.data[DOMAIN][config_entry.entry_id]
        zones = await api.get_module_zones(config_entry.data["udid"])
        tiles = await api.get_module_tiles(config_entry.data["udid"])

        _LOGGER.info("Tiles %s", tiles)
        [
            _LOGGER.info("Tile.id %d", tiles[tile])
            for tile in tiles
        ]

        async_add_entities(
            [
                TileTemperatureSensor(
                    tiles[tile],
                    api,
                    config_entry,
                )
                for tile in tiles
            ],
            True,
        )

        async_add_entities(
            [
                TileBatteryLevelSensor(
                    tiles[tile],
                    api,
                    config_entry,
                )
                for tile in tiles
            ],
            True,
        )

        async_add_entities(
            [
                TileSignalStrengthSensor(
                    tiles[tile],
                    api,
                    config_entry,
                )
                for tile in tiles
            ],
            True,
        )

        async_add_entities(
            [
                ZoneTemperatureSensor(
                    zones[zone],
                    api,
                    config_entry,
                )
                for zone in zones
            ],
            True,
        )

    except Exception as error:
        _LOGGER.exception('Failed to setup entry sensor, %s' %error)
        return False

class ZoneSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, device, api, config_entry):
        """Initialize the sensor."""
        _LOGGER.debug("Init ZoneSensor...")
        self._config_entry = config_entry
        self._api = api
        _LOGGER.debug('device["zone"]["id"] = %s', device["zone"]["id"])
        self._id = device["zone"]["id"]
        self._name = device["description"]["name"]
        self._target_temperature = device["zone"]["setTemperature"] / 10
        self._temperature = device["zone"]["currentTemperature"] / 10
        

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (self._config_entry.data["udid"], self.unique_id)
            },
            "name": self.name,
            "manufacturer": "Tech",
            "model": self._config_entry.data["type"],
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._temperature

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    async def async_update(self):
        device = await self._api.get_zone(self._config_entry.data["udid"], self._id)
        self._temperature = device["zone"]["setTemperature"] / 10


class ZoneTemperatureSensor(ZoneSensor):
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + " Temperature"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._temperature



class TileSensor(Entity):
    """Representation of a TileSensor."""

    def __init__(self, device, api, config_entry):
        """Initialize the tile sensor."""
        _LOGGER.debug("Init TileSensor...")
        self._config_entry = config_entry
        self._api = api
        _LOGGER.debug('Sensor device["id"] = %s', device)
        self._id = device["id"]
        self._name = device["params"]["description"]
        self._batteryLevel = device["params"]["batteryLevel"]
        self._temperature = device["params"]["value"] / 10
        self._signalStrength = device["params"]["signalStrength"]
        self._workingStatus = device["params"]["workingStatus"]
        self._state = device["params"]["workingStatus"]

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (self._config_entry.data["udid"], self._id)
            },
            "name": self._name,
            "manufacturer": "Tech",
            "model": self._config_entry.data["type"],
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id * 10

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._temperature

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    async def async_update(self):
        device = await self._api.get_tile(self._config_entry.data["udid"], self._id)
        self._temperature = device["params"]["value"] / 10

class TileTemperatureSensor(TileSensor):

    @property 
    def name(self):
        return self._name

    @property
    def state(self):
        return self._temperature 

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id * 10

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return sensor.DEVICE_CLASS_TEMPERATURE

class TileBatteryLevelSensor(TileSensor):

    @property 
    def name(self):
        return self._name + " Battery Level"

    @property
    def state(self):
        return self._batteryLevel 
    
    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id * 10 + 1

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return sensor.DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        return PERCENTAGE

class TileSignalStrengthSensor(TileSensor):

    @property 
    def name(self):
        return self._name + " Signal strenght"

    @property
    def state(self):
        return self._signalStrength 

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id * 10 + 2

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return sensor.DEVICE_CLASS_SIGNAL_STRENGTH        

    @property
    def unit_of_measurement(self):
        return SIGNAL_STRENGTH_DECIBELS