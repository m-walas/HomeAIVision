import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .store import HomeAIVisionStore
from .entities import CameraUrlEntity, ConfidenceThresholdEntity, DetectedObjectEntity, AzureRequestCountEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors for HomeAIVision integration."""
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    devices = store.get_devices()

    entities = []
    for device_data in devices.values():
        device_config = device_data.asdict()
        # _LOGGER.debug(f"[HomeAIVision] Setting up entities for device: {device_config}")
        entities.extend([
            # NOTE: ONLY sensor entities
            AzureRequestCountEntity(hass, device_config),
            CameraUrlEntity(hass, device_config),
        ])

    if entities:
        async_add_entities(entities)
        hass.data[DOMAIN].setdefault('entities', []).extend(entities)
        # _LOGGER.debug(f"[HomeAIVision] Added entities: {[entity.name for entity in entities]}")
    else:
        _LOGGER.warning("[HomeAIVision] No sensor entities to add.")
