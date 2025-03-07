# Pi-hole Collection Plugins

This directory contains the plugins for the `wzzrd.pihole` Ansible collection. These plugins provide modules for managing various aspects of Pi-hole DNS servers through their API.

## Module Structure

The collection provides several modules for interacting with Pi-hole:

```
plugins/
├── module_utils/            # Shared utilities for modules
│   ├── __init__.py          # Package initialization
│   ├── api_client.py        # Core API client for HTTP requests
│   ├── api_errors.py        # Custom exception classes
│   ├── action.py            # System action utilities
│   ├── adlist.py            # Adlist management utilities
│   ├── auth.py              # Authentication utilities
│   ├── blocking.py          # DNS blocking management utilities
│   ├── client.py            # Client management utilities
│   ├── cname.py             # CNAME record utilities
│   ├── dhcp.py              # DHCP reservation utilities
│   ├── dns.py               # Static DNS record utilities
│   ├── domain.py            # Domain whitelist/blacklist utilities
│   └── groups.py            # Group management utilities
└── modules/                 # Ansible modules
    ├── action.py            # Pi-hole system actions
    ├── adlist.py            # Manage adlists
    ├── auth.py              # Get session ID
    ├── batch_delete_groups.py # Batch delete groups
    ├── blocking.py          # Enable/disable DNS blocking
    ├── client.py            # Client management
    ├── cname_record.py      # CNAME record management
    ├── dhcp_reservation.py  # DHCP reservation management
    ├── dns_record.py        # Static DNS record management
    ├── domain.py            # Domain management
    └── group.py             # Group management
```

## Architecture Overview

### Module Utils

The `module_utils` directory contains shared code used by the Ansible modules. This promotes code reuse and maintainability:

#### Core Components

- **`api_client.py`**: The central API client that handles all HTTP communication with Pi-hole. It provides:
  - Session management with authentication headers
  - Consistent error handling and retry logic
  - Request/response processing
  - Static method for initial authentication

- **`api_errors.py`**: Custom exception hierarchy for better error handling:
  - `PiholeError`: Base exception class
  - `PiholeApiError`: General API errors with HTTP status codes
  - `PiholeAuthError`: Authentication failures (401)
  - `PiholeNotFoundError`: Resource not found (404)
  - `PiholeValidationError`: Client-side validation errors
  - `PiholeConnectionError`: Network and timeout errors

#### Utility Modules

Each utility module provides functions for specific Pi-hole resources:

- **`action.py`**: System actions (gravity update, DNS restart, log flushing)
- **`adlist.py`**: CRUD operations for blocklists and allowlists
- **`auth.py`**: Authentication helper functions
- **`blocking.py`**: DNS blocking status management
- **`client.py`**: Client configuration by IP/MAC/hostname/interface
- **`cname.py`**: CNAME DNS record management
- **`dhcp.py`**: DHCP static lease management
- **`dns.py`**: A record (static DNS) management
- **`domain.py`**: Whitelist/blacklist domain management
- **`groups.py`**: Group CRUD operations and batch operations

### Ansible Modules

Each module in the `modules` directory is a standalone Ansible module that:
- Imports and uses the appropriate utility functions
- Handles Ansible-specific concerns (argument parsing, check mode, return values)
- Provides idempotent operations
- Returns consistent response formats

## Available Modules

### `wzzrd.pihole.action`

Perform Pi-hole system actions like updating gravity, restarting DNS, or flushing logs.

```yaml
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
```

**Supported actions**: `gravity`, `restartdns`, `flush_logs`, `flush_arp`

### `wzzrd.pihole.adlist`

Manage Pi-hole adlists (blocklists or allowlists).

```yaml
- name: Add an adlist
  wzzrd.pihole.adlist:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    comment: "StevenBlack's unified hosts list"
    groups: ["Default", "BlockAds"]
    enabled: true
    state: present
```

**Key features**:
- Supports both blocklists and allowlists
- Group association
- Enable/disable functionality
- Idempotent operations

### `wzzrd.pihole.auth`

Authenticate with Pi-hole and retrieve a session ID.

```yaml
- name: Get Pi-hole session ID
  wzzrd.pihole.auth:
    pihole: "https://pihole.local"
    password: "{{ pihole_password }}"
  register: auth_result

- name: Set session ID for later use
  set_fact:
    pihole_sid: "{{ auth_result.sid }}"
```

**Note**: This module returns `changed=false` as it only retrieves data.

### `wzzrd.pihole.blocking`

Enable or disable Pi-hole DNS blocking.

```yaml
- name: Enable blocking
  wzzrd.pihole.blocking:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    enabled: true

- name: Disable blocking for 10 minutes
  wzzrd.pihole.blocking:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    enabled: false
    timer: 600
```

**Features**:
- Temporary disable with timer
- Force update option
- Current status retrieval

### `wzzrd.pihole.client`

Manage Pi-hole client configurations, which can be identified by IP, MAC, hostname, or interface.

```yaml
- name: Configure client by IP
  wzzrd.pihole.client:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    client: "192.168.1.100"
    comment: "Living Room TV"
    groups: ["IoT_Devices"]
    state: present

- name: Configure client by MAC
  wzzrd.pihole.client:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    client: "00:11:22:33:44:55"
    comment: "John's Phone"
    groups: ["Personal_Devices"]
    state: present
```

**Client identifiers**:
- IP addresses (IPv4/IPv6, including CIDR)
- MAC addresses
- Hostnames
- Interface names (prefixed with `:`)

