import os
from datetime import datetime, timedelta
import shutil
import asyncio
import aiofiles
from .const import CONF_MAX_IMAGES
import logging

_LOGGER = logging.getLogger(__name__)

def get_daily_folder_path(base_path):
    """
    Creates and returns a path for daily organized images.
    
    Args:
        base_path (str): The base directory where images are saved.
    
    Returns:
        str: Path to the daily folder.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = os.path.join(base_path, today)
    os.makedirs(daily_path, exist_ok=True)
    return daily_path

async def save_image(base_path, image_data, organize_by_day, max_images):
    """
    Saves an image to the filesystem, either in a daily folder or the base path.
    
    Args:
        base_path (str): The base directory where images are saved.
        image_data (bytes): The binary data of the image to save.
        organize_by_day (bool): Whether to organize images into daily folders.
        max_images (int): Maximum number of images to keep in the folder.
    """
    if organize_by_day:
        save_path = get_daily_folder_path(base_path)
    else:
        save_path = base_path

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

    if len(current_images) >= max_images:
        images_to_remove = current_images[:len(current_images) - max_images + 1]
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

    return image_path

async def clean_up_old_images(base_path, days_to_keep):
    """
    Removes image folders older than a specified number of days.
    
    Args:
        base_path (str): The base directory where images are saved.
        days_to_keep (int): Number of days to keep images before deletion.
    """
    if not os.path.exists(base_path):
        await asyncio.to_thread(os.makedirs, base_path, exist_ok=True)
        _LOGGER.info(f"[HomeAIVision] Created directory: {base_path}")
        return

    today = datetime.now()
    folder_names = await asyncio.to_thread(os.listdir, base_path)
    for folder_name in folder_names:
        folder_path = os.path.join(base_path, folder_name)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.strptime(folder_name, "%Y-%m-%d")
                if (today - folder_date).days > days_to_keep:
                    await asyncio.to_thread(shutil.rmtree, folder_path)
                    _LOGGER.info(f"[HomeAIVision] Deleted old image folder: {folder_path}")
            except ValueError:
                # NOTE: Ignore directories that do not match the expected date format
                continue
            except Exception as e:
                _LOGGER.error(f"[HomeAIVision] Failed to delete {folder_path}: {e}")
