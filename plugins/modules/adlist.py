#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+

from __future__ import annotations
DOCUMENTATION = r"""
---
module: adlist

short_description: Manage Pi-hole adlists via its API

version_added: "1.0.0"

description:
  - This module allows you to create, update, or remove adlists in a Pi-hole
    instance using its API.
  - It supports idempotent operations using the list address, comment, and enabled status.
  - You must provide a valid session ID (SID) for authentication.

author:
  - Maxim Burgerhout (@wzzrd)

options:
  pihole:
    description:
      - The base URL of the Pi-hole instance (e.g., https://pihole.local).
    required: true
    type: str
  sid:
    description:
      - Session ID used to authenticate with the Pi-hole API.
    required: true
    type: str
  address:
    description:
      - The URL of the adlist to manage.
      - For example, 'https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts'.
    required: true
    type: str
  type:
    description:
      - The type of list to manage.
    choices: [allow, block]
    default: block
    required: false
    type: str
  comment:
    description:
      - A comment to associate with the adlist.
      - If not provided during updates, the existing comment will be preserved.
    required: false
    type: str
  groups:
    description:
      - List of group names to associate with this adlist.
      - By default, the adlist is added to the "Default" group.
      - Group names are case-sensitive and must match exactly.
    required: false
    type: list
    elements: str
    default: ["Default"]
  enabled:
    description:
      - Whether the adlist is enabled.
    required: false
    type: bool
    default: true
  state:
    description:
      - Whether the adlist should exist or not.
    choices: [present, absent]
    default: present
    required: false
    type: str

requirements: []
"""

