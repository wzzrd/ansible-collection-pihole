#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026 Maxim Burgerhout <maxim@wzzrd.com>
# GNU General Public License v3.0+

DOCUMENTATION = r"""
---
module: domain

short_description: Manage Pi-hole domain entries (whitelist/blacklist) via its API

version_added: "1.0.0"

description:
  - This module allows you to add or remove domains from Pi-hole's whitelist/blacklist.
  - It supports creating both exact domains and regex patterns.
  - You can move domains between lists (e.g., from deny to allow) by specifying both type and kind.
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
  domain:
    description:
      - The domain to add or remove.
      - Can be an exact domain (e.g., example.com) or a regex pattern.
    required: true
    type: str
  type:
    description:
      - Whether to add the domain to the whitelist (allow) or blacklist (deny).
      - When state=present, this is the target type.
      - When state=absent, this is the type of the list from which to remove the domain.
    choices: [allow, deny]
    default: deny
    required: false # Default implies it's not strictly required if other params make intent clear (but usually is)
    type: str
  kind:
    description:
      - Whether the domain is an exact match or a regex pattern.
      - When state=present, this is the target kind.
      - When state=absent, this is the kind of the list from which to remove the domain.
    choices: [exact, regex]
    default: exact
    required: false # Default implies it's not strictly required
    type: str
  comment:
    description:
      - A comment to associate with the domain entry.
      - If not provided during updates, the existing comment will be preserved.
    required: false
    type: str
  groups:
    description:
      - List of group names to associate with this domain.
      - By default, the domain is added to the "Default" group.
      - Group names are case-sensitive and must match exactly.
    required: false
    type: list
    elements: str
    default: ["Default"]
  enabled:
    description:
      - Whether the domain entry is enabled.
    required: false
    type: bool
    default: true
  state:
    description:
      - Whether the domain entry should exist or not.
    choices: [present, absent]
    default: present
    required: false
    type: str

requirements: []
"""

EXAMPLES = r"""
- name: Add a domain to the blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "example.com"
    type: deny
    kind: exact
    comment: "Known malware site"
    state: present

- name: Add a domain to the whitelist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "good-site.com"
    type: allow
    kind: exact
    comment: "Company site"
    groups: ["Default", "Work"]
    state: present

- name: Add a regex pattern to the blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "^ad[.\\-_].*\\.example\\.com$"
    type: deny
    kind: regex
    comment: "Block all ad subdomains"
    state: present

- name: Change a domain from blacklist to whitelist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "example.com" # Domain to manage
    type: allow            # Target type: allowlist
    kind: exact            # Target kind: exact
    comment: "Moved from blacklist to whitelist"
    state: present         # Ensure it's present (which means add or update)
                           # The module logic will find it (if it exists, e.g. on blacklist)
                           # and then update it to be on the allowlist.

- name: Remove a domain from the blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "example.com"
    type: deny             # Type of list to remove from
    kind: exact            # Kind of list to remove from
    state: absent
"""

