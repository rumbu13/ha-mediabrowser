"""Sensors for the Media Browser (Emby/Jellyfin) integration."""

import logging
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from dateutil import parser
from dateutil.parser import ParserError
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    IMAGE_TYPES,
    LATEST_TYPES,
    POLL_COORDINATOR,
    PUSH_COORDINATOR,
    TICKS_PER_SECOND,
)
from .coordinator import MediaBrowserPollCoordinator, MediaBrowserPushCoordinator
from .entity import MediaBrowserPollEntity, MediaBrowserPushEntity
from .helpers import get_category_image_url, get_image_url, snake_case
from .models import MBItem

ICON_SENSOR_LIBRARY = "mdi:multimedia"
ICON_SENSOR_LATEST = "mdi:new-box"
ICON_SENSOR_SESSIONS = "mdi:play-box-multiple"


_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    poll_coordinator: MediaBrowserPollCoordinator = data[POLL_COORDINATOR]
    push_coordinator_raw: MediaBrowserPushCoordinator = data[PUSH_COORDINATOR]
    async_add_entities(
        [SessionsSensor(push_coordinator_raw)]
        + [
            LibrarySensor(poll_coordinator, library)
            for library in poll_coordinator.data.libraries.values()
        ]
        + [LatestSensor(poll_coordinator, item_id) for item_id in LATEST_TYPES]
    )


class SessionsSensor(MediaBrowserPushEntity, SensorEntity):
    """Defines a sensor entity."""

    def __init__(
        self, coordinator: MediaBrowserPushCoordinator, context: Any = None
    ) -> None:
        super().__init__(coordinator, context)
        self._attr_icon = ICON_SENSOR_SESSIONS
        self._attr_name = f"{coordinator.hub.server_name} Sessions"
        self._attr_unique_id = f"{coordinator.hub.server_id}-sessions"
        self._attr_native_unit_of_measurement = "Watching"
        self._latest_info: dict[str, dict[str, Any]] | None = coordinator.data.sessions
        self._update_from_data()

    def _handle_coordinator_update(self) -> None:
        self._latest_info = self.coordinator.data.sessions
        self._update_from_data()
        return super()._handle_coordinator_update()

    def _update_from_data(self) -> None:
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        if self._latest_info is not None:
            self._attr_native_value = len(
                [
                    session
                    for session in self._latest_info.values()
                    if "NowPlayingItem" in session
                ]
            )

            attrs = [
                _get_session_attr(session)
                for session in sorted(
                    self._latest_info.values(),
                    key=lambda x: str(x.get("LastActivityDate")),
                    reverse=True,
                )
            ]

            self._attr_extra_state_attributes = {
                "server_name": self.coordinator.hub.server_name,
                "server_id": self.coordinator.hub.server_id,
                "total_sessions": len(self._latest_info),
                "sessions": attrs,
            }

    @property
    def available(self) -> bool:
        return self._latest_info is not None and self.coordinator.last_update_success


class LibrarySensor(MediaBrowserPollEntity, SensorEntity):
    """Defines a sensor entity."""

    def __init__(
        self,
        coordinator: MediaBrowserPollCoordinator,
        library: MBItem,
        context: Any = None,
    ) -> None:
        super().__init__(coordinator, context)

        self._library_id: str = library.id
        self._attr_icon = ICON_SENSOR_LIBRARY
        self._attr_name = f"{self.hub.server_name} Library - {library.name}"
        self._attr_unique_id = f"{coordinator.data.info.id}-{library.id}-library"
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


