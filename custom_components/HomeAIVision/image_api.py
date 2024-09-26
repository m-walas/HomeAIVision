import asyncio
import os
import logging
from homeassistant.components.http import HomeAssistantView
from urllib.parse import unquote
from .const import DOMAIN

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
