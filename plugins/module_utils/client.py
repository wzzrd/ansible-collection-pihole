#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) Your Name or Organization
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole client management utilities.

This module provides functions for managing client configurations in Pi-hole.
Clients can be identified by IP address, MAC address, hostname, or interface.
"""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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


def get_client(client: PiholeApiClient, client_id: str) -> Optional[Dict[str, Any]]:
    """
    Get details for a specific client.
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
        raise PiholeApiError(f"Failed to retrieve client '{client_id}': {str(e)}")


def add_client(
    client: PiholeApiClient,
    client_id: str,
    comment: Optional[str] = None,  # This is comment_param from the module
    group_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Add a new client configuration.
    """
    data: Dict[str, Any] = {"client": client_id}

    # Only include 'comment' in the payload if it's explicitly provided (not None)
    if comment is not None:
        data["comment"] = comment

    # group_ids are expected to be provided by the module (e.g. [0] for default)
    if group_ids is not None:
        data["groups"] = group_ids
    else:
        # Fallback, though module should always provide it for 'present' state
        data["groups"] = [0]

    try:
        response = client._request("POST", "api/clients", json_data=data)
        response.raise_for_status()
        return response.json()
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to add client '{client_id}': {str(e)}")


def update_client(
    client: PiholeApiClient,
    client_id: str,
    comment: Optional[str] = None,  # This is comment_param from the module
    group_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Update an existing client configuration.
    """
    # URL encode the client identifier
    encoded_client = urllib.parse.quote(client_id)

    data: Dict[str, Any] = {}

    # Only include 'comment' in the PUT payload if it's explicitly provided (not None)
    # If comment_param was None in the module, 'comment' here will be None,
    # and the field will be omitted from the API call, preserving the existing comment.
    if comment is not None:
        data["comment"] = comment

    # group_ids are expected to be provided by the module
    if group_ids is not None:
        data["groups"] = group_ids
    else:
        # Should not happen if module logic is correct; update needs explicit groups.
        # As a safety, fetch current if not provided, though module aims to provide desired state.
        current_client_data = get_client(client, client_id)
        if current_client_data:
            data["groups"] = current_client_data.get("groups", [0])
        else:  # Should have been caught by module if client doesn't exist
            data["groups"] = [0]

    try:
        response = client._request(
            "PUT", f"api/clients/{encoded_client}", json_data=data
        )
        response.raise_for_status()
        return response.json()
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to update client '{client_id}': {str(e)}")


def delete_client(client: PiholeApiClient, client_id: str) -> bool:
    """
    Delete a client configuration.
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
        raise PiholeApiError(f"Failed to delete client '{client_id}': {str(e)}")
