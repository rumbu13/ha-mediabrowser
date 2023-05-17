"""Sensors for the Media Browser (Emby/Jellyfin) integration."""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    POLL_COORDINATOR,
    DOMAIN,
    LIBRARY_ICONS,
)
from .coordinator import MediaBrowserPollCoordinator
from .entity import MediaBrowserPollEntity, MediaBrowserPushEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: MediaBrowserPollCoordinator = data[POLL_COORDINATOR]
    async_add_entities(
        [SessionsSensor(coordinator)]
        + [
            LibrarySensor(coordinator, library_id)
            for library_id in coordinator.data.libraries
        ]
    )


class SessionsSensor(MediaBrowserPushEntity, SensorEntity):
    """Defines a sensor entity."""

    def __init__(
        self, coordinator: MediaBrowserPollCoordinator, context: Any = None
    ) -> None:
        super().__init__(coordinator, context)
        self._attr_icon = "mdi:play-box-multiple"
        self._attr_name = f"{coordinator.hub.server_name} Sessions"
        self._attr_unique_id = f"{coordinator.hub.server_id}-sessions"
        self._attr_native_unit_of_measurement = "Watching"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "server_name": self.coordinator.hub.server_name,
            "server_id": self.coordinator.hub.server_id,
            "total_sessions": len(self.coordinator.data.sessions),
            "sessions": [
                {
                    "device": session.device_name,
                    "client": session.client,
                    "playing": session.now_playing_item.name,
                }
                for session in self.coordinator.data.sessions
                if session.now_playing_item is not None
            ]
            + [
                {
                    "device": session.device_name,
                    "client": session.client,
                }
                for session in self.coordinator.data.sessions
                if session.now_playing_item is None
            ],
        }

    @property
    def native_value(self) -> StateType:
        return len(
            [
                session
                for session in self.coordinator.data.sessions
                if session.now_playing_item is not None
            ]
        )


class LibrarySensor(MediaBrowserPollEntity, SensorEntity):
    """Defines a sensor entity."""

    def __init__(
        self,
        coordinator: MediaBrowserPollCoordinator,
        library_id: str,
        context: Any = None,
    ) -> None:
        super().__init__(coordinator, context)

        self._library_id: str = library_id
        library = coordinator.data.libraries.get(library_id)
        self._attr_icon = LIBRARY_ICONS.get(library.collection_type or "")
        self._attr_name = (
            f'{coordinator.data.info.server_name} {library.name or "Unknown"} Library'
        )
        self._attr_unique_id = f"{coordinator.data.info.id}-{library_id}-library"
        self._attr_native_unit_of_measurement = "Items"

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        info = self.coordinator.data.library_infos.get(self._library_id)
        return info.count if info is not None else 0

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        info = self.coordinator.data.library_infos.get(self._library_id)
        return info.attributes if info is not None else None

    @property
    def available(self) -> bool:
        return self._library_id in self.coordinator.data.library_infos
