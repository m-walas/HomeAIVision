import logging
import attr  # type: ignore

from homeassistant.helpers.storage import Store  # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "homeaivision.devices"
STORAGE_VERSION = 1

# NOTE: Define signals for device addition and removal
DEVICE_ADDED_SIGNAL = f"{DOMAIN}_device_added"
DEVICE_EDITED_SIGNAL = f"{DOMAIN}_device_edited"
DEVICE_REMOVED_SIGNAL = f"{DOMAIN}_device_removed"

@attr.s
class DeviceData:
    """Class representing data for a single device."""

    id = attr.ib(type=str)
    name = attr.ib(type=str)
    url = attr.ib(type=str)
    to_detect_object = attr.ib(type=str)
    azure_confidence_threshold = attr.ib(type=float)
    armed = attr.ib(type=bool, default=False)
    send_notifications = attr.ib(type=bool, default=False)
    max_images_per_day = attr.ib(type=int, default=100)
    days_to_keep = attr.ib(type=int, default=30)
    motion_detection_history_size = attr.ib(type=int, default=10)
    motion_detection_interval = attr.ib(type=int, default=5)
    device_azure_request_count = attr.ib(type=int, default=0)
    local_sensitivity_level = attr.ib(type=str, default='medium')
    config_entry_id = attr.ib(type=str, default='')

    @classmethod
    def from_dict(cls, data):
        """
        Create a DeviceData instance from a dictionary.

        Args:
            data (dict): Dictionary containing device data.

        Returns:
            DeviceData: An instance of DeviceData.
        """
        # IMPORTANT: Provide default values for missing keys to maintain compatibility
        data.setdefault('armed', False)
        data.setdefault('send_notifications', False)
        data.setdefault('max_images_per_day', 100)
        data.setdefault('days_to_keep', 30)
        data.setdefault('motion_detection_history_size', 10)
        data.setdefault('motion_detection_interval', 5)
        data.setdefault('device_azure_request_count', 0)
        data.setdefault('local_sensitivity_level', 'medium')
        data.setdefault('config_entry_id', '')

        return cls(**data)

    def asdict(self):
        """Convert the DeviceData instance to a dictionary."""
        return attr.asdict(self)


@attr.s
class GlobalData:
    """Class representing global data for the integration."""

    global_azure_request_count = attr.ib(type=int, default=0)
    language = attr.ib(type=str, default="en")

    @classmethod
    def from_dict(cls, data):
        """
        Create a GlobalData instance from a dictionary.
        
        Args:
            data (dict): Dictionary containing global data.
        
        Returns:
            GlobalData: An instance of GlobalData.
        """
        return cls(
            global_azure_request_count=data.get('global_azure_request_count', 0),
            language=data.get('language', 'en'),
        )

    def asdict(self):
        """Convert the GlobalData instance to a dictionary."""
        return attr.asdict(self)


