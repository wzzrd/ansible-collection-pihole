# wzzrd.pihole

An Ansible collection for managing Pi-hole DNS servers through their v6 API.

> **Primary repository:** This collection is developed on [Gitea at git.wzzrd.com](https://git.wzzrd.com/wzzrd/ansible-collection-pihole). The [GitHub repository](https://github.com/wzzrd/ansible-collection-pihole) is a read-only mirror. Pull requests opened on GitHub will be applied manually upstream.

## Contents

| Category | Module | Description |
|---|---|---|
| **System** | `wzzrd.pihole.auth` | Authenticate and obtain a session ID |
| | `wzzrd.pihole.action` | Run gravity update, DNS restart, log flush |
| | `wzzrd.pihole.blocking` | Enable or disable DNS blocking |
| **Client/Group** | `wzzrd.pihole.group` | Create, rename, enable/disable groups |
| | `wzzrd.pihole.client` | Manage clients (IP, MAC, hostname, CIDR) |
| | `wzzrd.pihole.group_batch_delete` | Delete multiple groups at once |
| **DNS** | `wzzrd.pihole.dns_record` | Static A/AAAA records |
| | `wzzrd.pihole.cname_record` | CNAME alias records |
| | `wzzrd.pihole.dhcp_reservation` | Static DHCP leases |
| **Blocking** | `wzzrd.pihole.domain` | Per-domain allow/deny rules (exact or regex) |
| | `wzzrd.pihole.adlist` | Block and allow adlists |

## Requirements

- Python 3.8+
- Ansible 2.16.12+
- Python `requests` library
- Pi-hole v6.0+

Tested with:

- Python 3.13.3
- Ansible 2.16.13
- Pi-hole Docker Tag 2025.04.0 (Core v6.0.6 / FTL v6.1 / Web v6.1)

## Installation

From Ansible Galaxy:

```bash
ansible-galaxy collection install wzzrd.pihole
```

From source:

```bash
git clone https://git.wzzrd.com/wzzrd/ansible-collection-pihole.git
cd ansible-collection-pihole
ansible-galaxy collection build
ansible-galaxy collection install wzzrd-pihole-*.tar.gz
```

## Authentication

All modules except `auth` require a session ID (`sid`). Obtain one with the `auth` module and store it with `set_fact`:

```yaml
- name: Authenticate with Pi-hole
  wzzrd.pihole.auth:
    pihole: "https://pihole.acme.lab"
    password: "{{ pihole_password }}"
  register: auth_result

- name: Store session ID
  set_fact:
    pihole_sid: "{{ auth_result.sid }}"
```

Store your password in Ansible Vault:

```yaml
pihole_password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  ...encrypted value...
```

---

## Modules

### `wzzrd.pihole.auth`

Authenticate with the Pi-hole API and return a session ID.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `password` | yes | — | Pi-hole web password |

**Returns:** `sid` — session ID string for use in subsequent tasks.

```yaml
- name: Authenticate
  wzzrd.pihole.auth:
    pihole: "https://pihole.acme.lab"
    password: "{{ pihole_password }}"
  register: auth_result

- set_fact:
    pihole_sid: "{{ auth_result.sid }}"
```

---

### `wzzrd.pihole.action`

Trigger system-level Pi-hole actions.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `action` | yes | — | `gravity`, `restartdns`, `flush-logs`, `flush-arp` |

```yaml
- name: Update gravity
  wzzrd.pihole.action:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    action: gravity

- name: Restart DNS
  wzzrd.pihole.action:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    action: restartdns
```

---

### `wzzrd.pihole.blocking`

Enable or disable Pi-hole DNS blocking.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `enabled` | yes | — | `true` to enable blocking, `false` to disable |
| `timer` | no | — | Seconds until blocking is automatically re-enabled (disable only) |

```yaml
- name: Disable blocking for 5 minutes
  wzzrd.pihole.blocking:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    enabled: false
    timer: 300

- name: Re-enable blocking
  wzzrd.pihole.blocking:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    enabled: true
```

---

### `wzzrd.pihole.group`

Create, modify, or delete Pi-hole groups. Groups let you apply different adlists and domain rules to different sets of clients.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `name` | yes | — | Group name |
| `new_name` | no | — | Rename the group to this name |
| `comment` | no | — | Description |
| `enabled` | no | `true` | Whether the group is active |
| `state` | no | `present` | `present` or `absent` |

```yaml
- name: Create groups
  wzzrd.pihole.group:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    name: "{{ item.name }}"
    comment: "{{ item.comment }}"
    state: present
  loop:
    - { name: IoT, comment: "IoT devices" }
    - { name: Kids, comment: "Kids' devices" }
    - { name: Work, comment: "Work devices" }
```

---

### `wzzrd.pihole.client`

Manage Pi-hole clients. Clients can be identified by IPv4, IPv6, MAC address, hostname, or CIDR range.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `client` | yes | — | Client identifier (IP, MAC, hostname, CIDR) |
| `comment` | no | — | Description |
| `groups` | no | — | List of group names to assign this client to |
| `state` | no | `present` | `present` or `absent` |

```yaml
- name: Configure clients
  wzzrd.pihole.client:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    client: "{{ item.client }}"
    comment: "{{ item.comment }}"
    groups: "{{ item.groups }}"
    state: present
  loop:
    - { client: "192.168.88.20", comment: "NAS", groups: [Work] }
    - { client: "de:ad:be:ef:00:03", comment: "Laptop", groups: [Work] }
    - { client: "192.168.88.50", comment: "RPi Camera", groups: [IoT] }
```

---

### `wzzrd.pihole.group_batch_delete`

Delete multiple groups in a single operation.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `names` | yes | — | List of group names to delete |

```yaml
- name: Remove temporary groups
  wzzrd.pihole.group_batch_delete:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    names:
      - Temp_Group
      - Old_IoT
```

---

### `wzzrd.pihole.dns_record`

Manage static DNS records (A and AAAA).

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `ip` | yes | — | IP address (IPv4 or IPv6) |
| `name` | yes | — | Hostname |
| `unique` | no | `true` | Remove all other IPs for this hostname before adding |
| `state` | no | `present` | `present` or `absent` |

> **AAAA records:** When a hostname already has an A record, set `unique: false` on the AAAA record so both coexist. `unique: true` (the default) only removes IPs within the same address family.

```yaml
- name: Add A records
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    ip: "{{ item.ip }}"
    name: "{{ item.name }}"
    state: present
  loop:
    - { ip: "192.168.88.10", name: "nas01.acme.lab" }
    - { ip: "192.168.88.20", name: "workstation.acme.lab" }

- name: Add AAAA record alongside existing A record
  wzzrd.pihole.dns_record:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    ip: "fd00:dead:beef::10"
    name: "nas01.acme.lab"
    unique: false
    state: present
```

---

### `wzzrd.pihole.cname_record`

Manage CNAME alias records.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `cname` | yes | — | Alias hostname |
| `name` | yes | — | Target hostname |
| `state` | no | `present` | `present` or `absent` |

```yaml
- name: Add CNAME records
  wzzrd.pihole.cname_record:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    cname: "{{ item.cname }}"
    name: "{{ item.name }}"
    state: present
  loop:
    - { cname: "storage.acme.lab", name: "nas01.acme.lab" }
    - { cname: "files.acme.lab", name: "nas01.acme.lab" }
```

---

### `wzzrd.pihole.dhcp_reservation`

Manage static DHCP leases.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `hw` | yes | — | MAC address |
| `ip` | yes | — | Reserved IP address |
| `name` | yes | — | Hostname for the reservation |
| `state` | no | `present` | `present` or `absent` |

```yaml
- name: Create DHCP reservations
  wzzrd.pihole.dhcp_reservation:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    hw: "{{ item.hw }}"
    ip: "{{ item.ip }}"
    name: "{{ item.name }}"
    state: present
  loop:
    - { hw: "de:ad:be:ef:00:01", ip: "192.168.88.10", name: "nas01" }
    - { hw: "de:ad:be:ef:00:02", ip: "192.168.88.20", name: "workstation" }
    - { hw: "de:ad:be:ef:00:03", ip: "192.168.88.30", name: "laptop" }
```

---

### `wzzrd.pihole.domain`

Manage individual domain allow/deny rules.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `domain` | yes | — | Domain or regex pattern |
| `type` | yes | — | `allow` or `deny` |
| `kind` | yes | — | `exact` or `regex` |
| `comment` | no | — | Description |
| `groups` | no | — | List of group names |
| `enabled` | no | `true` | Whether the rule is active |
| `state` | no | `present` | `present` or `absent` |

```yaml
- name: Block specific domains
  wzzrd.pihole.domain:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    domain: "{{ item.domain }}"
    type: deny
    kind: "{{ item.kind }}"
    comment: "{{ item.comment }}"
    state: present
  loop:
    - { domain: "ads.example.com", kind: exact, comment: "Known ad server" }
    - { domain: "tracking.example.net", kind: exact, comment: "Tracking domain" }
    - { domain: "^ads\\..*\\.example\\.com$", kind: regex, comment: "All ad subdomains" }

- name: Allow a domain that is blocked by an adlist
  wzzrd.pihole.domain:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    domain: "legit.example.com"
    type: allow
    kind: exact
    state: present
```

---

### `wzzrd.pihole.adlist`

Manage block and allow adlists.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `pihole` | yes | — | URL of the Pi-hole instance |
| `sid` | yes | — | Session ID from `auth` |
| `address` | yes | — | URL of the adlist |
| `type` | no | `block` | `block` or `allow` |
| `comment` | no | — | Description |
| `groups` | no | — | List of group names |
| `enabled` | no | `true` | Whether the adlist is active |
| `state` | no | `present` | `present` or `absent` |

```yaml
- name: Add adlists
  wzzrd.pihole.adlist:
    pihole: "https://pihole.acme.lab"
    sid: "{{ pihole_sid }}"
    address: "{{ item.address }}"
    comment: "{{ item.comment }}"
    groups: [Default]
    enabled: true
    state: present
  loop:
    - address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
      comment: "StevenBlack unified hosts"
    - address: "https://s3.amazonaws.com/lists.disconnect.me/simple_tracking.txt"
      comment: "Disconnect.me tracking list"
```

---

## Complete example playbook

```yaml
---
- name: Configure acme.lab Pi-hole
  hosts: pihole_servers
  gather_facts: false
  vars:
    pihole_url: "https://pihole.acme.lab"
    pihole_password: !vault |
      $ANSIBLE_VAULT;1.1;AES256
      ...encrypted value...

  tasks:
    # ── Authentication ────────────────────────────────────────────────────
    - name: Authenticate with Pi-hole
      wzzrd.pihole.auth:
        pihole: "{{ pihole_url }}"
        password: "{{ pihole_password }}"
      register: auth_result

    - set_fact:
        pihole_sid: "{{ auth_result.sid }}"

    # ── Groups ────────────────────────────────────────────────────────────
    - name: Create groups
      wzzrd.pihole.group:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        name: "{{ item.name }}"
        comment: "{{ item.comment }}"
        state: present
      loop:
        - { name: IoT, comment: "IoT devices" }
        - { name: Work, comment: "Work devices" }

    # ── Clients ───────────────────────────────────────────────────────────
    - name: Configure clients
      wzzrd.pihole.client:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        client: "{{ item.client }}"
        comment: "{{ item.comment }}"
        groups: "{{ item.groups }}"
        state: present
      loop:
        - { client: "192.168.88.20", comment: "NAS",       groups: [Work] }
        - { client: "192.168.88.50", comment: "RPi Camera", groups: [IoT] }

    # ── DNS records ───────────────────────────────────────────────────────
    - name: Add A records
      wzzrd.pihole.dns_record:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        ip: "{{ item.ip }}"
        name: "{{ item.name }}"
        state: present
      loop:
        - { ip: "192.168.88.10", name: "nas01.acme.lab" }
        - { ip: "192.168.88.20", name: "workstation.acme.lab" }
        - { ip: "192.168.88.30", name: "laptop.acme.lab" }

    - name: Add AAAA record (dual-stack NAS)
      wzzrd.pihole.dns_record:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        ip: "fd00:dead:beef::10"
        name: "nas01.acme.lab"
        unique: false
        state: present

    - name: Add CNAME records
      wzzrd.pihole.cname_record:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        cname: "{{ item.cname }}"
        name: "{{ item.name }}"
        state: present
      loop:
        - { cname: "storage.acme.lab", name: "nas01.acme.lab" }
        - { cname: "files.acme.lab",   name: "nas01.acme.lab" }

    # ── DHCP reservations ─────────────────────────────────────────────────
    - name: Create DHCP reservations
      wzzrd.pihole.dhcp_reservation:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        hw: "{{ item.hw }}"
        ip: "{{ item.ip }}"
        name: "{{ item.name }}"
        state: present
      loop:
        - { hw: "de:ad:be:ef:00:01", ip: "192.168.88.10", name: "nas01" }
        - { hw: "de:ad:be:ef:00:02", ip: "192.168.88.20", name: "workstation" }

    # ── Adlists ───────────────────────────────────────────────────────────
    - name: Add block adlists
      wzzrd.pihole.adlist:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        address: "{{ item.address }}"
        comment: "{{ item.comment }}"
        groups: [Default]
        state: present
      loop:
        - address: "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
          comment: "StevenBlack unified hosts"

    # ── Individual domain rules ───────────────────────────────────────────
    - name: Block ad domains
      wzzrd.pihole.domain:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        domain: "{{ item.domain }}"
        type: deny
        kind: "{{ item.kind }}"
        state: present
      loop:
        - { domain: "ads.example.com", kind: exact }
        - { domain: "^ads\\..*\\.example\\.com$", kind: regex }

    # ── Apply changes ─────────────────────────────────────────────────────
    - name: Update gravity
      wzzrd.pihole.action:
        pihole: "{{ pihole_url }}"
        sid: "{{ pihole_sid }}"
        action: gravity
```

---

## Error handling

Modules raise exceptions from the `api_errors` hierarchy:

| Exception | Cause |
|---|---|
| `PiholeAuthError` | Authentication failed (wrong password, expired session) |
| `PiholeNotFoundError` | Resource not found |
| `PiholeValidationError` | Invalid parameter values |
| `PiholeConnectionError` | Network error or Pi-hole unreachable |
| `PiholeApiError` | Other API-level errors |

All exceptions are subclasses of `PiholeError`. When a module fails, Ansible reports the exception message, which includes the HTTP status code where applicable.

## Session management

Session IDs may expire after a period of inactivity. In long-running playbooks, re-authenticate periodically if you encounter authentication errors mid-run.

## Contributing

This collection is developed on [Gitea](https://git.wzzrd.com/wzzrd/ansible-collection-pihole). The [GitHub repository](https://github.com/wzzrd/ansible-collection-pihole) is a read-only mirror — pull requests opened there will be applied manually upstream. To contribute, open an issue or pull request on Gitea.

## License

GPL-2.0-or-later

## Author

Maxim Burgerhout <maxim@wzzrd.com>
