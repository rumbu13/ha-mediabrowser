"""Media players for the Media Browser (Emby/Jellyfin) integration."""


from datetime import datetime
from typing import Any
from .errors import NotFoundError

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
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as utildt

import json

from .const import (
    DOMAIN,
    PUSH_COORDINATOR,
)
from .coordinator import MediaBrowserPushCoordinator
from .entity import MediaBrowserPushEntity
from .models import MBSession
from .browse_media import async_browse_media_id

TICKS_PER_SECOND = 10000000
VOLUME_RATIO = 100

TYPE_MB_TO_HA: dict[str, str] = {
    "AggregateFolder": MediaType.PLAYLIST,
    "Audio": MediaType.MUSIC,
    "AudioBook": MediaType.PODCAST,
    "BasePluginFolder": MediaType.PLAYLIST,
    "Book": MediaType.IMAGE,
    "BoxSet": MediaType.PLAYLIST,
    "ChannelFolderItem": MediaType.CHANNELS,
    "CollectionFolder": MediaType.PLAYLIST,
    "Episode": MediaType.EPISODE,
    "Folder": MediaType.PLAYLIST,
    "Genre": MediaType.GENRE,
    "LiveTvChannel": MediaType.CHANNEL,
    "LiveTvProgram": MediaType.CHANNEL,
    "ManualPlaylistsFolder": MediaType.PLAYLIST,
    "Movie": MediaType.MOVIE,
    "MusicAlbum": MediaType.ALBUM,
    "MusicArtist": MediaType.ARTIST,
    "MusicGenre": MediaType.GENRE,
    "MusicVideo": MediaType.VIDEO,
    "Person": MediaType.ARTIST,
    "Photo": MediaType.IMAGE,
    "PhotoAlbum": MediaType.ALBUM,
    "Playlist": MediaType.PLAYLIST,
    "PlaylistFolder": MediaType.PLAYLIST,
    "Program": MediaType.APP,
    "Season": MediaType.SEASON,
    "Series": MediaType.TVSHOW,
    "Studio": MediaType.PLAYLIST,
    "Trailer": MediaType.VIDEO,
    "TvChannel": MediaType.CHANNEL,
    "TvProgram": MediaType.CHANNEL,
    "UserRootFolder": MediaType.PLAYLIST,
    "UserView": MediaType.PLAYLIST,
    "Video": MediaType.VIDEO,
    "Year": MediaType.PLAYLIST,
}

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
            session.id
            for session in coordinator.data.sessions.values()
            if session.id not in coordinator.players
        }

        new_entities = [
            MediaBrowserPlayer(coordinator.data.sessions[session_id], coordinator)
            for session_id in new_sessions
        ]

        coordinator.players |= new_sessions
        async_add_entities(new_entities)

    coordinator_update()
    entry.async_on_unload(coordinator.async_add_listener(coordinator_update))


