from homeassistant.components.frontend import add_extra_js_url
from .const import FRONTEND_SCRIPT_URL, DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_view(hass):
    """
    Sets up the HomeAIVision view in Home Assistant.
    """

    _LOGGER.debug("[HomeAIVision] Registering static path for HomeAIVision panel")

    try:
        hass.http.register_static_path(
            FRONTEND_SCRIPT_URL,
            hass.config.path("custom_components/HomeAIVision/homeaivision_panel.js"),
        )
        resources = hass.data.get("lovelace", {}).get("resources", None)
        if resources:
            already_added = any(r["url"].startswith(FRONTEND_SCRIPT_URL) for r in resources.async_items())
            if not already_added:
                add_extra_js_url(hass, FRONTEND_SCRIPT_URL)
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Failed to register static path: {e}")
        return

    try:
        hass.components.frontend.async_register_built_in_panel(
            component_name="custom",
            sidebar_title="HomeAIVision",
            sidebar_icon="mdi:camera",
            frontend_url_path="home-ai-vision",
            require_admin=False,
            config={
                "_panel_custom": {
                    "name": "homeaivision-panel",
                    "js_url": FRONTEND_SCRIPT_URL,
                }
            },
        )
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Failed to register built-in panel: {e}")

    try:
        resources = hass.data.get("lovelace", {}).get("resources", None)
        if resources:
            if not resources.loaded:
                await resources.async_load()
                resources.loaded = True

            frontend_added = False
            for r in resources.async_items():
                if r["url"].startswith(FRONTEND_SCRIPT_URL):
                    frontend_added = True
                    continue

                if "card-mod.js" in r["url"]:
                    add_extra_js_url(hass, r["url"])

            if not frontend_added:
                if hasattr(resources, "async_create_item"):
                    await resources.async_create_item(
                        {
                            "type": "module",
                            "url": f"{FRONTEND_SCRIPT_URL}?automatically-added",
                        }
                    )
                elif hasattr(resources, "data") and hasattr(resources.data, "append"):
                    resources.data.append(
                        {
                            "type": "module",
                            "url": f"{FRONTEND_SCRIPT_URL}?automatically-added",
                        }
                    )
    except KeyError:
        _LOGGER.warning("[HomeAIVision] Lovelace resources not found.")
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Error loading Lovelace resources: {e}")

    _LOGGER.info("[HomeAIVision] Completed HomeAIVision view setup")
