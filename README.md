# Ansible Collection - wzzrd.pihole

An Ansible collection for managing Pi-hole DNS servers through their API. This collection provides modules to configure and manage various aspects of Pi-hole, including client configurations, DNS records, adlists, groups, domains, DHCP, and more.

## Requirements

- Python 3.8+
- Ansible 2.10+
- Python `requests` library
- Pi-hole Server v6.0+ with web interface

Tested with:
- Python 3.13.3
- Ansible 2.16.13
- Pi-hole Docker Tag 2025.04.0
  - Core v6.0.6
  - FTL v6.1
  - Web interface v6.1

## Installation

From Ansible Galaxy:

```bash
ansible-galaxy collection install wzzrd.pihole
```

From source:

```bash
git clone https://github.com/wzzrd/ansible-collection-pihole.git
cd ansible-collection-pihole
ansible-galaxy collection build
ansible-galaxy collection install wzzrd-pihole-*.tar.gz
```

## Authentication

Pi-hole API requires authentication using a session ID. The collection provides a module to obtain this session ID:

```yaml
- name: Authenticate with Pi-hole
  wzzrd.pihole.auth:
    pihole: "https://pihole.local"
    password: "{{ pihole_web_password }}"
  register: auth_result

- name: Store the session ID for later use
  set_fact:
    pihole_sid: "{{ auth_result.sid }}"
```

## Example Playbook

Here's a comprehensive example playbook that demonstrates various Pi-hole configuration tasks:

```yaml
---
- name: Configure Pi-hole
  hosts: pihole_servers
  gather_facts: false
  vars:
    pihole_url: "https://pihole.local"
    pihole_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          ...encrypted password...

  tasks:
    - name: Authenticate with Pi-hole
      wzzrd.pihole.auth:
        pihole: "{{ pihole_url }}"
        password: "{{ pihole_password }}"
      register: auth_result

    - name: Set session ID
      set_fact:
        pihole_sid: "{{ auth_result.sid }}"

    - name: Create device groups
      wzzrd.pihole.group:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        name: "{{ item.name }}"
        comment: "{{ item.comment }}"
        state: present
      loop:
        - { name: "IoT_Devices", comment: "Internet of Things devices" }
        - { name: "Kids_Devices", comment: "Devices used by children" }
        - { name: "Work_Devices", comment: "Work-related devices" }

    - name: Configure clients
      wzzrd.pihole.client:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        client: "{{ item.client }}"
        comment: "{{ item.comment }}"
        groups: "{{ item.groups }}"
        state: present
      loop:
        - { client: "192.168.1.100", comment: "Living Room TV", groups: ["IoT_Devices"] }
        - { client: "00:11:22:33:44:55", comment: "John's Phone", groups: ["Default"] }
        - { client: "laptop.local", comment: "Work Laptop", groups: ["Work_Devices"] }

    - name: Add static DNS records
      wzzrd.pihole.dns_record:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        ip: "{{ item.ip }}"
        name: "{{ item.name }}"
        state: present
      loop:
        - { ip: "192.168.1.10", name: "printer.local" }
        - { ip: "192.168.1.20", name: "nas.local" }

    - name: Add CNAME records
      wzzrd.pihole.cname_record:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        cname: "{{ item.cname }}"
        name: "{{ item.name }}"
        state: present
      loop:
        - { cname: "www.local", name: "server.local" }
        - { cname: "ftp.local", name: "nas.local" }

    - name: Configure DHCP reservations
      wzzrd.pihole.dhcp_reservation:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        hw: "{{ item.hw }}"
        ip: "{{ item.ip }}"
        name: "{{ item.name }}"
        state: present
      loop:
        - { hw: "00:11:22:33:44:55", ip: "192.168.1.100", name: "laptop.local" }
        - { hw: "AA:BB:CC:DD:EE:FF", ip: "192.168.1.101", name: "phone.local" }

    - name: Add domains to blocklist
      wzzrd.pihole.domain:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        domain: "{{ item.domain }}"
        type: "{{ item.type }}"
        kind: "{{ item.kind }}"
        comment: "{{ item.comment | default('') }}"
        state: present
      loop:
        - { domain: "ads.example.com", type: "deny", kind: "exact", comment: "Known ad server" }
        - { domain: "tracking.example.net", type: "deny", kind: "exact", comment: "Tracking domain" }
        - { domain: "^ads\\..*\\.example\\.com$", type: "deny", kind: "regex", comment: "Block all ad subdomains" }

    - name: Add adlists
      wzzrd.pihole.adlist:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        address: "{{ item.address }}"
        comment: "{{ item.comment }}"
        state: present
      loop:
        - { address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts", comment: "StevenBlack's unified hosts list" }
        - { address: "https://s3.amazonaws.com/lists.disconnect.me/simple_tracking.txt", comment: "Disconnect.me Tracking list" }

    - name: Update gravity to apply changes
      wzzrd.pihole.action:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        action: gravity
```

