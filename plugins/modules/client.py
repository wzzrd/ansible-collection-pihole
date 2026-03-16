#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations
DOCUMENTATION = r"""
---
module: client

short_description: Manage Pi-hole clients via its API

version_added: "1.0.0"

description:
  - This module allows you to create, update, or remove client configurations in Pi-hole.
  - Clients can be identified by their IP address, MAC address, hostname, or interface.
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
  client:
    description:
      - The client identifier. Can be an IP address (IPv4/IPv6), MAC address, hostname, or interface name.
      - For IP addresses, both individual IPs and subnet ranges (CIDR notation) are supported.
      - For MAC addresses, use the format '12:34:56:78:9A:BC'.
      - For hostnames, use the domain name (e.g., 'laptop.local').
      - For interfaces, prefix with a colon (e.g., ':eth0').
    required: true
    type: str
  comment:
    description:
      - A comment to associate with the client.
      - If not provided during updates (i.e., parameter is omitted), the existing comment will be preserved.
      - To clear the comment, set comment to an empty string.
    required: false
    type: str
    default: null
  groups:
    description:
      - List of group names to associate with this client.
      - By default, the client is added to the "Default" group.
      - Group names are case-sensitive and must match exactly.
    required: false
    type: list
    elements: str
    default: ["Default"]
  state:
    description:
      - Whether the client configuration should exist or not.
    choices: [present, absent]
    default: present
    required: false
    type: str

requirements: []
"""

EXAMPLES = r"""
- name: Add a client configuration by IP address, no specific comment
  wzzrd.pihole.client:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    client: "192.168.1.101"
    groups: ["Default"]
    state: present

- name: Add a client with a specific comment
  wzzrd.pihole.client:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    client: "192.168.1.100"
    comment: "Living Room Smart TV"
    groups: ["IoT_Devices", "Default"]
    state: present

- name: Ensure a client has an explicitly empty comment
  wzzrd.pihole.client:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    client: "192.168.1.102"
    comment: ""
    state: present
"""

RETURN = r"""
changed:
  description: Whether a change was made to the client configuration.
  type: bool
  returned: always

msg:
  description: Information about the action that was performed.
  type: str
  returned: always

client:
  description: Details of the client that was created or modified.
  type: dict
  returned: when state is present and a client is created or updated

result:
  description: Raw response from the Pi-hole API.
  type: dict
  returned: when a client is created, updated, or deleted
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.client import (
    get_client,
    add_client,
    update_client,
    delete_client,
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
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "client": {"type": "str", "required": True},
        "comment": {"type": "str", "required": False, "default": None},
        "groups": {
            "type": "list",
            "elements": "str",
            "required": False,
            "default": ["Default"],
        },
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
    client_identifier = module.params["client"]
    comment_param = module.params["comment"]
    group_names_param = module.params["groups"]
    state = module.params["state"]

    try:
        api_client_instance = PiholeApiClient(pihole_url, sid)

        try:
            desired_group_ids = group_names_to_ids(
                api_client_instance, group_names_param
            )
        except PiholeValidationError as e:
            module.fail_json(msg=str(e))
            return

        existing_client_data = get_client(api_client_instance, client_identifier)
        exists = existing_client_data is not None

        if state == "present":
            if exists:
                needs_update = False

                # Comment comparison:
                # If comment_param is None, the user did not specify a comment, so we don't assess it for changes.
                # If comment_param is provided (e.g., "" or "some text"), then we compare.
                if comment_param is not None:
                    # Normalize existing comment: Pi-hole API might return null or empty string for "no comment".
                    # Treat null from API as an empty string for comparison purposes if user specified an empty string.
                    current_comment_on_pihole = existing_client_data.get("comment")
                    if current_comment_on_pihole is None:
                        current_comment_on_pihole = (
                            ""  # Treat API null as "" for comparison with user's ""
                        )

                    if current_comment_on_pihole != comment_param:
                        needs_update = True

                # Group comparison:
                current_groups_set = set(existing_client_data.get("groups", [0]))
                desired_groups_set = set(desired_group_ids)
                if desired_groups_set != current_groups_set:
                    needs_update = True

                if needs_update:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,
                            msg=f"Would update client '{client_identifier}'",
                        )

                    result = update_client(
                        api_client_instance,
                        client_identifier,
                        comment=comment_param,  # Pass user's specified comment (or None)
                        group_ids=desired_group_ids,
                    )

                    updated_client_details = (
                        result.get("clients", [{}])[0] if result.get("clients") else {}
                    )
                    module.exit_json(
                        changed=True,
                        result=result,
                        msg=f"Client '{client_identifier}' updated",
                        client=updated_client_details,
                    )
                else:
                    module.exit_json(
                        changed=False,
                        msg=f"Client '{client_identifier}' already exists with the specified properties",
                        client=existing_client_data,
                    )
            else:  # Client doesn't exist, create it
                if module.check_mode:
                    module.exit_json(
                        changed=True, msg=f"Would create client '{client_identifier}'"
                    )

                result = add_client(
                    api_client_instance,
                    client_identifier,
                    comment=comment_param,  # Pass user's specified comment (or None)
                    group_ids=desired_group_ids,
                )
                created_client_details = (
                    result.get("clients", [{}])[0] if result.get("clients") else {}
                )
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"Client '{client_identifier}' created",
                    client=created_client_details,
                )

        elif state == "absent":
            if exists:
                if module.check_mode:
                    module.exit_json(
                        changed=True, msg=f"Would delete client '{client_identifier}'"
                    )
                delete_success = delete_client(api_client_instance, client_identifier)
                if delete_success:
                    module.exit_json(
                        changed=True, msg=f"Client '{client_identifier}' deleted"
                    )
                else:
                    module.exit_json(
                        changed=False,
                        msg=f"Client '{client_identifier}' was already absent when deletion was attempted.",
                    )
            else:
                module.exit_json(
                    changed=False, msg=f"Client '{client_identifier}' does not exist"
                )

    except PiholeValidationError as e:
        module.fail_json(msg=str(e))
    except PiholeNotFoundError as e:
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
