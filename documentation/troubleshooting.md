# Troubleshooting

If you encounter issues while using HomeAIVision, this section provides solutions to common problems.

## 1. Azure Credentials Invalid

**Symptom**: During configuration, you receive an error stating that your Azure credentials are invalid.

**Solution**:

- **Verify API Key**: Ensure that the Azure API key entered is correct. You can find it in your Azure portal under Cognitive Services.
- **Check Endpoint URL**: Confirm that the endpoint URL is accurate and corresponds to the region of your Azure Cognitive Services.
- **API Permissions**: Ensure that the API key has the necessary permissions to access the Cognitive Services.

## 2. Camera URL Invalid

**Symptom**: An error message indicates that the camera URL is invalid.

**Solution**:

- **URL Format**: Ensure the camera URL starts with `http://` or `https://`.
- **Accessibility**: Verify that the camera stream is accessible from the network where Home Assistant is running. You can test this by opening the URL in a web browser on the same network.
- **Firewall Settings**: Check if any firewall or network settings are blocking access to the camera URL.

## 3. Device Not Found

**Symptom**: When trying to edit or remove a camera, an error states that the selected device was not found.

**Solution**:

- **Device ID**: Ensure that the device ID is correct and corresponds to an existing camera in the integration.
- **Data Corruption**: There might be corruption in the configuration data. Try restarting Home Assistant or re-adding the integration.
- **Logs**: Check Home Assistant logs for any related error messages that can provide more context.

## 4. Failed to Remove Device

**Symptom**: An error occurs when attempting to remove a camera from the integration.

**Solution**:

- **Permissions**: Ensure that Home Assistant has the necessary permissions to modify the device registry.
- **Manual Removal**: As a last resort, you can manually remove the device from the Home Assistant device registry via the UI or by editing the configuration files.
- **Logs**: Review the Home Assistant logs to identify specific errors that occurred during the removal process.

## 5. No Cameras Available

**Symptom**: When attempting to edit or remove a camera, an error indicates that there are no cameras available.

**Solution**:

- **Add a Camera**: Ensure that at least one camera has been added to the integration.
- **Configuration Check**: Verify that the camera was added successfully and is present in the `store.py` data.
- **Integration Status**: Ensure that the HomeAIVision integration is properly installed and loaded in Home Assistant.

## 6. Notifications Not Received

**Symptom**: Notifications are not being sent when objects are detected.

**Solution**:

- **Notification Service**: Ensure that a notification service is correctly set up in Home Assistant.
- **Integration Settings**: Check that the `send_notifications` option is enabled in the integration settings.
- **Logs**: Look into Home Assistant logs for any errors related to notification services.

## 7. High Motion Detection False Positives

**Symptom**: The integration frequently detects motion where there is none.

**Solution**:

- **Sensitivity Settings**: Adjust the `motion_detection_min_area` and `confidence_threshold` settings to better suit your environment.

    *Note*: Please refer to the [Camera Processing Documentation](camera_processing.md) for a better explanation and understanding of how camera images are analyzed.

- **Lighting Conditions**: Ensure consistent lighting to reduce false positives caused by shadows or flickering lights.
- **Camera Quality**: Higher resolution cameras provide better image quality, which can improve motion detection accuracy.

## 8. Image Saving Issues

**Symptom**: Images are not being saved as configured.

**Solution**:

- **Storage Path**: Ensure that the path specified for saving images is correct and writable by Home Assistant.
- **Disk Space**: Verify that there is sufficient disk space available for storing images.
- **Organizing by Day**: If organizing by day is enabled, ensure that the directory structure is being created properly.
- **Logs**: Check Home Assistant logs for any errors related to file saving or permissions.

## 9. Motion Detection Not Working Properly

**Symptom**: System does not detect motion or detects it too frequently/infrequently.

**Solution**:

- **Adjust Motion Detection Parameters**:
  - `motion_detection_min_area`: Increase if there are too many false positives.
  - `motion_detection_history_size`: Adjust to fine-tune dynamic thresholding.
  - `motion_detection_interval`: Ensure it's set to an appropriate value for your needs.
- **Lighting Conditions**: Maintain consistent lighting to improve detection accuracy.
- **Camera Quality**: Use a higher resolution camera for better image processing.

**Example Code Snippet**:

## 10. High CPU Usage

**Symptom**: Home Assistant operates slowly or consumes excessive CPU resources.

**Solution**:

- **Optimize Motion Detection Parameters**:
  - **Reduce `motion_detection_interval`**: Increasing the interval between checks can reduce CPU load.
- **Image Resolution**: Lowering image resolution can decrease processing overhead.
- **Hardware Limitations**: Ensure that the device running Home Assistant has adequate processing power.

## 11. Azure API Rate Limits Exceeded

**Symptom**: Integration stops working or Azure requests fail due to exceeded rate limits.

**Solution**:

- **Monitor API Usage**: Check your Azure portal to monitor API usage and ensure you are within your subscription limits.
- **Increase API Limits**: Upgrade your Azure Cognitive Services plan if you frequently exceed limits.
- **Optimize Azure Requests**: Ensure that unnecessary requests are minimized using `unknown_object_counter` and appropriate intervals.

## 12. Persistent Notifications Not Appearing

**Symptom**: Persistent notifications do not show up in Home Assistant interface.

**Solution**:

- **Check Notification Settings**: Ensure that notifications are enabled in the integration settings.
- **Review Logs**: Look for any errors related to notification services in Home Assistant logs.
- **Notification Service Availability**: Verify that the chosen notification platform (e.g., `notify.mobile_app`) is correctly configured and operational.

## 13. Connection Issues with Camera

**Symptom**: Unable to connect to the camera at the specified URL.

**Solution**:

- **Verify Camera Status**: Ensure that the camera is powered on and connected to the network.
- **Check Camera URL**: Confirm that the camera URL is correct and accessible from the Home Assistant server.
- **Network Configuration**: Ensure there are no network issues or firewall settings blocking access to the camera.

**Example Code Snippet**:

```python
async def fetch_image(session, cam_url):
    async with session.get(cam_url, timeout=30) as response:
        if response.status == 200:
            return await response.read()
        else:
            raise ValueError(f"Failed to fetch image, status code: {response.status}")
```

## 14. Errors During Motion Detection

**Symptom**: Errors occur during the motion detection process, causing the integration to fail.

**Solution**:

- **Check Image Processing**: Ensure that the images fetched from the camera are in a compatible format and not corrupted.
- **Review Motion Detection Parameters**: Incorrect parameters can cause the motion detection algorithms to malfunction. Adjust settings as needed.
- **Update Dependencies**: Make sure all required Python libraries (e.g., PIL, aiohttp) are up to date.

**Example Code Snippet**:

```python
def detect_motion(reference_image, current_image):
    diff_image = ImageChops.difference(reference_image, current_image)
    threshold = diff_image.point(lambda p: p > 50 and 255)
    cleaned = threshold.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    motion_score = sum(cleaned.histogram()[255:])
    return motion_score
```

## Contact Support

If you've tried the above solutions and still encounter issues, please reach out for support:

- **GitHub Issues**: Report your issue on the HomeAIVision [Issues Page](https://github.com/m-walas/HomeAIVision/issues).
- **Community Forums**: Seek help from the Home Assistant community on the [Home Assistant Forums](https://community.home-assistant.io/).

When reporting an issue, provide as much detail as possible, including:

- Steps to reproduce the issue.
- Relevant configuration settings.
- Log excerpts related to the problem.

Your feedback is invaluable in improving HomeAIVision!
