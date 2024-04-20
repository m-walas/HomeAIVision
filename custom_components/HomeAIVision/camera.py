import aiohttp
import asyncio
from PIL import Image, ImageDraw
import os
from datetime import datetime
import io
import logging

from .notification_manager import (
    send_notification,
)

from .const import (
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

from .image_save_manager import (
    save_image, 
    clean_up_old_images,
)

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
        tuple: A tuple containing a boolean indicating if a person was detected
                and the modified image data with drawn rectangles around detected persons.
    """
    headers = {
        'Ocp-Apim-Subscription-Key': azure_api_key,
        'Content-Type': 'application/octet-stream'
    }
    params = {
        'visualFeatures': 'Objects'
    }
    
    object_detection = False
    detected_object_name = None

    _LOGGER.debug(f"Azure API URL: {azure_endpoint}, Azure API Key: {azure_api_key[:5]}***")
    async with aiohttp.ClientSession() as session:
        try:
            _LOGGER.debug("Starting analyze")
            async with session.post(f"{azure_endpoint}/vision/v3.0/analyze", headers=headers, params=params, data=image_data) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to analyze image, status code: {response.status}")
                    response_text = await response.text()
                    _LOGGER.error(f"Error response: {response_text}")
                    return False, None, None
                
                response_json = await response.json()
                _LOGGER.debug(f"Azure response: {response_json}")
                image = Image.open(io.BytesIO(image_data))
                draw = ImageDraw.Draw(image)

                for item in response_json.get('objects', []):
                    _LOGGER.debug(f"Object detected with confidence {item['confidence']}: {item['object']}")
                    object_name = item['object']
                    if object_name in objects and item['confidence'] >= confidence_threshold:
                        object_detection = True
                        detected_object_name = object_name
                        rect = item['rectangle']
                        draw.rectangle([(rect['x'], rect['y']), (rect['x'] + rect['w'], rect['y'] + rect['h'])], outline="red", width=5)

                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                return object_detection, buffered.getvalue(), detected_object_name
        except Exception as e:
            _LOGGER.error(f"Error during analysis: {e}")
            return False, None, None


async def setup_periodic_camera_check(hass, entry):
    """
    Sets up periodic checking of the camera feed, analyzing for persons,
    and saving images where persons are detected.
    
    Args:
        hass (HomeAssistant): The HomeAssistant object.
        entry (ConfigEntry): The configuration entry for this integration.
    """
    cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
    days_to_keep = entry.data.get("days_to_keep", 7)
    organize_by_day = entry.data.get("organize_by_day", True)
    max_images = entry.data.get("max_images", 30)
    detected_objects = [entry.data.get(CONF_DETECTED_OBJECT)]
    confidence_threshold = entry.data.get(CONF_CONFIDENCE_THRESHOLD)
    
    clean_up_old_images(cam_frames_path, days_to_keep)

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                _LOGGER.debug(f"Camera URL: {entry.data[CONF_CAM_URL]}")
                async with session.get(entry.data[CONF_CAM_URL]) as response:
                    if response.status == 200:
                        _LOGGER.info("Image successfully downloaded")
                        image_data = await response.read()
                        object_detected, modified_image_data, detected_object_name = await analyze_and_draw_object(
                            image_data, 
                            entry.data[CONF_AZURE_API_KEY], 
                            entry.data[CONF_AZURE_ENDPOINT],
                            detected_objects,
                            confidence_threshold
                        )
                        if object_detected:
                            save_path = await save_image(cam_frames_path, modified_image_data, organize_by_day, max_images)
                            _LOGGER.info(f"Saving image: {save_path}")
                            
                            # send notification if notifications are enabled
                            if entry.data.get(CONF_SEND_NOTIFICATIONS):
                                language = entry.data.get(CONF_NOTIFICATION_LANGUAGE, "en")
                                relative_path = save_path.replace(hass.config.path(), "").lstrip("/")
                                await send_notification(hass, detected_object_name, relative_path, organize_by_day, language)
                    await asyncio.sleep(entry.data[CONF_TIME_BETWEEN_REQUESTS])
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {e}")