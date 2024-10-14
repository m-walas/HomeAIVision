import logging

from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore
from .entities import ConfidenceThresholdEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up number entities for HomeAIVision integration."""
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    devices = store.get_devices()

    entities = []
    for device_data in devices.values():
        device_config = device_data.asdict()
        _LOGGER.debug(f"[HomeAIVision] Setting up number entities for device: {device_config}")
        entities.extend([
            # NOTE: ONLY number entities
            ConfidenceThresholdEntity(hass, device_config),
        ])

    if entities:
        async_add_entities(entities)
        _LOGGER.debug(f"[HomeAIVision] Added number entities: {[entity.name for entity in entities]}")
    else:
        _LOGGER.warning("[HomeAIVision] No number entities to add.")
