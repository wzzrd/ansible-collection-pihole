#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) Your Name or Organization
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole group management utilities.

This module provides functions for managing groups in Pi-hole,
including creating, updating, deleting, and querying groups.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

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


def get_groups(client: PiholeApiClient) -> Dict[str, int]:
    """
    Retrieve all groups and map names to IDs.

    Args:
        client: Initialized Pi-hole API client

    Returns:
        Dictionary mapping group names to their IDs

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> groups = get_groups(client)
        >>> print(groups)
        {"Default": 0, "IoT_Devices": 1, "Kids_Devices": 2}
    """
    try:
        response = client._request("GET", "api/groups")
        response.raise_for_status()

        groups_data = response.json().get("groups", [])
        return {group.get("name"): group.get("id") for group in groups_data}

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve groups: {str(e)}")


def get_group(client: PiholeApiClient, name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific group by name.

    Args:
        client: Initialized Pi-hole API client
        name: Name of the group to retrieve

    Returns:
        Dictionary containing group details if found, None if not found

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    try:
        response = client._request("GET", f"api/groups/{name}")

        if response.status_code == 404:
            return None

        response.raise_for_status()

        groups = response.json().get("groups", [])
        return groups[0] if groups else None

    except PiholeNotFoundError:
        return None
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve group '{name}': {str(e)}")


def add_group(
    client: PiholeApiClient,
    name: str,
    comment: str = "",
    enabled: bool = True
) -> Dict[str, Any]:
    """
    Add a new group.

    Args:
        client: Initialized Pi-hole API client
        name: Name of the group to add
        comment: Optional comment for the group
        enabled: Whether the group is enabled (default: True)

    Returns:
        API response containing the created group

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    data = {
        "name": name,
        "comment": comment,
        "enabled": enabled
    }

    try:
        response = client._request("POST", "api/groups", json_data=data)
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to add group '{name}': {str(e)}")


def update_group(
    client: PiholeApiClient,
    name: str,
    new_name: Optional[str] = None,
    comment: Optional[str] = None,
    enabled: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update an existing group.

    Args:
        client: Initialized Pi-hole API client
        name: Current name of the group
        new_name: Optional new name for the group
        comment: Optional new comment (None preserves existing)
        enabled: Optional new enabled status (None preserves existing)

    Returns:
        API response containing the updated group

    Raises:
        PiholeValidationError: If the group doesn't exist
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    # Get current group details
    current_group = get_group(client, name)
    if not current_group:
        raise PiholeValidationError(f"Group '{name}' does not exist")

    # Prepare update data
    data: Dict[str, Any] = {}

    if new_name is not None:
        data["name"] = new_name

    # Preserve existing values if not specified
    data["comment"] = comment if comment is not None else current_group.get("comment", "")
    data["enabled"] = enabled if enabled is not None else current_group.get("enabled", True)

    try:
        response = client._request("PUT", f"api/groups/{name}", json_data=data)
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to update group '{name}': {str(e)}")


def delete_group(client: PiholeApiClient, name: str) -> Dict[str, Any]:
    """
    Delete a group.

    Args:
        client: Initialized Pi-hole API client
        name: Name of the group to delete

    Returns:
        Success response with message

    Raises:
        PiholeNotFoundError: If the group doesn't exist
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    try:
        response = client._request("DELETE", f"api/groups/{name}")

        # Handle empty successful responses
        if response.status_code == 204 or not response.text:
            return {
                "success": True,
                "message": f"Group '{name}' deleted successfully"
            }

        response.raise_for_status()

        # Try to parse as JSON, fall back to success message
        try:
            return response.json()
        except ValueError:
            return {
                "success": True,
                "message": f"Group '{name}' deleted successfully",
                "raw_response": response.text
            }

    except PiholeNotFoundError:
        raise PiholeNotFoundError(f"Group '{name}' does not exist")
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to delete group '{name}': {str(e)}")


def batch_delete_groups(
    client: PiholeApiClient,
    group_names: List[str]
) -> Dict[str, Any]:
    """
    Delete multiple groups in a single batch operation.

    Args:
        client: Initialized Pi-hole API client
        group_names: List of group names to delete

    Returns:
        Success response with message

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    if not group_names:
        return {"success": True, "message": "No groups to delete"}

    # Format group names as required by the API
    formatted_names = [{"item": name} for name in group_names]

    try:
        response = client._request(
            "POST",
            "api/groups:batchDelete",
            json_data=formatted_names
        )

        # 204 No Content - Success
        if response.status_code == 204:
            return {
                "success": True,
                "message": f"Successfully deleted {len(group_names)} groups",
                "status_code": 204
            }

        # Error handling for specific status codes
        if response.status_code in [400, 401, 404]:
            error_messages = {
                400: "Bad request - invalid data format",
                401: "Unauthorized - invalid session ID",
                404: "Not found - one or more groups don't exist"
            }
            error_msg = error_messages.get(response.status_code, "Unknown error")

            raise PiholeApiError(
                error_msg,
                status_code=response.status_code,
                response_text=response.text
            )

        response.raise_for_status()

        # This should rarely be reached
        return {
            "success": True,
            "message": f"Successfully deleted {len(group_names)} groups"
        }

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to batch delete groups: {str(e)}")


def group_names_to_ids(
    client: PiholeApiClient,
    group_names: List[str]
) -> List[int]:
    """
    Convert group names to their corresponding IDs.

    Args:
        client: Initialized Pi-hole API client
        group_names: List of group names to convert

    Returns:
        List of unique group IDs in the order first encountered

    Raises:
        PiholeValidationError: If any group name cannot be found
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors
    """
    if not group_names:
        return [0]  # Default group

    group_mapping = get_groups(client)

    group_ids: List[int] = []
    missing_groups: List[str] = []

    for name in group_names:
        if name in group_mapping:
            group_ids.append(group_mapping[name])
        else:
            missing_groups.append(name)

    if missing_groups:
        raise PiholeValidationError(
            f"The following groups do not exist: {', '.join(missing_groups)}"
        )

    # Remove duplicates while preserving order
    seen: Set[int] = set()
    unique_group_ids: List[int] = []
    for gid in group_ids:
        if gid not in seen:
            seen.add(gid)
            unique_group_ids.append(gid)

    return unique_group_ids
