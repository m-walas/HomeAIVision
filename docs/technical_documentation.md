# Technical Documentation

The technical documentation provides an in-depth look at the HomeAIVision integration's architecture, components, and workflows. This guide is intended for developers and advanced users who wish to understand or contribute to the integration's development.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Descriptions](#module-descriptions)
   - [Actions](#actions)
   - [Azure Client (azure_client.py)](#azure-client-azure_clientpy)
   - [Entities](#entities)
   - [Notification Manager (notification_manager.py)](#notification-manager-notification_managerpy)
   - [Save Image Manager (save_image_manager.py)](#save-image-manager-save_image_managerpy)
   - [Store (store.py)](#store-storepy)
   - [Strings (strings.json)](#strings-stringsjson)
3. [Data Flow](#data-flow)
4. [Key Functions and Workflows](#key-functions-and-workflows)
5. [Error Handling](#error-handling)
6. [Extensibility and Customization](#extensibility-and-customization)
7. [Security Considerations](#security-considerations)
8. [Contributing](#contributing)

## Architecture Overview

The HomeAIVision integration is designed to seamlessly integrate advanced AI vision capabilities into Home Assistant. It leverages Azure Cognitive Services to perform real-time object detection and motion analysis on camera feeds. The architecture consists of several interconnected modules, each responsible for specific functionalities:

- **Config Flow**: Handles the setup and configuration of the integration.
- **Camera Processing**: Manages image acquisition, motion detection, and communication with Azure.
- **Actions**: Defines custom actions that can be triggered from Home Assistant.
- **Azure Client**: Interfaces with Azure Cognitive Services for object detection.
- **Entities**: Represents sensors, numbers, and select entities within Home Assistant.
- **Notification Manager**: Handles sending notifications to users based on detection events.
- **Save Image Manager**: Manages saving and organizing images based on user settings.
- **Store**: Manages persistent storage of device configurations and counters.
- **Strings**: Contains translation strings for multi-language support.

## Module Descriptions

### Actions

**Purpose**: Defines custom actions that can be triggered from Home Assistant, such as manually analyzing an image or resetting counters.

- **Key Components**:
  - Action Definitions: `ACTION_MANUAL_ANALYZE`, `ACTION_RESET_LOCAL_COUNTER`, `ACTION_RESET_GLOBAL_COUNTER`
  - Action Handlers:
    - `handle_manual_analyze`: Performs a manual analysis by fetching an image from the camera, sending it to Azure for object detection, updating counters, saving the image, and sending notifications if enabled.

      ```yaml
      # example code
      service: homeaivision.manual_analyze
      data:
         device_id: "7280af57-a5d2-45a0-a806-e2e789e2092a"
      ```

    - `handle_reset_local_counter`: Resets the local Azure request counter for a specific device.

      ```yaml
      # example code
      service: homeaivision.reset_local_counter
      data:
         device_id: "7280af57-a5d2-45a0-a806-e2e789e2092a"
      ```

    - `handle_reset_global_counter`: Resets the global Azure request counter for all devices.

      ```yaml
      # example code
      service: homeaivision.reset_global_counter
      ```

### Azure Client (azure_client.py)

**Purpose**: Interfaces with Azure Cognitive Services to perform object detection on images.

- **Key Components**:
  - `analyze_image_with_azure`: Sends image data to Azure and processes the response to detect specified objects.
  - `extract_object_with_hierarchy`: Traverses detected objects to find matches based on a hierarchy.

### Entities

**Purpose**: Represents various sensors, numbers, and select entities within Home Assistant to monitor and configure HomeAIVision.

- **Key Components**:
  - **Base Entity**: `BaseHomeAIVisionEntity` serves as the base class for all entities, providing common attributes and initialization.
  - **Sensor Entities**:
    - `AzureRequestCountEntity`: Tracks the number of Azure requests made per device.
    - `CameraUrlEntity`: Displays a censored version of the camera URL for privacy.
    - `DeviceIdEntity`: Shows the unique device ID.
    - `NotificationEntity`: Indicates whether notifications are enabled.
  - **Configuration Entities**:
    - `ConfidenceThresholdEntity`: Allows users to set the confidence threshold for object detection.
    - `MotionDetectionIntervalEntity`: Lets users configure the interval between motion detection checks.
    - `DetectedObjectEntity`: Enables selection of which objects to detect.

### Notification Manager (notification_manager.py)

**Purpose**: Handles the creation and sending of notifications to users based on detection events.

- **Key Components**:
  - `send_notification`: Sends a notification with an optional image attachment using Home Assistant's notification service.
  - **Translation Handling**:
    - `load_translations`: Loads translation files based on the selected language.
    - `get_translated_message`: Retrieves the translated message for a given key.

### Save Image Manager (save_image_manager.py)

**Purpose**: Manages the saving, organizing, and cleaning of images captured by the integration.

- **Key Components**:
  - `save_image`: Saves images to the designated directory, organizing them by day if configured, and enforces storage limits.
  - `clean_up_old_images`: Removes images that exceed the retention policy based on the number of days to keep.

### Store (store.py)

**Purpose**: Manages persistent storage of device configurations, counters, and global settings.

- **Key Components**:
  - **Data Classes**:
    - `DeviceData`: Represents data for a single device.
    - `GlobalData`: Represents global data for the integration.
  - `HomeAIVisionStore`: Handles loading, saving, and managing device data and counters, including adding, updating, and removing devices.

### Strings (strings.json)

**Purpose**: Contains translation strings for multi-language support, enabling the integration to provide messages in various languages.

- **Key Components**:
  - **Configuration Steps**: Titles and descriptions for setup steps.
  - **Error Messages**: Descriptions of common errors.
  - **User Messages**: Notification messages for detected objects and other events.
  - **Selectors**: Options for language selection, actions, and objects to detect.

## Data Flow

### Initialization

1. User configures the integration via the Config Flow (`config_flow.py`).
2. `HomeAIVisionStore` loads existing device configurations and global data.

### Image Acquisition

- `camera_processing.py` periodically fetches images from each configured camera using `aiohttp`.

### Motion Detection

- Compares the current image with a reference image to detect motion using `detect_motion`.
- Calculates a motion score to determine the significance of the detected motion.

### Azure Analysis

- If significant motion is detected, the image is sent to Azure Cognitive Services via `azure_client.py` for object detection.
- The response from Azure is processed to identify specified objects with sufficient confidence.

### Notification and Image Saving

- Based on Azure's response, notifications are sent to the user using `notification_manager.py`.
- Images with detected objects are saved using `save_image_manager.py` according to user-defined settings.

### Reference Image Update

- The reference image is updated to adapt to changes in the environment, ensuring accurate future motion detections.

### Action Handling

- Users can trigger custom actions (e.g., manual analysis, resetting counters) using the Actions module.

   ***Note:*** *You can read more about the action (services) [here](https://developers.home-assistant.io/docs/dev_101_services).*

## Key Functions and Workflows

### handle_manual_analyze

- **Purpose**: Performs a manual analysis by fetching an image from the camera, sending it to Azure for object detection, updating counters, saving the image, and sending notifications if enabled.

### analyze_image_with_azure

- **Purpose**: Sends the image to Azure Cognitive Services for object detection and processes the response to identify specified objects.

### send_notification

- **Purpose**: Sends a notification to the user with an optional image attachment based on detected objects.

### save_image

- **Purpose**: Saves an image to the filesystem, organizing it into daily folders if configured, and enforcing storage limits.

### HomeAIVisionStore.async_load

- **Purpose**: Loads device data and global data from persistent storage.

### strings.json

- **Purpose**: Provides translation strings for various languages, enabling multi-language support within the integration.

## Error Handling

- **Connection Errors**:
  - **Camera Connection**: If the integration fails to connect to the camera, it logs an error and creates a persistent notification in Home Assistant to alert the user.
  - **Azure Connection**: Errors while connecting to Azure Cognitive Services are logged, and appropriate notifications are sent if necessary.
- **Image Processing Errors**:
  - Handles errors related to opening or processing images, ensuring that the system continues to operate smoothly without crashing.
- **API Rate Limits**:
  - Monitors the number of API requests to Azure to prevent exceeding rate limits.
- **Unexpected Exceptions**:
  - Catches and logs all unexpected exceptions with full tracebacks for debugging purposes.

## Extensibility and Customization

- **Adding New Detection Objects**: Users can add support for new objects by updating the `to_detect_object` configuration.
- **Integrating Additional Notification Platforms**: The Notification Manager can be extended to support additional notification platforms supported by Home Assistant.
- **Customizing Motion Detection Algorithms**: Parameters such as `motion_detection_min_area`, `motion_detection_history_size`, and `motion_detection_interval` can be adjusted for optimal performance.
- **Manual Actions**: Users can trigger manual actions such as manual analysis of camera feeds or resetting counters through Home Assistant's service calls.

## Security Considerations

- **API Key Management**: Azure API keys are securely stored within Home Assistant's configuration and are not exposed in logs or notifications.
- **Data Privacy**: Only necessary image data is sent to Azure for processing, adhering to best practices for data privacy.
- **Access Control**: Ensure that Home Assistant is secured with strong authentication mechanisms to prevent unauthorized access to the integration's settings and data.

## Contributing

Contributions to the HomeAIVision integration are welcome! Whether you're a developer looking to add new features or a user who wants to report an issue, your input is valuable.

1. **Development Setup**: Fork the repository, clone your fork, set up a virtual environment, install dependencies, and run Home Assistant in development mode.
2. **Coding Standards**: Follow Python's PEP 8 style guide for code formatting.
3. **Submitting Issues and Pull Requests**: Report bugs or suggest enhancements by opening an issue on GitHub, and submit pull requests with your proposed changes.
4. **Community Guidelines**: Be respectful and considerate in all interactions.

---

This documentation provides a foundation for understanding and working with HomeAIVision’s code and architecture. Happy contributing!
