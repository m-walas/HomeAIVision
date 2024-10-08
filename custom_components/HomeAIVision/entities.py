from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .store import HomeAIVisionStore

class BaseHomeAIVisionEntity(SensorEntity):
    """Podstawowa klasa dla encji HomeAIVision."""

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

class CameraUrlEntity(BaseHomeAIVisionEntity):
    """Encja reprezentująca URL kamery."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_camera_url"

    @property
    def name(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return f"{device_data.name} Camera URL"
        return "Unknown Camera URL"

    @property
    def state(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.url
        return None

class ConfidenceThresholdEntity(BaseHomeAIVisionEntity):
    """Encja reprezentująca próg pewności detekcji."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_confidence_threshold"

    @property
    def name(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return f"{device_data.name} Confidence Threshold"
        return "Unknown Confidence Threshold"

    @property
    def state(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.confidence_threshold
        return None

class DetectedObjectEntity(BaseHomeAIVisionEntity):
    """Encja reprezentująca wykrywany obiekt."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_detected_object"

    @property
    def name(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return f"{device_data.name} Detected Object"
        return "Unknown Detected Object"

    @property
    def state(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return device_data.detected_object
        return None

class AzureRequestCountEntity(BaseHomeAIVisionEntity, RestoreEntity):
    """Encja reprezentująca licznik zapytań do Azure."""

    def __init__(self, hass, device_config):
        super().__init__(hass, device_config)
        self._attr_unique_id = f"{self._device_id}_azure_request_count"
        self._state = 0

    @property
    def name(self):
        device_data = self.store.get_device(self._device_id)
        if device_data:
            return f"{device_data.name} Azure Request Count"
        return "Unknown Azure Request Count"

    @property
    def state(self):
        return self._state

    async def async_added_to_hass(self):
        """Obsługa dodania encji do Home Assistant."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state and state.state not in ('unknown', None):
            try:
                self._state = int(state.state)
            except ValueError:
                self._state = 0
        else:
            self._state = 0
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self._device_id}_update", self._handle_update
            )
        )

    @callback
    def _handle_update(self):
        """Obsługa aktualizacji z procesu analizy kamery."""
        self._state = self.hass.data.get(DOMAIN, {}).get('azure_request_counts', {}).get(self._device_id, 0)
        self.async_write_ha_state()
