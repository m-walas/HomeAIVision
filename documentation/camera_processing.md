# Camera Processing Module Overview

The `camera_processing` module is the core component of the HomeAIVision integration, responsible for handling image acquisition, motion detection with adaptive scaling, interaction with Azure Cognitive Services, and managing notifications and image storage. This document provides a comprehensive explanation of how `camera_processing` operates, including its functions, algorithms, and data flow.

## Overview

The `camera_processing` module performs the following primary functions:

- **Image Acquisition**: Fetches images from the configured camera feed at specified intervals.
- **Motion Detection with Scaling**: Analyzes image differences to detect significant motion, using adaptive thresholds based on image resolution and sensitivity settings.
- **Object Detection**: Sends motion-detected images to Azure for object recognition.
- **Notification and Image Management**: Sends notifications based on detected objects and manages image storage.

## Detailed Workflow

### 1. Image Acquisition

- **Periodic Fetching**: The module uses `aiohttp`, an asynchronous HTTP client, to fetch images from the camera URL at intervals defined by `motion_detection_interval` (default: 5 seconds). This ensures continuous monitoring of the camera feed for changes.
- **Reference Image Initialization**: Upon the first fetch, the module stores the initial image as a reference. This image serves as the baseline for future comparisons to detect motion in the camera's field of view.

### 2. Motion Detection with Adaptive Scaling

Detecting motion involves image comparison and analysis, with thresholds scaled based on image resolution and sensitivity settings:

- **Image Comparison**:
  - **Difference Calculation**: The module uses the Python Imaging Library (PIL) to calculate the difference between the current image and the reference image using `ImageChops.difference`.
  - **Grayscale Conversion**: Both images are converted to grayscale to simplify analysis and reduce computational complexity.

- **Thresholding and Cleaning**:
  - **Thresholding**: Pixels with a difference value greater than 50 are set to white (255), and others to black (0), creating a binary image that emphasizes areas of change.
  - **Morphological Operations**: The module applies dilation (`MaxFilter`) followed by erosion (`MinFilter`) to reduce noise and emphasize substantial movements.
  - **Motion Score**: The motion score is calculated by summing the white pixels in the cleaned binary image.

- **Adaptive Threshold Calculation**:
  - **Sensitivity Levels**: The system supports sensitivity levels (low, medium, high) which adjust the motion detection thresholds.
  - **Scaling Thresholds**: The thresholds are scaled based on the total number of pixels in the image and the selected sensitivity level.
  - **Threshold Parameters**:
    - `motion_detection_min_area`: The minimum area (in pixels) considered as significant motion, calculated as a percentage of the total pixels.
    - `min_dynamic_threshold` and `max_dynamic_threshold`: Boundaries for the dynamic threshold to prevent it from being too low or too high.
    - **Dynamic Threshold**: Calculated using the median and median absolute deviation (MAD) of recent motion scores, ensuring the system adapts to environmental changes.

### 3. Motion Analysis and Azure Interaction

Once motion is detected, the module determines whether it is significant enough for further analysis:

- **Significant Motion Detection**:
  - If the current motion score exceeds the dynamic threshold, it is considered significant motion.
  - The dynamic threshold adapts over time based on recent motion scores, making the system responsive to changing conditions.

- **Azure Request Intervals**:
  - **Optimized API Usage**: The module sends images to Azure only at certain intervals, determined by `unknown_object_counter` and predefined `azure_request_intervals` (e.g., `[0, 1, 2, 3, 4, 10, 15, 20]`).

- **Azure Analysis**:
  - **Object Detection**: Azure analyzes the image to identify predefined objects based on `to_detect_object` and `azure_confidence_threshold`.
  - **Response Handling**: The module uses the response from Azure to decide whether to send notifications or save images.

### 4. Notification and Image Management

- **Detected Objects**:
  - **Notifications**: If Azure detects a target object with sufficient confidence, a notification is sent to the user.
  - **Image Saving**: The detected image is saved to the specified directory (`cam_frames_path`) and organized by day if enabled.
  - **State Management**: The `object_present` flag is set to `True`, indicating that the object is currently in the scene.

- **Unknown Objects**:
  - **Counter Increment**: If no target object is detected, the `unknown_object_counter` is incremented.
  - **Emergency Alerts**: If the counter reaches `max_unknown_object_counter`, an emergency notification is sent, and the reference image is updated to prevent repeated alerts.

- **Reference Image Update**:
  - **Adaptive Baseline**: The reference image is updated periodically when no significant motion is detected or when the object leaves the scene, maintaining accuracy in motion detection.

## Key Functions and Methods

