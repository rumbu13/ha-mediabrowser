"""Hub for the Media Browser (Emby/Jellyfin) integration."""

from copy import deepcopy
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

from .helpers import (
    get_library_changed_event_data,
    get_user_data_changed_event_data,
    get_session_event_data,
    snake_case,
)

from .const import (
    APP_PLAYERS,
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
    CONF_EVENTS_ACTIVITY_LOG,
    CONF_EVENTS_OTHER,
    CONF_EVENTS_SESSIONS,
    CONF_EVENTS_TASKS,
    CONF_IGNORE_APP_PLAYERS,
    CONF_IGNORE_DLNA_PLAYERS,
    CONF_IGNORE_MOBILE_PLAYERS,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_TIMEOUT,
    DEFAULT_CLIENT_NAME,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_VERSION,
    DEFAULT_EVENTS_ACTIVITY_LOG,
    DEFAULT_EVENTS_OTHER,
    DEFAULT_EVENTS_SESSIONS,
    DEFAULT_EVENTS_TASKS,
    DEFAULT_IGNORE_APP_PLAYERS,
    DEFAULT_IGNORE_DLNA_PLAYERS,
    DEFAULT_IGNORE_MOBILE_PLAYERS,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_PORT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SSL_PORT,
    DEVICE_PROFILE_BASIC,
    DLNA_PLAYERS,
    KEEP_ALIVE_TIMEOUT,
    KEY_ALL,
    LATEST_QUERY_PARAMS,
    MOBILE_PLAYERS,
    WEB_PLAYERS,
    ApiUrl,
    Item,
    Query,
    Response,
    ServerType,
    Session,
    Value,
    WebsocketMessage,
)


_LOGGER = logging.getLogger(__package__)


