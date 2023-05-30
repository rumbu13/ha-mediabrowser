"""Sensors for the Media Browser (Emby/Jellyfin) integration."""

import logging
from datetime import date
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hub import MediaBrowserHub

from .const import (
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_USER,
    CONF_SENSORS,
    CONF_UPCOMING_MEDIA,
    DATA_HUB,
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
    Item,
    Response,
    Session,
)
from .entity import MediaBrowserEntity
from .helpers import (
    as_int,
    build_sensor_key,
    get_category_image_url,
    get_image_url,
    as_datetime,
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
    hub: MediaBrowserHub = data[DATA_HUB]

    async_add_entities(
        [SessionsSensor(hub)]
        + [
            LibrarySensor(
                hub,
                sensor[CONF_SENSOR_USER],
                sensor[CONF_SENSOR_ITEM_TYPE],
                sensor[CONF_SENSOR_LIBRARY],
                entry.options.get(CONF_UPCOMING_MEDIA, DEFAULT_UPCOMING_MEDIA),
            )
            for sensor in entry.options.get(CONF_SENSORS, [])
        ]
    )


class SessionsSensor(MediaBrowserEntity, SensorEntity):
    """Sensor counting active sessions."""

    def __init__(self, hub: MediaBrowserHub) -> None:
        super().__init__(hub)
        self._attr_icon = ICON_SENSOR_SESSIONS
        self._attr_name = f"{self.hub.name} {ENTITY_TITLE_MAP[EntityType.SESSIONS]}"
        self._attr_unique_id = f"{self.hub.server_id}-{EntityType.SESSIONS}"
        self._attr_native_unit_of_measurement = "Sessions"
        self._attr_should_poll = False
        self._attr_available = False
        self._sessions_unlistener: Callable[[], None] | None = None
        self._availability_unlistener: Callable[[], None] | None = None

    async def async_added_to_hass(self):
        self._sessions_unlistener = self.hub.on_sessions_changed(
            self._async_sessions_updated
        )

        self._availability_unlistener = self.hub.on_availability_changed(
            self._async_availability_updated
        )

        sessions = await self.hub.async_get_sessions()
        await self._async_sessions_updated(sessions)

    async def async_will_remove_from_hass(self):
        if self._sessions_unlistener is not None:
            self._sessions_unlistener()
        if self._availability_unlistener is not None:
            self._availability_unlistener()

    async def _async_sessions_updated(self, sessions: list[dict[str, Any]]) -> None:
        self._attr_available = True
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        self._attr_native_value = len(
            [session for session in sessions if Session.NOW_PLAYING_ITEM in session]
        )

        attrs = [
            _get_session_attr(session)
            for session in sorted(
                sessions,
                key=lambda x: str(x.get(Session.LAST_ACTIVITY_DATE)),
                reverse=True,
            )
        ]

        self._attr_extra_state_attributes = {
            "server_name": self.hub.server_name,
            "server_id": self.hub.server_id,
            "total_sessions": len(sessions),
            "sessions": attrs,
        }

        self.async_write_ha_state()

    async def _async_availability_updated(self, availability: bool) -> None:
        self._attr_available = availability


class LibrarySensor(MediaBrowserEntity, SensorEntity):
    """Custom sensor for displaying latest items"""

    def __init__(
        self,
        hub: MediaBrowserHub,
        user_id: str,
        item_type: ItemType,
        library_id: str,
        show_upcoming_data: bool,
    ) -> None:
        super().__init__(hub)
        self._item_type: ItemType = item_type
        self._user_id: str = user_id
        self._library_id: str = library_id
        self._show_upcoming_data = show_upcoming_data
        self._attr_name = f'{self.hub.name} {SENSOR_ITEM_TYPES[item_type]["title"]}'
        self._attr_unique_id = "-".join(
            [
                self.hub.server_id or "",
                build_sensor_key(user_id, item_type, library_id),
                EntityType.LIBRARY,
            ]
        )
        self._latest_info: dict[str, Any] | None = None
        self._attr_icon = SENSOR_ITEM_TYPES[item_type]["icon"]
        self._library_unlistener: Callable[[], None] | None = None
        self._availability_unlistener: Callable[[], None] | None = None

    async def async_added_to_hass(self):
        self._library_unlistener = self.hub.on_library_changed(
            self._library_id,
            self._user_id,
            self._item_type,
            self._async_library_changed,
        )
        self._availability_unlistener = self.hub.on_availability_changed(
            self._async_availability_updated
        )
        self.hub.force_library_change(self._library_id)

    async def async_will_remove_from_hass(self):
        if self._library_unlistener is not None:
            self._library_unlistener()
        if self._availability_unlistener is not None:
            self._availability_unlistener()

    async def _async_library_changed(self, data: dict[str, Any]) -> None:
        self._latest_info = data
        self._update_from_data()
        self.async_write_ha_state()

    async def _async_availability_updated(self, availability: bool) -> None:
        self._attr_available = availability

    def _update_from_data(self) -> None:
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        if self._latest_info is not None:
            self._attr_native_value = (
                as_int(self._latest_info, Response.TOTAL_RECORD_COUNT) or 0
            )
            self._attr_extra_state_attributes = {
                "latest": [
                    _get_sensor_attr(item, self.hub.server_url or "")
                    for item in self._latest_info[Response.ITEMS]
                ]
            }

            if self._show_upcoming_data:
                upcoming_data = [SENSOR_ITEM_TYPES[self._item_type]["upcoming"]]
                for item in self._latest_info[Response.ITEMS]:
                    upcoming_data.append(_get_upcoming_attr(item, self.hub.server_url))
                self._attr_extra_state_attributes["data"] = upcoming_data


def _get_session_attr(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for attr in [
        Session.USER_NAME,
        Session.CLIENT,
        Session.DEVICE_NAME,
        Session.DEVICE_ID,
        Session.APPLICATION_VERSION,
        Session.REMOTE_END_POINT,
        Session.SUPPORTS_REMOTE_CONTROL,
        Session.APP_ICON_URL,
    ]:
        if attr in data:
            result[snake_case(attr)] = data[attr]

    result[snake_case(Session.LAST_ACTIVITY_DATE)] = as_datetime(
        data, Session.LAST_ACTIVITY_DATE
    )

    if Session.NOW_PLAYING_ITEM in data:
        for attr in [
            Item.NAME,
            Item.TYPE,
            Item.MEDIA_TYPE,
        ]:
            if attr in data:
                result[f"playing_{snake_case(attr)}"] = data[Session.NOW_PLAYING_ITEM][
                    attr
                ]

    return result


def _get_sensor_attr(data: dict[str, Any], url: str) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for attr in [
        Item.ID,
        Item.NAME,
        Item.COMMUNITY_RATING,
        Item.CRITIC_RATING,
        Item.OFFICIAL_RATING,
        Item.ALBUM,
        Item.SEASON_NAME,
        Item.SERIES_NAME,
        Item.OVERVIEW,
        Item.PRODUCTION_YEAR,
    ]:
        if attr in data:
            result[snake_case(attr)] = data[attr]

    for attr in [Item.DATE_CREATED, Item.PREMIERE_DATE]:
        if datum := as_datetime(data, attr):
            result[snake_case(attr)] = datum

    if ticks := as_int(data, Item.RUNTIME_TICKS):
        result["runtime"] = ticks // TICKS_PER_SECOND

    if Item.INDEX_NUMBER in data and Item.PARENT_INDEX_NUMBER in data:
        result[
            "episode"
        ] = f"S{data[Item.PARENT_INDEX_NUMBER]:02d}E{data[Item.INDEX_NUMBER]:02d}"

    if Item.STUDIOS in data and len(data[Item.STUDIOS]) > 0:
        result["studios"] = ", ".join(
            item[Item.NAME] for item in data[Item.STUDIOS] if Item.NAME in item
        )

    if Item.GENRES in data and len(data[Item.GENRES]) > 0:
        result["genres"] = ", ".join(data[Item.GENRES])

    if Item.ARTISTS in data and len(data[Item.ARTISTS]) > 0:
        result["artists"] = ", ".join(data[Item.ARTISTS])

    if Item.TAGLINES in data and len(data[Item.TAGLINES]) > 0:
        result["tagline"] = data[Item.TAGLINES][0]

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
        "airdate": data.get(Item.DATE_CREATED, date.today().isoformat()),
        "aired": data.get(Item.PREMIERE_DATE, ""),
        "release": data.get("Year", ""),
        "poster": img_poster or "",
        "fanart": img_fanart or "",
        "rating": data.get(Item.COMMUNITY_RATING, data.get(Item.CRITIC_RATING, "")),
        "runtime": (as_int(data, Item.RUNTIME_TICKS) or 0) // TICKS_PER_MINUTE,
        "studio": ", ".join(item[Item.NAME] for item in data[Item.STUDIOS])
        if Item.STUDIOS in data and Item.NAME in data[Item.STUDIOS]
        else "",
        "number": f"S{data[Item.PARENT_INDEX_NUMBER]:02d}E{data[Item.INDEX_NUMBER]:02d}"
        if Item.PARENT_INDEX_NUMBER in data and Item.INDEX_NUMBER in data
        else "",
    }

    match data[Item.TYPE]:
        case ItemType.EPISODE | ItemType.SEASON:
            result["title"] = data.get(Item.SERIES_NAME, data.get(Item.NAME, ""))
            result["episode"] = data.get(Item.NAME, "")
        case ItemType.AUDIO:
            result["title"] = data.get(Item.ALBUM, data.get(Item.NAME, ""))
            result["episode"] = data.get(Item.NAME, "")
        case ItemType.TV_PROGRAM | ItemType.LIVE_TV_PROGRAM:
            result["title"] = data.get(Item.CHANNEL_NAME, data.get(Item.NAME, ""))
            result["episode"] = data.get(Item.NAME, "")
        case _:
            result["title"] = data.get(Item.NAME, "")
            result["episode"] = ""

    return result
