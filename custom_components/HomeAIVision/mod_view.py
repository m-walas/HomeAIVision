from homeassistant.components.frontend import add_extra_js_url

from .const import FRONTEND_SCRIPT_URL

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_view(hass):
    """
    Sets up the HomeAIVision view in Home Assistant.
    """

    # Serve the HomeAIVision controller and add it as extra_module_url
    _LOGGER.debug("Registering static path for HomeAIVision panel")
    hass.http.register_static_path(
        FRONTEND_SCRIPT_URL,
        hass.config.path("custom_components/HomeAIVision/homeaivision_panel.js"),
    )
    add_extra_js_url(hass, FRONTEND_SCRIPT_URL)

    # Serve the HomeAIVision Settings panel and register it as a panel
    _LOGGER.info(f"Registering panel for HomeAIVision view")
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

    # Also load HomeAIVision as a lovelace resource so it's accessible to Cast
    resources = hass.data["lovelace"]["resources"]
    if resources:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        frontend_added = False
        for r in resources.async_items():
            if r["url"].startswith(FRONTEND_SCRIPT_URL):
                frontend_added = True
                continue

            # While going through the resources, also preload card-mod if it is found
            if "card-mod.js" in r["url"]:
                add_extra_js_url(hass, r["url"])

        if not frontend_added:
            if getattr(resources, "async_create_item", None):
                await resources.async_create_item(
                    {
                        "res_type": "module",
                        "url": FRONTEND_SCRIPT_URL + "?automatically-added",
                    }
                )
            elif getattr(resources, "data", None) and getattr(
                resources.data, "append", None
            ):
                resources.data.append(
                    {
                        "type": "module",
                        "url": FRONTEND_SCRIPT_URL + "?automatically-added",
                    }
                )

    _LOGGER.info("Completed HomeAIVision view setup")
