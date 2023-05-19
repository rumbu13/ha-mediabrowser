"""Data coordinator for the Media Browser (Emby/Jellyfin) integration."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LATEST_QUERY_PARAMS, LATEST_TYPES, UPDATE_INTERVAL
from .helpers import response_to_dict
from .hub import MediaBrowserHub
from .models import MBItem, MBResponse, MBSystemInfo

_LOGGER = logging.getLogger(__package__)


class MediaBrowserPushData:
    """Stores MediaBrowser sessions state."""

    def __init__(self, sessions_raw: list[dict[str, Any]]) -> None:
        """Initialize MediaBrowser push data."""
        self.sessions: dict[str, dict[str, Any]] = {}
        for session in reversed(sessions_raw):
            self.sessions[get_session_key(session)] = session


class MediaBrowserPushCoordinator(DataUpdateCoordinator[MediaBrowserPushData]):
    """Data push coordinator."""

    def __init__(self, hass: HomeAssistant, hub: MediaBrowserHub) -> None:
        """Initialize MediaBrowser push coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.hub = hub
        self.hub.register_sessions_raw_callback(self._sessions_raw_callback)
        self.players: set[str] = set()

    async def _async_update_data(self) -> MediaBrowserPushData:
        return MediaBrowserPushData(await self.hub.async_get_sessions_raw())

    def _sessions_raw_callback(self, sessions: list[dict[str, Any]]) -> None:
        self.async_set_updated_data(MediaBrowserPushData(sessions))


class MediaBrowserPollData:
    """Stores MediaBrowser state."""

    def __init__(self) -> None:
        """Initialize MediaBrowser poll data."""
        self.ping: str | None = None
        self.info: MBSystemInfo = MBSystemInfo.empty()
        # self.sessions: list[MBSession] = []
        self.libraries: dict[str, MBItem] = {}
        self.library_infos: dict[str, LibraryInfo] = {}
        self.latest_infos: dict[str, list[dict[str, Any]]] = {}


class MediaBrowserPollCoordinator(DataUpdateCoordinator[MediaBrowserPollData]):
    """Data poll coordinator."""

    def __init__(self, hass: HomeAssistant, hub: MediaBrowserHub) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.hub = hub

    async def _async_update_data(self) -> MediaBrowserPollData:
        data: MediaBrowserPollData = MediaBrowserPollData()
        data.ping = await self.hub.async_ping()
        data.info = await self.hub.async_get_info()
        data.libraries = response_to_dict(await self.hub.async_get_libraries())
        data.library_infos = {}
        for library_id, library in data.libraries.items():
            info: LibraryInfo | None = None
            match library.collection_type:
                case "movies":
                    info = MovieLibraryInfo(self.hub, library_id)
                case "tvshows":
                    info = TVShowLibraryInfo(self.hub, library_id)
                case "music":
                    info = MusicLibraryInfo(self.hub, library_id)
                case "homevideos":
                    info = HomeVideosLibraryInfo(self.hub, library_id)
                case "musicvideos":
                    info = MusicVideosLibraryInfo(self.hub, library_id)
                case "books":
                    info = BooksLibraryInfo(self.hub, library_id)
                case "boxsets":
                    info = BoxsetsLibraryInfo(self.hub, library_id)
                case "mixed" | "" | None:
                    info = MixedLibraryInfo(self.hub, library_id)
                case _:
                    info = LibraryInfo(self.hub, library_id)
            if info is not None:
                await info.refresh()
                data.library_infos[library_id] = info
        for item_type in LATEST_TYPES:
            response = await self.hub.async_get_items_raw(
                LATEST_QUERY_PARAMS | {"IncludeItemTypes": item_type}
            )
            data.latest_infos[item_type] = (
                response["Items"] if "Items" in response else []
            )
        return data


class ItemInfo:
    """Basic item information."""

    def __init__(
        self, count_or_response: int | MBResponse, item: MBItem | None = None
    ) -> None:
        if isinstance(count_or_response, int):
            self.count: int = count_or_response
            self.item: MBItem | None = item
        else:
            self.count: int = count_or_response.total_record_count
            self.item: MBItem | None = (
                count_or_response.items[0] if len(count_or_response.items) > 0 else None
            )

    @property
    def attributes(self) -> dict[str, Any]:
        """Returns content as attributes."""
        data: dict[str, Any] = {"count": self.count}
        if self.item is not None:
            data["last_item_name"] = self.item.name
        return data


