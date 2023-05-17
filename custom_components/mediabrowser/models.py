"""Models for the Media Browser (Emby/Jellyfin) integration."""


from enum import Enum
import mimetypes
from typing import Any
from urllib.parse import urlparse

KEY_ITEMS = "Items"
KEY_LOCAL_ADDRESS = "LocalAddress"
KEY_OPERATING_SYSTEM = "OperatingSystem"
KEY_SERVER_NAME = "ServerName"
KEY_VERSION = "Version"
KEY_TOTAL_RECORD_COUNT = "TotalRecordCount"


class MediaBrowserType(Enum):
    """Possible values for server type."""

    EMBY = "emby"
    JELLYFIN = "jellyfin"


class MBIdBasedObject:
    """Object with an id."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = _safe_get(data, "Id")


class MBSystemInfo(MBIdBasedObject):
    """System information."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.operating_system: str = _safe_get(data, KEY_OPERATING_SYSTEM)
        self.server_name: str = _safe_get(data, KEY_SERVER_NAME)
        self.version: str = _safe_get(data, KEY_VERSION)
        self.local_address: str = _safe_get(data, KEY_LOCAL_ADDRESS)


class MBPlayState:
    """Session Play State."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.can_seek: bool = _safe_get(data, "CanSeek")
        self.is_paused: bool = _safe_get(data, "IsPaused")
        self.is_muted: bool = _safe_get(data, "IsMuted")
        self.repeat_mode: str = _safe_get(data, "RepeatMode")
        self.volume_level: int = _safe_get(data, "VolumeLevel")
        self.position_ticks: int = _safe_get(data, "PositionTicks")
        self.media_source_id: str = _safe_get(data, "MediaSourceId")


class MBMediaSource(MBIdBasedObject):
    """Media Source."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.path: str = _safe_get(data, "Path")