## Available Modules

The collection provides the following modules for managing Pi-hole:

### System Management

#### `wzzrd.pihole.action`
Perform system actions like updating gravity, restarting DNS, or flushing logs.

```yaml
- name: Update gravity (download adlists)
  wzzrd.pihole.action:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    action: gravity

- name: Restart DNS service
  wzzrd.pihole.action:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    action: restartdns
```

#### `wzzrd.pihole.auth`
Authenticate with the Pi-hole API and retrieve a session ID.

```yaml
- name: Get Pi-hole session ID
  wzzrd.pihole.auth:
    pihole: "https://pihole.local"
    password: "{{ pihole_password }}"
  register: auth_result
```

#### `wzzrd.pihole.blocking`
Manage Pi-hole DNS blocking status.

```yaml
- name: Disable blocking for 10 minutes
  wzzrd.pihole.blocking:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    enabled: false
    timer: 600
```

### Client and Group Management

#### `wzzrd.pihole.client`
Manage client configurations identified by IP, MAC, hostname, or interface.

```yaml
- name: Configure client by IP
  wzzrd.pihole.client:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    client: "192.168.1.100"
    comment: "Living Room TV"
    groups: ["IoT_Devices"]
    state: present
```

#### `wzzrd.pihole.group`
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
```

#### `wzzrd.pihole.group_batch_delete`
Delete multiple groups in a single operation.

```yaml
- name: Delete multiple groups
  wzzrd.pihole.group_batch_delete:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    names:
      - "Unused_Group_1"
      - "Temporary_Group"
```

### DNS Management

#### `wzzrd.pihole.dns_record`
Manage static DNS records (A records).

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

#### `wzzrd.pihole.cname_record`
Manage CNAME records.

```yaml
- name: Add CNAME record
  wzzrd.pihole.cname_record:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    cname: "alias.example.com"
    name: "target.example.com"
    state: present
```

#### `wzzrd.pihole.dhcp_reservation`
Manage DHCP reservations.

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

### Domain and Adlist Management

#### `wzzrd.pihole.domain`
Manage domain entries in Pi-hole whitelist/blacklist.

```yaml
- name: Add domain to blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "ads.example.com"
    type: deny
    kind: exact
    comment: "Known ad domain"
    groups: ["Default"]
    state: present

- name: Add regex pattern to blacklist
  wzzrd.pihole.domain:
    pihole: "https://pihole.local"
    sid: "{{ pihole_sid }}"
    domain: "^ads\\..*\\.example\\.com$"
    type: deny
    kind: regex
    comment: "Block all ad subdomains"
    state: present
```

#### `wzzrd.pihole.adlist`
Manage adlists (blocklists and allowlists).

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

## Module Documentation

For detailed documentation on each module, use the `ansible-doc` command:

```bash
ansible-doc wzzrd.pihole.dns_record
ansible-doc wzzrd.pihole.client
ansible-doc wzzrd.pihole.domain
# etc.
```

## Error Handling

All modules in this collection use consistent error handling. When a module fails, it will provide a descriptive error message including the HTTP status code and response content if available.

Common error types:
- Authentication failures (`Authentication error: ...`)
- Connection issues (`Connection error: ...`)
- API errors (`API error: ...`)
- Validation errors (when provided parameters are invalid)

## Session Management

Most Pi-hole API operations require a valid session ID. The `wzzrd.pihole.auth` module provides this ID, which should be stored and reused for subsequent tasks in a playbook.

**Note:** Pi-hole session IDs may expire after a period of inactivity. In long-running playbooks, you may need to re-authenticate periodically.

## Best Practices

1. **Store credentials securely**: Use Ansible Vault to encrypt your Pi-hole password.
2. **Use variables**: Define your Pi-hole URL and other common parameters as variables.
3. **Group related tasks**: Organize your playbooks logically by grouping related configurations.
4. **Apply changes**: Remember to run the gravity update action after making changes to adlists or domains.
5. **Use check mode**: Test your playbooks with `--check` before applying changes.

## License

GPL-2.0-or-later

## Author

- Your Name (@yourhandle)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
