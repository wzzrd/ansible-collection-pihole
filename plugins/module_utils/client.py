# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole client management utilities.

This module provides functions for managing client configurations in Pi-hole.
Clients can be identified by IP address, MAC address, hostname, or interface.
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
)


def get_client(client: PiholeApiClient, client_id: str) -> dict[str, Any] | None:
    """
    Get details for a specific client.

    Args:
        client: Initialized Pi-hole API client
        client_id: IP address, MAC address, hostname, or interface of the client

    Returns:
        Dict with client details if found, None otherwise

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    encoded_client = urllib.parse.quote(client_id)
    try:
        response = client._request("GET", f"api/clients/{encoded_client}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        clients = response.json().get("clients", [])
        return clients[0] if clients else None
    except PiholeNotFoundError:
        return None
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve client '{client_id}': {e}")


def add_client(
    client: PiholeApiClient,
    client_id: str,
    comment: str | None = None,  # This is comment_param from the module
    group_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Add a new client configuration.

    Args:
        client: Initialized Pi-hole API client
        client_id: IP address, MAC address, hostname, or interface of the client
        comment: Optional comment for the client
        group_ids: List of group IDs to associate (defaults to [0])

    Returns:
        API response containing the created client

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    data: dict[str, Any] = {
        "client": client_id,
        "groups": group_ids if group_ids is not None else [0],
    }

    if comment is not None:
        data["comment"] = comment

    try:
        response = client._request("POST", "api/clients", json_data=data)
        response.raise_for_status()
        return response.json()
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to add client '{client_id}': {e}")


def update_client(
    client: PiholeApiClient,
    client_id: str,
    group_ids: list[int],
    comment: str | None = None,
) -> dict[str, Any]:
    """
    Update an existing client configuration.

    Args:
        client: Initialized Pi-hole API client
        client_id: IP address, MAC address, hostname, or interface of the client
        group_ids: New list of group IDs to assign (caller must resolve these before calling)
        comment: New comment (None omits the field, preserving the existing value)

    Returns:
        API response containing the updated client

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    encoded_client = urllib.parse.quote(client_id)

    data: dict[str, Any] = {"groups": group_ids}

    if comment is not None:
        data["comment"] = comment

    try:
        response = client._request(
            "PUT", f"api/clients/{encoded_client}", json_data=data
        )
        response.raise_for_status()
        return response.json()
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to update client '{client_id}': {e}")


def delete_client(client: PiholeApiClient, client_id: str) -> bool:
    """
    Delete a client configuration.

    Args:
        client: Initialized Pi-hole API client
        client_id: IP address, MAC address, hostname, or interface of the client

    Returns:
        True if deleted, False if not found

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    encoded_client = urllib.parse.quote(client_id)
    try:
        response = client._request("DELETE", f"api/clients/{encoded_client}")
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True
    except PiholeNotFoundError:
        return False
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to delete client '{client_id}': {e}")
