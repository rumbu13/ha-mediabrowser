"""Helpers for the Media Browser (Emby/Jellyfin) integration."""


from .models import MBItem, MBResponse


def list_to_dict(items: list[MBItem]) -> dict[str, MBItem]:
    """Transforms a list in a dictionary."""
    if items is not None:
        return {item.id: item for item in items}
    return {}


def response_to_dict(response: MBResponse) -> dict[str, MBItem]:
    """Transforms a response list in a dictionary."""
    if response is not None:
        return list_to_dict(response.items)
    return {}
