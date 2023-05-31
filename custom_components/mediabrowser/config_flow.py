"""Config and Options flows for Media Browser (Emby/Jellyfin) integration."""
from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)

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
    CONF_EVENTS_ACTIVITY_LOG,
    CONF_EVENTS_OTHER,
    CONF_EVENTS_SESSIONS,
    CONF_EVENTS_TASKS,
    CONF_IGNORE_APP_PLAYERS,
    CONF_IGNORE_DLNA_PLAYERS,
    CONF_IGNORE_MOBILE_PLAYERS,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_PURGE_PLAYERS,
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_REMOVE,
    CONF_SENSOR_USER,
    CONF_SENSORS,
    CONF_SERVER,
    CONF_TIMEOUT,
    CONF_UPCOMING_MEDIA,
    DATA_HUB,
    DEFAULT_IGNORE_APP_PLAYERS,
    DEFAULT_IGNORE_DLNA_PLAYERS,
    DEFAULT_IGNORE_MOBILE_PLAYERS,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_PURGE_PLAYERS,
    DEFAULT_SENSORS,
    DEFAULT_SERVER_NAME,
    DEFAULT_UPCOMING_MEDIA,
    DOMAIN,
    SENSOR_ITEM_TYPES,
    KEY_ALL,
    Discovery,
    EntityType,
    Item,
    Server,
)
from .discovery import discover_mb
from .helpers import build_sensor_key_from_config, extract_sensor_key
from .hub import ClientMismatchError, MediaBrowserHub

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

        self.available_servers = {server[Server.ID]: server for server in discover_mb()}
        for entry in self._async_current_entries(include_ignore=True):
            if entry.unique_id is not None:
                self.available_servers.pop(entry.unique_id, None)

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
                    Discovery.ID
                ]: f'{server[Discovery.NAME] or "Unknown"} ({server[Discovery.ADDRESS]})'
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
            if await _validate_config(user_input, errors):
                await self.async_set_unique_id(user_input[CONF_CACHE_SERVER_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, user_input[CONF_CACHE_SERVER_NAME]),
                    data={},
                    options=user_input
                    | {
                        CONF_PURGE_PLAYERS: DEFAULT_PURGE_PLAYERS,
                        CONF_UPCOMING_MEDIA: DEFAULT_UPCOMING_MEDIA,
                        CONF_SENSORS: DEFAULT_SENSORS,
                    },
                )

        previous_input = user_input or {}

        default_url = None
        default_name = DEFAULT_SERVER_NAME
        default_username = None
        default_password = None
        if self.discovered_server_id is not None and self.available_servers is not None:
            server = self.available_servers[self.discovered_server_id]
            default_url = server[Discovery.ADDRESS]
            default_name = server[Discovery.NAME] or ""

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL,
                    default=previous_input.get(CONF_URL, default_url),
                ): str,
                vol.Required(
                    CONF_USERNAME,
                    default=previous_input.get(CONF_USERNAME, default_username),
                ): str,
                vol.Required(
                    CONF_PASSWORD,
                    default=previous_input.get(CONF_PASSWORD, default_password),
                ): str,
                vol.Optional(
                    CONF_NAME,
                    default=previous_input.get(CONF_NAME, default_name),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reauthorization step."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        assert entry is not None

        if user_input is not None:
            options = deepcopy(dict(entry.options))
            if await _validate_config(
                options,
                errors,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            ):
                return self.async_create_entry(
                    title=options.get(CONF_NAME, options.get(CONF_CACHE_SERVER_NAME)),
                    data={},
                    options=options,
                )
        previous_input = user_input or {}

        default_username = previous_input.get(
            CONF_USERNAME, entry.options.get(CONF_USERNAME)
        )
        default_password = previous_input.get(
            CONF_PASSWORD, entry.options.get(CONF_PASSWORD)
        )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=previous_input.get(CONF_USERNAME, default_username),
                ): str,
                vol.Required(
                    CONF_PASSWORD,
                    default=previous_input.get(CONF_PASSWORD, default_password),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reauth", data_schema=data_schema, errors=errors
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
                "libraries",
                "events",
                "add_sensor",
                "remove_sensor",
                "advanced",
            ],
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the authentication step."""
        errors: dict[str, str] = {}
        if user_input:
            if await _validate_config(
                self.options,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                errors=errors,
            ):
                return self.async_create_entry(
                    title=self.options.get(
                        CONF_NAME, self.options.get(CONF_CACHE_SERVER_NAME)
                    ),
                    data=self.options,
                )

        previous_input = user_input or {}

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=self.options.get(
                            CONF_USERNAME,
                            previous_input.get(
                                CONF_USERNAME, self.options.get(CONF_USERNAME)
                            ),
                        ),
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=self.options.get(
                            CONF_PASSWORD,
                            previous_input.get(
                                CONF_PASSWORD, self.options.get(CONF_PASSWORD)
                            ),
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_libraries(
        self, user_input: dict[str, Any] | None
    ) -> FlowResult:
        """Handle the authentication step."""
        if user_input:
            self.options |= user_input
            return self.async_create_entry(
                title=self.options.get(
                    CONF_NAME, self.options.get(CONF_CACHE_SERVER_NAME)
                ),
                data=self.options,
            )

        return self.async_show_form(
            step_id="libraries",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPCOMING_MEDIA,
                        default=self.options.get(CONF_UPCOMING_MEDIA),  # type: ignore
                    ): bool,
                }
            ),
        )

    async def async_step_events(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the events step."""
        if user_input:
            self.options |= user_input
            return self.async_create_entry(
                title=self.options.get(
                    CONF_NAME, self.options.get(CONF_CACHE_SERVER_NAME)
                ),
                data=self.options,
            )

        return self.async_show_form(
            step_id="events",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_EVENTS_SESSIONS,
                        default=self.options.get(CONF_EVENTS_SESSIONS),  # type: ignore
                    ): bool,
                    vol.Optional(
                        CONF_EVENTS_ACTIVITY_LOG,
                        default=self.options.get(CONF_EVENTS_ACTIVITY_LOG),  # type: ignore
                    ): bool,
                    vol.Optional(
                        CONF_EVENTS_TASKS,
                        default=self.options.get(CONF_EVENTS_TASKS),  # type: ignore
                    ): bool,
                    vol.Optional(
                        CONF_EVENTS_OTHER,
                        default=self.options.get(CONF_EVENTS_OTHER),  # type: ignore
                    ): bool,
                }
            ),
        )

    async def async_step_players(self, user_input: dict[str, Any] | None) -> FlowResult:
        """Handle the media players step."""
        if user_input:
            self.options |= user_input
            return self.async_create_entry(
                title=self.options.get(
                    CONF_NAME, self.options.get(CONF_CACHE_SERVER_NAME)
                ),
                data=self.options,
            )
        return self.async_show_form(
            step_id="players",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_IGNORE_WEB_PLAYERS,
                        default=self.options.get(
                            CONF_IGNORE_WEB_PLAYERS, DEFAULT_IGNORE_WEB_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_DLNA_PLAYERS,
                        default=self.options.get(
                            CONF_IGNORE_DLNA_PLAYERS, DEFAULT_IGNORE_DLNA_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_MOBILE_PLAYERS,
                        default=self.options.get(
                            CONF_IGNORE_MOBILE_PLAYERS, DEFAULT_IGNORE_MOBILE_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_IGNORE_APP_PLAYERS,
                        default=self.options.get(
                            CONF_IGNORE_APP_PLAYERS, DEFAULT_IGNORE_APP_PLAYERS
                        ),
                    ): bool,
                    vol.Required(
                        CONF_PURGE_PLAYERS,
                        default=self.options.get(
                            CONF_PURGE_PLAYERS, DEFAULT_PURGE_PLAYERS
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
            if entry.unique_id.endswith(f"-{EntityType.LIBRARY}")
        }

        if len(sensors) == 0 and len(entries) == 0:
            return self.async_abort(reason="no_sensors")

        if user_input:
            target = user_input[CONF_SENSOR_REMOVE]
            entry = entries.get(target)
            if entry is not None:
                entity_registry.async_remove(entry.entity_id)

            for sensor in sensors:
                if build_sensor_key_from_config(sensor) == target:
                    sensors.remove(sensor)
                    break

            self.options[CONF_SENSORS] = sensors

            return self.async_create_entry(
                title=self.options.get(
                    CONF_NAME, self.options.get(CONF_CACHE_SERVER_NAME)
                ),
                data=self.options,
            )

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
                        default=next(iter(entry_list), None),  # type: ignore
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
                if entry.unique_id.endswith(f"-{EntityType.LIBRARY}")
            }

            if sensor_key in configs or sensor_key in entries:
                return self.async_abort(reason="sensor_already_configured")

            sensors.append(user_input)

            self.options |= {CONF_SENSORS: sensors}

            return self.async_create_entry(title="", data=self.options)

        hub: MediaBrowserHub = self.hass.data[DOMAIN][self.config_entry.entry_id][
            DATA_HUB
        ]

        user_list = {KEY_ALL: "(All users)"} | {
            user["Id"]: user["Name"]
            for user in sorted(await hub.async_get_users(), key=lambda x: x["Name"])
        }

        library_list = {KEY_ALL: "(All libraries)"} | {
            library[Item.ID]: library[Item.NAME]
            for library in sorted(
                await hub.async_get_libraries(), key=lambda x: x[Item.NAME]
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
                        default=KEY_ALL,  # type: ignore
                    ): vol.In(library_list),
                    vol.Required(
                        CONF_SENSOR_USER,
                        default=KEY_ALL,  # type: ignore
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

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=self.config_entry.options.get(
                            CONF_NAME, self.options.get(CONF_NAME)
                        ),
                    ): str,
                    vol.Required(
                        CONF_CLIENT_NAME,
                        default=self.config_entry.options.get(
                            CONF_CLIENT_NAME, self.options.get(CONF_CLIENT_NAME)
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_NAME,
                        default=self.config_entry.options.get(
                            CONF_DEVICE_NAME, self.options.get(CONF_DEVICE_NAME)
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_ID,
                        default=self.config_entry.options.get(
                            CONF_DEVICE_ID, self.options.get(CONF_DEVICE_ID)
                        ),
                    ): str,
                    vol.Required(
                        CONF_DEVICE_VERSION,
                        default=self.config_entry.options.get(
                            CONF_DEVICE_VERSION, self.options.get(CONF_DEVICE_VERSION)
                        ),
                    ): str,
                    vol.Required(
                        CONF_TIMEOUT,
                        default=self.config_entry.options.get(
                            CONF_TIMEOUT, self.options.get(CONF_TIMEOUT)
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                }
            ),
        )


async def _validate_config(
    options: dict[str, Any],
    errors: dict[str, str],
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> bool:
    errors.clear()
    save_url = options.get(CONF_URL)
    save_username = options.get(CONF_USERNAME)
    save_password = options.get(CONF_PASSWORD)
    save_api_key = options.get(CONF_CACHE_SERVER_API_KEY)

    if url is not None:
        options[CONF_URL] = url
    if username is not None:
        options[CONF_USERNAME] = username
        options.pop(CONF_CACHE_SERVER_API_KEY, None)
    if password is not None:
        options[CONF_PASSWORD] = password
        options.pop(CONF_CACHE_SERVER_API_KEY, None)

    hub = MediaBrowserHub(options)
    try:
        await hub.async_start(False)
    except aiohttp.ClientConnectionError:
        errors["base"] = "cannot_connect"
    except aiohttp.ClientResponseError as err:
        match err.status:
            case 401:
                errors["base"] = "invalid_auth"
            case 403:
                errors["base"] = "weak_auth"
            case _:
                errors["base"] = "bad_request"
        _LOGGER.exception("ERROR")
    except (TimeoutError, asyncio.TimeoutError):
        _LOGGER.error("Timeout while connecting to %s", hub.server_url)
        errors["base"] = "timeout"
    except ClientMismatchError:
        errors["base"] = "mismatch"
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.debug("Unexpected error: %s (%s)", type(err), err)
        errors["base"] = "unknown"
    else:
        options[CONF_URL] = url or save_url
        options[CONF_USERNAME] = username or save_username
        options[CONF_PASSWORD] = password or save_password
        options[CONF_CACHE_SERVER_API_KEY] = hub.api_key or save_api_key
        options[CONF_CLIENT_NAME] = hub.client_name
        options[CONF_DEVICE_NAME] = hub.device_name
        options[CONF_DEVICE_ID] = hub.device_id
        options[CONF_DEVICE_VERSION] = hub.device_version
        options[CONF_IGNORE_WEB_PLAYERS] = hub.ignore_web_players
        options[CONF_IGNORE_DLNA_PLAYERS] = hub.ignore_dlna_players
        options[CONF_IGNORE_MOBILE_PLAYERS] = hub.ignore_mobile_players
        options[CONF_IGNORE_APP_PLAYERS] = hub.ignore_app_players
        options[CONF_NAME] = hub.server_name
        options[CONF_TIMEOUT] = hub.timeout
        options[CONF_CACHE_SERVER_ID] = hub.server_id
        options[CONF_CACHE_SERVER_NAME] = hub.server_name
        options[CONF_CACHE_SERVER_PING] = hub.server_ping
        options[CONF_CACHE_SERVER_VERSION] = hub.server_version
        options[CONF_CACHE_SERVER_USER_ID] = hub.user_id
        options[CONF_EVENTS_SESSIONS] = hub.send_session_events
        options[CONF_EVENTS_ACTIVITY_LOG] = hub.send_activity_events
        options[CONF_EVENTS_TASKS] = hub.send_task_events
        options[CONF_EVENTS_OTHER] = hub.send_other_events
        return True
    finally:
        await hub.async_stop()

    return False
