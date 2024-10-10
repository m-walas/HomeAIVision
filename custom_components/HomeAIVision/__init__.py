import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, CONF_AZURE_API_KEY, CONF_AZURE_ENDPOINT
from .camera import setup_periodic_camera_check
from .store import HomeAIVisionStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeAIVision integration from a config entry."""
    _LOGGER.debug(f"[HomeAIVision] async_setup_entry called with entry.data: {entry.data}")

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # NOTE: Initialize HomeAIVisionStore and load devices
    store = HomeAIVisionStore(hass)
    await store.async_load()
    hass.data[DOMAIN]['store'] = store

    # NOTE: Register services
    from .services import (
        SERVICE_MANUAL_ANALYZE,
        SERVICE_RESET_LOCAL_COUNTER,
        SERVICE_RESET_GLOBAL_COUNTER,
        handle_manual_analyze,
        handle_reset_local_counter,
        handle_reset_global_counter,
    )
    
    import voluptuous as vol

    hass.services.async_register(
        DOMAIN,
        SERVICE_MANUAL_ANALYZE,
        handle_manual_analyze,
        vol.Schema({
            vol.Required('device_id'): vol.All(str, vol.Length(min=1)),
        })
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_LOCAL_COUNTER,
        handle_reset_local_counter,
        vol.Schema({
            vol.Required('device_id'): vol.All(str, vol.Length(min=1)),
        })
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_GLOBAL_COUNTER,
        handle_reset_global_counter,
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
