import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entities import CameraUrlEntity, ConfidenceThresholdEntity, DetectedObjectEntity, AzureRequestCountEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors for HomeAIVision integration."""
    _LOGGER.debug(f"[HomeAIVision] async_setup_entry called with entry: {entry.data}")
    devices = entry.data.get("devices", {})

    entities = []
    for device_config in devices.values():
        _LOGGER.debug(f"[HomeAIVision] Setting up entities for device: {device_config}")
        entities.extend([
            CameraUrlEntity(hass, device_config, entry),
            ConfidenceThresholdEntity(hass, device_config, entry),
            DetectedObjectEntity(hass, device_config, entry),
            AzureRequestCountEntity(hass, device_config, entry),
        ])

    if entities:
        async_add_entities(entities)
        hass.data[DOMAIN].setdefault('entities', []).extend(entities)
        _LOGGER.debug(f"[HomeAIVision] Added entities: {[entity.name for entity in entities]}")
    else:
        _LOGGER.debug("[HomeAIVision] No entities to add.")
