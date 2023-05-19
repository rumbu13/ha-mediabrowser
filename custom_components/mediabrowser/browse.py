"""Browsing helper module."""

import logging

from .const import VIRTUAL_FOLDER_MAP
from .errors import BrowseMediaError
from .hub import MediaBrowserHub
from .models import MBItem

_LOGGER = logging.getLogger(__name__)

VIRTUAL_FILTER_MAP = {
    "artists": "ArtistIds",
    "composers": "ArtistIds",
    "album_artists": "ArtistIds",
    "persons": "PersonIds",
    "genres": "GenreIds",
    "studios": "StudioIds",
    "tags": "TagIds",
    "years": "Years",
}


async def get_children(hub: MediaBrowserHub, item: MBItem | None) -> list[MBItem]:
    """Gets children for the specified item."""
    if item is None:
        return await _get_libraries(hub)

    match item.type:
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
            return await _get_playlist_children(hub, item.id)

    if item.is_folder:
        return await _get_default_children(hub, item.id)

    return []


async def _get_libraries(hub: MediaBrowserHub) -> list[MBItem]:
    if hub.is_emby:
        try:
            root: MBItem = (
                await hub.async_get_items(
                    {"IncludeItemTypes": "UserRootFolder", "Recursive": "true"}
                )
            ).items[0]
        except IndexError:
            return []

        libraries = (
            await hub.async_get_items(
                {
                    "ParentId": root.id,
                    "IncludeItemTypes": "CollectionFolder",
                }
            )
        ).items
    else:
        libraries = (await hub.async_get_libraries()).items

    channels = (await hub.async_get_channels()).items

    return sorted(libraries + channels, key=lambda x: x.name or "")


async def _get_collection(hub: MediaBrowserHub, item: MBItem) -> list[MBItem]:
    match item.collection_type:
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
    return await _get_default_children(hub, item.id)


async def _get_movies(hub: MediaBrowserHub, library: MBItem) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "ParentId": library.id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return [
        _make_virtual_folder("persons", library.id),
        _make_virtual_folder("genres", library.id),
        _make_virtual_folder("studios", library.id),
        _make_virtual_folder("years", library.id),
        _make_virtual_folder("prefixes", library.id),
        _make_virtual_folder("folders", library.id),
    ] + children.items


async def _get_tvshows(hub: MediaBrowserHub, library: MBItem) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "IncludeItemTypes": "Series",
            "Recursive": "true",
            "ParentId": library.id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return [
        _make_virtual_folder("persons", library.id),
        _make_virtual_folder("genres", library.id),
        _make_virtual_folder("studios", library.id),
        _make_virtual_folder("prefixes", library.id),
        _make_virtual_folder("years", library.id),
        _make_virtual_folder("folders", library.id),
    ] + children.items


