"""Constants for the Media Browser (Emby/Jellyfin) integration."""

from typing import Any

from homeassistant.backports.enum import StrEnum
from homeassistant.components.media_player import MediaClass, MediaType

DOMAIN = "mediabrowser"


CONF_SERVER = "server"
CONF_CLIENT_NAME = "client"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_VERSION = "device_version"
CONF_DEVICE_ID = "device_id"
CONF_IGNORE_WEB_PLAYERS = "ignore_web_players"
CONF_IGNORE_DLNA_PLAYERS = "ignore_dlna_players"
CONF_IGNORE_MOBILE_PLAYERS = "ignore_mobile_players"
CONF_IGNORE_APP_PLAYERS = "ignore_app_players"
CONF_PURGE_PLAYERS = "purge_players"
CONF_TIMEOUT = "timeout"
CONF_UNIQUE_ID = "unique_id"
CONF_UPCOMING_MEDIA = "upcoming_media"

CONF_SERVER_ID = "server_id"
CONF_SERVER_PING = "server_ping"
CONF_SERVER_NAME = "server_name"


CONF_SENSORS = "sensors"
CONF_SENSOR_ITEM_TYPE = "sensor_type"
CONF_SENSOR_USER = "sensor_user"
CONF_SENSOR_LIBRARY = "sensor_library"
CONF_SENSOR_REMOVE = "sensor_remove"

CONF_CACHE_SERVER_NAME = "cache_server_name"
CONF_CACHE_SERVER_ID = "cache_server_id"
CONF_CACHE_SERVER_PING = "cache_server_ping"
CONF_CACHE_SERVER_VERSION = "cache_server_version"
CONF_CACHE_SERVER_API_KEY = "cache_api_key"
CONF_CACHE_SERVER_USER_ID = "cache_user_id"


DEFAULT_SERVER_NAME = "Media Browser"
DEFAULT_CLIENT_NAME = "Home Assistant"
DEFAULT_DEVICE_NAME = "Hub"
DEFAULT_DEVICE_VERSION = "1.0.0.0"
DEFAULT_REQUEST_TIMEOUT = 5
DEFAULT_IGNORE_WEB_PLAYERS = False
DEFAULT_IGNORE_DLNA_PLAYERS = False
DEFAULT_IGNORE_MOBILE_PLAYERS = False
DEFAULT_IGNORE_APP_PLAYERS = False
DEFAULT_PURGE_PLAYERS = False
DEFAULT_UPCOMING_MEDIA = False
DEFAULT_PORT = 8096
DEFAULT_SSL_PORT = 8920
DEFAULT_USE_SSL = False


DATA_HUB = "hub"
DATA_POLL_COORDINATOR = "poll_coordinator"

DISCOVERY_TIMEOUT = 1
DISCOVERY_MESSAGE_EMBY = b"who is EmbyServer?"
DISCOVERY_MESSAGE_JELLYFIN = b"who is JellyfinServer?"
DISCOVERY_BROADCAST = "255.255.255.255"
DISCOVERY_PORT = 7359

KEEP_ALIVE_TIMEOUT = 59


class ServerType(StrEnum):
    """MediaBrowser server types"""

    EMBY = "emby"
    JELLYFIN = "jellyfin"
    UNKNOWN = "unknown"


class Manufacturer(StrEnum):
    """MediaBrowser manufacturers"""

    EMBY = "Emby LLC"
    JELLYFIN = "Jellyfin"
    UNKNOWN = "Unknown"


MANUFACTURER_MAP = {
    ServerType.EMBY: Manufacturer.EMBY,
    ServerType.JELLYFIN: Manufacturer.JELLYFIN,
}

DASHBOARD_MAP = {
    ServerType.EMBY: "/web/index.html#!/dashboard",
    ServerType.JELLYFIN: "/web/index.html#!/dashboard",
}


class ApiUrl(StrEnum):
    """MediaBrowser URLs"""

    ALBUM_ARTISTS = "/AlbumArtists"
    ARTISTS = "/Artists"
    AUTH_KEYS = "/Auth/Keys"
    AUTHENTICATE = "/Users/AuthenticateByName"
    CHANNELS = "/Channels"
    COMMAND = "/Command"
    GENRES = "/Genres"
    INFO = "/System/Info/Public"
    ITEMS = "/Items"
    LIBRARIES = "/Library/MediaFolders"
    LIBRARY_REFRESH = "/Library/Refresh"
    PERSONS = "/Persons"
    PING = "/System/Ping"
    PLAYBACK_INFO = "/PlaybackInfo"
    PLAYING = "/Playing"
    PREFIXES = "/Items/Prefixes"
    RESTART = "/System/Restart"
    SEASONS = "/Seasons"
    SESSIONS = "/Sessions"
    SHOWS = "/Shows"
    SHUTDOWN = "/System/Shutdown"
    STUDIOS = "/Studios"
    TAGS = "/Tags"
    TEST_API_KEY = "/Auth/Keys"
    USERS = "/Users"
    YEARS = "/Years"


