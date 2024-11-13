import logging
import asyncio

from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore
from homeassistant.components.sensor import SensorEntity  # type: ignore
from homeassistant.components.number import NumberEntity  # type: ignore
from homeassistant.components.select import SelectEntity  # type: ignore
from homeassistant.components.switch import SwitchEntity  # type: ignore
from homeassistant.helpers.entity import Entity, EntityCategory  # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore
from .camera_processing import periodic_check

_LOGGER = logging.getLogger(__name__)


class BaseHomeAIVisionEntity(Entity):
    """Base class for HomeAIVision entities."""

    def __init__(self, hass, device_config):
        """
        Initialize the base entity for HomeAIVision.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        self.hass = hass
        self.store: HomeAIVisionStore = hass.data[DOMAIN]['store']
        self._device_id = device_config['id']
        self._device_name = device_config['name']
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "HomeAIVision",
            "model": "Intelligent Camera",
        }


# INFO: Important entity for arm/disarm functionality
class ArmedSwitchEntity(BaseHomeAIVisionEntity, SwitchEntity):
    """Entity representing the armed state of the camera."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_armed"
        self._attr_name = f"{self._device_name} Armed"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self):
        """Return True if the device is armed."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.armed
        return False

    async def async_turn_on(self, **kwargs):
        """Arm the device."""
        device_data = self.store.get_device(self._device_id)
        if device_data and not device_data.armed:
            device_data.armed = True
            await self.store.async_update_device(self._device_id, device_data)
            self.async_write_ha_state()
            # info: Start the periodic check task
            if self._device_id not in self.hass.data[DOMAIN]['camera_tasks']:
                stop_event = asyncio.Event()
                config_entry = self.hass.config_entries.async_get_entry(device_data.config_entry_id)
                if not config_entry:
                    _LOGGER.error(f"[HomeAIVision] Config entry not found for device {self._device_id}")
                    return
                task = self.hass.async_create_task(
                    periodic_check(self.hass, config_entry, device_data.asdict(), stop_event)
                )
                self.hass.data[DOMAIN]['camera_tasks'][self._device_id] = (task, stop_event)
                _LOGGER.debug(f"[HomeAIVision] Armed camera {self._device_id}, task started.")

    async def async_turn_off(self, **kwargs):
        """Disarm the device."""
        device_data = self.store.get_device(self._device_id)
        if device_data and device_data.armed:
            device_data.armed = False
            await self.store.async_update_device(self._device_id, device_data)
            self.async_write_ha_state()
            # info: Cancel the periodic check task
            camera_tasks = self.hass.data[DOMAIN].get('camera_tasks', {})
            task_tuple = camera_tasks.pop(self._device_id, None)
            if task_tuple:
                task, stop_event = task_tuple
                stop_event.set()
                task.cancel()
                _LOGGER.debug(f"[HomeAIVision] Disarmed camera {self._device_id}, task cancelled.")


# INFO: Sensor entities
class AzureRequestCountEntity(BaseHomeAIVisionEntity, SensorEntity):
    """Entity representing the Azure request count."""

    def __init__(self, hass, device_config):
        """
        Initialize the AzureRequestCountEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_azure_request_count"
        self._attr_name = f"{self._device_name} Azure Request Count"

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:counter"

    @property
    def state(self):
        """Return the current Azure request count."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.device_azure_request_count
        return None

    async def async_added_to_hass(self):
        """Handle addition of the entity to Home Assistant."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self._device_id}_update", self.async_write_ha_state
            )
        )


# INFO: Diagnostic entities
class CameraUrlEntity(BaseHomeAIVisionEntity, SensorEntity):
    """Entity representing the camera URL."""

    def __init__(self, hass, device_config):
        """
        Initialize the CameraUrlEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_camera_url"
        self._attr_name = f"{self._device_name} Camera URL"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:link"

    # IMPORTANT: Censor the camera URL for privacy
    """
    Return a censored URL of the camera for privacy.
    Currently returns only the IP address and port number of the camera.
    Works with URLs in the format http://<IP>:<PORT>/<rest of the URL>.
    Most cameras use this URL format.
    Please report an issue if an additional case is needed.
    """
    @property
    def state(self):
        """Return the censored camera URL."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            url = device_data.url
            if url:
                try:
                    url = url.split("//")[1]
                    url = url.split("/")[0]
                    url = url.split(":")
                    url = f"{url[0]}:{url[1]}***"
                    return url
                except IndexError:
                    _LOGGER.error(f"[HomeAIVision] Invalid URL format for device {self._device_id}")
                    return "Invalid URL"
        return None


