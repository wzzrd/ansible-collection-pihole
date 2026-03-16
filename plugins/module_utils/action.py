# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole system action utilities.

This module provides functions for performing various system actions
in Pi-hole, such as updating gravity or restarting services.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
        PiholeApiClient,
    )

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeError,
    PiholeValidationError,
)


def perform_action(client: PiholeApiClient, action: str) -> Dict[str, Any]:
    """
    Perform a system action in Pi-hole.

    Supported actions include updating gravity, restarting DNS,
    flushing logs, or flushing the ARP cache.

    Args:
        client: Initialized Pi-hole API client.
        action: The action to perform. Supported values are:
                "gravity", "restartdns", "flush_logs", "flush_arp".

    Returns:
        API response from Pi-hole, typically confirming success.

    Raises:
        PiholeValidationError: If the specified action is not supported.
        PiholeAuthError: If authentication fails.
        PiholeConnectionError: If connection to Pi-hole fails.
        PiholeApiError: For other API-related errors.
    """
    action_map = {
        "gravity": "gravity",
        "restartdns": "restartdns",
        "flush_logs": "flush/logs",
        "flush_arp": "flush/arp",
    }

    if action not in action_map:
        raise PiholeValidationError(
            f"Unsupported action: '{action}'. "
            f"Supported actions are: {', '.join(action_map.keys())}"
        )

    endpoint = f"api/action/{action_map[action]}"
    # Gravity updates can take a while
    timeout = 300 if action == "gravity" else client.timeout

    try:
        response = client._request("POST", endpoint, timeout=timeout)
        response.raise_for_status()

        # Try to parse as JSON, fall back to text if not JSON.
        # PiholeResponse.json() converts ValueError → PiholeApiError, so we
        # catch PiholeApiError here rather than ValueError.
        try:
            return response.json()
        except PiholeApiError:
            return {
                "success": True,
                "message": f"Action '{action}' performed successfully",
                "raw_response": response.text,
            }
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to perform action '{action}': {str(e)}")
