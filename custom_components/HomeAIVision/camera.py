import aiohttp
import asyncio
from PIL import Image, ImageDraw
import os
from datetime import datetime
import io
import logging

from .notification_manager import send_notification
from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_CAM_URL,
    CONF_TIME_BETWEEN_REQUESTS,
    CONF_ORGANIZE_BY_DAY,
    CONF_SEND_NOTIFICATIONS,
    CONF_NOTIFICATION_LANGUAGE,
    CONF_CONFIDENCE_THRESHOLD,
    CONF_DETECTED_OBJECT,
)
from .image_save_manager import save_image, clean_up_old_images

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

async def analyze_and_draw_object(image_data, azure_api_key, azure_endpoint, objects, confidence_threshold):
    """
    Analyzes the image for the presence of a person using Azure Cognitive Services.
    
    Args:
        image_data (bytes): The image data to analyze.
        azure_api_key (str): The API key for Azure Cognitive Services.
        azure_endpoint (str): The endpoint URL for Azure Cognitive Services.
        objects (list): A list of objects to detect in the image.
        confidence_threshold (float): The minimum confidence level required for detection.
    
    Returns:
        tuple: A tuple containing a boolean indicating if a person was detected,
        the modified image data with drawn rectangles around detected objects,
        and the name of the detected object.
    """
    headers = {
        'Ocp-Apim-Subscription-Key': azure_api_key,
        'Content-Type': 'application/octet-stream'
    }
    params = {
        'visualFeatures': 'Objects'
    }
    
    object_detected = False
    detected_object_name = None

    _LOGGER.debug(f"[HomeAIVision] Azure API URL: {azure_endpoint}, Azure API Key: {azure_api_key[:5]}***")
    async with aiohttp.ClientSession() as session:
        try:
            _LOGGER.debug("[HomeAIVision] Starting analyze")
            async with session.post(f"{azure_endpoint}/vision/v3.0/analyze", headers=headers, params=params, data=image_data) as response:
                if response.status != 200:
                    _LOGGER.error(f"[HomeAIVision] Failed to analyze image, status code: {response.status}")
                    response_text = await response.text()
                    _LOGGER.error(f"[HomeAIVision] Error response: {response_text}")
                    return False, None, None
                
                response_json = await response.json()
                _LOGGER.debug(f"[HomeAIVision] Azure response: {response_json}")
                image = Image.open(io.BytesIO(image_data))
                draw = ImageDraw.Draw(image)

                for item in response_json.get('objects', []):
                    _LOGGER.debug(f"[HomeAIVision] Object detected with confidence {item['confidence']}: {item['object']}")
                    object_name, confidence = extract_object_with_hierarchy(item, objects)
                    if object_name and confidence >= confidence_threshold:
                        object_detected = True
                        detected_object_name = object_name
                        rect = item['rectangle']
                        draw.rectangle([(rect['x'], rect['y']), (rect['x'] + rect['w'], rect['y'] + rect['h'])], outline="red", width=5)
                
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                return object_detected, buffered.getvalue(), detected_object_name
        except Exception as e:
            _LOGGER.error(f"Error during analysis: {e}")
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

async def update_azure_request_count(hass, entry_id):
    """
    Increments the Azure request counter and updates the config entry data.
    """
    hass.data[DOMAIN][entry_id]["azure_request_count"] += 1
    _LOGGER.debug(f"[HomeAIVision] Azure request count: {hass.data[DOMAIN][entry_id]['azure_request_count']}")

    # Aktualizacja config entry data
    config_entry = hass.config_entries.async_get_entry(entry_id)
    if config_entry:
        updated_data = config_entry.data.copy()
        updated_data["azure_request_count"] = hass.data[DOMAIN][entry_id]["azure_request_count"]
        hass.config_entries.async_update_entry(config_entry, data=updated_data)
        _LOGGER.debug(f"[HomeAIVision] Updated config entry data with new azure_request_count: {updated_data['azure_request_count']}")


async def setup_periodic_camera_check(hass, entry):
    """
    Sets up periodic checking of the camera feed, analyzing for persons,
    and saving images where persons are detected.
    
    Args:
        hass (HomeAssistant): The HomeAssistant object.
        entry (ConfigEntry): The configuration entry for this integration.
    """
    config = hass.data[DOMAIN][entry.entry_id]
    cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
    days_to_keep = config.get("days_to_keep", 7)
    organize_by_day = config.get("organize_by_day", True)
    max_images = config.get("max_images", 30)
    detected_objects = [config.get(CONF_DETECTED_OBJECT)]
    confidence_threshold = config.get("confidence_threshold", 0.6)
    time_between_requests = config.get("time_between_requests", 30)

    await clean_up_old_images(cam_frames_path, days_to_keep)

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                cam_url = config.get(CONF_CAM_URL, "")
                if "pwd=" in cam_url:
                    # Mask the password in logs
                    pwd_index = cam_url.find("pwd=") + len("pwd=")
                    cam_url_log = f"{cam_url[:pwd_index]}***"
                else:
                    cam_url_log = cam_url
                _LOGGER.debug(f"[HomeAIVision] Camera URL: {cam_url_log}")

                async with session.get(cam_url) as response:
                    if response.status == 200:
                        _LOGGER.info("[HomeAIVision] Image successfully downloaded")
                        image_data = await response.read()
                        object_detected, modified_image_data, detected_object_name = await analyze_and_draw_object(
                            image_data, 
                            config.get(CONF_AZURE_API_KEY),
                            config.get(CONF_AZURE_ENDPOINT),
                            detected_objects,
                            confidence_threshold
                        )
                        if object_detected and modified_image_data:
                            save_path = await save_image(cam_frames_path, modified_image_data, organize_by_day, max_images)
                            _LOGGER.info(f"[HomeAIVision] Saving image: {save_path}")

                            # Increment the Azure request counter
                            await update_azure_request_count(hass, entry.entry_id)
                            
                            # Send notification if enabled
                            if config.get("send_notifications", False):
                                language = config.get("notification_language", "en")
                                relative_path = save_path.replace(hass.config.path(), "").lstrip("/")
                                await send_notification(hass, detected_object_name, relative_path, organize_by_day, language)
                    else:
                        _LOGGER.warning(f"[HomeAIVision] Failed to download image, status code: {response.status}")
            except Exception as e:
                _LOGGER.error(f"[HomeAIVision] Unexpected error: {e}")
            
            await asyncio.sleep(time_between_requests)
