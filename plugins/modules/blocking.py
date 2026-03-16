#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = r"""
---
module: blocking

short_description: Manage Pi-hole DNS blocking status via its API

version_added: "1.0.0"

description:
  - This module allows you to enable or disable Pi-hole DNS blocking.
  - It supports setting a timer for temporary enabling/disabling.
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
  enabled:
    description:
      - Whether Pi-hole blocking should be enabled or disabled.
    required: true
    type: bool
  timer:
    description:
      - Number of seconds before restoring the opposite blocking state.
      - If set, blocking will automatically revert after the specified time.
      - For example, if C(enabled=false) and C(timer=300), blocking will be
        disabled for 5 minutes, then automatically re-enabled.
      - Set to 0 or omit to make the setting permanent.
    required: false
    type: int
    default: 0
  force:
    description:
      - If true, the module will report a change even if the state matches the desired state.
      - This can be used to ensure the timer is (re)set if specified.
    required: false
    type: bool
    default: false

requirements: []
"""

EXAMPLES = r"""
- name: Ensure Pi-hole blocking is enabled
  wzzrd.pihole.blocking:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    enabled: true

- name: Disable Pi-hole blocking for 10 minutes (600 seconds)
  wzzrd.pihole.blocking:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    enabled: false
    timer: 600

- name: Force Pi-hole blocking status update (even if unchanged)
  wzzrd.pihole.blocking:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    enabled: true
    force: true
"""

RETURN = r"""
changed:
  description: Whether a change was made to the blocking status.
  type: bool
  returned: always

msg:
  description: Information about the action that was performed.
  type: str
  returned: always

status:
  description: Current Pi-hole blocking status.
  type: dict
  returned: always
  contains:
    blocking:
      description: Current blocking status (enabled/disabled/failed/unknown).
      type: str
      returned: always
    timer:
      description: Remaining seconds on timer if one is active, null otherwise.
      type: int
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.blocking import (
    get_blocking_status,
    set_blocking_status,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeConnectionError,
    PiholeApiError,
)


def main():
    """
    Ansible module entry point for managing Pi-hole blocking status.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "enabled": {"type": "bool", "required": True},
        "timer": {"type": "int", "required": False, "default": 0},
        "force": {"type": "bool", "required": False, "default": False},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    pihole_url = module.params["pihole"]
    sid = module.params["sid"]
    desired_enabled_state = module.params["enabled"]
    desired_timer_state = (
        module.params["timer"] if module.params["timer"] > 0 else None
    )  # API expects null/omitted for no timer
    force_update = module.params["force"]

    try:
        # Initialize the Pi-hole API client
        client = PiholeApiClient(pihole_url, sid)

        # Get current blocking status
        current_status_data = get_blocking_status(client)

        # current_status_data might be {"blocking": "enabled", "timer": null} or {"blocking": "disabled", "timer": 300}
        # The API returns "enabled" or "disabled" as strings for "blocking".
        current_enabled_state = current_status_data.get("blocking") == "enabled"
        # The API returns an integer for "timer" if active, or null.
        current_timer_value = current_status_data.get("timer")

        # Determine if a change is needed
        # A change is needed if:
        # 1. `force` is true.
        # 2. The desired enabled state is different from the current enabled state.
        # 3. A timer is desired, and it's different from the current timer, OR no timer is currently set.
        # 4. No timer is desired, but one is currently set.
        needs_change = (
            force_update
            or (current_enabled_state != desired_enabled_state)
            or (
                desired_timer_state is not None
                and current_timer_value != desired_timer_state
            )
            or (desired_timer_state is None and current_timer_value is not None)
        )

        if needs_change:
            action_msg_verb = "enable" if desired_enabled_state else "disable"
            action_msg_timer = (
                f" for {desired_timer_state} seconds" if desired_timer_state else ""
            )
            full_action_msg = (
                f"Would {action_msg_verb} Pi-hole blocking{action_msg_timer}"
            )

            if module.check_mode:
                module.exit_json(
                    changed=True, msg=full_action_msg, status=current_status_data
                )

            updated_status_data = set_blocking_status(
                client, desired_enabled_state, desired_timer_state
            )
            module.exit_json(
                changed=True,
                msg=f"Pi-hole blocking {action_msg_verb}d{action_msg_timer}",
                status=updated_status_data,
            )
        else:
            # No changes needed
            current_state_msg_verb = "enabled" if current_enabled_state else "disabled"
            current_state_msg_timer = (
                f" with timer {current_timer_value}s"
                if current_timer_value is not None
                else ""
            )

            module.exit_json(
                changed=False,
                msg=f"Pi-hole blocking already {current_state_msg_verb}{current_state_msg_timer}",
                status=current_status_data,
            )

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
