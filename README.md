# HomeAIVision Integration for Home Assistant

![HomeAIVision Banner](baner.jpg)

Welcome to **HomeAIVision**! I'm here to make your home safer and smarter by bringing advanced AI vision capabilities right into your Home Assistant setup. Utilizing Azure Cognitive Services, I can analyze your home camera feed in real-time to detect human presence, ensuring that you only receive notifications that matter.

![Home Assistant](https://img.shields.io/badge/Home_Assistant-Custom_Component-blue.svg?style=for-the-badge&logo=homeassistant)
![Azure Cognitive Services](https://img.shields.io/badge/Azure_Cognitive_Services-Enabled-lightgrey.svg?style=for-the-badge&logo=microsoftazure)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Buy me a coffee](https://img.shields.io/badge/Buy_me_a_coffee-Donate-orange.svg?style=for-the-badge&logo=buymeacoffee)](https://buymeacoffee.com/mwalas)

## Prerequisites

Before installing HomeAIVision, ensure you have:

- **Home Assistant Installation**: Running locally, on a device like a Raspberry Pi, or a VM.
- **Camera Setup**: Accessible via a URL, testable in a web browser.
- **Azure Account**: Active account with an API key and endpoint URL from Azure Cognitive Services.

## Installation

1. **Download the Integration**:
   - Navigate to the [GitHub repository](https://github.com/m-walas/HomeAIVision).
   - Download and extract the ZIP file.

2. **Install the Custom Component**:
   - Create a `custom_components` directory in your Home Assistant configuration directory (`/config`) if it does not already exist.
   - Copy the `homeaivision` folder into the `custom_components` directory.

3. **Restart Home Assistant**:
   - Necessary to load the new integration. Restart via the server management page or service.

4. **Add the Integration**:
   - Go to **Configuration** > **Integrations**.
   - Click **Add Integration** and search for **HomeAIVision**.
   - Enter your Azure API key, endpoint, and camera URL as prompted.

## Configuration

### Initial Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| `azure_api_key` | Azure Cognitive Services API key. | N/A |
| `azure_endpoint` | Endpoint URL for Azure Cognitive Services. | N/A |
| `cam_url` | URL to access the camera feed. | N/A |
| `time_between_requests` | Seconds between image requests. | `30` |
| `send_notifications` | Enable or disable notifications. | `False` |
| `organize_by_day` | Organize saved images by day. | `True` |

### Additional Options
| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_images` | Max images per folder or in total. | `30` |
| `days_to_keep` | Days to keep images if organized by day. | `7` |
| `notification_language` | Notification language. | `English` |

## Features

- **Human Detection**: Uses AI to identify human presence.
- **Notifications**: Alerts sent to devices upon detection.
- **Image Saving**: Saves images where humans are detected.

## Troubleshooting

- Verify Azure API and endpoint accuracy.
- Ensure the camera URL is accessible from your Home Assistant setup.
- Review Home Assistant logs for errors related to this integration.

## Support the Project

Encounter issues or have suggestions? Please report them on our [Issues page](https://github.com/m-walas/HomeAIVision/issues). Your feedback helps improve HomeAIVision!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.