"""Browsing helper module."""

import logging
from typing import Any, Tuple

from .const import (
    VIRTUAL_FILTER_MAP,
    VIRTUAL_FOLDER_MAP,
    ItemType,
    Key,
    Query,
    ServerType,
    Value,
    VirtualFolder,
)
from .errors import BrowseMediaError
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__name__)


async def get_children(
    hub: MediaBrowserHub, item: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Gets children for the specified item."""
    if item is None:
        return await _get_libraries(hub)

    match item.get(Key.TYPE):
        case "CollectionFolder":
            return await _get_collection(hub, item)
        case "Virtual":
            return await _get_virtual_folder(hub, item)
        case (
            "Artist"
            | "AlbumArtist"
            | "MusicArtist"
            | "Person"
            | "Genre"
            | "MusicGenre"
            | "Studio"
            | "Prefix"
            | "Year"
            | "Tag"
        ):
            return await _get_virtual_children(hub, item)
        case "Playlist":
            return await _get_playlist_children(hub, item[Key.ID])

    if item.get(Key.IS_FOLDER, False):
        return await _get_default_children(hub, item[Key.ID])

    return []


async def _get_libraries(hub: MediaBrowserHub) -> list[dict[str, Any]]:
    return sorted(
        await hub.async_get_libraries_raw(), key=lambda x: x.get(Key.NAME, "")
    )


async def _get_collection(
    hub: MediaBrowserHub, item: dict[str, Any]
) -> list[dict[str, Any]]:
    match item.get(Key.COLLECTION_TYPE):
        case "movies":
            return await _get_movies(hub, item)
        case "tvshows":
            return await _get_tvshows(hub, item)
        case "music":
            return await _get_music(hub, item)
        case "audiobooks":
            return await _get_audio_books(hub, item)
        case "homevideos":
            return await _get_homevideos(hub, item)
        case "musicvideos":
            return await _get_musicvideos(hub, item)
    return await _get_default_children(hub, item[Key.ID])


async def _get_movies(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MOVIE,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Key.ID],
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.PERSONS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.STUDIOS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Key.ID]),
    ] + children.get(Key.ITEMS, [])


async def _get_tvshows(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.SERIES,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Key.ID],
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.PERSONS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.STUDIOS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Key.ID]),
    ] + children.get(Key.ITEMS, [])


async def _get_music(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    # emby/jellyfin bug: needs User/Items, Items ignores ParentId
    albums = await hub.async_get_user_items(
        hub.server_admin_id,
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_ALBUM,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Key.ID],
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        },
    )

    videos = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_VIDEO,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Key.ID],
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.ARTISTS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.ALBUM_ARTISTS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.COMPOSERS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.STUDIOS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PLAYLISTS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Key.ID]),
    ] + sorted(
        albums.get(Key.ITEMS, []) + videos.get(Key.ITEMS, []),
        key=lambda x: x.get(Key.SORT_NAME, x.get(Key.NAME, "")),
    )


async def _get_musicvideos(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_VIDEO,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Key.ID],
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.ARTISTS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PERSONS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Key.ID]),
    ] + children.get(Key.ITEMS, [])


async def _get_audio_books(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    # emby/jellyfin bug: needs User/Items, Items ignores ParentId
    children = await hub.async_get_user_items(
        hub.server_admin_id,
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_ALBUM,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Key.ID],
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        },
    )

    return [
        _make_virtual_folder(VirtualFolder.ARTISTS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PERSONS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Key.ID]),
    ] + children.get(Key.ITEMS, [])


async def _get_homevideos(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = [
        _make_virtual_folder(VirtualFolder.VIDEOS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.PHOTOS, library[Key.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Key.ID]),
    ]

    if hub.server_type == ServerType.EMBY:
        children.append(_make_virtual_folder(VirtualFolder.TAGS, library[Key.ID]))

    return children


async def _get_default_children(
    hub: MediaBrowserHub, parent_id: str
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.FALSE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: ",".join([Key.IS_FOLDER, Key.FILENAME]),
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )
    return children.get(Key.ITEMS, [])


async def _get_playlist_children(
    hub: MediaBrowserHub, parent_id: str
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.FALSE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.LIST_ITEM_ORDER,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )
    return children.get(Key.ITEMS, [])


async def _get_virtual_folder(
    hub: MediaBrowserHub, item: dict[str, Any]
) -> list[dict[str, Any]]:
    parts = item[Key.ID].split("/")
    match parts[0]:
        case VirtualFolder.ARTISTS:
            return await _get_artists(hub, parts[1])
        case VirtualFolder.ALBUM_ARTISTS:
            return await _get_album_artists(hub, parts[1])
        case VirtualFolder.COMPOSERS:
            return await _get_composers(hub, parts[1])
        case VirtualFolder.PERSONS:
            return await _get_persons(hub, parts[1])
        case VirtualFolder.GENRES:
            return await _get_genres(hub, parts[1])
        case VirtualFolder.STUDIOS:
            return await _get_studios(hub, parts[1])
        case VirtualFolder.PREFIXES:
            return await _get_prefixes(hub, parts[1])
        case VirtualFolder.YEARS:
            return await _get_years(hub, parts[1])
        case VirtualFolder.FOLDERS:
            return await _get_default_children(hub, parts[1])
        case VirtualFolder.VIDEOS:
            return await _get_videos(hub, parts[1])
        case VirtualFolder.PHOTOS:
            return await _get_photos(hub, parts[1])
        case VirtualFolder.TAGS:
            return await _get_tags(hub, parts[1])
        case VirtualFolder.PLAYLISTS:
            return await _get_playlists(hub, parts[1])

    raise BrowseMediaError(f"Unsupported virtual folder: {item[Key.ID]}")


async def _get_playlists(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.PLAYLIST,
        }
    )
    return children.get(Key.ITEMS, [])


async def _get_videos(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.VIDEO,
        }
    )
    return children.get(Key.ITEMS, [])


async def _get_photos(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.PHOTO,
        }
    )
    return children.get(Key.ITEMS, [])


async def _get_tags(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.TAG,
        }
    )
    return _make_virtual_subfolders(
        VirtualFolder.TAGS, children.get(Key.ITEMS, []), parent_id
    )


async def _get_artists(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_artists(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.ARTIST_TYPE: ",".join([Value.ARTIST, Value.COMPOSER]),
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.ARTISTS, children.get(Key.ITEMS, []), parent_id
    )


async def _get_composers(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_artists(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.ARTIST_TYPE: Value.COMPOSER,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.COMPOSERS, children.get(Key.ITEMS, []), parent_id
    )


async def _get_album_artists(
    hub: MediaBrowserHub, parent_id: str
) -> list[dict[str, Any]]:
    children = await hub.async_get_artists(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
            Query.ARTIST_TYPE: Value.ALBUM_ARTIST,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.COMPOSERS, children.get(Key.ITEMS, []), parent_id
    )


async def _get_persons(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_persons(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.PERSONS, children.get(Key.ITEMS, []), parent_id
    )


async def _get_genres(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_genres(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.GENRES, children.get(Key.ITEMS, []), parent_id
    )


async def _get_prefixes(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_prefixes(
        {
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return _make_virtual_subfolders(VirtualFolder.PREFIXES, children, parent_id)


async def _get_years(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_years(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.YEARS, children.get(Key.ITEMS, []), parent_id
    )


async def _get_studios(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_studios(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: Key.SORT_NAME,
            Query.SORT_ORDER: Value.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.STUDIOS, children.get(Key.ITEMS, []), parent_id
    )


def _make_virtual_folder(virtual_id: str, parent_id: str) -> dict[str, Any]:
    return dict[str, Any](
        {
            Key.ID: f"{virtual_id}/{parent_id}",
            Key.NAME: VIRTUAL_FOLDER_MAP[virtual_id],
            Key.PARENT_ID: parent_id,
            Key.TYPE: "Virtual",
            Key.IS_FOLDER: "true",
        }
    )


def _make_virtual_subfolder(
    virtual_id: str, item: dict[str, Any], parent_id: str
) -> dict[str, Any]:
    result = item
    if virtual_id in ["years", "prefixes"]:
        result[Key.ID] = f"{virtual_id}/{parent_id}/{item[Key.NAME]}"
    else:
        result[Key.ID] = f"{virtual_id}/{parent_id}/{item[Key.ID]}"
    result[Key.IS_FOLDER] = True
    return result


def _make_virtual_subfolders(
    virtual_id: str, items: list[dict[str, Any]], parent_id: str
) -> list[dict[str, Any]]:
    return [_make_virtual_subfolder(virtual_id, item, parent_id) for item in items]


async def get_item(hub: MediaBrowserHub, item_id: str) -> dict[str, Any]:
    """Parses a item identifier and gets the corresponding item."""
    parts = item_id.split("/")
    if len(parts) == 1:
        try:
            return (await hub.async_get_items({"Ids": item_id}))[Key.ITEMS][0]
        except (KeyError, IndexError) as idx:
            raise BrowseMediaError(f"Cannot find item {item_id}") from idx

    if len(parts) == 2:
        return _make_virtual_folder(parts[0], parts[1])

    if len(parts) == 3:
        match parts[0]:
            case "prefixes":
                item = dict[str, Any](
                    {Key.ID: parts[2], Key.NAME: parts[2], Key.TYPE: "Prefix"}
                )
            case "years":
                item = dict[str, Any](
                    {Key.ID: parts[2], Key.NAME: parts[2], Key.TYPE: "Year"}
                )
            case _:
                try:
                    item = (await hub.async_get_items({"Ids": parts[2]}))[Key.ITEMS][0]
                except (KeyError, IndexError) as idx:
                    raise BrowseMediaError(f"Cannot find item {item_id}") from idx
        return _make_virtual_subfolder(parts[0], item, parts[1])

    raise BrowseMediaError(f"Invalid item identifier {item_id}")


async def _get_virtual_children(
    hub: MediaBrowserHub, item: dict[str, Any]
) -> list[dict[str, Any]]:
    query: dict[str, str] = {
        Query.RECURSIVE: Value.TRUE,
        Query.SORT_BY: Key.SORT_NAME,
        Query.SORT_ORDER: Value.ASCENDING,
    }
    parts = item[Key.ID].split("/")
    query[Key.PARENT_ID] = parts[1]
    if parts[0] in VIRTUAL_FILTER_MAP:
        query[VIRTUAL_FILTER_MAP[parts[0]]] = parts[2]
    else:
        match parts[0]:
            case "prefixes":
                query[Query.NAME_STARTS_WITH] = parts[2]
            case _:
                raise BrowseMediaError(f"Unknown virtual folder type: {parts[0]}")

    library = (await hub.async_get_items({"Ids": parts[1]}))[Key.ITEMS][0]
    match library[Key.COLLECTION_TYPE]:
        case "movies":
            query[Query.INCLUDE_ITEM_TYPES] = "Movie"
        case "tvshows":
            query[Query.INCLUDE_ITEM_TYPES] = "Series"
        case "music" | "audiobooks":
            query[Query.INCLUDE_ITEM_TYPES] = "MusicAlbum"
        case "musicvideos":
            query[Query.INCLUDE_ITEM_TYPES] = "MusicVideo"
        case "homevideos":
            pass
        case _:
            raise BrowseMediaError(
                f"Unsupported virtual collection type: {library.collection_type}"
            )

    return (await hub.async_get_items(query))[Key.ITEMS]


async def get_stream_url(
    hub: MediaBrowserHub, item_id: str, item_media_type: str
) -> Tuple[str | None, str | None]:
    """get a stream url for the specified item_id"""
    url: str | None = None
    mime_type: str | None = None

    info = await hub.async_get_playback_info(item_id)

    if Key.MEDIA_SOURCES in info:
        direct_stream: bool = False
        bitrate: int = 0
        best: dict[str, Any] | None = None
        for source in info[Key.MEDIA_SOURCES]:
            current_ds: bool = source.get(Key.SUPPORTS_DIRECT_STREAM, False)
            current_br: int = int(source.get(Key.BITRATE, 0))
            if (
                (current_ds and not direct_stream)
                or (current_ds and direct_stream and current_br > bitrate)
                or (not current_ds and not direct_stream and current_br > bitrate)
            ):
                best = source
                bitrate = current_br
                direct_stream = current_ds

        if best is not None:
            if best.get(Key.SUPPORTS_DIRECT_STREAM, False):
                mime_type = f"{item_media_type}/{best.get(Key.CONTAINER)}"
                url = (
                    f'{hub.server_url}/{"Audio" if item_media_type == "Audio" else "Videos"}'
                    + f'/{item_id}/stream?static=true&MediaSourceId={best["Id"]}&api_key={hub.api_key}'
                )
            elif best.get(Key.SUPPORTS_TRANSCODING, False):
                url = f"{hub.server_url}{best[Key.TRANSCODING_URL]}"
                mime_type = f"{item_media_type}/{best.get(Key.TRANSCODING_CONTAINER, best.get(Key.CONTAINER))}"

    return (url, mime_type)
