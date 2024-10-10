# actions.py
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN
from .store import HomeAIVisionStore

_LOGGER = logging.getLogger(__name__)

# Definicje nazw akcji
ACTION_MANUAL_ANALYZE = "manual_analyze"
ACTION_RESET_LOCAL_COUNTER = "reset_local_counter"
ACTION_RESET_GLOBAL_COUNTER = "reset_global_counter"

# Schematy danych dla akcji
MANUAL_ANALYZE_SCHEMA = vol.Schema({
    vol.Required('device_id'): cv.string,
})

RESET_LOCAL_COUNTER_SCHEMA = vol.Schema({
    vol.Required('device_id'): cv.string,
})

# Implementacja funkcji obsługujących akcje
async def handle_manual_analyze(call: ServiceCall, hass: HomeAssistant):
    """Handle the manual analyze action call."""
    _LOGGER.debug(f"handle_manual_analyze called with data: {call.data}")
    device_id = call.data.get('device_id')
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']

    if not device_id:
        _LOGGER.error("[HomeAIVision] Manual Analyze action called without device_id")
        return

    device = store.get_device(device_id)
    if not device:
        _LOGGER.error(f"[HomeAIVision] Manual Analyze action called for unknown device_id: {device_id}")
        return

    # Wywołaj metodę analizy (musisz zaimplementować metodę analyze_device)
    from .camera import analyze_device  # Importuj tutaj, aby uniknąć problemów z cyklicznymi importami
    await analyze_device(hass, store, device_id)
    _LOGGER.info(f"[HomeAIVision] Manual analyze triggered for device {device_id}")

async def handle_reset_local_counter(call: ServiceCall, hass: HomeAssistant):
    """Handle the reset local counter action call."""
    device_id = call.data.get('device_id')
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']

    if not device_id:
        _LOGGER.error("[HomeAIVision] Reset Local Counter action called without device_id")
        return

    device = store.get_device(device_id)
    if not device:
        _LOGGER.error(f"[HomeAIVision] Reset Local Counter action called for unknown device_id: {device_id}")
        return

    device.device_azure_request_count = 0
    await store.async_update_device(device_id, device)
    _LOGGER.info(f"[HomeAIVision] Reset local Azure request count for device {device_id}")

    # Aktualizacja encji
    async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")

async def handle_reset_global_counter(call: ServiceCall, hass: HomeAssistant):
    """Handle the reset global counter action call."""
    store: HomeAIVisionStore = hass.data[DOMAIN]['store']
    await store.async_reset_global_counter()
    _LOGGER.info("[HomeAIVision] Reset global Azure request count")

    # Aktualizacja globalnej encji
    async_dispatcher_send(hass, f"{DOMAIN}_global_update")
