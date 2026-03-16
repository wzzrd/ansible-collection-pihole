#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations
DOCUMENTATION = r"""
---
module: action

short_description: Perform Pi-hole system actions via its API

version_added: "1.0.0"

description:
  - This module allows you to perform various system actions in Pi-hole.
  - Actions include updating gravity, restarting DNS, and flushing logs or network tables.
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
  action:
    description:
      - The action to perform.
    choices: [gravity, restartdns, flush_logs, flush_arp]
    required: true
    type: str

requirements: []
"""

EXAMPLES = r"""
- name: Update gravity (download adlists)
  wzzrd.pihole.action:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    action: gravity

- name: Restart Pi-hole DNS service
  wzzrd.pihole.action:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    action: restartdns

- name: Flush Pi-hole DNS logs
  wzzrd.pihole.action:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    action: flush_logs

- name: Flush Pi-hole network table
  wzzrd.pihole.action:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    action: flush_arp
"""

RETURN = r"""
changed:
  description: Whether the action was performed successfully.
  type: bool
  returned: always

msg:
  description: Information about the action that was performed.
  type: str
  returned: always

result:
  description: Raw response from Pi-hole API.
  type: dict
  returned: when available
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.action import perform_action
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeConnectionError,
    PiholeApiError,
    PiholeValidationError,
)


def main():
    """
    Ansible module entry point for performing Pi-hole system actions.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "action": {
            "type": "str",
            "required": True,
            "choices": ["gravity", "restartdns", "flush_logs", "flush_arp"],
        },
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    pihole_url = module.params["pihole"]
    sid = module.params["sid"]
    action_to_perform = module.params["action"]

    action_descriptions = {
        "gravity": "update gravity",
        "restartdns": "restart DNS service",
        "flush_logs": "flush DNS logs",
        "flush_arp": "flush network table",
    }

    try:
        # Initialize the Pi-hole API client
        client = PiholeApiClient(pihole_url, sid)

        # In check mode, just report what would happen
        if module.check_mode:
            module.exit_json(
                changed=True, msg=f"Would {action_descriptions[action_to_perform]}"
            )

        # Perform the action
        result = perform_action(client, action_to_perform)

        module.exit_json(
            changed=True,
            msg=f"Successfully performed action: {action_descriptions[action_to_perform]}",
            result=result,
        )

    except PiholeValidationError as e:
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
