# Troubleshooting

If you encounter issues while using HomeAIVision, this section provides solutions to common problems.

## 1. Azure Credentials Invalid

**Symptom**: During configuration, you receive an error stating that your Azure credentials are invalid.

**Solution**:

- Verify API Key: Ensure that the Azure API key entered is correct. You can find it in your Azure portal under Cognitive Services.
- Check Endpoint URL: Confirm that the endpoint URL is accurate and corresponds to the region of your Azure Cognitive Services.
- API Permissions: Ensure that the API key has the necessary permissions to access the Cognitive Services.

## 2. Camera URL Invalid

**Symptom**: An error message indicates that the camera URL is invalid.

**Solution**:

- URL Format: Ensure the camera URL starts with `http://` or `https://`.
- Accessibility: Verify that the camera stream is accessible from the network where Home Assistant is running. You can test this by opening the URL in a web browser on the same network.
- Firewall Settings: Check if any firewall or network settings are blocking access to the camera URL.

## 3. Device Not Found

**Symptom**: When trying to edit or remove a camera, an error states that the selected device was not found.

**Solution**:

- Device ID: Ensure that the device ID is correct and corresponds to an existing camera in the integration.
- Data Integrity: There might be issues with the configuration data. Try restarting Home Assistant or re-adding the integration.
- Logs: Check Home Assistant logs for any related error messages that can provide more context.

## 4. Failed to Remove Device

**Symptom**: An error occurs when attempting to remove a camera from the integration.

**Solution**:

- Permissions: Ensure that Home Assistant has the necessary permissions to modify the device registry.
- Manual Removal: As a last resort, you can manually remove the device from the Home Assistant device registry via the UI or by editing the configuration files.
- Logs: Review the Home Assistant logs to identify specific errors that occurred during the removal process.

## 5. No Cameras Available

**Symptom**: When attempting to edit or remove a camera, an error indicates that there are no cameras available.

**Solution**:

- Add a Camera: Ensure that at least one camera has been added to the integration.
- Configuration Check: Verify that the camera was added successfully and is present in the integration's data store.
- Integration Status: Ensure that the HomeAIVision integration is properly installed and loaded in Home Assistant.

## 6. Notifications Not Received

**Symptom**: Notifications are not being sent when objects are detected.

**Solution**:

- Notification Service: Ensure that a notification service is correctly set up in Home Assistant.
- Integration Settings: Check that the `send_notifications` option is enabled in the integration settings.
- Logs: Look into Home Assistant logs for any errors related to notification services.

## 7. Motion Detection Too Sensitive or Not Sensitive Enough

**Symptom**: The integration frequently detects motion when there is none (false positives) or fails to detect motion when it occurs (false negatives).

**Solution**:

- Adjust Sensitivity Level: HomeAIVision allows you to set the sensitivity level (low, medium, high) for motion detection.
  - **Low Sensitivity**: Use this setting if you're experiencing too many false positives. It requires more significant changes in the image to detect motion.
  - **High Sensitivity**: Use this setting if the system is not detecting motion when it should. It will detect smaller changes in the image.
- Modify Motion Detection Parameters:
  - `motion_detection_interval`: Adjust the interval between motion detection checks. A shorter interval may improve responsiveness but increase CPU usage.
- Consistent Lighting: Ensure that the environment has consistent lighting conditions to reduce false detections caused by shadows or light changes.
- Camera Positioning: Adjust the camera angle or position to reduce background movements (like trees or traffic) that might trigger motion detection.

## 8. Image Saving Issues

**Symptom**: Images are not being saved as configured.

**Solution**:

- Storage Path: Ensure that the path specified for saving images (`cam_frames_path`) is correct and writable by Home Assistant.
- Disk Space: Verify that there is sufficient disk space available for storing images.
- File Permissions: Check that Home Assistant has the necessary permissions to write to the specified directory.
- Logs: Check Home Assistant logs for any errors related to file saving or permissions.

## 9. Motion Detection Not Working Properly

**Symptom**: The system does not detect motion or detects it too frequently/infrequently.

**Solution**:

- Adjust Sensitivity Settings:
  - `local_sensitivity_level`: Change the sensitivity level in the device configuration to better suit your environment.
