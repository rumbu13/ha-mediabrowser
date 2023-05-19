"""Browse implementation for Media Browser (Emby/Jellyfin) integration."""

import logging

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_player.browse_media import BrowseMedia

from .browse import get_children, get_item
from .const import MEDIA_CLASS_MAP, MEDIA_TYPE_MAP
from .hub import MediaBrowserHub
from .models import MBItem

_LOGGER = logging.getLogger(__name__)

MEDIA_CLASS_NONE = ""
MEDIA_TYPE_NONE = ""

CONTENT_TYPE_MAP = {
    "Audio": MediaType.MUSIC,
    "AudioBook": MediaType.PODCAST,
    "Book": MediaType.APP,
    "Episode": MediaType.EPISODE,
    "Season": MediaType.SEASON,
    "Series": MediaType.TVSHOW,
    "Movie": MediaType.MOVIE,
    "Playlist": MediaType.PLAYLIST,
}

PLAYABLE_FOLDERS = {
    "BoxSet",
    "Genre",
    "LiveTvChannel",
    "ManualPlaylistFolder",
    "MusicAlbum",
    "MusicGenre",
    "PhotoAlbum",
    "Playlist",
    "PlaylistFolder",
    "Season",
    "Series",
}


async def async_browse_media(
    hub: MediaBrowserHub,
    item: MBItem | None,
    playable_types: list[str] | None,
    include_children: bool,
) -> BrowseMedia:
    """Browses the specified item."""
    if item is None:
        media_class = MediaClass.DIRECTORY
        media_content_type = ""
        media_content_id = "root"
        title = ""
        thumb = None
        can_expand = True
        can_play = False

    else:
        media_class = MEDIA_CLASS_MAP.get(item.type or "") or (
            MediaClass.DIRECTORY if item.is_folder else MEDIA_CLASS_NONE
        )
        media_content_type = MEDIA_TYPE_MAP.get(item.type or "") or ""
        thumb = item.thumb_url
        media_content_id = item.id
        title = item.name or "Unknown"
        can_play = (item.is_folder and item.type in PLAYABLE_FOLDERS) or (
            playable_types is not None and item.media_type in playable_types
        )

        can_expand = item.is_folder or False

    result = BrowseMedia(
        media_class=media_class,
        media_content_id=media_content_id,
        media_content_type=media_content_type,
        title=title,
        can_play=can_play,
        can_expand=can_expand,
        thumbnail=f"{hub.server_url}{thumb}" if thumb is not None else None,
        children_media_class=None,
    )

    if include_children:
        result.children = [
            await async_browse_media(hub, child, playable_types, False)
            for child in await get_children(hub, item)
            if child.is_folder
            or (playable_types is not None and child.media_type in playable_types)
        ]

    return result


async def async_browse_media_id(
    hub: MediaBrowserHub,
    item_id: str | None,
    playable_types: list[str] | None,
    include_children: bool,
) -> BrowseMedia:
    """Browses the specified item."""
    if item_id is None:
        item = None
    else:
        item = await get_item(hub, item_id)

    return await async_browse_media(hub, item, playable_types, include_children)