RETURN = r"""
changed:
  description: Whether a change was made to the domain entries.
  type: bool
  returned: always

msg:
  description: Information about the action that was performed.
  type: str
  returned: always

domain:
  description: Details of the domain that was created or modified.
  type: dict
  returned: when state is present and a domain is created or updated

result:
  description: Raw response from the Pi-hole API.
  type: dict
  returned: when a domain is created, updated, or deleted
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import (
    PiholeApiClient,
)
from ansible_collections.wzzrd.pihole.plugins.module_utils.domain import (
    get_domain,
    add_domain,
    update_domain,
    delete_domain,
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
    Ansible module entry point for managing Pi-hole domains.
    """
    module_args = {
        "pihole": {"type": "str", "required": True},
        "sid": {"type": "str", "required": True, "no_log": True},
        "domain": {"type": "str", "required": True},
        "type": {  # Target type for 'present', current type for 'absent'
            "type": "str",
            "required": False,
            "choices": ["allow", "deny"],
            "default": "deny",
        },
        "kind": {  # Target kind for 'present', current kind for 'absent'
            "type": "str",
            "required": False,
            "choices": ["exact", "regex"],
            "default": "exact",
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
    domain_name = module.params["domain"]
    # For 'present', these are the desired type/kind.
    # For 'absent', these specify which list the domain should be removed from.
    param_type = module.params["type"]
    param_kind = module.params["kind"]
    param_comment = module.params["comment"]
    param_group_names = module.params["groups"]
    param_enabled = module.params["enabled"]
    param_state = module.params["state"]

    try:
        api_client = PiholeApiClient(pihole_url, sid)
        param_group_ids = group_names_to_ids(api_client, param_group_names)  #

        # Try to find the domain in any list to determine its current location if it exists.
        # The get_domain utility can search without type/kind to find it anywhere.
        existing_domain_data, current_location = get_domain(api_client, domain_name)  #
        exists_somewhere = existing_domain_data is not None
        current_type, current_kind = (
            current_location if current_location else (None, None)
        )

        if param_state == "present":
            if exists_somewhere:  # Domain exists, may need update or move
                # Check if properties or location (type/kind) need to change
                needs_property_update = False
                if (
                    param_comment is not None
                    and existing_domain_data.get("comment", "") != param_comment
                ):
                    needs_property_update = True
                if (
                    param_enabled is not None
                    and existing_domain_data.get("enabled", True) != param_enabled
                ):
                    needs_property_update = True

                existing_group_ids = sorted(existing_domain_data.get("groups", [0]))
                if sorted(param_group_ids) != existing_group_ids:
                    needs_property_update = True

                is_different_list = (
                    current_type != param_type or current_kind != param_kind
                )

                if needs_property_update or is_different_list:
                    if module.check_mode:
                        msg = f"Would update domain '{domain_name}'"
                        if is_different_list:
                            msg += f" and move from {current_type}/{current_kind} to {param_type}/{param_kind}"
                        module.exit_json(changed=True, msg=msg)

                    # update_domain needs current_type/kind to find it, and target_type/kind for the update
                    result = update_domain(
                        api_client,
                        domain_name,
                        current_type,
                        current_kind,  # Current location
                        param_type,
                        param_kind,  # Target location
                        comment=param_comment,
                        group_ids=param_group_ids,
                        enabled=param_enabled,
                    )  #

                    updated_domain_details = (
                        result.get("domains", [{}])[0] if result.get("domains") else {}
                    )
                    msg = f"Domain '{domain_name}' updated"
                    if is_different_list:
                        msg = f"Domain '{domain_name}' moved from {current_type}/{current_kind} to {param_type}/{param_kind} and updated"
                    module.exit_json(
                        changed=True,
                        result=result,
                        msg=msg,
                        domain=updated_domain_details,
                    )
                else:
                    module.exit_json(
                        changed=False,
                        msg=f"Domain '{domain_name}' already exists as {param_type}/{param_kind} with specified properties",
                        domain=existing_domain_data,
                    )

            else:  # Domain does not exist, create it
                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        msg=f"Would add domain '{domain_name}' to {param_type}/{param_kind}",
                    )

                result = add_domain(
                    api_client,
                    domain_name,
                    param_type,
                    param_kind,
                    param_comment,
                    param_group_ids,
                    param_enabled,
                )  #
                created_domain_details = (
                    result.get("domains", [{}])[0] if result.get("domains") else {}
                )
                module.exit_json(
                    changed=True,
                    result=result,
                    msg=f"Domain '{domain_name}' added to {param_type}/{param_kind}",
                    domain=created_domain_details,
                )

        elif param_state == "absent":
            # For absent, we need to know exactly which list (type/kind) to remove from.
            if (
                exists_somewhere
                and current_type == param_type
                and current_kind == param_kind
            ):
                # It exists in the target list for deletion
                if module.check_mode:
                    module.exit_json(
                        changed=True,
                        msg=f"Would remove domain '{domain_name}' from {param_type}/{param_kind}",
                    )

                # delete_domain returns True if successful, False if not found by its own API call
                delete_success = delete_domain(
                    api_client, domain_name, param_type, param_kind
                )
                if delete_success:  # Successfully deleted
                    module.exit_json(
                        changed=True,
                        msg=f"Domain '{domain_name}' removed from {param_type}/{param_kind}",
                    )
                else:  # delete_domain returned False, meaning it was NOT found by the DELETE call
                    # This implies it was already absent from that specific list when deletion was attempted.
                    module.exit_json(
                        changed=False,
                        msg=f"Domain '{domain_name}' was already absent from {param_type}/{param_kind} when deletion was attempted.",
                    )
            elif exists_somewhere:  # Exists, but not in the list specified for deletion
                module.exit_json(
                    changed=False,
                    msg=f"Domain '{domain_name}' exists in {current_type}/{current_kind}, not in the specified {param_type}/{param_kind} for removal.",
                )
            else:  # Domain does not exist anywhere
                module.exit_json(
                    changed=False,
                    msg=f"Domain '{domain_name}' does not exist, cannot remove.",
                )

    except PiholeValidationError as e:
        module.fail_json(msg=str(e))
    except (
        PiholeNotFoundError
    ) as e:  # Can be raised by get_domain if specific type/kind not found
        module.fail_json(msg=f"Error related to domain not found: {str(e)}")
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
