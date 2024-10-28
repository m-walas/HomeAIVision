# Camera Processing

The `camera_processing` module is the core component of the HomeAIVision integration, responsible for handling image acquisition, motion detection, interaction with Azure Cognitive Services, and managing notifications and image storage. This document provides a comprehensive explanation of how `camera_processing` operates, including its functions, algorithms, and data flow.

## Overview

The `camera_processing` module performs the following primary functions:

- **Image Acquisition**: Fetches images from the configured camera feed at specified intervals.
- **Motion Detection**: Analyzes image differences to detect significant motion.
- **Object Detection**: Sends motion-detected images to Azure for object recognition.
- **Notification and Image Management**: Sends notifications based on detected objects and manages image storage.

## Detailed Workflow

### 1. Image Acquisition

- **Periodic Fetching**: The module uses `aiohttp`, an asynchronous HTTP client, to fetch images from the camera URL at intervals defined by `motion_detection_interval` (default: 5 seconds). This ensures that the system continuously monitors the camera feed for any changes.
- **Reference Image**: Upon the first fetch, the module stores the initial image as a reference image. This image serves as the baseline for future comparisons to detect changes or motion in the camera's field of view.

### 2. Motion Detection

Detecting motion is a two-step process involving image comparison and analysis:

- **Image Comparison**:
  - **Difference Calculation**: The module uses the Python Imaging Library (PIL) to calculate the difference between the current image and the reference image using `ImageChops.difference`.
  - **Grayscale Conversion**: Both images are converted to grayscale to simplify the analysis, focusing solely on changes in brightness and reducing computational complexity.

- **Thresholding and Cleaning**:
  - **Thresholding**: The difference image is processed to highlight significant changes. Pixels with a difference value greater than 50 are set to white (255), and others to black (0), creating a binary image that emphasizes areas of change.
  - **Morphological Operations**: To reduce noise and eliminate minor fluctuations (like flickering lights), the module applies dilation (`MaxFilter`) followed by erosion (`MinFilter`). This process helps in refining the motion detection by emphasizing substantial movements while ignoring insignificant ones.
  - **Motion Score**: The module calculates a motion score by summing the white pixels in the cleaned binary image. A higher motion score indicates a greater extent of motion detected in the frame.

### 3. Motion Analysis and Azure Interaction

Once motion is detected, the module determines whether it is significant enough to warrant further analysis using Azure Cognitive Services:

- **Dynamic Thresholding**:
  - **Adaptive Threshold**: Instead of using a fixed threshold, the module calculates a dynamic threshold based on historical motion scores. This approach allows the system to adapt to varying lighting conditions and scene changes, ensuring more accurate motion detection.
  - **Median and MAD**: The dynamic threshold is computed using the median and median absolute deviation (MAD) of recent motion scores. This statistical method helps in identifying and excluding outliers, preventing false positives from sudden, non-relevant changes.
  - **Outlier Detection**: The system identifies and ignores motion scores that are significantly higher than the median, which helps in filtering out anomalies that could cause false alarms.

- **Significant Motion**: If the current motion score exceeds the dynamic threshold, the module considers it as significant motion and proceeds to analyze the image with Azure Cognitive Services.

- **Azure Request Intervals**:
  - **Optimized API Usage**: To manage API usage and costs, the module doesn't send every detected motion to Azure. Instead, it uses an `unknown_object_counter` to determine when to send an image for analysis, ensuring that only meaningful events trigger Azure requests.

- **Azure Analysis**:
  - **Object Detection**: The significant motion-detected image is sent to Azure Cognitive Services, which analyzes the image to identify predefined objects (e.g., person, car, cat, dog) based on the configured `to_detect_object` list and `azure_confidence_threshold`.
  - **Response Handling**: Azure returns the detected objects along with their confidence scores, which the module uses to decide whether to send notifications and save images.

### 4. Notification and Image Management

After Azure analyzes the image, the module handles notifications and manages the storage of images:

- **Detected Objects**:
  - **Notifications**: If Azure detects a target object with sufficient confidence, the module sends a notification to the user, informing them of the detection.
  - **Image Saving**: The image with the detected object is saved to the specified directory (`cam_frames_path`). The system organizes saved images by day if enabled, and ensures that storage limits (`max_images`) and retention policies (`days_to_keep`) are enforced.

- **Unknown Objects**:
  - **Emergency Alerts**: If no target object is detected after multiple analyses (`max_unknown_object_counter`), the module sends an emergency notification to alert the user of potential unrecognized objects.

    ***Note:*** This procedure is designed not to completely ignore the detection of motion in the image through initial local analysis using PIL, even though Azure Cognitive Services does not recognize the object. The counter is set high enough so that notification of an unidentified object is sent only as a last resort.

- **Reference Image Update**:
  - **Adaptive Baseline**: If no significant motion is detected over a certain period (`max_no_object_detected`), the module updates the reference image to reflect the current scene. This ensures that the motion detection remains accurate and adapts to changes in the environment.

    ***Note:*** The reference image will never be updated when motion detection is suspected.

## Key Functions and Methods

### setup_periodic_camera_check

