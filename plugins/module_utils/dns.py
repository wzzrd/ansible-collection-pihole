# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole DNS record management utilities.

This module provides functions for managing static DNS records (A records)
in Pi-hole, including creating, checking, and deleting DNS entries.
"""

from __future__ import annotations

import ipaddress
import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

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
    record = urllib.parse.quote(f"{ip} {name}", safe="")

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
    record = urllib.parse.quote(f"{ip} {name}", safe="")

    try:
        response = client._request("DELETE", f"api/config/dns/hosts/{record}")
        response.raise_for_status()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to delete DNS record for {name} ({ip}): {str(e)}")


def parse_dns_records(raw_records: List[str]) -> List[Tuple[str, str]]:
    """
    Parse raw DNS record strings into (ip, name) tuples.

    Args:
        raw_records: List of strings in "ip name" format as returned by Pi-hole

    Returns:
        List of (ip, name) tuples for records that have both fields
    """
    result = []
    for rec_str in raw_records:
        parts = rec_str.split(None, 1)
        if len(parts) == 2:
            result.append((parts[0], parts[1]))
    return result


def find_conflicting_dns_records(
    parsed_records: List[Tuple[str, str]], ip: str, name: str
) -> List[Tuple[str, str]]:
    """
    Find existing DNS records that conflict with adding the given ip/name pair.

    Two conflict rules apply:
    - Same IP mapped to a different name is always a conflict.
    - Same name mapped to a different IP is a conflict only within the same address
      family: an A record and an AAAA record for the same hostname legitimately
      coexist and are not treated as conflicts.

    Args:
        parsed_records: Existing records as (ip, name) tuples
        ip: IP address of the record to be added
        name: Hostname of the record to be added

    Returns:
        List of (ip, name) tuples that must be removed to satisfy uniqueness
    """
    conflicts = []
    for rec_ip, rec_name in parsed_records:
        if rec_ip == ip and rec_name == name:
            continue  # exact match, not a conflict

        if rec_ip == ip:
            conflicts.append((rec_ip, rec_name))
        elif rec_name == name:
            try:
                same_family = (
                    ipaddress.ip_address(rec_ip).version
                    == ipaddress.ip_address(ip).version
                )
            except ValueError:
                same_family = True  # conservative: treat as conflict if unparseable
            if same_family:
                conflicts.append((rec_ip, rec_name))

    return conflicts
