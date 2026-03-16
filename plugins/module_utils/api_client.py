# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
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

import json
import urllib.error
import urllib.parse
from typing import Any

from ansible.module_utils.urls import open_url

from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeApiError,
    PiholeAuthError,
    PiholeConnectionError,
    PiholeNotFoundError,
)

class PiholeResponse:
    """Minimal HTTP response wrapper matching the requests.Response interface."""

    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self._body = body

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        try:
            return json.loads(self._body)
        except ValueError as exc:
            raise PiholeApiError(f"Invalid JSON response: {exc}")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise PiholeApiError(
                f"HTTP error {self.status_code}",
                status_code=self.status_code,
                response_text=self.text,
            )

class PiholeApiClient:
    """
    Client for base Pi-hole API operations.

    Handles making HTTP requests, session management, and common error responses.
    Specific resource management (groups, domains, etc.) is handled by
    functions in other module_utils files that utilize this client.
    """

    def __init__(self, base_url: str, sid: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.sid = sid
        self.timeout = timeout
        self.headers = {"sid": sid}

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> PiholeResponse:
        """
        Make a request to the Pi-hole API with appropriate error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (will be appended to base_url).
            json_data: Optional JSON data for POST/PUT requests.
            params: Optional query parameters.
            timeout: Optional custom timeout (defaults to self.timeout).

        Returns:
            A PiholeResponse wrapping the API response.

        Raises:
            PiholeAuthError: If authentication fails (401).
            PiholeNotFoundError: If the resource is not found (404).
            PiholeConnectionError: If connection to Pi-hole fails.
            PiholeApiError: For other HTTP errors or issues with the API response.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        request_timeout = timeout if timeout is not None else self.timeout

        body = None
        headers = dict(self.headers)
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        try:
            resp = open_url(
                url,
                data=body,
                headers=headers,
                method=method,
                validate_certs=False,
                timeout=request_timeout,
            )
            return PiholeResponse(resp.status, resp.read())

        except urllib.error.HTTPError as exc:
            status_code = exc.code
            response_body = exc.read()
            response_text = response_body.decode("utf-8", errors="replace")

            if status_code == 401:
                raise PiholeAuthError(
                    "Authentication failed. Invalid or expired session ID.",
                    status_code=status_code,
                    response_text=response_text,
                )
            if status_code == 404:
                raise PiholeNotFoundError(
                    f"Resource not found at {url}",
                    status_code=status_code,
                    response_text=response_text,
                )

            return PiholeResponse(status_code, response_body)

        except urllib.error.URLError as exc:
            if "timed out" in str(exc.reason).lower():
                raise PiholeConnectionError(
                    f"Connection to {self.base_url} timed out after {request_timeout} seconds"
                )
            raise PiholeConnectionError(
                f"Failed to connect to {self.base_url}: {str(exc.reason)}"
            )

        except (
            PiholeAuthError,
            PiholeNotFoundError,
            PiholeConnectionError,
            PiholeApiError,
        ):
            raise

        except Exception as exc:
            raise PiholeApiError(f"Request error for {url}: {str(exc)}")

    @classmethod
    def authenticate(cls, base_url: str, password: str, timeout: int = 10) -> str:
        """
        Authenticate with Pi-hole and obtain a session ID.

        Args:
            base_url: Base URL of the Pi-hole instance.
            password: Password for the Pi-hole web interface.
            timeout: Request timeout in seconds.

        Returns:
            Session ID (SID) string for authenticated API calls.

        Raises:
            PiholeAuthError: If authentication fails or no session ID is returned.
            PiholeConnectionError: If connection to Pi-hole fails.
            PiholeApiError: If the API returns an invalid response.
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
            data: dict[str, Any] = json.loads(resp.read())

            session_data = data.get("session", {})
            sid = session_data.get("sid")

            if not sid:
                raise PiholeAuthError(
                    "Authentication failed: No session ID returned by Pi-hole.",
                    response_text=str(data),
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
                    f"Connection to {auth_url} timed out after {timeout} seconds"
                )
            raise PiholeConnectionError(
                f"Failed to connect to {auth_url}: {str(exc.reason)}"
            )

        except (PiholeAuthError, PiholeConnectionError, PiholeApiError):
            raise

        except ValueError as exc:
            raise PiholeApiError(
                f"Invalid JSON response during authentication: {str(exc)}"
            )

        except Exception as exc:
            raise PiholeApiError(f"Unexpected error during authentication: {str(exc)}")
