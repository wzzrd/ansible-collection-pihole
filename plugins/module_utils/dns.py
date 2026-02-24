#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) Your Name or Organization
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole DNS record management utilities.

This module provides functions for managing static DNS records (A records)
in Pi-hole, including creating, checking, and deleting DNS entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
        PiholeApiClient,
    )

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeError,
)


def get_static_dns_records(client: PiholeApiClient) -> List[str]:
    """
    Get all static DNS records from Pi-hole.

    Args:
        client: Initialized Pi-hole API client

    Returns:
        List of static DNS records in format "ip name"

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> records = get_static_dns_records(client)
        >>> print(records)
        ["192.168.1.10 printer.local", "192.168.1.20 nas.local"]
    """
    try:
        response = client._request("GET", "api/config/dns/hosts")
        response.raise_for_status()

        data = response.json()
        return data.get("config", {}).get("dns", {}).get("hosts", [])

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve static DNS records: {str(e)}")


def check_static_dns_record_exists(client: PiholeApiClient, ip: str, name: str) -> bool:
    """
    Check if a specific static DNS record exists.

    Args:
        client: Initialized Pi-hole API client
        ip: IP address to check (e.g., "192.168.1.10")
        name: Hostname to check (e.g., "printer.local")

    Returns:
        True if the exact record exists, False otherwise

    Example:
        >>> exists = check_static_dns_record_exists(
        ...     client, "192.168.1.10", "printer.local"
        ... )
        >>> print(exists)
        True
    """
    records = get_static_dns_records(client)
    record = f"{ip} {name}"
    return record in records


def add_static_dns_record(
    client: PiholeApiClient, ip: str, name: str
) -> Dict[str, Any]:
    """
    Add a new static DNS record (A record).

    Args:
        client: Initialized Pi-hole API client
        ip: IP address for the DNS record (e.g., "192.168.1.10")
        name: Hostname for the DNS record (e.g., "printer.local")

    Returns:
        API response containing the operation result

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = add_static_dns_record(
        ...     client, "192.168.1.10", "printer.local"
        ... )
    """
    # URL encode the space as %20
    record = f"{ip}%20{name}"

    try:
        response = client._request("PUT", f"api/config/dns/hosts/{record}")
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to add DNS record for {name} ({ip}): {str(e)}")


def delete_static_dns_record(client: PiholeApiClient, ip: str, name: str) -> None:
    """
    Delete a static DNS record.

    Args:
        client: Initialized Pi-hole API client
        ip: IP address of the record to delete
        name: Hostname of the record to delete

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> delete_static_dns_record(client, "192.168.1.10", "printer.local")
    """
    # URL encode the space as %20
    record = f"{ip}%20{name}"

    try:
        response = client._request("DELETE", f"api/config/dns/hosts/{record}")
        response.raise_for_status()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to delete DNS record for {name} ({ip}): {str(e)}")
