"""Constants for the Media Browser (Emby/Jellyfin) integration."""

from datetime import timedelta

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
CONF_UNIQUE_ID = "unique_id"

CONF_LATEST_MOVIES = "latest_movies"
CONF_LATEST_SERIES = "latest_series"
CONF_LATEST_SONGS = "latest_songs"
CONF_LATEST_VIDEOS = "latest_videos"
CONF_LATEST_BOOKS = "latest_books"
CONF_LATEST_TRAILERS = "latest_trailers"
CONF_LATEST_MUSIC_VIDEOS = "latest_music_videos"
CONF_LATEST_PHOTOS = "latest_photos"

CONF_USER = "user"


DEFAULT_SERVER_NAME = "Media Browser"
DEFAULT_CLIENT_NAME = "Home Assistant"
DEFAULT_DEVICE_NAME = "Hub"
DEFAULT_DEVICE_VERSION = "1.0.0.0"
DEFAULT_REQUEST_TIMEOUT = 5


HUB = "hub"
POLL_COORDINATOR = "poll_coordinator"
PUSH_COORDINATOR = "push_coordinator"

HUB_INFO_ID = "Id"
HUB_INFO_NAME = "ServerName"
HUB_INFO_VERSION = "Version"
HUB_INFO_OS = "OperatingSystem"
HUB_INFO_URL = "LocalAddress"
HUB_ITEMS_ID = "Id"
HUB_ITEMS = "Items"
HUB_ITEMS_COUNT = "TotalRecordCount"


HUB_PARAM_PARENT_ID = "ParentId"
HUB_PARAM_INCLUDE_ITEM_TYPES = "IncludeItemTypes"
HUB_PARAM_ASCENDING = "Ascending"
HUB_PARAM_DESCENDING = "Descending"
HUB_PARAM_LIMIT = "Limit"
HUB_PARAM_RECURSIVE = "Recursive"
HUB_PARAM_SORT_ORDER = "SortOrder"
HUB_PARAM_SORT_DATE = "DateCreated"
HUB_PARAM_TRUE = "true"


UPDATE_INTERVAL = timedelta(seconds=30)

PING_ID_EMBY = "emby"
PING_ID_JELLYFIN = "jellyfin"

MANUFACTURER_EMBY = "Emby LLC"
MANUFACTURER_JELLYFIN = "Jellyfin"
MANUFACTURER_UNKNOWN = "Unknown"

DASHBOARD_EMBY = "/web/index.html#!/dashboard"
DASHBOARD_JELLYFIN = "/web/index.html#!/dashboard.html"

SESSION_NOW_PLAYING_ITEM = "NowPlayingItem"
SESSION_ID = "Id"
SESSION_CLIENT = "Client"
SESSION_DEVICE_NAME = "DeviceName"

ITEM_NAME = "Name"
ITEM_COLLECTION_TYPE = "CollectionType"


VIRTUAL_FOLDER_MAP = {
    "artists": "By Artist",
    "album_artists": "By Album Artist",
    "persons": "By Actor",
    "composers": "By Composer",
    "genres": "By Genre",
    "studios": "By Studio",
    "prefixes": "By Letter",
    "years": "By Year",
    "tags": "Tags",
    "folders": "Folders",
    "videos": "Videos",
    "photos": "Photos",
    "playlists": "Playlists",
}


MEDIA_CLASS_MAP = {
    "AggregateFolder": MediaClass.DIRECTORY,
    "Audio": MediaClass.TRACK,
    "AudioBook": MediaClass.ALBUM,
    "Artist": MediaClass.ARTIST,
    "BasePluginFolder": MediaClass.DIRECTORY,
    "BoxSet": MediaClass.DIRECTORY,
    "Book": MediaClass.APP,
    "Channel": MediaClass.CHANNEL,
    "ChannelFolderItem": MediaClass.DIRECTORY,
    "CollectionFolder": MediaClass.DIRECTORY,
    "Episode": MediaClass.EPISODE,
    "Folder": MediaClass.DIRECTORY,
    "Genre": MediaClass.GENRE,
    "LiveTvChannel": MediaClass.CHANNEL,
    "LiveTvProgram": MediaClass.VIDEO,
    "ManualPlaylistFolder": MediaClass.DIRECTORY,
    "Movie": MediaClass.MOVIE,
    "MusicAlbum": MediaClass.ALBUM,
    "MusicArtist": MediaClass.ARTIST,
    "MusicGenre": MediaClass.GENRE,
    "MusicVideo": MediaClass.VIDEO,
    "Person": MediaClass.ARTIST,
    "Photo": MediaClass.IMAGE,
    "PhotoAlbum": MediaClass.ALBUM,
    "Prefix": MediaClass.DIRECTORY,
    "Program": MediaClass.VIDEO,
    "Playlist": MediaClass.PLAYLIST,
    "PlaylistFolder": MediaClass.DIRECTORY,
    "Recording": MediaClass.VIDEO,
    "Season": MediaClass.SEASON,
    "Series": MediaClass.TV_SHOW,
    "Studio": MediaClass.DIRECTORY,
    "Virtual": MediaClass.DIRECTORY,
    "Trailer": MediaClass.VIDEO,
    "Tag": MediaClass.DIRECTORY,
    "TvChannel": MediaClass.CHANNEL,
    "TvProgram": MediaClass.VIDEO,
    "UserRootFolder": MediaClass.DIRECTORY,
    "UserView": MediaClass.DIRECTORY,
    "Video": MediaClass.VIDEO,
    "Year": MediaClass.DIRECTORY,
}

