"""Hub for the Media Browser (Emby/Jellyfin) integration."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp
import async_timeout
from homeassistant.util import uuid

from .const import (
    DEFAULT_CLIENT_NAME,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_VERSION,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SERVER_NAME,
    PING_ID_EMBY,
    PING_ID_JELLYFIN,
)
from .errors import ForbiddenError, NotFoundError, RequestError, UnauthorizedError
from .models import (
    KEY_ITEMS,
    KEY_TOTAL_RECORD_COUNT,
    KEY_VERSION,
    MBItem,
    MBResponse,
    MBSession,
    MBSessionsMessage,
    MBSystemInfo,
    MBUser,
)

API_URL_ALBUM_ARTISTS = "/AlbumArtists"
API_URL_ARTISTS = "/Artists"
API_URL_AUTH_KEYS = "/Auth/Keys"
API_URL_CHANNELS = "/Channels"
API_URL_COMMAND = "/Command"
API_URL_GENRES = "/Genres"
API_URL_INFO = "/System/Info"
API_URL_ITEMS = "/Items"
API_URL_LIBRARIES = "/Library/MediaFolders"
API_URL_LIBRARY_REFRESH = "/Library/Refresh"
API_URL_PERSONS = "/Persons"
API_URL_PING = "/System/Ping"
API_URL_PLAYING = "/Playing"
API_URL_PREFIXES = "/Items/Prefixes"
API_URL_RESTART = "/System/Restart"
API_URL_SEASONS = "/Seasons"
API_URL_SESSIONS = "/Sessions"
API_URL_SHOWS = "/Shows"
API_URL_SHUTDOWN = "/System/Shutdown"
API_URL_STUDIOS = "/Studios"
API_URL_TAGS = "/Tags"
API_URL_TEST_API_KEY = "/Auth/Keys"
API_URL_USERS = "/Users"
API_URL_YEARS = "/Years"


KEY_ACCEPT = "Accept"
KEY_AUTHORIZATION = "x-emby-authorization"
KEY_CLIENT = "MediaBrowserClient"
KEY_CODE = "code"
KEY_CONTENT_TYPE = "Content-Type"
KEY_DEVICE = "Device"
KEY_DEVICE_ID = "DeviceId"
KEY_ERROR = "error"
KEY_IS_HIDDEN = "isHidden"
KEY_LIMIT = "Limit"
KEY_MESSAGE = "message"
KEY_RECURSIVE = "Recursive"
KEY_SORT_BY = "SortBy"
KEY_SORT_ORDER = "SortOrder"

VAL_APP_JSON = "application/json"
VAL_TRUE = "true"
VAL_FALSE = "false"


_LOGGER = logging.getLogger(__package__)


class MediaBrowserHub:
    """Represents a Emby/Jellyfin connection."""

    def __init__(
        self,
        host: str,
        api_key: str,
        port: int | None = None,
        use_ssl: bool | None = None,
        timeout: float | None = None,
        client_name: str | None = None,
        device_name: str | None = None,
        device_id: str | None = None,
        device_version: str | None = None,
        custom_name: str | None = None,
        ignore_web_players: bool = False,
        ignore_dlna_players: bool = False,
        ignore_mobile_players: bool = False,
    ) -> None:
        self.host: str = host
        self.api_key: str = api_key
        self.port: int = port or (8920 if bool(use_ssl) else 8096)
        self.use_ssl: bool = bool(use_ssl)
        self.timeout: float = timeout or DEFAULT_REQUEST_TIMEOUT
        self.client_name: str = client_name or DEFAULT_CLIENT_NAME
        self.device_name: str = device_name or DEFAULT_DEVICE_NAME
        self.device_id: str = device_id or uuid.random_uuid_hex()
        self.device_version: str = device_version or DEFAULT_DEVICE_VERSION
        self.custom_name: str = custom_name or DEFAULT_SERVER_NAME
        self.ignore_web_players: bool = ignore_web_players
        self.ignore_dlna_players: bool = ignore_dlna_players
        self.ignore_mobile_players: bool = ignore_mobile_players

        schema_rest = "https" if use_ssl else "http"
        schema_ws = "wss" if use_ssl else "ws"

        self.rest_url: str = f"{schema_rest}://{self.host}:{self.port}"
        self.ws_url: str = f"{schema_ws}://{self.host}:{self.port}/websocket"

        auth = (
            f'{KEY_CLIENT}="{self.client_name}",'
            + f'{KEY_DEVICE}="{self.device_name}",'
            + f'{KEY_DEVICE_ID}="{self.device_id}",'
            + f'{KEY_VERSION}="{self.device_version}"'
        )
        headers = {
            KEY_CONTENT_TYPE: VAL_APP_JSON,
            KEY_ACCEPT: VAL_APP_JSON,
            KEY_AUTHORIZATION: auth,
        }
        connector = aiohttp.TCPConnector(ssl=self.use_ssl)
        self._rest = aiohttp.ClientSession(connector=connector, headers=headers)
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ping: str | None = None
        self._info: MBSystemInfo = MBSystemInfo.empty()
        self.rest_connected: bool = False
        self.ws_connected: bool = False
        self._abort_ws: bool = True
        self._impersonated_user: MBUser | None = None
        self._impersonated_admin: MBUser | None = None

        self._sessions_callbacks: set[Callable[[list[MBSession]], None]] = set()
        self._sessions_raw_callbacks: set[
            Callable[[list[dict[str, Any]]], None]
        ] = set()

    def register_sessions_callback(
        self, callback: Callable[[list[MBSession]], None]
    ) -> None:
        """Registers a callback for sessions update."""
        self._sessions_callbacks.add(callback)

    def register_sessions_raw_callback(
        self, callback: Callable[[list[dict[str, Any]]], None]
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_sessions_raw_callback() -> None:
            self._sessions_raw_callbacks.remove(callback)

        self._sessions_raw_callbacks.add(callback)
        return remove_sessions_raw_callback

    def unregister_sessions_callback(
        self, callback: Callable[[list[MBSession]], None]
    ) -> None:
        """Registers a callback for sessions update."""
        self._sessions_callbacks.discard(callback)

    async def async_connect(self) -> None:
        """Initiates a connection to the media server."""
        await self._async_rest_connect()
        await self._async_ws_connect()
        asyncio.ensure_future(self._async_ws_loop())

    async def async_disconnect(self) -> None:
        """Disconnect from the media server."""
        await self._async_ws_disconnect()
        await self._async_rest_disconnect()

    @property
    def server_id(self) -> str | None:
        """Returns the server unique identifier."""
        return self._info.id if self._info is not None else None

    @property
    def server_name(self) -> str:
        """Returns the server name."""
        return self.custom_name

    def real_server_name(self) -> str:
        """Returns the server name."""
        return (
            self._info.server_name
            if self._info is not None and self._info.server_name
            else self.custom_name
        )

    @property
    def server_version(self) -> str | None:
        """Returns the server version."""
        return self._info.version if self._info is not None else None

    @property
    def server_os(self) -> str | None:
        """Returns the server operating system."""
        return self._info.operating_system if self._info is not None else None

    @property
    def server_url(self) -> str | None:
        """Returns the server url."""
        return self._info.local_address if self._info is not None else None

    @property
    def is_emby(self) -> bool:
        """Returns true if the server is Emby."""
        return self._ping is not None and self._ping.lower().startswith(PING_ID_EMBY)

    @property
    def is_jellyfin(self) -> bool:
        """Returns true if the server is Jellyfin."""
        return self._ping is not None and self._ping.lower().startswith(
            PING_ID_JELLYFIN
        )

    @property
    def admin_id(self) -> str | None:
        """Returns an administrative user id for queries."""
        return (
            self._impersonated_admin.id
            if self._impersonated_admin is not None
            else None
        )

    @property
    def user_id(self) -> str | None:
        """Returns an the best user for queries having access to all libraries."""
        return (
            self._impersonated_user.id if self._impersonated_user is not None else None
        )

    async def _async_rest_post(
        self, url: str, data: Any = None, params: dict[str, Any] | None = None
    ) -> str:
        url = self.rest_url + url
        params = {"api_key": self.api_key} | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.post(url, json=data, params=params)
        _ensure_success_status(result.status, url)
        return await result.text()

    async def async_test_api_key(self, api_key: str) -> None:
        """Tests the specified api_key"""
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.get(
                API_URL_AUTH_KEYS, params={"api_key": api_key}
            )
        _ensure_success_status(result.status, API_URL_AUTH_KEYS)
        await result.json()

    async def _async_rest_get_response(
        self, url: str, params: dict[str, Any] | None
    ) -> aiohttp.ClientResponse:
        url = self.rest_url + url
        params = {"api_key": self.api_key} | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.get(url, params=params)
        _ensure_success_status(result.status, url)
        return result

    async def _async_rest_get_text(
        self, url: str, params: dict[str, Any] | None = None
    ) -> str:
        response = await self._async_rest_get_response(url, params)
        return await response.text()

    async def _async_rest_get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._async_rest_get_response(url, params)
        json_data = await response.json()
        if json_data is not None and KEY_ERROR in json_data:
            error = json_data[KEY_ERROR]
            error_code = error.get(KEY_CODE)
            error_message = error.get(KEY_MESSAGE)
            raise RequestError(
                f"Error {error_code} when getting data from {url}: {error_message}"
            )
        return json_data

    async def async_get_sessions(self) -> list[MBSession]:
        """Gets a list of sessions."""

        return self._preprocess_sessions(
            [
                MBSession(session)
                for session in await self._async_rest_get_json(API_URL_SESSIONS)
            ]
        )

    async def async_get_sessions_raw(self) -> list[dict[str, Any]]:
        """Gets a list of sessions."""

        return self._preprocess_sessions_raw(
            await self._async_rest_get_json(API_URL_SESSIONS)
        )

    async def async_ping(self) -> str | None:
        """Pings the server expecting some kind of pong."""
        self._ping = await self._async_rest_get_text(API_URL_PING)
        return self._ping

    async def async_get_libraries(self) -> MBResponse:
        """Gets the current server libraries."""
        return MBResponse(
            await self._async_rest_get_json(API_URL_LIBRARIES, {"isHidden": "false"})
        )

    async def async_get_items(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of items."""
        return MBResponse(await self._async_rest_get_json(API_URL_ITEMS, params))

    async def async_get_items_raw(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(API_URL_ITEMS, params)

    async def async_get_user_items(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of items."""
        return MBResponse(
            await self._async_rest_get_json(
                f"{API_URL_USERS}/{self.user_id}{API_URL_ITEMS}", params
            )
        )

    async def async_get_user_item(self, item_id: str) -> MBResponse:
        """Gets a single item."""
        return MBResponse(
            await self._async_rest_get_json(
                f"{API_URL_USERS}/{self.user_id}{API_URL_ITEMS}/{item_id}"
            )
        )

    async def async_get_channels(
        self, params: dict[str, Any] | None = None
    ) -> MBResponse:
        """Gets a list of items."""
        return MBResponse(await self._async_rest_get_json(API_URL_CHANNELS, params))

    async def async_get_artists(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of artists."""
        return MBResponse(await self._async_rest_get_json(API_URL_ARTISTS, params))

    async def async_get_album_artists(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of artists."""
        return MBResponse(
            await self._async_rest_get_json(API_URL_ALBUM_ARTISTS, params)
        )

    async def async_get_persons(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of persons."""
        return MBResponse(await self._async_rest_get_json(API_URL_PERSONS, params))

    async def async_get_studios(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of studios."""
        return MBResponse(await self._async_rest_get_json(API_URL_STUDIOS, params))

    async def async_get_genres(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of genres."""
        return MBResponse(await self._async_rest_get_json(API_URL_GENRES, params))

    async def async_get_prefixes(self, params: dict[str, Any]) -> list[MBItem]:
        """Gets a list of prefixes."""

        if self.is_emby:
            return [
                MBItem(prefix)
                for prefix in await self._async_rest_get_json(API_URL_PREFIXES, params)
            ]
        else:
            items = {
                item.name[0].upper()
                for item in (await self.async_get_items(params)).items
                if item.name is not None and len(item.name) > 0
            }
            return [MBItem({"Name": item}) for item in sorted(items)]

    async def async_get_years(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of years."""
        return MBResponse(await self._async_rest_get_json(API_URL_YEARS, params))

    async def async_get_seasons(
        self, series_id: str, params: dict[str, Any]
    ) -> MBResponse:
        """Gets a list of seasons."""
        return MBResponse(
            await self._async_rest_get_json(
                f"{API_URL_SHOWS}/{series_id}{API_URL_SEASONS}", params
            )
        )

    async def async_get_users(self) -> list[MBUser]:
        """Gets a list of users"""
        return [MBUser(user) for user in await self._async_rest_get_json(API_URL_USERS)]

    async def async_get_tags(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of tags."""
        if self.is_emby:
            return MBResponse(await self._async_rest_get_json(API_URL_TAGS, params))
        return MBResponse({KEY_ITEMS: [], KEY_TOTAL_RECORD_COUNT: 0})

    async def async_play_command(self, session_id, command: str, params=None):
        """Executes the specified play command."""
        url = f"{API_URL_SESSIONS}/{session_id}{API_URL_PLAYING}/{command}"
        return await self._async_rest_post(url, params=params)

    async def async_play(self, session_id: str, params=None):
        """Launch a play session."""
        url = f"{API_URL_SESSIONS}/{session_id}{API_URL_PLAYING}"
        return await self._async_rest_post(url, params=params)

    async def async_command(
        self, session_id: str, command: str, data=None, params=None
    ):
        """Executes the specified command."""
        url = f"{API_URL_SESSIONS}/{session_id}{API_URL_COMMAND}"
        data = {"Name": command, "Arguments": data}
        return await self._async_rest_post(url, data=data, params=params)

    async def async_restart(self) -> None:
        """Restarts the current server."""
        await self._async_rest_post(API_URL_RESTART)

    async def async_shutdown(self) -> None:
        """Shutdowns the current server."""
        await self._async_rest_post(API_URL_SHUTDOWN)

    async def async_rescan(self) -> None:
        """Rescans libraries on the current server."""
        await self._async_rest_post(API_URL_LIBRARY_REFRESH)

    async def _async_get_auth_keys(self) -> dict[str, Any]:
        return await self._async_rest_get_json(API_URL_AUTH_KEYS)

    async def async_get_info(self) -> MBSystemInfo:
        """Gets information about the server."""
        self._info = MBSystemInfo(await self._async_rest_get_json(API_URL_INFO))
        return self._info

    async def async_get_latest(self, item_type: str, limit: int = 5) -> MBResponse:
        """Obtains the last added items."""
        params = {
            KEY_LIMIT: limit,
            KEY_RECURSIVE: VAL_TRUE,
            KEY_SORT_BY: "DateCreated,SortName,ProductionYear",
            KEY_SORT_ORDER: "Descending,Descending,Descending",
            "IsVirtualItem": "false",
            "GroupItemsIntoCollections": "false",
            "Fields": "CommunityRating,Studios,PremiereDate,Genres,DateCreated,"
            + "OfficialRating,ParentIndexNumber,IndexNumber,AirTime,"
            + "ParentId,ImageTags,ParentPrimaryImageItemId,AlbumPrimaryImageTag,"
            + "AlbumId,SeriesPrimaryImageTag,SeriesId,"
            + "ChannelPrimaryImageTag,ChannelId,ParentArtItemId,ParentArtImageTag,SeriesName",
            "IncludeItemTypes": item_type,
        }
        return await self.async_get_items(params)

    async def async_get_latest_raw(
        self, item_type: str, limit: int = 5
    ) -> dict[str, Any]:
        """Obtains the last added items."""
        params = {
            KEY_LIMIT: limit,
            KEY_RECURSIVE: VAL_TRUE,
            KEY_SORT_BY: "DateCreated,SortName,ProductionYear",
            KEY_SORT_ORDER: "Descending,Descending,Descending",
            "IsVirtualItem": "false",
            "GroupItemsIntoCollections": "false",
            "Fields": "CommunityRating,Studios,PremiereDate,Genres,DateCreated,"
            + "OfficialRating,ParentIndexNumber,IndexNumber,AirTime,"
            + "ParentId,ImageTags,ParentPrimaryImageItemId,AlbumPrimaryImageTag,"
            + "AlbumId,SeriesPrimaryImageTag,SeriesId,"
            + "ChannelPrimaryImageTag,ChannelId,ParentArtItemId,ParentArtImageTag,SeriesName",
            "IncludeItemTypes": item_type,
        }
        return await self.async_get_items_raw(params)

    async def _async_impersonate(self) -> None:
        """Obtains the first admin user available."""
        users = await self.async_get_users()

        self._impersonated_admin = next(
            user
            for user in users
            if user.policy is not None
            and user.policy.is_administrator
            and (user.policy.is_disabled is None or not user.policy.is_disabled)
        )

        if self._impersonated_admin is None:
            raise PermissionError("Cannot impersonate an administrative user")

        if self._impersonated_admin.policy is not None:
            if self._impersonated_admin.policy.enable_all_folders:
                self._impersonated_user = self._impersonated_admin
            else:
                self._impersonated_user = next(
                    user
                    for user in users
                    if user.policy is not None
                    and user.policy.enable_all_folders
                    and (user.policy.is_disabled is None or not user.policy.is_disabled)
                )

        if self._impersonated_user is None:
            self._impersonated_user = self._impersonated_admin

    async def _async_rest_connect(self) -> None:
        if not self.rest_connected:
            await self.async_get_sessions()
            await self.async_ping()
            await self.async_get_info()
            await self._async_get_auth_keys()
            await self._async_impersonate()
            self.rest_connected = True

    async def _async_rest_disconnect(self):
        if self.rest_connected:
            try:
                await self._rest.close()
            finally:
                self.rest_connected = False

    async def _async_ws_connect(self) -> None:
        self._abort_ws = False
        async with async_timeout.timeout(self.timeout):
            self._ws = await self._rest.ws_connect(
                f"{self.ws_url}?DeviceId={self.device_id}&api_key={self.api_key}"
            )
        await self._ws.send_str('{"MessageType":"SessionsStart", "Data": "1500,1500"}')
        self.ws_connected = True

    async def _async_ws_disconnect(self) -> None:
        self._abort_ws = True
        try:
            if self.ws_connected and self._ws is not None:
                await self._ws.close()
        finally:
            self.ws_connected = False

    async def _async_ws_loop(self):
        failures = 0
        while not self._abort_ws:
            conn_failure = False
            try:
                await self._async_ws_connect()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Websocket connection error: %s", err)
                conn_failure = True
            else:
                failures = 0
                comm_failure = False
                while not self._abort_ws and not comm_failure and self._ws is not None:
                    try:
                        message = await self._ws.receive()
                        match message.type:
                            case aiohttp.WSMsgType.TEXT:
                                self._handle_message(message.data)
                            case aiohttp.WSMsgType.CLOSE | aiohttp.WSMsgType.CLOSING:
                                comm_failure = True
                                _LOGGER.warning("Websocket connection closed")
                            case aiohttp.WSMsgType.PING | aiohttp.WSMsgType.PONG:
                                _LOGGER.warning("Unexpected websocket ping or pong")
                            case aiohttp.WSMsgType.BINARY:
                                _LOGGER.warning("Unexpected websocket binary message")
                            case _:
                                comm_failure = True
                                _LOGGER.error("Websocket error: %s", message)
                    except Exception as err:  # pylint: disable=broad-except
                        _LOGGER.exception("Websocket communication error: %s", err)
                        comm_failure = True
                if comm_failure:
                    failures = failures + 1
            if conn_failure:
                failures = failures + 1
            if not self._abort_ws:
                secs = failures * 3 + 3
                _LOGGER.warning("Websocket reconnecting in %d seconds", secs)
                await asyncio.sleep(secs)

    def _preprocess_sessions(self, sessions: list[MBSession]) -> list[MBSession]:
        return [
            session
            for session in sessions
            if session.device_id != self.device_id
            and session.device_name != self.device_name
            and session.client != self.client_name
            and (
                not self.ignore_web_players
                or (self.ignore_web_players and not session.is_web)
            )
            and (
                not self.ignore_dlna_players
                or (self.ignore_dlna_players and not session.is_dlna)
            )
            and (
                not self.ignore_mobile_players
                or (self.ignore_mobile_players and not session.is_mobile)
            )
        ]

    def _preprocess_sessions_raw(
        self, sessions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            session
            for session in sessions
            if session.get("DeviceId") != self.device_id
            and session.get("Client") != self.client_name
            and not session.get("Client") in APP_PLAYERS
            and (
                not self.ignore_web_players
                or (
                    self.ignore_web_players and not session.get("Client") in WEB_PLAYERS
                )
            )
            and (
                not self.ignore_dlna_players
                or (
                    self.ignore_dlna_players
                    and not session.get("Client") in DLNA_PLAYERS
                )
            )
            and (
                not self.ignore_mobile_players
                or (
                    self.ignore_mobile_players
                    and not session.get("Client") in MOBILE_PLAYERS
                )
            )
        ]

    def _handle_message(self, message: str) -> None:
        msg = json.loads(message)
        if msg.get("MessageType") == "Sessions":
            session_message = MBSessionsMessage(msg)
            if session_message.sessions is not None:
                self._call_sessions_callbacks(
                    self._preprocess_sessions(session_message.sessions)
                )
            session_message_raw = msg["Data"]
            self._call_sessions_raw_callbacks(
                self._preprocess_sessions_raw(session_message_raw)
            )

    def _call_sessions_callbacks(self, sessions: list[MBSession]):
        for callback in self._sessions_callbacks:
            callback(sessions)

    def _call_sessions_raw_callbacks(self, sessions: list[dict[str, Any]]):
        for callback in self._sessions_raw_callbacks:
            callback(sessions)


def _ensure_success_status(status: int, url: str) -> None:
    if status not in [200, 204]:
        message = f"Error {status} when requesting data from {url}"
        match status:
            case 401:
                raise UnauthorizedError(message)
            case 403:
                raise ForbiddenError(message)
            case 404:
                raise NotFoundError(message)
            case _:
                raise RequestError(message)


WEB_PLAYERS = {"Emby Web"}

APP_PLAYERS = {"pyEmby", "HA"}

MOBILE_PLAYERS = {"Emby for Android", "Emby for iOS"}

DLNA_PLAYERS = {"Emby Server DLNA"}
