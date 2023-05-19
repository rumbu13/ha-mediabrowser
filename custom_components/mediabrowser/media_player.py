"""Media Player for the Media Browser (Emby/Jellyfin) integration."""

import json
import logging
from datetime import datetime
from typing import Any

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
from .const import DOMAIN, MEDIA_TYPE_MAP, PUSH_COORDINATOR, TICKS_PER_SECOND
from .coordinator import MediaBrowserPushCoordinator, get_session_key
from .entity import MediaBrowserPushEntity
from .errors import NotFoundError
from .helpers import get_image_url, to_float, to_int

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
        PUSH_COORDINATOR
    ]

    @callback
    def coordinator_update() -> None:
        new_sessions: set[str] = {
            get_session_key(session)
            for session in coordinator.data.sessions.values()
            if get_session_key(session) not in coordinator.players
        }

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
        self._attr_name = f"{coordinator.hub.server_name} {self._session['DeviceName']}"
        self._attr_unique_id = f"{coordinator.hub.server_id}-{self._session_key}"
        self._attr_media_image_remotely_accessible = False
        self._update_from_data()

    def _handle_coordinator_update(self) -> None:
        session = self._coordinator.data.sessions.get(self._session_key)
        if self._session is None or session is None or session != self._session:
            self._last_update = utildt.utcnow()
            self._session = session
            self._update_from_data()
            super()._handle_coordinator_update()

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
        self._attr_repeat = REPEAT_MB_TO_HA.get(play_state.get("RepeatMode", ""))
        self._attr_is_volume_muted = play_state.get("IsMuted")
        if ticks := play_state.get("PositionTicks"):
            ticks = to_int(ticks, "PositionTicks")
            self._attr_media_position = (
                ticks // TICKS_PER_SECOND if ticks is not None else None
            )
        if level := play_state.get("VolumeLevel"):
            level = to_float(level, "VolumeLevel")
            self._attr_volume_level = (
                level / VOLUME_RATIO if level is not None else None
            )

    def _update_from_item(self, item: dict[str, Any]) -> None:
        self._attr_media_album_artist = item.get("AlbumArtist")
        self._attr_media_album_name = item.get("Album")
        if artists := item.get("Artists"):
            self._attr_media_artist = next(iter(artists), None)
        self._attr_media_channel = item.get("ChannelName")
        self._attr_media_content_id = item.get("Id")
        if content_type := item.get("Type"):
            self._attr_media_content_type = MEDIA_TYPE_MAP.get(
                content_type, content_type
            )
        if ticks := item.get("RunTimeTicks"):
            ticks = to_int(ticks, "RunTimeTicks")
            self._attr_media_duration = (
                ticks // TICKS_PER_SECOND if ticks is not None else None
            )
        self._attr_media_episode = item.get("EpisodeTitle")
        self._attr_media_season = item.get("SeasonName")
        self._attr_media_series_title = item.get("SeriesName")
        self._attr_media_title = item.get("Name")
        self._attr_media_image_url = get_image_url(
            item, self.hub.server_url or "", "Backdrop", True
        )

    def _update_from_session(self, session: dict[str, Any]) -> None:
        self._attr_state = MediaPlayerState.OFF
        remote_control: bool = (
            "SupportsRemoteControl" in session and session["SupportsRemoteControl"]
        )
        self._attr_media_position_updated_at = self._last_update
        self._attr_app_id = session.get("Id")
        self._attr_app_name = session.get("Client")
        if remote_control:
            self._attr_state = MediaPlayerState.IDLE
            self._attr_supported_features |= (
                MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.STOP
            )
            if commands := session.get("SupportedCommands"):
                for command in commands:
                    self._attr_supported_features |= COMMAND_MB_TO_HA.get(command, 0)
            play_index = session.get("PlaylistIndex", 0)
            play_length = session.get("PlaylistLength", 0)
            if play_index > 0:
                self._attr_supported_features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
            if play_index < play_length - 1:
                self._attr_supported_features |= MediaPlayerEntityFeature.NEXT_TRACK
        if item := session.get("NowPlayingItem"):
            self._update_from_item(item)
            self._attr_state = MediaPlayerState.PLAYING
        if play := session.get("PlayState"):
            self._update_from_state(play)
            if remote_control:
                self._attr_supported_features |= MediaPlayerEntityFeature.PLAY
                if "CanSeek" in play and play["CanSeek"]:
                    self._attr_supported_features |= MediaPlayerEntityFeature.SEEK
            if (
                "IsPaused" in play
                and play["IsPaused"]
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
                self._session["Id"],
                "Seek",
                {"SeekPositionTicks": int(position * TICKS_PER_SECOND)},
            )

    async def async_media_next_track(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session["Id"], "NextTrack")

    async def async_media_previous_track(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session["Id"], "PreviousTrack")

    async def async_media_pause(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session["Id"], "Pause")

    async def async_media_play_pause(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session["Id"], "PlayPause")

    async def async_media_stop(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session["Id"], "Stop")

    async def async_media_play(self) -> None:
        if self._session is not None:
            await self.hub.async_play_command(self._session["Id"], "Unpause")

    async def async_mute_volume(self, mute: bool) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session["Id"], "Mute" if mute else "Unmute"
            )

    async def async_volume_up(self) -> None:
        if self._session is not None:
            await self.hub.async_command(self._session["Id"], "VolumeUp")

    async def async_volume_down(self) -> None:
        if self._session is not None:
            await self.hub.async_command(self._session["Id"], "VolumeDown")

    async def async_set_volume_level(self, volume: float) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session["Id"],
                "SetVolume",
                data={"Volume": int(volume * VOLUME_RATIO)},
            )

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        if self._session is not None:
            await self.hub.async_command(
                self._session["Id"],
                "SetRepeatMode",
                data={"RepeatMode": REPEAT_HA_TO_MB[repeat]},
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
                self._session.get("PlayableMediaTypes"),
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

            await self.hub.async_play(self._session["Id"], params)

    async def _async_play_media_json(self, media_id: str) -> str:
        params = json.loads(media_id)
        params["Limit"] = 1
        items = (await self.hub.async_get_items(params)).items
        if len(items) > 0:
            return items[0].id
        raise NotFoundError("Cannot find any item with the specified parameters")

    @property
    def available(self) -> bool:
        return (
            self._session is not None
            and get_session_key(self._session) in self._coordinator.data.sessions
            and self.coordinator.last_update_success
        )
