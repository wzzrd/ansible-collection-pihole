#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) Your Name or Organization
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole authentication utilities.

This module provides authentication-related functions for interacting
with the Pi-hole API.
"""

from __future__ import annotations

from typing import Dict, Any

import requests

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)


def authenticate(base_url: str, password: str, timeout: int = 10) -> str:
    """
    Authenticate with Pi-hole and obtain a session ID.

    This function performs authentication against the Pi-hole web API
    and returns a session ID (SID) that can be used for subsequent
    API calls.

    Args:
        base_url: Base URL of the Pi-hole instance (e.g., https://pihole.local)
        password: Password for the Pi-hole web interface
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Session ID (SID) string for authenticated API calls

    Raises:
        PiholeAuthError: If authentication fails or no session ID is returned
        PiholeConnectionError: If connection to Pi-hole fails
        PiholeApiError: If the API returns an invalid response

    Example:
        >>> sid = authenticate("https://pihole.local", "mypassword")
        >>> print(sid)
        "3f93ec7b846ebff8ec9b6219c6c0a2e6"
    """
    auth_url = f"{base_url.rstrip('/')}/api/auth"

    try:
        response = requests.post(auth_url, json={"password": password}, timeout=timeout)

        if response.status_code != 200:
            raise PiholeAuthError(
                f"Authentication failed with status code {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
            )

        data: Dict[str, Any] = response.json()
        session_data = data.get("session", {})
        sid = session_data.get("sid")

        if not sid:
            raise PiholeAuthError(
                "Authentication failed: No session ID returned", response_text=str(data)
            )

        return sid

    except requests.exceptions.Timeout:
        raise PiholeConnectionError(
            f"Connection to {base_url} timed out after {timeout} seconds"
        )
    except requests.exceptions.ConnectionError as e:
        raise PiholeConnectionError(f"Failed to connect to {base_url}: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise PiholeConnectionError(f"Request error: {str(e)}")
    except ValueError as e:
        raise PiholeApiError(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        # Catch any other exceptions and wrap them
        if isinstance(e, (PiholeAuthError, PiholeConnectionError, PiholeApiError)):
            raise
        raise PiholeApiError(f"Unexpected error during authentication: {str(e)}")
