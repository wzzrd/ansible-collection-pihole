# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole authentication utilities.

This module provides authentication-related functions for interacting
with the Pi-hole API.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any, Dict

from ansible.module_utils.urls import open_url

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
)


def authenticate(base_url: str, password: str, timeout: int = 10) -> str:
    """
    Authenticate with Pi-hole and obtain a session ID.

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
    """
    auth_url = f"{base_url.rstrip('/')}/api/auth"

    try:
        body = json.dumps({"password": password}).encode("utf-8")
        resp = open_url(
            auth_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
            validate_certs=False,
            timeout=timeout,
        )
        data: Dict[str, Any] = json.loads(resp.read())

        session_data = data.get("session", {})
        sid = session_data.get("sid")

        if not sid:
            raise PiholeAuthError(
                "Authentication failed: No session ID returned", response_text=str(data)
            )

        return sid

    except urllib.error.HTTPError as exc:
        status_code = exc.code
        response_text = exc.read().decode("utf-8", errors="replace")
        raise PiholeAuthError(
            f"Authentication failed with status code {status_code}",
            status_code=status_code,
            response_text=response_text,
        )

    except urllib.error.URLError as exc:
        if "timed out" in str(exc.reason).lower():
            raise PiholeConnectionError(
                f"Connection to {base_url} timed out after {timeout} seconds"
            )
        raise PiholeConnectionError(
            f"Failed to connect to {base_url}: {str(exc.reason)}"
        )

    except (PiholeAuthError, PiholeConnectionError, PiholeApiError):
        raise

    except ValueError as exc:
        raise PiholeApiError(f"Invalid JSON response: {str(exc)}")

    except Exception as exc:
        raise PiholeApiError(f"Unexpected error during authentication: {str(exc)}")