class Key(StrEnum):
    """Key used across library"""

    ACCEPT = "Accept"
    ADDRESS = "Address"
    ALBUM = "Album"
    ALBUM_ARTIST = "AlbumArtist"
    ALBUM_ARTISTS = "AbumArtists"
    ALBUM_ID = "AlbumId"
    ALBUM_PRIMARY_IMAGE_TAG = "AlbumPrimaryImageTag"
    ALL = "(all)"
    APP_ICON_URL = "AppIconUrl"
    APPLICATION_VERSION = "ApplicationVersion"
    ART = "Art"
    ARTIST_ITEMS = "ArtistItems"
    ARTIST_TYPE = "ArtistType"
    ARTISTS = "Artists"
    AUTHORIZATION = "x-emby-authorization"
    BACKDROP = "Backdrop"
    BACKDROP_IMAGE_TAGS = "BackdropImageTags"
    BITRATE = "Bitrate"
    CAN_SEEK = "CanSeek"
    CHANNEL = "Channel"
    CHANNEL_ID = "ChannelId"
    CHANNEL_NAME = "ChannelName"
    CHANNEL_PRIMARY_IMAGE_TAG = "ChannelPrimaryImageTag"
    CHILD_COUNT = "ChildCount"
    CLIENT = "Client"
    COLLECTION_TYPE = "CollectionType"
    COMMUNITY_RATING = "CommunityRating"
    CONTAINER = "Container"
    CONTENT_TYPE = "Content-Type"
    CRITIC_RATING = "CriticRating"
    DATA = "Data"
    DATE_CREATED = "DateCreated"
    DEVICE = "Device"
    DEVICE_ID = "DeviceId"
    DEVICE_NAME = "DeviceName"
    ENABLE_ALL_FOLDERS = "EnableAllFolders"
    EPISODE_TITLE = "EpisodeTitle"
    FILENAME = "Filename"
    GENRE_ITEMS = "GenreItems"
    GENRES = "Genres"
    ID = "Id"
    INDEX_NUMBER = "IndexNumber"
    IS_ACTIVE = "IsActive"
    IS_ADMINISTRATOR = "IsAdministrator"
    IS_DISABLED = "IsDisabled"
    IS_FOLDER = "IsFolder"
    IS_MUTED = "IsMuted"
    IS_PAUSED = "IsPaused"
    IMAGE_TAGS = "ImageTags"
    ITEMS = "Items"
    LAST_ACTIVITY_DATE = "LastActivityDate"
    LIST_ITEM_ORDER = "ListItemOrder"
    LOCAL_ADDRESS = "LocalAddress"
    LOGO = "Logo"
    MBCLIENT = "MediaBrowserClient"
    MEDIA_SOURCE_ID = "MediaSourceId"
    MEDIA_SOURCES = "MediaSources"
    MEDIA_TYPE = "MediaType"
    MESSAGE_TYPE = "MessageType"
    NAME = "Name"
    NOW_PLAYING_ITEM = "NowPlayingItem"
    OFFICIAL_RATING = "OfficialRating"
    OPERATING_SYSTEM = "OperatingSystem"
    OVERVIEW = "Overview"
    PARENT = "Parent"
    PARENT_ART_IMAGE_TAG = "ParentArtImageTag"
    PARENT_ART_ITEM_ID = "ParentArtItemId"
    PARENT_BACKDROP_IMAGE_TAGS = "ParentBackdropImageTags"
    PARENT_BACKDROP_ITEM_ID = "ParentBackdropItemId"
    PARENT_ID = "ParentId"
    PARENT_INDEX_NUMBER = "ParentIndexNumber"
    PARENT_LOGO_IMAGE_TAG = "ParentLogoImageTag"
    PARENT_LOGO_ITEM_ID = "ParentLogoItemId"
    PARENT_PRIMARY_IMAGE_TAG = "ParentPrimaryImageTag"
    PARENT_PRIMARY_IMAGE_ITEM_ID = "ParentPrimaryImageItemId"
    PARENT_THUMB_IMAGE_TAG = "ParentThumbImageTag"
    PARENT_THUMB_ITEM_ID = "ParentThumbItemId"
    PATH = "Path"
    POLICY = "Policy"
    PLAY_STATE = "PlayState"
    PLAYABLE_MEDIA_TYPES = "PlayableMediaTypes"
    PLAYLIST_INDEX = "PlaylistIndex"
    PLAYLIST_LENGTH = "PlaylistLength"
    PREMIERE_DATE = "PremiereDate"
    PRODUCTION_YEAR = "ProductionYear"
    POSITION_TICKS = "PositionTicks"
    PRIMARY = "Primary"
    REMOTE_END_POINT = "RemoteEndPoint"
    SERIES_ID = "SeriesId"
    SERIES_THUMB_IMAGE_TAG = "SeriesThumbImageTag"
    REPEAT_MODE = "RepeatMode"
    RUNTIME_TICKS = "RunTimeTicks"
    SCREENSHOT = "Screenshot"
    SCREENSHOT_IMAGE_TAGS = "ScreenshotImageTags"
    SORT_NAME = "SortName"
    SEASON_NAME = "SeasonName"
    SERIES = "Series"
    SERIES_NAME = "SeriesName"
    SERIES_PRIMARY_IMAGE_TAG = "SeriesPrimaryImageTag"
    SERVER_NAME = "ServerName"
    STUDIOS = "Studios"
    SUPPORTED_COMMANDS = "SupportedCommands"
    SUPPORTS_DIRECT_STREAM = "SupportsDirectStream"
    SUPPORTS_MEDIA_CONTROL = "SupportsMediaControl"
    SUPPORTS_REMOTE_CONTROL = "SupportsRemoteControl"
    SUPPORTS_TRANSCODING = "SupportsTranscoding"
    TAGLINES = "Taglines"
    TOTAL_RECORD_COUNT = "TotalRecordCount"
    TRANSCODING_CONTAINER = "TranscodingContainer"
    TRANSCODING_URL = "TranscodingUrl"
    TYPE = "Type"
    THUMB = "Thumb"
    USER_NAME = "UserName"
    VERSION = "Version"
    VOLUME_LEVEL = "VolumeLevel"


