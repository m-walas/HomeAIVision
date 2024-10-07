from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN

class CameraUrlEntity(SensorEntity):
    def __init__(self, hass, device_config, config_entry):
        self.hass = hass
        self._config_entry = config_entry
        self._device_id = device_config['id']
        self._attr_unique_id = f"{self._device_id}_camera_url"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_config['name'],
            "manufacturer": "HomeAIVision",
            "model": "Intelligent Camera",
        }

    @property
    def name(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return f"{device_config.get('name', 'Camera')} Camera URL"
    
    @property
    def state(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return device_config.get("url")
    
    @property
    def unique_id(self):
        return self._attr_unique_id

class ConfidenceThresholdEntity(SensorEntity):
    def __init__(self, hass, device_config, config_entry):
        self.hass = hass
        self._config_entry = config_entry
        self._device_id = device_config['id']
        self._attr_unique_id = f"{self._device_id}_confidence_threshold"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_config['name'],
            "manufacturer": "HomeAIVision",
            "model": "Intelligent Camera",
        }

    @property
    def name(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return f"{device_config.get('name', 'Camera')} Confidence Threshold"

    @property
    def state(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return device_config.get("confidence_threshold")
    
    @property
    def unique_id(self):
        return self._attr_unique_id

class DetectedObjectEntity(SensorEntity):
    def __init__(self, hass, device_config, config_entry):
        self.hass = hass
        self._config_entry = config_entry
        self._device_id = device_config['id']
        self._attr_unique_id = f"{self._device_id}_detected_object"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_config['name'],
            "manufacturer": "HomeAIVision",
            "model": "Intelligent Camera",
        }

    @property
    def name(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return f"{device_config.get('name', 'Camera')} Detected Object"

    @property
    def state(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return device_config.get("detected_object")
    
    @property
    def unique_id(self):
        return self._attr_unique_id

class AzureRequestCountEntity(SensorEntity, RestoreEntity):
    def __init__(self, hass, device_config, config_entry):
        self.hass = hass
        self._config_entry = config_entry
        self._device_id = device_config['id']
        self._attr_unique_id = f"{self._device_id}_azure_request_count"
        self._state = 0
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_config['name'],
            "manufacturer": "HomeAIVision",
            "model": "Intelligent Camera",
        }

    @property
    def name(self):
        device_config = self._config_entry.data.get('devices', {}).get(self._device_id, {})
        return f"{device_config.get('name', 'Camera')} Azure Request Count"

    @property
    def state(self):
        return self._state
    
    @property
    def unique_id(self):
        return self._attr_unique_id

    async def async_added_to_hass(self):
        """Restore previous state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state and state.state != 'unknown':
            self._state = int(state.state)
        else:
            self._state = 0

        # Register dispatcher signal for updates
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self._device_id}_update", self._handle_update
            )
        )

    @callback
    def _handle_update(self):
        """Handle state update."""
        # Retrieve the updated count from hass.data
        self._state = self.hass.data.get(DOMAIN, {}).get('azure_request_counts', {}).get(self._device_id, 0)
        self.async_write_ha_state()
