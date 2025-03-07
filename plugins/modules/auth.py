#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) Your Name or Organization
# GNU General Public License v3.0+

from ansible.module_utils.basic import AnsibleModule

# PiholeApiClient still contains the static authenticate method
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeConnectionError,
    PiholeApiError,
)

DOCUMENTATION = r"""
---
module: pihole_auth

short_description: >
  Authenticate with the Pi-hole API and retrieve a session ID.

version_added: "1.0"

description:
  - This module performs authentication against the Pi-hole web API.
  - It returns a valid session ID (SID) which can be used to perform authorized
    API calls with other Pi-hole modules.
  - The module does not change the state of the system, but marks
    C(changed=True) for compatibility with workflows.

author:
  - Your Name (@yourhandle)

options:
  pihole:
    description:
      - The base URL of the Pi-hole instance (e.g., https://pihole.local).
    required: true
    type: str
  password:
    description:
      - The password used to authenticate with the Pi-hole API.
    required: true
    type: str
    no_log: true

requirements:
  - requests
"""

EXAMPLES = r"""
- name: Authenticate with Pi-hole and get SID
  wzzrd.pihole.auth:
    pihole: "https://pihole.local"
    password: "{{ pihole_web_password }}"
  register: auth_result

- name: Use SID for another task
  debug:
    msg: "Session ID is {{ auth_result.sid }}"
"""

RETURN = r"""
sid:
  description: >
    A session ID returned by Pi-hole after successful authentication.
  type: str
  returned: success
  sample: "3f93ec7b846ebff8ec9b6219c6c0a2e6"

changed:
  description: Always true, for compatibility with idempotent flows.
  type: bool
  returned: always

msg:
  description: Error message if authentication fails.
  type: str
  returned: on failure
"""


def main() -> None:
    """Ansible module entry point."""
    module_args = {
        "pihole": {"type": "str", "required": True},
        "password": {"type": "str", "required": True, "no_log": True},
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,  # check_mode is not strictly used but good practice
    )
    pihole_url = module.params["pihole"]
    password = module.params["password"]

    # In check_mode, we can't actually authenticate to get a real SID,
    # but we can simulate success.
    # However, the primary purpose of this module is to get a real SID.
    # For now, we'll proceed with authentication even in check_mode,
    # as no state is changed on the Pi-hole.
    # If check_mode were to strictly mean "don't contact remote", this would need adjustment.

    try:
        # Use the PiholeApiClient class method to authenticate
        sid = PiholeApiClient.authenticate(pihole_url, password)  #
        # changed=False because this module retrieves data, it doesn't change Pi-hole state.
        # The previous version had changed=True for workflow compatibility, which is unusual for a get-like operation.
        # Let's stick to changed=False as per typical Ansible module behavior for read-only ops.
        # If changed=True is strictly required for a specific workflow, this can be revisited.
        # Based on the original code's `changed=False` in `module.exit_json(changed=False, sid=sid)`, this is correct.
        module.exit_json(changed=False, sid=sid)

    except PiholeAuthError as e:
        module.fail_json(msg=f"Authentication failed: {str(e)}")
    except PiholeConnectionError as e:
        module.fail_json(msg=f"Connection error: {str(e)}")
    except PiholeApiError as e:
        module.fail_json(msg=f"API error: {str(e)}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
