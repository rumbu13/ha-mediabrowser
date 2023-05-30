"""Media Player for the Media Browser (Emby/Jellyfin) integration."""

import json
import logging
from datetime import datetime
from typing import Any, Callable

import homeassistant.helpers.entity_registry as entreg
import homeassistant.util.dt as utildt
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistant
from .hub import MediaBrowserHub

from .browse_media import async_browse_media_id
from .const import (
    CONF_PURGE_PLAYERS,
    DATA_HUB,
    DOMAIN,
    MANUFACTURER_MAP,
    MEDIA_TYPE_MAP,
    TICKS_PER_SECOND,
    EntityType,
    ImageType,
    Item,
    Manufacturer,
    PlayState,
    Response,
    Session,
)

from .entity import MediaBrowserEntity
from .errors import NotFoundError
from .helpers import extract_player_key, get_image_url, as_float, as_int

VOLUME_RATIO = 100
_LOGGER = logging.getLogger(__package__)


COMMAND_MB_TO_HA: dict[str, int] = {
    "Mute": MediaPlayerEntityFeature.VOLUME_MUTE,
    "Unmute": MediaPlayerEntityFeature.VOLUME_MUTE,
    "ToggleMute": MediaPlayerEntityFeature.VOLUME_MUTE,
    "SetVolume": MediaPlayerEntityFeature.VOLUME_SET,
    "VolumeSet": MediaPlayerEntityFeature.VOLUME_SET,
    "VolumeUp": MediaPlayerEntityFeature.VOLUME_STEP,
    "VolumeDown": MediaPlayerEntityFeature.VOLUME_STEP,
    "SetRepeatMode": MediaPlayerEntityFeature.REPEAT_SET,
}

REPEAT_HA_TO_MB = {
    RepeatMode.OFF: "RepeatNone",
    RepeatMode.ONE: "RepeatOne",
    RepeatMode.ALL: "RepeatAll",
}


REPEAT_MB_TO_HA = {v: k for k, v in REPEAT_HA_TO_MB.items()}

