import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def setup_device(hass: HomeAssistant, entry: ConfigEntry, device_config: dict):
    """
    Store device configuration for later use in sensor platform.
    """
    _LOGGER.debug(f"[HomeAIVision] Setting up device with config: {device_config}")

    devices = hass.data.setdefault(DOMAIN, {}).setdefault('devices', {})
    devices[device_config['id']] = device_config

    _LOGGER.debug(f"[HomeAIVision] Device stored: {device_config['name']}")