class Query(StrEnum):
    """Query parameters"""

    ARTIST_TYPE = "ArtistType"
    GROUP_ITEMS_INTO_COLLECTIONS = "GroupItemsIntoCollections"
    FIELDS = "Fields"
    IDS = "Ids"
    IS_HIDDEN = "isHidden"
    IS_VIRTUAL_ITEM = "IsVirtualItem"
    INCLUDE_ITEM_TYPES = "IncludeItemTypes"
    LIMIT = "Limit"
    NAME_STARTS_WITH = "NameStartsWith"
    PARENT_ID = "ParentId"
    RECURSIVE = "Recursive"
    SORT_BY = "SortBy"
    SORT_ORDER = "SortOrder"


class Value(StrEnum):
    """Values for query parameters"""

    ASCENDING = "Ascending"
    APPLICATION_JSON = "application/json"
    ARTIST = "Artist"
    ALBUM_ARTIST = "AlbumArtist"
    COMPOSER = "Composer"
    DESCENDING = "Descending"
    FALSE = "false"
    MEDIA_SOURCES = "MediaSources"
    TRUE = "true"


class ItemType(StrEnum):
    """Item types"""

    AUDIO = "Audio"
    AUDIO_BOOK = "AudioBook"
    ARTIST = "Artist"
    BOOK = "Book"
    BOXSET = "BoxSet"
    CHANNEL = "Channel"
    EPISODE = "Episode"
    GENRE = "Genre"
    LIVE_TV_CHANNEL = "LiveTvChannel"
    LIVE_TV_PROGRAM = "LiveTVProgram"
    MANUAL_PLAYLIST_FOLDER = "ManualPlaylistFolder"
    MOVIE = "Movie"
    MUSIC_ALBUM = "MusicAlbum"
    MUSIC_ARTIST = "MusicArtist"
    MUSIC_GENRE = "MusicGenre"
    MUSIC_VIDEO = "MusicVideo"
    PERSON = "Person"
    PHOTO = "Photo"
    PHOTO_ALBUM = "PhotoAlbum"
    PLAYLIST = "Playlist"
    PLAYLIST_FOLDER = "PlaylistFolder"
    PROGRAM = "Program"
    RECORDING = "Recording"
    SEASON = "Season"
    SERIES = "Series"
    STUDIO = "Studio"
    VIDEO = "Video"
    TAG = "Tag"
    TRAILER = "Trailer"
    TV_CHANNEL = "TvChannel"
    TV_PROGRAM = "TvProgram"


