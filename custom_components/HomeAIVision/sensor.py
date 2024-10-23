import logging

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore

from .const import DOMAIN
from .store import HomeAIVisionStore
from .entities import (
    CameraUrlEntity,
    GlobalAzureRequestCountEntity,
    AzureRequestCountEntity,
    DeviceIdEntity,
    NotificationEntity
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """
    Set up sensor entities for the HomeAIVision integration from a config entry.
    
    This function initializes and adds sensor entities related to Azure request counts,
    camera diagnostics, device identification, and notification status for each configured
    device in the HomeAIVision integration.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for the integration.
        async_add_entities (callable): The function to add entities to Home Assistant.
    """
    # INFO: Retrieve the store instance from Home Assistant data
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    if not store:
        _LOGGER.error("[HomeAIVision] Store not found in hass.data")
        return
    devices = store.get_devices()

    entities = []
    # NOTE: Initialize the global Azure request count sensor once
    global_sensor = GlobalAzureRequestCountEntity(hass)
    entities.append(global_sensor)

    for device_data in devices.values():
        device_config = device_data.asdict()
        _LOGGER.debug(f"[HomeAIVision] Setting up sensor entities for device: {device_config}")
        entities.extend([
            # IMPORTANT: Only sensor entities are being set up here
            AzureRequestCountEntity(hass, device_config),
            # NOTE: Add diagnostic sensor entities
            CameraUrlEntity(hass, device_config),
            DeviceIdEntity(hass, device_config),
            NotificationEntity(hass, device_config),
        ])

    if entities:
        # INFO: Add the configured sensor entities to Home Assistant
        async_add_entities(entities)
        hass.data[DOMAIN].setdefault('entities', []).extend(entities)
        _LOGGER.debug(f"[HomeAIVision] Added sensor entities: {[entity.name for entity in entities]}")
    else:
        # WARNING: No sensor entities were found to add
        _LOGGER.warning("[HomeAIVision] No sensor entities to add.")
