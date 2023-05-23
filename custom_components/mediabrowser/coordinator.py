"""Data coordinator for the Media Browser (Emby/Jellyfin) integration."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LATEST_QUERY_PARAMS, Key, Query
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__package__)


class MediaBrowserPushData:
    """Stores MediaBrowser sessions state."""

    def __init__(self, sessions_raw: list[dict[str, Any]]) -> None:
        """Initialize MediaBrowser push data."""
        self.sessions: dict[str, dict[str, Any]] = {}
        for session in reversed(sessions_raw):
            self.sessions[get_session_key(session)] = session


class MediaBrowserPushCoordinator(DataUpdateCoordinator[MediaBrowserPushData]):
    """Data push coordinator."""

    def __init__(self, hass: HomeAssistant, hub: MediaBrowserHub) -> None:
        """Initialize MediaBrowser push coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.hub = hub
        self.hub.register_sessions_raw_callback(self._sessions_raw_callback)
        self.players: set[str] = set()
        self.last_sessions: list[dict[str, Any]] = []

    async def _async_update_data(self) -> MediaBrowserPushData:
        return MediaBrowserPushData(await self.hub.async_get_sessions_raw())

    def _sessions_raw_callback(self, sessions: list[dict[str, Any]]) -> None:
        if not _compare_sessions(self.last_sessions, sessions):
            self.last_sessions = sessions
            self.async_set_updated_data(MediaBrowserPushData(sessions))


def _compare_sessions(
    sessions1: list[dict[str, Any]], sessions2: list[dict[str, Any]]
) -> bool:
    if len(sessions1) != len(sessions2):
        return False

    dict1 = {get_session_key(session): session for session in sessions1}
    dict2 = {get_session_key(session): session for session in sessions2}

    set1 = set(dict1)
    set2 = set(dict2)

    if any(set1 - set2) or any(set2 - set1):
        return False

    for key, value in dict1.items():
        if not _compare_session(value, dict2[key]):
            return False

    return True


SESSION_MONITORED_PROPERTIES = {
    Key.ID,
    Key.LAST_ACTIVITY_DATE,
    Key.USER_NAME,
    Key.CLIENT,
    Key.DEVICE_NAME,
    Key.DEVICE_ID,
    Key.APPLICATION_VERSION,
    Key.REMOTE_END_POINT,
    Key.SUPPORTS_REMOTE_CONTROL,
    Key.APP_ICON_URL,
    Key.SUPPORTED_COMMANDS,
    Key.PLAYLIST_INDEX,
    Key.PLAYLIST_LENGTH,
}

NPI_MONITORED_PROPERTIES = {Key.ID}

PS_MONITORED_PROPERTIES = {
    Key.CAN_SEEK,
    Key.IS_PAUSED,
    Key.IS_MUTED,
    Key.POSITION_TICKS,
    Key.VOLUME_LEVEL,
    Key.REPEAT_MODE,
}


def _compare_session(session1: dict[str, Any], session2: dict[str, Any]) -> bool:
    for prop in SESSION_MONITORED_PROPERTIES:
        if session1.get(prop) != session2.get(prop):
            return False

    ps1 = session1.get(Key.PLAY_STATE)
    ps2 = session2.get(Key.PLAY_STATE)

    if ps1 is None:
        return ps2 is None

    if ps2 is None:
        return False

    for prop in PS_MONITORED_PROPERTIES:
        if ps1.get(prop) != ps2.get(prop):
            return False

    np1 = session1.get(Key.NOW_PLAYING_ITEM)
    np2 = session2.get(Key.NOW_PLAYING_ITEM)

    if np1 is None:
        return np2 is None

    if np2 is None:
        return False

    for prop in NPI_MONITORED_PROPERTIES:
        if np1.get(prop) != np2.get(prop):
            return False

    return True


class MediaBrowserPollData:
    """Stores MediaBrowser state."""

    def __init__(self) -> None:
        """Initialize MediaBrowser poll data."""
        # user_id[item_type[library_id[items:total_record_count]]]
        self.library_infos: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        self.libraries: dict[str, dict[str, Any]] = {}
        self.users: dict[str, dict[str, Any]] = {}


class MediaBrowserPollCoordinator(DataUpdateCoordinator[MediaBrowserPollData]):
    """Data poll coordinator."""

    def __init__(
        self, hass: HomeAssistant, hub: MediaBrowserHub, scan_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan_interval)
        )
        self.hub = hub
        # user/type/library_id
        self.library_sensors: dict[str, dict[str, set[str]]] = {}

    async def _async_update_data(self) -> MediaBrowserPollData:
        data: MediaBrowserPollData = MediaBrowserPollData()
        data.library_infos = {}
        data.libraries = {
            library["Id"]: library
            for library in await self.hub.async_get_libraries_raw()
        }
        data.users = {user["Id"]: user for user in await self.hub.async_get_users_raw()}

        for user_id, item_type_dict in self.library_sensors.items():
            data.library_infos[user_id] = {}
            for item_type, library_set in item_type_dict.items():
                data.library_infos[user_id][item_type] = {}
                for library_id in library_set:
                    params = LATEST_QUERY_PARAMS | {Query.INCLUDE_ITEM_TYPES: item_type}
                    if library_id != Key.ALL:
                        params |= {Key.PARENT_ID: library_id}
                    data.library_infos[user_id][item_type][library_id] = (
                        await self.hub.async_get_user_items_raw(user_id, params)
                        if user_id != Key.ALL
                        else await self.hub.async_get_items_raw(params)
                    )

        return data


def get_session_key(session: dict[str, Any]) -> str:
    """Gets a uniqe session key"""
    return f"{session[Key.DEVICE_ID]}-{session[Key.CLIENT]}"