class LatestSensor(MediaBrowserPollEntity, SensorEntity):
    """Defines a sensor entity."""

    def __init__(
        self,
        coordinator: MediaBrowserPollCoordinator,
        item_type: str,
        context: Any = None,
    ) -> None:
        super().__init__(coordinator, context)

        self._item_type: str = item_type
        self._latest_info: list[dict[str, Any]] | None = None
        self._attr_icon = ICON_SENSOR_LATEST
        self._attr_name = f'{coordinator.data.info.server_name} Latest {LATEST_TYPES[item_type]["title"]}'
        self._attr_unique_id = f"{coordinator.data.info.id}-{item_type}-latest"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._update_from_data()

    def _handle_coordinator_update(self) -> None:
        self._latest_info = self.coordinator.data.latest_infos.get(self._item_type)
        self._update_from_data()
        return super()._handle_coordinator_update()

    def _update_from_data(self) -> None:
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        if self._latest_info is not None:
            try:
                self._attr_native_value = (
                    parser.isoparse(self._latest_info[0]["DateCreated"])
                    if len(self._latest_info) > 0
                    else None
                )
            except ParserError:
                _LOGGER.error("Invalid date: %s", self._latest_info[0]["DateCreated"])

            self._attr_extra_state_attributes = {
                "latest": [
                    _get_latest_attr(item, self.hub.server_url or "")
                    for item in self._latest_info
                ]
            }

    @property
    def available(self) -> bool:
        return (
            self._item_type in self.coordinator.data.latest_infos
            and self.coordinator.last_update_success
        )


def _get_session_attr(data: dict[str, Any]) -> dict[str, Any]:
    """Gets standard upcoming media formatted data."""

    result: dict[str, Any] = {}

    for attr in [
        "UserName",
        "Client",
        "DeviceName",
        "DeviceId",
        "ApplicationVersion",
        "RemoteEndPoint",
        "SupportsRemoteControl",
        "AppIconUrl",
    ]:
        if attr in data:
            result[snake_case(attr)] = data[attr]

    if "LastActivityDate" in data:
        try:
            result[snake_case("LastActivityDate")] = parser.isoparse(
                data["LastActivityDate"]
            )
        except ParserError:
            _LOGGER.warning(
                "Invalid date: %s:%s", "LastActivityDate", data["LastActivityDate"]
            )

    if "NowPlayingItem" in data:
        for attr in [
            "Name",
            "Type",
            "MediaType",
        ]:
            if attr in data:
                result[f"playing_{snake_case(attr)}"] = data["NowPlaying"][attr]

    return result


def _get_latest_attr(data: dict[str, Any], url: str) -> dict[str, Any]:
    """Gets standard upcoming media formatted data."""

    result: dict[str, Any] = {}

    for attr in [
        "Id",
        "Name",
        "CommunityRating",
        "CriticRating",
        "OfficialRating",
        "Album",
        "SeasonName",
        "SeriesName",
        "Overview",
        "ProductionYear",
    ]:
        if attr in data:
            result[snake_case(attr)] = data[attr]

    for attr in ["DateCreated", "PremiereDate"]:
        if attr in data:
            try:
                result[snake_case(attr)] = parser.isoparse(data[attr])
            except ParserError:
                _LOGGER.warning("Invalid date: %s:%s", attr, data[attr])

    if "RunTimeTicks" in data:
        try:
            result["runtime"] = float(data["RunTimeTicks"]) // TICKS_PER_SECOND
        except ValueError:
            _LOGGER.warning("Invalid run time ticks: %s", data["RuntimeTicks"])

    if "IndexNumber" in data and "ParentIndexNumber" in data:
        result[
            "episode"
        ] = f'S{data["ParentIndexNumber"]:02d}E{data["IndexNumber"]:02d}'

    if "Studios" in data and len(data["Studios"]) > 0:
        result["studios"] = ", ".join(
            item["Name"] for item in data["Studios"] if "Name" in item
        )

    if "Genres" in data and len(data["Genres"]) > 0:
        result["genres"] = ", ".join(data["Genres"])

    if "Artists" in data and len(data["Artists"]) > 0:
        result["artists"] = ", ".join(data["Artists"])

    if "Taglines" in data and len(data["Taglines"]) > 0:
        result["tagline"] = data["Taglines"][0]

    for image_type in IMAGE_TYPES:
        image = get_image_url(data, url, image_type, False)
        if image is not None:
            result[f"image_{snake_case(image_type)}"] = image
        for category in ["Parent", "Album", "Series", "Channel"]:
            image = get_category_image_url(data, url, image_type, category)
            if image is not None:
                result[f"image_{snake_case(image_type)}_{snake_case(category)}"] = image

    return result
