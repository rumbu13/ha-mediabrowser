"""Entity base class for the Media Browser (Emby/Jellyfin) integration."""

from homeassistant.exceptions import HomeAssistantError


class RequestError(HomeAssistantError):
    """Error to indicate an invalid response."""


class ForbiddenError(RequestError):
    """Error to indicate that acces to a resource is forbidden (403)."""


class UnauthorizedError(RequestError):
    """Error to indicate that access to a resource is unauthorized (401)."""


class NotFoundError(RequestError):
    """Error to indicate that a resource cannot be found (404)."""


class ConnectError(HomeAssistantError):
    """Error to indicate that a coonection cannot be established."""


class MismatchError(HomeAssistantError):
    """Error to indicate that there is a mismatch between expected and real server unique id."""


class BrowseMediaError(HomeAssistantError):
    """Error to indicate that a browsing operation failed."""
