"""Helpers for the Media Browser (Emby/Jellyfin) integration."""


import logging
import re
from typing import Any

from dateutil import parser
from dateutil.parser import ParserError

from .const import (
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_USER,
    ImageCategory,
    ImageType,
    ItemType,
    Key,
)

_LOGGER = logging.getLogger(__package__)


_SNAKE_SUB1 = re.compile("(.)([A-Z][a-z]+)")
_SNAKE_SUB2 = re.compile("([a-z0-9])([A-Z])")


def snake_case(name):
    "Converts a string to snake case"
    name = re.sub(_SNAKE_SUB1, r"\1_\2", name)
    return re.sub(_SNAKE_SUB2, r"\1_\2", name).lower()


def get_image_url(
    data: dict[str, Any], url: str, image_type: ImageType, parent_fallback: bool = False
) -> str | None:
    """Gets an image falling back to parent (optionally)"""
    image_id: str | None = None
    parts = data[Key.ID].split("/")
    real_id: str = parts[0] if len(parts) == 0 else parts[-1]
    image_tags = f"{image_type}ImageTags"
    if Key.IMAGE_TAGS in data and image_type in data[Key.IMAGE_TAGS]:
        image_id = real_id
    elif image_tags in data and len(data[image_tags]) > 0:
        image_id = real_id
    elif parent_fallback:
        for category in ImageCategory:
            image_url = get_category_image_url(data, url, image_type, category)
            if image_url is not None:
                return image_url
        return None
    return (
        f"{url}/Items/{image_id}/Images/{image_type}" if image_id is not None else None
    )


def get_category_image_url(
    data: dict[str, Any], url: str, image_type: ImageType, category: ImageCategory
) -> str | None:
    """Gets an image from the specified category"""
    image_id = None
    categ_image_id = f"{category}{image_type}ImageItemId"
    categ_item_id = f"{category}{image_type}ItemId"
    categ_tag = f"{category}{image_type}ImageTag"
    categ_tags = f"{category}{image_type}ImageTags"
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
        f"{url}/Items/{image_id}/Images/{image_type}" if image_id is not None else None
    )


def build_sensor_key_from_config(config: dict[str, str]) -> str:
    """Returns a key for a latest sensor"""
    return build_sensor_key(
        config[CONF_SENSOR_USER],
        ItemType(config[CONF_SENSOR_ITEM_TYPE]),
        config[CONF_SENSOR_LIBRARY],
    )


def build_sensor_key(user: str, item_type: ItemType, library_id: str) -> str:
    """Returns a key for a latest sensor"""
    return f"{user}-{item_type}-{library_id}"


def extract_sensor_key(unique_id: str) -> str:
    """Gets a sensor key by dropping server id from the beginning and sensor type from the end"""
    parts = unique_id.split("-")
    return "-".join(parts[1:-1])


def extract_player_key(unique_id: str) -> str:
    """Gets a session key by dropping server id from the beginning and entity type from the end"""
    parts = unique_id.split("-")
    return "-".join(parts[1:-1])


def get_player_key(session: dict[str, Any]) -> str:
    """Gets a unique session key"""
    return f"{session[Key.DEVICE_ID]}-{session[Key.CLIENT]}"


def is_float(val: Any, log_level: int = logging.NOTSET) -> bool:
    """Checks if val can be converted to int"""
    try:
        _ = float(val)
    except ValueError:
        if log_level != logging.NOTSET:
            _LOGGER.log(log_level, "Invalid float value: %s", val)
        return False
    except OverflowError:
        if log_level != logging.NOTSET:
            _LOGGER.log(log_level, "Overflow while converting to float: %s", val)
        return False
    return True


def is_int(val: Any, log_level: int = logging.NOTSET) -> bool:
    """Checks if val can be converted to int"""
    try:
        _ = int(val)
    except ValueError:
        if log_level != logging.NOTSET:
            _LOGGER.log(log_level, "Invalid int value: %s", val)
        return False
    return True


def is_datetime(val: Any, log_level: int = logging.NOTSET) -> bool:
    """Checks if val can be converted to int"""
    try:
        _ = parser.isoparse(val)
    except ParserError:
        if log_level != logging.NOTSET:
            _LOGGER.log(log_level, "Invalid date value: %s", val)
        return False
    return True


def autolog(message):
    "Automatically log the current function details."
    import inspect

    # Get the previous frame in the stack, otherwise it would
    # be this function!!!
    func = inspect.currentframe().f_back.f_code
    # Dump the message + the name of this function to the log.
    _LOGGER.debug(
        "%s: %s in %s:%i", message, func.co_name, func.co_filename, func.co_firstlineno
    )