class VirtualFolder(StrEnum):
    """Custom virtual folders"""

    ALBUM_ARTISTS = "album_artists"
    ARTISTS = "artists"
    PERSONS = "persons"
    COMPOSERS = "composers"
    FOLDERS = "folders"
    GENRES = "genres"
    PHOTOS = "photos"
    PLAYLISTS = "playlists"
    PREFIXES = "prefixes"
    STUDIOS = "studios"
    TAGS = "tags"
    VIDEOS = "videos"
    YEARS = "years"


class ImageType(StrEnum):
    """Image types."""

    PRIMARY = "Primary"
    BACKDROP = "Backdrop"
    ART = "Art"
    THUMB = "Thumb"
    BANNER = "Banner"
    LOGO = "Logo"
    DISC = "Disc"
    BOX = "Box"
    SCREENSHOT = "Screenshot"
    MENU = "Menu"
    CHAPTER = "Chapter"
    BOX_REAR = "BoxRear"
    PROFILE = "Profile"


class ImageCategory(StrEnum):
    """Image caetgories"""

    PARENT = "Parent"
    ALBUM = "Album"
    SERIES = "Series"
    CHANNEL = "Channel"


class EntityType(StrEnum):
    """Suffixes for unique ids"""

    LIBRARY = "library"
    PLAYER = "player"
    RESCAN = "rescan"
    RESTART = "restart"
    SESSIONS = "sessions"
    SHUTDOWN = "shutdown"


ENTITY_TITLE_MAP = {
    EntityType.RESCAN: "Rescan Libraries",
    EntityType.RESTART: "Restart",
    EntityType.SESSIONS: "Sessions",
    EntityType.SHUTDOWN: "Shutdown",
}

VIRTUAL_FOLDER_MAP: dict[str, str] = {
    VirtualFolder.ARTISTS: "By Artist",
    VirtualFolder.ALBUM_ARTISTS: "By Album Artist",
    VirtualFolder.PERSONS: "By Actor",
    VirtualFolder.COMPOSERS: "By Composer",
    VirtualFolder.GENRES: "By Genre",
    VirtualFolder.STUDIOS: "By Studio",
    VirtualFolder.PREFIXES: "By Letter",
    VirtualFolder.YEARS: "By Year",
    VirtualFolder.TAGS: "Tags",
    VirtualFolder.FOLDERS: "Folders",
    VirtualFolder.VIDEOS: "Videos",
    VirtualFolder.PHOTOS: "Photos",
    VirtualFolder.PLAYLISTS: "Playlists",
}


MEDIA_CLASS_MAP: dict[str, MediaClass] = {
    ItemType.AUDIO: MediaClass.TRACK,
    ItemType.AUDIO_BOOK: MediaClass.ALBUM,
    ItemType.ARTIST: MediaClass.ARTIST,
    ItemType.BOOK: MediaClass.APP,
    ItemType.CHANNEL: MediaClass.CHANNEL,
    ItemType.EPISODE: MediaClass.EPISODE,
    ItemType.GENRE: MediaClass.GENRE,
    ItemType.LIVE_TV_CHANNEL: MediaClass.CHANNEL,
    ItemType.LIVE_TV_PROGRAM: MediaClass.VIDEO,
    ItemType.MOVIE: MediaClass.MOVIE,
    ItemType.MUSIC_ALBUM: MediaClass.ALBUM,
    ItemType.MUSIC_ARTIST: MediaClass.ARTIST,
    ItemType.MUSIC_GENRE: MediaClass.GENRE,
    ItemType.MUSIC_VIDEO: MediaClass.VIDEO,
    ItemType.PERSON: MediaClass.ARTIST,
    ItemType.PHOTO: MediaClass.IMAGE,
    ItemType.PHOTO_ALBUM: MediaClass.ALBUM,
    ItemType.PROGRAM: MediaClass.VIDEO,
    ItemType.PLAYLIST: MediaClass.PLAYLIST,
    ItemType.RECORDING: MediaClass.VIDEO,
    ItemType.STUDIO: MediaClass.GENRE,
    ItemType.SEASON: MediaClass.SEASON,
    ItemType.SERIES: MediaClass.TV_SHOW,
    ItemType.TRAILER: MediaClass.VIDEO,
    ItemType.TV_CHANNEL: MediaClass.CHANNEL,
    ItemType.TV_PROGRAM: MediaClass.VIDEO,
    ItemType.VIDEO: MediaClass.VIDEO,
}

