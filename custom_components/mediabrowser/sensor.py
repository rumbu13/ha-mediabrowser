"""Sensors for the Media Browser (Emby/Jellyfin) integration."""

import logging
from datetime import date
from typing import Any

from dateutil import parser
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_USER,
    CONF_SENSORS,
    CONF_UPCOMING_MEDIA,
    DATA_POLL_COORDINATOR,
    DATA_PUSH_COORDINATOR,
    DEFAULT_UPCOMING_MEDIA,
    DOMAIN,
    ENTITY_TITLE_MAP,
    SENSOR_ITEM_TYPES,
    TICKS_PER_MINUTE,
    TICKS_PER_SECOND,
    EntityType,
    ImageCategory,
    ImageType,
    ItemType,
    Key,
)
from .coordinator import MediaBrowserPollCoordinator, MediaBrowserPushCoordinator
from .entity import MediaBrowserPollEntity, MediaBrowserPushEntity
from .helpers import (
    build_sensor_key,
    get_category_image_url,
    get_image_url,
    is_datetime,
    is_int,
    snake_case,
)

ICON_SENSOR_LIBRARY = "mdi:multimedia"
ICON_SENSOR_SESSIONS = "mdi:play-box-multiple"


_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    poll_coordinator: MediaBrowserPollCoordinator = data[DATA_POLL_COORDINATOR]
    push_coordinator: MediaBrowserPushCoordinator = data[DATA_PUSH_COORDINATOR]
    await push_coordinator.async_refresh()

    async_add_entities(
        [SessionsSensor(push_coordinator)]
        + [
            LibrarySensor(
                poll_coordinator,
                sensor[CONF_SENSOR_USER],
                sensor[CONF_SENSOR_ITEM_TYPE],
                sensor[CONF_SENSOR_LIBRARY],
                entry.options.get(CONF_UPCOMING_MEDIA, DEFAULT_UPCOMING_MEDIA),
            )
            for sensor in entry.options.get(CONF_SENSORS, [])
        ]
    )


def _build_library_sensors(
    coordinator: MediaBrowserPollCoordinator, entry: ConfigEntry
) -> list[Any]:
    sensors = entry.options.get(CONF_SENSORS, [])
    result = []
    for sensor in sensors:
        user_id = sensor[CONF_SENSOR_USER]
        item_type = sensor[CONF_SENSOR_ITEM_TYPE]
        library_id = sensor[CONF_SENSOR_LIBRARY]
        if user_id not in coordinator.library_sensors:
            coordinator.library_sensors[user_id] = {}
        if item_type not in coordinator.library_sensors[user_id]:
            coordinator.library_sensors[user_id][item_type] = set()
        coordinator.library_sensors[user_id][item_type].add(library_id)
        result.append(
            LibrarySensor(
                coordinator,
                sensor[CONF_SENSOR_USER],
                sensor[CONF_SENSOR_ITEM_TYPE],
                sensor[CONF_SENSOR_LIBRARY],
                entry.options.get(CONF_UPCOMING_MEDIA, DEFAULT_UPCOMING_MEDIA),
            )
        )
    return result


class SessionsSensor(MediaBrowserPushEntity, SensorEntity):
    """Defines a sensor entity."""

    def __init__(
        self, coordinator: MediaBrowserPushCoordinator, context: Any = None
    ) -> None:
        super().__init__(coordinator, context)
        self._attr_icon = ICON_SENSOR_SESSIONS
        self._attr_name = f"{self.hub.name} {ENTITY_TITLE_MAP[EntityType.SESSIONS]}"
        self._attr_unique_id = f"{self.hub.server_id}-{EntityType.SESSIONS}"
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
                    if Key.NOW_PLAYING_ITEM in session
                ]
            )

            attrs = [
                _get_session_attr(session)
                for session in sorted(
                    self._latest_info.values(),
                    key=lambda x: str(x.get(Key.LAST_ACTIVITY_DATE)),
                    reverse=True,
                )
            ]

            self._attr_extra_state_attributes = {
                "server_name": self.hub.server_name,
                "server_id": self.hub.server_id,
                "total_sessions": len(self._latest_info),
                "sessions": attrs,
            }

    @property
    def available(self) -> bool:
        return self._latest_info is not None and self.coordinator.last_update_success


