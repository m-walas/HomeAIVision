import logging
import uuid
import aiohttp
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.components.persistent_notification import create as pn_create
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_config_entry

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

_LOGGER = logging.getLogger(__name__)


async def verify_azure_credentials(azure_api_key, azure_endpoint):
    """Verifies the Azure API credentials by making a test request to the Azure Vision API."""
    headers = {'Ocp-Apim-Subscription-Key': azure_api_key}
    test_url = azure_endpoint.rstrip("/") + "/vision/v3.0/analyze"
    async with aiohttp.ClientSession() as session:
        async with session.post(test_url, headers=headers) as response:
            return response.status != 401


def verify_camera_url(cam_url):
    """Checks if the camera URL is properly formatted, starting with http:// or https://."""
    return cam_url.startswith("http://") or cam_url.startswith("https://")


class HomeAIVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Manages the configuration flow for the HomeAIVision integration."""
    VERSION = 1
    temp_config = {}

    async def async_step_user(self, user_input=None):
        """Initial step to configure the Azure credentials and integration title."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(CONF_INTEGRATION_TITLE, default="HomeAIVision"): str,
                }),
            )
        self.temp_config['integration_title'] = user_input[CONF_INTEGRATION_TITLE]
        return await self.async_step_azure_conf()

    async def async_step_azure_conf(self, user_input=None):
        """Step to configure the Azure API credentials."""
        errors = {}
        if user_input is not None:
            azure_valid = await verify_azure_credentials(
                user_input[CONF_AZURE_API_KEY], user_input[CONF_AZURE_ENDPOINT]
            )
            if not azure_valid:
                errors["base"] = "azure_credentials_invalid"
            else:
                self.temp_config.update(user_input)
                return self.async_create_entry(
                    title=self.temp_config['integration_title'], 
                    data={
                        CONF_AZURE_API_KEY: self.temp_config[CONF_AZURE_API_KEY],
                        CONF_AZURE_ENDPOINT: self.temp_config[CONF_AZURE_ENDPOINT],
                        "devices": {},
                    }
                )

        return self.async_show_form(
            step_id="azure_conf",
            data_schema=vol.Schema({
                vol.Required(CONF_AZURE_API_KEY): str,
                vol.Required(CONF_AZURE_ENDPOINT): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Returns the options flow to add or edit devices."""
        return HomeAIVisionOptionsFlow(config_entry)


class HomeAIVisionOptionsFlow(config_entries.OptionsFlow):
    """Manages the options flow for adding and editing devices (cameras)."""

    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.device_id = None
        self.remove = False

    async def async_step_init(self, user_input=None):
        """Entry point for managing devices (cameras)."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({
                    vol.Required("action"): vol.In({
                        "add_device": "Add New Camera",
                        "edit_device": "Edit Existing Camera",
                        "remove_device": "Remove Camera",
                    }),
                }),
            )

        if user_input["action"] == "add_device":
            return await self.async_step_add_camera()
        elif user_input["action"] == "edit_device":
            return await self.async_step_select_device()
        elif user_input["action"] == "remove_device":
            self.remove = True
            return await self.async_step_select_device(remove=True)

    async def async_step_add_camera(self, user_input=None):
        """Step to add a new camera device."""
        errors = {}
        if user_input is not None:
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"
            else:
                device_id = str(uuid.uuid4())
                new_device = {
                    "id": device_id,
                    "name": user_input.get("name", "Camera"),
                    "url": user_input[CONF_CAM_URL],
                    "detected_object": user_input[CONF_DETECTED_OBJECT],
                    "confidence_threshold": user_input[CONF_CONFIDENCE_THRESHOLD],
                    "send_notifications": user_input.get(CONF_SEND_NOTIFICATIONS, False),
                    "organize_by_day": user_input.get(CONF_ORGANIZE_BY_DAY, True),
                    "max_images": user_input.get(CONF_MAX_IMAGES, 30),
                    "time_between_requests": user_input.get(CONF_TIME_BETWEEN_REQUESTS, 30),
                }

                _LOGGER.debug(f"[HomeAIVision] Adding new device: {new_device}")

                devices = self.config_entry.data.get("devices", {})
                devices[device_id] = new_device
                # INFO: update the config entry data with the new device
                updated_data = {**self.config_entry.data, "devices": devices}

                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=updated_data
                )

                # INFO: reload the integration
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="New Camera Added", data={})

        return self.async_show_form(
            step_id="add_camera",
            data_schema=vol.Schema({
                vol.Required("name", default="Camera"): str,
                vol.Required(CONF_CAM_URL): str,
                vol.Required(CONF_DETECTED_OBJECT, default='person'): vol.In({
                    'person': "Person", 'car': "Car", 'cat': "Cat", 'dog': "Dog"
                }),
                vol.Required(CONF_CONFIDENCE_THRESHOLD, default=0.6): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=False): bool,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=True): bool,
                vol.Optional(CONF_MAX_IMAGES, default=30): int,
                vol.Optional(CONF_TIME_BETWEEN_REQUESTS, default=30): int,
            }),
            errors=errors,
        )

    async def async_step_select_device(self, user_input=None, remove=False):
        """Select a device to edit or remove."""
        devices = self.config_entry.data.get("devices", {})
        if not devices:
            return self.async_abort(reason="no_devices")

        device_options = {dev_id: dev_conf["name"] for dev_id, dev_conf in devices.items()}

        if user_input is None:
            return self.async_show_form(
                step_id="select_device",
                data_schema=vol.Schema({
                    vol.Required("device"): vol.In(device_options),
                }),
            )

        self.device_id = user_input["device"]
        if self.remove:
            return await self.async_step_remove_device()
        else:
            return await self.async_step_edit_camera()

    async def async_step_edit_camera(self, user_input=None):
        """Edit the selected camera device."""
        devices = self.config_entry.data.get("devices", {})
        device_config = devices.get(self.device_id)

        errors = {}
        if user_input is not None:
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"
            else:
                # INFO: update the device configuration
                updated_device = {
                    **device_config,
                    "name": user_input.get("name", device_config["name"]),
                    "url": user_input[CONF_CAM_URL],
                    "detected_object": user_input[CONF_DETECTED_OBJECT],
                    "confidence_threshold": user_input[CONF_CONFIDENCE_THRESHOLD],
                    "send_notifications": user_input.get(CONF_SEND_NOTIFICATIONS, device_config.get("send_notifications", False)),
                    "organize_by_day": user_input.get(CONF_ORGANIZE_BY_DAY, device_config.get("organize_by_day", True)),
                    "max_images": user_input.get(CONF_MAX_IMAGES, device_config.get("max_images", 30)),
                    "time_between_requests": user_input.get(CONF_TIME_BETWEEN_REQUESTS, device_config.get("time_between_requests", 30)),
                }
                devices = self.config_entry.data.get("devices", {})
                devices[self.device_id] = updated_device

                updated_data = {**self.config_entry.data, "devices": devices}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=updated_data
                )

                # INFO: reload the integration
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="Camera Updated", data={})

        if device_config is None:
            return self.async_abort(reason="device_not_found")

        return self.async_show_form(
            step_id="edit_camera",
            data_schema=vol.Schema({
                vol.Required("name", default=device_config.get("name", "Camera")): str,
                vol.Required(CONF_CAM_URL, default=device_config.get("url", "")): str,
                vol.Required(CONF_DETECTED_OBJECT, default=device_config.get(CONF_DETECTED_OBJECT, 'person')): vol.In({
                    'person': "Person", 'car': "Car", 'cat': "Cat", 'dog': "Dog"
                }),
                vol.Required(CONF_CONFIDENCE_THRESHOLD, default=device_config.get("confidence_threshold", 0.6)): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=device_config.get("send_notifications", False)): bool,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=device_config.get("organize_by_day", True)): bool,
                vol.Optional(CONF_MAX_IMAGES, default=device_config.get("max_images", 30)): int,
                vol.Optional(CONF_TIME_BETWEEN_REQUESTS, default=device_config.get("time_between_requests", 30)): int,
            }),
            errors=errors,
        )

    async def async_step_remove_device(self, user_input=None):
        """Remove the selected camera device."""
        devices = self.config_entry.data.get("devices", {})
        device_config = devices.pop(self.device_id, None)

        if device_config:
            updated_data = {**self.config_entry.data, "devices": devices}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_data
            )

            # INFO: Remove entities associated with the device
            entity_registry = async_get_entity_registry(self.hass)
            entries = async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)
            for entry in entries:
                if entry.unique_id.startswith(f"{self.device_id}_"):
                    entity_registry.async_remove(entry.entity_id)

            # INFO: Reload the integration
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="Camera Removed", data={})
        else:
            return self.async_abort(reason="device_not_found")