MEDIA_TYPE_MAP: dict[str, MediaType] = {
    ItemType.AUDIO: MediaType.TRACK,
    ItemType.AUDIO_BOOK: MediaType.MUSIC,
    ItemType.ARTIST: MediaType.ARTIST,
    ItemType.BOOK: MediaType.APP,
    ItemType.CHANNEL: MediaType.CHANNEL,
    ItemType.EPISODE: MediaType.EPISODE,
    ItemType.GENRE: MediaType.GENRE,
    ItemType.LIVE_TV_CHANNEL: MediaType.CHANNEL,
    ItemType.LIVE_TV_PROGRAM: MediaType.VIDEO,
    ItemType.MOVIE: MediaType.MOVIE,
    ItemType.MUSIC_ALBUM: MediaType.ALBUM,
    ItemType.MUSIC_ARTIST: MediaType.ARTIST,
    ItemType.MUSIC_GENRE: MediaType.GENRE,
    ItemType.MUSIC_VIDEO: MediaType.VIDEO,
    ItemType.PERSON: MediaType.ARTIST,
    ItemType.PHOTO: MediaType.IMAGE,
    ItemType.PHOTO_ALBUM: MediaType.ALBUM,
    ItemType.PROGRAM: MediaType.VIDEO,
    ItemType.PLAYLIST: MediaType.PLAYLIST,
    ItemType.RECORDING: MediaType.VIDEO,
    ItemType.SEASON: MediaType.SEASON,
    ItemType.SERIES: MediaType.TVSHOW,
    ItemType.STUDIO: MediaType.GENRE,
    ItemType.TRAILER: MediaType.VIDEO,
    ItemType.TV_CHANNEL: MediaType.CHANNEL,
    ItemType.TV_PROGRAM: MediaType.VIDEO,
    ItemType.VIDEO: MediaType.VIDEO,
}

MEDIA_CLASS_NONE = ""
MEDIA_TYPE_NONE = ""
TYPE_NONE = ""
TITLE_NONE = ""
ID_NONE = ""


PLAYABLE_FOLDERS = {
    ItemType.BOXSET,
    ItemType.GENRE,
    ItemType.LIVE_TV_CHANNEL,
    ItemType.MANUAL_PLAYLIST_FOLDER,
    ItemType.MUSIC_ALBUM,
    ItemType.MUSIC_GENRE,
    ItemType.PHOTO_ALBUM,
    ItemType.PLAYLIST,
    ItemType.PLAYLIST_FOLDER,
    ItemType.SEASON,
    ItemType.SERIES,
}

UPCOMING_SENSOR_DEFAULT = {
    "title_default": "$title",
    "line1_default": "$episode",
    "line2_default": "$release",
    "line3_default": "$rating - $runtime",
    "line4_default": "$number - $studio",
    "icon": "mdi:new-box",
}

UPCOMING_SENSOR_SERIES = {
    "title_default": "$title",
    "line1_default": "$episode",
    "line2_default": "$release",
    "line3_default": "$rating - $runtime",
    "line4_default": "$number - $studio",
    "icon": "mdi:new-box",
}

UPCOMING_SENSOR_MOVIE = {
    "title_default": "$title",
    "line1_default": "$release",
    "line2_default": "$genres",
    "line3_default": "$rating - $runtime",
    "line4_default": "$studio",
    "icon": "mdi:new-box",
}