class LibrarySensor(MediaBrowserPollEntity, SensorEntity):
    """Custom sensor for displaying latest items"""

    def __init__(
        self,
        coordinator: MediaBrowserPollCoordinator,
        user_id: str,
        item_type: ItemType,
        library_id: str,
        show_upcoming_data: bool,
    ) -> None:
        super().__init__(coordinator)
        self._item_type: ItemType = item_type
        self._user_id: str = user_id
        self._library_id: str = library_id
        self._show_upcoming_data = show_upcoming_data
        name = f'{self.hub.name} {SENSOR_ITEM_TYPES[item_type]["title"]}'
        if library_id != Key.ALL and library_id in coordinator.data.libraries:
            name = name + " - " + coordinator.data.libraries[library_id][Key.NAME]
        if user_id != Key.ALL and user_id in coordinator.data.users:
            name = name + f" ({coordinator.data.users[user_id][Key.NAME]})"
        self._attr_name = name
        self._attr_unique_id = f"{self.hub.server_id}-{build_sensor_key(user_id, item_type, library_id)}-{EntityType.LIBRARY}"
        self._latest_info: dict[str, Any] | None = None
        self._attr_icon = SENSOR_ITEM_TYPES[item_type]["icon"]
        self._update_from_coordinator()
        self._update_from_data()

    def _update_from_coordinator(self):
        self._latest_info = (
            self.coordinator.data.library_infos[self._user_id][self._item_type][
                self._library_id
            ]
            if self._user_id in self.coordinator.data.library_infos
            and self._item_type in self.coordinator.data.library_infos[self._user_id]
            and self._library_id
            in self.coordinator.data.library_infos[self._user_id][self._item_type]
            else None
        )

    def _handle_coordinator_update(self) -> None:
        self._update_from_coordinator()
        self._update_from_data()
        return super()._handle_coordinator_update()

    def _update_from_data(self) -> None:
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        if self._latest_info is not None:
            self._attr_native_value = (
                int(self._latest_info[Key.TOTAL_RECORD_COUNT])
                if Key.TOTAL_RECORD_COUNT in self._latest_info
                and is_int(self._latest_info[Key.TOTAL_RECORD_COUNT], logging.WARNING)
                else 0
            )

            self._attr_extra_state_attributes = {
                "latest": [
                    _get_sensor_attr(item, self.hub.server_url or "")
                    for item in self._latest_info[Key.ITEMS]
                ]
            }

            if self._show_upcoming_data:
                upcoming_data = [SENSOR_ITEM_TYPES[self._item_type]["upcoming"]]
                for item in self._latest_info[Key.ITEMS]:
                    upcoming_data.append(_get_upcoming_attr(item, self.hub.server_url))
                self._attr_extra_state_attributes["data"] = upcoming_data