class MediaBrowserPlayer(MediaBrowserPushEntity, MediaPlayerEntity):
    """Represents a media player entity."""

    def __init__(
        self,
        session: MBSession,
        coordinator: MediaBrowserPushCoordinator,
        context: Any = None,
    ) -> None:
        super().__init__(coordinator, context)

        self.coordinator = coordinator
        self.session_id: str = session.id
        self.session: MBSession = coordinator.data.sessions[session.id]
        self.last_update: datetime = None
        self._attr_name = (
            f"{coordinator.hub.server_name} {self.session.device_name } Player"
        )
        self._attr_unique_id = f"{coordinator.hub.server_id}-{session.id}"
        self._attr_media_image_remotely_accessible = False

    def _handle_coordinator_update(self) -> None:
        self.session = self.coordinator.data.sessions.get(self.session_id)
        self.last_update = utildt.utcnow()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return (
            self.session_id in self.coordinator.data.sessions
            and self.coordinator.last_update_success
        )

    @property
    def device_info(self) -> DeviceInfo | None:
        try:
            return DeviceInfo(
                identifiers={(DOMAIN, self.session.device_id)},
                model=self.session.client,
                name=self.session.device_name,
                sw_version=self.session.application_version,
                via_device=(DOMAIN, self.coordinator.hub.server_id),
            )
        except AttributeError:
            return None

    @property
    def media_album_artist(self) -> str | None:
        try:
            return self.session.now_playing_item.album_artist
        except AttributeError:
            return None

    @property
    def media_album_name(self) -> str | None:
        try:
            return self.session.now_playing_item.album
        except AttributeError:
            return None

    @property
    def media_artist(self) -> str | None:
        try:
            return self.session.now_playing_item.artists[0]
        except (AttributeError, IndexError, TypeError):
            return None

    @property
    def media_channel(self) -> str | None:
        try:
            return self.session.now_playing_item.channel_name
        except AttributeError:
            return None

    @property
    def media_content_id(self) -> str | None:
        try:
            return self.session.now_playing_item.id
        except AttributeError:
            return None

    @property
    def media_content_type(self) -> MediaType | str | None:
        try:
            original_type = self.session.now_playing_item.type
            return TYPE_MB_TO_HA.get(original_type, original_type)
        except AttributeError:
            return None

    @property
    def media_duration(self) -> int | None:
        try:
            return self.session.now_playing_item.runtime_ticks // TICKS_PER_SECOND
        except (AttributeError, TypeError):
            return None

    @property
    def media_episode(self) -> str | None:
        try:
            return self.session.now_playing_item.episode_title
        except AttributeError:
            return None

    @property
    def media_position(self) -> int | None:
        try:
            return self.session.play_state.position_ticks // TICKS_PER_SECOND
        except (AttributeError, TypeError):
            return None

    @property
    def media_season(self) -> str | None:
        try:
            return self.session.now_playing_item.season_name
        except AttributeError:
            return None

    @property
    def media_series_title(self) -> str | None:
        try:
            return self.session.now_playing_item.series_name
        except AttributeError:
            return None

    @property
    def media_title(self) -> str | None:
        try:
            return self.session.now_playing_item.name
        except AttributeError:
            return None

    @property
    def state(self) -> MediaPlayerState | None:
        if self.session is not None:
            if self.session.now_playing_item is not None:
                if self.session.play_state is not None:
                    if self.session.play_state.is_paused:
                        return MediaPlayerState.PAUSED
                return MediaPlayerState.PLAYING
            if self.session.supports_remote_control:
                return MediaPlayerState.IDLE
            else:
                return MediaPlayerState.OFF

        return None

    @property
    def media_image_url(self) -> str | None:
        try:
            image_url = self.session.now_playing_item.backdrop_url
            return (
                f"{self.hub.server_url}{image_url}" if image_url is not None else None
            )
        except AttributeError:
            return None

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        features = MediaPlayerEntityFeature(0)
        if (
            self.session is None
            or self.session.supports_remote_control is None
            or self.session.supports_remote_control is False
        ):
            return features

        if self.session.supported_commands is not None:
            for command in self.session.supported_commands:
                features |= COMMAND_MB_TO_HA.get(command, 0)
        if self.session.play_state is not None:
            if self.session.play_state.can_seek:
                features |= MediaPlayerEntityFeature.SEEK

        if self.session.supports_remote_control:
            features |= (
                MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.STOP
            )

        if self.session.now_playing_item is not None:
            features |= MediaPlayerEntityFeature.PLAY

        play_index = self.session.playlist_index or 0
        play_length = self.session.playlist_length or 0

        if play_index > 0:
            features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
        if play_index < play_length - 1:
            features |= MediaPlayerEntityFeature.NEXT_TRACK

        return features

    @property
    def media_position_updated_at(self) -> datetime | None:
        return self.last_update

    @property
    def app_id(self) -> str | None:
        try:
            return self.session.id
        except AttributeError:
            return None

    @property
    def app_name(self) -> str | None:
        try:
            return self.session.client
        except AttributeError:
            return None

    @property
    def source(self) -> str | None:
        try:
            return self.session.play_state.media_source_id
        except AttributeError:
            return None

    @property
    def repeat(self) -> RepeatMode | None:
        try:
            return REPEAT_MB_TO_HA.get(self.session.play_state.repeat_mode)
        except AttributeError:
            return None

    @property
    def is_volume_muted(self) -> bool | None:
        try:
            return self.session.play_state.is_muted
        except AttributeError:
            return None

    @property
    def volume_level(self) -> float | None:
        try:
            return float(self.session.play_state.volume_level) / VOLUME_RATIO
        except (AttributeError, TypeError):
            return None

    async def async_media_seek(self, position: float) -> None:
        if self.session is not None:
            await self.hub.async_play_command(
                self.session.id,
                "Seek",
                {"SeekPositionTicks": int(position * TICKS_PER_SECOND)},
            )

    async def async_media_next_track(self) -> None:
        if self.session is not None:
            await self.hub.async_play_command(self.session.id, "NextTrack")

    async def async_media_previous_track(self) -> None:
        if self.session is not None:
            await self.hub.async_play_command(self.session.id, "PreviousTrack")

    async def async_media_pause(self) -> None:
        if self.session is not None:
            await self.hub.async_play_command(self.session.id, "Pause")

    async def async_media_play_pause(self) -> None:
        if self.session is not None:
            await self.hub.async_play_command(self.session.id, "PlayPause")

    async def async_media_stop(self) -> None:
        if self.session is not None:
            await self.hub.async_play_command(self.session.id, "Stop")

    async def async_media_play(self) -> None:
        if self.session is not None:
            await self.hub.async_play_command(self.session.id, "Unpause")

    async def async_mute_volume(self, mute: bool) -> None:
        return await self.hub.async_command(
            self.session.id, "Mute" if mute else "Unmute"
        )

    async def async_volume_up(self) -> None:
        if self.session is not None:
            await self.hub.async_command(self.session.id, "VolumeUp")

    async def async_volume_down(self) -> None:
        if self.session is not None:
            await self.hub.async_command(self.session.id, "VolumeDown")

    async def async_set_volume_level(self, volume: float) -> None:
        if self.session is not None:
            await self.hub.async_command(
                self.session.id,
                "SetVolume",
                data={"Volume": int(volume * VOLUME_RATIO)},
            )

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        if self.session is not None:
            await self.hub.async_command(
                self.session_id,
                "SetRepeatMode",
                data={"RepeatMode": REPEAT_HA_TO_MB[repeat]},
            )

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        if self.session is not None:
            return await async_browse_media_id(
                self.hub, media_content_id, self.session.playable_media_types, True
            )

        return None

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        if media_id.startswith("{"):
            media_id = await self._async_play_media_json(media_id)

        params = {"PlayCommand": "PlayNow", "ItemIds": media_id}

        if "command" in kwargs:
            params["PlayCommand"] = kwargs["command"]

        if "start_position" in kwargs:
            params["StartPositionTicks"] = (
                float(kwargs["start_position"]) * TICKS_PER_SECOND
            )

        await self.hub.async_play(self.session.id, params)

    async def _async_play_media_json(self, media_id: str) -> str:
        params = json.loads(media_id)
        params["Limit"] = 1
        items = (await self.hub.async_get_items(params)).items
        if len(items) > 0:
            return items[0].id
        raise NotFoundError("Cannot find any item with the specified parameters")
