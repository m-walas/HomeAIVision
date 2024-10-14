import asyncio
import logging
import io
import aiohttp # type: ignore

from PIL import Image, ImageDraw # type: ignore
from datetime import datetime # type: ignore
from aiohttp import ClientConnectorError # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send # type: ignore
from homeassistant.components.persistent_notification import create as pn_create # type: ignore

from .notification_manager import send_notification
from .save_image_manager import save_image, clean_up_old_images
from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_TO_DETECT_OBJECT,
)
from .store import HomeAIVisionStore

_LOGGER = logging.getLogger(__name__)
# _LOGGER = logging.getLogger("homeaivision")
# _AZURE_LOGGER = logging.getLogger("azure_cognitiveservices_vision_computervision")

async def analyze_and_draw_object(
    image_data, azure_api_key, azure_endpoint, objects, confidence_threshold
):
    """
    Analyzes the image for the presence of specified objects using Azure
    Cognitive Services.
    """
    headers = {
        'Ocp-Apim-Subscription-Key': azure_api_key,
        'Content-Type': 'application/octet-stream',
    }
    params = {'visualFeatures': 'Objects'}

    object_detected = False
    detected_object_name = None

    _LOGGER.debug(
        f"[HomeAIVision] Azure API URL: {azure_endpoint}, "
        f"Azure API Key: {azure_api_key[:5]}***"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{azure_endpoint}/vision/v3.0/analyze",
                headers=headers,
                params=params,
                data=image_data,
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        f"[HomeAIVision] Failed to analyze image, "
                        f"status code: {response.status}"
                    )
                    response_text = await response.text()
                    _LOGGER.error(
                        f"[HomeAIVision] Error response: {response_text}"
                    )
                    return False, None, None

                response_json = await response.json()
                _LOGGER.debug(f"Azure response: {response_json}")
                # _AZURE_LOGGER.info(f"Received response from Azure: {response_json}")

                image = Image.open(io.BytesIO(image_data))
                draw = ImageDraw.Draw(image)

                for item in response_json.get('objects', []):
                    _LOGGER.debug(
                        f"[HomeAIVision] Object detected with confidence "
                        f"{item['confidence']}: {item['object']}"
                    )
                    object_name, confidence = extract_object_with_hierarchy(
                        item, objects
                    )
                    if object_name and confidence >= confidence_threshold:
                        object_detected = True
                        detected_object_name = object_name
                        rect = item['rectangle']
                        draw.rectangle(
                            [
                                (rect['x'], rect['y']),
                                (rect['x'] + rect['w'], rect['y'] + rect['h']),
                            ],
                            outline="red",
                            width=5,
                        )

                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                return object_detected, buffered.getvalue(), detected_object_name
    except Exception as e:
        _LOGGER.error(f"Error during analysis: {e}")
        # _AZURE_LOGGER.exception("Exception occurred during Azure analysis")
        return False, None, None


def extract_object_with_hierarchy(item, target_objects):
    """
    Traverse the object and its parents to find a matching target object.
    """
    while item:
        if item['object'] in target_objects:
            return item['object'], item['confidence']
        item = item.get('parent')
    return None, None


async def setup_periodic_camera_check(hass, entry, device_config):
    """
    Sets up periodic checking of the camera feed, analyzing for objects,
    and saving images where objects are detected.
    """
    device_id = device_config['id']
    store = hass.data[DOMAIN]['store']
    cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
    days_to_keep = device_config.get("days_to_keep", 7)
    organize_by_day = device_config.get("organize_by_day", True)
    max_images = device_config.get("max_images", 30)
    to_detect_object = [device_config.get(CONF_TO_DETECT_OBJECT)]
    confidence_threshold = device_config.get("confidence_threshold", 0.6)
    time_between_requests = device_config.get("time_between_requests", 30)
    send_notifications = device_config.get("send_notifications", False)
    cam_url = device_config.get("url", "")

    if not cam_url:
        _LOGGER.error(
            f"[HomeAIVision] Camera URL is missing for device "
            f"{device_config['name']}"
        )
        return

    await clean_up_old_images(cam_frames_path, days_to_keep)

    async def periodic_check():
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    # NOTE: Get the latest device configuration
                    device = store.get_device(device_id)
                    if not device:
                        _LOGGER.error(f"[HomeAIVision] Device {device_id} not found")
                        break
                    to_detect_object = [device.to_detect_object]
                    confidence_threshold = device.confidence_threshold

                    _LOGGER.debug(f"[HomeAIVision] Current to detect objects: {to_detect_object}")
                    if "pwd=" in cam_url:
                        pwd_index = cam_url.find("pwd=") + len("pwd=")
                        cam_url_log = f"{cam_url[:pwd_index]}***"
                    else:
                        cam_url_log = cam_url
                    _LOGGER.debug(
                        f"[HomeAIVision] Camera URL: {cam_url_log}"
                    )

                    async with session.get(cam_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            (
                                object_detected,
                                modified_image_data,
                                detected_object_name,
                            ) = await analyze_and_draw_object(
                                image_data,
                                entry.data.get(CONF_AZURE_API_KEY),
                                entry.data.get(CONF_AZURE_ENDPOINT),
                                to_detect_object,
                                confidence_threshold,
                            )

                            # NOTE: Increment the Azure request counter
                            device = store.get_device(device_id)
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
                                save_path = await save_image(
                                    cam_frames_path,
                                    modified_image_data,
                                    organize_by_day,
                                    max_images,
                                )
                                # _LOGGER.info(f"[HomeAIVision] Saving image: {save_path}")

                                # NOTE: Send notification if enabled
                                if send_notifications:
                                    language = store.get_language()
                                    _LOGGER.debug(f"[HomeAIVision] Notification language: {language}")
                                    relative_path = save_path.replace(
                                        hass.config.path(), ""
                                    ).lstrip("/")
                                    await send_notification(
                                        hass,
                                        detected_object_name,
                                        relative_path,
                                        organize_by_day,
                                        language,
                                    )
                        else:
                            _LOGGER.warning(
                                f"[HomeAIVision] Failed to download image, "
                                f"status code: {response.status}"
                            )
                except ClientConnectorError:
                    _LOGGER.error(
                        f"[HomeAIVision] Unable to connect to the camera at "
                        f"{cam_url}. Please check if the camera is online "
                        f"and the URL is correct."
                    )
                    pn_create(
                        hass,
                        (
                            f"Unable to connect to the camera at {cam_url}. "
                            "Please check if the camera is online and the "
                            "URL is correct."
                        ),
                        title="HomeAIVision Camera Connection Error",
                        notification_id=f"homeaivision_camera_error_{device_id}",
                    )
                except Exception as e:
                    _LOGGER.error(f"[HomeAIVision] Unexpected error: {e}")

                await asyncio.sleep(time_between_requests)

    # NOTE: Start the periodic check in the background
    hass.loop.create_task(periodic_check())
