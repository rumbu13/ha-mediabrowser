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

LIBRARY_ICONS = {
    "": "mdi:filmstrip",
    "audiobooks": "mdi:book-music",
    "books": "mdi:bookshelf",
    "boxsets": "mdi:filmstrip-box",
    "mixed": "mdi:filmstrip",
    "homevideos": "mdi:multimedia",
    "movies": "mdi:filmstrip-box",
    "music": "mdi:music",
    "musicvideos": "mdi:youtube",
    "playlists": "mdi:playlist-music",
    "tvshows": "mdi:filmstrip-box-multiple",
}

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
    "Audio": MediaType.TRACK,
    "AudioBook": MediaType.ALBUM,
    "Artist": MediaType.ARTIST,
    "Book": MediaType.APP,
    "Channel": MediaType.CHANNEL,
    "Episode": MediaType.EPISODE,
    "Genre": MediaType.GENRE,
    "LiveTvChannel": MediaType.CHANNEL,
    "LiveTvProgram": MediaType.VIDEO,
    "Movie": MediaType.MOVIE,
    "MusicAlbum": MediaType.ALBUM,
    "MusicArtist": MediaType.ARTIST,
    "MusicGenre": MediaType.GENRE,
    "MusicVideo": MediaType.VIDEO,
    "Person": MediaType.ARTIST,
    "Photo": MediaType.IMAGE,
    "PhotoAlbum": MediaType.ALBUM,
    "Program": MediaType.VIDEO,
    "Playlist": MediaType.PLAYLIST,
    "Recording": MediaType.VIDEO,
    "Season": MediaType.SEASON,
    "Series": MediaType.TVSHOW,
    "Trailer": MediaType.VIDEO,
    "TvChannel": MediaType.CHANNEL,
    "TvProgram": MediaType.VIDEO,
    "Video": MediaType.VIDEO,
}
