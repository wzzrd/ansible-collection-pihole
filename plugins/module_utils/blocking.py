# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole DNS blocking management utilities.

This module provides functions for managing the DNS blocking status
in Pi-hole, including enabling, disabling, and checking the current state.
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


def get_blocking_status(client: PiholeApiClient) -> dict[str, Any]:
    """
    Get the current blocking status from Pi-hole.

    Args:
        client: Initialized Pi-hole API client.

    Returns:
        Dictionary with blocking status information.
        Example: {"blocking": "enabled", "timer": null}
                 {"blocking": "disabled", "timer": 300}

    Raises:
        PiholeAuthError: If authentication fails.
        PiholeConnectionError: If connection to Pi-hole fails.
        PiholeApiError: For other API-related errors.
    """
    try:
        response = client._request("GET", "api/dns/blocking")
        response.raise_for_status()
        return response.json()
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve blocking status: {e}")


def set_blocking_status(
    client: PiholeApiClient, enabled: bool, timer: int | None = None
) -> dict[str, Any]:
    """
    Set the DNS blocking status in Pi-hole.

    Args:
        client: Initialized Pi-hole API client.
        enabled: True to enable blocking, False to disable.
        timer: Optional duration in seconds to keep the status,
               after which it reverts to the opposite state.
               None or 0 means the change is permanent.

    Returns:
        Dictionary with the updated blocking status.

    Raises:
        PiholeAuthError: If authentication fails.
        PiholeConnectionError: If connection to Pi-hole fails.
        PiholeApiError: For other API-related errors.
    """
    data: dict[str, Any] = {"blocking": enabled}

    if timer is not None and timer > 0:
        data["timer"] = timer

    try:
        response = client._request("POST", "api/dns/blocking", json_data=data)
        response.raise_for_status()
        return response.json()
    except PiholeError:
        raise
    except Exception as e:
        action = "enable" if enabled else "disable"
        msg = f"Failed to {action} blocking"
        if timer:
            msg += f" for {timer} seconds"
        raise PiholeApiError(f"{msg}: {e}")
