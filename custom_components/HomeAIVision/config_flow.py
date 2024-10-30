import logging
import uuid
import asyncio
import re
import aiohttp  # type: ignore
import voluptuous as vol  # type: ignore
import homeassistant.helpers.config_validation as cv  # type: ignore

from homeassistant import config_entries  # type: ignore
from homeassistant.core import callback  # type: ignore
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, async_entries_for_config_entry  # type: ignore
from homeassistant.helpers.device_registry import async_get as async_get_device_registry  # type: ignore
from homeassistant.helpers.selector import selector  # type: ignore

from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_CAM_URL,
    CONF_MAX_IMAGES_PER_DAY,
    CONF_DAYS_TO_KEEP,
    CONF_SEND_NOTIFICATIONS,
    CONF_LANGUAGE,
    CONF_TO_DETECT_OBJECT,
    CONF_AZURE_CONFIDENCE_THRESHOLD,
    CONF_INTEGRATION_TITLE,
    CONF_MOTION_DETECTION_MIN_AREA,
    CONF_MOTION_DETECTION_HISTORY_SIZE,
    CONF_MOTION_DETECTION_INTERVAL,
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
                vol.Required(CONF_LANGUAGE, default="en"): selector({
                    "select": {
                        "options": ["en", "pl", "es", "fr", "de"],
                        "translation_key": "language",
                    }
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
        self.camera_data = {} # info: temporary storage for camera data across steps

    async def async_step_init(self, user_input=None):
        self.store : HomeAIVisionStore = self.hass.data[DOMAIN]['store']
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({
                    vol.Required("action"): selector({
                        "select": {
                            "options": ["add_device", "edit_device", "remove_device"],
                            "translation_key": "action",
                        }
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
        """First step for adding a camera: Camera settings."""
        errors = {}
        NAME_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")
        if user_input is not None:
            # info: validate the camera URL
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"

            # info: validate the camera name
            camera_name = user_input.get("name")
            if not NAME_REGEX.match(camera_name):
                errors["name"] = "invalid_characters"
            elif any(device.name == camera_name for device in self.store.get_devices().values()):
                errors["name"] = "name_not_unique"

            if not errors:
                # info: store the camera data and proceed to the next step
                self.camera_data.update(user_input)
                return await self.async_step_add_camera_detection()

        return self.async_show_form(
            step_id="add_camera",
            data_schema=vol.Schema({
                vol.Required("name", default="Camera"): str,
                vol.Required(CONF_CAM_URL): str,
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=False): bool,
                vol.Optional(CONF_MAX_IMAGES_PER_DAY, default=100): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
                vol.Optional(CONF_DAYS_TO_KEEP, default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
            }),
            description_placeholders={
                "camera_settings": "Configure your camera's basic settings."
            },
            errors=errors,
        )

    async def async_step_add_camera_detection(self, user_input=None):
        """Second step for adding a camera: Detection settings."""
        errors = {}
        if user_input is not None:
            # info: Combine the detection settings with the previous camera settings
            self.camera_data.update(user_input)
            # info: All data collected, proceed to the next step
            device_id = str(uuid.uuid4())
            new_device = DeviceData(
                id=device_id,
                name=self.camera_data.get("name", "Camera"),
                url=self.camera_data[CONF_CAM_URL],
                to_detect_object=self.camera_data[CONF_TO_DETECT_OBJECT],
                azure_confidence_threshold=self.camera_data[CONF_AZURE_CONFIDENCE_THRESHOLD],
                send_notifications=self.camera_data.get(CONF_SEND_NOTIFICATIONS, False),
                max_images_per_day=self.camera_data.get(CONF_MAX_IMAGES_PER_DAY, 100),
                days_to_keep=self.camera_data.get(CONF_DAYS_TO_KEEP, 30),
                motion_detection_min_area=self.camera_data.get(CONF_MOTION_DETECTION_MIN_AREA, 6000),
                motion_detection_history_size=self.camera_data.get(CONF_MOTION_DETECTION_HISTORY_SIZE, 10),
                motion_detection_interval=self.camera_data.get(CONF_MOTION_DETECTION_INTERVAL, 5),
            )

            _LOGGER.debug(f"[HomeAIVision] Adding new device: {new_device.asdict()}")

            await self.store.async_add_device(new_device)

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="New Camera Added", data={})

        return self.async_show_form(
            step_id="add_camera_detection",
            data_schema=vol.Schema({
                vol.Required(CONF_TO_DETECT_OBJECT, default="person"): selector({
                    "select": {
                        "options": ["person", "car", "cat", "dog"],
                        "translation_key": "to_detect_object",
                    }
                }),
                vol.Required(CONF_AZURE_CONFIDENCE_THRESHOLD, default=0.6): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(CONF_MOTION_DETECTION_MIN_AREA, default=6000): vol.All(vol.Coerce(int), vol.Range(min=0)),
                vol.Optional(CONF_MOTION_DETECTION_HISTORY_SIZE, default=10): vol.All(vol.Coerce(int), vol.Range(min=2)),
                vol.Optional(CONF_MOTION_DETECTION_INTERVAL, default=5): vol.All(vol.Coerce(int), vol.Range(min=1, max=600)),
            }),
            description_placeholders={
                "detection_settings": "Configure detection settings. Advanced settings are pre-configured; change them only if necessary."
            },
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
        """First step for editing a camera: Camera settings."""
        device = self.store.get_device(self.device_id)
        errors = {}
        NAME_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")
        if user_input is not None:
            # info: validate the camera URL
            if not verify_camera_url(user_input[CONF_CAM_URL]):
                errors["base"] = "camera_url_invalid"

            # info: validate the camera name excluding the editing camera
            camera_name = user_input.get("name")
            if not NAME_REGEX.match(camera_name):
                errors["name"] = "invalid_characters"
            elif any(device.name == camera_name for device in self.store.get_devices().values() if device.id != self.device_id):
                errors["name"] = "name_not_unique"

            if not errors:
                # info: store the updated camera data and proceed to the next step
                self.camera_data.update(user_input)
                return await self.async_step_edit_camera_detection()

        if device is None:
            return self.async_abort(reason="device_not_found")

        return self.async_show_form(
            step_id="edit_camera",
            data_schema=vol.Schema({
                vol.Required("name", default=device.name): str,
                vol.Required(CONF_CAM_URL, default=device.url): str,
                vol.Optional(CONF_SEND_NOTIFICATIONS, default=device.send_notifications): bool,
                vol.Optional(CONF_MAX_IMAGES_PER_DAY, default=device.max_images_per_day): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(CONF_DAYS_TO_KEEP, default=device.days_to_keep): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }),
            description_placeholders={
                "camera_settings": "Update your camera's basic settings."
            },
            errors=errors,
        )

    async def async_step_edit_camera_detection(self, user_input=None):
        """Second step for editing a camera: Detection settings."""
        device = self.store.get_device(self.device_id)
        errors = {}
        if user_input is not None:
            # info: Combine the detection settings with the previous camera settings
            self.camera_data.update(user_input)

            updated_device = DeviceData(
                id=device.id,
                name=self.camera_data.get("name", device.name),
                url=self.camera_data[CONF_CAM_URL],
                to_detect_object=self.camera_data[CONF_TO_DETECT_OBJECT],
                azure_confidence_threshold=self.camera_data[CONF_AZURE_CONFIDENCE_THRESHOLD],
                send_notifications=self.camera_data.get(CONF_SEND_NOTIFICATIONS, device.send_notifications),
                max_images_per_day=self.camera_data.get(CONF_MAX_IMAGES_PER_DAY, device.max_images_per_day),
                days_to_keep=self.camera_data.get(CONF_DAYS_TO_KEEP, device.days_to_keep),
                motion_detection_min_area=self.camera_data.get(CONF_MOTION_DETECTION_MIN_AREA, device.motion_detection_min_area),
                motion_detection_history_size=self.camera_data.get(CONF_MOTION_DETECTION_HISTORY_SIZE, device.motion_detection_history_size,),
                motion_detection_interval=self.camera_data.get(CONF_MOTION_DETECTION_INTERVAL, device.motion_detection_interval),
            )

            await self.store.async_update_device(self.device_id, updated_device)

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="Camera Updated", data={})

        if device is None:
            return self.async_abort(reason="device_not_found")

        return self.async_show_form(
            step_id="edit_camera_detection",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_TO_DETECT_OBJECT, 
                    default=device.to_detect_object
                ): selector({
                    "select": {
                        "options": ["person", "car", "cat", "dog"],
                        "translation_key": "to_detect_object",
                    }
                }),
                vol.Required(
                    CONF_AZURE_CONFIDENCE_THRESHOLD,
                    default=device.azure_confidence_threshold,
                ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1)),
                vol.Optional(
                    CONF_MOTION_DETECTION_MIN_AREA,
                    default=device.motion_detection_min_area,
                ): vol.All(vol.Coerce(int), vol.Range(min=0)),
                vol.Optional(
                    CONF_MOTION_DETECTION_HISTORY_SIZE,
                    default=device.motion_detection_history_size,
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(
                    CONF_MOTION_DETECTION_INTERVAL,
                    default=device.motion_detection_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=600)),
            }),
            description_placeholders={
                "detection_settings": "Update detection settings. Advanced settings are pre-configured; change them only if necessary."
            },
            errors=errors,
        )

    async def async_step_remove_device(self, user_input=None):
        device = self.store.get_device(self.device_id)

        if device:
            # NOTE: Delete device from store
            await self.store.async_remove_device(self.device_id)

            # NOTE: Delete device from Device Registry
            device_registry = async_get_device_registry(self.hass)
            device_entry = device_registry.async_get_device({(DOMAIN, device.id)})

            if device_entry:
                try:
                    device_registry.async_remove_device(device_entry.id)
                except Exception as e:
                    _LOGGER.error(f"Failed to remove device {device.id}: {e}")
                    return self.async_abort(reason="remove_failed")

            # NOTE: Delete all entities associated with this device
            entity_registry = async_get_entity_registry(self.hass)
            entries = async_entries_for_config_entry(
                entity_registry, self.config_entry.entry_id
            )

            for entry in entries:
                if entry.unique_id.startswith(f"{self.device_id}_"):
                    entity_registry.async_remove(entry.entity_id)

            # NOTE: Cancel and remove the associated camera task
            camera_tasks = self.hass.data[DOMAIN].get('camera_tasks', {})
            task_tuple = camera_tasks.pop(self.device_id, None)
            if task_tuple:
                task, stop_event = task_tuple
                stop_event.set()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    _LOGGER.debug(f"[HomeAIVision] Camera task for device {self.device_id} successfully cancelled.")
                except Exception as e:
                    _LOGGER.error(f"[HomeAIVision] Error cancelling camera task for device {self.device_id}: {e}")

            return self.async_create_entry(title="Camera Removed", data={})
        else:
            return self.async_abort(reason="device_not_found")
