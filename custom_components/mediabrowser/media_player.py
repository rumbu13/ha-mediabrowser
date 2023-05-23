"""Media Player for the Media Browser (Emby/Jellyfin) integration."""

import json
import logging
from datetime import datetime
from typing import Any

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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .browse_media import async_browse_media_id
from .const import (
    CONF_PURGE_PLAYERS,
    DATA_PUSH_COORDINATOR,
    DOMAIN,
    MEDIA_TYPE_MAP,
    TICKS_PER_SECOND,
    ImageType,
    Key,
)
from .coordinator import MediaBrowserPushCoordinator, get_session_key
from .entity import MediaBrowserPushEntity
from .errors import NotFoundError
from .helpers import extract_player_key, get_image_url, is_float, is_int

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sets up media players from a config entry."""

    coordinator: MediaBrowserPushCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_PUSH_COORDINATOR
    ]

    @callback
    def coordinator_update() -> None:
        new_sessions: set[str] = {
            get_session_key(session)
            for session in coordinator.data.sessions.values()
            if get_session_key(session) not in coordinator.players
        }

        if entry.options.get(CONF_PURGE_PLAYERS):
            entity_registry = entreg.async_get(hass)
            players = [
                player
                for player in entreg.async_entries_for_config_entry(
                    entity_registry, entry.entry_id
                )
                if player.unique_id.endswith("-player")
                and extract_player_key(player.unique_id) not in coordinator.players
            ]
            for player in players:
                _LOGGER.debug("Purging %s", player.entity_id)
                entity_registry.async_remove(player.entity_id)

        new_entities = [
            MediaBrowserPlayer(coordinator.data.sessions[session_key], coordinator)
            for session_key in new_sessions
        ]

        coordinator.players |= new_sessions
        async_add_entities(new_entities)

    coordinator_update()
    entry.async_on_unload(coordinator.async_add_listener(coordinator_update))


class MediaBrowserPlayer(MediaBrowserPushEntity, MediaPlayerEntity):
    """Represents a media player entity."""

    def __init__(
        self,
        session: dict[str, Any],
        coordinator: MediaBrowserPushCoordinator,
        context: Any = None,
    ) -> None:
        super().__init__(coordinator, context)
        self._coordinator = coordinator
        self._session_key: str = get_session_key(session)
        self._session: dict[str, Any] | None = session
        self._last_update: datetime | None = None
        self._attr_name = f"{self.hub.name} {self._session[Key.DEVICE_NAME]}"
        self._attr_unique_id = f"{self.hub.server_id}-{self._session_key}-player"
        self._attr_media_image_remotely_accessible = False
        self._update_from_data()

    def _handle_coordinator_update(self) -> None:
        session = self._coordinator.data.sessions.get(self._session_key)
        if self._session is None or session is None or session != self._session:
            self._last_update = utildt.utcnow()
            self._session = session
            self._update_from_data()
            super()._handle_coordinator_update()
        if session is None:
            self._coordinator.players.remove(self._session_key)

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
        self._attr_state = None

    def _update_from_state(self, play_state: dict[str, Any]) -> None:
        self._attr_repeat = REPEAT_MB_TO_HA.get(play_state.get(Key.REPEAT_MODE, ""))
        self._attr_is_volume_muted = play_state.get(Key.IS_MUTED)
        if ticks := play_state.get(Key.POSITION_TICKS):
            ticks = int(ticks) if is_int(ticks, logging.WARNING) else None
            self._attr_media_position = (
                ticks // TICKS_PER_SECOND if ticks is not None else None
            )
        if level := play_state.get(Key.VOLUME_LEVEL):
            level = float(level) if is_float(level, logging.WARNING) else None
            self._attr_volume_level = (
                level / VOLUME_RATIO if level is not None else None
            )

    def _update_from_item(self, item: dict[str, Any]) -> None:
        self._attr_media_album_artist = item.get(Key.ALBUM_ARTIST)
        self._attr_media_album_name = item.get(Key.ALBUM)
        if artists := item.get(Key.ARTISTS):
            self._attr_media_artist = next(iter(artists), None)
        self._attr_media_channel = item.get(Key.CHANNEL_NAME)
        self._attr_media_content_id = item.get(Key.ID)
        if content_type := item.get(Key.TYPE):
            self._attr_media_content_type = MEDIA_TYPE_MAP.get(
                content_type, content_type
            )
        if ticks := item.get(Key.RUNTIME_TICKS):
            ticks = int(ticks) if is_int(ticks, logging.WARNING) else None
            self._attr_media_duration = (
                ticks // TICKS_PER_SECOND if ticks is not None else None
            )
        self._attr_media_episode = item.get(Key.EPISODE_TITLE)
        self._attr_media_season = item.get(Key.SEASON_NAME)
        self._attr_media_series_title = item.get(Key.SERIES_NAME)
        self._attr_media_title = item.get(Key.NAME)
        self._attr_media_image_url = get_image_url(
            item, self.hub.server_url, ImageType.BACKDROP, True
        )

    def _update_from_session(self, session: dict[str, Any]) -> None:
        self._attr_state = MediaPlayerState.OFF
        remote_control: bool = (
            Key.SUPPORTS_REMOTE_CONTROL in session
            and session[Key.SUPPORTS_REMOTE_CONTROL]
        )
        self._attr_media_position_updated_at = self._last_update
        self._attr_app_id = session.get(Key.ID)
        self._attr_app_name = session.get(Key.CLIENT)
        if remote_control:
            self._attr_state = MediaPlayerState.IDLE
            self._attr_supported_features |= (
                MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.STOP
            )
            if commands := session.get(Key.SUPPORTED_COMMANDS):
                for command in commands:
                    self._attr_supported_features |= COMMAND_MB_TO_HA.get(command, 0)
            play_index = session.get(Key.PLAYLIST_INDEX, 0)
            play_length = session.get(Key.PLAYLIST_LENGTH, 0)
            if play_index > 0:
                self._attr_supported_features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
            if play_index < play_length - 1:
                self._attr_supported_features |= MediaPlayerEntityFeature.NEXT_TRACK
        if item := session.get(Key.NOW_PLAYING_ITEM):
            self._update_from_item(item)
            self._attr_state = MediaPlayerState.PLAYING
        if play := session.get(Key.PLAY_STATE):
            self._update_from_state(play)
            if remote_control:
                self._attr_supported_features |= MediaPlayerEntityFeature.PLAY
                if Key.CAN_SEEK in play and play[Key.CAN_SEEK]:
                    self._attr_supported_features |= MediaPlayerEntityFeature.SEEK
            if (
                Key.IS_PAUSED in play
                and play[Key.IS_PAUSED]
                and self._attr_state == MediaPlayerState.PLAYING
            ):
                self._attr_state = MediaPlayerState.PAUSED

    def _update_from_data(self) -> None:
        self._update_init()
        if self._session is not None:
            self._update_from_session(self._session)

    async def async_media_seek(self, position: float) -> None:
        if self._session is not None:
            await self.hub.async_play_command(
                self._session[Key.ID],
                "Seek",
                {"SeekPositionTicks": int(position * TICKS_PER_SECOND)},
            )

    async def async_media_next_track(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session[Key.ID], "NextTrack")

    async def async_media_previous_track(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session[Key.ID], "PreviousTrack")

    async def async_media_pause(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session[Key.ID], "Pause")

    async def async_media_play_pause(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session[Key.ID], "PlayPause")

    async def async_media_stop(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session[Key.ID], "Stop")

    async def async_media_play(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session[Key.ID], "Unpause")

    async def async_mute_volume(self, mute: bool) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session[Key.ID], "Mute" if mute else "Unmute"
            )

    async def async_volume_up(self) -> None:
        if self._session is not None:
            await self.hub.async_command(self._session[Key.ID], "VolumeUp")

    async def async_volume_down(self) -> None:
        if self._session is not None:
            await self.hub.async_command(self._session[Key.ID], "VolumeDown")

    async def async_set_volume_level(self, volume: float) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session[Key.ID],
                "SetVolume",
                data={"Volume": int(volume * VOLUME_RATIO)},
            )

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session[Key.ID],
                "SetRepeatMode",
                data={Key.REPEAT_MODE: REPEAT_HA_TO_MB[repeat]},
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
                self._session.get(Key.PLAYABLE_MEDIA_TYPES),
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

            await self.hub.async_play(self._session[Key.ID], params)

    async def _async_play_media_json(self, media_id: str) -> str:
        params = json.loads(media_id)
        params["Limit"] = 1
        try:
            items = (await self.hub.async_get_items_raw(params))[Key.ITEMS][0]
        except (KeyError, IndexError) as err:
            raise NotFoundError(
                "Cannot find any item with the specified parameters"
            ) from err
        return items[0]["Id"]

    @property
    def available(self) -> bool:
        return (
            self._session is not None
            and get_session_key(self._session) in self._coordinator.data.sessions
            and self.coordinator.last_update_success
        )