class LibraryInfo:
    """Basic library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        """Initialize object."""
        self._hub: MediaBrowserHub = hub
        self._library_id: str = library_id

        self.item_info = ItemInfo(0, None)

    async def _fetch_items(self, item_types: str) -> MBResponse:
        params = {
            "Limit": "1",
            "Recursive": "true",
            "SortOrder": "Descending",
            "SortBy": "DateCreated",
            "ParentId": self._library_id,
            "IncludeItemTypes": item_types,
        }
        return await self._hub.async_get_items(params)

    async def _fetch_artists(self) -> MBResponse:
        params = {
            "Limit": "1",
            "Recursive": "true",
            "SortOrder": "Descending",
            "SortBy": "DateCreated",
            "ParentId": self._library_id,
        }
        return await self._hub.async_get_artists(params)

    async def _fetch_studios(self) -> MBResponse:
        params = {
            "Limit": "1",
            "Recursive": "true",
            "SortOrder": "Descending",
            "SortBy": "DateCreated",
            "ParentId": self._library_id,
        }
        return await self._hub.async_get_studios(params)

    async def _fetch_genres(self) -> MBResponse:
        params = {
            "Limit": "1",
            "Recursive": "true",
            "SortOrder": "Descending",
            "SortBy": "DateCreated",
            "ParentId": self._library_id,
        }
        return await self._hub.async_get_genres(params)

    async def _fetch_persons(self) -> MBResponse:
        params = {
            "Limit": "1",
            "Recursive": "true",
            "SortOrder": "Descending",
            "SortBy": "DateCreated",
            "ParentId": self._library_id,
        }
        return await self._hub.async_get_persons(params)

    async def _fetch_tags(self) -> MBResponse:
        params = {
            "Limit": "1",
            "Recursive": "true",
            "SortOrder": "Descending",
            "SortBy": "DateCreated",
            "ParentId": self._library_id,
        }
        return await self._hub.async_get_tags(params)

    async def refresh(self):
        """Refreshes the current data."""
        self.item_info = ItemInfo(await self._fetch_items(""))

    @property
    def attributes(self) -> dict[str, Any]:
        """Returns attributes as a dictionary."""
        return {}

    @property
    def count(self) -> int:
        """Returns items count."""
        return self.item_info.count if self.item_info is not None else 0


class MovieLibraryInfo(LibraryInfo):
    """Movie library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        super().__init__(hub, library_id)
        self.artists_info = ItemInfo(0, None)
        self.genres_info = ItemInfo(0, None)
        self.studios_info = ItemInfo(0, None)

    async def refresh(self):
        self.item_info = ItemInfo(await self._fetch_items("Movie"))
        if self._hub.is_emby:
            self.artists_info = ItemInfo(await self._fetch_persons())
        self.genres_info = ItemInfo(await self._fetch_genres())
        self.studios_info = ItemInfo(await self._fetch_studios())

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "movies": self.item_info.attributes,
            "artists": self.artists_info.attributes,
            "studios": self.studios_info.attributes,
            "genres": self.genres_info.attributes,
        }


class TVShowLibraryInfo(LibraryInfo):
    """Movie library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        super().__init__(hub, library_id)
        self.seasons_info = ItemInfo(0, None)
        self.shows_info = ItemInfo(0, None)
        self.artists_info = ItemInfo(0, None)
        self.genres_info = ItemInfo(0, None)
        self.studios_info = ItemInfo(0, None)

    async def refresh(self):
        self.item_info = ItemInfo(await self._fetch_items("Episode"))
        self.seasons_info = ItemInfo(await self._fetch_items("Season"))
        self.shows_info = ItemInfo(await self._fetch_items("Series"))
        if self._hub.is_emby:
            self.artists_info = ItemInfo(await self._fetch_persons())
        self.genres_info = ItemInfo(await self._fetch_genres())
        self.studios_info = ItemInfo(await self._fetch_studios())

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "episodes": self.item_info.attributes,
            "seasons": self.seasons_info.attributes,
            "shows": self.shows_info.attributes,
            "artists": self.artists_info.attributes,
            "studios": self.studios_info.attributes,
            "genres": self.genres_info.attributes,
        }


class MusicLibraryInfo(LibraryInfo):
    """Music library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        super().__init__(hub, library_id)
        self.albums_info = ItemInfo(0, None)
        self.artists_info = ItemInfo(0, None)
        self.genres_info = ItemInfo(0, None)
        self.studios_info = ItemInfo(0, None)

    async def refresh(self) -> None:
        self.item_info = ItemInfo(await self._fetch_items("Audio"))
        self.albums_info = ItemInfo(await self._fetch_items("MusicAlbum"))
        self.artists_info = ItemInfo(await self._fetch_artists())
        self.genres_info = ItemInfo(await self._fetch_genres())
        self.studios_info = ItemInfo(await self._fetch_studios())

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "songs": self.item_info.attributes,
            "albums": self.albums_info.attributes,
            "artists": self.artists_info.attributes,
            "studios": self.studios_info.attributes,
            "genres": self.genres_info.attributes,
        }


