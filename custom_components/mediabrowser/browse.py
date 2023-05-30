"""Browsing helper module."""

import logging
from typing import Any

from .helpers import as_int

from .const import (
    VIRTUAL_FILTER_MAP,
    VIRTUAL_FOLDER_MAP,
    ArtistType,
    CollectionType,
    ItemType,
    Item,
    MediaSource,
    Query,
    Response,
    ServerType,
    SortBy,
    SortOrder,
    Value,
    VirtualFolder,
)
from .errors import BrowseMediaError
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__name__)


async def get_children(
    hub: MediaBrowserHub, item: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Get children for the specified item."""
    if item is None:
        return await _get_libraries(hub)

    match item.get(Item.TYPE):
        case ItemType.COLLECTION_FOLDER:
            return await _get_collection(hub, item)
        case ItemType.VIRTUAL:
            return await _get_virtual_folder(hub, item)
        case (
            ItemType.ARTIST
            | ItemType.ALBUM_ARTIST
            | ItemType.MUSIC_ARTIST
            | ItemType.PERSON
            | ItemType.GENRE
            | ItemType.MUSIC_GENRE
            | ItemType.STUDIO
            | ItemType.PREFIX
            | ItemType.YEAR
            | ItemType.TAG
        ):
            return await _get_virtual_children(hub, item)
        case ItemType.PLAYLIST:
            return await _get_playlist_children(hub, item[Item.ID])

    if item.get(Item.IS_FOLDER, False):
        return await _get_default_children(hub, item[Item.ID])

    return []


async def _get_libraries(hub: MediaBrowserHub) -> list[dict[str, Any]]:
    return sorted(await hub.async_get_libraries(), key=lambda x: x.get(Item.NAME, ""))


async def _get_collection(
    hub: MediaBrowserHub, item: dict[str, Any]
) -> list[dict[str, Any]]:
    match item.get(Item.COLLECTION_TYPE):
        case CollectionType.MOVIES:
            return await _get_movies(hub, item)
        case CollectionType.TVSHOWS:
            return await _get_tvshows(hub, item)
        case CollectionType.MUSIC:
            return await _get_music(hub, item)
        case CollectionType.AUDIOBOOKS:
            return await _get_audio_books(hub, item)
        case CollectionType.HOMEVIDEOS:
            return await _get_homevideos(hub, item)
        case CollectionType.MUSICVIDEOS:
            return await _get_musicvideos(hub, item)
    return await _get_default_children(hub, item[Item.ID])


async def _get_movies(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MOVIE,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Item.ID],
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.PERSONS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.STUDIOS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Item.ID]),
    ] + children.get(Response.ITEMS, [])


async def _get_tvshows(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.SERIES,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Item.ID],
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.PERSONS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.STUDIOS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Item.ID]),
    ] + children.get(Response.ITEMS, [])


async def _get_music(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    # emby/jellyfin bug: needs User/Items, Items ignores ParentId
    albums = await hub.async_get_user_items(
        hub.user_id or "",
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_ALBUM,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Item.ID],
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        },
    )

    videos = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_VIDEO,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Item.ID],
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.ARTISTS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.ALBUM_ARTISTS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.COMPOSERS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.STUDIOS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PLAYLISTS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Item.ID]),
    ] + sorted(
        albums.get(Response.ITEMS, []) + videos.get(Response.ITEMS, []),
        key=lambda x: x.get(Item.SORT_NAME, x.get(Item.NAME, "")),
    )


async def _get_musicvideos(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_VIDEO,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Item.ID],
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return [
        _make_virtual_folder(VirtualFolder.ARTISTS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PERSONS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Item.ID]),
    ] + children.get(Response.ITEMS, [])


async def _get_audio_books(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    # emby/jellyfin bug: needs User/Items, Items ignores ParentId
    children = await hub.async_get_user_items(
        hub.user_id or "",
        {
            Query.INCLUDE_ITEM_TYPES: ItemType.MUSIC_ALBUM,
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: library[Item.ID],
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        },
    )

    return [
        _make_virtual_folder(VirtualFolder.ARTISTS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.GENRES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PERSONS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.YEARS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PREFIXES, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Item.ID]),
    ] + children.get(Response.ITEMS, [])


async def _get_homevideos(
    hub: MediaBrowserHub, library: dict[str, Any]
) -> list[dict[str, Any]]:
    children = [
        _make_virtual_folder(VirtualFolder.VIDEOS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.PHOTOS, library[Item.ID]),
        _make_virtual_folder(VirtualFolder.FOLDERS, library[Item.ID]),
    ]

    if hub.server_type == ServerType.EMBY:
        children.append(_make_virtual_folder(VirtualFolder.TAGS, library[Item.ID]))

    return children


async def _get_default_children(
    hub: MediaBrowserHub, parent_id: str
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.FALSE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: ",".join([SortBy.IS_FOLDER, SortBy.FILENAME]),
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )
    return children.get(Response.ITEMS, [])


async def _get_playlist_children(
    hub: MediaBrowserHub, parent_id: str
) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.FALSE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.LIST_ITEM_ORDER,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )
    return children.get(Response.ITEMS, [])


async def _get_virtual_folder(
    hub: MediaBrowserHub, item: dict[str, Any]
) -> list[dict[str, Any]]:
    parts = item[Item.ID].split("/")
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

    raise BrowseMediaError(f"Unsupported virtual folder: {item[Item.ID]}")


async def _get_playlists(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.PLAYLIST,
        }
    )
    return children.get(Response.ITEMS, [])


async def _get_videos(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.VIDEO,
        }
    )
    return children.get(Response.ITEMS, [])


async def _get_photos(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.PHOTO,
        }
    )
    return children.get(Response.ITEMS, [])


async def _get_tags(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_items(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.INCLUDE_ITEM_TYPES: ItemType.TAG,
        }
    )
    return _make_virtual_subfolders(
        VirtualFolder.TAGS, children.get(Response.ITEMS, []), parent_id
    )


async def _get_artists(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_artists(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.ARTIST_TYPE: ",".join([ArtistType.ARTIST, ArtistType.COMPOSER]),
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.ARTISTS, children.get(Response.ITEMS, []), parent_id
    )


async def _get_composers(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_artists(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.ARTIST_TYPE: ArtistType.COMPOSER,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.COMPOSERS, children.get(Response.ITEMS, []), parent_id
    )


async def _get_album_artists(
    hub: MediaBrowserHub, parent_id: str
) -> list[dict[str, Any]]:
    children = await hub.async_get_artists(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
            Query.ARTIST_TYPE: ArtistType.ALBUM_ARTIST,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.COMPOSERS, children.get(Response.ITEMS, []), parent_id
    )


async def _get_persons(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_persons(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.PERSONS, children.get(Response.ITEMS, []), parent_id
    )


async def _get_genres(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_genres(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.GENRES, children.get(Response.ITEMS, []), parent_id
    )


async def _get_prefixes(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_prefixes(
        {
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return _make_virtual_subfolders(VirtualFolder.PREFIXES, children, parent_id)


async def _get_years(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_years(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.YEARS, children.get(Response.ITEMS, []), parent_id
    )


async def _get_studios(hub: MediaBrowserHub, parent_id: str) -> list[dict[str, Any]]:
    children = await hub.async_get_studios(
        {
            Query.RECURSIVE: Value.TRUE,
            Query.PARENT_ID: parent_id,
            Query.SORT_BY: SortBy.SORT_NAME,
            Query.SORT_ORDER: SortOrder.ASCENDING,
        }
    )

    return _make_virtual_subfolders(
        VirtualFolder.STUDIOS, children.get(Response.ITEMS, []), parent_id
    )


def _make_virtual_folder(virtual_id: str, parent_id: str) -> dict[str, Any]:
    return dict[str, Any](
        {
            Item.ID: f"{virtual_id}/{parent_id}",
            Item.NAME: VIRTUAL_FOLDER_MAP[virtual_id],
            Item.PARENT_ID: parent_id,
            Item.TYPE: ItemType.VIRTUAL,
            Item.IS_FOLDER: Value.FALSE,
        }
    )


def _make_virtual_subfolder(
    virtual_id: str, item: dict[str, Any], parent_id: str
) -> dict[str, Any]:
    result = item
    if virtual_id in [VirtualFolder.YEARS, VirtualFolder.PREFIXES]:
        result[Item.ID] = f"{virtual_id}/{parent_id}/{item[Item.NAME]}"
    else:
        result[Item.ID] = f"{virtual_id}/{parent_id}/{item[Item.ID]}"
    result[Item.IS_FOLDER] = True
    return result


def _make_virtual_subfolders(
    virtual_id: str, items: list[dict[str, Any]], parent_id: str
) -> list[dict[str, Any]]:
    return [_make_virtual_subfolder(virtual_id, item, parent_id) for item in items]


async def get_item(hub: MediaBrowserHub, item_id: str) -> dict[str, Any]:
    """Parse an item identifier and gets the corresponding item."""
    parts = item_id.split("/")
    if len(parts) == 1:
        try:
            return (await hub.async_get_items({Query.IDS: item_id}))[Response.ITEMS][0]
        except (KeyError, IndexError) as idx:
            raise BrowseMediaError(f"Cannot find item {item_id}") from idx

    if len(parts) == 2:
        return _make_virtual_folder(parts[0], parts[1])

    if len(parts) == 3:
        match parts[0]:
            case "prefixes":
                item = dict[str, Any](
                    {Item.ID: parts[2], Item.NAME: parts[2], Item.TYPE: ItemType.PREFIX}
                )
            case "years":
                item = dict[str, Any](
                    {Item.ID: parts[2], Item.NAME: parts[2], Item.TYPE: ItemType.YEAR}
                )
            case _:
                try:
                    item = (await hub.async_get_items({Query.IDS: parts[2]}))[
                        Response.ITEMS
                    ][0]
                except (KeyError, IndexError) as idx:
                    raise BrowseMediaError(f"Cannot find item {item_id}") from idx
        return _make_virtual_subfolder(parts[0], item, parts[1])

    raise BrowseMediaError(f"Invalid item identifier {item_id}")


async def _get_virtual_children(
    hub: MediaBrowserHub, item: dict[str, Any]
) -> list[dict[str, Any]]:
    query: dict[str, str] = {
        Query.RECURSIVE: Value.TRUE,
        Query.SORT_BY: SortBy.SORT_NAME,
        Query.SORT_ORDER: SortOrder.ASCENDING,
    }
    parts = item[Item.ID].split("/")
    query[Item.PARENT_ID] = parts[1]
    if parts[0] in VIRTUAL_FILTER_MAP:
        query[VIRTUAL_FILTER_MAP[parts[0]]] = parts[2]
    else:
        match parts[0]:
            case "prefixes":
                query[Query.NAME_STARTS_WITH] = parts[2]
            case _:
                raise BrowseMediaError(f"Unknown virtual folder type: {parts[0]}")

    library = (await hub.async_get_items({"Ids": parts[1]}))[Response.ITEMS][0]
    match library[Item.COLLECTION_TYPE]:
        case CollectionType.MOVIES:
            query[Query.INCLUDE_ITEM_TYPES] = ItemType.MOVIE
        case CollectionType.TVSHOWS:
            query[Query.INCLUDE_ITEM_TYPES] = ItemType.SERIES
        case CollectionType.MUSIC | CollectionType.AUDIOBOOKS:
            query[Query.INCLUDE_ITEM_TYPES] = ItemType.MUSIC_ALBUM
        case CollectionType.MUSICVIDEOS:
            query[Query.INCLUDE_ITEM_TYPES] = ItemType.MUSIC_VIDEO
        case CollectionType.HOMEVIDEOS:
            pass
        case _:
            raise BrowseMediaError(
                f"Unsupported virtual collection type: {library.collection_type}"
            )

    return (await hub.async_get_items(query))[Response.ITEMS]


async def get_stream_url(
    hub: MediaBrowserHub, item_id: str, item_media_type: str
) -> tuple[str | None, str | None]:
    """Get a stream url for the specified item_id."""
    url: str | None = None
    mime_type: str | None = None

    info = await hub.async_get_playback_info(item_id)

    if Item.MEDIA_SOURCES in info:
        direct_stream: bool = False
        bitrate: int = 0
        best: dict[str, Any] | None = None
        for source in info[Item.MEDIA_SOURCES]:
            current_ds: bool = source.get(MediaSource.SUPPORTS_DIRECT_STREAM, False)
            current_br: int = as_int(source, MediaSource.BITRATE) or 0
            if (
                (current_ds and not direct_stream)
                or (current_ds and direct_stream and current_br > bitrate)
                or (not current_ds and not direct_stream and current_br > bitrate)
            ):
                best = source
                bitrate = current_br
                direct_stream = current_ds

        if best is not None:
            if best.get(MediaSource.SUPPORTS_DIRECT_STREAM, False):
                mime_type = (
                    f"{item_media_type.lower()}/{best.get(MediaSource.CONTAINER)}"
                )
                url = f"{hub.server_url}{best[MediaSource.DIRECT_STREAM_URL]}"
            elif best.get(MediaSource.SUPPORTS_TRANSCODING, False):
                url = f"{hub.server_url}{best[MediaSource.TRANSCODING_URL]}"
                mime_type = "/".join(
                    (
                        item_media_type.lower(),
                        best.get(
                            MediaSource.TRANSCODING_CONTAINER,
                            best.get(MediaSource.CONTAINER),
                        ),
                    ),
                )

    return (url, mime_type)
