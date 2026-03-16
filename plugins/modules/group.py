#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: group

short_description: Manage Pi-hole groups via its API

version_added: "1.0.0"

description:
  - This module allows you to create, update, or remove groups in a Pi-hole
    instance using its API.
  - It supports idempotent operations using the group name, comment, and enabled status.
  - You must provide a valid session ID (SID) for authentication.
  - Supports renaming groups by providing both 'name' and 'new_name' parameters.

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
  name:
    description:
      - The name of the group to manage.
    required: true
    type: str
  new_name:
    description:
      - The new name to assign to the group when renaming.
      - Only used when renaming a group and state is 'present'.
    required: false
    type: str
  comment:
    description:
      - The comment for the group.
      - If not provided during updates, the existing comment will be preserved by the API/utility.
    required: false
    type: str
  enabled:
    description:
      - Whether the group is enabled or not.
      - If not provided during updates, the existing status will be preserved by the API/utility.
    required: false
    type: bool
  state:
    description:
      - Whether the group should exist or not.
    choices: [present, absent]
    default: present
    required: false
    type: str

requirements: []
"""

EXAMPLES = r"""
- name: Ensure a group is present
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "trusted_devices"
    comment: "Devices excluded from blocking"
    enabled: true
    state: present

- name: Update an existing group's comment
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "trusted_devices"
    comment: "Updated comment for trusted devices"
    state: present

- name: Rename a group (preserving existing comment and enabled status)
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "trusted_devices"
    new_name: "whitelisted_devices"
    state: present

- name: Disable a group
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "trusted_devices"
    enabled: false
    state: present

- name: Ensure a group is removed
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "trusted_devices"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was made to the group configuration.
  type: bool
  returned: always

msg:
  description: Information about the action that was performed.
  type: str
  returned: always

group:
  description: Details of the group that was created or modified.
  type: dict
  returned: when state is present and a group is created or updated

result:
  description: Raw response from the Pi-hole API.
  type: dict
  returned: when a group is created, updated, or deleted
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.groups import (
    get_group,
    add_group,
    update_group,
    delete_group,
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
    Ansible module entry point for managing Pi-hole groups.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "name": {"type": "str", "required": True},
        "new_name": {"type": "str", "required": False, "default": None},
        "comment": {"type": "str", "required": False, "default": None},
        "enabled": {
            "type": "bool",
            "required": False,
            "default": None,
        },  # None means preserve if updating
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
    current_name = module.params["name"]
    new_name_param = module.params["new_name"]
    comment_param = module.params["comment"]
    enabled_param = module.params["enabled"]  # This can be True, False, or None
    state = module.params["state"]

    try:
        api_client = PiholeApiClient(pihole_url, sid)
        existing_group_data = get_group(api_client, current_name)
        exists = existing_group_data is not None

        if state == "present":
            if exists:
                # Determine what needs to be updated
                needs_update = False
                desired_name_for_update = (
                    new_name_param if new_name_param else current_name
                )

                if new_name_param and new_name_param != current_name:
                    needs_update = True
                if (
                    comment_param is not None
                    and existing_group_data.get("comment", "") != comment_param
                ):
                    needs_update = True
                if (
                    enabled_param is not None
                    and existing_group_data.get("enabled", True) != enabled_param
                ):
                    needs_update = True

                if needs_update:
                    if module.check_mode:
                        msg = f"Would update group '{current_name}'"
                        if new_name_param and new_name_param != current_name:
                            msg += f" to name '{new_name_param}'"
                        if comment_param is not None:
                            msg += f", comment to '{comment_param}'"
                        if enabled_param is not None:
                            msg += f", enabled to {enabled_param}"
                        module.exit_json(changed=True, msg=msg)

                    # update_group utility handles None for comment/enabled to preserve existing
                    result = update_group(
                        api_client,
                        current_name,
                        new_name_param,
                        comment_param,
                        enabled_param,
                    )
                    updated_group_details = (
                        result.get("groups", [{}])[0] if result.get("groups") else {}
                    )

                    msg = f"Group '{current_name}'"
                    if new_name_param and new_name_param != current_name:
                        msg += f" renamed to '{new_name_param}' and updated."
                    else:
                        msg += " updated."
                    module.exit_json(
                        changed=True,
                        result=result,
                        msg=msg,
                        group=updated_group_details,
                    )
                else:
                    module.exit_json(
                        changed=False,
                        msg=f"Group '{current_name}' already exists with the specified properties.",
                        group=existing_group_data,
                    )

            else:  # Group doesn't exist, create it
                # If new_name is provided and group doesn't exist, use new_name for creation.
                # If new_name is not provided, use current_name.
                name_for_creation = new_name_param if new_name_param else current_name

                # For add_group, 'enabled' defaults to True, 'comment' to "" if not provided.
                # If params are None, use these defaults for creation.
                comment_for_creation = (
                    comment_param if comment_param is not None else ""
                )
                enabled_for_creation = (
                    enabled_param if enabled_param is not None else True
                )

                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        msg=f"Would create group '{name_for_creation}' with comment '{comment_for_creation}', enabled: {enabled_for_creation}",
                    )

                result = add_group(
                    api_client,
                    name_for_creation,
                    comment_for_creation,
                    enabled_for_creation,
                )
                created_group_details = (
                    result.get("groups", [{}])[0] if result.get("groups") else {}
                )
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"Group '{name_for_creation}' created.",
                    group=created_group_details,
                )

        elif state == "absent":
            if exists:
                if module.check_mode:
                    module.exit_json(
                        changed=True, msg=f"Would delete group '{current_name}'"
                    )

                result = delete_group(api_client, current_name)
                # delete_group utility returns a dict like {"success": True, "message": "..."}
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=result.get("message", f"Group '{current_name}' deleted"),
                )
            else:
                module.exit_json(
                    changed=False, msg=f"Group '{current_name}' does not exist."
                )

    except PiholeValidationError as e:
        module.fail_json(msg=str(e))
    except PiholeNotFoundError as e:  # Should be caught by get_group returning None
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