- Verify Camera Feed: Ensure that the camera feed is providing clear images. Blurry or low-quality images can affect motion detection accuracy.
- Consistent Environment: Ensure that there are no repetitive movements in the environment (like a rotating fan) that could affect motion detection.

## 10. High CPU Usage

**Symptom**: Home Assistant operates slowly or consumes excessive CPU resources.

**Solution**:

- Optimize Motion Detection Interval:
  - Increase `motion_detection_interval`: Increasing the interval between motion detection checks can reduce CPU load.
- Adjust Image Resolution:
  - Lower Image Resolution: Use a lower resolution stream from the camera to decrease processing overhead.
- Hardware Limitations:
  - Upgrade Hardware: Ensure that the device running Home Assistant has adequate processing power to handle image processing tasks.

## 11. Azure API Rate Limits Exceeded

**Symptom**: Integration stops working or Azure requests fail due to exceeded rate limits.

**Solution**:

- Monitor API Usage: Check your Azure portal to monitor API usage and ensure you are within your subscription limits.
- Optimize Azure Requests:
  - Adjust `azure_request_intervals`: Modify the intervals at which images are sent to Azure to reduce the number of requests.
  - Use `max_unknown_object_counter`: Set an appropriate maximum counter to prevent excessive requests when no target object is detected.
- Upgrade Subscription: Consider upgrading your Azure Cognitive Services plan if you frequently exceed limits.

## 12. Persistent Notifications Not Appearing

**Symptom**: Persistent notifications do not show up in the Home Assistant interface.

**Solution**:

- Check Notification Settings: Ensure that notifications are enabled in the integration settings.
- Review Logs: Look for any errors related to notification services in Home Assistant logs.
- Notification Service Availability: Verify that the chosen notification platform (e.g., `persistent_notification`) is correctly configured and operational.

## 13. Connection Issues with Camera

**Symptom**: Unable to connect to the camera at the specified URL.

**Solution**:

- Verify Camera Status: Ensure that the camera is powered on and connected to the network.
- Check Camera URL: Confirm that the camera URL is correct and accessible from the Home Assistant server.
- Network Configuration: Ensure there are no network issues or firewall settings blocking access to the camera.
- Test the URL: Try accessing the camera URL directly from a browser on the same network as Home Assistant.

## 14. Errors During Motion Detection

**Symptom**: Errors occur during the motion detection process, causing the integration to fail.

**Solution**:

- Check Image Format: Ensure that the images fetched from the camera are in a supported format (e.g., JPEG).
- Update Dependencies: Make sure all required Python libraries are up to date.
- Review Motion Detection Parameters: Incorrect parameters can cause the motion detection algorithms to malfunction. Adjust settings as needed.

## 15. Reference Image Not Updating

**Symptom**: The reference image used for motion detection is not updating, causing inaccurate motion detection.

**Solution**:

- Ensure Reference Image Update Conditions: The reference image is updated periodically when no significant motion is detected and when the object leaves the scene. Ensure that these conditions are met in your environment.
- Adjust `max_unknown_object_counter`: If the counter reaches its maximum value without detecting a target object, the reference image is updated. Adjust this value if necessary.
- Logs: Check the logs to see if there are messages indicating when the reference image is updated.

## 16. Target Object Not Detected

**Symptom**: The system fails to detect the target object even when it is clearly visible.

**Solution**:

- Adjust Azure Confidence Threshold: Lower the `azure_confidence_threshold` in the device configuration to allow detections with lower confidence levels.
- Verify Azure Configuration: Ensure that the `to_detect_object` parameter is correctly set to the object you want to detect.
- Improve Image Quality: Ensure that the camera provides clear images. Poor lighting or low resolution can affect object detection accuracy.
- Check Azure Service Status: Verify that Azure Cognitive Services are operational and not experiencing outages.

## Contact Support

If you've tried the above solutions and still encounter issues, please reach out for support:

- **GitHub Issues**: Report your issue on the HomeAIVision Issues Page.
- **Community Forums**: Seek help from the Home Assistant community on the Home Assistant Forums.

When reporting an issue, provide as much detail as possible, including:

- Steps to reproduce the issue.
- Relevant configuration settings.
- Log excerpts related to the problem.

Your feedback is invaluable in improving HomeAIVision!
