"""The Media Browser (Emby/Jellyfin) integration."""
from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.entity_registry as entity_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CACHE_SERVER_ADMIN_ID,
    CONF_CACHE_SERVER_ID,
    CONF_CACHE_SERVER_NAME,
    CONF_CACHE_SERVER_OS,
    CONF_CACHE_SERVER_PING,
    CONF_CACHE_SERVER_VERSION,
    CONF_SCAN_INTERVAL,
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_USER,
    CONF_SENSORS,
    DATA_HUB,
    DATA_POLL_COORDINATOR,
    DATA_PUSH_COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import MediaBrowserPollCoordinator, MediaBrowserPushCoordinator
from .errors import UnauthorizedError
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.MEDIA_PLAYER, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Media Browser (Emby/Jellyfin) from a config entry."""

    hub = MediaBrowserHub(entry.data, entry.options)

    try:
        await hub.async_connect()
    except UnauthorizedError as err:
        _LOGGER.error("Cannot authenticate to %s: %s", entry.data[CONF_HOST], err)
        return False
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Cannot connect to %s: %s", entry.data[CONF_HOST], err)
        return False

    new_options = {
        CONF_CACHE_SERVER_NAME: hub.server_name,
        CONF_CACHE_SERVER_ID: hub.server_id,
        CONF_CACHE_SERVER_PING: hub.server_ping,
        CONF_CACHE_SERVER_VERSION: hub.server_version,
        CONF_CACHE_SERVER_ADMIN_ID: hub.server_admin_id,
        CONF_CACHE_SERVER_OS: hub.server_os,
    }

    hass.config_entries.async_update_entry(entry, options=entry.options | new_options)

    poll_coordinator = MediaBrowserPollCoordinator(
        hass, hub, entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    push_coordinator = MediaBrowserPushCoordinator(hass, hub)

    sensors = entry.options.get(CONF_SENSORS, [])
    for sensor in sensors:
        user_id = sensor[CONF_SENSOR_USER]
        item_type = sensor[CONF_SENSOR_ITEM_TYPE]
        library_id = sensor[CONF_SENSOR_LIBRARY]
        if user_id not in poll_coordinator.library_sensors:
            poll_coordinator.library_sensors[user_id] = {}
        if item_type not in poll_coordinator.library_sensors[user_id]:
            poll_coordinator.library_sensors[user_id][item_type] = set()
        poll_coordinator.library_sensors[user_id][item_type].add(library_id)

    push_coordinator = MediaBrowserPushCoordinator(hass, hub)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)
    hass.data[DOMAIN][entry.entry_id][DATA_HUB] = hub
    hass.data[DOMAIN][entry.entry_id][DATA_POLL_COORDINATOR] = poll_coordinator
    hass.data[DOMAIN][entry.entry_id][DATA_PUSH_COORDINATOR] = push_coordinator

    await poll_coordinator.async_config_entry_first_refresh()
    await push_coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        hub: MediaBrowserHub = data[DATA_HUB]
        await hub.async_disconnect()

    return unload_ok


async def async_options_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
