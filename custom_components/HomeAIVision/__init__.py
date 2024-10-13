import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_AZURE_API_KEY, CONF_AZURE_ENDPOINT
from .camera import setup_periodic_camera_check
from .store import HomeAIVisionStore
from .actions import (
    ACTION_MANUAL_ANALYZE,
    ACTION_RESET_LOCAL_COUNTER,
    ACTION_RESET_GLOBAL_COUNTER,
    handle_manual_analyze,
    handle_reset_local_counter,
    handle_reset_global_counter
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeAIVision integration from a config entry."""
    _LOGGER.debug(f"[HomeAIVision] async_setup_entry called with entry.data: {entry.data}")

    try:   
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        # NOTE: Initialize HomeAIVisionStore
        store = HomeAIVisionStore(hass)
        await store.async_load()
        hass.data[DOMAIN]['store'] = store

        # NOTE: Keep Azure API Key and Endpoint in hass.data
        hass.data[DOMAIN]['azure_api_key'] = entry.data.get(CONF_AZURE_API_KEY)
        hass.data[DOMAIN]['azure_endpoint'] = entry.data.get(CONF_AZURE_ENDPOINT)

        # NOTE: Define internal functions defines the services
        async def service_manual_analyze(call: ServiceCall):
            await handle_manual_analyze(call, hass)

        async def service_reset_local_counter(call: ServiceCall):
            await handle_reset_local_counter(call, hass)

        async def service_reset_global_counter(call: ServiceCall):
            await handle_reset_global_counter(call, hass)

        # NOTE: Register services (actions)
        hass.services.async_register(
            DOMAIN,
            ACTION_MANUAL_ANALYZE,
            service_manual_analyze,
            schema=vol.Schema({vol.Required('device_id'): cv.string})
        )

        hass.services.async_register(
            DOMAIN,
            ACTION_RESET_LOCAL_COUNTER,
            service_reset_local_counter,
            schema=vol.Schema({vol.Required('device_id'): cv.string})
        )

        hass.services.async_register(
            DOMAIN,
            ACTION_RESET_GLOBAL_COUNTER,
            service_reset_global_counter,
            schema=vol.Schema({})
        )

        # NOTE: Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # NOTE: Start periodic camera checks for each device
        devices = store.get_devices()
        for device_config in devices.values():
            hass.async_create_task(
                setup_periodic_camera_check(hass, entry, device_config.asdict())
            )

        return True
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] async_setup_entry failed with exception: {e}")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"[HomeAIVision] async_unload_entry called with entry.data: {entry.data}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop('store', None)
    return unload_ok


async def async_remove_config_entry_device(hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry) -> bool:
    """Remove a config entry from a device."""
    _LOGGER.debug(f"[HomeAIVision] Removing device: {device_entry.id}")

    store: HomeAIVisionStore = hass.data[DOMAIN].get('store')
    if store is None:
        _LOGGER.error("Store not found in hass.data")
        return False

    # NOTE: Delete device from store
    await store.async_remove_device(device_entry.id)

    _LOGGER.debug(f"[HomeAIVision] Device {device_entry.id} removed successfully")
    return True
