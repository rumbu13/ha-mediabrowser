"""Config and Options flows for Media Browser (Emby/Jellyfin) integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_NAME, CONF_PORT, CONF_SSL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_CLIENT_NAME,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_VERSION,
    CONF_IGNORE_DLNA_PLAYERS,
    CONF_IGNORE_MOBILE_PLAYERS,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_LATEST_MOVIES,
    CONF_LATEST_MUSIC_VIDEOS,
    CONF_LATEST_PHOTOS,
    CONF_LATEST_SERIES,
    CONF_LATEST_SONGS,
    CONF_LATEST_TRAILERS,
    CONF_LATEST_VIDEOS,
    CONF_SERVER,
    CONF_USER,
    DEFAULT_SERVER_NAME,
    DOMAIN,
    HUB,
)
from .discovery import discover_mb
from .errors import ConnectError, ForbiddenError, RequestError, UnauthorizedError
from .hub import MediaBrowserHub
from .models import MBDiscovery

_LOGGER = logging.getLogger(__name__)


class MediaBrowserConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for Media Browser (Emby/Jellyfin)."""

    VERSION = 1

    def __init__(self) -> None:
        self.available_servers: dict[str, MBDiscovery] | None = None
        self.host: str | None = None
        self.port: int | None = None
        self.use_ssl: bool = False
        self.name: str | None = None
        self.discovered_server_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial discovery step."""

        self.available_servers = {server.id: server for server in discover_mb()}
        for entry in self._async_current_entries(include_ignore=True):
            if entry.unique_id is not None:
                self.available_servers.pop(entry.unique_id)

        if self.available_servers is not None:
            if len(self.available_servers) == 0:
                return await self.async_step_manual()
            if len(self.available_servers) == 1:
                self.discovered_server_id = next(iter(self.available_servers))
                return await self.async_step_manual()

        return await self.async_step_select()

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle multiple servers discovered step."""
        if user_input is not None:
            self.discovered_server_id = user_input[CONF_SERVER]
            return await self.async_step_manual()

        server_list = (
            {
                server.id: f'{server.name or "Unknown"} ({server.address})'
                for server in self.available_servers.values()
            }
            if self.available_servers is not None
            else {}
        )

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({vol.Required(CONF_SERVER): vol.In(server_list)}),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            hub = MediaBrowserHub(
                host=user_input[CONF_HOST],
                api_key=user_input[CONF_API_KEY],
                port=user_input[CONF_PORT],
                use_ssl=user_input[CONF_SSL],
                custom_name=user_input[CONF_NAME],
            )
            try:
                await hub.async_connect()
            except (ConnectError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except ForbiddenError:
                errors["base"] = "weak_auth"
            except UnauthorizedError:
                errors["base"] = "invalid_auth"
            except RequestError:
                errors["base"] = "bad_request"
            except (TimeoutError, asyncio.TimeoutError):
                errors["base"] = "timeout"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(hub.server_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, hub.server_name),
                    data=user_input,
                    options={
                        CONF_API_KEY: hub.api_key,
                        CONF_CLIENT_NAME: hub.client_name,
                        CONF_DEVICE_NAME: hub.device_name,
                        CONF_DEVICE_ID: hub.device_id,
                        CONF_DEVICE_VERSION: hub.device_version,
                        CONF_IGNORE_WEB_PLAYERS: True,
                        CONF_IGNORE_DLNA_PLAYERS: False,
                        CONF_IGNORE_MOBILE_PLAYERS: False,
                        CONF_LATEST_MOVIES: True,
                        CONF_LATEST_VIDEOS: True,
                        CONF_LATEST_MUSIC_VIDEOS: True,
                        CONF_LATEST_PHOTOS: True,
                        CONF_LATEST_SERIES: True,
                        CONF_LATEST_TRAILERS: True,
                        CONF_NAME: hub.server_name,
                    },
                )
            finally:
                await hub.async_disconnect()

        previous_input = user_input or {}

        default_host: str | None = None
        default_port: int | None = None
        default_ssl: bool | None = None
        default_name: str = DEFAULT_SERVER_NAME
        if self.discovered_server_id is not None and self.available_servers is not None:
            server = self.available_servers[self.discovered_server_id]
            default_host = server.host
            default_port = server.port or (8920 if server.use_ssl else 8096)
            default_ssl = server.use_ssl
            default_name = server.name or ""

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=previous_input.get(CONF_HOST, default_host)
                ): str,
                vol.Optional(
                    CONF_PORT, default=previous_input.get(CONF_PORT, default_port)
                ): int,
                vol.Optional(
                    CONF_SSL, default=previous_input.get(CONF_SSL, default_ssl)
                ): bool,
                vol.Required(
                    CONF_API_KEY, default=previous_input.get(CONF_API_KEY, "")
                ): str,
                vol.Optional(
                    CONF_NAME, default=previous_input.get(CONF_NAME, default_name)
                ): str,
            }
        )

        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return MediaBrowserOptionsFlow(config_entry)


