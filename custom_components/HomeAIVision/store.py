import logging
import attr
from homeassistant.helpers.storage import Store

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
    days_to_keep = attr.ib(type=int, default=7)
    device_azure_request_count = attr.ib(type=int, default=0)

    @classmethod
    def from_dict(cls, data):
        data.setdefault('device_azure_request_count', 0)
        return cls(**data)

    def asdict(self):
        return attr.asdict(self)


@attr.s
class GlobalData:
    global_azure_request_count = attr.ib(type=int, default=0)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def asdict(self):
        return attr.asdict(self)


class HomeAIVisionStore:
    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.devices = {}
        self.global_data = GlobalData()
        self._listeners = []

    async def async_load(self):
        data = await self.store.async_load()
        if data is not None:
            devices_data = data.get('devices', {})
            self.devices = {
                device_id: DeviceData.from_dict(device_data)
                for device_id, device_data in devices_data.items()
            }
            global_data = data.get('global', {})
            self.global_data = GlobalData.from_dict(global_data)
        else:
            self.devices = {}
            self.global_data = GlobalData()

    async def async_save(self):
        data = {
            'devices': {
                device_id: device_data.asdict()
                for device_id, device_data in self.devices.items()
            },
            'global': self.global_data.asdict(),
        }
        await self.store.async_save(data)

    def get_device(self, device_id):
        return self.devices.get(device_id)

    def get_devices(self):
        return self.devices

    async def async_add_device(self, device_data):
        self.devices[device_data.id] = device_data
        _LOGGER.debug(f"[HomeAIVision] Added new device: {device_data.asdict()}")
        await self.async_save()
        self._notify_listeners()

    async def async_update_device(self, device_id, device_data):
        self.devices[device_id] = device_data
        _LOGGER.debug(f"[HomeAIVision] Updated device: {device_id}: {device_data.asdict()}")
        await self.async_save()
        self._notify_listeners()

    async def async_remove_device(self, device_id):
        if device_id in self.devices:
            del self.devices[device_id]
            _LOGGER.debug(f"[HomeAIVision] Deleted device: {device_id}")
            await self.async_save()
            self._notify_listeners()

    async def async_increment_global_counter(self):
        self.global_data.global_azure_request_count += 1
        _LOGGER.debug(f"[HomeAIVision] Increase global counter Azure: {self.global_data.global_azure_request_count}")
        await self.async_save()
        self._notify_listeners()

    async def async_reset_global_counter(self):
        self.global_data.global_azure_request_count = 0
        _LOGGER.debug("[HomeAIVision] Reset global counter")
        await self.async_save()
        self._notify_listeners()

    def get_global_counter(self):
        return self.global_data.global_azure_request_count

    def add_listener(self, listener):
        self._listeners.append(listener)

    def _notify_listeners(self):
        for listener in self._listeners:
            listener()
