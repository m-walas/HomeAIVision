import logging

from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore
from homeassistant.components.sensor import SensorEntity  # type: ignore
from homeassistant.components.number import NumberEntity  # type: ignore
from homeassistant.components.select import SelectEntity  # type: ignore
from homeassistant.helpers.entity import Entity, EntityCategory  # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore

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
        self._attr_mode = 'slider'

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
