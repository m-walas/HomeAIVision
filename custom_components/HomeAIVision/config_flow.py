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
)


# Helper function to verify Azure API key and endpoint by making a test request.
# It returns True if credentials are valid, otherwise False.
async def verify_azure_credentials(azure_api_key, azure_endpoint):
    headers = {'Ocp-Apim-Subscription-Key': azure_api_key}
    test_url = azure_endpoint.rstrip("/") + "/vision/v3.0/analyze"
    async with aiohttp.ClientSession() as session:
        async with session.post(test_url, headers=headers) as response:
            return response.status != 401


# Helper function to check if the camera URL is properly formatted.
# It performs a simple check to see if the URL starts with http:// or https://
def verify_camera_url(cam_url):
    return cam_url.startswith("http://") or cam_url.startswith("https://")


class HomeAIVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    temp_config = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            azure_valid = await verify_azure_credentials(user_input[CONF_AZURE_API_KEY], user_input[CONF_AZURE_ENDPOINT])
            if not azure_valid:
                errors["base"] = "azure_credentials_invalid"
                
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"

            if not errors:
                self.temp_config = user_input
                return await self.async_step_additional_options()
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_AZURE_API_KEY): str,
                vol.Required(CONF_AZURE_ENDPOINT): str,
                vol.Required(CONF_CAM_URL): str,
#
                vol.Required(CONF_TIME_BETWEEN_REQUESTS, default=30): cv.positive_int,
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=False): bool,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=True): bool,
            }),
            errors=errors,
        )


    async def async_step_additional_options(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.temp_config.update(user_input)
            return self.async_create_entry(title="HomeAIVision", data=self.temp_config)

        fields = {
            vol.Required(CONF_MAX_IMAGES, default=30): cv.positive_int,
        }
        if self.temp_config.get(CONF_ORGANIZE_BY_DAY, True):
            fields[vol.Required(CONF_DAYS_TO_KEEP, default=7)] = cv.positive_int
        if self.temp_config.get(CONF_SEND_NOTIFICATIONS, False):
            fields[vol.Required(CONF_NOTIFICATION_LANGUAGE, default='en')] = vol.In({'en': 'English', 'pl': 'Polski'})

        return self.async_show_form(
            step_id="additional_options",
            data_schema=vol.Schema(fields),
            errors={},
        )


class HomeAIVisionOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_MAX_IMAGES, default=self.config_entry.options.get(CONF_MAX_IMAGES, 30)): cv.positive_int,
                vol.Required(CONF_TIME_BETWEEN_REQUESTS, default=self.config_entry.options.get(CONF_TIME_BETWEEN_REQUESTS, 30)): cv.positive_int,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=self.config_entry.options.get(CONF_ORGANIZE_BY_DAY, True)): bool,
                vol.Optional(CONF_DAYS_TO_KEEP, default=self.config_entry.options.get(CONF_DAYS_TO_KEEP, 7)): cv.positive_int,
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=self.config_entry.options.get(CONF_SEND_NOTIFICATIONS, False)): bool,
                vol.Optional(CONF_NOTIFICATION_LANGUAGE, default=self.config_entry.options.get(CONF_NOTIFICATION_LANGUAGE, 'en')): vol.In({'en': 'English', 'pl': 'Polski'}),
            }),
        )