class DeviceIdEntity(BaseHomeAIVisionEntity, SensorEntity):
    """Entity representing the device ID."""

    def __init__(self, hass, device_config):
        """
        Initialize the DeviceIdEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_device_id"
        self._attr_name = f"{self._device_name} Device ID"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:information"

    @property
    def state(self):
        """Return the device ID."""
        return self._device_id


class NotificationEntity(BaseHomeAIVisionEntity, SensorEntity):
    """
    Entity representing the notification status.
    On/Off state of the notification.
    """

    def __init__(self, hass, device_config):
        """
        Initialize the NotificationEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_notification"
        self._attr_name = f"{self._device_name} Notification"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:bell"

    # NOTE: If the notification state is True, return 'On' else 'Off'
    @property
    def state(self):
        """Return the notification status as 'On' or 'Off'."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return "On" if device_data.send_notifications else "Off"
        return None


class MaxImagesPerDayEntity(BaseHomeAIVisionEntity, SensorEntity):
    """Entity representing the maximum images per day for the device."""

    def __init__(self, hass, device_config):
        """
        Initialize the MaxImagesPerDayEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_max_images_per_day"
        self._attr_name = f"{self._device_name} Max Images Per Day"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:camera"

    @property
    def state(self):
        """Return the maximum images per day."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.max_images_per_day
        return None


# INFO: Configuration entities
class ConfidenceThresholdEntity(BaseHomeAIVisionEntity, NumberEntity):
    """Entity representing the detection confidence threshold."""
    
    def __init__(self, hass, device_config):
        """
        Initialize the ConfidenceThresholdEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_azure_confidence_threshold"
        self._attr_name = f"{self._device_name} Confidence Threshold"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_min_value = 0.1
        self._attr_native_max_value = 1.0
        self._attr_native_step = 0.01
        self._attr_mode = 'number'

    @property
    def native_value(self):
        """Return the current confidence threshold."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.azure_confidence_threshold
        return None

    async def async_set_native_value(self, value: float):
        """
        Set a new confidence threshold value.

        Args:
            value (float): The new confidence threshold.
        """
        device_data = self.store.get_device(self._device_id)
        if device_data:
            device_data.azure_confidence_threshold = value
            await self.store.async_update_device(self._device_id, device_data)
            self.async_write_ha_state()


class MotionDetectionIntervalEntity(BaseHomeAIVisionEntity, NumberEntity):
    """Entity representing the motion detection interval."""
    
    def __init__(self, hass, device_config):
        """
        Initialize the MotionDetectionIntervalEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_motion_detection_interval"
        self._attr_name = f"{self._device_name} Motion Detection Interval"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_min_value = 1
        self._attr_native_max_value = 600
        self._attr_native_step = 1
        self._attr_mode = 'slider'

    @property
    def native_value(self):
        """Return the current motion detection interval."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.motion_detection_interval
        return None

    async def async_set_native_value(self, value: int):
        """
        Set a new motion detection interval value.

        Args:
            value (int): The new motion detection interval.
        """
        device_data = self.store.get_device(self._device_id)
        if device_data:
            device_data.motion_detection_interval = value
            await self.store.async_update_device(self._device_id, device_data)
            self.async_write_ha_state()


class DetectedObjectEntity(BaseHomeAIVisionEntity, SelectEntity):
    """Entity representing the detected object."""
    
    def __init__(self, hass, device_config):
        """
        Initialize the DetectedObjectEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
            device_config (dict): Configuration parameters for the device.
        """
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_detected_object"
        self._attr_name = f"{self._device_name} Detected Object"
        self._attr_entity_category = EntityCategory.CONFIG
        self._options = ['person', 'car', 'cat', 'dog']

    @property
    def options(self):
        """Return a list of selectable options."""
        return self._options

    @property
    def current_option(self):
        """Return the currently selected detected object."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.to_detect_object
        return None

    async def async_select_option(self, option: str):
        """
        Select a new detected object option.

        Args:
            option (str): The selected option.
        """
        if option in self._options:
            device_data = self.store.get_device(self._device_id)
            if device_data:
                device_data.to_detect_object = option
                await self.store.async_update_device(self._device_id, device_data)
                self.async_write_ha_state()
        else:
            _LOGGER.error(f"Invalid option selected: {option}")


class LocalSensitivityLevelEntity(BaseHomeAIVisionEntity, SelectEntity):
    """Entity representing the local sensitivity level."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_local_sensitivity_level"
        self._attr_name = f"{self._device_name} Local Sensitivity Level"
        self._attr_entity_category = EntityCategory.CONFIG
        self._options = ['low', 'medium', 'high']

    @property
    def options(self):
        """Return a list of selectable options."""
        return self._options

    @property
    def current_option(self):
        """Return the currently selected sensitivity level."""
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.local_sensitivity_level
        return None

    async def async_select_option(self, option: str):
        """Set a new sensitivity level option."""
        if option in self._options:
            device_data = self.store.get_device(self._device_id)
            if device_data:
                device_data.local_sensitivity_level = option
                await self.store.async_update_device(self._device_id, device_data)
                self.async_write_ha_state()
        else:
            _LOGGER.error(f"Invalid local sensitivity level selected: {option}")


# INFO: Global sensor entities
class GlobalAzureRequestCountEntity(SensorEntity):
    """Entity representing the global Azure request count."""

    def __init__(self, hass):
        """
        Initialize the GlobalAzureRequestCountEntity.

        Args:
            hass (HomeAssistant): The Home Assistant instance.
        """
        super().__init__()
        self.hass = hass
        try:
            self.store: HomeAIVisionStore = hass.data[DOMAIN]['store']
        except KeyError:
            _LOGGER.error("[HomeAIVision] Store not found in hass.data")
            self.store = None
        self._attr_unique_id = f"{DOMAIN}_global_azure_request_count"
        self._attr_name = "Global Azure Request Count"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "global")},
            "name": "HomeAIVision",
            "manufacturer": "HomeAIVision",
            "model": "Intelligent Camera",
        }

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:counter"

    @property
    def state(self):
        """Return the global Azure request count."""
        if self.store:
            return self.store.get_global_counter()
        return None

    async def async_added_to_hass(self):
        """Handle addition of the entity to Home Assistant."""
        if self.store:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass, f"{DOMAIN}_global_update", self.async_write_ha_state
                )
            )
        else:
            _LOGGER.error("[HomeAIVision] Cannot add dispatcher because store is None")