class HomeVideosLibraryInfo(LibraryInfo):
    """Movie library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        super().__init__(hub, library_id)
        self.photo_info = ItemInfo(0, None)
        self.video_info = ItemInfo(0, None)
        self.albums_info = ItemInfo(0, None)
        self.tags_info = ItemInfo(0, None)

    async def refresh(self):
        self.item_info = ItemInfo(await self._fetch_items("Photo,Video"))
        self.photo_info = ItemInfo(await self._fetch_items("Photo"))
        self.video_info = ItemInfo(await self._fetch_items("Video"))
        self.albums_info = ItemInfo(await self._fetch_items("PhotoAlbum"))
        if self._hub.is_emby:
            self.tags_info = ItemInfo(await self._fetch_tags())

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "total": self.item_info.attributes,
            "photos": self.photo_info.attributes,
            "videos": self.video_info.attributes,
            "albums": self.albums_info.attributes,
            "tags": self.tags_info.attributes,
        }


class MusicVideosLibraryInfo(LibraryInfo):
    """Movie library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        super().__init__(hub, library_id)
        self.artists_info = ItemInfo(0, None)
        self.genres_info = ItemInfo(0, None)
        self.studios_info = ItemInfo(0, None)

    async def refresh(self):
        self.item_info = ItemInfo(await self._fetch_items("MusicVideo"))
        if self._hub.is_emby:
            self.artists_info = ItemInfo(await self._fetch_persons())
        self.genres_info = ItemInfo(await self._fetch_genres())
        self.studios_info = ItemInfo(await self._fetch_studios())

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "videos": self.item_info.attributes,
            "artists": self.artists_info.attributes,
            "studios": self.studios_info.attributes,
            "genres": self.genres_info.attributes,
        }


class BooksLibraryInfo(LibraryInfo):
    """Books library information."""

    async def refresh(self) -> None:
        self.item_info = ItemInfo(await self._fetch_items("Book"))

    @property
    def attributes(self) -> dict[str, Any]:
        return {"books": self.item_info.attributes}


class BoxsetsLibraryInfo(LibraryInfo):
    """Boxsets library information."""

    async def refresh(self) -> None:
        self.item_info = ItemInfo(await self._fetch_items("BoxSet"))

    @property
    def attributes(self) -> dict[str, Any]:
        return {"boxsets": self.item_info.attributes}


class MixedLibraryInfo(LibraryInfo):
    """Mixed library information."""

    def __init__(self, hub: MediaBrowserHub, library_id: str) -> None:
        super().__init__(hub, library_id)
        self.movies_info = ItemInfo(0, None)
        self.episodes_info = ItemInfo(0, None)
        self.seasons_info = ItemInfo(0, None)
        self.shows_info = ItemInfo(0, None)
        self.artists_info = ItemInfo(0, None)
        self.genres_info = ItemInfo(0, None)
        self.studios_info = ItemInfo(0, None)

    async def refresh(self) -> None:
        self.item_info = ItemInfo(await self._fetch_items("Episode,Movie"))
        self.movies_info = ItemInfo(await self._fetch_items("Movie"))
        self.episodes_info = ItemInfo(await self._fetch_items("Episode"))
        self.seasons_info = ItemInfo(await self._fetch_items("Season"))
        self.shows_info = ItemInfo(await self._fetch_items("Series"))
        if self._hub.is_emby:
            self.artists_info = ItemInfo(await self._fetch_persons())
        self.genres_info = ItemInfo(await self._fetch_genres())
        self.studios_info = ItemInfo(await self._fetch_studios())

    @property
    def attributes(self) -> dict[str, Any]:
        return {
            "total": self.item_info.attributes,
            "movies": self.movies_info.attributes,
            "episodes": self.episodes_info.attributes,
            "seasons": self.seasons_info.attributes,
            "shows": self.shows_info.attributes,
            "artists": self.artists_info.attributes,
            "studios": self.studios_info.attributes,
            "genres": self.genres_info.attributes,
        }


def get_session_key(session: dict[str, Any]) -> str:
    """Gets a uniqe session key"""
    return f'{session["DeviceId"]}-{session["Client"]}'