class MediaBrowserOptionsFlow(OptionsFlow):
    """Handle an option flow for Media Browser (Emby/Jellyfin)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None  # pylint: disable=W0613
    ) -> FlowResult:
        """Handle the initial step."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["auth", "players", "latest", "advanced"],
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the authentication step."""
        errors: dict[str, str] = {}
        hub: MediaBrowserHub = self.hass.data[DOMAIN][self.config_entry.entry_id][HUB]

        if user_input:
            try:
                await hub.async_test_api_key(user_input[CONF_API_KEY])
            except (ConnectError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except ForbiddenError:
                errors["base"] = "weak_auth"
            except UnauthorizedError:
                errors["base"] = "invalid_auth"
            except (TimeoutError, asyncio.TimeoutError):
                errors["base"] = "timeout"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="", data=self.config_entry.options | user_input
                )

        users = await hub.async_get_users()

        user_list = {
            user.id: user.name
            + " ("
            + (
                "admin"
                if user.policy is not None and user.policy.is_administrator
                else "normal"
            )
            + ")"
            for user in users
            if user.name is not None
        }

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=self.config_entry.options.get(CONF_API_KEY, ""),
                    ): str,
                    vol.Optional(
                        CONF_USER,
                        default=self.config_entry.options.get(CONF_USER, hub.user_id),
                    ): vol.In(user_list),
                }
            ),
            errors=errors,
        )

    async def async_step_players(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the media players step."""
        if user_input:
            return self.async_create_entry(
                title="", data=self.config_entry.options | user_input
            )
        return self.async_show_form(
            step_id="players",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IGNORE_WEB_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_WEB_PLAYERS, False
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_DLNA_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_DLNA_PLAYERS, False
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_MOBILE_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_MOBILE_PLAYERS, False
                        ),
                    ): bool,
                }
            ),
        )

    async def async_step_latest(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the media latest step."""
        if user_input:
            return self.async_create_entry(
                title="", data=self.config_entry.options | user_input
            )
        return self.async_show_form(
            step_id="latest",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LATEST_MOVIES,
                        default=self.config_entry.options.get(CONF_LATEST_MOVIES, True),
                    ): bool,
                    vol.Required(
                        CONF_LATEST_SERIES,
                        default=self.config_entry.options.get(CONF_LATEST_SERIES, True),
                    ): bool,
                    vol.Required(
                        CONF_LATEST_SONGS,
                        default=self.config_entry.options.get(CONF_LATEST_SONGS, True),
                    ): bool,
                    vol.Required(
                        CONF_LATEST_MUSIC_VIDEOS,
                        default=self.config_entry.options.get(
                            CONF_LATEST_MUSIC_VIDEOS, True
                        ),
                    ): bool,
                    vol.Required(
                        CONF_LATEST_PHOTOS,
                        default=self.config_entry.options.get(CONF_LATEST_PHOTOS, True),
                    ): bool,
                    vol.Required(
                        CONF_LATEST_VIDEOS,
                        default=self.config_entry.options.get(CONF_LATEST_VIDEOS, True),
                    ): bool,
                    vol.Required(
                        CONF_LATEST_TRAILERS,
                        default=self.config_entry.options.get(
                            CONF_LATEST_TRAILERS, True
                        ),
                    ): bool,
                }
            ),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input:
            return self.async_create_entry(
                title="", data=self.config_entry.options | user_input
            )

        hub: MediaBrowserHub = self.hass.data[DOMAIN][self.config_entry.entry_id][HUB]

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=self.config_entry.options.get(
                            CONF_NAME, hub.server_name
                        ),
                    ): str,
                    vol.Required(
                        CONF_CLIENT_NAME,
                        default=self.config_entry.options.get(
                            CONF_CLIENT_NAME, hub.client_name
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_NAME,
                        default=self.config_entry.options.get(
                            CONF_DEVICE_NAME, hub.device_name
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_ID,
                        default=self.config_entry.options.get(
                            CONF_DEVICE_ID, hub.device_id
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_VERSION,
                        default=self.config_entry.options.get(
                            CONF_DEVICE_VERSION, hub.device_version
                        ),
                    ): str,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
