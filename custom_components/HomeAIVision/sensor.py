import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .store import HomeAIVisionStore
from .entities import CameraUrlEntity, GlobalAzureRequestCountEntity, AzureRequestCountEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors for HomeAIVision integration."""
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    if not store:
        _LOGGER.error("[HomeAIVision] Store not found in hass.data")
        return
    devices = store.get_devices()

    entities = []
    # NOTE: Initialize the global sensor once
    global_sensor = GlobalAzureRequestCountEntity(hass)
    entities.append(global_sensor)

    for device_data in devices.values():
        device_config = device_data.asdict()
        entities.extend([
            # IMPORTANT: Only sensor entities
            AzureRequestCountEntity(hass, device_config),
            CameraUrlEntity(hass, device_config),
        ])

    if entities:
        async_add_entities(entities)
        hass.data[DOMAIN].setdefault('entities', []).extend(entities)
    else:
        _LOGGER.warning("[HomeAIVision] No sensor entities to add.")
