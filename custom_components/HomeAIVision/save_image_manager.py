import os
import shutil
import asyncio
import aiofiles # type: ignore
import logging

from datetime import datetime, timedelta

from .const import CONF_MAX_IMAGES_PER_DAY

_LOGGER = logging.getLogger(__name__)

def get_device_folder_path(base_path, device_name):
    """
    Creates and returns a path for the device's images.
    
    Args:
        base_path (str): The base directory where images are saved.
        device_name (str): The name of the device (camera).
    
    Returns:
        str: Path to the device's folder.
    """
    device_path = os.path.join(base_path, device_name)
    os.makedirs(device_path, exist_ok=True)
    return device_path

def get_daily_folder_path(device_path):
    """
    Creates and returns a path for daily organized images within a device's folder.
    
    Args:
        device_path (str): The directory of the device.
    
    Returns:
        str: Path to the daily folder.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = os.path.join(device_path, today)
    os.makedirs(daily_path, exist_ok=True)
    return daily_path

async def save_image(base_path, device_name, image_data, max_images_per_day, days_to_keep):
    """
    Saves an image to the filesystem, organizing it into device and date folders,
    and enforcing storage limits.
    
    Args:
        base_path (str): The base directory where images are saved.
        device_name (str): The name of the device (camera).
        image_data (bytes): The binary data of the image to save.
        max_images_per_day (int): Maximum number of images per day per camera.
        days_to_keep (int): Number of days to keep images before deletion.
    """
    device_path = get_device_folder_path(base_path, device_name)
    save_path = get_daily_folder_path(device_path)

    try:
        current_images = await asyncio.to_thread(
            lambda: sorted(
                [f for f in os.listdir(save_path) if f.lower().endswith((".jpg", ".jpeg"))],
                key=lambda x: os.path.getmtime(os.path.join(save_path, x))
            )
        )
    except FileNotFoundError:
        _LOGGER.warning(f"[HomeAIVision] Save path does not exist: {save_path}")
        current_images = []

    if len(current_images) >= max_images_per_day:
        images_to_remove = current_images[:len(current_images) - max_images_per_day + 1]
        await asyncio.gather(*[
            asyncio.to_thread(os.remove, os.path.join(save_path, extra_image))
            for extra_image in images_to_remove
        ])
        for extra_image in images_to_remove:
            _LOGGER.info(f"[HomeAIVision] Removed old image: {extra_image}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    image_path = os.path.join(save_path, f"cam_frame_{timestamp}.jpg")

    try:
        async with aiofiles.open(image_path, 'wb') as file:
            await file.write(image_data)
        _LOGGER.info(f"[HomeAIVision] Saved image: {image_path}")
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Failed to save image {image_path}: {e}")

    # NOTE: Cleanup old images after saving
    await clean_up_old_images(device_path, days_to_keep)

    return image_path

async def clean_up_old_images(device_path, days_to_keep):
    """
    Removes image folders older than a specified number of days within a device's folder.
    
    Args:
        device_path (str): The directory of the device.
        days_to_keep (int): Number of days to keep images before deletion.
    """
    if not os.path.exists(device_path):
        await asyncio.to_thread(os.makedirs, device_path, exist_ok=True)
        _LOGGER.info(f"[HomeAIVision] Created device directory: {device_path}")
        return

    today = datetime.now()
    folder_names = await asyncio.to_thread(os.listdir, device_path)
    for folder_name in folder_names:
        folder_path = os.path.join(device_path, folder_name)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.strptime(folder_name, "%Y-%m-%d")
                if (today - folder_date).days > days_to_keep:
                    await asyncio.to_thread(shutil.rmtree, folder_path)
                    _LOGGER.info(f"[HomeAIVision] Deleted old image folder: {folder_path}")
            except ValueError:
                # info: Ignore directories that do not match the date format
                continue
            except Exception as e:
                _LOGGER.error(f"[HomeAIVision] Failed to delete {folder_path}: {e}")
