"""Helpers for the Media Browser (Emby/Jellyfin) integration."""


from datetime import datetime
import logging
import re
from typing import Any

from dateutil import parser
from dateutil.parser import ParserError
import inspect

from .const import (
    CONF_SENSOR_ITEM_TYPE,
    CONF_SENSOR_LIBRARY,
    CONF_SENSOR_USER,
    ImageCategory,
    ImageType,
    ItemType,
    Item,
)

_LOGGER = logging.getLogger(__package__)


_SNAKE_SUB1 = re.compile("(.)([A-Z][a-z]+)")
_SNAKE_SUB2 = re.compile("([a-z0-9])([A-Z])")


def snake_case(name: str):
    "Converts a string to snake case"
    name = re.sub(_SNAKE_SUB1, r"\1_\2", name)
    return re.sub(_SNAKE_SUB2, r"\1_\2", name).lower()


def camel_case(name: str):
    "Converts a string to camel case"
    name = "".join([part.capitalize() for part in name.split("_")])


def get_image_url(
    data: dict[str, Any], url: str, image_type: ImageType, parent_fallback: bool = False
) -> str | None:
    """Gets an image falling back to parent (optionally)"""
    image_id: str | None = None
    parts = data[Item.ID].split("/")
    real_id: str = parts[0] if len(parts) == 0 else parts[-1]
    image_tags = f"{image_type}ImageTags"
    if Item.IMAGE_TAGS in data and image_type in data[Item.IMAGE_TAGS]:
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


def as_datetime(
    data: dict[str, Any], key: str, log_level: int = logging.DEBUG
) -> datetime | None:
    """Checks if val can be converted to datetime and logs failure optionaly"""
    if dateval := data.get(key):
        if isinstance(dateval, datetime):
            return dateval
        try:
            result = parser.isoparse(dateval)
        except ParserError:
            if log_level != logging.NOTSET:
                _LOGGER.log(
                    log_level, "Invalid date/time value for %s: %s", key, dateval
                )
        else:
            return result
    return None


def as_int(
    data: dict[str, Any], key: str, log_level: int = logging.DEBUG
) -> int | None:
    """Checks if val can be converted to int and logs failure optionaly"""
    if intval := data.get(key):
        if isinstance(intval, int):
            return intval
        try:
            result = int(intval)
        except ValueError:
            if log_level != logging.NOTSET:
                _LOGGER.log(log_level, "Invalid integral value for %s: %s", key, intval)
        else:
            return result
    return None


def as_float(
    data: dict[str, Any], key: str, log_level: int = logging.DEBUG
) -> float | None:
    """Checks if val can be converted to int and logs failure optionaly"""
    if floatval := data.get(key):
        if isinstance(floatval, float):
            return floatval
        try:
            result = float(floatval)
        except (ValueError, OverflowError):
            if log_level != logging.NOTSET:
                _LOGGER.log(log_level, "Invalid float value for %s: %s", key, floatval)
        else:
            return result
    return None


def as_bool(
    data: dict[str, Any], key: str, log_level: int = logging.DEBUG
) -> bool | None:
    """Checks if val can be converted to int and logs failure optionaly"""
    if boolval := data.get(key):
        if isinstance(boolval, bool):
            return boolval
        elif isinstance(boolval, str):
            bool_str = boolval.lower()
            if bool_str == "true":
                return True
            if bool_str == "false":
                return False
        if log_level != logging.NOTSET:
            _LOGGER.log(log_level, "Invalid bool value for %s: %s", key, boolval)

    return None


def snake_cased_json(original: Any | None) -> Any | None:
    """Convert an entire json object to snake case"""
    if original is None:
        return None
    if isinstance(original, dict):
        result = {}
        for key, value in original.items():
            result[snake_case(key)] = snake_cased_json(value)
        return result
    elif isinstance(original, list):
        return [snake_cased_json(item) for item in original]
    else:
        return original


def camel_cased_json(original: Any | None) -> Any | None:
    """Convert an entire json object to camel case"""
    if original is None:
        return None
    if isinstance(original, dict):
        result = {}
        for key, value in original.items():
            result[camel_case(key)] = camel_cased_json(value)
        return result
    elif isinstance(original, list):
        return [camel_cased_json(item) for item in original]
    else:
        return original


def autolog(message):
    "Automatically log the current function details."
    func = inspect.currentframe().f_back.f_code  # type: ignore
    _LOGGER.debug(
        "%s: %s in %s:%i", message, func.co_name, func.co_filename, func.co_firstlineno
    )
