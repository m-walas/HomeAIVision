import logging

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore
from .entities import DetectedObjectEntity, LocalSensitivityLevelEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """
    Set up select entities for the HomeAIVision integration from a config entry.
    
    This function initializes and adds select entities related to detected objects
    for each configured device in the HomeAIVision integration.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for the integration.
        async_add_entities (callable): The function to add entities to Home Assistant.
    """
    # INFO: Retrieve the store instance from Home Assistant data
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    devices = store.get_devices()

    entities = []
    for device_data in devices.values():
        device_config = device_data.asdict()
        _LOGGER.debug(f"[HomeAIVision] Setting up select entities for device: {device_config}")
        
        entities.extend([
            # NOTE: ONLY select entities are being set up here
            DetectedObjectEntity(hass, device_config),
            LocalSensitivityLevelEntity(hass, device_config),
        ])

    if entities:
        # INFO: Add the configured select entities to Home Assistant
        async_add_entities(entities)
        _LOGGER.debug(f"[HomeAIVision] Added select entities: {[entity.name for entity in entities]}")
    else:
        # WARNING: No select entities were found to add
        _LOGGER.warning("[HomeAIVision] No select entities to add.")