spawned_players: set[str] = set()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sets up media players from a config entry."""

    hub: MediaBrowserHub = hass.data[DOMAIN][entry.entry_id][DATA_HUB]

    async def session_changed(
        old_session: dict[str, Any] | None, new_session: dict[str, Any] | None
    ):
        if old_session is None and new_session is not None:
            if new_session[Session.ID] not in spawned_players:
                async_add_entities([MediaBrowserPlayer(hub, new_session)])

        if (
            new_session is None
            and old_session is not None
            and CONF_PURGE_PLAYERS in entry.options
        ):
            entity_registry = entreg.async_get(hass)
            if player_entity := next(
                (
                    entity
                    for entity in entreg.async_entries_for_config_entry(
                        entity_registry, entry.entry_id
                    )
                    if entity.unique_id.endswith(f"-{EntityType.PLAYER}")
                    and extract_player_key(entity.unique_id) == old_session[Session.ID]
                ),
                None,
            ):
                _LOGGER.debug("Purging media player %s", player_entity.entity_id)
                spawned_players.discard(extract_player_key(player_entity.unique_id))
                entity_registry.async_remove(player_entity.entity_id)

    sessions = await hub.async_get_last_sessions()
    async_add_entities([MediaBrowserPlayer(hub, session) for session in sessions])
    for session in sessions:
        spawned_players.add(session[Session.ID])

    entry.async_on_unload(hub.on_session_changed(session_changed))


class MediaBrowserPlayer(MediaBrowserEntity, MediaPlayerEntity):
    """Represents a media player entity."""

    def __init__(self, hub: MediaBrowserHub, session: dict[str, Any]) -> None:
        super().__init__(hub)
        self._session_key: str = session[Session.ID]
        self._device_name: str | None = session.get(Session.DEVICE_NAME)
        self._device_version = session.get(Session.APPLICATION_VERSION)
        self._device_model: str | None = session.get(Session.CLIENT)

        self._session: dict[str, Any] | None = session
        self._last_update: datetime | None = None

        self._availability_unlistener: Callable[[], None] | None = None
        self._session_changed_unlistener: Callable[[], None] | None = None

        self._attr_name = f"{self.hub.name} {self._session[Session.DEVICE_NAME]}"
        self._attr_unique_id = (
            f"{self.hub.server_id}-{self._session_key}-{EntityType.PLAYER}"
        )
        self._attr_media_image_remotely_accessible = False
        self._attr_available = hub.is_available
        self._update_from_data()

    async def async_added_to_hass(self):
        self._availability_unlistener = self.hub.on_availability_changed(
            self._async_availability_changed
        )
        self._session_changed_unlistener = self.hub.on_session_changed(
            self._async_session_changed
        )

    async def async_will_remove_from_hass(self):
        if self._availability_unlistener is not None:
            self._availability_unlistener()
        if self._session_changed_unlistener is not None:
            self._session_changed_unlistener()

        self._availability_unlistener = None
        self._session_changed_unlistener = None

    async def _async_availability_changed(self, availability: bool):
        self._attr_available = availability
        self.async_write_ha_state()

    async def _async_session_changed(
        self, old_session: dict[str, Any] | None, new_session: dict[str, Any] | None
    ):
        if (
            old_session is not None and old_session[Session.ID] == self._session_key
        ) or (new_session is not None and new_session[Session.ID] == self._session_key):
            self._session = new_session
            if new_session is not None:
                self._last_update = utildt.utcnow()
                self._device_name = new_session.get(Session.DEVICE_NAME)
                self._device_version = new_session.get(Session.APPLICATION_VERSION)
                self._device_model = new_session.get(Session.CLIENT)
            self._update_from_data()
            self.async_write_ha_state()

    def _update_init(self) -> None:
        self._attr_extra_state_attributes = {}
        self._attr_media_album_artist = None
        self._attr_media_album_name = None
        self._attr_media_artist = None
        self._attr_media_channel = None
        self._attr_media_content_id = None
        self._attr_media_content_type = None
        self._attr_media_duration = None
        self._attr_media_episode = None
        self._attr_media_position = None
        self._attr_media_season = None
        self._attr_media_series_title = None
        self._attr_media_title = None
        self._attr_media_image_url = None
        self._attr_media_position_updated_at = None
        self._attr_app_id = None
        self._attr_app_name = None
        self._attr_repeat = None
        self._attr_is_volume_muted = None
        self._attr_volume_level = None
        self._attr_supported_features = MediaPlayerEntityFeature(0)
        self._attr_state = MediaPlayerState.OFF

    def _update_from_state(self, play_state: dict[str, Any]) -> None:
        self._attr_repeat = REPEAT_MB_TO_HA.get(
            play_state.get(PlayState.REPEAT_MODE, "")
        )
        self._attr_is_volume_muted = play_state.get(PlayState.IS_MUTED)
        if ticks := as_int(play_state, PlayState.POSITION_TICKS):
            self._attr_media_position = ticks // TICKS_PER_SECOND

        if level := as_float(play_state, PlayState.VOLUME_LEVEL):
            self._attr_volume_level = level / VOLUME_RATIO

    def _update_from_item(self, item: dict[str, Any]) -> None:
        self._attr_media_album_artist = item.get(Item.ALBUM_ARTIST)
        self._attr_media_album_name = item.get(Item.ALBUM)
        if artists := item.get(Item.ARTISTS):
            self._attr_media_artist = next(iter(artists), None)
        self._attr_media_channel = item.get(Item.CHANNEL_NAME)
        self._attr_media_content_id = item.get(Item.ID)
        if content_type := item.get(Item.TYPE):
            self._attr_media_content_type = MEDIA_TYPE_MAP.get(
                content_type, content_type
            )
        if ticks := as_int(item, Item.RUNTIME_TICKS):
            self._attr_media_duration = ticks // TICKS_PER_SECOND
        self._attr_media_episode = item.get(Item.EPISODE_TITLE)
        self._attr_media_season = item.get(Item.SEASON_NAME)
        self._attr_media_series_title = item.get(Item.SERIES_NAME)
        self._attr_media_title = item.get(Item.NAME)
        self._attr_media_image_url = get_image_url(
            item, self.hub.server_url, ImageType.BACKDROP, True
        )

    def _update_from_session(self, session: dict[str, Any]) -> None:
        self._attr_state = MediaPlayerState.OFF
        remote_control: bool = (
            Session.SUPPORTS_REMOTE_CONTROL in session
            and session[Session.SUPPORTS_REMOTE_CONTROL]
        )
        self._attr_media_position_updated_at = self._last_update
        self._attr_app_id = session.get(Session.ID)
        self._attr_app_name = session.get(Session.CLIENT)
        if remote_control:
            self._attr_state = MediaPlayerState.IDLE
            self._attr_supported_features |= (
                MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.STOP
            )
            if commands := session.get(Session.SUPPORTED_COMMANDS):
                for command in commands:
                    self._attr_supported_features |= COMMAND_MB_TO_HA.get(command, 0)
            play_index = session.get(Session.PLAYLIST_INDEX, 0)
            play_length = session.get(Session.PLAYLIST_LENGTH, 0)
            if play_index > 0:
                self._attr_supported_features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
            if play_index < play_length - 1:
                self._attr_supported_features |= MediaPlayerEntityFeature.NEXT_TRACK
        if item := session.get(Session.NOW_PLAYING_ITEM):
            self._update_from_item(item)
            self._attr_state = MediaPlayerState.PLAYING
        if play := session.get(Session.PLAY_STATE):
            self._update_from_state(play)
            if remote_control:
                self._attr_supported_features |= MediaPlayerEntityFeature.PLAY
                if PlayState.CAN_SEEK in play and play[PlayState.CAN_SEEK]:
                    self._attr_supported_features |= MediaPlayerEntityFeature.SEEK
            if (
                PlayState.IS_PAUSED in play
                and play[PlayState.IS_PAUSED]
                and self._attr_state == MediaPlayerState.PLAYING
            ):
                self._attr_state = MediaPlayerState.PAUSED

    def _update_from_data(self) -> None:
        self._update_init()
        if self._session is not None:
            self._update_from_session(self._session)

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, self._session_key or "")},
            manufacturer=MANUFACTURER_MAP.get(
                self.hub.server_type, Manufacturer.UNKNOWN
            ),
            name=self._device_name,
            sw_version=self._device_version,
            model=self._device_model,
            via_device=(DOMAIN, self.hub.server_id or ""),
        )

    async def async_media_seek(self, position: float) -> None:
        if self._session is not None:
            await self.hub.async_play_command(
                self._session_key,
                "Seek",
                {"SeekPositionTicks": int(position * TICKS_PER_SECOND)},
            )

    async def async_media_next_track(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session_key, "NextTrack")

    async def async_media_previous_track(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session_key, "PreviousTrack")

    async def async_media_pause(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session_key, "Pause")

    async def async_media_play_pause(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session_key, "PlayPause")

    async def async_media_stop(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session_key, "Stop")

    async def async_media_play(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session_key, "Unpause")

    async def async_mute_volume(self, mute: bool) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session_key, "Mute" if mute else "Unmute"
            )

    async def async_volume_up(self) -> None:
        if self._session is not None:
            await self.hub.async_command(self._session_key, "VolumeUp")

    async def async_volume_down(self) -> None:
        if self._session is not None:
            await self.hub.async_command(self._session_key, "VolumeDown")

    async def async_set_volume_level(self, volume: float) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session_key,
                "SetVolume",
                data={"Volume": int(volume * VOLUME_RATIO)},
            )

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session_key,
                "SetRepeatMode",
                data={PlayState.REPEAT_MODE: REPEAT_HA_TO_MB[repeat]},
            )

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia | None:
        if self._session is not None:
            return await async_browse_media_id(
                self.hub,
                media_content_id,
                self._session.get(Session.PLAYABLE_MEDIA_TYPES),
                True,
            )
        return None

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        if self._session is not None:
            if media_id.startswith("{"):
                media_id = await self._async_play_media_json(media_id)

            params = {"PlayCommand": "PlayNow", "ItemIds": media_id}

            await self.hub.async_play(self._session_key, params)

    async def _async_play_media_json(self, media_id: str) -> str:
        params = json.loads(media_id)
        params["Limit"] = 1
        try:
            items = (await self.hub.async_get_items(params))[Response.ITEMS][0]
        except (KeyError, IndexError) as err:
            raise NotFoundError(
                "Cannot find any item with the specified parameters"
            ) from err
        return items[0]["Id"]
