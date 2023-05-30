"""Discovery tools for the Media Browser (Emby/Jellyfin) integration."""
import json
import logging
import socket
from typing import Any

from .const import (
    DISCOVERY_BROADCAST,
    DISCOVERY_MESSAGE_EMBY,
    DISCOVERY_MESSAGE_JELLYFIN,
    DISCOVERY_PORT,
    DISCOVERY_TIMEOUT,
    Discovery,
    ServerType,
)

_LOGGER = logging.getLogger(__package__)

MOCK = True


def discover_mb(timeout: float = DISCOVERY_TIMEOUT) -> list[dict[str, Any]]:
    """Broadcasts all local networks and waits for a response from Emby or Jellyfin servers."""
    if MOCK:
        return [
            {
                "Address": "http://192.168.1.145:8096",
                "Id": "33aeee8e703b4e168a84d63fe37b8dfe",
                "Name": "Rumbuflix",
                "Type": ServerType.EMBY,
            },
            {
                "Address": "http://192.168.1.145:8097",
                "Id": "19a3c6e569704103847360d350995f47",
                "Name": "ZOTAC",
                "EndpointAddress": None,
                "Type": ServerType.JELLYFIN,
            },
        ]
    return _discover_message(
        DISCOVERY_MESSAGE_EMBY, ServerType.EMBY, timeout
    ) + _discover_message(DISCOVERY_MESSAGE_JELLYFIN, ServerType.JELLYFIN, timeout)


def _discover_message(
    message: bytes, server_type: ServerType, timeout: float = DISCOVERY_TIMEOUT
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    interfaces = socket.getaddrinfo(
        host=socket.gethostname(), port=None, family=socket.AF_INET
    )
    all_ip_addresses = [ip[-1][0] for ip in interfaces]
    for ip_address in all_ip_addresses:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(timeout)
            sock.bind((ip_address, 0))
            sock.sendto(message, (DISCOVERY_BROADCAST, DISCOVERY_PORT))
            data = sock.recv(1024)
            discovery = json.loads(data.decode("utf-8"))

            if Discovery.ADDRESS in discovery and Discovery.ID in discovery:
                result.append(discovery | {"Type": server_type})
            else:
                _LOGGER.warning(
                    "Ignored response because id or address is missing "
                    + "from discovery message received from %s",
                    ip_address,
                )
        except TimeoutError:
            _LOGGER.debug("Timeout while waiting for response from %s", ip_address)
        except json.JSONDecodeError:
            _LOGGER.warning("Malformed discovered message received from %s", ip_address)
        finally:
            sock.close()

    return result
