# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole adlist management utilities.

This module provides functions for managing adlists (blocklists and allowlists)
in Pi-hole, including adding, updating, and removing lists.
"""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
        PiholeApiClient,
    )

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeError,
    PiholeNotFoundError,
    PiholeValidationError,
)


def get_adlist(
    client: PiholeApiClient, address: str, list_type: str = "block"
) -> dict[str, Any] | None:
    """
    Get details for a specific adlist.

    Args:
        client: Initialized Pi-hole API client
        address: URL of the adlist
        list_type: Type of list ("block" or "allow")

    Returns:
        Dict with adlist details if found, None otherwise

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> adlist = get_adlist(
        ...     client,
        ...     "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
        ... )
        >>> if adlist:
        ...     print(f"Adlist enabled: {adlist.get('enabled')}")
    """
    # Build the endpoint with optional query parameter.
    # URL-encode the address so that https:// in the address does not
    # corrupt the URL path (which would strip the ?type= parameter from
    # the request before it reaches Pi-hole, causing "bad_request" warnings).
    encoded_address = urllib.parse.quote(address, safe="")
    endpoint = f"api/lists/{encoded_address}"
    if list_type:
        endpoint += f"?type={list_type}"

    try:
        response = client._request("GET", endpoint)

        if response.status_code == 404:
            return None

        response.raise_for_status()

        lists = response.json().get("lists", [])
        return lists[0] if lists else None

    except PiholeNotFoundError:
        return None
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve adlist '{address}': {e}")


def add_adlist(
    client: PiholeApiClient,
    address: str,
    list_type: str = "block",
    comment: str | None = None,
    group_ids: list[int] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """
    Add a new adlist.

    Args:
        client: Initialized Pi-hole API client
        address: URL of the adlist to add
        list_type: Type of list ("block" or "allow")
        comment: Optional comment for the adlist
        group_ids: Optional list of group IDs to associate
        enabled: Whether the adlist is enabled (default: True)

    Returns:
        API response containing the created adlist

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = add_adlist(
        ...     client,
        ...     "https://someblocked.hosts/list.txt",
        ...     comment="Community maintained blocklist",
        ...     group_ids=[0, 1]
        ... )
    """
    data: dict[str, Any] = {"address": address, "enabled": enabled}

    if comment is not None:
        data["comment"] = comment

    if group_ids is not None:
        data["groups"] = group_ids

    try:
        response = client._request(
            "POST", f"api/lists?type={list_type}", json_data=data
        )
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to add adlist '{address}' as {list_type}: {e}")


def update_adlist(
    client: PiholeApiClient,
    address: str,
    list_type: str | None = None,
    comment: str | None = None,
    group_ids: list[int] | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """
    Update an existing adlist.

    Args:
        client: Initialized Pi-hole API client
        address: URL of the adlist to update
        list_type: New type for the adlist (None preserves existing)
        comment: New comment (None preserves existing)
        group_ids: New list of group IDs (None preserves existing)
        enabled: New enabled status (None preserves existing)

    Returns:
        API response containing the updated adlist

    Raises:
        PiholeValidationError: If the adlist doesn't exist
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = update_adlist(
        ...     client,
        ...     "https://someblocked.hosts/list.txt",
        ...     enabled=False,
        ...     comment="Temporarily disabled"
        ... )
    """
    # Get current adlist details
    current_adlist = get_adlist(client, address)

    if not current_adlist:
        raise PiholeValidationError(f"Adlist '{address}' does not exist")

    encoded_address = urllib.parse.quote(address, safe="")
    query_type = f"?type={list_type}" if list_type else ""
    endpoint = f"api/lists/{encoded_address}{query_type}"

    # Build the data preserving existing values
    data: dict[str, Any] = {}

    if list_type is not None:
        data["type"] = list_type

    data["comment"] = (
        comment if comment is not None else current_adlist.get("comment", "")
    )
    data["groups"] = (
        group_ids if group_ids is not None else current_adlist.get("groups", [0])
    )
    data["enabled"] = (
        enabled if enabled is not None else current_adlist.get("enabled", True)
    )

    try:
        response = client._request("PUT", endpoint, json_data=data)
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to update adlist '{address}': {e}")


def delete_adlist(
    client: PiholeApiClient, address: str, list_type: str = "block"
) -> dict[str, Any]:
    """
    Delete an adlist.

    Args:
        client: Initialized Pi-hole API client
        address: URL of the adlist to delete
        list_type: Type of list ("block" or "allow")

    Returns:
        Success response with message

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = delete_adlist(
        ...     client,
        ...     "https://someblocked.hosts/list.txt"
        ... )
        >>> print(result["message"])
    """
    encoded_address = urllib.parse.quote(address, safe="")
    query_type = f"?type={list_type}" if list_type else ""
    endpoint = f"api/lists/{encoded_address}{query_type}"

    try:
        response = client._request("DELETE", endpoint)

        if response.status_code == 404:
            return {"success": False, "message": f"Adlist '{address}' not found"}

        response.raise_for_status()

        # Handle empty successful responses
        if response.status_code == 204 or not response.text:
            return {
                "success": True,
                "message": f"Adlist '{address}' deleted successfully",
            }

        # Try to parse as JSON, fall back to success message
        try:
            return response.json()
        except ValueError:
            return {
                "success": True,
                "message": f"Adlist '{address}' deleted successfully",
                "raw_response": response.text,
            }

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to delete adlist '{address}': {e}")