async def _get_music(hub: MediaBrowserHub, library: MBItem) -> list[MBItem]:
    # emby/jellyfin bug: needs User/Items, Items ignores ParentId
    albums = await hub.async_get_user_items(
        {
            "IncludeItemTypes": "MusicAlbum",
            "Recursive": "true",
            "ParentId": library.id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    videos = await hub.async_get_items(
        {
            "IncludeItemTypes": "MusicVideo",
            "Recursive": "true",
            "ParentId": library.id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return [
        _make_virtual_folder("artists", library.id),
        _make_virtual_folder("album_artists", library.id),
        _make_virtual_folder("composers", library.id),
        _make_virtual_folder("genres", library.id),
        _make_virtual_folder("studios", library.id),
        _make_virtual_folder("prefixes", library.id),
        _make_virtual_folder("years", library.id),
        _make_virtual_folder("playlists", library.id),
        _make_virtual_folder("folders", library.id),
    ] + sorted(
        albums.items + videos.items,
        key=lambda x: x.sort_name if x.sort_name is not None else x.name or "",
    )


async def _get_musicvideos(hub: MediaBrowserHub, library: MBItem) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "IncludeItemTypes": "MusicVideo",
            "Recursive": "true",
            "ParentId": library.id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return [
        _make_virtual_folder("artists", library.id),
        _make_virtual_folder("genres", library.id),
        _make_virtual_folder("prefixes", library.id),
        _make_virtual_folder("years", library.id),
        _make_virtual_folder("folders", library.id),
    ] + children.items


async def _get_audio_books(hub: MediaBrowserHub, library: MBItem) -> list[MBItem]:
    # emby/jellyfin bug: needs User/Items, Items ignores ParentId
    children = await hub.async_get_user_items(
        {
            "IncludeItemTypes": "MusicAlbum",
            "Recursive": "true",
            "ParentId": library.id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return [
        _make_virtual_folder("artists", library.id),
        _make_virtual_folder("genres", library.id),
        _make_virtual_folder("prefixes", library.id),
        _make_virtual_folder("years", library.id),
        _make_virtual_folder("folders", library.id),
    ] + children.items


async def _get_homevideos(hub: MediaBrowserHub, library: MBItem) -> list[MBItem]:
    children = [
        _make_virtual_folder("videos", library.id),
        _make_virtual_folder("photos", library.id),
        _make_virtual_folder("folders", library.id),
    ]

    if hub.is_emby:
        children.append(_make_virtual_folder("tags", library.id))

    return children


async def _get_default_children(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "Recursive": "false",
            "ParentId": parent_id,
            "SortBy": "IsFolder,Filename",
            "SortOrder": "Ascending",
        }
    )
    return children.items


async def _get_playlist_children(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "Recursive": "false",
            "ParentId": parent_id,
            "SortBy": "ListItemOrder",
            "SortOrder": "Ascending",
        }
    )
    return children.items


async def _get_virtual_folder(hub: MediaBrowserHub, item: MBItem) -> list[MBItem]:
    parts = item.id.split("/")
    match parts[0]:
        case "artists":
            return await _get_artists(hub, parts[1])
        case "album_artists":
            return await _get_album_artists(hub, parts[1])
        case "composers":
            return await _get_composers(hub, parts[1])
        case "persons":
            return await _get_persons(hub, parts[1])
        case "genres":
            return await _get_genres(hub, parts[1])
        case "studios":
            return await _get_studios(hub, parts[1])
        case "prefixes":
            return await _get_prefixes(hub, parts[1])
        case "years":
            return await _get_years(hub, parts[1])
        case "folders":
            return await _get_default_children(hub, parts[1])
        case "videos":
            return await _get_videos(hub, parts[1])
        case "photos":
            return await _get_photos(hub, parts[1])
        case "tags":
            return await _get_tags(hub, parts[1])
        case "playlists":
            return await _get_playlists(hub, parts[1])

    raise BrowseMediaError(f"Unsupported virtual folder: {item.id}")


async def _get_playlists(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "IncludeItemTypes": "Playlist",
        }
    )
    return children.items


async def _get_videos(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "IncludeItemTypes": "Video",
        }
    )
    return children.items


async def _get_photos(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "IncludeItemTypes": "Photo",
        }
    )
    return children.items


async def _get_tags(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_items(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "IncludeItemTypes": "Tag",
        }
    )
    return _make_virtual_subfolders("tags", children.items, parent_id)


async def _get_artists(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_artists(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "ArtistType": "Artist,AlbumArtist",
        }
    )

    return _make_virtual_subfolders("artists", children.items, parent_id)


async def _get_composers(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_artists(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "ArtistType": "Composer",
        }
    )

    return _make_virtual_subfolders("composers", children.items, parent_id)


async def _get_album_artists(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_artists(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
            "ArtistType": "AlbumArtist",
        }
    )

    return _make_virtual_subfolders("album_artists", children.items, parent_id)


async def _get_persons(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_persons(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return _make_virtual_subfolders("persons", children.items, parent_id)


async def _get_genres(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_genres(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return _make_virtual_subfolders("genres", children.items, parent_id)


async def _get_prefixes(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_prefixes(
        {
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return _make_virtual_subfolders("prefixes", children, parent_id)


async def _get_years(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_years(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return _make_virtual_subfolders("years", children.items, parent_id)


async def _get_studios(hub: MediaBrowserHub, parent_id: str) -> list[MBItem]:
    children = await hub.async_get_studios(
        {
            "Recursive": "true",
            "ParentId": parent_id,
            "SortBy": "SortName",
            "SortOrder": "Ascending",
        }
    )

    return _make_virtual_subfolders("studios", children.items, parent_id)


def _make_virtual_folder(virtual_id: str, parent_id: str) -> MBItem:
    return MBItem(
        {
            "Id": f"{virtual_id}/{parent_id}",
            "Name": VIRTUAL_FOLDER_MAP[virtual_id],
            "ParentId": parent_id,
            "Type": "Virtual",
            "IsFolder": "true",
        }
    )


def _make_virtual_subfolder(virtual_id: str, item: MBItem, parent_id: str) -> MBItem:
    result = item
    if virtual_id in ["years", "prefixes"]:
        result.id = f"{virtual_id}/{parent_id}/{item.name}"
    else:
        result.id = f"{virtual_id}/{parent_id}/{item.id}"
    result.is_folder = True
    return result


def _make_virtual_subfolders(
    virtual_id: str, items: list[MBItem], parent_id: str
) -> list[MBItem]:
    return [_make_virtual_subfolder(virtual_id, item, parent_id) for item in items]


async def get_item(hub: MediaBrowserHub, item_id: str) -> MBItem:
    """Parses a item identifier and gets the corresponding item."""
    parts = item_id.split("/")
    if len(parts) == 1:
        try:
            return (await hub.async_get_items({"Ids": item_id})).items[0]
        except IndexError as idx:
            raise BrowseMediaError(f"Cannot find item {item_id}") from idx

    if len(parts) == 2:
        return _make_virtual_folder(parts[0], parts[1])

    if len(parts) == 3:
        match parts[0]:
            case "prefixes":
                item = MBItem({"Id": parts[2], "Name": parts[2], "Type": "Prefix"})
            case "years":
                item = MBItem({"Id": parts[2], "Name": parts[2], "Type": "Year"})
            case _:
                try:
                    item = (await hub.async_get_items({"Ids": parts[2]})).items[0]
                except IndexError as idx:
                    raise BrowseMediaError(f"Cannot find item {item_id}") from idx
        return _make_virtual_subfolder(parts[0], item, parts[1])

    raise BrowseMediaError(f"Invalid item identifier {item_id}")


async def _get_virtual_children(hub: MediaBrowserHub, item: MBItem) -> list[MBItem]:
    query = {
        "Recursive": "true",
        "SortBy": "SortName",
        "SortOrder": "Ascending",
    }
    parts = item.id.split("/")
    query["ParentId"] = parts[1]
    if parts[0] in VIRTUAL_FILTER_MAP:
        query[VIRTUAL_FILTER_MAP[parts[0]]] = parts[2]
    else:
        match parts[0]:
            case "prefixes":
                query["NameStartsWith"] = parts[2]
            case _:
                raise BrowseMediaError(f"Unknown virtual folder type: {parts[0]}")

    library = (await hub.async_get_items({"Ids": parts[1]})).items[0]
    match library.collection_type:
        case "movies":
            query["IncludeItemTypes"] = "Movie"
        case "tvshows":
            query["IncludeItemTypes"] = "Series"
        case "music" | "audiobooks":
            query["IncludeItemTypes"] = "MusicAlbum"
        case "musicvideos":
            query["IncludeItemTypes"] = "MusicVideo"
        case "homevideos":
            pass
        case _:
            raise BrowseMediaError(
                f"Unsupported virtual collection type: {library.collection_type}"
            )

    return (await hub.async_get_items(query)).items
