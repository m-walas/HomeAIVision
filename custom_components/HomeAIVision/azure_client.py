import aiohttp  # type: ignore
import logging
import io
from PIL import Image, ImageDraw

_LOGGER = logging.getLogger(__name__)

async def analyze_image_with_azure(
    image_data, azure_api_key, azure_endpoint, objects, confidence_threshold
):
    """
    Analyzes the image for the presence of specified objects using Azure Cognitive Services.

    Parameters:
    - image_data (bytes): The image data in bytes.
    - azure_api_key (str): Azure Cognitive Services API key.
    - azure_endpoint (str): Azure Cognitive Services endpoint URL.
    - objects (list): List of objects to detect.
    - confidence_threshold (float): Minimum confidence level to consider a detection valid.

    Returns:
    - tuple:
        - object_detected (bool): Indicates if the target object was detected.
        - modified_image_data (bytes or None): The image data with detected objects outlined.
        - detected_object_name (str or None): The name of the detected object.
    """
    headers = {
        'Ocp-Apim-Subscription-Key': azure_api_key,
        'Content-Type': 'application/octet-stream',
    }
    params = {'visualFeatures': 'Objects'}

    object_detected = False
    detected_object_name = None

    _LOGGER.debug(
        f"[HomeAIVision] Azure API URL: {azure_endpoint}, "
        f"Azure API Key: {azure_api_key[:5]}***"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{azure_endpoint}/vision/v3.0/analyze",
                headers=headers,
                params=params,
                data=image_data,
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        f"[HomeAIVision] Failed to analyze image, "
                        f"status code: {response.status}"
                    )
                    response_text = await response.text()
                    _LOGGER.error(
                        f"[HomeAIVision] Error response: {response_text}"
                    )
                    return False, None, None

                response_json = await response.json()
                _LOGGER.debug(f"Azure response: {response_json}")

                # INFO: Open the original image for drawing detected objects
                image = Image.open(io.BytesIO(image_data))
                draw = ImageDraw.Draw(image)

                for item in response_json.get('objects', []):
                    _LOGGER.debug(
                        f"[HomeAIVision] Detected object with confidence "
                        f"{item['confidence']}: {item['object']}"
                    )
                    object_name, confidence = extract_object_with_hierarchy(
                        item, objects
                    )
                    if object_name and confidence >= confidence_threshold:
                        object_detected = True
                        detected_object_name = object_name
                        rect = item['rectangle']
                        # NOTE: Draw a rectangle around the detected object
                        draw.rectangle(
                            [
                                (rect['x'], rect['y']),
                                (rect['x'] + rect['w'], rect['y'] + rect['h']),
                            ],
                            outline="red",
                            width=5,
                        )

                # INFO: Save the modified image with detected objects outlined
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                return object_detected, buffered.getvalue(), detected_object_name
    except Exception as e:
        _LOGGER.error(f"[HomeAIVision] Error during Azure analysis: {e}")
        return False, None, None


def extract_object_with_hierarchy(item, target_objects):
    """
    Traverse the object and its parents to find a matching target object.

    Parameters:
    - item (dict): The object item from Azure response.
    - target_objects (list): List of target object names to detect.

    Returns:
    - tuple:
        - object_name (str or None): The name of the detected object.
        - confidence (float or None): The confidence level of the detection.
    """
    while item:
        if item['object'] in target_objects:
            return item['object'], item['confidence']
        # NOTE: Traverse to the parent object if available
        item = item.get('parent')
    return None, None
