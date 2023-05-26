"""The Media Browser (Emby/Jellyfin) integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CACHE_SERVER_API_KEY,
    CONF_CACHE_SERVER_ID,
    CONF_CACHE_SERVER_NAME,
    CONF_CACHE_SERVER_PING,
    CONF_CACHE_SERVER_USER_ID,
    CONF_CACHE_SERVER_VERSION,
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_USER,
    CONF_SENSORS,
    DATA_HUB,
    DATA_POLL_COORDINATOR,
    DOMAIN,
)
from .hub import MediaBrowserHub, ServerOptions

_LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.MEDIA_PLAYER, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Media Browser (Emby/Jellyfin) from a config entry."""

    hub = MediaBrowserHub(ServerOptions(entry.options))

    try:
        await hub.async_start(True)
    except aiohttp.ClientConnectionError as err:
        raise ConfigEntryNotReady from err
    except aiohttp.ClientResponseError as err:
        if err.status == 401:
            raise ConfigEntryAuthFailed from err
        raise ConfigEntryNotReady from err
    except (asyncio.TimeoutError, TimeoutError) as err:
        raise ConfigEntryNotReady from err

    new_options = {
        CONF_CACHE_SERVER_NAME: hub.server_name,
        CONF_CACHE_SERVER_ID: hub.server_id,
        CONF_CACHE_SERVER_PING: hub.server_ping,
        CONF_CACHE_SERVER_VERSION: hub.server_version,
        CONF_CACHE_SERVER_API_KEY: hub.api_key,
        CONF_CACHE_SERVER_USER_ID: hub.user_id,
    }

    hass.config_entries.async_update_entry(entry, options=entry.options | new_options)

    _LOGGER.debug(entry.options | new_options)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)
    hass.data[DOMAIN][entry.entry_id][DATA_HUB] = hub

    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        hub: MediaBrowserHub = data[DATA_HUB]
        await hub.async_stop()

    return unload_ok


async def async_options_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
