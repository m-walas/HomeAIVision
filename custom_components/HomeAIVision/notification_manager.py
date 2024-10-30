import json
import os
import logging
import aiofiles # type: ignore

from homeassistant.helpers.network import get_url # type: ignore

_LOGGER = logging.getLogger(__name__)

async def send_notification(hass, to_detect_object, image_path=None, notification_language='en'):
    """
    Send a notification message via Home Assistant with an optional image attachment.

    Args:
        hass: The Home Assistant instance.
        to_detect_object (str): The object that was detected.
        image_path (str, optional): The path to the image within the `www` directory.
        notification_language (str, optional): The language for the notification.
    """
    try:
        message_key = f"{to_detect_object}_detected"

        base_url = get_url(hass, prefer_external=False, allow_internal=True)
        _LOGGER.debug(f"[HomeAIVision] Base URL for notification: {base_url}")
        message = await get_translated_message(notification_language, message_key)

        data = {"message": message}
        if image_path:
            corrected_image_path = image_path.lstrip('/').replace('www/', '', 1)
            image_url = f"{base_url}/local/{corrected_image_path}"
            _LOGGER.debug(f"[HomeAIVision] Full image URL for notification: {image_url}")
            data["data"] = {
                "attachment": {
                    "content-type": "jpeg",
                    "url": image_url
                }
            }

        await hass.services.async_call("notify", "notify", data, blocking=True)
    except Exception as e:
        _LOGGER.error(f"Failed to send notification: {e}")

async def load_translations(language):
    base_dir = os.path.dirname(__file__)
    translations_path = os.path.join(base_dir, 'translations', f'{language}.json')
    default_translations_path = os.path.join(base_dir, 'translations', 'en.json')

    if not os.path.exists(translations_path):
        _LOGGER.warning(f"[HomeAIVision] Translation file for {language} not found. Falling back to English.")
        translations_path = default_translations_path

    try:
        async with aiofiles.open(translations_path, 'r', encoding='utf-8') as file:
            content = await file.read()
            return json.loads(content)
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Error loading translation file: {e}")
        return {}

async def get_translated_message(language, message_key):
    translations = await load_translations(language)
    message = translations.get("message", {}).get(message_key)

    if message is None:
        _LOGGER.warning(f"[HomeAIVision] No translation found for {message_key} in {language}, using default message")
        message = "Default message"

    return message
