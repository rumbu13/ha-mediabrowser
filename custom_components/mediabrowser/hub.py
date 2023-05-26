"""Hub for the Media Browser (Emby/Jellyfin) integration."""

import urllib.parse
import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, Awaitable

import aiohttp
import async_timeout
from homeassistant.const import CONF_USERNAME, CONF_NAME, CONF_PASSWORD, CONF_URL
from homeassistant.util import uuid

from .helpers import autolog

from .const import (
    CONF_CACHE_SERVER_API_KEY,
    CONF_CACHE_SERVER_ID,
    CONF_CACHE_SERVER_NAME,
    CONF_CACHE_SERVER_PING,
    CONF_CACHE_SERVER_USER_ID,
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
    DEVICE_PROFILE,
    KEEP_ALIVE_TIMEOUT,
    ApiUrl,
    Key,
    Query,
    ServerType,
    Value,
)


_LOGGER = logging.getLogger(__package__)


class ServerOptions:
    """Represents a class storing server options"""

    def __init__(self, options: dict[str, Any]) -> None:
        self._data: dict[str, Any] = options
        self._parsed_url = urllib.parse.urlparse(self.url)

    @property
    def url(self) -> str:
        """Url of the server"""
        return self._data[CONF_URL]

    @property
    def username(self) -> str:
        """Username"""
        return self._data[CONF_USERNAME]

    @property
    def password(self) -> str:
        """Password"""
        return self._data[CONF_PASSWORD]

    @property
    def name(self) -> str | None:
        """Custom name"""
        return self._data.get(CONF_NAME)

    @property
    def device_name(self) -> str | None:
        """Device name"""
        return self._data.get(CONF_DEVICE_NAME)

    @property
    def device_id(self) -> str | None:
        """Device unique identifier"""
        return self._data.get(CONF_DEVICE_ID)

    @property
    def client_name(self) -> str | None:
        """Client name"""
        return self._data.get(CONF_CLIENT_NAME)

    @property
    def device_version(self) -> str | None:
        """Version"""
        return self._data.get(CONF_DEVICE_VERSION)

    @property
    def timeout(self) -> int | None:
        """Connection timeout"""
        return self._data.get(CONF_TIMEOUT)

    @property
    def ignore_web_players(self) -> bool | None:
        """Should ignore web players"""
        return self._data.get(CONF_IGNORE_WEB_PLAYERS)

    @property
    def ignore_dlna_players(self) -> bool | None:
        """Should ignore DLNA players"""
        return self._data.get(CONF_IGNORE_DLNA_PLAYERS)

    @property
    def ignore_mobile_players(self) -> bool | None:
        """Should ignore mobile players"""
        return self._data.get(CONF_IGNORE_MOBILE_PLAYERS)

    @property
    def ignore_app_players(self) -> bool | None:
        """Should ignore application players"""
        return self._data.get(CONF_IGNORE_APP_PLAYERS)

    @property
    def cached_api_key(self) -> str | None:
        """Cached API key"""
        return self._data.get(CONF_CACHE_SERVER_API_KEY)

    @property
    def cached_server_id(self) -> str | None:
        """Cached server unique identifier"""
        return self._data.get(CONF_CACHE_SERVER_ID)

    @property
    def cached_server_name(self) -> str | None:
        """Cached server name"""
        return self._data.get(CONF_CACHE_SERVER_NAME)

    @property
    def cached_server_ping(self) -> str | None:
        """Cached server ping response"""
        return self._data.get(CONF_CACHE_SERVER_PING)

    @property
    def cached_server_user_id(self) -> str | None:
        """Cached server user unique identifier"""
        return self._data.get(CONF_CACHE_SERVER_USER_ID)

    @property
    def cached_server_version(self) -> str | None:
        """Cached server version"""
        return self._data.get(CONF_CACHE_SERVER_VERSION)

    @property
    def host(self) -> str:
        "Hostname extracted from URL"
        return self._parsed_url.hostname

    @property
    def port(self) -> int | None:
        "Port extracted from URL"
        return self._parsed_url.port

    @property
    def use_ssl(self) -> bool:
        "Use SSL or not extracted from URL"
        return (
            self._parsed_url.scheme == "https"
            or self._parsed_url.scheme == ""
            and self._parsed_url.port == DEFAULT_SSL_PORT
        )


