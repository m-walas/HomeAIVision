# Configuration Guide

Once HomeAIVision is installed, you can configure it to suit your needs. This guide walks you through the available settings and how to customize them.

## Installation and Initial Configuration

### Prerequisites

Before installing HomeAIVision, ensure you have the following:

- **Home Assistant Installation**: Running locally, on a device like a Raspberry Pi, or a VM. More details can be found here.
- **Camera Setup**: Accessible via a URL, testable in a web browser. Ensure your camera stream is accessible from the network Home Assistant is on.
- **Azure Account**: Active account with an API key and endpoint URL from Azure Cognitive Services. Get your API key here.

### Step-by-Step Installation and Configuration

1. **Download the Integration**:
   - Visit the GitHub repository.
   - Click on the 'Code' button and select 'Download ZIP'. Extract the file.

2. **Install the Custom Component**:
   - Ensure a `custom_components` directory exists in your Home Assistant configuration directory (`/config`).
   - Copy the `homeaivision` folder from the extracted ZIP into the `custom_components` directory.

3. **Restart Home Assistant**:
   - This step is necessary to recognize the new integration. Restart via the server management page or restart the Home Assistant service.

4. **Add the Integration**:
   - Navigate to **Configuration > Integrations** in Home Assistant.
   - Click on **Add Integration** and search for **HomeAIVision**.
   - Fill in your Azure API key, endpoint URL, and integration title as prompted. These can be obtained from your Azure Cognitive Services account.

## Initial Configuration

After adding the integration, you will need to configure the global settings and add your camera devices. The configuration is divided into two main sections:

- **Global Settings**: Azure credentials and integration-wide preferences.
- **Device Settings**: Individual camera configurations and detection parameters.

### Global Settings

| Parameter              | Description                                     | Default |
|------------------------|-------------------------------------------------|---------|
| `azure_api_key`        | Azure Cognitive Services API key.               |         |
| `azure_endpoint`       | Endpoint URL for Azure Cognitive Services.      |         |
| `language`             | Language for notifications and interface elements. | `en` |

### Device Settings

For each camera device you add, you can configure the following parameters:

| Parameter                  | Description                                            | Default   |
|----------------------------|--------------------------------------------------------|-----------|
| `name`                     | Friendly name for the camera.                          | `Camera`  |
| `cam_url`                  | URL to access the camera feed.                         |           |
| `send_notifications`       | Enable or disable notifications upon detection.        | `False`   |
| `organize_by_day`          | Organize saved images by day.                          | `True`    |
| `max_images`               | Maximum number of images to store per folder or in total. | `30`     |
| `days_to_keep`             | Number of days to keep images if organized by day.     | `7`       |
| `to_detect_object`         | Select which objects to detect (e.g., person, car, cat, dog). | `person` |
| `azure_confidence_threshold` | Minimum confidence threshold for detections.        | `0.6`     |
| `motion_detection_min_area` | Minimum area (in pixels) for motion detection.        | `6000`    |
| `motion_detection_history_size` | Number of historical motion scores to maintain for dynamic thresholding. | `10`  |
| `motion_detection_interval` | Interval (in seconds) between motion detection checks. | `5`       |

### Configuration Parameters

#### 1. Global Settings

These settings apply to the entire HomeAIVision integration and are configured during the initial setup.

| Parameter                  | Description                                     | Default |
|----------------------------|-------------------------------------------------|---------|
| `azure_api_key`            | Your Azure Cognitive Services API key.          |         |
| `azure_endpoint`           | The endpoint URL for your Azure Cognitive Services. |       |
| `language`                 | Language for notifications and interface elements. | `en`   |

**Example Configuration:**

```yaml
homeaivision:
  azure_api_key: "your_azure_api_key"
  azure_endpoint: "https://your-azure-endpoint.cognitiveservices.azure.com/"
  language: "en"
```

#### 2. Device Settings

Each camera device added to HomeAIVision can be individually configured with the following parameters:

