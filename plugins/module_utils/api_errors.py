# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole API error classes for Ansible modules.

This module defines custom exception classes used throughout the Pi-hole
Ansible collection for handling various error conditions.
"""

from __future__ import annotations

class PiholeError(Exception):
    """Base exception class for all Pi-hole API errors."""

    pass

class PiholeApiError(PiholeError):
    """
    Exception raised for API errors from Pi-hole.

    Attributes:
        message: Error message describing the issue
        status_code: HTTP status code from the API response
        response_text: Raw response text from the API
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        """
        Initialize a Pi-hole API error.

        Args:
            message: Error message describing the issue
            status_code: Optional HTTP status code from the API response
            response_text: Optional raw response text from the API
        """
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)

    def __str__(self) -> str:
        """Return a string representation of the error."""
        if self.status_code:
            return f"{self.args[0]} (HTTP {self.status_code})"
        return str(self.args[0])

class PiholeAuthError(PiholeApiError):
    """Exception raised for authentication errors (401 Unauthorized)."""

    pass

class PiholeNotFoundError(PiholeApiError):
    """Exception raised when a requested resource is not found (404 Not Found)."""

    pass

class PiholeValidationError(PiholeError):
    """
    Exception raised for client-side validation errors.

    This is used when input validation fails before making an API call.
    """

    pass

class PiholeConnectionError(PiholeError):
    """
    Exception raised for network connection errors.

    This includes timeouts, DNS resolution failures, and other
    network-related issues.
    """

    pass
