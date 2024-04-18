import os
from datetime import datetime, timedelta
import shutil
import aiofiles
from .const import CONF_MAX_IMAGES
from PIL import Image
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

    current_images = sorted(os.listdir(save_path), key=lambda x: os.path.getmtime(os.path.join(save_path, x)))
    if len(current_images) >= max_images:
        for extra_image in current_images[:len(current_images) - max_images + 1]:
            os.remove(os.path.join(save_path, extra_image))

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    image_path = os.path.join(save_path, f"cam_frame_{timestamp}.jpg")
    async with aiofiles.open(image_path, 'wb') as file:
        await file.write(image_data)
    return image_path

def clean_up_old_images(base_path, days_to_keep):
    """
    Removes image folders older than a specified number of days.
    
    Args:
        base_path (str): The base directory where images are saved.
        days_to_keep (int): Number of days to keep images before deletion.
    """
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
        _LOGGER.info(f"Created directory: {base_path}")
        return

    today = datetime.now()
    for folder_name in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder_name)
        if os.path.isdir(folder_path):
            try:
                folder_date = datetime.strptime(folder_name, "%Y-%m-%d")
                if (today - folder_date).days > days_to_keep:
                    shutil.rmtree(folder_path)
                    print(f"Deleted old image folder: {folder_path}")
            except ValueError:
                #! Ignore directories that do not match the expected date format
                continue