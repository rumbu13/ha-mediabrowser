"""Models for the Media Browser (Emby/Jellyfin) integration."""


import mimetypes
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from dateutil import parser

from .const import DEFAULT_SERVER_NAME, TICKS_PER_SECOND

KEY_ADDRESS = "Address"
KEY_ALBUM = "Album"
KEY_ALBUM_ARTIST = "AlbumArtist"
KEY_ALBUM_ARTISTS = "AbumArtists"
KEY_ALBUM_ID = "AlbumId"
KEY_ALBUM_PRIMARY_IMAGE_TAG = "AlbumPrimaryImageTag"
KEY_APPLICATION_VERSION = "ApplicationVersion"
KEY_ART = "Art"
KEY_ARTIST_ITEMS = "ArtistItems"
KEY_BACKDROP = "Backdrop"
KEY_BACKDROP_IMAGE_TAGS = "BackdropImageTags"
KEY_CAN_SEEK = "CanSeek"
KEY_CHANNEL_ID = "ChannelId"
KEY_CHANNEL_NAME = "ChannelName"
KEY_CHANNEL_PRIMARY_IMAGE_TAG = "ChannelPrimaryImageTag"
KEY_CHILD_COUNT = "ChildCount"
KEY_CLIENT = "Client"
KEY_COLLECTION_TYPE = "CollectionType"
KEY_COMMUNITY_RATING = "CommunityRating"
KEY_CONTAINER = "Container"
KEY_DATA = "Data"
KEY_DATE_CREATED = "DateCreated"
KEY_DEVICE_ID = "DeviceId"
KEY_DEVICE_NAME = "DeviceName"
KEY_ENABLE_ALL_FOLDERS = "EnableAllFolders"
KEY_EPISODE_TITLE = "EpisodeTitle"
KEY_GENRE_ITEMS = "GenreItems"
KEY_ID = "Id"
KEY_INDEX_NUMBER = "IndexNumber"
KEY_IS_ACTIVE = "IsActive"
KEY_IS_ADMINISTRATOR = "IsAdministrator"
KEY_IS_DISABLED = "IsDisabled"
KEY_IS_FOLDER = "IsFolder"
KEY_IS_MUTED = "IsMuted"
KEY_IS_PAUSED = "IsPaused"
KEY_IMAGE_TAGS = "ImageTags"
KEY_ITEMS = "Items"
KEY_LAST_ACTIVITY_DATE = "LastActivityDate"
KEY_LOCAL_ADDRESS = "LocalAddress"
KEY_LOGO = "Logo"
KEY_MEDIA_SOURCE_ID = "MediaSourceId"
KEY_MEDIA_SOURCES = "MediaSources"
KEY_MEDIA_TYPE = "MediaType"
KEY_MESSAGE_TYPE = "MessageType"
KEY_NAME = "Name"
KEY_NOW_PLAYING_ITEM = "NowPlayingItem"
KEY_OFFICIAL_RATING = "OfficialRating"
KEY_OPERATING_SYSTEM = "OperatingSystem"
KEY_PARENT_ART_IMAGE_TAG = "ParentArtImageTag"
KEY_PARENT_ART_ITEM_ID = "ParentArtItemId"
KEY_PARENT_BACKDROP_IMAGE_TAGS = "ParentBackdropImageTags"
KEY_PARENT_BACKDROP_ITEM_ID = "ParentBackdropItemId"
KEY_PARENT_ID = "ParentId"
KEY_PARENT_INDEX_NUMBER = "ParentIndexNumber"
KEY_PARENT_LOGO_IMAGE_TAG = "ParentLogoImageTag"
KEY_PARENT_LOGO_ITEM_ID = "ParentLogoItemId"
KEY_PARENT_PRIMARY_IMAGE_TAG = "ParentPrimaryImageTag"
KEY_PARENT_PRIMARY_IMAGE_ITEM_ID = "ParentPrimaryImageItemId"
KEY_PARENT_THUMB_IMAGE_TAG = "ParentThumbImageTag"
KEY_PARENT_THUMB_ITEM_ID = "ParentThumbItemId"
KEY_PATH = "Path"
KEY_POLICY = "Policy"
KEY_PLAY_STATE = "PlayState"
KEY_PLAYABLE_MEDIA_TYPES = "PlayableMediaTypes"
KEY_PLAYLIST_INDEX = "PlaylistIndex"
KEY_PLAYLIST_LENGTH = "PlaylistLength"
KEY_PREMIERE_DATE = "PremiereDate"
KEY_POSITION_TICKS = "PositionTicks"
KEY_PRIMARY = "Primary"
KEY_SERIES_ID = "SeriesId"
KEY_SERIES_THUMB_IMAGE_TAG = "SeriesThumbImageTag"
KEY_REPEAT_MODE = "RepeatMode"
KEY_RUNTIME_TICKS = "RunTimeTicks"
KEY_SCREENSHOT = "Screenshot"
KEY_SCREENSHOT_IMAGE_TAGS = "ScreenshotImageTags"
KEY_SORT_NAME = "SortName"
KEY_SEASON_NAME = "SeasonName"
KEY_SERIES_NAME = "SeriesName"
KEY_SERIES_PRIMARY_IMAGE_TAG = "SeriesPrimaryImageTag"
KEY_SERVER_NAME = "ServerName"
KEY_STUDIOS = "Studios"
KEY_SUPPORTED_COMMANDS = "SupportedCommands"
KEY_SUPPORTS_MEDIA_CONTROL = "SupportsMediaControl"
KEY_SUPPORTS_REMOTE_CONTROL = "SupportsRemoteControl"
KEY_TOTAL_RECORD_COUNT = "TotalRecordCount"
KEY_TYPE = "Type"
KEY_THUMB = "Thumb"
KEY_VERSION = "Version"
KEY_VOLUME_LEVEL = "VolumeLevel"