class MediaBrowserHub:
    """Represents a Emby/Jellyfin connection."""

    def __init__(self, options: dict[str, Any]) -> None:
        parsed_url = urllib.parse.urlparse(options[CONF_URL])
        self._host: str = parsed_url.hostname
        self.username: str = options[CONF_USERNAME]
        self.password: str = options[CONF_PASSWORD]
        self._use_ssl: bool = parsed_url.scheme == "https" or (
            parsed_url.scheme == "" and parsed_url.port == DEFAULT_SSL_PORT
        )
        self._port: int = (
            parsed_url.port
            if parsed_url.port is not None
            else (DEFAULT_SSL_PORT if self._use_ssl else DEFAULT_PORT)
        )

        self.timeout: float = options.get(CONF_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
        self.client_name: str = options.get(CONF_CLIENT_NAME, DEFAULT_CLIENT_NAME)
        self.device_name: str = options.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        self.device_id: str = options.get(CONF_DEVICE_ID, uuid.random_uuid_hex())
        self.device_version: str = (
            options.get(CONF_DEVICE_VERSION) or DEFAULT_DEVICE_VERSION
        )
        self._custom_name: str | None = options.get(CONF_NAME)
        self.ignore_web_players: bool = options.get(
            CONF_IGNORE_WEB_PLAYERS, DEFAULT_IGNORE_WEB_PLAYERS
        )
        self.ignore_dlna_players: bool = options.get(
            CONF_IGNORE_DLNA_PLAYERS,
            DEFAULT_IGNORE_DLNA_PLAYERS,
        )
        self.ignore_mobile_players: bool = options.get(
            CONF_IGNORE_MOBILE_PLAYERS,
            DEFAULT_IGNORE_MOBILE_PLAYERS,
        )
        self.ignore_app_players: bool = options.get(
            CONF_IGNORE_APP_PLAYERS,
            DEFAULT_IGNORE_APP_PLAYERS,
        )

        self.send_session_events: bool = options.get(
            CONF_EVENTS_SESSIONS, DEFAULT_EVENTS_SESSIONS
        )
        self.send_activity_events: bool = options.get(
            CONF_EVENTS_ACTIVITY_LOG,
            DEFAULT_EVENTS_ACTIVITY_LOG,
        )
        self.send_task_events: bool = options.get(
            CONF_EVENTS_TASKS,
            DEFAULT_EVENTS_TASKS,
        )
        self.send_other_events: bool = options.get(
            CONF_EVENTS_OTHER,
            DEFAULT_EVENTS_OTHER,
        )

        self.api_key: str | None = options.get(CONF_CACHE_SERVER_API_KEY)
        self.user_id: str | None = options.get(CONF_CACHE_SERVER_USER_ID)
        self.server_id: str | None = options.get(CONF_CACHE_SERVER_ID)
        self.server_name: str | None = options.get(CONF_CACHE_SERVER_NAME)
        self.server_ping: str | None = options.get(CONF_CACHE_SERVER_PING)
        self.server_version: str | None = options.get(CONF_CACHE_SERVER_VERSION)

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

        self._availability_listeners: set[Callable[[bool], Awaitable[None]]] = set()
        self._availability_task: asyncio.Task[None] | None = None
        self.is_available: bool = False

        self._sessions: dict[str, dict[str, Any]] = {}
        self._raw_sessions: dict[str, dict[str, Any]] = {}

        self._library_infos: dict[tuple[str, str, str], dict[str, Any]] = {}

        self._sessions_listeners: set[
            Callable[[list[dict[str, Any]]], Awaitable[None]]
        ] = set()

        self._session_changed_listeners: set[
            Callable[[dict[str, Any] | None, dict[str, Any] | None], Awaitable[None]]
        ] = set()

        self._library_listeners: dict[
            tuple[str, str, str], set[Callable[[dict[str, Any]], Awaitable[None]]]
        ] = {}

        self._websocket_listeners: set[
            Callable[[str, dict[str, Any] | None], Awaitable[None]]
        ] = set()

        self._last_activity_log_entry: str | None = None

    @property
    def server_type(self) -> ServerType:
        """Returns the server type"""
        if self.server_ping is not None:
            return (
                ServerType.EMBY
                if self.server_ping.lower().startswith(ServerType.EMBY)
                else (
                    ServerType.JELLYFIN
                    if self.server_ping.strip('"')
                    .lower()
                    .startswith(ServerType.JELLYFIN)
                    else ServerType.UNKNOWN
                )
            )
        return ServerType.UNKNOWN

    @property
    def name(self) -> str | None:
        """Returns the server name."""
        return self._custom_name or self.server_name

    def on_availability_changed(
        self, callback: Callable[[bool], Awaitable[None]]
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_availability_listener() -> None:
            self._availability_listeners.discard(callback)

        self._availability_listeners.add(callback)
        return remove_availability_listener

    def on_sessions_changed(
        self, callback: Callable[[list[dict[str, Any]]], Awaitable[None]]
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_sessions_listener() -> None:
            self._sessions_listeners.discard(callback)

        self._sessions_listeners.add(callback)
        return remove_sessions_listener

    def on_session_changed(
        self,
        callback: Callable[
            [dict[str, Any] | None, dict[str, Any] | None], Awaitable[None]
        ],
    ) -> Callable[[], None]:
        """Registers a callback for sessions update."""

        def remove_session_changed_listener() -> None:
            self._session_changed_listeners.discard(callback)

        self._session_changed_listeners.add(callback)
        return remove_session_changed_listener

    def on_library_changed(
        self,
        library_id: str,
        user_id: str,
        item_type: str,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
    ):
        """Registers a callback for library change"""
        library_listeners = self._library_listeners.setdefault(
            (library_id, user_id, item_type), set()
        )

        self._library_infos.setdefault((library_id, user_id, item_type), {})

        def remove_library_listener() -> None:
            library_listeners.discard(callback)
            if not any(library_listeners):
                self._library_infos.pop((library_id, user_id, item_type), None)

        library_listeners.add(callback)
        return remove_library_listener

    def on_websocket_message(
        self, callback: Callable[[str, dict[str, Any] | None], Awaitable[None]]
    ) -> Callable[[], None]:
        """Registers a callback for websocket messages."""

        def remove_websocket_listener() -> None:
            self._websocket_listeners.discard(callback)

        self._websocket_listeners.add(callback)
        return remove_websocket_listener

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
        # jellyfin crashes sometimes if using /Items, providing 500 Internal server error
        return await self.async_get_user_items(self.user_id, params)  # type: ignore
        # await self._async_needs_authentication()
        # return await self._async_rest_get_json(ApiUrl.ITEMS, params)

    async def async_get_libraries(self) -> list[dict[str, Any]]:
        """Gets the current server libraries."""
        await self._async_needs_authentication()
        libraries = (
            await self._async_rest_get_json(
                ApiUrl.LIBRARIES, {Query.IS_HIDDEN: Value.FALSE}
            )
        )[Response.ITEMS]
        channels = (await self._async_rest_get_json(ApiUrl.CHANNELS))[Response.ITEMS]
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

    async def async_get_last_sessions(self) -> list[dict[str, Any]]:
        """Return current sessions from server or from cache if the server is not available"""
        if self.is_available:
            return await self.async_get_sessions()
        else:
            return list(self._sessions.values())

    async def async_get_playback_info(self, item_id: str) -> dict[str, Any]:
        """Gets Playback information for the specified item"""
        data = {
            "UserId": self.user_id,
            "DeviceProfile": DEVICE_PROFILE_BASIC,
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
        items = (await self.async_get_items(params))[Response.ITEMS]
        prefixes = set(item[Item.NAME] for item in items if Item.NAME in item)
        return [{Item.NAME: prefix[0]} for prefix in prefixes if len(prefix) > 0]

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
        await self._async_needs_sessions()
        if websocket:
            if self._ws_loop is None or self._ws_loop.done:
                self._ws_loop = asyncio.ensure_future(self._async_ws_loop())

    async def async_stop(self) -> None:
        """Disconnect from the media server."""
        if self._ws_loop is not None and not self._ws_loop.done:
            self._ws_loop.cancel()
        await self._async_ws_disconnect()
        self._ws_loop = None
        await self._rest.close()

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

    async def _async_get_activity_log_entries(
        self, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Get activity log entries"""
        await self._async_needs_authentication()
        return await self._async_rest_get_json(ApiUrl.ACTIVITY_LOG_ENTRIES, params)

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

    async def _async_needs_sessions(self):
        if not any(self._sessions):
            sessions = await self.async_get_sessions()
            self._sessions = {session[Session.ID]: session for session in sessions}

    async def _async_needs_server_verification(self) -> None:
        """Gets information about the server."""
        await self._async_ping()
        info = await self._async_rest_get_json(ApiUrl.INFO)
        server_id = info["Id"]
        if self.server_id is not None and self.server_id != server_id:
            raise ClientMismatchError(
                "Server changed, unique id doesn't match:"
                + f"{self.server_id} (stored) vs {server_id} (remote)"
            )
        self.server_id = info.get("Id")
        self.server_name = info.get("ServerName")
        self.server_version = info.get("Version")

    async def _async_ping(self) -> str | None:
        """Pings the server expecting some kind of pong."""
        self.server_ping = await self._async_rest_get_text(ApiUrl.PING)
        return self.server_ping

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
        _LOGGER.debug("Connecting to %s", self._ws_url)
        self._abort = False
        async with async_timeout.timeout(self.timeout):
            self._ws = await self._rest.ws_connect(self._ws_url)
        await self._ws.send_str('{"MessageType":"SessionsStart", "Data": "0,1500"}')
        if self.send_activity_events:
            await self._ws.send_str(
                '{"MessageType":"ActivityLogEntryStart", "Data": "0,1000"}'
            )
        if self.send_task_events:
            await self._ws.send_str(
                '{"MessageType":"ScheduledTasksInfoStart", "Data": "0,1500"}'
            )

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
                await self._async_needs_sessions()
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
                self._set_available(True)
                delay = 0
                while not self._abort and self._ws is not None and not self._ws.closed:
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
                            case (
                                aiohttp.WSMsgType.CLOSE
                                | aiohttp.WSMsgType.CLOSING
                                | aiohttp.WSMsgType.CLOSED
                            ):
                                _LOGGER.debug("Connection closed")
                            case _:
                                _LOGGER.warning(
                                    "Unexpected websocket message: %s", message.type
                                )
                self._set_available(False)
            if self._abort:
                break
            delay = min(delay * 2 + 2, 60)
            _LOGGER.debug("Reconnecting in %d seconds", delay)
            await asyncio.sleep(delay)

    def _auth_update(self) -> None:
        schema_ws = "wss" if self._use_ssl else "ws"
        self._ws_url: str = f"{schema_ws}://{self._host}:{self._port}"
        _LOGGER.debug(
            "Server is %s because ping is %s", self.server_type, self.server_ping
        )
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

    async def _call_availability_listeners(self, available: bool) -> None:
        listeners = self._availability_listeners.copy()
        try:
            for listener in listeners:
                try:
                    await listener(available)
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error while handling availability listener %s: %s",
                        listener,
                        err,
                    )
        except asyncio.CancelledError:
            pass

    async def _call_sessions_listeners(self, sessions: list[dict[str, Any]]):
        listeners = self._sessions_listeners.copy()
        for listener in listeners:
            try:
                await listener(sessions)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Error while handling sessions listener %s: %s", listener, err
                )

    async def _call_session_changed_listeners(
        self,
        added: list[dict[str, Any]],
        removed: list[dict[str, Any]],
        updated: list[tuple[dict[str, Any], dict[str, Any]]],
    ) -> None:
        listeners = self._session_changed_listeners.copy()

        events = (
            [(None, session) for session in added]
            + [(session, None) for session in removed]
            + updated
        )

        for event in events:
            for listener in listeners:
                try:
                    await listener(event[0], event[1])
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error while handling availability listener %s: %s",
                        listener,
                        err,
                    )

    async def _call_library_listeners(self, library_ids: list[str]):
        listeners_dict = {
            key: listeners
            for key, listeners in self._library_listeners.items()
            if key[0] in library_ids
        }
        infos = self._library_infos.copy()
        for key, listeners in listeners_dict.items():
            if info := infos.get(key):
                for listener in listeners:
                    try:
                        await listener(info)
                    except Exception as err:  # pylint: disable=broad-except
                        _LOGGER.error(
                            "Error while handling library listener %s: %s",
                            listener,
                            err,
                        )

    async def _call_websocket_listeners(
        self, message_type: str, data: dict[str, Any] | None
    ):
        listeners = self._websocket_listeners.copy()
        for listener in listeners:
            try:
                await listener(message_type, data)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(
                    "Error while handling websocket listener %s: %s",
                    listener,
                    err,
                )

    async def _call_websocket_listeners_for_list(self, messages: list[tuple[str, Any]]):
        listeners = self._websocket_listeners.copy()
        for message in messages:
            for listener in listeners:
                try:
                    await listener(message[0], message[1])
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error while handling websocket listener %s: %s",
                        listener,
                        err,
                    )

    def _set_available(self, availability: bool):
        _LOGGER.debug(
            "%s server became %s",
            self.server_name,
            "available" if availability else "unavailable",
        )
        self.is_available = availability
        if any(self._availability_listeners):
            if self._availability_task is not None:
                if not self._availability_task.done:
                    self._availability_task.cancel()
            self._availability_task = asyncio.ensure_future(
                self._call_availability_listeners(availability)
            )

    def _get_changed_sessions(
        self,
        old_sessions: dict[str, dict[str, Any]],
        new_sessions: dict[str, dict[str, Any]],
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[tuple[dict[str, Any], dict[str, Any]]],
    ]:
        added_sessions = [
            session
            for session_id, session in new_sessions.items()
            if session_id not in old_sessions
        ]

        removed_sessions = [
            session
            for session_id, session in old_sessions.items()
            if session_id not in new_sessions
        ]

        updated_sessions = [
            (old_sessions[session_id], session)
            for session_id, session in new_sessions.items()
            if session_id in old_sessions and old_sessions[session_id] != session
        ]

        return (added_sessions, removed_sessions, updated_sessions)

    async def _handle_sessions_message(self, sessions: list[dict[str, Any]]) -> None:
        old_raw_sessions = deepcopy(self._raw_sessions)
        old_sessions = deepcopy(self._sessions)

        new_raw_sessions = {
            session["Id"]: get_session_event_data(deepcopy(session))
            for session in sessions
        }
        new_sessions = {
            session["Id"]: session for session in self._preprocess_sessions(sessions)
        }
        self._raw_sessions = new_raw_sessions
        self._sessions = new_sessions

        if any(self._sessions_listeners):
            await self._call_sessions_listeners(list(new_sessions.values()))

        if self.send_session_events and any(self._websocket_listeners):
            added, removed, updated = self._get_changed_sessions(
                old_raw_sessions, new_raw_sessions
            )

            messages = (
                [
                    (
                        "session_changed",
                        {
                            "old": None,
                            "new": session,
                        },
                    )
                    for session in added
                ]
                + [
                    (
                        "session_changed",
                        {
                            "old": session,
                            "new": None,
                        },
                    )
                    for session in removed
                ]
                + [
                    (
                        "session_changed",
                        {
                            "old": old,
                            "new": new,
                        },
                    )
                    for old, new in updated
                ]
            )
            await self._call_websocket_listeners_for_list(messages)

        if any(self._session_changed_listeners):
            added, removed, updated = self._get_changed_sessions(
                old_sessions, new_sessions
            )
            await self._call_session_changed_listeners(added, removed, updated)

    async def _handle_activity_log_message(self):
        params = {}
        if self._last_activity_log_entry is not None:
            params[Query.MIN_DATE] = self._last_activity_log_entry
        else:
            params[Query.LIMIT] = 1
        drop_first_entry = self._last_activity_log_entry is not None
        response = await self._async_get_activity_log_entries(params)
        if entries := response.get(Response.ITEMS):
            new_last = max(
                (entry.get(Item.DATE, "") for entry in entries),
                default=self._last_activity_log_entry or "",
            )
            if new_last != "":
                self._last_activity_log_entry = new_last

            messages = [
                ("activity_log_entry", entry | {"server_id": self.server_id})
                for entry in sorted(entries, key=lambda x: x.get(Item.DATE, 0))
            ]

            if drop_first_entry and len(messages) > 0:
                messages = messages[1:]
            if any(messages):
                await self._call_websocket_listeners_for_list(messages)

    async def _handle_library_changed_message(
        self, data: dict[str, Any], force_updates: bool = False
    ) -> None:
        old_data = self._library_infos.copy()
        new_data = self._library_infos.copy()
        listeners = self._library_listeners.copy()

        collection_folders = data.get(Item.COLLECTION_FOLDERS, [])
        keys = [
            key
            for key, listeners in listeners.items()
            if listeners is not None
            and any(listeners)
            and (key[0] in collection_folders or key[0] == KEY_ALL)
        ]

        for key in keys:
            library_id, user_id, item_type = key
            params = LATEST_QUERY_PARAMS | {Query.INCLUDE_ITEM_TYPES: item_type}
            if library_id != KEY_ALL:
                params |= {Item.PARENT_ID: library_id}
            new_data[key] = (
                await self.async_get_user_items(user_id, params)
                if user_id != KEY_ALL
                else await self.async_get_items(params)
            )

        self._library_infos = new_data

        updated_keys = (
            [key for key in keys if new_data[key] != old_data.get(key)]
            if not force_updates
            else keys
        )

        for key in updated_keys:
            for listener in listeners[key]:
                try:
                    await listener(new_data[key])
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error while handling library listener %s: %s",
                        listener,
                        err,
                    )

    async def _handle_message(self, message: str):
        msg = json.loads(message)

        if msg_type := msg.get("MessageType"):
            call_listeners = self.send_other_events
            data = msg.get("Data")
            match msg_type:
                case WebsocketMessage.SESSIONS:
                    sessions = deepcopy(data)
                    asyncio.ensure_future(self._handle_sessions_message(sessions))
                    call_listeners = False
                case WebsocketMessage.KEEP_ALIVE:
                    _LOGGER.debug(
                        "KeepAlive response received from %s", self.server_url
                    )
                    call_listeners = False
                case WebsocketMessage.FORCE_KEEP_ALIVE:
                    _LOGGER.debug(
                        "ForceKeepAlive response received from %s", self.server_url
                    )
                    self._keep_alive_timeout = msg.get("Data", KEEP_ALIVE_TIMEOUT) / 2
                    call_listeners = False
                case WebsocketMessage.LIBRARY_CHANGED:
                    if any(self._library_listeners):
                        asyncio.ensure_future(
                            self._handle_library_changed_message(data)
                        )
                    data = get_library_changed_event_data(data)
                case WebsocketMessage.ACTIVITY_LOG_ENTRY:
                    if self.send_activity_events and any(self._websocket_listeners):
                        asyncio.ensure_future(self._handle_activity_log_message())
                    call_listeners = False
                case WebsocketMessage.SCHEDULED_TASK_INFO:
                    call_listeners = self.send_task_events
                case WebsocketMessage.USER_DATA_CHANGED:
                    data = get_user_data_changed_event_data(data)

            if call_listeners and any(self._websocket_listeners):
                data = {
                    "server_id": self.server_id,
                    snake_case(msg_type): (data or {}),
                }
                asyncio.ensure_future(
                    self._call_websocket_listeners(snake_case(msg_type), data)
                )
        if self._keep_alive_timeout is not None:
            elapsed = datetime.utcnow() - self._last_keep_alive
            if elapsed.total_seconds() >= self._keep_alive_timeout:
                self._send_keep_alive()

    def force_library_change(self, library_id: str):
        """Force a library update"""
        asyncio.ensure_future(
            self._handle_library_changed_message(
                {"CollectionFolders": [library_id]}, force_updates=True
            )
        )

    def _preprocess_sessions(
        self, sessions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            session
            for session in sessions
            if session.get(Item.DEVICE_ID) != self.device_id
            and session.get(Item.CLIENT) != self.client_name
            and (
                not self.ignore_web_players
                or (
                    self.ignore_web_players
                    and not session.get(Item.CLIENT) in WEB_PLAYERS
                )
            )
            and (
                not self.ignore_dlna_players
                or (
                    self.ignore_dlna_players
                    and not session.get(Item.CLIENT) in DLNA_PLAYERS
                )
            )
            and (
                not self.ignore_mobile_players
                or (
                    self.ignore_mobile_players
                    and not session.get(Item.CLIENT) in MOBILE_PLAYERS
                )
            )
            and (
                not self.ignore_app_players
                or (
                    self.ignore_app_players
                    and not session.get(Item.CLIENT) in APP_PLAYERS
                )
            )
        ]

    def _send_keep_alive(self) -> None:
        if not self._abort and self._ws is not None:
            _LOGGER.debug("Sending keep alive message")
            asyncio.ensure_future(self._ws.send_str('{"MessageType":"KeepAlive"}'))
            self._last_keep_alive = datetime.utcnow()
            self._keep_alive_timeout = None


class ClientMismatchError(aiohttp.ClientError):
    """Server unique id mismatch"""
