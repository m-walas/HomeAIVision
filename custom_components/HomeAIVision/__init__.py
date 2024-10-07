import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_AZURE_API_KEY, CONF_AZURE_ENDPOINT
from .device_manager import setup_device
from .camera import setup_periodic_camera_check

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeAIVision integration from a config entry."""
    _LOGGER.debug(f"[HomeAIVision] async_setup_entry called with entry: {entry.data}")
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Store integration configuration
    hass.data[DOMAIN][entry.entry_id] = {
        "azure_api_key": entry.data.get(CONF_AZURE_API_KEY),
        "azure_endpoint": entry.data.get(CONF_AZURE_ENDPOINT),
    }

    # Set up devices
    await async_setup_devices(hass, entry)

    # Load sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    # Start periodic camera checks for each device
    devices = entry.data.get("devices", {})
    for device_config in devices.values():
        hass.async_create_task(
            setup_periodic_camera_check(hass, entry, device_config)
        )

    return True


async def async_setup_devices(hass: HomeAssistant, entry: ConfigEntry):
    """Set up devices (cameras) defined under the entry."""
    devices = entry.data.get("devices", {})
    for device_config in devices.values():
        await setup_device(hass, entry, device_config)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor"]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
