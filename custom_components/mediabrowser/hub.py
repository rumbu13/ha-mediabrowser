"""Hub for the Media Browser (Emby/Jellyfin) integration."""

import asyncio
import json
import logging
from typing import Any
from collections.abc import Callable
import aiohttp
import async_timeout

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


from .errors import ForbiddenError, NotFoundError, RequestError, UnauthorizedError
from .const import (
    DEFAULT_CLIENT_NAME,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_VERSION,
    DEFAULT_REQUEST_TIMEOUT,
    PING_ID_EMBY,
    PING_ID_JELLYFIN,
)


from homeassistant.util import uuid

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
API_URL_USERS = "/Users"
API_URL_YEARS = "Years"


KEY_ACCEPT = "Accept"
KEY_AUTHORIZATION = "x-emby-authorization"
KEY_CLIENT = "MediaBrowserClient"
KEY_DEVICE = "Device"
KEY_DEVICE_ID = "DeviceId"
KEY_CONTENT_TYPE = "Content-Type"

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
        self.custom_name: str = custom_name
        self.ignore_web_players: bool = ignore_web_players
        self.ignore_dlna_players: bool = ignore_dlna_players
        self.ignore_mobile_players: bool = ignore_mobile_players

        schema_rest = "https" if use_ssl else "http"
        schema_ws = "wss" if use_ssl else "ws"

        self.rest_url: str = f"{schema_rest}://{self.host}:{self.port}"
        self.ws_url: str = f"{schema_ws}://{self.host}:{self.port}/websocket"

        auth = f'{KEY_CLIENT}="{self.client_name}",{KEY_DEVICE}="{self.device_name}",{KEY_DEVICE_ID}="{self.device_id}",{KEY_VERSION}="{self.device_version}"'
        headers = {
            KEY_CONTENT_TYPE: "application/json",
            KEY_ACCEPT: "application/json",
            KEY_AUTHORIZATION: auth,
        }
        connector = aiohttp.TCPConnector(ssl=self.use_ssl)
        self._rest = aiohttp.ClientSession(connector=connector, headers=headers)
        self._ws = None
        self._ping: str = None
        self._info: MBSystemInfo = None
        self.rest_connected = False
        self.ws_connected = False
        self._abort_ws: bool = True
        self._impersonated_user: MBUser = None
        self._impersonated_admin: MBUser = None

        self._sessions_callbacks: set[Callable[[list[MBSession]], None]] = set()

    def register_sessions_callback(
        self, callback: Callable[[list[MBSession]], None]
    ) -> None:
        """Registers a callback for sessions update."""
        self._sessions_callbacks.add(callback)

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
    def server_id(self) -> str:
        """Returns the server unique identifier."""
        return self._info.id

    @property
    def server_name(self) -> str:
        """Returns the server name."""
        return self._info.server_name or self.custom_name

    @property
    def server_version(self) -> str:
        """Returns the server version."""
        return self._info.version

    @property
    def server_os(self) -> str:
        """Returns the server operating system."""
        return self._info.operating_system

    @property
    def server_url(self) -> str:
        """Returns the server url."""
        return self._info.local_address

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
    def admin_id(self) -> str:
        """Returns an administrative user id for queries."""
        return self._impersonated_admin.id

    @property
    def user_id(self) -> str:
        """Returns an the best user for queries having access to all libraries."""
        return self._impersonated_user.id

    async def _async_rest_post(
        self, url: str, data: Any = None, params: dict[str, Any] | None = None
    ) -> str:
        url = self.rest_url + url
        params = {"api_key": self.api_key} | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.post(url, json=data, params=params)
        _ensure_success_status(result.status, url)
        return await result.text()

    async def _async_rest_get(self, url: str, params: dict = None):
        url = self.rest_url + url
        params = {"api_key": self.api_key} | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.get(url, params=params)
        _ensure_success_status(result.status, url)
        json_data = None
        try:
            json_data = await result.json()
        except json.JSONDecodeError:
            return await result.text()
        if json_data is not None and "error" in json_data:
            raise ConnectionError(
                'Error {} when getting data from "{}": {}'.format(json_data["error"]["code"], url, json_data["error"]["message"]),
            )
        return json_data

    async def async_get_sessions(self) -> list[MBSession]:
        """Gets a list of sessions."""

        return self._preprocess_sessions(
            [
                MBSession(session)
                for session in await self._async_rest_get(API_URL_SESSIONS)
            ]
        )

    async def async_ping(self) -> str:
        """Pings the server expecting some kind of pong."""
        self._ping = await self._async_rest_get(API_URL_PING)
        return self._ping

    async def async_get_libraries(self) -> MBResponse:
        """Gets the current server libraries."""
        return MBResponse(
            await self._async_rest_get(API_URL_LIBRARIES, {"isHidden": "false"})
        )

    async def async_get_items(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of items."""
        return MBResponse(await self._async_rest_get(API_URL_ITEMS, params))

    async def async_get_user_items(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of items."""
        return MBResponse(
            await self._async_rest_get(
                f"{API_URL_USERS}/{self.user_id}{API_URL_ITEMS}", params
            )
        )

    async def async_get_user_item(self, item_id: str) -> MBResponse:
        """Gets a singe item."""
        return MBItem(
            await self._async_rest_get(
                f"{API_URL_USERS}/{self.user_id}{API_URL_ITEMS}/{item_id}"
            )
        )

    async def async_get_channels(self, params: dict[str, Any] = None) -> MBResponse:
        """Gets a list of items."""
        return MBResponse(await self._async_rest_get(API_URL_CHANNELS, params))

    async def async_get_artists(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of artists."""
        return MBResponse(await self._async_rest_get(API_URL_ARTISTS, params))

    async def async_get_album_artists(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of artists."""
        return MBResponse(await self._async_rest_get(API_URL_ALBUM_ARTISTS, params))

    async def async_get_persons(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of persons."""
        return MBResponse(await self._async_rest_get(API_URL_PERSONS, params))

    async def async_get_studios(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of studios."""
        return MBResponse(await self._async_rest_get(API_URL_STUDIOS, params))

    async def async_get_genres(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of genres."""
        return MBResponse(await self._async_rest_get(API_URL_GENRES, params))

    async def async_get_prefixes(self, params: dict[str, Any]) -> list[MBItem]:
        """Gets a list of prefixes."""

        if self.is_emby:
            return [
                MBItem(prefix)
                for prefix in await self._async_rest_get(API_URL_PREFIXES, params)
            ]
        else:
            items = {
                item.name[0].upper()
                for item in (await self.async_get_items(params)).items
            }
            return [MBItem({"Name": item}) for item in sorted(items)]

    async def async_get_years(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of years."""
        return MBResponse(await self._async_rest_get("/Years", params))

    async def async_get_seasons(
        self, series_id: str, params: dict[str, Any]
    ) -> MBResponse:
        """Gets a list of seasons."""
        return MBResponse(
            await self._async_rest_get(
                f"{API_URL_SHOWS}/{series_id}{API_URL_SEASONS}", params
            )
        )

    async def async_get_tags(self, params: dict[str, Any]) -> MBResponse:
        """Gets a list of tags."""
        if self.is_emby:
            return MBResponse(await self._async_rest_get(API_URL_TAGS, params))
        return MBResponse({KEY_ITEMS: [], KEY_TOTAL_RECORD_COUNT: 0})

    async def async_play_command(self, session_id, command: str, params=None):
        """Executes the specified play command."""
        url = f"{API_URL_SESSIONS}/{session_id}{API_URL_PLAYING}/{command}"
        return await self._async_rest_post(url, params=params)

    async def async_play(self, session_id, params=None):
        """Launch a play session."""
        url = f"{API_URL_SESSIONS}/{session_id}{API_URL_PLAYING}"
        return await self._async_rest_post(url, params=params)

    async def async_command(self, session_id, command, data=None, params=None):
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
        return await self._async_rest_get(API_URL_AUTH_KEYS)

    async def async_get_info(self) -> MBSystemInfo:
        """Gets information about the server."""
        self._info = MBSystemInfo(await self._async_rest_get(API_URL_INFO))
        return self._info

    async def _async_impersonate(self) -> MBUser | None:
        """Obtains the first admin user available."""
        users: list[MBUser] = [
            MBUser(user) for user in await self._async_rest_get(API_URL_USERS)
        ]

        self._impersonated_admin = next(
            user
            for user in users
            if user.policy is not None
            and user.policy.is_administrator
            and (user.policy.is_disabled is None or not user.policy.is_disabled)
        )

        if self._impersonated_admin is None:
            raise PermissionError("Cannot impersonate an administrative user")

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
                while not self._abort_ws and not comm_failure:
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

    def _handle_message(self, message: dict[str, Any]) -> None:
        msg = json.loads(message)
        if msg.get("MessageType") == "Sessions":
            session_message = MBSessionsMessage(msg)
            self._call_sessions_callbacks(
                self._preprocess_sessions(session_message.sessions)
            )

    def _call_sessions_callbacks(self, sessions: list[MBSession]):
        for callback in self._sessions_callbacks:
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
