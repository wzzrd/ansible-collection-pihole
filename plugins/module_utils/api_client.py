#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) Your Name or Organization
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Core API client for interacting with the Pi-hole API.

This module provides the base PiholeApiClient class responsible for
making HTTP requests to the Pi-hole API, handling authentication,
and managing common error scenarios. Specific API functionalities
(e.g., managing domains, groups, DNS records) are implemented in
separate utility modules that use this client.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests
import urllib.parse  # Keep for potential future use if any core request needs it, though not directly used by kept methods.

# Suppress InsecureRequestWarning for self-signed certificates common in homelab Pi-hole setups.
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
    PiholeNotFoundError,
    # PiholeValidationError is not directly raised by the core client, but by utilities.
)


class PiholeApiClient:
    """
    Client for base Pi-hole API operations.

    Handles making HTTP requests, session management, and common error responses.
    Specific resource management (groups, domains, etc.) is handled by
    functions in other module_utils files that utilize this client.
    """

    def __init__(self, base_url: str, sid: str, timeout: int = 10):
        """
        Initialize the Pi-hole API client.

        Args:
            base_url: Base URL of the Pi-hole instance (e.g., https://pihole.local).
            sid: Session ID for authentication.
            timeout: Default request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.sid = sid
        self.timeout = timeout
        self.headers = {"sid": sid}

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Make a request to the Pi-hole API with appropriate error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (will be appended to base_url).
            json_data: Optional JSON data for POST/PUT requests.
            params: Optional query parameters.
            timeout: Optional custom timeout (defaults to self.timeout).

        Returns:
            The API response object.

        Raises:
            PiholeAuthError: If authentication fails (401).
            PiholeNotFoundError: If the resource is not found (404).
            PiholeConnectionError: If connection to Pi-hole fails (timeout, network error).
            PiholeApiError: For other HTTP errors or issues with the API response.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_timeout = timeout if timeout is not None else self.timeout

        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                headers=self.headers,
                timeout=request_timeout,
                verify=False,
            )

            if response.status_code == 401:
                raise PiholeAuthError(
                    "Authentication failed. Invalid or expired session ID.",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            if response.status_code == 404:
                raise PiholeNotFoundError(
                    f"Resource not found at {url}",
                    status_code=response.status_code,
                    response_text=response.text,
                )

            # Other HTTP errors will be caught by response.raise_for_status()
            # or handled by the calling utility function if specific logic is needed.
            return response

        except requests.exceptions.Timeout:
            raise PiholeConnectionError(
                f"Connection to {self.base_url} timed out after {request_timeout} seconds"
            )
        except requests.exceptions.ConnectionError as e:
            raise PiholeConnectionError(
                f"Failed to connect to {self.base_url}: {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            # This is a catch-all for other requests-related exceptions
            raise PiholeApiError(f"Request error for {url}: {str(e)}")

    @classmethod
    def authenticate(cls, base_url: str, password: str, timeout: int = 10) -> str:
        """
        Authenticate with Pi-hole and obtain a session ID.

        This method is primarily used by the `pihole_auth` Ansible module.

        Args:
            base_url: Base URL of the Pi-hole instance.
            password: Password for the Pi-hole web interface.
            timeout: Request timeout in seconds.

        Returns:
            Session ID (SID) string for authenticated API calls.

        Raises:
            PiholeAuthError: If authentication fails or no session ID is returned.
            PiholeConnectionError: If connection to Pi-hole fails.
            PiholeApiError: If the API returns an invalid response (e.g., non-JSON).
        """
        auth_url = f"{base_url.rstrip('/')}/api/auth"

        try:
            response = requests.post(
                auth_url, json={"password": password}, timeout=timeout, verify=False
            )

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
                    "Authentication failed: No session ID returned by Pi-hole.",
                    response_text=str(data),
                )

            return sid

        except requests.exceptions.Timeout:
            raise PiholeConnectionError(
                f"Connection to {auth_url} timed out after {timeout} seconds"
            )
        except requests.exceptions.ConnectionError as e:
            raise PiholeConnectionError(f"Failed to connect to {auth_url}: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise PiholeApiError(f"Request error during authentication: {str(e)}")
        except ValueError as e: # Handles JSON decoding errors
            raise PiholeApiError(
                f"Invalid JSON response during authentication: {str(e)}",
                response_text=response.text if 'response' in locals() else None
            )
        except Exception as e:
            # Catch any other unexpected exceptions and wrap them
            if isinstance(e, (PiholeAuthError, PiholeConnectionError, PiholeApiError)):
                raise
            raise PiholeApiError(f"Unexpected error during authentication: {str(e)}")
