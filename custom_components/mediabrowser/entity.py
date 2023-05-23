"""Entity base class for the Media Browser (Emby/Jellyfin) integration."""

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DASHBOARD_MAP, DOMAIN, MANUFACTURER_MAP, Manufacturer
from .coordinator import MediaBrowserPollCoordinator, MediaBrowserPushCoordinator
from .hub import MediaBrowserHub


class MediaBrowserEntity(Entity):
    """Media Browser entity ancestor with device info."""

    def __init__(self, hub: MediaBrowserHub) -> None:
        self.hub = hub

    @property
    def device_info(self) -> DeviceInfo | None:
        return _get_device_info(self.hub)


class MediaBrowserPollEntity(CoordinatorEntity[MediaBrowserPollCoordinator]):
    """Media Browser poll entity ancestor."""

    def __init__(
        self, coordinator: MediaBrowserPollCoordinator, context: Any = None
    ) -> None:
        super().__init__(coordinator, context)
        self.hub = coordinator.hub

    @property
    def device_info(self) -> DeviceInfo | None:
        return _get_device_info(self.hub)


class MediaBrowserPushEntity(CoordinatorEntity[MediaBrowserPushCoordinator]):
    """Media Browser push entity ancestor."""

    def __init__(
        self, coordinator: MediaBrowserPushCoordinator, context: Any = None
    ) -> None:
        super().__init__(coordinator, context)
        self.hub = coordinator.hub

    @property
    def device_info(self) -> DeviceInfo | None:
        return _get_device_info(self.hub)


def _get_device_info(hub: MediaBrowserHub) -> DeviceInfo:
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, hub.server_id or "")},
        manufacturer=MANUFACTURER_MAP.get(hub.server_type, Manufacturer.UNKNOWN),
        name=hub.server_name,
        sw_version=hub.server_version,
        model=f"{hub.server_name} ({hub.server_os})",
        configuration_url=f"{hub.server_url}{DASHBOARD_MAP.get(hub.server_type, '')}",
    )
