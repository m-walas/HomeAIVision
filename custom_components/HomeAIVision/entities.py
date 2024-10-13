import logging

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import Entity, EntityCategory

from .const import DOMAIN
from .store import HomeAIVisionStore

_LOGGER = logging.getLogger(__name__)


class BaseHomeAIVisionEntity(Entity):
    """Base class for HomeAIVision entities."""

    def __init__(self, hass, device_config):
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

# NOTE: Sensor entities
class AzureRequestCountEntity(BaseHomeAIVisionEntity, SensorEntity):
    """Entity representing the Azure request count."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_azure_request_count"
        self._attr_name = f"{self._device_name} Azure Request Count"

    @property
    def icon(self):
        return "mdi:counter"

    @property
    def state(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.device_azure_request_count
        return None

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self._device_id}_update", self.async_write_ha_state
            )
        )


class CameraUrlEntity(BaseHomeAIVisionEntity, SensorEntity):
    """Entity representing the camera URL."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_camera_url"
        self._attr_name = f"{self._device_name} Camera URL"

    @property
    def icon(self):
        return "mdi:link"

    @property
    def state(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.url
        return None


# NOTE: Configuration entities
class ConfidenceThresholdEntity(BaseHomeAIVisionEntity, NumberEntity):
    """Entity representing the detection confidence threshold."""
    
    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_confidence_threshold"
        self._attr_name = f"{self._device_name} Confidence Threshold"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_min_value = 0.1
        self._attr_native_max_value = 1.0
        self._attr_native_step = 0.01
        self._attr_mode = 'slider'

    @property
    def native_value(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.confidence_threshold
        return None

    async def async_set_native_value(self, value: float):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            device_data.confidence_threshold = value
            await self.store.async_update_device(self._device_id, device_data)
            self.async_write_ha_state()


class DetectedObjectEntity(BaseHomeAIVisionEntity, SelectEntity):
    """Entity representing the detected object."""
    
    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_detected_object"
        self._attr_name = f"{self._device_name} Detected Object"
        self._attr_entity_category = EntityCategory.CONFIG
        self._options = ['person', 'car', 'cat', 'dog']

    @property
    def options(self):
        """Return a set of selectable options."""
        return self._options

    @property
    def current_option(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.to_detect_object
        return None

    async def async_select_option(self, option: str):
        if option in self._options:
            device_data = self.store.get_device(self._device_id)
            if device_data:
                device_data.to_detect_object = option
                await self.store.async_update_device(self._device_id, device_data)
                self.async_write_ha_state()
        else:
            _LOGGER.error(f"Invalid option selected: {option}")

# NOTE: Global sensor entities
class GlobalAzureRequestCountEntity(SensorEntity):
    """Entity representing the global Azure request count."""

    def __init__(self, hass):
        """Initialize the global Azure request count entity."""
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
        return "mdi:counter"

    @property
    def state(self):
        """Return the state of the global Azure request count."""
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
