"""The Media Source implementation for the MediaBrowser integration."""

import logging
from typing import Any

from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .browse import get_children, get_item, get_stream_url
from .const import (
    DATA_HUB,
    DOMAIN,
    MEDIA_CLASS_MAP,
    MEDIA_CLASS_NONE,
    MEDIA_TYPE_MAP,
    MEDIA_TYPE_NONE,
    TITLE_NONE,
    ImageType,
    Item,
    Query,
    Response,
    ServerType,
)
from .errors import BrowseMediaError
from .helpers import get_image_url
from .hub import MediaBrowserHub
from .icons import EMBY_ICON, JELLYFIN_ICON

_LOGGER = logging.getLogger(__name__)

PLAYABLE_MEDIA_TYPES = {"Audio", "Video", "Photo"}


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up MediaBrowser media source."""

    entries = hass.config_entries.async_entries(DOMAIN)
    hubs = [hass.data[DOMAIN][entry.entry_id][DATA_HUB] for entry in entries]

    return MBSource(hubs)


class MBSource(MediaSource):
    """Provide MediaBrowser servers as media sources."""

    name: str = "Emby/Jellyfin"

    def __init__(self, hubs: list[MediaBrowserHub]) -> None:
        """Create a new media source."""
        super().__init__(DOMAIN)
        self.hubs = {hub.server_id: hub for hub in hubs}

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Return a streamable URL and associated mime type."""

        parts = item.identifier.split("/")

        hub = self.hubs[parts[0]]

        media_item = (
            await hub.async_get_items(
                {Query.FIELDS: Item.MEDIA_SOURCES, Query.IDS: parts[1]}
            )
        )[Response.ITEMS][0]

        url: str | None = None
        match media_item.get(Item.MEDIA_TYPE, ""):
            case "Video" | "Audio":
                url, mime_type = await get_stream_url(
                    hub, parts[1], media_item.get(Item.MEDIA_TYPE)
                )
            case "Photo":
                url = _get_photo_url(hub, parts[1])
                mime_type = "image/jpeg"
            case _:
                raise BrowseMediaError(
                    f"Unsupported media type:{media_item.get(Item.MEDIA_TYPE, '')}"
                )

        if mime_type is not None and url is not None:
            return PlayMedia(url, mime_type)

        raise BrowseMediaError(f"Cannot obtain mime information for {item.identifier}")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse the specified item."""
        if not item.identifier:
            return await self._async_browse_hubs()

        pos = item.identifier.find("/")
        if pos < 0:
            return await self._async_browse(self.hubs[item.identifier], None, True)
        return await self._async_browse(
            self.hubs[item.identifier[0:pos]], item.identifier[pos + 1 :], True
        )

    async def _async_browse(
        self, hub: MediaBrowserHub, item_id: str | None, include_children: bool
    ) -> BrowseMediaSource:
        """Browses the specified item."""
        if item_id is None:
            item = None
        else:
            item = await get_item(hub, item_id)

        return await self._async_browse_item(hub, item, include_children)

    async def _async_browse_hubs(self) -> BrowseMediaSource:
        source = BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title="Media Browser",
            can_play=False,
            can_expand=True,
            thumbnail=EMBY_ICON,
        )
        source.children = [
            await self._async_browse(hub, None, False) for hub in self.hubs.values()
        ]
        source.children_media_class = MediaClass.DIRECTORY

        return source

    async def _async_browse_item(
        self, hub: MediaBrowserHub, item: dict[str, Any] | None, include_children: bool
    ) -> BrowseMediaSource:
        if item is None:
            media_class = MediaClass.DIRECTORY
            media_content_type = MEDIA_TYPE_NONE
            media_content_id = hub.server_id
            title = hub.name
            can_expand = True
            can_play = False
            thumb = EMBY_ICON if hub.server_type == ServerType.EMBY else JELLYFIN_ICON

        else:
            item_type: str = item.get(Item.TYPE, "")
            media_type: str = item.get(Item.MEDIA_TYPE, MEDIA_TYPE_NONE)
            is_folder: bool = item.get(Item.IS_FOLDER, False)

            media_class = MEDIA_CLASS_MAP.get(
                item_type, MediaClass.DIRECTORY if is_folder else MEDIA_CLASS_NONE
            )
            media_content_type = MEDIA_TYPE_MAP.get(item_type, item_type)
            thumb = thumb = (
                get_image_url(item, hub.server_url, ImageType.THUMB, True)
                or get_image_url(item, hub.server_url, ImageType.PRIMARY, True)
                or get_image_url(item, hub.server_url, ImageType.BACKDROP, True)
                or get_image_url(item, hub.server_url, ImageType.SCREENSHOT, True)
            )
            media_content_id = f"{hub.server_id}/{item.get(Item.ID)}"
            title = item.get(Item.NAME, TITLE_NONE)
            can_play = media_type in PLAYABLE_MEDIA_TYPES
            can_expand = is_folder

        result = BrowseMediaSource(
            domain=DOMAIN,
            media_class=media_class,
            identifier=media_content_id,
            media_content_type=media_content_type,
            title=title,
            can_play=can_play,
            can_expand=can_expand,
            thumbnail=thumb,
            children_media_class=None,
        )

        if include_children:
            result.children = [
                await self._async_browse_item(hub, child, False)
                for child in await get_children(hub, item)
                if child.get(Item.IS_FOLDER, False)
                or child.get(Item.MEDIA_TYPE, MEDIA_TYPE_NONE) in PLAYABLE_MEDIA_TYPES
            ]

        return result


def _get_photo_url(hub: MediaBrowserHub, item_id: str) -> str | None:
    return f"{hub.server_url}/Items/{item_id}/Images/Primary?api_key={hub.api_key}"
