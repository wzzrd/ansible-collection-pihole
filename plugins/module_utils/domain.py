# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pi-hole domain management utilities.

This module provides functions for managing domains in Pi-hole's whitelist
and blacklist, including exact domains and regex patterns.
"""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

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


def get_domain(
    client: PiholeApiClient,
    domain: str,
    domain_type: Optional[str] = None,
    domain_kind: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[str, str]]]:
    """
    Get details for a domain from whitelist or blacklist.

    Args:
        client: Initialized Pi-hole API client
        domain: Domain to search for
        domain_type: Type of domain (allow/deny), if None searches both
        domain_kind: Kind of domain (exact/regex), if None searches both

    Returns:
        Tuple containing:
            - Dict with domain details if found, None otherwise
            - Tuple of (domain_type, domain_kind) if found, None otherwise

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> domain_info, location = get_domain(client, "example.com")
        >>> if domain_info:
        ...     print(f"Found in {location[0]}/{location[1]}")
    """
    # URL encode the domain
    encoded_domain = urllib.parse.quote(domain)

    # Build the URL based on which parameters are provided
    if domain_type and domain_kind:
        endpoint = f"api/domains/{domain_type}/{domain_kind}/{encoded_domain}"
    elif domain_type:
        endpoint = f"api/domains/{domain_type}/{encoded_domain}"
    elif domain_kind:
        endpoint = f"api/domains/{domain_kind}/{encoded_domain}"
    else:
        endpoint = f"api/domains/{encoded_domain}"

    try:
        response = client._request("GET", endpoint)

        if response.status_code == 404:
            return None, None

        response.raise_for_status()
        domains = response.json().get("domains", [])

        if domains:
            found_domain = domains[0]
            found_type = found_domain.get("type")
            found_kind = found_domain.get("kind")
            return found_domain, (found_type, found_kind)

        return None, None

    except PiholeNotFoundError:
        return None, None
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to retrieve domain '{domain}': {str(e)}")


def add_domain(
    client: PiholeApiClient,
    domain: str,
    domain_type: str,
    domain_kind: str,
    comment: Optional[str] = None,
    group_ids: Optional[List[int]] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """
    Add a domain to the whitelist or blacklist.

    Args:
        client: Initialized Pi-hole API client
        domain: Domain to add (exact domain or regex pattern)
        domain_type: Type of domain (allow/deny)
        domain_kind: Kind of domain (exact/regex)
        comment: Optional comment for the domain
        group_ids: Optional list of group IDs to associate
        enabled: Whether the domain is enabled (default: True)

    Returns:
        API response containing the created domain

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> result = add_domain(
        ...     client,
        ...     "ads.example.com",
        ...     "deny",
        ...     "exact",
        ...     comment="Known ad server"
        ... )
    """
    data: Dict[str, Any] = {"domain": domain, "enabled": enabled}

    if comment is not None:
        data["comment"] = comment

    if group_ids is not None:
        data["groups"] = group_ids

    try:
        response = client._request(
            "POST", f"api/domains/{domain_type}/{domain_kind}", json_data=data
        )
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(
            f"Failed to add domain '{domain}' as {domain_type}/{domain_kind}: {str(e)}"
        )


def update_domain(
    client: PiholeApiClient,
    domain: str,
    current_type: str,
    current_kind: str,
    target_type: str,
    target_kind: str,
    comment: Optional[str] = None,
    group_ids: Optional[List[int]] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Update a domain in the whitelist or blacklist.

    Can be used to move domains between lists or update their properties.

    Args:
        client: Initialized Pi-hole API client
        domain: Domain to update
        current_type: Current type of domain (allow/deny)
        current_kind: Current kind of domain (exact/regex)
        target_type: Target type for the domain (allow/deny)
        target_kind: Target kind for the domain (exact/regex)
        comment: New comment (None preserves existing)
        group_ids: New list of group IDs (None preserves existing)
        enabled: New enabled status (None preserves existing)

    Returns:
        API response containing the updated domain

    Raises:
        PiholeValidationError: If the domain doesn't exist
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> # Move domain from blacklist to whitelist
        >>> result = update_domain(
        ...     client,
        ...     "example.com",
        ...     current_type="deny",
        ...     current_kind="exact",
        ...     target_type="allow",
        ...     target_kind="exact"
        ... )
    """
    # Get current domain details
    current_domain, _location = get_domain(client, domain, current_type, current_kind)

    if not current_domain:
        raise PiholeValidationError(
            f"Domain '{domain}' does not exist as {current_type}/{current_kind}"
        )

    # URL encode the domain
    encoded_domain = urllib.parse.quote(domain)

    # Use the TARGET type/kind in the URL
    endpoint = f"api/domains/{target_type}/{target_kind}/{encoded_domain}"

    # Build the data for the PUT request
    data: Dict[str, Any] = {}

    # Include the CURRENT type/kind when moving between lists
    if current_type != target_type or current_kind != target_kind:
        data["type"] = current_type
        data["kind"] = current_kind

    # Preserve existing values if not specified
    data["comment"] = (
        comment if comment is not None else current_domain.get("comment", "")
    )
    data["groups"] = (
        group_ids if group_ids is not None else current_domain.get("groups", [0])
    )
    data["enabled"] = (
        enabled if enabled is not None else current_domain.get("enabled", True)
    )

    try:
        response = client._request("PUT", endpoint, json_data=data)
        response.raise_for_status()
        return response.json()

    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(f"Failed to update domain '{domain}': {str(e)}")


def delete_domain(
    client: PiholeApiClient, domain: str, domain_type: str, domain_kind: str
) -> bool:
    """
    Delete a domain from the whitelist or blacklist.

    Args:
        client: Initialized Pi-hole API client
        domain: Domain to delete
        domain_type: Type of domain (allow/deny)
        domain_kind: Kind of domain (exact/regex)

    Returns:
        True if deleted successfully, False if not found

    Raises:
        PiholeAuthError: If authentication fails
        PiholeConnectionError: If connection fails
        PiholeApiError: For other API errors

    Example:
        >>> success = delete_domain(client, "ads.example.com", "deny", "exact")
        >>> if success:
        ...     print("Domain removed from blacklist")
    """
    # URL encode the domain
    encoded_domain = urllib.parse.quote(domain)
    endpoint = f"api/domains/{domain_type}/{domain_kind}/{encoded_domain}"

    try:
        response = client._request("DELETE", endpoint)

        if response.status_code == 404:
            return False

        response.raise_for_status()
        return True

    except PiholeNotFoundError:
        return False
    except PiholeError:
        raise
    except Exception as e:
        raise PiholeApiError(
            f"Failed to delete domain '{domain}' from {domain_type}/{domain_kind}: {str(e)}"
        )
