import logging
import aiohttp # type: ignore

from homeassistant.core import HomeAssistant, ServiceCall # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send # type: ignore
from homeassistant.components.persistent_notification import create as pn_create # type: ignore
from aiohttp import ClientConnectorError # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore
from .camera import analyze_and_draw_object
from .save_image_manager import save_image
from .notification_manager import send_notification

_LOGGER = logging.getLogger(__name__)

# NOTE: Define the actions that can be called from Home Assistant
ACTION_MANUAL_ANALYZE = "manual_analyze"
ACTION_RESET_LOCAL_COUNTER = "reset_local_counter"
ACTION_RESET_GLOBAL_COUNTER = "reset_global_counter"


# NOTE: Implementations of the actions
async def handle_manual_analyze(call: ServiceCall, hass: HomeAssistant):
    """Handle the manual analyze action call."""
    _LOGGER.debug(f"handle_manual_analyze called with data: {call.data}")
    device_id = call.data.get('device_id')
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    device = store.get_device(device_id)

    # NOTE: Check if device_id is provided
    if not device_id:
        _LOGGER.error("[HomeAIVision] Manual Analyze action called without device_id")
        return

    # NOTE: Check if device exists
    if not device:
        _LOGGER.error(f"[HomeAIVision] Manual Analyze action called for unknown device_id: {device_id}")
        return

    # NOTE: Check if camera URL is provided
    if not device.url:
        _LOGGER.error(f"[HomeAIVision] Manual Analyze action called for device {device_id} without camera URL")
        return

    # NOTE: Load Azure API Key and Endpoint from integration config
    azure_api_key = hass.data[DOMAIN].get('azure_api_key')
    azure_endpoint = hass.data[DOMAIN].get('azure_endpoint')
    if not azure_api_key or not azure_endpoint:
        _LOGGER.error("[HomeAIVision] Azure API Key or Endpoint not found in config")
        return

    to_detect_object = device.to_detect_object
    confidence_threshold = device.confidence_threshold

    _LOGGER.debug(f"[HomeAIVision] Starting manual analysis for device {device_id}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(device.url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    object_detected, modified_image_data, detected_object_name = await analyze_and_draw_object(
                        image_data,
                        azure_api_key,
                        azure_endpoint,
                        to_detect_object,
                        confidence_threshold,
                    )

                    # NOTE: Increment the Azure request counter
                    if device:
                        device.device_azure_request_count += 1
                        await store.async_save()
                        async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")
                        _LOGGER.info(f"[HomeAIVision] Device {device_id} Azure request count: {device.device_azure_request_count}")
                    else:
                        _LOGGER.error(
                            f"[HomeAIVision] Device {device_id} not found in store"
                        )

                    # NOTE: Increment global counter
                    await store.async_increment_global_counter()
                    _LOGGER.info(f"[HomeAIVision] Global counter Azure: {store.get_global_counter()}")

                    # NOTE: Save the image if object detected
                    if object_detected and modified_image_data:
                        cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
                        save_path = await save_image(
                            cam_frames_path,
                            modified_image_data,
                            device.organize_by_day,
                            device.max_images,
                        )
                        _LOGGER.info(f"[HomeAIVision] Analysis complete for device {device_id}, image saved at {save_path}")

                        # NOTE: Send notification if enabled
                        if device.send_notifications:
                            language = store.get_language()
                            _LOGGER.debug(f"[HomeAIVision] Notification language: {language}")
                            relative_path = save_path.replace(hass.config.path(), "").lstrip("/")
                            await send_notification(
                                hass,
                                detected_object_name,
                                relative_path,
                                device.organize_by_day,
                                language,
                            )

                    _LOGGER.info(f"[HomeAIVision] Manual analyze triggered for device {device_id}")
                else:
                    _LOGGER.warning(f"[HomeAIVision] Failed to download image, status code: {response.status}")
    except ClientConnectorError:
        _LOGGER.error(
            f"[HomeAIVision] Unable to connect to the camera at {device.url}. Please check if the camera is online and the URL is correct."
        )
        pn_create(
            hass,
            (
                f"Unable to connect to the camera at {device.url}. "
                "Please check if the camera is online and the URL is correct."
            ),
            title="HomeAIVision Camera Connection Error",
            notification_id=f"homeaivision_camera_error_{device_id}",
        )
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Unexpected error during manual analysis: {e}")


async def handle_reset_local_counter(call: ServiceCall, hass: HomeAssistant):
    """Handle the reset local counter action call."""
    device_id = call.data.get('device_id')
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']

    if not device_id:
        _LOGGER.error("[HomeAIVision] Reset Local Counter action called without device_id")
        return

    device = store.get_device(device_id)
    if not device:
        _LOGGER.error(f"[HomeAIVision] Reset Local Counter action called for unknown device_id: {device_id}")
        return

    device.device_azure_request_count = 0
    await store.async_update_device(device_id, device)
    _LOGGER.info(f"[HomeAIVision] Reset local Azure request count for device {device_id}")

    async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")


async def handle_reset_global_counter(call: ServiceCall, hass: HomeAssistant):
    """Handle the reset global counter action call."""
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    await store.async_reset_global_counter()
    _LOGGER.info("[HomeAIVision] Reset global Azure request count")

    async_dispatcher_send(hass, f"{DOMAIN}_global_update")