### `wzzrd.pihole.cname_record`

Manage CNAME records in Pi-hole.

```yaml
- name: Add a CNAME record
  wzzrd.pihole.cname_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    cname: "alias.example.com"
    name: "target.example.com"
    state: present
```

**Features**:
- Unique enforcement (RFC compliance)
- Wildcard deletion support
- Batch operations

### `wzzrd.pihole.dhcp_reservation`

Manage DHCP reservations in Pi-hole.

```yaml
- name: Create DHCP reservation
  wzzrd.pihole.dhcp_reservation:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    hw: "00:11:22:33:44:55"
    ip: "192.168.1.100"
    name: "laptop.local"
    state: present
```

### `wzzrd.pihole.dns_record`

Manage static DNS records (A records) in Pi-hole.

```yaml
- name: Create DNS record
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    ip: "192.168.1.10"
    name: "printer.local"
    state: present
    unique: true
```

**Features**:
- Unique constraint enforcement
- Wildcard deletion
- Multiple records per IP/hostname support

### `wzzrd.pihole.domain`

Manage domain entries in Pi-hole whitelist/blacklist.

```yaml
- name: Add a domain to blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "example.com"
    type: deny
    kind: exact
    comment: "Known ad domain"
    groups: ["Default"]
    state: present

- name: Add a regex pattern to blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "^ads\\..*\\.example\\.com$"
    type: deny
    kind: regex
    comment: "Block all ad subdomains"
    state: present
```

**Domain types**: `allow` (whitelist), `deny` (blacklist)
**Domain kinds**: `exact`, `regex`

### `wzzrd.pihole.group`

Manage groups in Pi-hole.

```yaml
- name: Create a group
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "IoT_Devices"
    comment: "Internet of Things devices"
    enabled: true
    state: present

- name: Rename a group
  wzzrd.pihole.group:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    name: "IoT_Devices"
    new_name: "Smart_Home_Devices"
    state: present
```

### `wzzrd.pihole.group_batch_delete`

Delete multiple groups in a single operation.

```yaml
- name: Delete multiple groups
  wzzrd.pihole.group_batch_delete:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    names:
      - "Unused_Group_1"
      - "Temporary_Group"
      - "Test_Group"
```

## Module Development Guide

### Creating a New Module

1. **Create the utility module** in `module_utils/`:
   ```python
   # module_utils/new_feature.py
   from typing import Dict, Any, Optional
   from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import PiholeApiClient
   from ansible_collections.wzzrd.pihole.plugins.module_utils.api_errors import PiholeApiError

   def get_feature(client: PiholeApiClient, feature_id: str) -> Optional[Dict[str, Any]]:
       """Get a specific feature."""
       # Implementation
   ```

2. **Create the Ansible module** in `modules/`:
   ```python
   # modules/new_feature.py
   from ansible.module_utils.basic import AnsibleModule
   from ansible_collections.wzzrd.pihole.plugins.module_utils.api_client import PiholeApiClient
   from ansible_collections.wzzrd.pihole.plugins.module_utils.new_feature import get_feature

   def main():
       module_args = {
           "pihole": {"type": "str", "required": True},
           "sid": {"type": "str", "required": True, "no_log": True},
           # Add your parameters
       }

       module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
       # Implementation
   ```

### Best Practices

1. **Error Handling**: Always use the custom exception classes for consistent error handling
2. **Idempotency**: Ensure modules are idempotent - running them multiple times should not change the result
3. **Check Mode**: Support check mode where possible
4. **Documentation**: Include comprehensive DOCUMENTATION, EXAMPLES, and RETURN sections
5. **Type Hints**: Use type hints for better code clarity and IDE support

## API Compatibility

This collection is designed for Pi-hole v6.0+ with the latest API endpoints. The modules are tested with:

- Pi-hole Docker Tag 2025.04.0
- Core v6.0.6
- FTL v6.1
- Web interface v6.1

Older versions of Pi-hole may not support all features used by this collection.

## Error Handling

All modules use the same error handling approach through the shared API client. Errors are categorized into:

- `PiholeAuthError`: Authentication failures
- `PiholeConnectionError`: Network connectivity issues
- `PiholeApiError`: API errors (bad requests, server errors)
- `PiholeValidationError`: Input validation errors
- `PiholeNotFoundError`: Resource not found errors

These exceptions are caught by the modules and converted to appropriate Ansible error messages.

## Session Management

Most Pi-hole API operations require a valid session ID. The `wzzrd.pihole.auth` module provides this ID, which should be stored and reused for subsequent tasks in a playbook.

**Important**: Pi-hole session IDs may expire after a period of inactivity. In long-running playbooks, you may need to re-authenticate periodically.

## Testing

When developing or modifying modules:

1. Test with `--check` mode first
2. Verify idempotency by running the same task multiple times
3. Test both `present` and `absent` states
4. Verify error handling with invalid inputs
5. Test with different Pi-hole configurations

## Documentation

For detailed module documentation, use the `ansible-doc` command:

```bash
ansible-doc wzzrd.pihole.dns_record
ansible-doc wzzrd.pihole.client
# etc.
```

## Contributing

When contributing new modules or modifications:

1. Follow the existing code structure and patterns
2. Include comprehensive documentation
3. Add type hints to utility functions
4. Ensure proper error handling
5. Test thoroughly with Pi-hole v6.0+
6. Update this README if adding new modules