class MediaBrowserHub:
    """Represents a Emby/Jellyfin connection."""

    def __init__(self, options: ServerOptions) -> None:
        self._host: str = options.host
        self.username: str = options.username
        self.password: str = options.password
        self._use_ssl: bool = options.use_ssl
        self._port: int = (
            options.port
            if options.port is not None
            else (DEFAULT_SSL_PORT if self._use_ssl else DEFAULT_PORT)
        )
        self.api_key: str | None = options.cached_api_key
        self.user_id: str | None = options.cached_server_user_id
        self.timeout: float = options.timeout or DEFAULT_REQUEST_TIMEOUT
        self.client_name: str = options.client_name or DEFAULT_CLIENT_NAME
        self.device_name: str = options.device_name or DEFAULT_DEVICE_NAME
        if options.device_id is None:
            _LOGGER.warning("Missing device id")
        self.device_id: str = options.device_id or uuid.random_uuid_hex()
        self.device_version: str = options.device_version or DEFAULT_DEVICE_VERSION
        self._custom_name: str | None = options.name
        self.ignore_web_players: bool = (
            options.ignore_web_players or DEFAULT_IGNORE_WEB_PLAYERS
        )
        self.ignore_dlna_players: bool = (
            options.ignore_dlna_players or DEFAULT_IGNORE_DLNA_PLAYERS
        )
        self.ignore_mobile_players: bool = (
            options.ignore_mobile_players or DEFAULT_IGNORE_MOBILE_PLAYERS
        )
        self.ignore_app_players: bool = (
            options.ignore_app_players or DEFAULT_IGNORE_APP_PLAYERS
        )
        self.server_id: str | None = options.cached_server_id
        self.server_name: str | None = options.cached_server_name
        self.server_ping: str | None = options.cached_server_ping
        self.server_version: str | None = options.cached_server_version

        self._last_keep_alive: datetime = datetime.utcnow()
        self._keep_alive_timeout: float | None = None

        schema_rest = "https" if self._use_ssl else "http"
        self._rest_url: str = f"{schema_rest}://{self._host}:{self._port}"
        self.server_url: str = self._rest_url
        self._default_params: dict[str, Any] = {}

        self._default_headers: dict[str, Any] = {
            "Content-Type": "application/json",
            "Accept": "text/html, application/json",
        }
        self._default_auth: dict[str, str] = {}
        self._ws_url: str = ""
        self._auth_update()

        self._is_api_key_validated: bool = False

        connector = aiohttp.TCPConnector(ssl=self._use_ssl)
        self._rest = aiohttp.ClientSession(connector=connector)
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ws_loop: asyncio.Task[None] | None = None

        self._abort: bool = True

        self._sessions_listeners: set[
            Callable[[list[dict[str, Any]]], Awaitable[None]]
        ] = set()
        self._library_listeners: set[
            Callable[[dict[str, Any]], Awaitable[None]]
        ] = set()

    @property
    def server_type(self) -> ServerType:
        """Returns the server type"""
        if self.server_ping is not None:
            return (
                ServerType.EMBY
                if self.server_ping.lower().startswith(ServerType.EMBY)
                else (
                    ServerType.JELLYFIN
                    if self.server_ping.strip('"').startswith(ServerType.JELLYFIN)
                    else ServerType.UNKNOWN
                )
            )
        return ServerType.UNKNOWN

    @property
    def name(self) -> str | None:
        """Returns the server name."""
        return self._custom_name or self.server_name

    def add_sessions_listener(
        self, callback: Callable[[list[dict[str, Any]]], Awaitable[None]]
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_sessions_listener() -> None:
            self._sessions_listeners.remove(callback)

        self._sessions_listeners.add(callback)
        return remove_sessions_listener

    def add_library_listener(
        self, callback: Callable[[list[dict[str, Any]]], Awaitable[None]]
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_library_listener() -> None:
            self._library_listeners.remove(callback)

        self._library_listeners.add(callback)
        return remove_library_listener

    async def async_command(
        self, session_id: str, command: str, data=None, params=None
    ):
        """Executes the specified command."""
        await self._async_needs_authentication()
        url = f"{ApiUrl.SESSIONS}/{session_id}{ApiUrl.COMMAND}"
        data = {"Name": command, "Arguments": data}
        return await self._async_rest_post_get_text(url, data=data, params=params)

    async def async_get_artists(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.ARTISTS, params)

    async def async_get_genres(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.GENRES, params)

    async def async_get_items(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.ITEMS, params)

    async def async_get_libraries_raw(self) -> list[dict[str, Any]]:
        """Gets the current server libraries."""
        await self._async_needs_authentication()
        libraries = (
            await self._async_rest_get_json(
                ApiUrl.LIBRARIES, {Query.IS_HIDDEN: Value.FALSE}
            )
        )[Key.ITEMS]
        channels = (await self._async_rest_get_json(ApiUrl.CHANNELS))[Key.ITEMS]
        return libraries + channels

    async def async_get_persons(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.PERSONS, params)

    async def async_get_sessions(self) -> list[dict[str, Any]]:
        """Gets a list of sessions."""
        await self._async_needs_authentication()
        return self._preprocess_sessions(
            await self._async_rest_get_json(ApiUrl.SESSIONS)
        )

    async def async_get_playback_info(self, item_id: str) -> dict[str, Any]:
        """Gets Playback information for the specified item"""
        data = {
            "UserId": self.user_id,
            "DeviceProfile": DEVICE_PROFILE,
            "AutoOpenLiveStream": True,
            "IsPlayback": True,
        }
        return await self._async_rest_post_get_json(
            f"{ApiUrl.ITEMS}/{item_id}{ApiUrl.PLAYBACK_INFO}", data=data
        )

    async def async_get_prefixes(self, params: dict[str, Any]) -> list[dict[str, str]]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        if self.server_type == ServerType.EMBY:
            return await self._async_rest_get_json(ApiUrl.PREFIXES, params)
        items = (await self.async_get_items(params))[Key.ITEMS]
        prefixes = set(item[Key.NAME] for item in items if Key.NAME in item)
        return [{Key.NAME: prefix[0]} for prefix in prefixes if len(prefix) > 0]

    async def async_get_studios(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.STUDIOS, params)

    async def async_get_user_items(
        self, user_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(
            f"{ApiUrl.USERS}/{user_id}{ApiUrl.ITEMS}", params
        )

    async def async_get_users(self) -> list[dict[str, Any]]:
        """Gets a list of users"""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.USERS)

    async def async_get_years(self, params: dict[str, Any]) -> dict[str, Any]:
        """Gets a list of items."""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.YEARS, params)

    async def async_ping(self) -> str | None:
        """Pings the server expecting some kind of pong."""
        self.server_ping = await self._async_rest_get_text(ApiUrl.PING)
        return self.server_ping

    async def async_play(self, session_id: str, params=None):
        """Launch a play session."""
        await self._async_needs_authentication()
        url = f"{ApiUrl.SESSIONS}/{session_id}{ApiUrl.PLAYING}"
        return await self._async_rest_post_get_text(url, params=params)

    async def async_play_command(self, session_id, command: str, params=None):
        """Executes the specified play command."""
        await self._async_needs_authentication()
        url = f"{ApiUrl.SESSIONS}/{session_id}{ApiUrl.PLAYING}/{command}"
        return await self._async_rest_post_get_text(url, params=params)

    async def async_rescan(self) -> None:
        """Rescans libraries on the current server."""
        await self._async_needs_authentication()
        await self._async_rest_post_get_text(ApiUrl.LIBRARY_REFRESH)

    async def async_restart(self) -> None:
        """Restarts the current server."""
        await self._async_needs_authentication()
        await self._async_rest_post_get_text(ApiUrl.RESTART)

    async def async_shutdown(self) -> None:
        """Shutdowns the current server."""
        await self._async_needs_authentication()
        await self._async_rest_post_get_text(ApiUrl.SHUTDOWN)

    async def async_start(self, websocket: bool) -> None:
        """Initiates a connection to the media server."""
        await self._async_needs_server_verification()
        await self._async_needs_authentication()
        if websocket:
            if self._ws_loop is None or self._ws_loop.done:
                self._ws_loop = asyncio.ensure_future(self._async_ws_loop())

    async def async_stop(self) -> None:
        """Disconnect from the media server."""
        autolog(">>>")
        if self._ws_loop is not None and not self._ws_loop.done:
            self._ws_loop.cancel()
        await self._async_ws_disconnect()
        self._ws_loop = None
        await self._rest.close()

    async def async_test_custom_auth(self, username, password):
        """Test specified credentials"""
        old_api_key = self.api_key
        self.api_key = None
        self._auth_update()
        try:
            _ = await self._async_rest_post_get_json(
                ApiUrl.AUTHENTICATE, {"username": username, "pw": password}
            )
            _ = await self._async_rest_post_get_json(ApiUrl.AUTH_KEYS)
        finally:
            self.api_key = old_api_key
            self._auth_update()

    async def async_test_auth(self) -> dict[str, Any]:
        """Test if the current user has administrative rights"""
        return await self._async_rest_get_json(ApiUrl.AUTH_KEYS)

    async def _async_authenticate(self) -> None:
        self.api_key = None
        self._auth_update()
        response = await self._async_rest_post_get_json(
            ApiUrl.AUTHENTICATE, {"username": self.username, "pw": self.password}
        )
        self.api_key = response["AccessToken"]
        self.user_id = response["User"]["Id"]
        self._is_api_key_validated = True
        self._auth_update()

    async def _async_needs_authentication(self):
        if self.api_key is None:
            await self._async_authenticate()
        elif not self._is_api_key_validated:
            try:
                _ = await self.async_test_auth()
            except aiohttp.ClientResponseError as err:
                if err.status == 401:
                    await self._async_authenticate()
                else:
                    raise err

    async def _async_needs_server_verification(self) -> None:
        """Gets information about the server."""
        await self.async_ping()
        info = await self._async_rest_get_json(ApiUrl.INFO)
        server_id = info["Id"]
        if self.server_id is not None and self.server_id != server_id:
            raise ClientMismatchError(
                f"Server changed, unique id doesn't match: {self.server_id} (stored) vs {server_id} (remote)"
            )
        self.server_id = info.get("Id")
        self.server_name = info.get("ServerName")
        self.server_version = info.get("Version")

    async def _async_rest_post_response(
        self, url: str, data: Any = None, params: dict[str, Any] | None = None
    ) -> aiohttp.ClientResponse:
        url = self._rest_url + url
        params = self._default_params | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.post(
                url,
                json=data,
                params=params,
                headers=self._default_headers,
                raise_for_status=True,
            )
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

    async def _async_rest_get_response(
        self, url: str, params: dict[str, Any] | None
    ) -> aiohttp.ClientResponse:
        url = self._rest_url + url
        params = self._default_params | (params or {})
        async with async_timeout.timeout(self.timeout):
            result = await self._rest.get(
                url, params=params, headers=self._default_headers, raise_for_status=True
            )
        return result

    async def _async_rest_get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Any:
        response = await self._async_rest_get_response(url, params)
        return await response.json()

    async def _async_rest_get_text(
        self, url: str, params: dict[str, Any] | None = None
    ) -> str:
        response = await self._async_rest_get_response(url, params)
        return await response.text()

    async def _async_ws_connect(self) -> None:
        self._abort = False
        async with async_timeout.timeout(self.timeout):
            self._ws = await self._rest.ws_connect(
                f"{self._ws_url}?DeviceId={self.device_id}&api_key={self.api_key}"
            )
        await self._ws.send_str('{"MessageType":"SessionsStart", "Data": "1500,1500"}')

    async def _async_ws_disconnect(self) -> None:
        self._abort = True
        try:
            if self._ws is not None and not self._ws.closed:
                await self._ws.close()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Error while closing websocket connection: %s", err)
        self._ws = None

    async def _async_ws_loop(self):
        delay = 0
        self._abort = False
        while not self._abort:
            try:
                await self._async_needs_server_verification()
                await self._async_needs_authentication()
                await self._async_ws_connect()
            except ClientMismatchError as err:
                _LOGGER.warning("Server mismatch: %s", err)
            except aiohttp.ClientConnectionError as err:
                _LOGGER.warning("Connection error: %s", err)
            except aiohttp.ClientResponseError as err:
                _LOGGER.warning("Request error: %s (%s)", err.status, err.message)
            except (asyncio.TimeoutError, TimeoutError) as err:
                _LOGGER.warning("Timeout error: %s", err)
            except asyncio.CancelledError:
                _LOGGER.debug("Task was cancelled")
                break
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning("Unexpected error: %s", err)
            else:
                delay = 0
                while not self._abort and not self._ws.closed:
                    try:
                        message = await self._ws.receive(self._keep_alive_timeout)
                    except (asyncio.TimeoutError, TimeoutError):
                        self._send_keep_alive()
                    except asyncio.CancelledError:
                        _LOGGER.debug("Task was cancelled")
                        break
                    except Exception as err:  # pylint: disable=broad-except
                        _LOGGER.error("Websocket error: %s", err)
                        break
                    else:
                        match message.type:
                            case aiohttp.WSMsgType.TEXT:
                                await self._handle_message(message.data)
                            case aiohttp.WSMsgType.CLOSE | aiohttp.WSMsgType.CLOSING | aiohttp.WSMsgType.CLOSED:
                                _LOGGER.debug("Connection closed")
                            case _:
                                _LOGGER.warning(
                                    "Unexpected websocket message: %s", message.type
                                )
            if self._abort:
                break
            delay = max(delay * 2 + 2, 60)
            _LOGGER.debug("Reconnecting in %d seconds", delay)
            await asyncio.sleep(delay)

    def _auth_update(self) -> None:
        schema_ws = "wss" if self._use_ssl else "ws"
        self._ws_url: str = f"{schema_ws}://{self._host}:{self._port}"

        if self.server_ping is not None and self.server_type == ServerType.JELLYFIN:
            self._ws_url += "/socket"
            auth = (
                f'MediaBrowser Client="{self.client_name}"'
                + f', Device="{self.device_name}"'
                + f', DeviceId="{self.device_id}"'
                + f', Version="{self.device_version}"'
            )
            if self.api_key is not None:
                auth += f', Token="{self.api_key}"'
                self._ws_url += f"?api_key={self.api_key}"
            self._default_headers["X-Emby-Authorization"] = auth
        else:
            self._ws_url += "/embywebsocket"
            self._default_params["X-Emby-Client"] = self.client_name
            self._default_params["X-Emby-Device-Name"] = self.device_name
            self._default_params["X-Emby-Device-Id"] = self.device_id
            self._default_params["X-Emby-Client-Version"] = self.device_version
            if self.api_key is not None:
                self._default_params["X-Emby-Token"] = self.api_key
                self._ws_url += f"?api_key={self.api_key}&deviceId={self.device_id}"
            else:
                self._default_params.pop("X-Emby-Token", None)

    async def _call_sessions_listeners(self, sessions: list[dict[str, Any]]):
        for listener in self._sessions_listeners:
            try:
                _LOGGER.debug(listener)
                await listener(sessions)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error while handling sessions listener: %s", err)

    async def _call_library_listeners(self, event: dict[str, Any]):
        for listener in self._library_listeners:
            try:
                await listener(event)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning("Error while handling library listener: %s", err)

    async def _handle_message(self, message: str):
        msg = json.loads(message)

        if msg_type := msg.get("MessageType"):
            match msg_type:
                case "Sessions":
                    session_message = msg["Data"]
                    await self._call_sessions_listeners(
                        self._preprocess_sessions(session_message)
                    )
                case "KeepAlive":
                    _LOGGER.debug(
                        "KeepAlive response received from %s", self.server_url
                    )
                case "ForceKeepAlive":
                    _LOGGER.warning(
                        "ForceKeepAlive response received from %s", self.server_url
                    )
                    self._keep_alive_timeout = msg.get("Data", KEEP_ALIVE_TIMEOUT) / 2
                case "LibraryChanged":
                    event = msg["Data"]
                    await self._call_library_listeners(event)
                case _:
                    _LOGGER.warning(
                        "Unexpected message type (%s) received from %s",
                        msg_type,
                        self.server_url,
                    )
        if self._keep_alive_timeout is not None:
            elapsed = datetime.utcnow() - self._last_keep_alive
            if elapsed.total_seconds() >= self._keep_alive_timeout:
                self._send_keep_alive()

    def _preprocess_sessions(
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

    def _send_keep_alive(self) -> None:
        if not self._abort and self._ws is not None:
            _LOGGER.debug("Sending keep alive message")
            asyncio.ensure_future(self._ws.send_str('{"MessageType":"KeepAlive"}'))
            self._last_keep_alive = datetime.utcnow()
            self._keep_alive_timeout = None


WEB_PLAYERS = {"Emby Web", "Jellyfin Web"}

APP_PLAYERS = {"pyEmby", "HA", "Home Assistant"}

MOBILE_PLAYERS = {"Emby for Android", "Emby for iOS"}

DLNA_PLAYERS = {"Emby Server DLNA"}


class ClientMismatchError(aiohttp.ClientError):
    """Server unique id mismatch"""