VAL_SESSIONS = "Sessions"
VAL_UNKNOWN_OS = "Unknown OS"
VAL_UNKNOWN_VERSION = "?.?.?.?"
VAL_UNKNOWN_ADDRESS = "0.0.0.0"


class MediaBrowserType(Enum):
    """Possible values for server type."""

    EMBY = "emby"
    JELLYFIN = "jellyfin"


class MBIdBasedObject:
    """Object with mandatory id."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = str(data.get(KEY_ID))  # pylint: disable=invalid-name


class MBSystemInfo(MBIdBasedObject):
    """System information."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.operating_system: str = data.get(KEY_OPERATING_SYSTEM, VAL_UNKNOWN_OS)
        self.server_name: str = data.get(KEY_SERVER_NAME, DEFAULT_SERVER_NAME)
        self.version: str = data.get(KEY_VERSION, VAL_UNKNOWN_VERSION)
        self.local_address: str = data.get(KEY_LOCAL_ADDRESS, VAL_UNKNOWN_ADDRESS)

    @classmethod
    def empty(cls):
        """Create a default value that cannot be None"""
        return cls({"Id": 0})


class MBPlayState:
    """Session Play State."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.can_seek: bool = data[KEY_CAN_SEEK]
        self.is_paused: bool = data[KEY_IS_PAUSED]
        self.is_muted: bool = data[KEY_IS_MUTED]
        self.media_source_id: str | None = data.get(KEY_MEDIA_SOURCE_ID)
        self.position_ticks: int | None = data.get(KEY_POSITION_TICKS)
        self.repeat_mode: str = data[KEY_REPEAT_MODE]
        self.volume_level: int | None = data.get(KEY_VOLUME_LEVEL)


class MBMediaSource(MBIdBasedObject):
    """Media Source."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.path: str | None = data.get(KEY_PATH)


class MBIdNamedObject(MBIdBasedObject):
    """Object with id and name"""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.name: str | None = data.get(KEY_NAME)


