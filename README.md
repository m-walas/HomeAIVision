# HomeAIVision Integration for Home Assistant

![HomeAIVision Banner](images/baner.png)

Welcome to **HomeAIVision**! I'm here to make your home safer and smarter by bringing advanced AI vision capabilities right into your Home Assistant setup. Utilizing Azure Cognitive Services, I can analyze your home camera feed in real-time to detect human presence and other objects, ensuring that you only receive notifications that matter.

![Home Assistant](https://img.shields.io/badge/Home_Assistant-Custom_Component-blue.svg?style=for-the-badge&logo=homeassistant)
![Azure Cognitive Services](https://img.shields.io/badge/Azure_Cognitive_Services-Enabled-lightgrey.svg?style=for-the-badge&logo=microsoftazure)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

## Overview

HomeAIVision leverages Azure Cognitive Services to provide intelligent object detection and motion analysis from your camera feeds. Whether you're looking to enhance home security or monitor activity, HomeAIVision offers a reliable and customizable solution.

For detailed information on installation, configuration, and technical aspects, please refer to the [Full Documentation](docs/README.md).

## Installation and Configuration

Before installing HomeAIVision, ensure you have the following prerequisites:

- **Home Assistant Installation**: Running locally, on a device like a Raspberry Pi, or a VM. More details can be found [here](https://www.home-assistant.io/installation/).
- **Camera Setup**: Accessible via a URL, testable in a web browser. Ensure your camera stream is accessible from the network Home Assistant is on.
- **Azure Account**: Active account with an API key and endpoint URL from Azure Cognitive Services. [Get your API key here](https://portal.azure.com/).

### Step-by-Step Installation and Configuration

1. **Download the Integration**:
   - Visit the [GitHub repository](https://github.com/m-walas/HomeAIVision).
   - Click on the 'Code' button and select 'Download ZIP'. Extract the file.

2. **Install the Custom Component**:
   - Ensure a `custom_components` directory exists in your Home Assistant configuration directory (`/config`).
   - Copy the `homeaivision` folder from the extracted ZIP into the `custom_components` directory.

3. **Restart Home Assistant**:
   - This step is necessary to recognize the new integration. Restart via the server management page or restart the Home Assistant service.

4. **Add the Integration**:
   - Navigate to **Configuration** > **Integrations** in Home Assistant.
   - Click on **Add Integration** and search for **HomeAIVision**.
   - Fill in your Azure API key, endpoint URL, and camera URL as prompted. These can be obtained from your Azure Cognitive Services account.

5. **Configure Detection Settings**:
   - After adding the integration, go to **Configuration** > **Integrations** > **HomeAIVision** > **Options**.
   - Configure detection settings such as objects to detect, confidence thresholds, motion detection parameters, notification preferences, and image saving options.

### Configuration Parameters

#### Initial Configuration

| Parameter                     | Description                                           | Default |
|-------------------------------|-------------------------------------------------------|---------|
| `azure_api_key`               | Azure Cognitive Services API key.                     |         |
| `azure_endpoint`              | Endpoint URL for Azure Cognitive Services.            |         |
| `cam_url`                     | URL to access the camera feed.                        |         |
| `send_notifications`          | Enable or disable notifications.                      | `False` |
| `to_detect_object`            | Select which objects to detect (e.g., person, car).   | `person`|
| `azure_confidence_threshold`  | Minimum confidence threshold for detections.          | `0.6`   |
| `motion_detection_min_area`   | Minimum area for motion detection.                    | `6000`  |
| `motion_detection_history_size`| History size for motion detection.                   | `10`    |
| `motion_detection_interval`   | Interval (in seconds) between motion detection checks.| `5`     |

#### Additional Options

| Parameter                | Description                                       | Default |
|--------------------------|---------------------------------------------------|---------|
| `max_images`             | Max images per device.                            | `100`    |
| `days_to_keep`           | Days to keep images.                              | `30`     |
| `notification_language`  | Notification language.                            | `English` |

![config_flow](images/config_flow.png)

For more detailed configuration options and advanced settings, refer to the [Configuration Guide](docs/configuration.md).

## Features

- **Object Detection**: Utilizes Azure Cognitive Services to identify objects such as persons, cars, cats, and dogs in the camera feed.
- **Notifications**: Alerts are sent to your devices upon detection of specified objects, ensuring you're always informed about relevant events.
- **Image Saving**: Captures and saves images where specified objects are detected, organizing them based on your settings for easy access and review.
- **Motion Detection**: Detects motion in the camera feed using pixel difference analysis to trigger object detection only when necessary, optimizing performance and reducing unnecessary API calls.

## Actions

HomeAIVision provides several actions that you can trigger manually or automate within Home Assistant. These actions allow you to interact with the integration's functionality directly from your Home Assistant interface or through automations.

### Available Actions

#### Manual Analyze (`manual_analyze`)

- **Description**: Performs a manual analysis by fetching an image from the camera, sending it to Azure for object detection, updating counters, saving the image, and sending notifications if enabled.
- **Use Case**: Useful for on-demand analysis when you want to check the current state without waiting for the next scheduled motion detection.

#### Reset Local Counter (`reset_local_counter`)

- **Description**: Resets the local Azure request counter for a specific device. This is useful for tracking the number of API requests made by each device individually.
- **Use Case**: Helps in managing and monitoring API usage per device, ensuring that individual devices do not exceed their allotted API calls.

#### Reset Global Counter (`reset_global_counter`)

- **Description**: Resets the global Azure request counter that tracks the total number of API requests made by all devices combined.
- **Use Case**: Useful for resetting the total count monthly or at regular intervals to align with Azure's free tier limits and monitor overall usage.

### Example Automation: Reset Global Azure Request Counter Monthly

To ensure that your integration does not exceed the Azure free tier limit of 5,000 API requests per month, it is a good practice to reset the global counter at the beginning of each month. This helps monitor the use of sent queries by all devices.

***Note:*** *Remember, the first 12 months of Azure Cognitive Services entitles you to send 5,000 queries per month free of charge.*

#### Automation YAML Example

```yaml
automation:
  - alias: "Reset Global Azure Request Counter Monthly"
    trigger:
      - platform: time
        at: "00:00"
        date: "1" # The first day of the month
    action:
      - service: homeaivision.reset_global_counter
```

### Explanation

- **Trigger**: The automation is set to trigger at midnight on the first day of every month.
- **Action**: Calls the `homeaivision.reset_global_counter` service to reset the global API request counter.

### Benefits

- **Monitoring**: Helps keep track of monthly API usage and ensures you stay within the free tier limits.
- **Cost Management**: Prevents unexpected charges by resetting the counter, allowing you to monitor usage effectively.

For more detailed examples and advanced automations, refer to the [Full Documentation](docs/README.md).

## Technical Documentation

For a comprehensive technical overview of the integration, including architecture, components, workflows, and detailed module descriptions, refer to the [Technical Documentation](docs/technical_documentation.md).

## Camera Processing

Understand how HomeAIVision processes camera feeds, detects motion, and interacts with Azure Cognitive Services by reading the [Camera Processing Details](docs/camera_processing.md).

## Troubleshooting

If you encounter issues, refer to the [Troubleshooting Guide](docs/troubleshooting.md) for solutions to common problems.

## Support the Project

If you like HomeAIVision and find it useful, consider giving it a ⭐ on [GitHub](https://github.com/m-walas/HomeAIVision)! Your support encourages further development and helps others discover the project.

Encounter issues or have suggestions? Please report them on our [Issues page](https://github.com/m-walas/HomeAIVision/issues). Your feedback is invaluable and helps improve HomeAIVision!

[![Buy me a coffee](https://img.shields.io/badge/Buy_me_a_coffee-Donate-orange.svg?style=for-the-badge&logo=buymeacoffee)](https://buymeacoffee.com/mwalas)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