class MBItem(MBIdBasedObject):
    """Base Item."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.name: str = _safe_get(data, "Name")
        self.sort_name: str = _safe_get(data, "SortName")
        self.backdrop_image_tags: list[str] = _safe_get(data, "BackdropImageTags")
        self.parent_backdrop_image_tags: list[str] = _safe_get(
            data, "ParentBackdropImageTags"
        )
        self.parent_backdrop_item_id = _safe_get(data, "ParentBackdropItemId")
        self.collection_type: str = _safe_get(data, "CollectionType")
        self.media_type: str = _safe_get(data, "MediaType")
        self.type: str = _safe_get(data, "Type")
        self.runtime_ticks: int = _safe_get(data, "RunTimeTicks")
        self.album_artist: str = _safe_get(data, "AlbumArtist")
        self.album: str = _safe_get(data, "Album")
        self.artists: list[str] = _safe_get(data, "Artists")
        self.channel_name: str = _safe_get(data, "ChannelName")
        self.episode_title: str = _safe_get(data, "EpisodeTitle")
        self.season_name: str = _safe_get(data, "SeasonName")
        self.series_name: str = _safe_get(data, "SeriesName")
        self.index_number: int = _safe_get(data, "IndexNumber")
        self.image_tags: dict[str, str] = _safe_get(data, "ImageTags")
        self.parent_id: str = _safe_get(data, "ParentId")
        self.parent_thumb_item_id: str = _safe_get(data, "ParentThumbItemId")
        self.parent_thumb_image_tag: str = _safe_get(data, "ParentThumbImageTag")
        self.parent_art_item_id: str = _safe_get(data, "ParentArtItemId")
        self.parent_art_image_tag: str = _safe_get(data, "ParentArtImageTag")
        self.parent_backdrop_item_id: str = _safe_get(data, "ParentBackdropItemId")
        self.parent_backdrop_image_tags: list[str] = _safe_get(
            data, "ParentBackdropImageTags"
        )
        self.parent_primary_image_item_id: str = _safe_get(
            data, "ParentPrimaryImageItemId"
        )
        self.parent_primary_image_tag: str = _safe_get(data, "ParentPrimaryImageTag")
        self.series_thumb_image_tag: str = _safe_get(data, "SeriesThumbImageTag")
        self.series_id: str = _safe_get(data, "SeriesId")
        self.series_primary_image_tag: str = _safe_get(data, "SeriesPrimaryImageTag")
        self.album_primary_image_tag: str = _safe_get(data, "AlbumPrimaryImageTag")
        self.album_id: str = _safe_get(data, "AlbumId")
        self.screenshot_image_tags: list[str] = _safe_get(data, "ScreenshotImageTags")
        self.parent_logo_image_tag: str = _safe_get(data, "ParentLogoImageTag")
        self.parent_logo_item_id: str = _safe_get(data, "ParentLogoItemId")
        self.channel_primary_image_tags: str = _safe_get(data, "ChannelPrimaryImageTag")
        self.channel_id: str = _safe_get(data, "ChannelId")

        self.is_folder: bool = _safe_get(data, "IsFolder")
        self.child_count: int = _safe_get(data, "ChildCount")

        self.media_sources: list[MBMediaSource] = None
        media_sources = _safe_get(data, "MediaSources")
        if media_sources is not None:
            self.media_sources = [MBMediaSource(item) for item in media_sources]

        self.container: str = _safe_get(data, "Container")

    @property
    def real_id(self) -> str:
        """Gets the real item id if some virtual folder is encoded."""
        parts = self.id.split("/")
        return parts[-1] if len(parts) > 1 else self.id

    @property
    def backdrop_url(self) -> str | None:
        """Gets the best image as backdrop if available."""
        item_id = None
        item_tag = None
        if self.backdrop_image_tags is not None:
            if len(self.backdrop_image_tags) > 0:
                item_tag = "Backdrop"
                item_id = self.real_id

        if item_id is None:
            if self.image_tags is not None:
                if "Backdrop" in self.image_tags:
                    item_tag = "Backdrop"
                    item_id = self.real_id
                elif "Primary" in self.image_tags:
                    item_tag = "Primary"
                    item_id = self.real_id
                elif len(self.image_tags) > 0:
                    item_tag = next(iter(self.image_tags))[0]
                    item_id = self.real_id

        if item_id is None:
            if self.parent_backdrop_item_id is not None:
                item_tag = "Backdrop"
                item_id = self.parent_backdrop_item_id

        if item_id is None:
            if self.parent_backdrop_image_tags is not None:
                if (
                    self.parent_id is not None
                    or self.parent_backdrop_item_id is not None
                ):
                    item_tag = "Backdrop"
                    item_id = self.parent_id or self.parent_backdrop_item_id

        if item_id is not None:
            return f"/Items/{item_id}/Images/{item_tag}"

        return None

    @property
    def thumb_url(self) -> str | None:
        """Gets the best image as thumbnail if available."""
        item_id = None
        item_tag = None
        if self.image_tags is not None:
            if "Thumb" in self.image_tags:
                item_tag = "Thumb"
                item_id = self.real_id
            elif "Art" in self.image_tags:
                item_tag = "Art"
                item_id = self.real_id
            elif "Primary" in self.image_tags:
                item_tag = "Primary"
                item_id = self.real_id
            elif len(self.image_tags) > 0:
                item_tag = next(iter(self.image_tags))[0]
                item_id = self.real_id
        if not item_id:
            if self.screenshot_image_tags is not None:
                item_tag = "Screenshot"
                item_id = self.real_id
        if not item_id:
            if self.parent_thumb_item_id is not None:
                item_tag = "Thumb"
                item_id = self.parent_thumb_item_id
        if not item_id:
            if self.parent_thumb_image_tag is not None and self.parent_id is not None:
                item_tag = "Thumb"
                item_id = self.parent_id
        if not item_id:
            if self.parent_art_item_id is not None:
                item_tag = "Art"
                item_id = self.parent_art_item_id
        if not item_id:
            if self.parent_art_image_tag is not None and self.parent_id is not None:
                item_tag = "Art"
                item_id = self.parent_id
        if not item_id:
            if self.parent_primary_image_item_id is not None:
                item_tag = "Primary"
                item_id = self.parent_primary_image_item_id
        if not item_id:
            if self.parent_primary_image_tag is not None and self.parent_id is not None:
                item_tag = "Primary"
                item_id = self.parent_id
        if not item_id:
            if self.parent_backdrop_item_id is not None:
                item_tag = "Backdrop"
                item_id = self.parent_backdrop_item_id
        if not item_id:
            if (
                self.parent_backdrop_image_tags is not None
                and self.parent_id is not None
            ):
                item_tag = "Backdrop"
                item_id = self.parent_id
        if not item_id:
            if self.parent_logo_item_id is not None:
                item_tag = "Logo"
                item_id = self.parent_logo_item_id
        if not item_id:
            if self.parent_logo_image_tag is not None and self.parent_id is not None:
                item_tag = "Logo"
                item_id = self.parent_id
        if not item_id:
            if self.series_thumb_image_tag is not None and self.series_id is not None:
                item_tag = "Thumb"
                item_id = self.series_id
        if not item_id:
            if self.series_primary_image_tag is not None and self.series_id is not None:
                item_tag = "Primary"
                item_id = self.series_id
        if not item_id:
            if self.album_primary_image_tag is not None and self.album_id is not None:
                item_tag = "Primary"
                item_id = self.album_id
        if not item_id:
            if (
                self.channel_primary_image_tags is not None
                and self.channel_id is not None
            ):
                item_tag = "Primary"
                item_id = self.channel_id

        if item_id is not None:
            return f"/Items/{item_id}/Images/{item_tag}"

    @property
    def mime_type(self) -> str | None:
        """Gets the MIME type of the specified item."""
        if self.media_sources is not None and len(self.media_sources) > 0:
            mime_type, _ = mimetypes.guess_type(self.media_sources[0].path)
            return mime_type
        if self.container is not None:
            try:
                return mimetypes.types_map["." + self.container]
            except KeyError:
                return None
        return None


class MBSession(MBIdBasedObject):
    """Session object."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.client: str = _safe_get(data, "Client")
        self.device_name: str = _safe_get(data, "DeviceName")
        self.device_id: str = _safe_get(data, "DeviceId")
        self.application_version: str = _safe_get(data, "ApplicationVersion")
        self.play_state: MBPlayState = (
            MBPlayState(data["PlayState"])
            if data is not None and "PlayState" in data
            else None
        )
        self.now_playing_item: MBItem = (
            MBItem(data["NowPlayingItem"])
            if data is not None and "NowPlayingItem" in data
            else None
        )
        self.supported_commands: list[str] = _safe_get(data, "SupportedCommands")
        self.supports_media_control: bool = _safe_get(data, "SupportsMediaControl")
        self.supports_remote_control: bool = _safe_get(data, "SupportsRemoteControl")
        self.is_active: bool = _safe_get(data, "IsActive")
        self.playable_media_types: list[str] = _safe_get(data, "PlayableMediaTypes")
        self.playlist_index: int = _safe_get(data, "PlaylistIndex")
        self.playlist_length: int = _safe_get(data, "PlaylistLength")

    @property
    def is_dlna(self) -> bool:
        """Return true if this session is a DLNA session."""
        return self.client is not None and "dlna" in self.client.lower()

    @property
    def is_mobile(self) -> bool:
        """Return true if this session is a mobile session."""
        if self.client is not None:
            return any(x in self.client.lower() for x in [" android", " ios"])
        return False

    @property
    def is_web(self) -> bool:
        """Return true if this session is a web session."""
        return self.client is not None and " web" in self.client.lower()


