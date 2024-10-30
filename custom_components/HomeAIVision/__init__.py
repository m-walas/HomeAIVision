import logging
import asyncio
import voluptuous as vol  # type: ignore

from homeassistant.core import HomeAssistant, ServiceCall, callback, CoreState  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.helpers import config_validation as cv  # type: ignore
from homeassistant.const import EVENT_HOMEASSISTANT_START  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore

from .const import DOMAIN, CONF_AZURE_API_KEY, CONF_AZURE_ENDPOINT
from .camera_processing import periodic_check
from .store import HomeAIVisionStore, DEVICE_ADDED_SIGNAL, DEVICE_REMOVED_SIGNAL
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


async def log_running_tasks_service(call: ServiceCall, hass: HomeAssistant):
    """
    Service to log all currently running tasks.

    Args:
        call (ServiceCall): The service call object.
        hass (HomeAssistant): The Home Assistant instance.
    """
    tasks = asyncio.all_tasks(loop=hass.loop)
    _LOGGER.debug(f"[HomeAIVision] Running tasks: {tasks}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up HomeAIVision integration from a config entry.

    This function initializes the integration by setting up the store,
    registering services, forwarding setup to platforms, and scheduling
    periodic camera checks to start after HA has fully started.

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

        # NOTE: Initialize a dictionary to store camera tasks and stop events
        if 'camera_tasks' not in hass.data[DOMAIN]:
            hass.data[DOMAIN]['camera_tasks'] = {}

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

        # NOTE: Register the log_running_tasks_service
        hass.services.async_register(
            DOMAIN,
            'log_tasks',
            lambda call: log_running_tasks_service(call, hass),
            schema=vol.Schema({})
        )

        # NOTE: Forward setup to the specified platforms (sensor, number, select)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # NOTE: Define a callback to start periodic checks
        @callback
        def start_periodic_checks(event=None):
            """
            Start periodic checks for all devices.
            """
            _LOGGER.debug("[HomeAIVision] Starting periodic checks for all devices.")
            devices = store.get_devices()
            for device_config in devices.values():
                if device_config.id not in hass.data[DOMAIN]['camera_tasks']:
                    stop_event = asyncio.Event()
                    task = hass.async_create_task(
                        periodic_check(hass, entry, device_config.asdict(), stop_event)
                    )
                    hass.data[DOMAIN]['camera_tasks'][device_config.id] = (task, stop_event)
                    _LOGGER.debug(f"[HomeAIVision] Camera_tasks: {hass.data[DOMAIN]['camera_tasks']}")

        # NOTE: Start periodic checks immediately if HA is already running
        if hass.state == CoreState.running:
            _LOGGER.debug("[HomeAIVision] HA is already running, starting periodic checks.")
            start_periodic_checks()
            # NOTE: Log all running tasks
            # hass.async_create_task(log_running_tasks_service({}, hass))
        else:
            # NOTE: Register the callback to be called once HA has started
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_periodic_checks)

        # NOTE: Define handlers for device added and removed signals
        @callback
        def handle_device_added(device):
            """
            Handle the addition of a new device.

            Args:
                device (dict): The device data dictionary.
            """
            device_id = device['id']
            if device_id not in hass.data[DOMAIN]['camera_tasks']:
                _LOGGER.debug(f"[HomeAIVision] Adding new device {device_id}.")
                stop_event = asyncio.Event()
                task = hass.async_create_task(
                    periodic_check(hass, entry, device, stop_event)
                )
                hass.data[DOMAIN]['camera_tasks'][device_id] = (task, stop_event)
                _LOGGER.debug(f"[HomeAIVision] Started periodic_check for device {device_id}")

        @callback
        def handle_device_removed(device):
            """
            Handle the removal of a device.

            Args:
                device (dict): The device data dictionary.
            """
            device_id = device['id']
            task_stop_event = hass.data[DOMAIN]['camera_tasks'].pop(device_id, (None, None))
            task, stop_event = task_stop_event
            if task and stop_event:
                stop_event.set()
                task.cancel()
                _LOGGER.debug(f"[HomeAIVision] Signaled stop for periodic_check of device {device_id} for entry {entry.entry_id}")

        # NOTE: Connect the signal handlers
        device_added_listener = async_dispatcher_connect(hass, DEVICE_ADDED_SIGNAL, handle_device_added)
        device_removed_listener = async_dispatcher_connect(hass, DEVICE_REMOVED_SIGNAL, handle_device_removed)
        hass.data[DOMAIN]['device_added_listener'] = device_added_listener
        hass.data[DOMAIN]['device_removed_listener'] = device_removed_listener

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
        _LOGGER.debug("[HomeAIVision] Unloading platforms successful.")

        camera_tasks = hass.data[DOMAIN].pop('camera_tasks', {})
        for device_id, (task, stop_event) in camera_tasks.items():
            _LOGGER.debug(f"[HomeAIVision] Signaling stop for periodic_check of device {device_id} for entry {entry.entry_id}")
            stop_event.set()
            task.cancel()

        # NOTE: Wait for all camera tasks to finish cancelling
        try:
            if camera_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*[t for t, _ in camera_tasks.values()], return_exceptions=True), 
                    timeout=10
                )
                _LOGGER.debug("[HomeAIVision] All camera tasks successfully cancelled.")
        except asyncio.TimeoutError:
            _LOGGER.warning("[HomeAIVision] Some camera tasks did not finish cancelling in time.")

        # NOTE: Disconnect dispatcher listeners if they exist
        device_added_listener = hass.data[DOMAIN].pop('device_added_listener', None)
        device_removed_listener = hass.data[DOMAIN].pop('device_removed_listener', None)
        if device_added_listener:
            device_added_listener()
            _LOGGER.debug("[HomeAIVision] Disconnected device_added_listener.")
        if device_removed_listener:
            device_removed_listener()
            _LOGGER.debug("[HomeAIVision] Disconnected device_removed_listener.")

        # NOTE: Finally, remove the store
        hass.data[DOMAIN].pop('store', None)
    else:
        _LOGGER.error("[HomeAIVision] Unloading platforms failed.")

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

#     # Delete device from store
#     await store.async_remove_device(device_entry.id)

#     _LOGGER.debug(f"[HomeAIVision] Device {device_entry.id} removed successfully")
#     return True
