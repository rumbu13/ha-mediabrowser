"""Hub for the Media Browser (Emby/Jellyfin) integration."""

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from types import MappingProxyType
from typing import Any

import aiohttp
import async_timeout
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_NAME, CONF_PORT, CONF_SSL
from homeassistant.util import uuid

from .const import (
    CONF_CACHE_SERVER_ADMIN_ID,
    CONF_CACHE_SERVER_ID,
    CONF_CACHE_SERVER_NAME,
    CONF_CACHE_SERVER_OS,
    CONF_CACHE_SERVER_PING,
    CONF_CACHE_SERVER_VERSION,
    CONF_CLIENT_NAME,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_VERSION,
    CONF_IGNORE_APP_PLAYERS,
    CONF_IGNORE_DLNA_PLAYERS,
    CONF_IGNORE_MOBILE_PLAYERS,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_TIMEOUT,
    DEFAULT_CLIENT_NAME,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_VERSION,
    DEFAULT_IGNORE_APP_PLAYERS,
    DEFAULT_IGNORE_DLNA_PLAYERS,
    DEFAULT_IGNORE_MOBILE_PLAYERS,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_PORT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SSL_PORT,
    DEFAULT_USE_SSL,
    DEVICE_PROFILE,
    KEEP_ALIVE_TIMEOUT,
    ApiUrl,
    Key,
    Query,
    ServerType,
    Value,
)
from .errors import (
    ForbiddenError,
    MismatchError,
    NotFoundError,
    RequestError,
    UnauthorizedError,
)

_LOGGER = logging.getLogger(__package__)


