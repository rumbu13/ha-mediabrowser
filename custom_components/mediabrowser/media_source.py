"""The Media Source implementation for the MediaBrowser integration."""


from .errors import BrowseMediaError
from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .browse import get_children, get_item
from .const import DOMAIN, HUB, MEDIA_CLASS_MAP
from .hub import MediaBrowserHub
from .models import MBItem
from .icons import EMBY_ICON, JELLYFIN_ICON

PLAYABLE_MEDIA_TYPES = {"Audio", "Video", "Photo"}


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up MediaBrowser media source."""

    entries = hass.config_entries.async_entries(DOMAIN)
    hubs = [hass.data[DOMAIN][entry.entry_id][HUB] for entry in entries]

    return MBSource(hubs)


class MBSource(MediaSource):
    """Provide MediaBrowser servers as media sources."""

    name: str = "Emby/Jellyfin"

    def __init__(self, hubs: list[MediaBrowserHub]) -> None:
        super().__init__(DOMAIN)
        self.hubs = {hub.server_id: hub for hub in hubs}

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Return a streamable URL and associated mime type."""

        parts = item.identifier.split("/")

        hub = self.hubs[parts[0]]

        media_item = (
            await hub.async_get_items({"Fields": "MediaSources", "Ids": parts[1]})
        ).items[0]

        url: str = None
        match media_item.media_type:
            case "Video":
                url = _get_video_url(hub, media_item)
            case "Audio":
                url = _get_audio_url(hub, media_item.id)
            case "Photo":
                url = _get_photo_url(hub, media_item.id)
            case _:
                raise BrowseMediaError(
                    f"Unsupported media type:{media_item.media_type}"
                )

        if media_item.mime_type is not None:
            return PlayMedia(url, media_item.mime_type)

        raise BrowseMediaError(f"Cannot obtain mime information for {item.id}")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        if not item.identifier:
            return await self._async_browse_hubs()

        p = item.identifier.find("/")
        if p < 0:
            return await self._async_browse(self.hubs[item.identifier], None, True)
        return await self._async_browse(
            self.hubs[item.identifier[0:p]], item.identifier[p + 1 :], True
        )

    async def _async_browse(
        self, hub: MediaBrowserHub, item_id: str, include_children: bool
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
        self, hub: MediaBrowserHub, item: MBItem, include_children: bool
    ) -> BrowseMediaSource:
        if item is None:
            media_class = MediaClass.DIRECTORY
            media_content_type = ""
            media_content_id = hub.server_id
            title = hub.server_name
            can_expand = True
            can_play = False
            thumb = EMBY_ICON if hub.is_emby else JELLYFIN_ICON

        else:
            media_class = MEDIA_CLASS_MAP.get(item.type) or (
                MediaClass.DIRECTORY if item.is_folder else None
            )
            media_content_type = item.mime_type
            thumb = (
                f"{hub.server_url}{item.thumb_url}"
                if item.thumb_url is not None
                else None
            )
            media_content_id = f"{hub.server_id}/{item.id}"
            title = item.name
            can_play = item.media_type in PLAYABLE_MEDIA_TYPES
            can_expand = item.is_folder

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
                if child.is_folder or child.media_type in PLAYABLE_MEDIA_TYPES
            ]

        return result


def _get_audio_url(hub: MediaBrowserHub, item_id: str) -> str | None:
    return f"{hub.server_url}/Audio/{item_id}/universal?UserId={hub.user_id}&api_key={hub.api_key}"


def _get_video_url(hub: MediaBrowserHub, item: MBItem) -> str | None:
    media_source = (
        item.media_sources[0]
        if item.media_sources is not None and len(item.media_sources) > 0
        else None
    )
    if media_source is not None:
        return f"{hub.server_url}/Videos/{item.id}/master.m3u8?api_key={hub.api_key}&MediaSourceId={media_source.id}"
    return None


def _get_photo_url(hub: MediaBrowserHub, item_id: str) -> str | None:
    return f"{hub.server_url}/Items/{item_id}/Images/Primary?api_key={hub.api_key}"