class MBItem(MBIdNamedObject):
    """Base Item."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)

        self.album: str | None = data.get(KEY_ALBUM)
        self.album_artist: str | None = data.get(KEY_ALBUM_ARTIST)
        self.album_id: str | None = data.get(KEY_ALBUM_ID)
        self.album_artists: list[MBIdNamedObject] = (
            [MBIdNamedObject(artist) for artist in data[KEY_ALBUM_ARTISTS]]
            if KEY_ALBUM_ARTISTS in data
            else []
        )
        self.album_primary_image_tag: str | None = data.get(KEY_ALBUM_PRIMARY_IMAGE_TAG)
        self.artists: list[MBIdNamedObject] = (
            [MBIdNamedObject(artist) for artist in data[KEY_ARTIST_ITEMS]]
            if KEY_ARTIST_ITEMS in data
            else []
        )
        self.backdrop_image_tags: list[str] = data.get(KEY_BACKDROP_IMAGE_TAGS, [])
        self.channel_id: str | None = data.get(KEY_CHANNEL_ID)
        self.channel_name: str | None = data.get(KEY_CHANNEL_NAME)
        self.channel_primary_image_tag: str | None = data.get(
            KEY_CHANNEL_PRIMARY_IMAGE_TAG
        )
        self.child_count: int | None = data.get(KEY_CHILD_COUNT)
        self.collection_type: str | None = data.get(KEY_COLLECTION_TYPE)
        self.community_rating: float | None = data.get(KEY_COMMUNITY_RATING)
        self.container: str | None = data.get(KEY_CONTAINER)
        self.date_created: datetime | None = (
            parser.isoparse(data[KEY_DATE_CREATED])
            if KEY_DATE_CREATED in data
            else None
        )
        self.episode_title: str | None = data.get(KEY_EPISODE_TITLE)
        self.genres: list[MBIdNamedObject] = (
            [MBIdNamedObject(studio) for studio in data[KEY_GENRE_ITEMS]]
            if KEY_GENRE_ITEMS in data
            else []
        )
        self.image_tags: dict[str, str] | None = data.get(KEY_IMAGE_TAGS)
        self.index_number: int | None = data.get(KEY_INDEX_NUMBER)
        self.is_folder: bool | None = data.get(KEY_IS_FOLDER)
        self.media_sources: list[MBMediaSource] | None = (
            [MBMediaSource(item) for item in data[KEY_MEDIA_SOURCES]]
            if KEY_MEDIA_SOURCES in data
            else []
        )
        self.media_type: str | None = data.get(KEY_MEDIA_TYPE)
        self.official_rating: str | None = data.get(KEY_OFFICIAL_RATING)
        self.parent_art_item_id: str | None = data.get(KEY_PARENT_ART_ITEM_ID)
        self.parent_art_image_tag: str | None = data.get(KEY_PARENT_ART_IMAGE_TAG)
        self.parent_backdrop_image_tags: list[str] = data.get(
            KEY_PARENT_BACKDROP_IMAGE_TAGS, []
        )
        self.parent_backdrop_item_id: str | None = data.get(KEY_PARENT_BACKDROP_ITEM_ID)
        self.parent_id: str | None = data.get(KEY_PARENT_ID)
        self.parent_index_number: int | None = data.get(KEY_PARENT_INDEX_NUMBER)
        self.parent_logo_image_tag: str | None = data.get(KEY_PARENT_LOGO_IMAGE_TAG)
        self.parent_logo_item_id: str | None = data.get(KEY_PARENT_LOGO_ITEM_ID)
        self.parent_primary_image_item_id: str | None = data.get(
            KEY_PARENT_PRIMARY_IMAGE_ITEM_ID
        )
        self.parent_primary_image_tag: str | None = data.get(
            KEY_PARENT_PRIMARY_IMAGE_TAG
        )
        self.parent_thumb_item_id: str | None = data.get(KEY_PARENT_THUMB_ITEM_ID)
        self.parent_thumb_image_tag: str | None = data.get(KEY_PARENT_THUMB_IMAGE_TAG)
        self.premiere_date: datetime | None = (
            parser.isoparse(data[KEY_PREMIERE_DATE])
            if KEY_PREMIERE_DATE in data
            else None
        )
        self.runtime_ticks: int | None = data.get(KEY_RUNTIME_TICKS)
        self.screenshot_image_tags: list[str] = data.get(KEY_SCREENSHOT_IMAGE_TAGS, [])
        self.season_name: str | None = data.get(KEY_SEASON_NAME)
        self.series_name: str | None = data.get(KEY_SERIES_NAME)
        self.series_id: str | None = data.get(KEY_SERIES_ID)
        self.series_primary_image_tag: str | None = data.get(
            KEY_SERIES_PRIMARY_IMAGE_TAG
        )
        self.series_thumb_image_tag: str | None = data.get(KEY_SERIES_THUMB_IMAGE_TAG)
        self.sort_name: str | None = data.get(KEY_SORT_NAME)
        self.studios: list[MBIdNamedObject] = (
            [MBIdNamedObject(studio) for studio in data[KEY_STUDIOS]]
            if KEY_STUDIOS in data
            else []
        )
        self.type: str | None = data.get(KEY_TYPE)

    @property
    def real_id(self) -> str | None:
        """Gets the real item id if some virtual folder is encoded."""
        if self.id is not None:
            parts = self.id.split("/")
            return parts[-1] if len(parts) > 1 else self.id
        return None

    @property
    def backdrop_url(self) -> str | None:
        """Gets the best image as backdrop if available."""
        item_id = None
        item_tag = None
        if self.backdrop_image_tags is not None:
            if len(self.backdrop_image_tags) > 0:
                item_tag = KEY_BACKDROP
                item_id = self.real_id

        if item_id is None:
            if self.image_tags is not None:
                if KEY_BACKDROP in self.image_tags:
                    item_tag = KEY_BACKDROP
                    item_id = self.real_id
                elif KEY_PRIMARY in self.image_tags:
                    item_tag = KEY_PRIMARY
                    item_id = self.real_id
                elif len(self.image_tags) > 0:
                    item_tag = next(iter(self.image_tags))
                    item_id = self.real_id

        if item_id is None:
            if self.parent_backdrop_item_id is not None:
                item_tag = KEY_BACKDROP
                item_id = self.parent_backdrop_item_id

        if item_id is None:
            if self.parent_backdrop_image_tags is not None:
                if (
                    self.parent_id is not None
                    or self.parent_backdrop_item_id is not None
                ):
                    item_tag = KEY_BACKDROP
                    item_id = self.parent_id or self.parent_backdrop_item_id

        if item_id is not None:
            return f"/Items/{item_id}/Images/{item_tag}"

        return None

    @property
    def poster_url(self) -> str | None:
        """Gets the best image as poster if available."""
        item_id = None
        item_tag = None

        if self.image_tags is not None:
            if KEY_PRIMARY in self.image_tags:
                item_tag = KEY_PRIMARY
                item_id = self.real_id
            elif len(self.image_tags) > 0:
                item_tag = next(iter(self.image_tags))
                item_id = self.real_id

        if item_id is None:
            if self.parent_primary_image_item_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.parent_primary_image_item_id

        if item_id is None:
            if self.album_primary_image_tag is not None and self.album_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.album_id

        if item_id is None:
            if self.series_primary_image_tag is not None and self.series_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.series_id

        if item_id is None:
            if (
                self.channel_primary_image_tag is not None
                and self.channel_id is not None
            ):
                item_tag = KEY_PRIMARY
                item_id = self.channel_id

        if item_id is not None:
            return f"/Items/{item_id}/Images/{item_tag}"

        return None

    @property
    def art_url(self) -> str | None:
        """Gets the best image as fanart if available."""
        item_id = None
        item_tag = None

        if self.image_tags is not None:
            if KEY_ART in self.image_tags:
                item_tag = KEY_ART
                item_id = self.real_id
            elif len(self.image_tags) > 0:
                item_tag = next(iter(self.image_tags))
                item_id = self.real_id

        if item_id is None:
            if self.parent_art_item_id is not None:
                item_tag = KEY_ART
                item_id = self.parent_art_item_id

        if item_id is None:
            if self.parent_art_image_tag is not None and self.parent_id is not None:
                item_tag = KEY_ART
                item_id = self.parent_id

        if item_id is not None:
            return f"/Items/{item_id}/Images/{item_tag}"

        return None

    @property
    def thumb_url(self) -> str | None:
        """Gets the best image as thumbnail if available."""
        item_id = None
        item_tag = None
        if self.image_tags is not None:
            if KEY_THUMB in self.image_tags:
                item_tag = KEY_THUMB
                item_id = self.real_id
            elif KEY_ART in self.image_tags:
                item_tag = KEY_ART
                item_id = self.real_id
            elif KEY_PRIMARY in self.image_tags:
                item_tag = KEY_PRIMARY
                item_id = self.real_id
            elif len(self.image_tags) > 0:
                item_tag = next(iter(self.image_tags))
                item_id = self.real_id
        if not item_id:
            if self.screenshot_image_tags is not None:
                item_tag = KEY_SCREENSHOT
                item_id = self.real_id
        if not item_id:
            if self.parent_thumb_item_id is not None:
                item_tag = KEY_THUMB
                item_id = self.parent_thumb_item_id
        if not item_id:
            if self.parent_thumb_image_tag is not None and self.parent_id is not None:
                item_tag = KEY_THUMB
                item_id = self.parent_id
        if not item_id:
            if self.parent_art_item_id is not None:
                item_tag = KEY_ART
                item_id = self.parent_art_item_id
        if not item_id:
            if self.parent_art_image_tag is not None and self.parent_id is not None:
                item_tag = KEY_ART
                item_id = self.parent_id
        if not item_id:
            if self.parent_primary_image_item_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.parent_primary_image_item_id
        if not item_id:
            if self.parent_primary_image_tag is not None and self.parent_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.parent_id
        if not item_id:
            if self.parent_backdrop_item_id is not None:
                item_tag = KEY_BACKDROP
                item_id = self.parent_backdrop_item_id
        if not item_id:
            if (
                self.parent_backdrop_image_tags is not None
                and self.parent_id is not None
            ):
                item_tag = KEY_BACKDROP
                item_id = self.parent_id
        if not item_id:
            if self.parent_logo_item_id is not None:
                item_tag = KEY_LOGO
                item_id = self.parent_logo_item_id
        if not item_id:
            if self.parent_logo_image_tag is not None and self.parent_id is not None:
                item_tag = KEY_LOGO
                item_id = self.parent_id
        if not item_id:
            if self.series_thumb_image_tag is not None and self.series_id is not None:
                item_tag = KEY_THUMB
                item_id = self.series_id
        if not item_id:
            if self.series_primary_image_tag is not None and self.series_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.series_id
        if not item_id:
            if self.album_primary_image_tag is not None and self.album_id is not None:
                item_tag = KEY_PRIMARY
                item_id = self.album_id
        if not item_id:
            if (
                self.channel_primary_image_tag is not None
                and self.channel_id is not None
            ):
                item_tag = KEY_PRIMARY
                item_id = self.channel_id

        if item_id is not None:
            return f"/Items/{item_id}/Images/{item_tag}"

    @property
    def mime_type(self) -> str | None:
        """Gets the MIME type of the specified item."""
        if (
            self.media_sources is not None
            and len(self.media_sources) > 0
            and self.media_sources[0].path is not None
        ):
            mime_type, _ = mimetypes.guess_type(self.media_sources[0].path)
            return mime_type
        if self.container is not None:
            try:
                return mimetypes.types_map["." + self.container]
            except KeyError:
                return None
        return None

    @property
    def upcoming_data(self) -> dict[str, Any]:
        """Gets standard upcoming media formatted data."""

        studios = (
            ",".join(studio.name for studio in self.studios if studio.name is not None)
            if self.studios is not None and len(self.studios) > 0
            else None
        )
        genres = (
            ",".join(genre.name for genre in self.genres if genre.name is not None)
            if self.genres is not None
            else None
        )

        artists = (
            ",".join(artist.name for artist in self.artists if artist.name is not None)
            if self.artists is not None
            else None
        )

        result: dict[str, Any] = {"id": self.id}

        poster = self.poster_url
        fanart = self.art_url
        backdrop = self.backdrop_url
        thumb = self.thumb_url

        if self.name is not None:
            result["name"] = self.name

        if self.premiere_date is not None:
            result["premiere"] = self.premiere_date

        if self.date_created is not None:
            result["added"] = self.date_created

        if self.runtime_ticks is not None:
            result["runtime"] = self.runtime_ticks // TICKS_PER_SECOND

        if self.community_rating is not None:
            result["rating"] = self.community_rating

        if self.official_rating is not None:
            result["official_rating"] = self.official_rating

        if studios is not None and len(studios) > 0:
            result["studios"] = studios
        if genres is not None and len(genres) > 0:
            result["genres"] = genres
        if artists is not None and len(artists) > 0:
            result["artists"] = artists

        if self.album is not None:
            result["album"] = self.album

        if self.season_name is not None:
            result["season"] = self.season_name
        if self.series_name is not None:
            result["series"] = self.series_name
        if self.index_number is not None and self.parent_index_number is not None:
            result[
                "episode"
            ] = f"S{self.parent_index_number:02d}E{self.index_number:02d}"

        if poster is not None:
            result["poster"] = poster
        if fanart is not None:
            result["fanart"] = fanart
        if backdrop is not None:
            result["backdrop"] = backdrop
        if thumb is not None:
            result["thumbnail"] = thumb

        return result


class MBSession(MBIdBasedObject):
    """Session object."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.application_version: str | None = data.get(KEY_APPLICATION_VERSION)
        self.client: str | None = data.get(KEY_CLIENT)
        self.device_name: str | None = data.get(KEY_DEVICE_NAME)
        self.device_id: str | None = data.get(KEY_DEVICE_ID)
        self.is_active: bool | None = data.get(KEY_IS_ACTIVE)
        self.last_activity_date: datetime = parser.isoparse(
            data[KEY_LAST_ACTIVITY_DATE]
        )
        self.now_playing_item: MBItem | None = (
            MBItem(data[KEY_NOW_PLAYING_ITEM]) if KEY_NOW_PLAYING_ITEM in data else None
        )
        self.play_state: MBPlayState = MBPlayState(data[KEY_PLAY_STATE])
        self.playlist_index: int | None = data.get(KEY_PLAYLIST_INDEX)
        self.playlist_length: int | None = data.get(KEY_PLAYLIST_LENGTH)
        self.playable_media_types: list[str] = data[KEY_PLAYABLE_MEDIA_TYPES]
        self.supported_commands: list[str] = data[KEY_SUPPORTED_COMMANDS]
        self.supports_media_control: bool | None = data.get(KEY_SUPPORTS_MEDIA_CONTROL)
        self.supports_remote_control: bool = data[KEY_SUPPORTS_REMOTE_CONTROL]

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
        items = data.get(KEY_ITEMS)
        self.items: list[MBItem] = (
            [MBItem(item) for item in items] if items is not None else []
        )
        self.total_record_count: int = (
            data[KEY_TOTAL_RECORD_COUNT]
            if data is not None and KEY_TOTAL_RECORD_COUNT in data
            else 0
        )


