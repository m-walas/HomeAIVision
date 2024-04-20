from homeassistant import config_entries
import voluptuous as vol
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import aiohttp

from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_CAM_URL,
    CONF_MAX_IMAGES,
    CONF_TIME_BETWEEN_REQUESTS,
    CONF_ORGANIZE_BY_DAY,
    CONF_DAYS_TO_KEEP,
    CONF_SEND_NOTIFICATIONS,
    CONF_NOTIFICATION_LANGUAGE,
    CONF_DETECTED_OBJECT,
    CONF_CONFIDENCE_THRESHOLD,
    CONF_INTEGRATION_TITLE,
)

import logging

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


async def verify_azure_credentials(azure_api_key, azure_endpoint):
    """
    Verifies the Azure API credentials by making a test request to the Azure Vision API.
    Returns True if the API credentials are valid, otherwise False.
    """
    headers = {'Ocp-Apim-Subscription-Key': azure_api_key}
    test_url = azure_endpoint.rstrip("/") + "/vision/v3.0/analyze"
    async with aiohttp.ClientSession() as session:
        async with session.post(test_url, headers=headers) as response:
            return response.status != 401


def verify_camera_url(cam_url):
    """
    Checks if the camera URL is properly formatted, starting with http:// or https://.
    Returns True if the URL is valid, otherwise False.
    """
    return cam_url.startswith("http://") or cam_url.startswith("https://")


class HomeAIVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Manages the configuration flow for the HomeAIVision integration.
    """
    VERSION = 1
    temp_config = {}


    async def async_step_user(self, user_input=None):
        """
        Initial step in the configuration flow, allowing the user to provide a custom title for the integration.
        """
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(CONF_INTEGRATION_TITLE, default="HomeAIVision"): str,
                }),
            )
        self.temp_config['integration_title'] = user_input['integration_title']
        return await self.async_step_azure_conf()


    async def async_step_azure_conf(self, user_input=None):
        """
        Handles the main configuration step where users enter their Azure API key, endpoint, camera URL, and other options.
        """
        errors = {}
        if user_input is not None:
            azure_valid = await verify_azure_credentials(user_input[CONF_AZURE_API_KEY], user_input[CONF_AZURE_ENDPOINT])
            if not azure_valid:
                errors["base"] = "azure_credentials_invalid"
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"
            if not errors:
                self.temp_config.update(user_input)
                return await self.async_step_additional_options()

        return self.async_show_form(
            step_id="azure_conf",
            data_schema=vol.Schema({
                vol.Required(CONF_AZURE_API_KEY): str,
                vol.Required(CONF_AZURE_ENDPOINT): str,
                vol.Required(CONF_CAM_URL): str,
                vol.Required(CONF_TIME_BETWEEN_REQUESTS, default=30): cv.positive_int,
                vol.Required(CONF_DETECTED_OBJECT, default='person'): vol.In({
                    'person': "Person", 'car': "Car", 'cat': "Cat", 'dog': "Dog"
                }),
                vol.Required(CONF_CONFIDENCE_THRESHOLD, default=0.6): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=False): bool,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=True): bool,
            }),
            errors=errors,
            description_placeholders={"min_confidence": "Setting the confidence threshold below 0.1 is not recommended."}
        )


    async def async_step_additional_options(self, user_input=None):
        """
        Handles additional configuration options like maximum images, days to keep images, and notification language.
        """
        if user_input is not None:
            self.temp_config.update(user_input)
            return self.async_create_entry(title=self.temp_config['integration_title'], data=self.temp_config)
        fields = {
            vol.Required(CONF_MAX_IMAGES, default=30): cv.positive_int,
            vol.Required(CONF_DAYS_TO_KEEP, default=7): cv.positive_int,
            vol.Required(CONF_NOTIFICATION_LANGUAGE, default='en'): vol.In({'en': 'English', 'pl': 'Polski'})
        }
        if self.temp_config.get(CONF_SEND_NOTIFICATIONS, False):
            fields[vol.Required(CONF_NOTIFICATION_LANGUAGE, default='en')] = vol.In({'en': 'English', 'pl': 'Polski'})

        return self.async_show_form(
            step_id="additional_options",
            data_schema=vol.Schema(fields),
        )
