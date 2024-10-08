import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_AZURE_API_KEY, CONF_AZURE_ENDPOINT
from .device_manager import setup_device
from .camera import setup_periodic_camera_check
from .store import HomeAIVisionStore

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeAIVision integration from a config entry."""
    _LOGGER.debug(f"[HomeAIVision] async_setup_entry called with entry.data: {entry.data}")

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Store integration configuration
    hass.data[DOMAIN][entry.entry_id] = {
        "azure_api_key": entry.data.get(CONF_AZURE_API_KEY),
        "azure_endpoint": entry.data.get(CONF_AZURE_ENDPOINT),
    }

    # Initialize HomeAIVisionStore and load devices
    store = HomeAIVisionStore(hass)
    await store.async_load()
    hass.data[DOMAIN]['store'] = store

    # Set up devices
    await async_setup_devices(hass, entry, store)

    # Load sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # Start periodic camera checks for each device
    devices = store.get_devices()
    for device_config in devices.values():
        hass.async_create_task(
            setup_periodic_camera_check(hass, entry, device_config.asdict())
        )

    return True

async def async_setup_devices(hass: HomeAssistant, entry: ConfigEntry, store: HomeAIVisionStore):
    """Set up devices (cameras) from the store."""
    devices = store.get_devices()
    for device_config in devices.values():
        await setup_device(hass, entry, device_config.asdict())

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug(f"[HomeAIVision] async_unload_entry called with entry.data: {entry.data}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