- **`periodic_check`**
  - **Purpose**: Periodically fetches images, detects motion with adaptive scaling, analyzes images with Azure if significant motion is detected, and manages notifications and image saving.
  - **Workflow**:
    - **Initialization**: Sets up variables and paths, initializes parameters, and cleans old images.
    - **Periodic Loop**:
      - **Image Fetching**: Retrieves the latest image from the camera.
      - **Motion Detection**:
        - Processes the image to compute the `motion_score`.
        - Updates the `motion_history` and calculates the dynamic threshold.
        - Determines if the motion is significant based on the adaptive threshold.
      - **Azure Analysis**:
        - Sends the image to Azure at specified intervals for object detection.
        - Handles the Azure response, updating counters and managing notifications.
      - **Reference Image Management**: Updates the reference image when appropriate.
    - **Error Handling**: Catches and logs exceptions, ensuring robustness.

- **`calculate_scaled_thresholds`**
  - **Purpose**: Calculates motion detection thresholds based on image resolution and sensitivity settings.
  - **Parameters**:
    - `current_image`: The current image fetched from the camera.
    - `local_sensitivity_level`: User-defined sensitivity level (low, medium, high).
  - **Calculations**:
    - **Total Pixels**: Computes the total number of pixels in the image.
    - **Motion Threshold Percentage**: Determines the percentage of total pixels that constitute significant motion based on sensitivity.
    - **Thresholds**:
      - `motion_detection_min_area`: Minimum number of pixels that must change to be considered motion.
      - `min_dynamic_threshold` and `max_dynamic_threshold`: Boundaries for dynamic thresholding.

- **`process_image`**
  - **Purpose**: Processes the image and calculates the motion score.
  - **Workflow**:
    - **Image Conversion**: Converts the image to grayscale.
    - **Difference Calculation**: Computes the difference between the current image and the reference image.
    - **Thresholding**: Applies a threshold to emphasize significant differences.
    - **Cleaning**: Uses morphological filters to reduce noise.
    - **Motion Score Calculation**: Sums the pixels representing motion to compute the `motion_score`.

## Scenario-Based Workflow

- **Scenario 1: Significant Motion Detected Without Target Object**
  - **Motion Detection**: Significant motion is detected based on the adaptive threshold.
  - **Azure Analysis**: The image is sent to Azure for object detection at specified intervals.
  - **No Target Object Detected**:
    - **Counter Increment**: `unknown_object_counter` is incremented.
    - **Emergency Notification**: If the counter reaches `max_unknown_object_counter`, an emergency notification is sent.
    - **Reference Image Update**: The reference image is updated to prevent repeated alerts.

- **Scenario 2: Target Object Detected**
  - **Motion Detection**: Significant motion is detected.
  - **Azure Analysis**: Azure detects the target object.
  - **State Update**:
    - `object_present`: Set to `True`.
    - **Notification**: A notification is sent to the user.
    - **Image Saving**: The image is saved if enabled.
    - **Counter Reset**: `unknown_object_counter` is reset.

- **Scenario 3: Object Leaves the Scene**
  - **Motion Detection**: Motion score falls below the minimum area threshold.
  - **State Update**:
    - `object_present`: Set to `False`.
    - **Reference Image Update**: The reference image is updated to reflect the new scene.

## Counters and Logic

- **`unknown_object_counter`**:
  - Tracks the number of consecutive times significant motion is detected without recognizing a target object.
  - Resets when a target object is detected or when the reference image is updated after reaching the maximum count.

- **`azure_request_intervals`**:
  - Defines specific intervals at which images are sent to Azure for analysis.
  - Optimizes API usage by reducing the number of requests during prolonged motion without target object detection.

- **Ensuring Single Instance of `periodic_check`**
  - To prevent multiple instances from running simultaneously, each device should have only one running instance of `periodic_check`. This can be managed by tracking running tasks within `hass.data`.

## Monitoring and Debugging

- **Logging**: Extensive debug logging is implemented throughout the module to assist in monitoring the system's behavior and troubleshooting issues.

## Best Practices

- **Sensitivity Adjustment**: Users can adjust the sensitivity level (low, medium, high) based on their environment to optimize motion detection.
- **Manage API Costs**: Use `azure_request_intervals` wisely to control API requests and manage costs associated with Azure Cognitive Services.
- **Secure Configuration**: Protect Azure API keys and secure the Home Assistant instance to prevent unauthorized access.

## Conclusion

The `camera_processing` module ensures efficient and accurate motion and object detection by leveraging Azure's powerful AI capabilities and adaptive motion detection algorithms. Its design allows for customization and scaling based on user preferences and environmental conditions, making HomeAIVision a versatile tool for enhancing home automation and security.

With built-in notification handling and intelligent motion analysis, HomeAIVision provides a seamless experience, ensuring you are always informed about relevant events without the need for additional automations.

For more information on configuration and usage, refer to the **Configuration Guide**.
