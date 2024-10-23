import asyncio
import logging
import io
import aiohttp  # type: ignore
import traceback  # NOTE: Added to handle full tracebacks in logging
from PIL import Image, ImageChops, ImageFilter, ImageStat

from datetime import datetime
from aiohttp import ClientConnectorError  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore
from homeassistant.components.persistent_notification import create as pn_create  # type: ignore

from .notification_manager import send_notification
from .save_image_manager import save_image, clean_up_old_images
from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_TO_DETECT_OBJECT,
    CONF_AZURE_CONFIDENCE_THRESHOLD,
    CONF_MOTION_DETECTION_THRESHOLD,
    CONF_MOTION_DETECTION_FRAME_SKIP,
    CONF_MOTION_DETECTION_INTERVAL,
)
from .store import HomeAIVisionStore
from .azure_client import analyze_image_with_azure

_LOGGER = logging.getLogger(__name__)

async def setup_periodic_camera_check(hass, entry, device_config):
    """
    Sets up a periodic camera check for motion detection and analysis.
    
    This function initializes the periodic task that fetches images from the camera,
    detects motion based on pixel differences, and sends images to Azure for object analysis
    when significant motion is detected.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for the integration.
        device_config (dict): Configuration parameters for the specific device.
    """
    device_id = device_config['id']
    store = hass.data[DOMAIN]['store']
    cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
    days_to_keep = device_config.get("days_to_keep", 7)
    organize_by_day = device_config.get("organize_by_day", True)
    max_images = device_config.get("max_images", 30)
    to_detect_object = [device_config.get(CONF_TO_DETECT_OBJECT)]
    azure_confidence_threshold = device_config.get(CONF_AZURE_CONFIDENCE_THRESHOLD, 0.6)
    send_notifications = device_config.get("send_notifications", False)
    cam_url = device_config.get("url", "")

    # NOTE: Motion detection parameters
    motion_detection_threshold = device_config.get(CONF_MOTION_DETECTION_THRESHOLD, 10000)
    motion_detection_frame_skip = device_config.get(CONF_MOTION_DETECTION_FRAME_SKIP, 2)
    motion_detection_interval = device_config.get(CONF_MOTION_DETECTION_INTERVAL, 3)

    if not cam_url:
        _LOGGER.error(
            f"[HomeAIVision] No camera URL provided for device "
            f"{device_config['name']}"
        )
        return

    # INFO: Clean up old images based on retention policy
    await clean_up_old_images(cam_frames_path, days_to_keep)

    async def periodic_check():
        """
        Periodically checks the camera feed for motion and analyzes detected motion.
        
        This coroutine runs in an infinite loop, fetching images from the camera at specified intervals,
        detecting motion by comparing consecutive frames, and sending images to Azure for further analysis
        if significant motion is detected.
        """
        async with aiohttp.ClientSession() as session:
            prev_image = None
            frame_count = 0

            while True:
                try:
                    # NOTE: Fetch the latest device configuration
                    device = store.get_device(device_id)
                    if not device:
                        _LOGGER.error(f"[HomeAIVision] Device {device_id} not found")
                        break
                    to_detect_object = [device.to_detect_object]
                    azure_confidence_threshold = device.azure_confidence_threshold

                    # INFO: Fetch image from the camera
                    async with session.get(cam_url) as response:
                        if response.status == 200:
                            image_data = await response.read()

                            # INFO: Open image using PIL in grayscale mode
                            current_image = Image.open(io.BytesIO(image_data)).convert('L')  # Grayscale

                            frame_count += 1

                            # NOTE: Skip frames based on frame_skip setting
                            if frame_count % motion_detection_frame_skip != 0:
                                await asyncio.sleep(motion_detection_interval)
                                continue

                            if prev_image is None:
                                prev_image = current_image
                                await asyncio.sleep(motion_detection_interval)
                                continue

                            # INFO: Calculate the difference between the current and previous images
                            diff_image = ImageChops.difference(prev_image, current_image)

                            # NOTE: Apply threshold to obtain a binary image
                            threshold = diff_image.point(lambda p: p > 30 and 255)

                            # NOTE: Apply morphological operations to reduce noise
                            # Dilation
                            dilated = threshold.filter(ImageFilter.MaxFilter(3))
                            # Erosion
                            eroded = dilated.filter(ImageFilter.MinFilter(3))

                            # NOTE: Calculate motion score
                            histogram = eroded.histogram()
                            motion_score = sum(histogram[255:])

                            # Update the previous image for the next comparison
                            prev_image = current_image

                            if motion_score < motion_detection_threshold:
                                _LOGGER.debug(f"No significant motion detected. Motion score: {motion_score}")
                                await asyncio.sleep(motion_detection_interval)
                                continue
                            else:
                                _LOGGER.debug(f"Motion detected with motion score: {motion_score}")
                                # NOTE: If motion is detected, start processing the image with Azure

                                (
                                    object_detected,
                                    modified_image_data,
                                    detected_object_name,
                                ) = await analyze_image_with_azure(
                                    image_data,
                                    entry.data.get(CONF_AZURE_API_KEY),
                                    entry.data.get(CONF_AZURE_ENDPOINT),
                                    to_detect_object,
                                    azure_confidence_threshold,
                                )

                                # INFO: Increase the request count for the device
                                device = store.get_device(device_id)
                                if device:
                                    device.device_azure_request_count += 1
                                    await store.async_save()
                                    async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")
                                    _LOGGER.info(f"[HomeAIVision] Device {device_id} Azure request count: {device.device_azure_request_count}")
                                else:
                                    _LOGGER.error(
                                        f"[HomeAIVision] Device {device_id} not found in store"
                                    )

                                # INFO: Increase the global request count
                                await store.async_increment_global_counter()
                                _LOGGER.info(f"[HomeAIVision] Global Azure request counter: {store.get_global_counter()}")

                                # NOTE: Save the image if an object is detected
                                if object_detected and modified_image_data:
                                    save_path = await save_image(
                                        cam_frames_path,
                                        modified_image_data,
                                        organize_by_day,
                                        max_images,
                                    )
                                    # NOTE: Send notification if enabled
                                    if send_notifications:
                                        language = store.get_language()
                                        _LOGGER.debug(f"[HomeAIVision] Notification language: {language}")
                                        relative_path = save_path.replace(
                                            hass.config.path(), ""
                                        ).lstrip("/")
                                        await send_notification(
                                            hass,
                                            detected_object_name,
                                            relative_path,
                                            organize_by_day,
                                            language,
                                        )
                        else:
                            _LOGGER.warning(
                                f"[HomeAIVision] Failed to fetch image, "
                                f"status code: {response.status}"
                            )
                except ClientConnectorError:
                    _LOGGER.error(
                        f"[HomeAIVision] Unable to connect to the camera at "
                        f"{cam_url}. Please ensure the camera is online "
                        f"and the URL is correct."
                    )
                    # NOTE: Create a persistent notification for connection errors
                    pn_create(
                        hass,
                        (
                            f"Unable to connect to the camera at {cam_url}. "
                            "Please ensure the camera is online and the URL is correct."
                        ),
                        title="HomeAIVision Camera Connection Error",
                        notification_id=f"homeaivision_camera_error_{device_id}",
                    )
                except Exception as e:
                    _LOGGER.error(f"[HomeAIVision] Unexpected error: {e}")
                    # IMPORTANT: Log the full traceback for debugging purposes
                    _LOGGER.debug(traceback.format_exc())

                await asyncio.sleep(motion_detection_interval)

    # IMPORTANT: Start the periodic camera check task
    hass.loop.create_task(periodic_check())