| Parameter                  | Description                                            | Default   |
|----------------------------|--------------------------------------------------------|-----------|
| `name`                     | Friendly name for the camera.                          | `Camera`  |
| `cam_url`                  | URL to access the camera feed.                         |           |
| `send_notifications`       | Enable or disable notifications upon detection.        | `False`   |
| `organize_by_day`          | Organize saved images by day.                          | `True`    |
| `max_images`               | Maximum number of images to store per folder or in total. | `30`     |
| `days_to_keep`             | Number of days to keep images if organized by day.     | `7`       |
| `to_detect_object`         | Select which objects to detect (e.g., person, car, cat, dog). | `person` |
| `azure_confidence_threshold` | Minimum confidence threshold for detections.        | `0.6`     |
| `motion_detection_min_area` | Minimum area (in pixels) for motion detection.        | `6000`    |
| `motion_detection_history_size` | Number of historical motion scores to maintain for dynamic thresholding. | `10`  |
| `motion_detection_interval` | Interval (in seconds) between motion detection checks. | `5`       |

**Example Configuration:**

```yaml
homeaivision:
  devices:
    - name: "Front Door Camera"
      cam_url: "http://camera.local/stream"
      send_notifications: true
      organize_by_day: true
      max_images: 50
      days_to_keep: 10
      to_detect_object: "person"
      azure_confidence_threshold: 0.7
      motion_detection_min_area: 8000
      motion_detection_history_size: 15
      motion_detection_interval: 5
```

### Configuration Flow Overview

HomeAIVision uses a configuration flow to guide you through setting up the integration and adding camera devices. The process consists of the following steps:

**User Step**:

- **Integration Title**: Assign a friendly name to your HomeAIVision integration.

**Azure Configuration Step**:

- **Azure API Key**: Enter your Azure Cognitive Services API key.
- **Azure Endpoint**: Enter the endpoint URL for your Azure Cognitive Services.
- **Language**: Select the language for notifications and interface elements.

**Options Flow**:

- **Action Selection**: Choose to add, edit, or remove a camera device.

1. **Add Camera**:
   - **Camera Settings**: Configure basic settings such as name and camera URL.
   - **Detection Settings**: Configure object detection parameters and motion detection settings.

2. **Edit Camera**:
   - **Camera Settings**: Update camera name and URL.
   - **Detection Settings**: Update detection parameters and motion detection settings.

3. **Remove Camera**: Select and remove an existing camera device.

*Note*: Refer to the [Technical Documentation](technical_documentation.md) for a detailed explanation of each configuration step and the underlying processes.

### Advanced Settings

For advanced configurations, such as customizing motion detection parameters and object detection thresholds beyond the initial setup, refer to the [Technical Documentation](technical_documentation.md).

## Changing Configuration

To update settings after the initial setup:

- Navigate to **Configuration > Integrations** in Home Assistant.
- Find **HomeAIVision** and click on **Options**.
- Choose an action:
  - **Add Device**: Add a new camera device.
  - **Edit Device**: Modify settings of an existing camera.
  - **Remove Device**: Remove an existing camera from the integration.

Follow the prompts to adjust settings as needed and save changes.

## Adding a New Camera Device

- Go to **Configuration > Integrations > HomeAIVision > Options**.
- Select **Add Device**.
- Enter the camera's name and URL.
- Configure detection settings, including objects to detect, confidence thresholds, and motion detection parameters.
- Save the configuration to add the new camera to HomeAIVision.

## Editing an Existing Camera Device

- Go to **Configuration > Integrations > HomeAIVision > Options**.
- Select **Edit Device**.
- Choose the camera you want to modify.
- Update the desired settings and save changes.

## Removing a Camera Device

- Go to **Configuration > Integrations > HomeAIVision > Options**.
- Select **Remove Device**.
- Choose the camera you want to remove.
- Confirm the removal to delete the camera from HomeAIVision.

### Best Practices

- **Secure Your Azure Credentials**: Keep your Azure API key and endpoint URL confidential. Do not expose them in public repositories or unsecured locations.
- **Optimize Motion Detection Parameters**: Adjust `motion_detection_min_area` and `motion_detection_history_size` to reduce false positives and enhance detection accuracy based on your environment.
- **Regularly Review Saved Images**: Monitor and manage saved images to ensure you are only storing relevant data and not exceeding storage limits.
- **Update Integration Regularly**: Keep HomeAIVision updated to benefit from the latest features, improvements, and security patches.

For more detailed technical information and troubleshooting, refer to the respective sections in the **[Full Documentation](README.md)**.
