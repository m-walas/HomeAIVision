import os
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START

from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_CAM_URL,
    CONF_MAX_IMAGES,
    CONF_TIME_BETWEEN_REQUESTS,
    CONF_ORGANIZE_BY_DAY,
    CONF_DAYS_TO_KEEP,
    CONF_SEND_NOTIFICATIONS,
    CONF_NOTIFICATION_LANGUAGE,
    CONF_DETECTED_OBJECT,
    CONF_CONFIDENCE_THRESHOLD,
    CONF_INTEGRATION_TITLE,
)
from .camera import setup_periodic_camera_check
from .mod_view import async_setup_view
from .image_api import ImageListView

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        "organize_by_day": entry.data.get(CONF_ORGANIZE_BY_DAY, False),
        "days_to_keep": entry.data.get(CONF_DAYS_TO_KEEP, 7),
        "max_images": entry.data.get(CONF_MAX_IMAGES, 30),
        "time_between_requests": entry.data.get(CONF_TIME_BETWEEN_REQUESTS, 30),
        "send_notifications": entry.data.get(CONF_SEND_NOTIFICATIONS, False),
        "notification_language": entry.data.get(CONF_NOTIFICATION_LANGUAGE, "en"),
        "detected_object": entry.data.get(CONF_DETECTED_OBJECT, "person"),
        "confidence_threshold": entry.data.get(CONF_CONFIDENCE_THRESHOLD, 0.6),
        "integration_title": entry.data.get(CONF_INTEGRATION_TITLE, "Home AI Vision"),
        "azure_api_key": entry.data.get(CONF_AZURE_API_KEY),
        "azure_endpoint": entry.data.get(CONF_AZURE_ENDPOINT),
        "cam_url": entry.data.get(CONF_CAM_URL),
        "azure_request_count": entry.data.get("azure_request_count", 0),
    }

    hass.http.register_view(ImageListView)

    await async_setup_view(hass)

    async def start_camera_analysis(event):
        await setup_periodic_camera_check(hass, entry)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_camera_analysis)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "binary_sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
