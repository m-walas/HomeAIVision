import asyncio
import logging
import io
import aiohttp  # type: ignore
import traceback

from PIL import Image, ImageChops, ImageFilter
from statistics import median

import time

from aiohttp import ClientConnectorError  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore
from homeassistant.components.persistent_notification import create as pn_create  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore

from .notification_manager import send_notification
from .save_image_manager import save_image, clean_up_old_images
from .const import (
    DOMAIN,
    CONF_AZURE_API_KEY,
    CONF_AZURE_ENDPOINT,
    CONF_MOTION_DETECTION_MIN_AREA,
    CONF_MOTION_DETECTION_HISTORY_SIZE,
)
from .store import HomeAIVisionStore
from .azure_client import analyze_image_with_azure

_LOGGER = logging.getLogger(__name__)


async def periodic_check(hass: HomeAssistant, entry: ConfigEntry, device_config: dict, stop_event: asyncio.Event):
    """
    Periodically checks the camera feed for motion and analyzes detected motion.

    Args:
        hass (HomeAssistant): The Home Assistant instance.
        entry (ConfigEntry): The configuration entry for the integration.
        device_config (dict): Configuration parameters for the specific device.
        stop_event (asyncio.Event): Signal to stop the periodic check.
    """
    device_id = device_config['id']
    store = hass.data[DOMAIN]['store']
    cam_frames_path = hass.config.path("www/HomeAIVision/cam_frames/")
    days_to_keep = device_config.get("days_to_keep", 30)
    max_images_per_day = device_config.get("max_images_per_day", 100)
    send_notifications = device_config.get("send_notifications", False)
    cam_url = device_config.get("url", "")

    # NOTE: Motion detection parameters
    motion_detection_min_area = device_config.get(CONF_MOTION_DETECTION_MIN_AREA, 6000)
    motion_detection_history_size = device_config.get(CONF_MOTION_DETECTION_HISTORY_SIZE, 10)
    motion_detection_interval = device_config.get("motion_detection_interval", 5)

    if not cam_url:
        _LOGGER.error(
            f"[HomeAIVision] No camera URL provided for device "
            f"{device_config['name']}"
        )
        return

    # NOTE: Clean up old images based on retention policy
    await clean_up_old_images(cam_frames_path, days_to_keep)

    _LOGGER.debug(f"[HomeAIVision] Starting periodic_check for device {device_id}")
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            reference_image = None                                  # info: Reference image for motion detection
            reference_image_time = time.monotonic()                 # info: Time when reference image was last updated
            object_present = False                                  # info: Flag to track if object is currently present
            motion_history = []                                     # info: List to store motion scores when no object is present
            unknown_object_counter = 0                              # info: Counter for unknown objects
            max_unknown_object_counter = 20                         # info: Max count before emergency notification
            azure_request_intervals = [0, 1, 2, 3, 4, 10, 15, 20]   # info: Intervals for Azure requests
            max_dynamic_threshold = 10000                           # info: Maximum allowed dynamic threshold
            min_dynamic_threshold = 2000                            # info: Minimum allowed dynamic threshold
            outlier_multiplier = 3                                  # info: Multiplier for determining outliers

            while not stop_event.is_set():
                try:
                    # NOTE: Fetch the latest device configuration
                    device = store.get_device(device_id)
                    if not device:
                        _LOGGER.error(f"[HomeAIVision] Device {device_id} not found")
                        break
                    to_detect_object = [device.to_detect_object]
                    azure_confidence_threshold = device.azure_confidence_threshold

                    # NOTE: Fetch image from the camera
                    async with session.get(cam_url) as response:
                        if response.status == 200:
                            image_data = await response.read()

                            if reference_image is None:
                                try:
                                    current_image = await hass.async_add_executor_job(
                                        lambda: Image.open(io.BytesIO(image_data)).convert('L')
                                    )
                                    reference_image = current_image
                                    reference_image_time = time.monotonic()
                                    _LOGGER.debug("Reference image initialized.")
                                except (IOError, SyntaxError) as e:
                                    _LOGGER.error(f"Failed to initialize reference image: {e}")
                                continue

                            # NOTE: Process image using executor to avoid blocking
                            try:
                                motion_score, current_image = await hass.async_add_executor_job(
                                    process_image, image_data, reference_image
                                )
                            except (IOError, SyntaxError) as e:
                                _LOGGER.error(f"Failed to process image: {e}")
                                continue

                            if not object_present:
                                # NOTE: Outlier detection threshold
                                if motion_history:
                                    med_motion = median(motion_history)
                                    mad_motion = median([abs(m - med_motion) for m in motion_history])
                                    # info: Define the upper outlier threshold
                                    outlier_threshold = med_motion + outlier_multiplier * mad_motion
                                else:
                                    # info: When motion_history is empty
                                    med_motion = 0
                                    mad_motion = 0
                                    outlier_threshold = max_dynamic_threshold

                                # NOTE: Include motion_score if it's not significantly higher than the median
                                if motion_score >= outlier_threshold:
                                    _LOGGER.debug(f"Ignoring outlier motion score: {motion_score}")
                                else:
                                    # info: update motion history
                                    motion_history.append(motion_score)
                                    if len(motion_history) > motion_detection_history_size:
                                        motion_history.pop(0)

                                # important: Recalculate dynamic threshold
                                if len(motion_history) >= 2:
                                    med_motion = median(motion_history)
                                    mad_motion = median([abs(m - med_motion) for m in motion_history])
                                    dynamic_threshold = med_motion + 2 * mad_motion
                                    dynamic_threshold = max(min_dynamic_threshold, min(dynamic_threshold, max_dynamic_threshold))
                                else:
                                    dynamic_threshold = motion_detection_min_area

                                _LOGGER.debug(f"Dynamic motion threshold: {dynamic_threshold}, current motion score: {motion_score}")

                                if motion_score > dynamic_threshold:
                                    _LOGGER.debug(f"Significant motion detected. Motion score: {motion_score}")

                                    # IMPORTANT: Decide whether to send a request to Azure
                                    if unknown_object_counter in azure_request_intervals:
                                        _LOGGER.debug(f"Sending image to Azure for analysis. Counter: {unknown_object_counter}")

                                        # NOTE: Motion detected, send image to Azure
                                        detected, modified_image_data, detected_object_name = await analyze_image_with_azure(
                                            image_data,
                                            entry.data.get(CONF_AZURE_API_KEY),
                                            entry.data.get(CONF_AZURE_ENDPOINT),
                                            to_detect_object,
                                            azure_confidence_threshold,
                                        )

                                        # NOTE: Increase the request count for the device
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

                                        # NOTE: Increase the global request count
                                        await store.async_increment_global_counter()
                                        _LOGGER.info(f"[HomeAIVision] Global Azure request counter: {store.get_global_counter()}")

                                        if detected:
                                            # warning: Object is being present now
                                            object_present = True
                                            _LOGGER.debug(f"Object '{detected_object_name}' detected by Azure.")
                                            # info: Reset unknown_object_counter
                                            unknown_object_counter = 0
                                        else:
                                            _LOGGER.debug("No target object detected by Azure.")
                                            # warning: Increment unknown_object_counter
                                            unknown_object_counter += 1

                                            if unknown_object_counter >= max_unknown_object_counter:
                                                _LOGGER.info("Unknown object detected multiple times without recognition.")
                                                # IMPORTANT: Send emergency notification
                                                if send_notifications:
                                                    language = store.get_language()
                                                    _LOGGER.debug(f"[HomeAIVision] Notification language: {language}")
                                                    await send_notification(
                                                        hass,
                                                        "unknown_object",
                                                        image_path=None,
                                                        notification_language=language,
                                                    )
                                                # IMPORTANT: Update reference image after reaching max detections
                                                reference_age = time.monotonic() - reference_image_time
                                                _LOGGER.info(f"Updating reference image after {unknown_object_counter} unknown detections. Old reference image age: {reference_age:.2f} seconds.")
                                                reference_image = current_image
                                                reference_image_time = time.monotonic()
                                                motion_history.clear()
                                                # info: Reset unknown_object_counter
                                                unknown_object_counter = 0

                                        # NOTE: Save the image if an object is detected
                                        if detected and modified_image_data:
                                            device_name = device_config['name']
                                            save_path = await save_image(
                                                cam_frames_path,
                                                device_name,
                                                modified_image_data,
                                                max_images_per_day,
                                                days_to_keep,
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
                                                    notification_language=language,
                                                )
                                            # warning: Reset motion history
                                            motion_history.clear()
                                    else:
                                        _LOGGER.debug(f"Skipping Azure analysis at counter {unknown_object_counter}.")
                                        unknown_object_counter += 1

                                        if unknown_object_counter >= max_unknown_object_counter:
                                            _LOGGER.info("Unknown object detected multiple times without recognition.")
                                            # IMPORTANT: Send emergency notification
                                            if send_notifications:
                                                language = store.get_language()
                                                _LOGGER.debug(f"[HomeAIVision] Notification language: {language}")
                                                await send_notification(
                                                    hass,
                                                    "unknown_object",
                                                    image_path=None,
                                                    notification_language=language,
                                                )
                                            # IMPORTANT: Update reference image after reaching max detections
                                            reference_age = time.monotonic() - reference_image_time
                                            _LOGGER.info(f"Updating reference image after {unknown_object_counter} unknown detections. Old reference image age: {reference_age:.2f} seconds.")
                                            reference_image = current_image
                                            reference_image_time = time.monotonic()
                                            motion_history.clear()
                                            # info: Reset unknown_object_counter
                                            unknown_object_counter = 0
                                else:
                                    _LOGGER.debug(f"No significant motion detected. Motion score: {motion_score}")
                                    # info: Update reference image periodically when no motion is detected
                                    reference_image = current_image
                                    reference_image_time = time.monotonic()
                                    _LOGGER.debug("Reference image updated.")
                                    # info: reset unknown_object_counter
                                    unknown_object_counter = 0
                            else:
                                # info: Object is present, check if it has left the scene
                                if motion_score < motion_detection_min_area:
                                    _LOGGER.debug(f"No motion detected. Motion score: {motion_score}")
                                    object_present = False
                                    _LOGGER.debug("Object has left the scene.")
                                    # important: Update reference image after object leaves the scene
                                    reference_image = current_image
                                    reference_image_time = time.monotonic()
                                    _LOGGER.debug("Reference image updated after object left.")
                                    unknown_object_counter = 0
                                else:
                                    # info: calculate how long the reference image has been held
                                    reference_age = time.monotonic() - reference_image_time
                                    _LOGGER.debug(f"Object still present. Reference image age: {reference_age:.2f} seconds")
                                    # info: object still present, do nothing
                                    pass
                        else:
                            _LOGGER.warning(
                                f"[HomeAIVision] Failed to fetch image, status code: {response.status}"
                            )
                except ClientConnectorError:
                    _LOGGER.error(
                        f"[HomeAIVision] Unable to connect to the camera at {cam_url}. "
                        f"Please ensure the camera is online and the URL is correct."
                    )
                    # NOTE: Create a persistent notification for connection errors
                    await hass.async_add_executor_job(
                        pn_create,
                        hass,
                        (
                            f"Unable to connect to the camera at {cam_url}. "
                            "Please ensure the camera is online and the URL is correct."
                        ),
                        title="HomeAIVision Camera Connection Error",
                        notification_id=f"homeaivision_camera_error_{device_id}",
                    )
                except asyncio.CancelledError:
                    _LOGGER.debug(f"[HomeAIVision] Camera check task for device {device_id} cancelled.")
                    break
                except Exception as e:
                    _LOGGER.error(f"[HomeAIVision] Unexpected error: {e}")
                    # info: Log the full traceback for debugging purposes
                    _LOGGER.debug(traceback.format_exc())

                # _LOGGER.debug(f"[HomeAIVision] Waiting for {motion_detection_interval} seconds or stop_event")
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=motion_detection_interval)
                except asyncio.TimeoutError:
                    pass

    except asyncio.CancelledError:
        _LOGGER.debug(f"[HomeAIVision] periodic_check for device {device_id} was cancelled.")
        raise
    finally:
        _LOGGER.debug(f"[HomeAIVision] periodic_check has finished for device {device_id}")


def process_image(image_data, reference_image):
    """
    Process the image and calculate motion score.

    Args:
        image_data (bytes): The raw image data.
        reference_image (PIL.Image.Image): The reference image for motion detection.

    Returns:
        tuple: (motion_score, current_image)
    """
    current_image = Image.open(io.BytesIO(image_data)).convert('L')
    diff_image = ImageChops.difference(reference_image, current_image)
    threshold = diff_image.point(lambda p: p > 50 and 255)
    cleaned = threshold.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    motion_score = sum(cleaned.histogram()[255:])
    return motion_score, current_image
