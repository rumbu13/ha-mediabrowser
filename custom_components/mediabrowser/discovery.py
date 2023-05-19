"""Discovery tools for the Media Browser (Emby/Jellyfin) integration."""
import json
import logging
import socket

from .models import MBDiscovery, MediaBrowserType

DISCOVERY_TIMEOUT = 1
DISCOVERY_MESSAGE_EMBY = b"who is EmbyServer?"
DISCOVERY_MESSAGE_JELLYFIN = b"who is JellyfinServer?"
DISCOVERY_BROADCAST = "255.255.255.255"
DISCOVERY_PORT = 7359

_LOGGER = logging.getLogger(__package__)

MOCK = True


def discover_mb(timeout: float = DISCOVERY_TIMEOUT) -> list[MBDiscovery]:
    """Broadcasts all local networks and waits for a response from Emby or Jellyfin servers."""
    if MOCK:
        return [
            MBDiscovery(
                {
                    "Address": "http://192.168.1.145:8096",
                    "Id": "33aeee8e703b4e168a84d63fe37b8dfe",
                    "Name": "Rumbuflix",
                },
                MediaBrowserType.EMBY,
            ),
            MBDiscovery(
                {
                    "Address": "http://192.168.1.145:8097",
                    "Id": "19a3c6e569704103847360d350995f47",
                    "Name": "ZOTAC",
                    "EndpointAddress": None,
                },
                MediaBrowserType.JELLYFIN,
            ),
        ]
    return _discover_message(
        DISCOVERY_MESSAGE_EMBY, MediaBrowserType.EMBY, timeout
    ) + _discover_message(
        DISCOVERY_MESSAGE_JELLYFIN, MediaBrowserType.JELLYFIN, timeout
    )


def _discover_message(
    message: bytes, server_type: MediaBrowserType, timeout: float = DISCOVERY_TIMEOUT
) -> list[MBDiscovery]:
    result: list[MBDiscovery] = []
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
            discovery = MBDiscovery(json.loads(data.decode("utf-8")), server_type)

            if discovery.address is not None and discovery.id is not None:
                result.append(discovery)
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
