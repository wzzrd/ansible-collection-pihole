#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+

DOCUMENTATION = r"""
---
module: dhcp_reservation

short_description: Manage Pi-hole DHCP reservations via its API

version_added: "1.0.0"

description:
  - This module allows you to create or delete DHCP reservations in a Pi-hole
    instance using its API.
  - It supports idempotent operations using the device's MAC address, IP,
    and hostname.
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
  hw:
    description:
      - Hardware (MAC) address of the device to reserve a DHCP lease for.
    required: true
    type: str
  ip:
    description:
      - The static IP address to assign to the device.
    required: true
    type: str
  name:
    description:
      - The hostname to associate with the DHCP reservation.
    required: true
    type: str
  state:
    description:
      - Whether the DHCP reservation should exist or be removed.
    choices: [present, absent]
    default: present
    required: false
    type: str

requirements: []
"""

EXAMPLES = r"""
- name: Ensure a DHCP reservation is present
  wzzrd.pihole.dhcp_reservation:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    hw: "00:11:22:33:44:55"
    ip: "192.168.1.100"
    name: "mydevice.local"
    state: present

- name: Ensure a DHCP reservation is removed
  wzzrd.pihole.dhcp_reservation:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    hw: "00:11:22:33:44:55"
    ip: "192.168.1.100"
    name: "mydevice.local"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was made to the DHCP configuration.
  type: bool
  returned: always

msg:
  description: Information about the action performed or an error message.
  type: str
  returned: always

result:
  description: Raw response from the Pi-hole API when a reservation is added.
  type: dict
  returned: when state is present and a reservation is added
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.dhcp import (
    check_dhcp_reservation_exists,
    add_dhcp_reservation,
    delete_dhcp_reservation,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import (
    PiholeAuthError,
    PiholeConnectionError,
    PiholeApiError,
)


def main():
    """
    Ansible module entry point for managing Pi-hole DHCP reservations.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "hw": {"type": "str", "required": True},
        "ip": {"type": "str", "required": True},
        "name": {"type": "str", "required": True},
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
    hw_address = module.params["hw"]
    ip_address = module.params["ip"]
    hostname = module.params["name"]
    state = module.params["state"]

    try:
        # Initialize the Pi-hole API client
        client = PiholeApiClient(pihole_url, sid)

        # Check if the reservation exists
        exists = check_dhcp_reservation_exists(
            client, hw_address, ip_address, hostname
        )  #

        if state == "present":
            if exists:
                module.exit_json(
                    changed=False,
                    msg=f"DHCP reservation for MAC {hw_address} ({ip_address} -> {hostname}) already exists.",
                )
            else:
                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        msg=f"Would add DHCP reservation for MAC {hw_address} ({ip_address} -> {hostname}).",
                    )

                result = add_dhcp_reservation(
                    client, hw_address, ip_address, hostname
                )  #
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"DHCP reservation for MAC {hw_address} ({ip_address} -> {hostname}) added.",
                )

        elif state == "absent":
            if not exists:
                module.exit_json(
                    changed=False,
                    msg=f"DHCP reservation for MAC {hw_address} ({ip_address} -> {hostname}) does not exist.",
                )
            else:
                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        msg=f"Would delete DHCP reservation for MAC {hw_address} ({ip_address} -> {hostname}).",
                    )

                delete_dhcp_reservation(client, hw_address, ip_address, hostname)  #
                module.exit_json(
                    changed=True,
                    msg=f"DHCP reservation for MAC {hw_address} ({ip_address} -> {hostname}) deleted.",
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
