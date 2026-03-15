#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+

DOCUMENTATION = r"""
---
module: cname_record

short_description: Manage Pi-hole CNAME DNS records via its API

version_added: "1.0.0"

description:
  - This module allows you to create or remove CNAME records in a Pi-hole instance using its API.
  - You must provide a valid session ID (SID) for authentication.
  - Supports uniqueness enforcement and wildcard deletion.
  - Per DNS specification, a given alias (CNAME) may only point to a single canonical name.

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
  cname:
    description:
      - The alias (CNAME) to be added or removed.
      - Use "all" with state=absent and a specific 'name' to remove all aliases pointing to that name.
    required: true
    type: str
  name:
    description:
      - The canonical name the alias should point to.
      - Use "all" with state=absent and a specific 'cname' to remove all targets assigned to the alias.
    required: true
    type: str
  state:
    description:
      - Whether the CNAME record should exist or not.
    choices: [present, absent]
    default: present
    required: false
    type: str
  unique:
    description:
      - >
        If true (default), ensures that before adding a CNAME record (cname_A -> target_A),
        any existing CNAME record (cname_A -> target_B) is removed.
        Also, if adding (cname_A -> target_A), any existing (cname_X -> target_A)
        would be removed. This behavior might be stricter than DNS RFCs for the target side
        but can be useful for exclusive CNAME target management in Pi-hole.
        This option primarily affects the 'present' state.
    type: bool
    required: false
    default: true

requirements: []
"""

EXAMPLES = r"""
- name: Ensure a CNAME record exists in Pi-hole
  wzzrd.pihole.cname_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    cname: "alias.example.com"
    name: "target.example.com"
    state: present

- name: Remove a specific CNAME record
  wzzrd.pihole.cname_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    cname: "alias.example.com"
    name: "target.example.com"
    state: absent

- name: Remove all aliases pointing to a specific target
  wzzrd.pihole.cname_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    cname: "all" # This implies 'cname' is wildcard for deletion
    name: "target.example.com" # Target is specific
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was made.
  type: bool
  returned: always
msg:
  description: Informational message on actions taken.
  type: str
  returned: on change or check_mode or error
result:
  description: Raw response from Pi-hole API (on successful add).
  type: dict
  returned: when state is present and a record is added
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.cname import (
    get_cname_records,
    check_cname_record_exists,
    add_cname_record,
    delete_cname_record,
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
    Ansible module entry point for CNAME record management.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "cname": {"type": "str", "required": True},  # This is the alias
        "name": {"type": "str", "required": True},  # This is the target
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
    cname_alias = module.params["cname"]
    target_name = module.params["name"]
    state = module.params["state"]
    unique_flag = module.params["unique"]

    try:
        api_client = PiholeApiClient(pihole_url, sid)
        existing_raw_records = get_cname_records(api_client)  #

        # Parse existing records into a more usable format, e.g., list of tuples
        # Pi-hole API returns them as "cname,target" strings
        parsed_existing_records = []
        for rec_str in existing_raw_records:
            parts = rec_str.split(",", 1)
            if len(parts) == 2:
                parsed_existing_records.append((parts[0], parts[1]))

        exact_match_exists = check_cname_record_exists(
            api_client, cname_alias, target_name
        )  #

        if state == "present":
            conflicts_to_remove = []
            made_changes_during_conflict_resolution = False

            if unique_flag:
                # Check for RFC violation: an alias (cname_alias) cannot point to multiple targets.
                # Also, if unique is true, ensure target_name is not pointed to by other cnames.
                for rec_c, rec_t in parsed_existing_records:
                    is_current_record = rec_c == cname_alias and rec_t == target_name
                    if is_current_record:
                        continue

                    # Conflict 1: Same CNAME alias points to a different target. Must be removed.
                    if rec_c == cname_alias and rec_t != target_name:
                        conflicts_to_remove.append((rec_c, rec_t))

                    # Conflict 2 (stricter 'unique' interpretation):
                    # Different CNAME alias points to the same target. Remove if unique.
                    if rec_t == target_name and rec_c != cname_alias:
                        conflicts_to_remove.append((rec_c, rec_t))

                if conflicts_to_remove:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,  # Even if target record exists, removing conflicts is a change
                            msg=(
                                f"Would remove {len(conflicts_to_remove)} conflicting CNAME records "
                                f"to uniquely set {cname_alias} -> {target_name}."
                            ),
                        )

                    for conf_c, conf_t in conflicts_to_remove:
                        delete_cname_record(api_client, conf_c, conf_t)  #
                        made_changes_during_conflict_resolution = True

                    # After removing conflicts, the target record might now effectively "not exist"
                    # if it was one of the conflicts (e.g. cname_alias -> old_target).
                    # Re-check for an exact match if we are trying to create cname_alias -> target_name
                    exact_match_exists = check_cname_record_exists(
                        api_client, cname_alias, target_name
                    )  #

            if exact_match_exists and not made_changes_during_conflict_resolution:
                module.exit_json(
                    changed=False,
                    msg=f"CNAME record {cname_alias} -> {target_name} already exists.",
                )
            else:
                if (
                    module.check_mode and not made_changes_during_conflict_resolution
                ):  # if conflicts were handled, already exited
                    module.exit_json(
                        changed=True,
                        msg=f"Would add CNAME record {cname_alias} -> {target_name}.",
                    )

                result = add_cname_record(api_client, cname_alias, target_name)  #
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"CNAME record {cname_alias} -> {target_name} added/ensured.",
                )

        elif state == "absent":
            if cname_alias.lower() == "all" and target_name.lower() == "all":
                module.fail_json(
                    msg="Refusing to remove all CNAME records. Specify at least one of 'cname' or 'name' not to be 'all'."
                )

            records_to_delete = []
            if (
                cname_alias.lower() == "all"
            ):  # Delete all CNAMEs pointing to target_name
                for rec_c, rec_t in parsed_existing_records:
                    if rec_t == target_name:
                        records_to_delete.append((rec_c, rec_t))
            elif target_name.lower() == "all":  # Delete all targets for cname_alias
                for rec_c, rec_t in parsed_existing_records:
                    if rec_c == cname_alias:
                        records_to_delete.append((rec_c, rec_t))
            elif exact_match_exists:  # Specific record to delete
                records_to_delete.append((cname_alias, target_name))

            if not records_to_delete:
                module.exit_json(
                    changed=False, msg="No matching CNAME records found to delete."
                )

            if module.check_mode:
                msg = f"Would remove {len(records_to_delete)} CNAME record(s): "
                msg += ", ".join([f"{c} -> {t}" for c, t in records_to_delete])
                module.exit_json(changed=True, msg=msg)

            for rec_c, rec_t in records_to_delete:
                delete_cname_record(api_client, rec_c, rec_t)  #

            module.exit_json(
                changed=True, msg=f"Removed {len(records_to_delete)} CNAME record(s)."
            )

    except PiholeValidationError as e:
        module.fail_json(msg=str(e))
    except (
        PiholeNotFoundError
    ) as e:  # Should be handled by check_exists, but as safeguard
        module.fail_json(msg=str(e))
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
