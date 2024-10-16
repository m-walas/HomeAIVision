import logging
import uuid
import aiohttp # type: ignore
import voluptuous as vol # type: ignore 
import homeassistant.helpers.config_validation as cv # type: ignore

from homeassistant import config_entries # type: ignore
from homeassistant.core import callback # type: ignore 
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_config_entry # type: ignore
from homeassistant.helpers.device_registry import async_get as async_get_device_registry # type: ignore

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
    CONF_LANGUAGE,
    CONF_TO_DETECT_OBJECT,
    CONF_CONFIDENCE_THRESHOLD,
    CONF_INTEGRATION_TITLE,
)

from .store import HomeAIVisionStore, DeviceData

_LOGGER = logging.getLogger(__name__)


async def verify_azure_credentials(azure_api_key, azure_endpoint):
    headers = {'Ocp-Apim-Subscription-Key': azure_api_key}
    test_url = azure_endpoint.rstrip("/") + "/vision/v3.0/analyze"
    async with aiohttp.ClientSession() as session:
        async with session.post(test_url, headers=headers) as response:
            return response.status != 401


def verify_camera_url(cam_url):
    return cam_url.startswith("http://") or cam_url.startswith("https://")


class HomeAIVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    temp_config = {}

    async def async_step_user(self, user_input=None):
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
                        CONF_LANGUAGE: self.temp_config.get(CONF_LANGUAGE, "en"),
                        "devices": {},
                        "global": {
                            "global_azure_request_count": 0,
                            "language": self.temp_config.get(CONF_LANGUAGE, "en"),
                        },
                    }
                )

        return self.async_show_form(
            step_id="azure_conf",
            data_schema=vol.Schema({
                vol.Required(CONF_AZURE_API_KEY): str,
                vol.Required(CONF_AZURE_ENDPOINT): str,
                vol.Required(CONF_LANGUAGE, default="en"): vol.In({
                    "en": "English",
                    "pl": "Polski",
                    "es": "Español",
                    "fr": "Français",
                    "de": "Deutsch",
                }),
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HomeAIVisionOptionsFlow(config_entry)


class HomeAIVisionOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.device_id = None
        self.remove = False

    async def async_step_init(self, user_input=None):
        self.store : HomeAIVisionStore = self.hass.data[DOMAIN]['store']
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
            return await self.async_step_select_device()

    async def async_step_add_camera(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"
            else:
                device_id = str(uuid.uuid4())
                new_device = DeviceData(
                    id=device_id,
                    name=user_input.get("name", "Camera"),
                    url=user_input[CONF_CAM_URL],
                    to_detect_object=user_input[CONF_TO_DETECT_OBJECT],
                    confidence_threshold=user_input[CONF_CONFIDENCE_THRESHOLD],
                    send_notifications=user_input.get(CONF_SEND_NOTIFICATIONS, False),
                    organize_by_day=user_input.get(CONF_ORGANIZE_BY_DAY, True),
                    max_images=user_input.get(CONF_MAX_IMAGES, 30),
                    time_between_requests=user_input.get(CONF_TIME_BETWEEN_REQUESTS, 30),
                )

                _LOGGER.debug(f"[HomeAIVision] Adding new device: {new_device.asdict()}")

                await self.store.async_add_device(new_device)

                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="New Camera Added", data={})

        return self.async_show_form(
            step_id="add_camera",
            data_schema=vol.Schema({
                vol.Required("name", default="Camera"): str,
                vol.Required(CONF_CAM_URL): str,
                vol.Required(CONF_TO_DETECT_OBJECT, default='person'): vol.In({
                    'person': "Person", 'car': "Car", 'cat': "Cat", 'dog': "Dog"
                }),
                vol.Required(CONF_CONFIDENCE_THRESHOLD, default=0.6): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=False): bool,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=True): bool,
                vol.Optional(CONF_MAX_IMAGES, default=30): int,
                vol.Optional(CONF_TIME_BETWEEN_REQUESTS, default=30): int,
                vol.Optional(CONF_DAYS_TO_KEEP, default=7): int,
            }),
            errors=errors,
        )

    async def async_step_select_device(self, user_input=None):
        devices = self.store.get_devices()
        if not devices:
            return self.async_abort(reason="no_devices")

        device_options = {dev_id: dev_conf.name for dev_id, dev_conf in devices.items()}

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
        device = self.store.get_device(self.device_id)

        errors = {}
        if user_input is not None:
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"
            else:
                updated_device = DeviceData(
                    id=device.id,
                    name=user_input.get("name", device.name),
                    url=user_input[CONF_CAM_URL],
                    to_detect_object=user_input[CONF_TO_DETECT_OBJECT],
                    confidence_threshold=user_input[CONF_CONFIDENCE_THRESHOLD],
                    send_notifications=user_input.get(CONF_SEND_NOTIFICATIONS, device.send_notifications),
                    organize_by_day=user_input.get(CONF_ORGANIZE_BY_DAY, device.organize_by_day),
                    max_images=user_input.get(CONF_MAX_IMAGES, device.max_images),
                    time_between_requests=user_input.get(CONF_TIME_BETWEEN_REQUESTS, device.time_between_requests),
                )

                await self.store.async_update_device(self.device_id, updated_device)

                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="Camera Updated", data={})

        if device is None:
            return self.async_abort(reason="device_not_found")

        return self.async_show_form(
            step_id="edit_camera",
            data_schema=vol.Schema({
                vol.Required("name", default=device.name): str,
                vol.Required(CONF_CAM_URL, default=device.url): str,
                vol.Required(CONF_TO_DETECT_OBJECT, default=device.to_detect_object): vol.In({
                    'person': "Person", 'car': "Car", 'cat': "Cat", 'dog': "Dog"
                }),
                vol.Required(CONF_CONFIDENCE_THRESHOLD, default=device.confidence_threshold): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=device.send_notifications): bool,
                vol.Optional(CONF_ORGANIZE_BY_DAY, default=device.organize_by_day): bool,
                vol.Optional(CONF_MAX_IMAGES, default=device.max_images): int,
                vol.Optional(CONF_TIME_BETWEEN_REQUESTS, default=device.time_between_requests): int,
                vol.Optional(CONF_DAYS_TO_KEEP, default=device.days_to_keep): int,
            }),
            errors=errors,
        )

    async def async_step_remove_device(self, user_input=None):
        device = self.store.get_device(self.device_id)

        if device:
            # NOTE: Delete device from store
            await self.store.async_remove_device(self.device_id)

            # NOTE: Delete device from Device Registry
            device_registry = async_get_device_registry(self.hass)
            device_entry = device_registry.async_get(device.id)

            if device_entry:
                try:
                    device_registry.async_remove_device(device_entry.id)
                except Exception as e:
                    _LOGGER.error(f"Failed to remove device {device.id}: {e}")
                    return self.async_abort(reason="remove_failed")

            # NOTE: Delete all entities associated with this device
            entity_registry = async_get_entity_registry(self.hass)
            entries = async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)

            for entry in entries:
                if entry.unique_id.startswith(f"{self.device_id}_"):
                    entity_registry.async_remove(entry.entity_id)

            return self.async_create_entry(title="Camera Removed", data={})
        else:
            return self.async_abort(reason="device_not_found")
