#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+

from __future__ import annotations
DOCUMENTATION = r"""
---
module: dns_record

short_description: Manage Pi-hole static DNS records (A records) via its API

version_added: "1.0.0"

description:
  - This module allows you to create or delete static A records (IP → hostname)
    in a Pi-hole instance using its API.
  - It supports idempotent management of entries.
  - You must provide a valid session ID (SID) for authentication.

author:
  - Maxim Burgerhout (@wzzrd)

options:
  pihole:
    description:
      - URL of the Pi-hole instance (e.g., https://pihole.local).
    required: true
    type: str
  sid:
    description:
      - Session ID used for authenticating with the Pi-hole API.
    required: true
    type: str
  ip:
    description:
      - The IP address to associate with the hostname.
      - Use "all" with state=absent and a specific 'name' to remove all IPs mapped to that name.
    required: true
    type: str
  name:
    description:
      - The DNS hostname to map to the IP address.
      - Use "all" with state=absent and a specific 'ip' to remove all names mapped to that IP.
    required: true
    type: str
  state:
    description:
      - Whether the DNS record should exist or not.
    choices: [present, absent]
    default: present
    required: false
    type: str
  unique:
    description:
      - >
        If true (default), when adding a record (e.g., 1.2.3.4 -> myhost.local),
        it ensures that 'myhost.local' does not point to any other IP,
        and '1.2.3.4' does not resolve to any other hostname.
        Any such conflicting records will be removed before adding the new one.
        This applies only when state is 'present'.
      - If false, allows multiple names per IP or multiple IPs per name.
    required: false
    type: bool
    default: true

requirements: []
"""

EXAMPLES = r"""
- name: Ensure static DNS record is present (and unique)
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    ip: "192.168.1.10"
    name: "printer.local"
    state: present
    unique: true

- name: Ensure static DNS record is absent
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    ip: "192.168.1.10"
    name: "printer.local"
    state: absent

- name: Remove all DNS records for IP 192.168.1.20
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    ip: "192.168.1.20"
    name: "all"
    state: absent

- name: Remove all DNS records for hostname server.local
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    ip: "all"
    name: "server.local"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was made.
  type: bool
  returned: always

msg:
  description: Informational or error message.
  type: str
  returned: always

result:
  description: Raw response from Pi-hole API (on successful add).
  type: dict
  returned: when state is present and a record is added and successful
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.dns import (
    get_static_dns_records,
    check_static_dns_record_exists,
    add_static_dns_record,
    delete_static_dns_record,
    parse_dns_records,
    find_conflicting_dns_records,
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
    Ansible module entry point for managing Pi-hole static DNS records.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "ip": {"type": "str", "required": True},
        "name": {"type": "str", "required": True},
        "state": {
            "type": "str",
            "required": False,
            "choices": ["present", "absent"],
            "default": "present",
        },
        "unique": {"type": "bool", "required": False, "default": True},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    pihole_url = module.params["pihole"]
    sid = module.params["sid"]
    ip_param = module.params["ip"]
    name_param = module.params["name"]
    state = module.params["state"]
    unique_flag = module.params["unique"]

    try:
        api_client = PiholeApiClient(pihole_url, sid)
        existing_raw_records = get_static_dns_records(api_client)
        parsed_existing_records = parse_dns_records(existing_raw_records)

        exact_match_exists = check_static_dns_record_exists(
            api_client, ip_param, name_param
        )

        if state == "present":
            if ip_param.lower() == "all" or name_param.lower() == "all":
                module.fail_json(
                    msg="Cannot use 'all' for 'ip' or 'name' when state is 'present'."
                )

            conflicts_to_remove = []
            made_changes_during_conflict_resolution = False

            if unique_flag:
                conflicts_to_remove = find_conflicting_dns_records(
                    parsed_existing_records, ip_param, name_param
                )

                if conflicts_to_remove:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,  # Removing conflicts is a change
                            msg=(
                                f"Would remove {len(conflicts_to_remove)} conflicting DNS records "
                                f"to uniquely set {ip_param} -> {name_param}."
                            ),
                        )

                    for conf_ip, conf_name in conflicts_to_remove:
                        delete_static_dns_record(api_client, conf_ip, conf_name)
                        made_changes_during_conflict_resolution = True

                    # Re-check for exact match after conflict resolution
                    exact_match_exists = check_static_dns_record_exists(
                        api_client, ip_param, name_param
                    )

            if exact_match_exists and not made_changes_during_conflict_resolution:
                module.exit_json(
                    changed=False,
                    msg=f"DNS record {ip_param} -> {name_param} already exists.",
                )
            else:
                # If check_mode and no conflict changes made, this is where we'd add
                if module.check_mode and not made_changes_during_conflict_resolution:
                    module.exit_json(
                        changed=True,
                        msg=f"Would add DNS record {ip_param} -> {name_param}.",
                    )

                result = add_static_dns_record(api_client, ip_param, name_param)
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"DNS record {ip_param} -> {name_param} added/ensured.",
                )

        elif state == "absent":
            if name_param.lower() == "all" and ip_param.lower() == "all":
                module.fail_json(
                    msg="Refusing to remove all DNS records: either 'name' or 'ip' can be 'all', but not both."
                )

            records_to_delete = []
            if name_param.lower() == "all":  # Delete all records for the given IP
                for rec_ip, rec_name in parsed_existing_records:
                    if rec_ip == ip_param:
                        records_to_delete.append((rec_ip, rec_name))
            elif ip_param.lower() == "all":  # Delete all records for the given name
                for rec_ip, rec_name in parsed_existing_records:
                    if rec_name == name_param:
                        records_to_delete.append((rec_ip, rec_name))
            elif exact_match_exists:  # Specific record to delete
                records_to_delete.append((ip_param, name_param))

            if not records_to_delete:
                module.exit_json(
                    changed=False, msg="No matching DNS records found to delete."
                )

            if module.check_mode:
                msg = f"Would remove {len(records_to_delete)} DNS record(s): "
                msg += ", ".join([f"{ip} -> {name}" for ip, name in records_to_delete])
                module.exit_json(changed=True, msg=msg)

            for rec_ip_del, rec_name_del in records_to_delete:
                delete_static_dns_record(api_client, rec_ip_del, rec_name_del)

            module.exit_json(
                changed=True, msg=f"Removed {len(records_to_delete)} DNS record(s)."
            )

    except PiholeValidationError as e:
        module.fail_json(msg=str(e))
    except (
        PiholeNotFoundError
    ) as e:  # Should generally be handled by logic, but as a fallback
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
