import aiohttp
import asyncio
import logging
import io
from PIL import Image, ImageDraw
from datetime import datetime
from aiohttp import ClientConnectorError

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.components.persistent_notification import (
    create as pn_create,
)

from .notification_manager import send_notification
from .save_image_manager import save_image, clean_up_old_images
from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_DETECTED_OBJECT,
)

_LOGGER = logging.getLogger(__name__)

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
            _LOGGER.debug("[HomeAIVision] Starting analyze")
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
                _LOGGER.debug(
                    f"[HomeAIVision] Azure response: {response_json}"
                )
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
        _LOGGER.error(f"[HomeAIVision] Error during analysis: {e}")
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
    cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
    days_to_keep = device_config.get("days_to_keep", 7)
    organize_by_day = device_config.get("organize_by_day", True)
    max_images = device_config.get("max_images", 30)
    detected_objects = [device_config.get(CONF_DETECTED_OBJECT)]
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
                            _LOGGER.info(
                                "[HomeAIVision] Image successfully downloaded"
                            )
                            image_data = await response.read()
                            (
                                object_detected,
                                modified_image_data,
                                detected_object_name,
                            ) = await analyze_and_draw_object(
                                image_data,
                                entry.data.get(CONF_AZURE_API_KEY),
                                entry.data.get(CONF_AZURE_ENDPOINT),
                                detected_objects,
                                confidence_threshold,
                            )
                            if object_detected and modified_image_data:
                                save_path = await save_image(
                                    cam_frames_path,
                                    modified_image_data,
                                    organize_by_day,
                                    max_images,
                                )
                                _LOGGER.info(
                                    f"[HomeAIVision] Saving image: {save_path}"
                                )

                                # Increment the Azure request counter
                                hass.data.setdefault(DOMAIN, {}).setdefault('azure_request_counts', {})
                                counts = hass.data[DOMAIN]['azure_request_counts']
                                counts[device_id] = counts.get(device_id, 0) + 1

                                # Signal the entity to update its state
                                async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")

                                # Send notification if enabled
                                if send_notifications:
                                    language = device_config.get(
                                        "notification_language", "en"
                                    )
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

    # Start the periodic check in the background
    hass.loop.create_task(periodic_check())
