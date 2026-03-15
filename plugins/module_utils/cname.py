# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole CNAME record management utilities.

This module provides functions for managing CNAME DNS records in Pi-hole,
including creating, checking, and deleting CNAME entries.
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


def get_cname_records(client: PiholeApiClient) -> List[str]:
    """
    Get all CNAME records from Pi-hole.

    Args:
        client: Initialized Pi-hole API client

    Returns:
        List of CNAME records in format "cname,target"

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> records = get_cname_records(client)
        >>> print(records)
        ["alias.example.com,target.example.com", "www.local,server.local"]
    """
    try:
        response = client._request("GET", "api/config/dns/cnameRecords")
        response.raise_for_status()

        data = response.json()
        return data.get("config", {}).get("dns", {}).get("cnameRecords", [])

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve CNAME records: {str(e)}")


def check_cname_record_exists(client: PiholeApiClient, cname: str, target: str) -> bool:
    """
    Check if a specific CNAME record exists.

    Args:
        client: Initialized Pi-hole API client
        cname: The alias (CNAME) to check
        target: The canonical name (target) to check

    Returns:
        True if the exact record exists, False otherwise

    Example:
        >>> exists = check_cname_record_exists(
        ...     client, "alias.example.com", "target.example.com"
        ... )
        >>> print(exists)
        True
    """
    records = get_cname_records(client)
    record = f"{cname},{target}"
    return record in records


def add_cname_record(
    client: PiholeApiClient, cname: str, target: str
) -> Dict[str, Any]:
    """
    Add a new CNAME record.

    Per DNS specification, a given alias (CNAME) may only point to
    a single canonical name.

    Args:
        client: Initialized Pi-hole API client
        cname: The alias (CNAME) to create
        target: The canonical name the alias should point to

    Returns:
        API response containing the operation result

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = add_cname_record(
        ...     client, "alias.example.com", "target.example.com"
        ... )
    """
    record = f"{cname},{target}"

    try:
        response = client._request("PUT", f"api/config/dns/cnameRecords/{record}")
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(
            f"Failed to add CNAME record {cname} -> {target}: {str(e)}"
        )


def delete_cname_record(client: PiholeApiClient, cname: str, target: str) -> None:
    """
    Delete a CNAME record.

    Args:
        client: Initialized Pi-hole API client
        cname: The alias (CNAME) to delete
        target: The canonical name (target) of the record to delete

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> delete_cname_record(
        ...     client, "alias.example.com", "target.example.com"
        ... )
    """
    record = f"{cname},{target}"

    try:
        response = client._request("DELETE", f"api/config/dns/cnameRecords/{record}")
        response.raise_for_status()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(
            f"Failed to delete CNAME record {cname} -> {target}: {str(e)}"
        )