```python
async def setup_periodic_camera_check(hass: HomeAssistant, entry: ConfigEntry, device_config: dict):
    ...
```

**Purpose**: Sets up a periodic task that fetches images from the camera, detects motion, and analyzes images with Azure if significant motion is detected.

**Parameters**:

- `hass`: Home Assistant instance.
- `entry`: Configuration entry for the integration.
- `device_config`: Configuration parameters for the specific device.

**Workflow**:

- **Initialization**:
  - Sets up necessary variables and paths based on `device_config`.
  - Initializes parameters for motion detection and Azure interaction.
  - Cleans up old images based on retention policies.

- **Periodic Loop**:
  - **Fetches the Latest Image**: Retrieves the current image from the camera using `aiohttp`.
  - **Opens and Processes the Image**: Converts the raw image data to a grayscale PIL Image object.
  - **Detects Motion**: Compares the current image with the reference image to calculate the motion score.
  - **Determines Significance**: Uses dynamic thresholding to decide if the detected motion is significant.
  - **Sends to Azure**: If significant motion is detected, sends the image to Azure for object recognition.
  - **Manages Notifications and Image Saving**: Based on Azure's response, sends notifications and saves images as configured.
  - **Updates Reference Image**: Adjusts the reference image based on motion detection results to maintain accurate future detections.
  - **Handles Errors Gracefully**: Catches and logs connection issues and unexpected exceptions to ensure continuous operation.

- **Cleanup**:
  - Ensures old images are cleaned up based on retention policies to manage storage efficiently.

### periodic_check

Within `setup_periodic_camera_check`, the `periodic_check` coroutine performs the main processing steps.

**Steps**:

1. **Fetch Image**: Retrieves the current image from the camera using `aiohttp`.
2. **Open Image**: Converts the raw image data to a grayscale PIL Image object.
3. **Motion Detection**:
   - Compares the current image with the reference image.
   - Applies thresholding and morphological operations to create a binary image.
   - Calculates the motion score based on the number of white pixels.
4. **Dynamic Thresholding**: Adjusts the motion threshold based on historical data to adapt to environmental changes.
5. **Azure Analysis**:
   - Determines if an Azure analysis is necessary based on the `unknown_object_counter`.
   - Sends the image to Azure if conditions are met.
   - Processes Azure's response to detect target objects.
6. **Notifications and Image Saving**:
   - Sends notifications if target objects are detected.
   - Saves images according to user settings.
7. **Reference Image Management**: Updates the reference image when no motion is detected for a certain period or when the object is no longer present.

## Example Code Snippets

### fetch_image

```python
async def fetch_image(session, cam_url):
    async with session.get(cam_url, timeout=30) as response:
        if response.status == 200:
            return await response.read()
        else:
            raise ValueError(f"Failed to fetch image, status code: {response.status}")
```

**Purpose**: Asynchronously fetches an image from the camera URL.

### detect_motion

```python
def detect_motion(reference_image, current_image):
    diff_image = ImageChops.difference(reference_image, current_image)
    threshold = diff_image.point(lambda p: p > 50 and 255)
    cleaned = threshold.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    motion_score = sum(cleaned.histogram()[255:])
    return motion_score
```

**Purpose**: Detects motion by comparing the current image with the reference image.

### analyze_with_azure

```python
async def analyze_with_azure(image_data, azure_api_key, azure_endpoint, objects, confidence_threshold):
    detected, modified_image_data, detected_object_name = await analyze_image_with_azure(
        image_data,
        azure_api_key,
        azure_endpoint,
        objects,
        confidence_threshold,
    )
    return detected, modified_image_data, detected_object_name
```

**Purpose**: Sends the image to Azure for object detection.

### send_notification

```python
async def send_notification(hass, message_key, image_path, language):
    message = await get_translated_message(language, message_key)
    await hass.services.async_call(
        'notify', 'homeaivision', {'message': message, 'data': {'image': image_path}}
    )
```

**Purpose**: Sends a notification to the user if enabled.

## Security Considerations

- **API Key Management**: Azure API keys are stored securely within Home Assistant's configuration and are not exposed. Ensure that your Home Assistant instance is secured to prevent unauthorized access to configuration files.
- **Data Privacy**: Only necessary image data is sent to Azure for processing. The system adheres to best practices for data privacy by limiting the scope of image analysis to predefined objects and not storing sensitive information beyond the configured retention period.

## Extensibility

- **Adding New Detection Objects**: Easily add support for new objects by updating the `to_detect_object` configuration and corresponding translations in `strings.json`. This allows the integration to recognize and notify about additional objects as needed.
- **Custom Notifications**: Integrate with different notification platforms supported by Home Assistant for customized alerts. You can configure how and where notifications are sent based on your preferences.

## Conclusion

The `camera_processing` module ensures efficient and accurate motion and object detection by leveraging Azure's powerful AI capabilities. Its modular design allows for easy customization and extension, making HomeAIVision a versatile tool for enhancing home automation and security.

With built-in notification handling and intelligent motion analysis, HomeAIVision provides a seamless experience, ensuring you are always informed about relevant events without the need for additional automations.

For more information on configuration and usage, refer to the **[Configuration Guide](configuration.md)**.
