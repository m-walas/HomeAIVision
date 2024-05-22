import os
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START

from .const import DOMAIN
from .camera import setup_periodic_camera_check
from .mod_view import async_setup_view
from .api import async_register_http_endpoints

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async def start_camera_analysis(event):
        await setup_periodic_camera_check(hass, entry)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_camera_analysis)

    await async_setup_view(hass)
    await async_register_http_endpoints(hass)

    return True
