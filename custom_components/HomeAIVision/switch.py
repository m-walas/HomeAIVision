import logging

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore
from .entities import ArmedSwitchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """
    Set up switch entities for the HomeAIVision integration from a config entry.

    This function initializes and adds switch entities related to arming/disarming
    for each configured device in the HomeAIVision integration.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for the integration.
        async_add_entities (callable): The function to add entities to Home Assistant.
    """
    # NOTE: Retrieve the store instance from Home Assistant data
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    if not store:
        _LOGGER.error("[HomeAIVision] Store not found in hass.data")
        return

    devices = store.get_devices()

    entities = []
    for device_data in devices.values():
        device_config = device_data.asdict()
        _LOGGER.debug(f"[HomeAIVision] Setting up switch entity for device: {device_config}")
        
        entities.append(ArmedSwitchEntity(hass, device_config))

    if entities:
        # info: Add the configured switch entities to Home Assistant
        async_add_entities(entities)
        _LOGGER.debug(f"[HomeAIVision] Added switch entities: {[entity.name for entity in entities]}")
    else:
        # WARNING: Warn if no switch entities were found to add
        _LOGGER.warning("[HomeAIVision] No switch entities to add.")
