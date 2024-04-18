from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START

from .const import DOMAIN, CONF_TIME_BETWEEN_REQUESTS
from .camera import setup_periodic_camera_check

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async def start_camera_analysis(event):
        await setup_periodic_camera_check(hass, entry)
    
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_camera_analysis)

    return True