class MBResponse:
    """Standard REST response."""

    def __init__(self, data: dict[str, Any]) -> None:
        items = _safe_get(data, "Items")
        self.items = [MBItem(item) for item in items] if items is not None else None
        self.total_record_count: int = (
            data["TotalRecordCount"]
            if data is not None and "TotalRecordCount" in data
            else None
        )


class MBMessage:
    """Websocket message."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.message_type: str = _safe_get(data, "MessageType")


class MBSessionsMessage(MBMessage):
    """Sessions websocket message."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.sessions: list[MBSession] = (
            [MBSession(session_data) for session_data in data["Data"]]
            if data is not None and self.message_type == "Sessions" and "Data" in data
            else None
        )


class MBPolicy:
    """User policy."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.is_administrator: str = _safe_get(data, "IsAdministrator")
        self.is_disabled: str = _safe_get(data, "IsDisabled")
        self.enable_all_folders: bool = _safe_get(data, "EnableAllFolders")


class MBUser(MBIdBasedObject):
    """User information."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.name: str = _safe_get(data, "Name")
        self.address: str = _safe_get(data, "Address")
        self.policy: MBPolicy = MBPolicy(_safe_get(data, "Policy"))


class MBDiscovery(MBIdBasedObject):
    """Discovery information."""

    def __init__(self, data: dict[str, Any], server_type: MediaBrowserType) -> None:
        super().__init__(data)
        self.name: str = _safe_get(data, "Name")
        self.address: str = _safe_get(data, "Address")
        self.endpoint: str = _safe_get(data, "Endpoint")
        self.server_type = server_type

    @property
    def host(self) -> str | None:
        """Extract the host from the discovery info."""
        if self.address is not None:
            parse_result = urlparse(self.address)
            return parse_result.hostname
        return None

    @property
    def port(self) -> int | None:
        """Extract the port from the discovery info."""
        if self.address is not None:
            parse_result = urlparse(self.address)
            return parse_result.port
        return None

    @property
    def use_ssl(self) -> int | None:
        """Returns true if the address from the discovery info uses SSL."""
        if self.address is not None:
            parse_result = urlparse(self.address)
            return parse_result.scheme == "https"
        return None


def _safe_get(data: dict[str, Any], key: str) -> Any:
    return data.get(key) if data is not None else None
