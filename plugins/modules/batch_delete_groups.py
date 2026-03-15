#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+

DOCUMENTATION = r"""
---
module: batch_delete_groups

short_description: Batch delete multiple Pi-hole groups via its API

version_added: "1.0.0"

description:
  - This module allows you to delete multiple groups in a single operation from a Pi-hole instance using its API.
  - It is more efficient than deleting groups one by one when removing multiple groups.
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
  names:
    description:
      - A list of group names to delete.
    required: true
    type: list
    elements: str

requirements: []
"""

EXAMPLES = r"""
- name: Delete multiple groups at once
  wzzrd.pihole.group_batch_delete:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    names:
      - "trusted_devices"
      - "test_group"
      - "temporary_group"
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

result:
  description: Raw response from the Pi-hole API.
  type: dict
  returned: when groups are deleted

deleted_count:
  description: Number of groups that were successfully deleted.
  type: int
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.groups import (
    get_groups,
    batch_delete_groups,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeConnectionError,
    PiholeApiError,
)


def main():
    """
    Ansible module entry point for batch deleting Pi-hole groups.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "names": {"type": "list", "required": True, "elements": "str"},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    pihole_url = module.params["pihole"]
    sid = module.params["sid"]
    group_names_to_delete = module.params["names"]

    try:
        # Initialize the Pi-hole API client
        client = PiholeApiClient(pihole_url, sid)

        # Get all available groups to check which ones actually exist
        all_groups_map = get_groups(client)  #
        existing_group_names = list(all_groups_map.keys())

        # Filter to only delete groups that actually exist
        groups_that_exist_and_will_be_deleted = [
            name for name in group_names_to_delete if name in existing_group_names
        ]

        if not groups_that_exist_and_will_be_deleted:
            module.exit_json(
                changed=False,
                msg="None of the specified groups exist or no groups specified for deletion.",
                deleted_count=0,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,  # A change would occur if any specified groups exist
                msg=(
                    f"Would delete {len(groups_that_exist_and_will_be_deleted)} groups: "
                    f"{', '.join(groups_that_exist_and_will_be_deleted)}"
                ),
                deleted_count=len(groups_that_exist_and_will_be_deleted),
            )

        result = batch_delete_groups(client, groups_that_exist_and_will_be_deleted)  #

        # The batch_delete_groups utility should return a dict that might include success/message
        # or raise an error. The module's return should reflect this.
        # Assuming the utility function returns a dict similar to what the API client method did,
        # or a more structured success/failure indication.
        # For now, rely on it raising an exception on failure.

        module.exit_json(
            changed=True,
            result=result,  # Contains the raw API response from the utility function
            msg=f"Batch deleted {len(groups_that_exist_and_will_be_deleted)} groups.",
            deleted_count=len(groups_that_exist_and_will_be_deleted),
        )

    except PiholeAuthError as e:
        module.fail_json(msg=f"Authentication error: {str(e)}")
    except PiholeConnectionError as e:
        module.fail_json(msg=f"Connection error: {str(e)}")
    except PiholeApiError as e:
        module.fail_json(msg=f"API error: {str(e)}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
