import logging
from homeassistant.helpers.storage import Store
import attr

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "homeaivision.devices"
STORAGE_VERSION = 1

@attr.s
class DeviceData:
    id = attr.ib(type=str)
    name = attr.ib(type=str)
    url = attr.ib(type=str)
    detected_object = attr.ib(type=str)
    confidence_threshold = attr.ib(type=float)
    send_notifications = attr.ib(type=bool, default=False)
    organize_by_day = attr.ib(type=bool, default=True)
    max_images = attr.ib(type=int, default=30)
    time_between_requests = attr.ib(type=int, default=30)
    azure_request_count = attr.ib(type=int, default=0)

    @classmethod
    def from_dict(cls, data):
        data.setdefault('azure_request_count', 0)
        return cls(**data)

    def asdict(self):
        return attr.asdict(self)

class HomeAIVisionStore:
    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.devices = {}
        self._listeners = []

    async def async_load(self):
        data = await self.store.async_load()
        if data is not None:
            self.devices = {
                device_id: DeviceData.from_dict(device_data)
                for device_id, device_data in data.get('devices', {}).items()
            }
        else:
            self.devices = {}

    async def async_save(self):
        data = {
            'devices': {
                device_id: device_data.asdict()
                for device_id, device_data in self.devices.items()
            }
        }
        await self.store.async_save(data)

    def get_device(self, device_id):
        return self.devices.get(device_id)

    def get_devices(self):
        return self.devices

    async def async_add_device(self, device_data):
        self.devices[device_data.id] = device_data
        await self.async_save()
        self._notify_listeners()

    async def async_update_device(self, device_id, device_data):
        self.devices[device_id] = device_data
        await self.async_save()
        self._notify_listeners()

    async def async_remove_device(self, device_id):
        if device_id in self.devices:
            del self.devices[device_id]
            await self.async_save()
            self._notify_listeners()

    def add_listener(self, listener):
        self._listeners.append(listener)

    def _notify_listeners(self):
        for listener in self._listeners:
            listener()