class MBMessage:
    """Websocket message."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.message_type: str | None = data.get(KEY_MESSAGE_TYPE)


class MBSessionsMessage(MBMessage):
    """Sessions websocket message."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.sessions: list[MBSession] = (
            [MBSession(session_data) for session_data in data[KEY_DATA]]
            if data is not None
            and self.message_type == VAL_SESSIONS
            and KEY_DATA in data
            else []
        )


class MBPolicy:
    """User policy."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.is_administrator: bool = data[KEY_IS_ADMINISTRATOR]
        self.is_disabled: bool = data[KEY_IS_DISABLED]
        self.enable_all_folders: bool = data[KEY_ENABLE_ALL_FOLDERS]


class MBUser(MBIdNamedObject):
    """User information."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self.policy: MBPolicy | None = (
            MBPolicy(data[KEY_POLICY]) if KEY_POLICY in data else None
        )


class MBDiscovery(MBIdNamedObject):
    """Discovery information."""

    def __init__(self, data: dict[str, Any], server_type: MediaBrowserType) -> None:
        super().__init__(data)
        self.address: str = data[KEY_ADDRESS]
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
    def use_ssl(self) -> bool | None:
        """Returns true if the address from the discovery info uses SSL."""
        if self.address is not None:
            parse_result = urlparse(self.address)
            return parse_result.scheme == "https"
        return None
