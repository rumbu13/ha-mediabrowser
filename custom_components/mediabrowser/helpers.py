"""Helpers for the Media Browser (Emby/Jellyfin) integration."""


import logging
import re
from datetime import datetime
from typing import Any

from dateutil import parser
from dateutil.parser import ParserError

from .const import IMAGE_CATEGORIES
from .models import MBItem, MBResponse

_LOGGER = logging.getLogger(__package__)


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


_SNAKE_SUB1 = re.compile("(.)([A-Z][a-z]+)")
_SNAKE_SUB2 = re.compile("([a-z0-9])([A-Z])")


def snake_case(name):
    "Converts a string to snake case"
    name = re.sub(_SNAKE_SUB1, r"\1_\2", name)
    return re.sub(_SNAKE_SUB2, r"\1_\2", name).lower()


def to_float(value: Any, text: str, log_level: int = logging.WARNING) -> float | None:
    """Converts a value to float and logs the result if failed"""
    try:
        return float(value)
    except ValueError:
        _LOGGER.log(log_level, "Invalid float value %s: %s", text, value)
    except OverflowError:
        _LOGGER.warning(log_level, "Overflow float value %s: %s", text, value)
    return None


def to_int(
    value: Any, text: str, default_value=0, log_level: int = logging.WARNING
) -> int | None:
    """Converts a value to int and logs the result if failed"""
    try:
        return int(value)
    except ValueError:
        _LOGGER.log(log_level, "Invalid intger value %s: %s", text, value)
    return default_value


def to_datetime(
    value: Any, text: str, log_level: int = logging.WARNING
) -> datetime | None:
    """Converts a value to datetime and logs the result if failed"""
    try:
        return parser.isoparse(value)
    except ParserError:
        _LOGGER.log(log_level, "Invalid datetime %s: %s", text, value)
    return None


def get_image_url(
    data: dict[str, Any], url: str, item_type: str, parent_fallback: bool = False
) -> str | None:
    """Gets an image falling back to parent (optionally)"""
    image_id: str | None = None
    image_tags = f"{item_type}ImageTags"
    if "ImageTags" in data and item_type in data["ImageTags"]:
        image_id = data["Id"]
    elif image_tags in data and len(data[image_tags]) > 0:
        image_id = data["Id"]
    elif parent_fallback:
        for category in IMAGE_CATEGORIES:
            image_id = get_category_image_url(data, url, item_type, category)
            if image_id is not None:
                break
    return (
        f"{url}/Items/{image_id}/Images/{item_type}" if image_id is not None else None
    )


def get_category_image_url(
    data: dict[str, Any], url: str, item_type: str, category: str
) -> str | None:
    """Gets an image from the specified category"""
    image_id = None
    categ_image_id = f"{category}{item_type}ImageItemId"
    categ_item_id = f"{category}{item_type}ItemId"
    categ_tag = f"{category}{item_type}ImageTag"
    categ_tags = f"{category}{item_type}ImageTags"
    categ_id = f"{category}Id"
    if categ_image_id in data:
        image_id = data[categ_image_id]
    elif categ_item_id in data:
        image_id = data[categ_item_id]
    elif categ_tag in data and categ_id in data:
        image_id = data[categ_id]
    elif categ_tags in data and categ_id in data and len(data[categ_tags]) > 0:
        image_id = data[categ_id]
    return (
        f"{url}/Items/{image_id}/Images/{item_type}" if image_id is not None else None
    )
