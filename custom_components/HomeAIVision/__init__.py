import logging
import voluptuous as vol  # type: ignore

from homeassistant.core import HomeAssistant, ServiceCall  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.helpers.device_registry import DeviceEntry  # type: ignore
from homeassistant.helpers import config_validation as cv  # type: ignore

from .const import DOMAIN, CONF_AZURE_API_KEY, CONF_AZURE_ENDPOINT
from .camera_processing import setup_periodic_camera_check
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

# INFO: Define the platforms supported by this integration
PLATFORMS = ["sensor", "number", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up HomeAIVision integration from a config entry.

    This function initializes the integration by setting up the store,
    registering services, forwarding setup to platforms, and starting
    periodic camera checks for each device.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for the integration.

    Returns:
        bool: True if setup was successful, False otherwise.
    """
    _LOGGER.debug(f"[HomeAIVision] async_setup_entry called with entry.data: {entry.data}")

    try:
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        # NOTE: Initialize HomeAIVisionStore to manage devices and counters
        store = HomeAIVisionStore(hass)
        await store.async_load()
        hass.data[DOMAIN]['store'] = store

        # NOTE: Store Azure API Key and Endpoint in hass.data for easy access
        hass.data[DOMAIN]['azure_api_key'] = entry.data.get(CONF_AZURE_API_KEY)
        hass.data[DOMAIN]['azure_endpoint'] = entry.data.get(CONF_AZURE_ENDPOINT)

        # NOTE: Set the global integration language from the config entry
        language = entry.data.get('global', {}).get('language', 'en')
        await store.async_set_language(language)

        # NOTE: Define internal service handler functions
        async def service_manual_analyze(call: ServiceCall):
            """
            Handle the manual analyze service call.

            Args:
                call (ServiceCall): The service call object containing data.
            """
            await handle_manual_analyze(call, hass)

        async def service_reset_local_counter(call: ServiceCall):
            """
            Handle the reset local counter service call.

            Args:
                call (ServiceCall): The service call object containing data.
            """
            await handle_reset_local_counter(call, hass)

        async def service_reset_global_counter(call: ServiceCall):
            """
            Handle the reset global counter service call.

            Args:
                call (ServiceCall): The service call object containing data.
            """
            await handle_reset_global_counter(call, hass)

        # NOTE: Register services (actions) with Home Assistant
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

        # NOTE: Forward setup to the specified platforms (sensor, number, select)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # NOTE: Start periodic camera checks for each configured device
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
    """
    Unload a config entry.

    This function handles the unloading of the integration by unloading
    platforms and cleaning up stored data.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry to unload.

    Returns:
        bool: True if unloading was successful, False otherwise.
    """
    _LOGGER.debug(f"[HomeAIVision] async_unload_entry called with entry.data: {entry.data}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop('store', None)
    return unload_ok


# NOTE: By adding the following function, we give the user the ability to permanently remove a device from the integration using the UI button.
# NOTE: Not recommended, removing devices are implemented in options menu from config_flow.  
# async def async_remove_config_entry_device(
#     hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
# ) -> bool:
#     """
#     Remove a config entry from a device.

#     This function handles the removal of a device from the integration,
#     including cleanup from the store and device/entity registry.

#     Args:
#         hass (HomeAssistant): The Home Assistant instance.
#         config_entry (ConfigEntry): The configuration entry.
#         device_entry (DeviceEntry): The device entry to remove.

#     Returns:
#         bool: True if the device was successfully removed, False otherwise.
#     """
#     _LOGGER.debug(f"[HomeAIVision] Removing device: {device_entry.id}")

#     store: HomeAIVisionStore = hass.data[DOMAIN].get('store')
#     if store is None:
#         _LOGGER.error("Store not found in hass.data")
#         return False

#     # NOTE: Delete device from store
#     await store.async_remove_device(device_entry.id)

#     _LOGGER.debug(f"[HomeAIVision] Device {device_entry.id} removed successfully")
#     return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug(f"[HomeAIVision] async_unload_entry called with entry.data: {entry.data}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop('store', None)
    return unload_ok