def _get_session_attr(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for attr in [
        Key.USER_NAME,
        Key.CLIENT,
        Key.DEVICE_NAME,
        Key.DEVICE_ID,
        Key.APPLICATION_VERSION,
        Key.REMOTE_END_POINT,
        Key.SUPPORTS_REMOTE_CONTROL,
        Key.APP_ICON_URL,
    ]:
        if attr in data:
            result[snake_case(attr)] = data[attr]

    if last_activity := data.get(Key.LAST_ACTIVITY_DATE):
        if is_datetime(last_activity):
            result[snake_case(Key.LAST_ACTIVITY_DATE)] = parser.isoparse(last_activity)

    if Key.NOW_PLAYING_ITEM in data:
        for attr in [
            Key.NAME,
            Key.TYPE,
            Key.MEDIA_TYPE,
        ]:
            if attr in data:
                result[f"playing_{snake_case(attr)}"] = data[Key.NOW_PLAYING_ITEM][attr]

    return result


def _get_sensor_attr(data: dict[str, Any], url: str) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for attr in [
        Key.ID,
        Key.NAME,
        Key.COMMUNITY_RATING,
        Key.CRITIC_RATING,
        Key.OFFICIAL_RATING,
        Key.ALBUM,
        Key.SEASON_NAME,
        Key.SERIES_NAME,
        Key.OVERVIEW,
        Key.PRODUCTION_YEAR,
    ]:
        if attr in data:
            result[snake_case(attr)] = data[attr]

    for attr in [Key.DATE_CREATED, Key.PREMIERE_DATE]:
        if attr in data and is_datetime(data[attr]):
            result[snake_case(attr)] = parser.isoparse(data[attr])

    if ticks := data.get(Key.RUNTIME_TICKS):
        if is_int(ticks):
            result["runtime"] = int(ticks) // TICKS_PER_SECOND

    if Key.INDEX_NUMBER in data and Key.PARENT_INDEX_NUMBER in data:
        result[
            "episode"
        ] = f"S{data[Key.PARENT_INDEX_NUMBER]:02d}E{data[Key.INDEX_NUMBER]:02d}"

    if Key.STUDIOS in data and len(data[Key.STUDIOS]) > 0:
        result["studios"] = ", ".join(
            item[Key.NAME] for item in data[Key.STUDIOS] if Key.NAME in item
        )

    if Key.GENRES in data and len(data[Key.GENRES]) > 0:
        result["genres"] = ", ".join(data[Key.GENRES])

    if Key.ARTISTS in data and len(data[Key.ARTISTS]) > 0:
        result["artists"] = ", ".join(data[Key.ARTISTS])

    if Key.TAGLINES in data and len(data[Key.TAGLINES]) > 0:
        result["tagline"] = data[Key.TAGLINES][0]

    for image_type in ImageType:
        image = get_image_url(data, url, image_type, False)
        if image is not None:
            result[f"image_{snake_case(image_type)}"] = image
        for category in ImageCategory:
            image = get_category_image_url(data, url, image_type, category)
            if image is not None:
                result[f"image_{snake_case(image_type)}_{snake_case(category)}"] = image

    return result


def _get_upcoming_attr(data: dict[str, Any], url: str) -> dict[str, Any]:
    img_poster = (
        get_image_url(data, url, ImageType.PRIMARY, True)
        or get_image_url(data, url, ImageType.SCREENSHOT, True)
        or get_image_url(data, url, ImageType.THUMB, True)
    )
    img_fanart = (
        get_image_url(data, url, ImageType.ART, True)
        or get_image_url(data, url, ImageType.BACKDROP, True)
        or get_image_url(data, url, ImageType.PRIMARY, True)
        or get_image_url(data, url, ImageType.THUMB, True)
    )

    result: dict[str, Any] = {
        "airdate": data.get(Key.DATE_CREATED, date.today().isoformat()),
        "aired": data.get(Key.PREMIERE_DATE, ""),
        "release": data.get("Year", ""),
        "poster": img_poster or "",
        "fanart": img_fanart or "",
        "rating": data.get(Key.COMMUNITY_RATING, data.get(Key.CRITIC_RATING, "")),
        "runtime": int(data[Key.RUNTIME_TICKS]) // TICKS_PER_MINUTE
        if Key.RUNTIME_TICKS in data and is_int(data[Key.RUNTIME_TICKS])
        else "",
        "studio": ", ".join(item[Key.NAME] for item in data[Key.STUDIOS])
        if Key.STUDIOS in data and Key.NAME in data[Key.STUDIOS]
        else "",
        "number": f"S{data[Key.PARENT_INDEX_NUMBER]:02d}E{data[Key.INDEX_NUMBER]:02d}"
        if Key.PARENT_INDEX_NUMBER in data
        and Key.INDEX_NUMBER
        and is_int(data[Key.PARENT_INDEX_NUMBER])
        and is_int(data[Key.INDEX_NUMBER])
        else "",
    }

    match data[Key.TYPE]:
        case ItemType.EPISODE | ItemType.SEASON:
            result["title"] = data.get(Key.SERIES_NAME, data.get(Key.NAME, ""))
            result["episode"] = data.get(Key.NAME, "")
        case ItemType.AUDIO:
            result["title"] = data.get(Key.ALBUM, data.get(Key.NAME, ""))
            result["episode"] = data.get(Key.NAME, "")
        case ItemType.TV_PROGRAM | ItemType.LIVE_TV_PROGRAM:
            result["title"] = data.get(Key.CHANNEL_NAME, data.get(Key.NAME, ""))
            result["episode"] = data.get(Key.NAME, "")
        case _:
            result["title"] = data.get(Key.NAME, "")
            result["episode"] = ""

    return result