SENSOR_ITEM_TYPES = {
    ItemType.MOVIE: {
        "title": "Movies",
        "icon": "mdi:movie",
        "upcoming": UPCOMING_SENSOR_MOVIE,
    },
    ItemType.EPISODE: {
        "title": "Episodes",
        "icon": "mdi:movie",
        "upcoming": UPCOMING_SENSOR_SERIES,
    },
    ItemType.SERIES: {
        "title": "Series",
        "icon": "mdi:movie",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.SEASON: {
        "title": "Seasons",
        "icon": "mdi:movie",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.AUDIO: {
        "title": "Music",
        "icon": "mdi:music",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.BOOK: {
        "title": "Books",
        "icon": "mdi:book",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.MUSIC_VIDEO: {
        "title": "Music Videos",
        "icon": "mdi:video-account",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.PHOTO: {
        "title": "Photos",
        "icon": "mdi:image",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.VIDEO: {
        "title": "Videos",
        "icon": "mdi:video",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.TRAILER: {
        "title": "Trailers",
        "icon": "mdi:movie-filter",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.GENRE: {
        "title": "Genres",
        "icon": "mdi:multimedia",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.MUSIC_ALBUM: {
        "title": "Music Albums",
        "icon": "mdi:music",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.MUSIC_ARTIST: {
        "title": "Music Artists",
        "icon": "mdi:account-music",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.MUSIC_GENRE: {
        "title": "Music Genres",
        "icon": "mdi:multimedia",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.PERSON: {
        "title": "Persons",
        "icon": "mdi:acount",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.PHOTO_ALBUM: {
        "title": "Photo Albums",
        "icon": "mdi:image",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.PLAYLIST: {
        "title": "Playlists",
        "icon": "mdi:playlist-play",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.STUDIO: {
        "title": "Studios",
        "icon": "mdi:domain",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.TV_CHANNEL: {
        "title": "TV Channels",
        "icon": "mdi:television",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.LIVE_TV_CHANNEL: {
        "title": "Live TV Channels",
        "icon": "mdi:television",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
    ItemType.LIVE_TV_PROGRAM: {
        "title": "Live TV Program",
        "icon": "mdi:television",
        "upcoming": UPCOMING_SENSOR_DEFAULT,
    },
}

DEFAULT_SENSORS = [
    {
        CONF_SENSOR_USER: Key.ALL,
        CONF_SENSOR_LIBRARY: Key.ALL,
        CONF_SENSOR_ITEM_TYPE: ItemType.MOVIE,
    },
    {
        CONF_SENSOR_USER: Key.ALL,
        CONF_SENSOR_LIBRARY: Key.ALL,
        CONF_SENSOR_ITEM_TYPE: ItemType.EPISODE,
    },
    {
        CONF_SENSOR_USER: Key.ALL,
        CONF_SENSOR_LIBRARY: Key.ALL,
        CONF_SENSOR_ITEM_TYPE: ItemType.AUDIO,
    },
]

TICKS_PER_SECOND = 10000000
TICKS_PER_MINUTE = TICKS_PER_SECOND * 60


LATEST_QUERY_FIELDS = {
    Key.ALBUM_ID,
    Key.ALBUM_PRIMARY_IMAGE_TAG,
    Key.ARTISTS,
    Key.BACKDROP_IMAGE_TAGS,
    Key.CHANNEL_PRIMARY_IMAGE_TAG,
    Key.COMMUNITY_RATING,
    Key.CRITIC_RATING,
    Key.DATE_CREATED,
    Key.GENRES,
    Key.IMAGE_TAGS,
    Key.INDEX_NUMBER,
    Key.OFFICIAL_RATING,
    Key.OVERVIEW,
    Key.PARENT_ART_IMAGE_TAG,
    Key.PARENT_ART_ITEM_ID,
    Key.PARENT_BACKDROP_IMAGE_TAGS,
    Key.PARENT_BACKDROP_ITEM_ID,
    Key.PARENT_ID,
    Key.PARENT_LOGO_IMAGE_TAG,
    Key.PARENT_INDEX_NUMBER,
    Key.PARENT_PRIMARY_IMAGE_ITEM_ID,
    Key.PARENT_PRIMARY_IMAGE_TAG,
    Key.PARENT_THUMB_IMAGE_TAG,
    Key.PARENT_THUMB_ITEM_ID,
    Key.PREMIERE_DATE,
    Key.PRODUCTION_YEAR,
    Key.RUNTIME_TICKS,
    Key.SEASON_NAME,
    Key.SCREENSHOT_IMAGE_TAGS,
    Key.SERIES_ID,
    Key.SERIES_NAME,
    Key.SERIES_PRIMARY_IMAGE_TAG,
    Key.SERIES_THUMB_IMAGE_TAG,
    Key.STUDIOS,
    Key.TAGLINES,
}

LATEST_QUERY_SORT_BY = [Key.DATE_CREATED, Key.SORT_NAME, Key.PRODUCTION_YEAR]
LATEST_QUERY_SORT_ORDER = [Value.DESCENDING, Value.ASCENDING, Value.DESCENDING]
LATEST_QUERY_PARAMS: dict[str, Any] = {
    Query.RECURSIVE: Value.TRUE,
    Query.IS_VIRTUAL_ITEM: Value.FALSE,
    Query.GROUP_ITEMS_INTO_COLLECTIONS: Value.FALSE,
    Query.SORT_BY: ",".join(LATEST_QUERY_SORT_BY),
    Query.SORT_ORDER: ",".join(LATEST_QUERY_SORT_ORDER),
    Query.FIELDS: ",".join(LATEST_QUERY_FIELDS),
    Query.LIMIT: 5,
}

VIRTUAL_FILTER_MAP = {
    VirtualFolder.ARTISTS: "ArtistIds",
    VirtualFolder.COMPOSERS: "ArtistIds",
    VirtualFolder.ALBUM_ARTISTS: "ArtistIds",
    VirtualFolder.PERSONS: "PersonIds",
    VirtualFolder.GENRES: "GenreIds",
    VirtualFolder.STUDIOS: "StudioIds",
    VirtualFolder.TAGS: "TagIds",
    VirtualFolder.YEARS: "Years",
}

DEVICE_PROFILE = {
    "MaxStaticBitrate": 140000000,
    "MaxStreamingBitrate": 140000000,
    "MusicStreamingTranscodingBitrate": 384000,
    "DirectPlayProfiles": [
        {"Container": "aac", "Type": "Audio"},
        {"Container": "aac", "Type": "Audio", "AudioCodec": "aac"},
        {
            "Container": "flv",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac,mp3",
        },
        {"Container": "flac", "Type": "Audio"},
        {"Container": "m4a", "AudioCodec": "aac", "Type": "Audio"},
        {"Container": "m4b", "AudioCodec": "aac", "Type": "Audio"},
        {
            "Container": "mkv",
            "Type": "Video",
            "VideoCodec": "h264,h265,hevc,av1,vp8,vp9",
            "AudioCodec": "mp3,aac,opus,flac,vorbis",
        },
        {
            "Container": "mov",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "mp3,aac,opus,flac,vorbis",
        },
        {"Container": "mp2,mp3", "Type": "Audio", "AudioCodec": "mp2"},
        {"Container": "mp3", "Type": "Audio"},
        {"Container": "mp3", "Type": "Audio", "AudioCodec": "mp3"},
        {"Container": "mp4", "AudioCodec": "aac", "Type": "Audio"},
        {
            "Container": "mp4,m4v",
            "Type": "Video",
            "VideoCodec": "h264,h265,hevc,av1,vp8,vp9",
            "AudioCodec": "mp3,aac,opus,flac,vorbis",
        },
        {"Container": "ogg", "Type": "Audio"},
        {"Container": "opus", "Type": "Audio"},
        {"Container": "wav", "Type": "Audio"},
        {"Container": "wav", "Type": "Audio", "AudioCodec": "PCM_S16LE,PCM_S24LE"},
        {"Container": "webma,webm", "Type": "Audio"},
        {"Container": "webm", "AudioCodec": "webma", "Type": "Audio"},
        {"Container": "webm", "AudioCodec": "opus", "Type": "Audio"},
        {
            "Container": "webm",
            "Type": "Video",
            "AudioCodec": "vorbis,opus",
            "VideoCodec": "av1,vp8,vp9",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "aac",
            "Type": "Audio",
            "AudioCodec": "aac",
            "Context": "Streaming",
            "Protocol": "hls",
            "MaxAudioChannels": "2",
            "MinSegments": "1",
            "BreakOnNonKeyFrames": True,
        },
        {
            "Container": "aac",
            "Type": "Audio",
            "AudioCodec": "aac",
            "Context": "Streaming",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "aac",
            "Type": "Audio",
            "AudioCodec": "aac",
            "Context": "Static",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "m4s,ts",
            "Type": "Video",
            "AudioCodec": "mp3,aac",
            "VideoCodec": "h264,h265,hevc",
            "Context": "Streaming",
            "Protocol": "hls",
            "MaxAudioChannels": "2",
            "MinSegments": "1",
            "BreakOnNonKeyFrames": True,
            "ManifestSubtitles": "vtt",
        },
        {
            "Container": "mkv",
            "Type": "Video",
            "AudioCodec": "mp3,aac,opus,flac,vorbis",
            "VideoCodec": "h264,h265,hevc,av1,vp8,vp9",
            "Context": "Static",
            "MaxAudioChannels": "2",
            "CopyTimestamps": True,
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Static",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "mp4",
            "Type": "Video",
            "AudioCodec": "mp3,aac,opus,flac,vorbis",
            "VideoCodec": "h264",
            "Context": "Static",
            "Protocol": "http",
        },
        {
            "Container": "opus",
            "Type": "Audio",
            "AudioCodec": "opus",
            "Context": "Streaming",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "opus",
            "Type": "Audio",
            "AudioCodec": "opus",
            "Context": "Static",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "wav",
            "Type": "Audio",
            "AudioCodec": "wav",
            "Context": "Streaming",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "wav",
            "Type": "Audio",
            "AudioCodec": "wav",
            "Context": "Static",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "webm",
            "Type": "Video",
            "AudioCodec": "vorbis",
            "VideoCodec": "vpx",
            "Context": "Streaming",
            "Protocol": "http",
            "MaxAudioChannels": "2",
        },
        {
            "Container": "ts",
            "Type": "Audio",
            "AudioCodec": "aac",
            "Context": "Streaming",
            "Protocol": "hls",
            "MaxAudioChannels": "2",
            "MinSegments": "1",
            "BreakOnNonKeyFrames": True,
        },
        {
            "Container": "ts",
            "Type": "Video",
            "AudioCodec": "aac,mp3",
            "VideoCodec": "h264",
            "Context": "Streaming",
            "Protocol": "hls",
            "MaxAudioChannels": "2",
            "MinSegments": "1",
            "BreakOnNonKeyFrames": True,
        },
    ],
    "ContainerProfiles": [],
    "CodecProfiles": [
        {
            "Type": "VideoAudio",
            "Codec": "aac",
            "Conditions": [
                {
                    "Condition": "Equals",
                    "Property": "IsSecondaryAudio",
                    "Value": "false",
                    "IsRequired": False,
                }
            ],
        },
        {
            "Type": "VideoAudio",
            "Conditions": [
                {
                    "Condition": "Equals",
                    "Property": "IsSecondaryAudio",
                    "Value": "false",
                    "IsRequired": False,
                }
            ],
        },
        {
            "Type": "Video",
            "Codec": "h264",
            "Conditions": [
                {
                    "Condition": "NotEquals",
                    "Property": "IsAnamorphic",
                    "Value": "true",
                    "IsRequired": False,
                },
                {
                    "Condition": "NotEquals",
                    "Property": "IsAnamorphic",
                    "Value": "true",
                    "IsRequired": False,
                },
                {
                    "Condition": "EqualsAny",
                    "Property": "VideoProfile",
                    "Value": "high|main|baseline|constrained baseline|high 10",
                    "IsRequired": False,
                },
                {
                    "Condition": "EqualsAny",
                    "Property": "VideoRangeType",
                    "Value": "SDR",
                    "IsRequired": False,
                },
                {
                    "Condition": "LessThanEqual",
                    "Property": "VideoLevel",
                    "Value": "52",
                    "IsRequired": False,
                },
                {
                    "Condition": "NotEquals",
                    "Property": "IsInterlaced",
                    "Value": "true",
                    "IsRequired": False,
                },
            ],
        },
        {
            "Type": "Video",
            "Codec": "hevc",
            "Conditions": [
                {
                    "Condition": "NotEquals",
                    "Property": "IsAnamorphic",
                    "Value": "true",
                    "IsRequired": False,
                },
                {
                    "Condition": "EqualsAny",
                    "Property": "VideoProfile",
                    "Value": "main|main 10",
                    "IsRequired": False,
                },
                {
                    "Condition": "EqualsAny",
                    "Property": "VideoRangeType",
                    "Value": "SDR",
                    "IsRequired": False,
                },
                {
                    "Condition": "LessThanEqual",
                    "Property": "VideoLevel",
                    "Value": "183",
                    "IsRequired": False,
                },
                {
                    "Condition": "NotEquals",
                    "Property": "IsInterlaced",
                    "Value": "true",
                    "IsRequired": False,
                },
            ],
        },
        {
            "Type": "Video",
            "Codec": "vp9",
            "Conditions": [
                {
                    "Condition": "EqualsAny",
                    "Property": "VideoRangeType",
                    "Value": "SDR|HDR10|HLG",
                    "IsRequired": False,
                }
            ],
        },
        {
            "Type": "Video",
            "Codec": "av1",
            "Conditions": [
                {
                    "Condition": "EqualsAny",
                    "Property": "VideoRangeType",
                    "Value": "SDR|HDR10|HLG",
                    "IsRequired": False,
                }
            ],
        },
    ],
    "SubtitleProfiles": [
        {"Format": "vtt", "Method": "Hls"},
        {"Format": "eia_608", "Method": "VideoSideData", "Protocol": "hls"},
        {"Format": "eia_708", "Method": "VideoSideData", "Protocol": "hls"},
        {"Format": "vtt", "Method": "External"},
        {"Format": "ass", "Method": "External"},
        {"Format": "ssa", "Method": "External"},
    ],
    "ResponseProfiles": [
        {"Type": "Video", "Container": "m4v", "MimeType": "video/mp4"}
    ],
}
