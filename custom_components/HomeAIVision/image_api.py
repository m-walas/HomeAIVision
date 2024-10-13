import asyncio
import os
import logging
from homeassistant.components.http import HomeAssistantView
from urllib.parse import unquote
from .const import DOMAIN
from aiohttp.web import json_response

_LOGGER = logging.getLogger(__name__)

async def get_listdir(path):
    return await asyncio.get_event_loop().run_in_executor(None, os.listdir, path)

async def isdir(path):
    return await asyncio.get_event_loop().run_in_executor(None, os.path.isdir, path)

async def isfile(path):
    return await asyncio.get_event_loop().run_in_executor(None, os.path.isfile, path)

class ImageListView(HomeAssistantView):
    """View to handle image operations."""

    url = "/api/homeaivision/images"
    name = "api:homeaivision:images"
    requires_auth = True

    async def get(self, request):
        """Handle GET requests to retrieve images."""
        hass = request.app["hass"]
        user = request["hass_user"]

        entry_id = None
        for eid, data in hass.data.get(DOMAIN, {}).items():
            entry_id = eid
            break

        if not entry_id:
            return self.json({"success": False, "error": "invalid_entry_id"}, status=400)

        config = hass.data[DOMAIN][entry_id]
        organize_by_day = config.get("organize_by_day", False)
        cam_frames_dir = hass.config.path("www/HomeAIVision/cam_frames")

        images = []
        current_day = None

        if organize_by_day:
            try:
                day_dirs = sorted(await get_listdir(cam_frames_dir), reverse=True)
                for day_dir in day_dirs:
                    day_path = os.path.join(cam_frames_dir, day_dir)
                    if await isdir(day_path):
                        day_images = []
                        img_files = sorted(await get_listdir(day_path), reverse=True)
                        for img in img_files:
                            img_path = os.path.join(day_path, img)
                            if await isfile(img_path) and img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                day_images.append({"url": f"/local/HomeAIVision/cam_frames/{day_dir}/{img}"})
                        if day_images:
                            images.append({
                                "day": day_dir,
                                "images": day_images
                            })
                return self.json({
                    "success": True,
                    "images": images,
                    "currentDay": current_day,
                    "organizeByDay": organize_by_day
                })
            except Exception as e:
                _LOGGER.error(f"Error retrieving organized images: {e}")
                return self.json({"success": False, "error": "error_retrieving_images"}, status=500)
        else:
            try:
                img_files = sorted(await get_listdir(cam_frames_dir), reverse=True)
                for img in img_files:
                    img_path = os.path.join(cam_frames_dir, img)
                    if await isfile(img_path) and img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        images.append({"url": f"/local/HomeAIVision/cam_frames/{img}"})
                return self.json({
                    "success": True,
                    "images": images,
                    "currentDay": current_day,
                    "organizeByDay": organize_by_day
                })
            except Exception as e:
                _LOGGER.error(f"Error retrieving unorganized images: {e}")
                return self.json({"success": False, "error": "error_retrieving_images"}, status=500)

class ConfigDataView(HomeAssistantView):
    """View to get HomeAIVision configuration data."""

    url = "/api/homeaivision/config"
    name = "api:homeaivision:config"
    requires_auth = True

    async def get(self, request):
        """Handle GET requests to retrieve configuration data."""
        hass = request.app["hass"]
        user = request["hass_user"]

        _LOGGER.info("Received request for configuration data")
        
        entry_id = None
        for eid, data in hass.data.get(DOMAIN, {}).items():
            entry_id = eid
            break

        if not entry_id:
            _LOGGER.error("No valid entry ID found")
            return json_response({"success": False, "error": "invalid_entry_id"}, status=400)

        config = hass.data[DOMAIN][entry_id]

        config_data = {
            "organize_by_day": config.get("organize_by_day", False),
            "days_to_keep": config.get("days_to_keep", 7),
            "max_images": config.get("max_images", 30),
            "time_between_requests": config.get("time_between_requests", 30),
            "send_notifications": config.get("send_notifications", False),
            "notification_language": config.get("notification_language", "en"),
            "to_detect_object": config.get("to_detect_object", "person"),
            "confidence_threshold": config.get("confidence_threshold", 0.6),
            "integration_title": config.get("integration_title", "Home AI Vision"),
        }

        _LOGGER.info(f"Returning configuration data: {config_data}")
        
        return json_response({
            "success": True,
            "config": config_data
        }, status=200)
