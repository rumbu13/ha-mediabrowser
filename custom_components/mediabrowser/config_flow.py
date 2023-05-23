"""Config and Options flows for Media Browser (Emby/Jellyfin) integration."""
from __future__ import annotations

import asyncio
import logging
import urllib.parse
from copy import deepcopy
from types import MappingProxyType
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_NAME, CONF_PORT, CONF_SSL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)
from voluptuous.schema_builder import UNDEFINED

from .const import (
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
    CONF_PURGE_PLAYERS,
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_REMOVE,
    CONF_SENSOR_USER,
    CONF_SENSORS,
    CONF_SERVER,
    CONF_TIMEOUT,
    CONF_UPCOMING_MEDIA,
    CONF_USER,
    DATA_HUB,
    DEFAULT_IGNORE_APP_PLAYERS,
    DEFAULT_IGNORE_DLNA_PLAYERS,
    DEFAULT_IGNORE_MOBILE_PLAYERS,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_PURGE_PLAYERS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SENSORS,
    DEFAULT_UPCOMING_MEDIA,
    DOMAIN,
    SENSOR_ITEM_TYPES,
    Key,
)
from .discovery import discover_mb
from .errors import ConnectError, ForbiddenError, RequestError, UnauthorizedError
from .helpers import build_sensor_key_from_config, extract_sensor_key
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__name__)


class MediaBrowserConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for Media Browser (Emby/Jellyfin)."""

    VERSION = 1

    def __init__(self) -> None:
        self.available_servers: dict[str, Any] | None = None
        self.host: str | None = None
        self.port: int | None = None
        self.use_ssl: bool = False
        self.name: str | None = None
        self.discovered_server_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial discovery step."""

        self.available_servers = {server[Key.ID]: server for server in discover_mb()}
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
                server[
                    Key.ID
                ]: f'{server[Key.NAME] or "Unknown"} ({server[Key.ADDRESS]})'
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
                config=MappingProxyType(
                    {
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input.get(CONF_PORT),
                        CONF_SSL: user_input.get(CONF_SSL),
                    }
                ),
                options=MappingProxyType(
                    {
                        CONF_API_KEY: user_input.get(CONF_API_KEY),
                        CONF_NAME: user_input.get(CONF_NAME),
                    }
                ),
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
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: hub.port,
                        CONF_SSL: hub.use_ssl,
                    },
                    options={
                        CONF_API_KEY: hub.api_key,
                        CONF_USER: hub.server_admin_id,
                        CONF_CLIENT_NAME: hub.client_name,
                        CONF_DEVICE_NAME: hub.device_name,
                        CONF_DEVICE_ID: hub.device_id,
                        CONF_DEVICE_VERSION: hub.device_version,
                        CONF_IGNORE_WEB_PLAYERS: hub.ignore_web_players,
                        CONF_IGNORE_DLNA_PLAYERS: hub.ignore_dlna_players,
                        CONF_IGNORE_MOBILE_PLAYERS: hub.ignore_mobile_players,
                        CONF_IGNORE_APP_PLAYERS: hub.ignore_app_players,
                        CONF_PURGE_PLAYERS: DEFAULT_PURGE_PLAYERS,
                        CONF_UPCOMING_MEDIA: DEFAULT_UPCOMING_MEDIA,
                        CONF_NAME: hub.server_name,
                        CONF_TIMEOUT: hub.timeout,
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                        CONF_SENSORS: DEFAULT_SENSORS,
                        CONF_CACHE_SERVER_ID: hub.server_id,
                        CONF_CACHE_SERVER_NAME: hub.server_name,
                        CONF_CACHE_SERVER_PING: hub.server_ping,
                        CONF_CACHE_SERVER_OS: hub.server_os,
                        CONF_CACHE_SERVER_VERSION: hub.server_version,
                    },
                )
            finally:
                await hub.async_disconnect()

        previous_input = user_input or {}

        default_host = UNDEFINED
        default_port = UNDEFINED
        default_ssl = UNDEFINED
        default_name = UNDEFINED
        default_api_key = UNDEFINED
        if self.discovered_server_id is not None and self.available_servers is not None:
            server = self.available_servers[self.discovered_server_id]
            parsed = urllib.parse.urlparse(server[Key.ADDRESS])
            default_host = parsed.hostname
            default_port = parsed.port or (8920 if parsed.scheme == "https" else 8096)
            default_ssl = parsed.scheme == "https"
            default_name = server[Key.NAME] or ""

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=previous_input.get(CONF_HOST, default_host),
                ): str,
                vol.Optional(
                    CONF_PORT,
                    default=previous_input.get(CONF_PORT, default_port),
                    description={"suggested_value": default_port},
                ): int,
                vol.Optional(
                    CONF_SSL,
                    default=previous_input.get(CONF_SSL, default_ssl),
                    description={"suggested_value": default_ssl},
                ): bool,
                vol.Required(
                    CONF_API_KEY,
                    default=previous_input.get(CONF_API_KEY, default_api_key),
                ): str,
                vol.Optional(
                    CONF_NAME,
                    description={"suggested_value": default_name},
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
        self.options = deepcopy(dict(config_entry.options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None  # pylint: disable=W0613
    ) -> FlowResult:
        """Handle the initial step."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "auth",
                "players",
                "add_sensor",
                "remove_sensor",
                "advanced",
            ],
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the authentication step."""
        errors: dict[str, str] = {}
        hub: MediaBrowserHub = self.hass.data[DOMAIN][self.config_entry.entry_id][
            DATA_HUB
        ]

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
                self.options |= user_input
                return self.async_create_entry(title="", data=self.options)

        users = await hub.async_get_users_raw()

        user_list = {
            user[Key.ID]: user[Key.NAME]
            + " ("
            + (
                "admin"
                if Key.POLICY in user
                and Key.IS_ADMINISTRATOR in user[Key.POLICY]
                and user[Key.POLICY][Key.IS_ADMINISTRATOR]
                else "normal"
            )
            + ")"
            for user in users
            if Key.NAME in user
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
                        default=self.config_entry.options.get(
                            CONF_USER, hub.server_admin_id
                        ),
                    ): vol.In(user_list),
                }
            ),
            errors=errors,
        )

    async def async_step_players(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the media players step."""
        if user_input:
            self.options |= user_input
            return self.async_create_entry(title="", data=self.options)
        return self.async_show_form(
            step_id="players",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IGNORE_WEB_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_WEB_PLAYERS, DEFAULT_IGNORE_WEB_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_DLNA_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_DLNA_PLAYERS, DEFAULT_IGNORE_DLNA_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_MOBILE_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_MOBILE_PLAYERS, DEFAULT_IGNORE_MOBILE_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_APP_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_APP_PLAYERS, DEFAULT_IGNORE_APP_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_PURGE_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_PURGE_PLAYERS, DEFAULT_PURGE_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_UPCOMING_MEDIA,
                        default=self.config_entry.options.get(
                            CONF_UPCOMING_MEDIA, DEFAULT_UPCOMING_MEDIA
                        ),
                    ): bool,
                }
            ),
        )

    async def async_step_remove_sensor(
        self, user_input: dict[str, Any] | None
    ) -> FlowResult:
        """Handle a step to remove a new latest sensor."""

        sensors = self.options.get(CONF_SENSORS, [])

        entity_registry = async_get(self.hass)
        entries = {
            extract_sensor_key(entry.unique_id): entry
            for entry in async_entries_for_config_entry(
                entity_registry, self.config_entry.entry_id
            )
            if entry.unique_id.endswith("-latest")
        }

        if len(sensors) == 0 and len(entries) == 0:
            return self.async_abort(reason="no_sensors")

        if user_input:
            target = user_input[CONF_SENSOR_REMOVE]
            entry = entries.get(target)
            if entry is not None:
                entity_registry.async_remove(entry.entity_id)

            _LOGGER.debug("Target is %s", target)
            for sensor in sensors:
                _LOGGER.debug("Sensor: %s", build_sensor_key_from_config(sensor))
                if build_sensor_key_from_config(sensor) == target:
                    sensors.remove(sensor)
                    break

            self.options[CONF_SENSORS] = sensors

            _LOGGER.debug(sensors)

            return self.async_create_entry(title="", data=self.options)

        entry_list = {
            key: value.name or value.original_name
            for key, value in sorted(
                entries.items(), key=lambda x: x[1].name or x[1].original_name  # type: ignore
            )
        }

        return self.async_show_form(
            step_id="remove_sensor",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SENSOR_REMOVE,
                        default=next(iter(entry_list)),  # type: ignore
                    ): vol.In(entry_list),
                }
            ),
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None
    ) -> FlowResult:
        """Handle a step to add a new latest sensor."""
        if user_input:
            sensor_key = build_sensor_key_from_config(user_input)

            sensors = self.options.get(CONF_SENSORS, [])

            configs = {
                build_sensor_key_from_config(config): config for config in sensors
            }

            entity_registry = async_get(self.hass)
            entries = {
                extract_sensor_key(entry.unique_id): entry
                for entry in async_entries_for_config_entry(
                    entity_registry, self.config_entry.entry_id
                )
                if entry.unique_id.endswith("-latest")
            }

            if sensor_key in configs or sensor_key in entries:
                return self.async_abort(reason="sensor_already_configured")

            sensors.append(user_input)

            self.options |= {CONF_SENSORS: sensors}

            return self.async_create_entry(title="", data=self.options)

        hub: MediaBrowserHub = self.hass.data[DOMAIN][self.config_entry.entry_id][
            DATA_HUB
        ]

        user_list = {Key.ALL: "(All users)"} | {
            user["Id"]: user["Name"]
            for user in sorted(await hub.async_get_users_raw(), key=lambda x: x["Name"])
        }

        library_list = {Key.ALL: "(All libraries)"} | {
            library[Key.ID]: library[Key.NAME]
            for library in sorted(
                await hub.async_get_libraries_raw(), key=lambda x: x[Key.NAME]
            )
        }

        type_list = {
            key: value["title"]
            for key, value in sorted(
                SENSOR_ITEM_TYPES.items(), key=lambda x: x[1]["title"]
            )
        }

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SENSOR_ITEM_TYPE,
                        default="Movie",  # type: ignore
                    ): vol.In(type_list),
                    vol.Required(
                        CONF_SENSOR_LIBRARY,
                        default=Key.ALL,  # type: ignore
                    ): vol.In(library_list),
                    vol.Required(
                        CONF_SENSOR_USER,
                        default=Key.ALL,  # type: ignore
                    ): vol.In(user_list),
                }
            ),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None
    ) -> FlowResult:
        """Handle the advanced step."""
        if user_input:
            self.options |= user_input
            return self.async_create_entry(title="", data=self.options)

        hub: MediaBrowserHub = self.hass.data[DOMAIN][self.config_entry.entry_id][
            DATA_HUB
        ]

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
                    vol.Required(
                        CONF_TIMEOUT,
                        default=self.config_entry.options.get(
                            CONF_TIMEOUT, hub.timeout
                        ),
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): str,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