MEDIA_TYPE_MAP = {
    "AggregateFolder": MediaType.PLAYLIST,
    "Audio": MediaType.TRACK,
    "AudioBook": MediaType.MUSIC,
    "Artist": MediaType.ARTIST,
    "BasePluginFolder": MediaType.PLAYLIST,
    "Book": MediaType.APP,
    "BoxSet": MediaType.PLAYLIST,
    "Channel": MediaType.CHANNEL,
    "ChannelFolderItem": MediaType.CHANNELS,
    "CollectionFolder": MediaType.PLAYLIST,
    "Episode": MediaType.EPISODE,
    "Folder": MediaType.PLAYLIST,
    "Genre": MediaType.GENRE,
    "LiveTvChannel": MediaType.CHANNEL,
    "LiveTvProgram": MediaType.VIDEO,
    "ManualPlaylistsFolder": MediaType.PLAYLIST,
    "Movie": MediaType.MOVIE,
    "MusicAlbum": MediaType.ALBUM,
    "MusicArtist": MediaType.ARTIST,
    "MusicGenre": MediaType.GENRE,
    "MusicVideo": MediaType.VIDEO,
    "Person": MediaType.ARTIST,
    "Photo": MediaType.IMAGE,
    "PhotoAlbum": MediaType.ALBUM,
    "PlaylistFolder": MediaType.PLAYLIST,
    "Program": MediaType.VIDEO,
    "Playlist": MediaType.PLAYLIST,
    "Recording": MediaType.VIDEO,
    "Season": MediaType.SEASON,
    "Series": MediaType.TVSHOW,
    "Studio": MediaType.PLAYLIST,
    "Trailer": MediaType.VIDEO,
    "TvChannel": MediaType.CHANNEL,
    "TvProgram": MediaType.VIDEO,
    "UserRootFolder": MediaType.PLAYLIST,
    "UserView": MediaType.PLAYLIST,
    "Video": MediaType.VIDEO,
    "Year": MediaType.PLAYLIST,
}


LATEST_TYPES = {
    "Movie": {
        "title": "Movies",
        "icon": "mdi:movie",
    },
    "Episode": {
        "title": "Series",
        "icon": "mdi:card-multiple",
    },
    "Audio": {
        "title": "Music",
        "icon": "mdi:music",
    },
    "Book": {
        "title": "Books",
        "icon": "mdi:book",
    },
    "MusicVideo": {
        "title": "Music Videos",
        "icon": "mdi:video-account",
    },
    "Photo": {
        "title": "Photos",
        "icon": "mdi:image",
    },
    "Video": {
        "title": "Videos",
        "icon": "mdi:video",
    },
    "Trailer": {
        "title": "Trailers",
        "icon": "mdi:movie-filter",
    },
}

TICKS_PER_SECOND = 10000000

IMAGE_TYPES = {
    "Primary",
    "Backdrop",
    "Art",
    "Thumb",
    "Banner",
    "Logo",
    "Disc",
    "Box",
    "Screenshot",
    "Menu",
    "Chapter",
    "BoxRear",
    "Profile",
}

IMAGE_CATEGORIES = {
    "Parent",
    "Album",
    "Series",
    "Channel",
}


LATEST_QUERY_FIELDS = {
    "AlbumId",
    "AlbumPrimaryImageTag",
    "Artists",
    "BackdropImageTags",
    "ChannelPrimaryImageTag",
    "CommunityRating",
    "CriticRating",
    "DateCreated",
    "Genres",
    "ImageTags",
    "IndexNumber",
    "OfficialRating",
    "Overview",
    "ParentArtImageTag",
    "ParentArtItemId",
    "ParentBackdropImageTags",
    "ParentBackdropItemId",
    "ParentId",
    "ParentLogoImageTag",
    "ParentIndexNumber",
    "ParentPrimaryImageItemId",
    "ParentPrimaryImageTag",
    "ParentThumbImageTag",
    "ParentThumbItemId",
    "PremiereDate",
    "ProductionYear",
    "RunTimeTicks",
    "SeasonName",
    "ScreenshotImageTags",
    "SeriesId",
    "SeriesName",
    "SeriesPrimaryImageTag",
    "SeriesThumbImageTag",
    "Studios",
    "Taglines",
}

LATEST_QUERY_SORT_BY = ["DateCreated", "SortName", "ProductionYear"]
LATEST_QUERY_SORT_ORDER = ["Descending", "Ascending", "Descending"]
LATEST_QUERY_PARAMS = {
    "Recursive": "true",
    "IsVirtualItem": "false",
    "GroupItemsIntoCollections": "false",
    "SortBy": ",".join(LATEST_QUERY_SORT_BY),
    "SortOrder": ",".join(LATEST_QUERY_SORT_ORDER),
    "Fields": ",".join(LATEST_QUERY_FIELDS),
    "Limit": 5,
}
