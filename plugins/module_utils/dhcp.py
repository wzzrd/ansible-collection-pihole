# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole DHCP reservation management utilities.

This module provides functions for managing DHCP reservations in Pi-hole,
including creating, checking, and deleting static DHCP leases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
        PiholeApiClient,
    )

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeError,
)


def get_dhcp_reservations(client: PiholeApiClient) -> list[str]:
    """
    Get all DHCP reservations from Pi-hole.

    Args:
        client: Initialized Pi-hole API client

    Returns:
        List of DHCP reservations in format "hw,ip,name"

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> reservations = get_dhcp_reservations(client)
        >>> print(reservations)
        ["00:11:22:33:44:55,192.168.1.100,laptop.local"]
    """
    try:
        response = client._request("GET", "api/config/dhcp/hosts")
        response.raise_for_status()

        data = response.json()
        return data.get("config", {}).get("dhcp", {}).get("hosts", [])

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve DHCP reservations: {e}")


def check_dhcp_reservation_exists(
    client: PiholeApiClient, hw: str, ip: str, name: str
) -> bool:
    """
    Check if a specific DHCP reservation exists.

    Args:
        client: Initialized Pi-hole API client
        hw: MAC address (e.g., "00:11:22:33:44:55")
        ip: IP address to check (e.g., "192.168.1.100")
        name: Hostname to check (e.g., "laptop.local")

    Returns:
        True if the exact reservation exists, False otherwise

    Example:
        >>> exists = check_dhcp_reservation_exists(
        ...     client, "00:11:22:33:44:55", "192.168.1.100", "laptop.local"
        ... )
        >>> print(exists)
        True
    """
    reservations = get_dhcp_reservations(client)
    reservation = f"{hw},{ip},{name}".lower()
    return reservation in [r.lower() for r in reservations]


def add_dhcp_reservation(
    client: PiholeApiClient, hw: str, ip: str, name: str
) -> dict[str, Any]:
    """
    Add a new DHCP reservation.

    Args:
        client: Initialized Pi-hole API client
        hw: MAC address (e.g., "00:11:22:33:44:55")
        ip: IP address to reserve (e.g., "192.168.1.100")
        name: Hostname for the reservation (e.g., "laptop.local")

    Returns:
        API response containing the operation result

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = add_dhcp_reservation(
        ...     client, "00:11:22:33:44:55", "192.168.1.100", "laptop.local"
        ... )
    """
    reservation = f"{hw.lower()},{ip},{name}"

    try:
        response = client._request("PUT", f"api/config/dhcp/hosts/{reservation}")
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to add DHCP reservation for {hw}: {e}")


def delete_dhcp_reservation(
    client: PiholeApiClient, hw: str, ip: str, name: str
) -> None:
    """
    Delete a DHCP reservation.

    Args:
        client: Initialized Pi-hole API client
        hw: MAC address of the reservation to delete
        ip: IP address of the reservation to delete
        name: Hostname of the reservation to delete

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> delete_dhcp_reservation(
        ...     client, "00:11:22:33:44:55", "192.168.1.100", "laptop.local"
        ... )
    """
    reservation = f"{hw.lower()},{ip},{name}"

    try:
        response = client._request("DELETE", f"api/config/dhcp/hosts/{reservation}")
        response.raise_for_status()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to delete DHCP reservation for {hw}: {e}")
