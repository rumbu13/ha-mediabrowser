"""The Media Browser (Emby/Jellyfin) integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CLIENT_NAME,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_VERSION,
    CONF_IGNORE_DLNA_PLAYERS,
    CONF_IGNORE_MOBILE_PLAYERS,
    CONF_IGNORE_WEB_PLAYERS,
    DOMAIN,
    HUB,
    POLL_COORDINATOR,
    PUSH_COORDINATOR,
)
from .coordinator import MediaBrowserPollCoordinator, MediaBrowserPushCoordinator
from .errors import UnauthorizedError
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.MEDIA_PLAYER, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Media Browser (Emby/Jellyfin) from a config entry."""

    hub = MediaBrowserHub(
        host=entry.data[CONF_HOST],
        api_key=entry.options[CONF_API_KEY],
        client_name=entry.options[CONF_CLIENT_NAME],
        device_id=entry.options[CONF_DEVICE_ID],
        device_name=entry.options[CONF_DEVICE_NAME],
        device_version=entry.options[CONF_DEVICE_VERSION],
        port=entry.data[CONF_PORT],
        use_ssl=entry.data[CONF_SSL],
        custom_name=entry.data.get(CONF_NAME),
        ignore_web_players=entry.options.get(CONF_IGNORE_WEB_PLAYERS, False),
        ignore_dlna_players=entry.options.get(CONF_IGNORE_DLNA_PLAYERS, False),
        ignore_mobile_players=entry.options.get(CONF_IGNORE_MOBILE_PLAYERS, False),
    )

    try:
        await hub.async_connect()
    except UnauthorizedError as err:
        _LOGGER.error("Cannot authenticate to %s: %s", entry.data[CONF_HOST], err)
        return False
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Cannot connect to %s: %s", entry.data[CONF_HOST], err)
        return False

    poll_coordinator = MediaBrowserPollCoordinator(hass, hub)
    push_coordinator = MediaBrowserPushCoordinator(hass, hub)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)
    hass.data[DOMAIN][entry.entry_id][HUB] = hub
    hass.data[DOMAIN][entry.entry_id][POLL_COORDINATOR] = poll_coordinator
    hass.data[DOMAIN][entry.entry_id][PUSH_COORDINATOR] = push_coordinator

    await poll_coordinator.async_config_entry_first_refresh()
    await push_coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        hub: MediaBrowserHub = data[HUB]
        await hub.async_disconnect()

    return unload_ok


async def async_options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