class MediaBrowserHub:
    """Represents a Emby/Jellyfin connection."""

    def __init__(
        self, config: MappingProxyType[str, Any], options: MappingProxyType[str, Any]
    ) -> None:
        self.host: str = config[CONF_HOST]
        self.api_key: str = options[CONF_API_KEY]
        self.use_ssl: bool = config.get(CONF_SSL, DEFAULT_USE_SSL)
        self.port: int = config.get(
            CONF_PORT, DEFAULT_SSL_PORT if self.use_ssl else DEFAULT_PORT
        )
        self.timeout: float = options.get(CONF_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
        self.client_name: str = options.get(CONF_CLIENT_NAME, DEFAULT_CLIENT_NAME)
        self.device_name: str = options.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        self.device_id: str = options.get(CONF_DEVICE_ID, uuid.random_uuid_hex())
        self.device_version: str = options.get(
            CONF_DEVICE_VERSION, DEFAULT_DEVICE_VERSION
        )
        self.custom_name: str | None = options.get(CONF_NAME)
        self.ignore_web_players: bool = options.get(
            CONF_IGNORE_WEB_PLAYERS, DEFAULT_IGNORE_WEB_PLAYERS
        )
        self.ignore_dlna_players: bool = options.get(
            CONF_IGNORE_DLNA_PLAYERS, DEFAULT_IGNORE_DLNA_PLAYERS
        )
        self.ignore_mobile_players: bool = options.get(
            CONF_IGNORE_MOBILE_PLAYERS, DEFAULT_IGNORE_MOBILE_PLAYERS
        )
        self.ignore_app_players: bool = options.get(
            CONF_IGNORE_APP_PLAYERS, DEFAULT_IGNORE_APP_PLAYERS
        )

        self.server_id: str | None = options.get(CONF_CACHE_SERVER_ID)
        self.server_name: str | None = options.get(CONF_CACHE_SERVER_NAME)
        self.server_ping: str | None = options.get(CONF_CACHE_SERVER_PING)
        self.server_os: str | None = options.get(CONF_CACHE_SERVER_OS)
        self.server_version: str | None = options.get(CONF_CACHE_SERVER_VERSION)
        self.server_admin_id: str = options.get(CONF_CACHE_SERVER_ADMIN_ID, "")

        self.last_keep_alive: datetime = datetime.utcnow()
        self.keep_alive_timeout: float | None = None

        schema_rest = "https" if self.use_ssl else "http"
        schema_ws = "wss" if self.use_ssl else "ws"

        self.rest_url: str = f"{schema_rest}://{self.host}:{self.port}"
        self.ws_url: str = f"{schema_ws}://{self.host}:{self.port}/websocket"

        self.server_url: str = self.rest_url

        auth = (
            f'{Key.MBCLIENT}="{self.client_name}",'
            + f'{Key.DEVICE}="{self.device_name}",'
            + f'{Key.DEVICE_ID}="{self.device_id}",'
            + f'{Key.VERSION}="{self.device_version}"'
        )
        headers: dict[str, Any] = {
            Key.CONTENT_TYPE: Value.APPLICATION_JSON,
            Key.ACCEPT: Value.APPLICATION_JSON,
            Key.AUTHORIZATION: auth,
        }
        connector = aiohttp.TCPConnector(ssl=self.use_ssl)
        self._rest = aiohttp.ClientSession(connector=connector, headers=headers)
        self._ws: aiohttp.ClientWebSocketResponse | None = None

        self.rest_connected: bool = False
        self.ws_connected: bool = False
        self._abort_ws: bool = True

        self._sessions_raw_callbacks: set[
            Callable[[list[dict[str, Any]]], None]
        ] = set()

    def register_sessions_raw_callback(
        self, callback: Callable[[list[dict[str, Any]]], None]
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_sessions_raw_callback() -> None:
            self._sessions_raw_callbacks.remove(callback)

        self._sessions_raw_callbacks.add(callback)
        return remove_sessions_raw_callback

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
    def server_type(self) -> ServerType:
        """Returns the server type"""
        if self.server_ping is not None:
            return (
                ServerType.EMBY
                if self.server_ping.lower().startswith(ServerType.EMBY)
                else (
                    ServerType.JELLYFIN
                    if self.server_ping.startswith(ServerType.JELLYFIN)
                    else ServerType.UNKNOWN
                )
            )
        return ServerType.UNKNOWN

    @property
    def name(self) -> str | None:
        """Returns the server name."""
        return self.custom_name or self.server_name

    async def _async_rest_post_response(
        self, url: str, data: Any = None, params: dict[str, Any] | None = None
    ) -> aiohttp.ClientResponse:
        url = self.rest_url + url
        params = {"api_key": self.api_key} | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.post(url, json=data, params=params)
        _ensure_success_status(result.status, url)
        return result

    async def _async_rest_post_get_json(
        self, url: str, data: Any = None, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = await self._async_rest_post_response(url, data, params)
        return await response.json()

    async def _async_rest_post_get_text(
        self, url: str, data: Any = None, params: dict[str, Any] | None = None
    ) -> str:
        response = await self._async_rest_post_response(url, data, params)
        return await response.text()

    async def async_test_api_key(self, api_key: str) -> None:
        """Tests the specified api_key"""
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.get(ApiUrl.AUTH_KEYS, params={"api_key": api_key})
        _ensure_success_status(result.status, ApiUrl.AUTH_KEYS)
        await result.json()

    async def async_test_user(self, user_id: str) -> None:
        """Obtains the first admin user available."""
        users = await self.async_get_users_raw()
        admin = next(
            (user for user in users if user.get(Key.ID) == user_id),
            None,
        )
        if admin is None or Key.ID not in admin:
            raise PermissionError("Cannot find a suitable user to impersonate")

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
        return await response.json()

    async def async_get_sessions_raw(self) -> list[dict[str, Any]]:
        """Gets a list of sessions."""

        return self._preprocess_sessions_raw(
            await self._async_rest_get_json(ApiUrl.SESSIONS)
        )

    async def async_ping(self) -> str | None:
        """Pings the server expecting some kind of pong."""
        self.server_ping = await self._async_rest_get_text(ApiUrl.PING)
        return self.server_ping

    async def async_get_libraries_raw(self) -> list[dict[str, Any]]:
        """Gets the current server libraries."""
        libraries = (
            await self._async_rest_get_json(
                ApiUrl.LIBRARIES, {Query.IS_HIDDEN: Value.FALSE}
            )
        )[Key.ITEMS]
        channels = (await self._async_rest_get_json(ApiUrl.CHANNELS))[Key.ITEMS]
        return libraries + channels

    async def async_get_items_raw(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(ApiUrl.ITEMS, params)

    async def async_get_artists(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(ApiUrl.ARTISTS, params)

    async def async_get_persons(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(ApiUrl.PERSONS, params)

    async def async_get_genres(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(ApiUrl.GENRES, params)

    async def async_get_prefixes(self, params: dict[str, Any]) -> list[dict[str, str]]:
        """Gets a list of items."""
        if self.server_type == ServerType.EMBY:
            return await self._async_rest_get_json(ApiUrl.PREFIXES, params)
        items = (await self.async_get_items_raw(params))[Key.ITEMS]
        prefixes = set(item[Key.NAME] for item in items if Key.NAME in item)
        return [{Key.NAME: prefix[0]} for prefix in prefixes if len(prefix) > 0]

    async def async_get_years(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(ApiUrl.YEARS, params)

    async def async_get_studios(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(ApiUrl.STUDIOS, params)

    async def async_get_user_items_raw(
        self, user_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Gets a list of items."""
        return await self._async_rest_get_json(
            f"{ApiUrl.USERS}/{user_id}{ApiUrl.ITEMS}", params
        )

    async def async_get_users_raw(self) -> list[dict[str, Any]]:
        """Gets a list of users"""
        return await self._async_rest_get_json(ApiUrl.USERS)

    async def async_play_command(self, session_id, command: str, params=None):
        """Executes the specified play command."""
        url = f"{ApiUrl.SESSIONS}/{session_id}{ApiUrl.PLAYING}/{command}"
        return await self._async_rest_post_get_text(url, params=params)

    async def async_play(self, session_id: str, params=None):
        """Launch a play session."""
        url = f"{ApiUrl.SESSIONS}/{session_id}{ApiUrl.PLAYING}"
        return await self._async_rest_post_get_text(url, params=params)

    async def async_command(
        self, session_id: str, command: str, data=None, params=None
    ):
        """Executes the specified command."""
        url = f"{ApiUrl.SESSIONS}/{session_id}{ApiUrl.COMMAND}"
        data = {"Name": command, "Arguments": data}
        return await self._async_rest_post_get_text(url, data=data, params=params)

    async def async_restart(self) -> None:
        """Restarts the current server."""
        await self._async_rest_post_get_text(ApiUrl.RESTART)

    async def async_shutdown(self) -> None:
        """Shutdowns the current server."""
        await self._async_rest_post_get_text(ApiUrl.SHUTDOWN)

    async def async_rescan(self) -> None:
        """Rescans libraries on the current server."""
        await self._async_rest_post_get_text(ApiUrl.LIBRARY_REFRESH)

    async def _async_get_auth_keys(self) -> dict[str, Any]:
        return await self._async_rest_get_json(ApiUrl.AUTH_KEYS)

    async def async_get_info_raw(self) -> dict[str, Any]:
        """Gets information about the server."""
        info = await self._async_rest_get_json(ApiUrl.INFO)
        self.server_id = info[Key.ID]
        self.server_os = info.get("OperatingSystem")
        self.server_name = info.get("ServerName")
        self.server_version = info.get("Version")
        return info

    async def _async_impersonate(self) -> None:
        """Obtains the first admin user available."""
        users = await self.async_get_users_raw()

        admin: dict[str, Any] | None = None

        if self.server_admin_id is not None:
            admin = next(
                (user for user in users if user.get(Key.ID) == self.server_admin_id),
                None,
            )

        if admin is None:
            admin = next(
                (
                    user
                    for user in users
                    if Key.POLICY in user
                    and user[Key.POLICY].get(Key.IS_ADMINISTRATOR, False)
                    and not user[Key.POLICY].get(Key.IS_DISABLED, False)
                ),
                None,
            )

        if admin is None or Key.ID not in admin:
            raise PermissionError("Cannot find a suitable user to impersonate")

        self.server_admin_id = admin[Key.ID]

    async def _async_rest_connect(self) -> None:
        if not self.rest_connected:
            old_server_id = self.server_id
            await self.async_get_sessions_raw()
            await self.async_ping()
            await self.async_get_info_raw()
            if old_server_id is not None and self.server_id != old_server_id:
                raise MismatchError(
                    f"Server changed, unique id doesn't match: {old_server_id} (stored) vs {self.server_admin_id} (remote)"
                )
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
            self._ws = None

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
                        message = await self._ws.receive(self.keep_alive_timeout)
                        match message.type:
                            case aiohttp.WSMsgType.TEXT:
                                self._handle_message(message.data)
                            case aiohttp.WSMsgType.CLOSE | aiohttp.WSMsgType.CLOSING | aiohttp.WSMsgType.CLOSED:
                                comm_failure = True
                                _LOGGER.warning("Websocket connection closed")
                            case _:
                                _LOGGER.warning(
                                    "Unexpected websocket message: %s", message.type
                                )
                    except (TimeoutError, asyncio.TimeoutError):
                        self._send_keep_alive()
                    except Exception as err:  # pylint: disable=broad-except
                        _LOGGER.error("Websocket communication error: %s", err)
                        comm_failure = True
                if comm_failure:
                    failures = failures + 1
            if conn_failure:
                failures = failures + 1
            if not self._abort_ws:
                secs = failures * 3 + 3
                _LOGGER.warning("Websocket reconnecting in %d seconds", secs)
                await asyncio.sleep(secs)
            self._ws = None

    async def async_playback_info(self, item_id: str) -> dict[str, Any]:
        """Gets Playback information for the specified item"""
        data = {
            "UserId": self.server_admin_id,
            "DeviceProfile": DEVICE_PROFILE,
            "AutoOpenLiveStream": True,
            "IsPlayback": True,
        }
        return await self._async_rest_post_get_json(
            f"{ApiUrl.ITEMS}/{item_id}{ApiUrl.PLAYBACK_INFO}", data=data
        )

    def _handle_message(self, message: str):
        msg = json.loads(message)

        if msg_type := msg.get("MessageType"):
            match msg_type:
                case "Sessions":
                    session_message = msg["Data"]
                    self._call_sessions_raw_callbacks(
                        self._preprocess_sessions_raw(session_message)
                    )
                case "KeepAlive":
                    _LOGGER.debug(
                        "KeepAlive response received from %s", self.server_url
                    )
                case "ForceKeepAlive":
                    _LOGGER.warning(
                        "ForceKeepAlive response received from %s", self.server_url
                    )
                    self.keep_alive_timeout = msg.get("Data", KEEP_ALIVE_TIMEOUT) / 2
                case _:
                    _LOGGER.warning(
                        "Unexpected message type (%s) received from %s",
                        msg_type,
                        self.server_url,
                    )
        if self.keep_alive_timeout is not None:
            elapsed = datetime.utcnow() - self.last_keep_alive
            if elapsed.total_seconds() >= self.keep_alive_timeout:
                self._send_keep_alive()

    def _send_keep_alive(self) -> None:
        if self.ws_connected and not self._abort_ws and self._ws is not None:
            _LOGGER.debug("Sending keep alive message")
            asyncio.ensure_future(self._ws.send_str('{"MessageType":"KeepAlive"}'))
            self.last_keep_alive = datetime.utcnow()
            self.keep_alive_timeout = None

    def _preprocess_sessions_raw(
        self, sessions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            session
            for session in sessions
            if session.get(Key.DEVICE_ID) != self.device_id
            and session.get(Key.CLIENT) != self.client_name
            and (
                not self.ignore_web_players
                or (
                    self.ignore_web_players
                    and not session.get(Key.CLIENT) in WEB_PLAYERS
                )
            )
            and (
                not self.ignore_dlna_players
                or (
                    self.ignore_dlna_players
                    and not session.get(Key.CLIENT) in DLNA_PLAYERS
                )
            )
            and (
                not self.ignore_mobile_players
                or (
                    self.ignore_mobile_players
                    and not session.get(Key.CLIENT) in MOBILE_PLAYERS
                )
            )
            and (
                not self.ignore_app_players
                or (
                    self.ignore_app_players
                    and not session.get(Key.CLIENT) in APP_PLAYERS
                )
            )
        ]

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


WEB_PLAYERS = {"Emby Web", "Jellyfin Web"}

APP_PLAYERS = {"pyEmby", "HA", "Home Assistant"}

MOBILE_PLAYERS = {"Emby for Android", "Emby for iOS"}

DLNA_PLAYERS = {"Emby Server DLNA"}