EXAMPLES = r"""
- name: Ensure an adlist is present
  wzzrd.pihole.adlist:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    comment: "StevenBlack's unified hosts list"
    state: present

- name: Update an existing adlist's comment
  wzzrd.pihole.adlist:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    comment: "Updated: StevenBlack's unified hosts list"
    state: present

- name: Add an adlist to specific groups
  wzzrd.pihole.adlist:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    groups: ["Default", "IoT_Devices"]
    state: present

- name: Disable an adlist
  wzzrd.pihole.adlist:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    enabled: false
    state: present

- name: Remove an adlist
  wzzrd.pihole.adlist:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was made to the adlist configuration.
  type: bool
  returned: always

msg:
  description: Information about the action that was performed.
  type: str
  returned: always

adlist:
  description: Details of the adlist that was created or modified.
  type: dict
  returned: when state is present and an adlist is created or updated

result:
  description: Raw response from the Pi-hole API.
  type: dict
  returned: when an adlist is created, updated, or deleted
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.adlist import (
    get_adlist,
    add_adlist,
    update_adlist,
    delete_adlist,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.groups import (
    group_names_to_ids,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeConnectionError,
    PiholeApiError,
    PiholeValidationError,
    PiholeNotFoundError,
)


def main():
    """
    Ansible module entry point for managing Pi-hole adlists.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "address": {"type": "str", "required": True},
        "type": {
            "type": "str",
            "required": False,
            "choices": ["allow", "block"],
            "default": "block",
        },
        "comment": {"type": "str", "required": False, "default": None},
        "groups": {
            "type": "list",
            "elements": "str",
            "required": False,
            "default": ["Default"],
        },
        "enabled": {"type": "bool", "required": False, "default": True},
        "state": {
            "type": "str",
            "required": False,
            "choices": ["present", "absent"],
            "default": "present",
        },
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    pihole_url = module.params["pihole"]
    sid = module.params["sid"]
    address = module.params["address"]
    list_type = module.params["type"]
    comment_param = module.params["comment"]
    group_names = module.params["groups"]
    enabled_param = module.params["enabled"]
    state = module.params["state"]

    try:
        # Initialize the Pi-hole API client
        client = PiholeApiClient(pihole_url, sid)

        # Convert group names to IDs
        try:
            group_ids = group_names_to_ids(client, group_names)
        except PiholeValidationError as e:
            module.fail_json(msg=str(e))
            return  # Ensure exit after fail_json

        # Check if the adlist exists
        existing_adlist = get_adlist(client, address, list_type)
        exists = existing_adlist is not None

        if state == "present":
            if exists:
                needs_update = False
                # Check if comment needs updating
                if (
                    comment_param is not None
                    and existing_adlist.get("comment", "") != comment_param
                ):
                    needs_update = True
                # Check if enabled status needs updating
                if (
                    enabled_param is not None
                    and existing_adlist.get("enabled", True) != enabled_param
                ):
                    needs_update = True
                # Check if groups need updating (compare sorted lists of IDs)
                # Default group ID is 0 if not specified
                existing_group_ids = sorted(existing_adlist.get("groups", [0]))
                if sorted(group_ids) != existing_group_ids:
                    needs_update = True

                if needs_update:
                    if module.check_mode:
                        module.exit_json(
                            changed=True, msg=f"Would update adlist '{address}'"
                        )

                    # For update, pass None for params not being changed to preserve existing values
                    # The utility function handles fetching current values if specific ones are None
                    updated_comment = (
                        comment_param
                        if comment_param is not None
                        else existing_adlist.get("comment")
                    )
                    updated_enabled = (
                        enabled_param
                        if enabled_param is not None
                        else existing_adlist.get("enabled")
                    )

                    result = update_adlist(
                        client,
                        address,
                        list_type=list_type,
                        comment=updated_comment,
                        group_ids=group_ids,
                        enabled=updated_enabled,
                    )

                    updated_adlist_details = None
                    if result and "lists" in result and result["lists"]:
                        updated_adlist_details = result["lists"][0]

                    module.exit_json(
                        changed=True,
                        result=result,
                        msg=f"Adlist '{address}' updated",
                        adlist=updated_adlist_details,
                    )
                else:
                    module.exit_json(
                        changed=False,
                        msg=f"Adlist '{address}' already exists with the specified properties",
                        adlist=existing_adlist,
                    )
            else:  # Adlist doesn't exist, create it
                if module.check_mode:
                    module.exit_json(
                        changed=True, msg=f"Would create adlist '{address}'"
                    )

                result = add_adlist(
                    client, address, list_type, comment_param, group_ids, enabled_param
                )
                created_adlist_details = None
                if result and "lists" in result and result["lists"]:
                    created_adlist_details = result["lists"][0]
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"Adlist '{address}' created",
                    adlist=created_adlist_details,
                )

        elif state == "absent":
            if exists:
                if module.check_mode:
                    module.exit_json(
                        changed=True, msg=f"Would delete adlist '{address}'"
                    )

                # delete_adlist utility returns a dict with "success": True/False
                result = delete_adlist(client, address, list_type)
                if result.get("success"):  # Successfully deleted
                    module.exit_json(
                        changed=True, result=result, msg=f"Adlist '{address}' deleted"
                    )
                else:  # Adlist was not found by the delete call (e.g., 404) or other delete failure
                    # If it was a 404, it means it was already absent.
                    is_not_found_error = (
                        "not found" in result.get("message", "").lower()
                    )
                    if is_not_found_error:
                        module.exit_json(
                            changed=False,
                            result=result,
                            msg=f"Adlist '{address}' was already absent when deletion was attempted.",
                        )
                    else:
                        module.fail_json(
                            msg=result.get(
                                "message", f"Failed to delete adlist '{address}'."
                            )
                        )
            else:  # Adlist does not exist (based on initial get_adlist check)
                module.exit_json(
                    changed=False, msg=f"Adlist '{address}' does not exist"
                )

    except PiholeValidationError as e:
        module.fail_json(msg=str(e))
    except (
        PiholeNotFoundError
    ) as e:  # Should be caught by get_adlist returning None, but as a safeguard
        module.fail_json(msg=str(e))
    except PiholeAuthError as e:
        module.fail_json(msg=f"Authentication error: {e}")
    except PiholeConnectionError as e:
        module.fail_json(msg=f"Connection error: {e}")
    except PiholeApiError as e:
        module.fail_json(msg=f"API error: {e}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
