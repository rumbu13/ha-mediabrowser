"""Browse implementation for Media Browser (Emby/Jellyfin) integration."""


import logging
from typing import Any

from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_player.browse_media import BrowseMedia

from .browse import get_children, get_item
from .const import (
    ID_NONE,
    MEDIA_CLASS_MAP,
    MEDIA_CLASS_NONE,
    MEDIA_TYPE_MAP,
    MEDIA_TYPE_NONE,
    PLAYABLE_FOLDERS,
    TITLE_NONE,
    TYPE_NONE,
    ImageType,
    Item,
)
from .helpers import get_image_url
from .hub import MediaBrowserHub

_LOGGER = logging.getLogger(__name__)


async def async_browse_media(
    hub: MediaBrowserHub,
    item: dict[str, Any] | None,
    playable_types: list[str] | None,
    include_children: bool,
) -> BrowseMedia:
    """Browses the specified item."""

    if item is None:
        media_class = MediaClass.DIRECTORY
        media_content_type = TYPE_NONE
        media_content_id = "root"
        title = ""
        thumb = None
        can_expand = True
        can_play = False

    else:
        item_type: str = item.get(Item.TYPE, "")
        media_type: str = item.get(Item.MEDIA_TYPE, MEDIA_TYPE_NONE)
        is_folder: bool = item.get(Item.IS_FOLDER, False)

        media_class = MEDIA_CLASS_MAP.get(
            item_type, MediaClass.DIRECTORY if is_folder else MEDIA_CLASS_NONE
        )
        media_content_type = MEDIA_TYPE_MAP.get(item_type, item_type)
        thumb = (
            get_image_url(item, hub.server_url, ImageType.THUMB, True)
            or get_image_url(item, hub.server_url, ImageType.PRIMARY, True)
            or get_image_url(item, hub.server_url, ImageType.BACKDROP, True)
            or get_image_url(item, hub.server_url, ImageType.SCREENSHOT, True)
        )

        media_content_id = item.get(Item.ID, ID_NONE)
        title = item.get(Item.NAME, TITLE_NONE)
        can_play = (is_folder and item_type in PLAYABLE_FOLDERS) or (
            playable_types is not None and media_type in playable_types
        )
        can_expand = is_folder

    result = BrowseMedia(
        media_class=media_class,
        media_content_id=media_content_id,
        media_content_type=media_content_type,
        title=title,
        can_play=can_play,
        can_expand=can_expand,
        thumbnail=thumb,
        children_media_class=None,
    )

    if include_children:
        result.children = [
            await async_browse_media(hub, child, playable_types, False)
            for child in await get_children(hub, item)
            if child.get(Item.IS_FOLDER, False)
            or (
                playable_types is not None
                and child.get(Item.MEDIA_TYPE, MEDIA_TYPE_NONE) in playable_types
            )
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
