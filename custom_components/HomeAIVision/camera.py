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
)

from .image_save_manager import (
    save_image, 
    clean_up_old_images,
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

async def analyze_and_draw_person(image_data, azure_api_key, azure_endpoint):
    """
    Analyzes the image for the presence of a person using Azure Cognitive Services.
    
    Args:
        image_data (bytes): The image data to analyze.
        azure_api_key (str): The API key for Azure Cognitive Services.
        azure_endpoint (str): The endpoint URL for Azure Cognitive Services.
    
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
    person_detected = False
    _LOGGER.debug(f"Azure API URL: {azure_endpoint}, Azure API Key: {azure_api_key[:5]}***")
    async with aiohttp.ClientSession() as session:
        try:
            _LOGGER.debug("Starting analyze")
            async with session.post(f"{azure_endpoint}/vision/v3.0/analyze", headers=headers, params=params, data=image_data) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to analyze image, status code: {response.status}")
                    response_text = await response.text()
                    _LOGGER.error(f"Error response: {response_text}")
                    return False, None
                
                response_json = await response.json()
                _LOGGER.debug(f"Azure response: {response_json}")
                image = Image.open(io.BytesIO(image_data))
                draw = ImageDraw.Draw(image)
                for detected_object in response_json.get('objects', []):
                    _LOGGER.debug(f"Object detected with confidence {detected_object['confidence']}: {detected_object['object']}")
                    if detected_object['object'] == 'person' and detected_object['confidence'] > 0.6:
                        person_detected = True
                        rect = detected_object['rectangle']
                        draw.rectangle([(rect['x'], rect['y']), (rect['x'] + rect['w'], rect['y'] + rect['h'])], outline="red", width=5)
                
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                return person_detected, buffered.getvalue()
        except Exception as e:
            _LOGGER.error(f"Error during analysis: {e}")
            return False, None


async def setup_periodic_camera_check(hass, entry):
    """
    Sets up periodic checking of the camera feed, analyzing for persons,
    and saving images where persons are detected.
    
    Args:
        hass (HomeAssistant): The HomeAssistant object.
        entry (ConfigEntry): The configuration entry for this integration.
    """
    cam_frames_path = hass.config.path("www/camera_analysis/cam_frames/")
    days_to_keep = entry.data.get("days_to_keep", 7)
    organize_by_day = entry.data.get("organize_by_day", True)
    max_images = entry.data.get("max_images", 30)
    
    clean_up_old_images(cam_frames_path, days_to_keep)

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                _LOGGER.debug(f"Camera URL: {entry.data[CONF_CAM_URL]}")
                async with session.get(entry.data[CONF_CAM_URL]) as response:
                    if response.status == 200:
                        _LOGGER.info("Image successfully downloaded")
                        image_data = await response.read()
                        person_detected, modified_image_data = await analyze_and_draw_person(image_data, entry.data[CONF_AZURE_API_KEY], entry.data[CONF_AZURE_ENDPOINT])
                        if person_detected:
                            save_path = await save_image(cam_frames_path, modified_image_data, organize_by_day, max_images)
                            _LOGGER.info(f"Saving image: {save_path}")
                            
                            # send notification if send_notification = true
                            if person_detected and entry.data.get(CONF_SEND_NOTIFICATIONS):
                                language = entry.data.get(CONF_NOTIFICATION_LANGUAGE, "en")
                                message_key = "person_detected"
                                relative_path = save_path.replace(hass.config.path(), "").lstrip("/")
                                await send_notification(hass, message_key, relative_path, entry.data.get(CONF_ORGANIZE_BY_DAY, True), language)
                    await asyncio.sleep(entry.data[CONF_TIME_BETWEEN_REQUESTS])
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {e}")