class HomeAIVisionStore:
    """Class to manage storage and retrieval of HomeAIVision data."""

    def __init__(self, hass):
        """
        Initialize the HomeAIVisionStore.
        
        Args:
            hass (HomeAssistant): The Home Assistant instance.
        """
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.devices = {}
        self.global_data = GlobalData()
        self._listeners = []

    async def async_load(self):
        """
        Load data from storage.
        
        This function loads device data and global data from the persistent storage.
        If no data is found, it initializes empty structures.
        """
        data = await self.store.async_load()
        if data is not None:
            devices_data = data.get('devices', {})
            self.devices = {
                device_id: DeviceData.from_dict(device_data)
                for device_id, device_data in devices_data.items()
            }
            global_data = data.get('global', {})
            self.global_data = GlobalData.from_dict(global_data)
            _LOGGER.info("[HomeAIVision] Data loaded successfully from storage.")
        else:
            self.devices = {}
            self.global_data = GlobalData()
            _LOGGER.info("[HomeAIVision] No existing data found. Initialized with default values.")

    async def async_save(self):
        """
        Save current data to storage.
        
        This function saves the current state of devices and global data to persistent storage.
        """
        data = {
            'devices': {
                device_id: device_data.asdict()
                for device_id, device_data in self.devices.items()
            },
            'global': self.global_data.asdict(),
        }
        await self.store.async_save(data)
        _LOGGER.debug("[HomeAIVision] Data saved successfully to storage.")

    def get_device(self, device_id):
        """
        Retrieve a device by its ID.
        
        Args:
            device_id (str): The unique identifier of the device.
        
        Returns:
            DeviceData or None: The device data if found, else None.
        """
        return self.devices.get(device_id)

    def get_devices(self):
        """
        Retrieve all devices.
        
        Returns:
            dict: A dictionary of all devices keyed by their IDs.
        """
        return self.devices

    async def async_add_device(self, device_data: DeviceData):
        """
        Add a new device to the store.
        
        Args:
            device_data (DeviceData): The data of the device to add.
        """
        self.devices[device_data.id] = device_data
        _LOGGER.debug(f"[HomeAIVision] Added new device: {device_data.asdict()}")
        await self.async_save()
        self._notify_listeners()
        # NOTE: Send a signal to notify the integration about the new device
        async_dispatcher_send(self.hass, DEVICE_ADDED_SIGNAL, device_data.asdict())

    async def async_update_device(self, device_id, device_data: DeviceData):
        """
        Update an existing device in the store.
        
        Args:
            device_id (str): The unique identifier of the device.
            device_data (DeviceData): The updated data of the device.
        """
        self.devices[device_id] = device_data
        _LOGGER.debug(f"[HomeAIVision] Updated device: {device_id}: {device_data.asdict()}")
        await self.async_save()
        self._notify_listeners()
        # NOTE: Send a signal to notify the integration about the updated device
        async_dispatcher_send(self.hass, DEVICE_EDITED_SIGNAL, device_data.asdict())

    async def async_remove_device(self, device_id: str):
        """
        Remove a device from the store.
        
        Args:
            device_id (str): The unique identifier of the device to remove.
        """
        if device_id in self.devices:
            device = self.devices.pop(device_id)
            _LOGGER.debug(f"[HomeAIVision] Deleted device: {device_id}.")
            await self.async_save()
            self._notify_listeners()
            # NOTE: Send a signal to notify the integration about the removed device
            async_dispatcher_send(self.hass, DEVICE_REMOVED_SIGNAL, device.asdict())
        else:
            _LOGGER.warning(f"[HomeAIVision] Attempted to delete non-existent device: {device_id}")

    async def async_increment_global_counter(self):
        """
        Increment the global Azure request counter.
        """
        self.global_data.global_azure_request_count += 1
        _LOGGER.debug(f"[HomeAIVision] Increased global Azure request counter to: {self.global_data.global_azure_request_count}")
        await self.async_save()
        self._notify_listeners()

    async def async_reset_global_counter(self):
        """
        Reset the global Azure request counter to zero.
        """
        self.global_data.global_azure_request_count = 0
        _LOGGER.debug("[HomeAIVision] Reset global Azure request counter to 0")
        await self.async_save()
        self._notify_listeners()

    def get_global_counter(self):
        """
        Retrieve the global Azure request counter.
        
        Returns:
            int: The current value of the global Azure request counter.
        """
        return self.global_data.global_azure_request_count

    def get_language(self):
        """
        Retrieve the current notification language.
        
        Returns:
            str: The language code for notifications.
        """
        return self.global_data.language

    async def async_set_language(self, language: str):
        """
        Set the notification language.
        
        Args:
            language (str): The language code to set for notifications.
        """
        self.global_data.language = language
        _LOGGER.debug(f"[HomeAIVision] Set notification language to: {language}")
        await self.async_save()
        self._notify_listeners()

    def add_listener(self, listener):
        """
        Add a listener to be notified on data changes.
        
        Args:
            listener (callable): The callback function to add as a listener.
        """
        self._listeners.append(listener)
        _LOGGER.debug("[HomeAIVision] Added a new listener.")

    def _notify_listeners(self):
        """
        Notify all registered listeners about data changes.
        """
        for listener in self._listeners:
            listener()
        _LOGGER.debug("[HomeAIVision] Notified all listeners about data changes.")
