# CLAUDE.md — wzzrd.pihole developer guide

## Project overview

`wzzrd.pihole` is an Ansible collection of modules for managing Pi-hole v6 instances through their REST API. It covers authentication, groups, clients, static DNS (A/AAAA/CNAME), DHCP reservations, adlists, and individual domain rules.

The Pi-hole v6 API is a break from v5: all management happens via `/api/` endpoints (JSON, not form-encoded), authentication returns a session token, and configuration is stored under a unified `/api/config` tree.

---

## Architecture

### Module layout

Each functional area has two files:

```
plugins/modules/<resource>.py          # Ansible module: argument_spec, AnsibleModule, thin wrapper
plugins/module_utils/<resource>.py     # Business logic: API calls, idempotence checks, return values
```

The module itself just defines argument_spec and delegates to a `run_module(module)` function in the corresponding util. This keeps the testable logic in `module_utils/` and the Ansible scaffolding in `modules/`.

### `api_client.py`

Central HTTP client (`PiholeClient`). All requests go through this class.

- **Base URL** set at construction time.
- **Auth header:** `sid: <value>` — sent on every authenticated request (not a cookie, not `X-FTL-SID`).
- **Self-signed cert warnings** are suppressed via `urllib3.disable_warnings`.
- Methods: `get(path)`, `post(path, data)`, `put(path, data)`, `delete(path)`.

### `api_errors.py`

Exception hierarchy:

```
PiholeError (base)
├── PiholeApiError
├── PiholeAuthError
├── PiholeNotFoundError
├── PiholeValidationError
└── PiholeConnectionError
```

Raise the most specific subclass. Modules catch these and call `module.fail_json(msg=str(e))`.

### Per-resource utils

| File | Manages |
|---|---|
| `auth.py` | POST /api/auth, returns sid |
| `action.py` | POST /api/action/{action} |
| `blocking.py` | GET/POST /api/blocking |
| `groups.py` | CRUD for groups |
| `client.py` | CRUD for clients |
| `dns.py` | Static DNS hosts (A/AAAA) |
| `cname.py` | CNAME records |
| `dhcp.py` | DHCP reservations |
| `domain.py` | Per-domain allow/deny rules |
| `adlist.py` | Adlists (block/allow) |

---

## Authentication

```
POST /api/auth
Body: {"password": "<pihole-web-password>"}
Response: {"session": {"sid": "<session-id>", ...}}
```

All subsequent requests include the header `sid: <session-id>`.

Session IDs can expire. In Molecule verify tasks, add retries (see below).

---

## Key API endpoints (Pi-hole v6)

| Resource | Endpoint |
|---|---|
| Auth | `POST /api/auth` |
| Static DNS hosts | `GET/POST/DELETE /api/config/dns/hosts` |
| CNAME records | `GET/POST/DELETE /api/config/dns/cnameRecords` |
| DHCP reservations | `GET/POST/DELETE /api/config/dhcp/hosts` |
| Groups | `GET/POST/PUT/DELETE /api/groups` |
| Clients | `GET/POST/PUT/DELETE /api/clients` |
| Adlists | `GET/POST/PUT/DELETE /api/lists` |
| Domains | `GET/POST/PUT/DELETE /api/domains/{type}/{kind}/{domain}` |
| Blocking | `GET/POST /api/blocking` |
| Actions | `POST /api/action/{gravity,restartdns,...}` |
| Config (bulk) | `GET/PUT /api/config` |

Static DNS response format: `json.config.dns.hosts` → list of `"ip name"` strings.
CNAME response format: `json.config.dns.cnameRecords` → list of `"alias,target"` strings.

**Note:** Pi-hole v5 endpoints (`/api/customdns`, `/api/customcname`) do not exist in v6.

---

## Testing

### Unit tests

```bash
pip install -r tests/requirements.txt
pytest tests/unit/ -v
```

`pytest.ini` is at the **repo root** with `testpaths = tests`. This tells pytest to discover tests anywhere under `tests/`, which covers all 10 test files in `tests/unit/module_utils/`. (Contrast with the sibling `wzzrd.ghdl` collection, where `pytest.ini` lives inside `tests/unit/` and uses `testpaths = .` — that works because ghdl has a single focused test directory.)

### Black formatting

```bash
black --check plugins/ tests/
```

Or to auto-fix:

```bash
black plugins/ tests/
```

### Molecule integration tests

```bash
# Install the collection first (required — modules are loaded from the installed path)
ansible-galaxy collection install . --upgrade

# Run a scenario
molecule test -s dns_dhcp
molecule test -s blocklists

# Test against a specific Pi-hole version
PIHOLE_VERSION=2024.07.0 molecule test -s dns_dhcp
```

---

## Module development guide

To add a new module (e.g., `wzzrd.pihole.teleporter`):

1. **Create the util** `plugins/module_utils/teleporter.py` with a `run_module(module)` function and any helper functions. Import `PiholeClient` from `api_client` and raise `PiholeError` subclasses on failure.

2. **Create the module** `plugins/modules/teleporter.py`:
   - Define `argument_spec`
   - Instantiate `AnsibleModule`
   - Call `run_module(module)` from `module_utils.teleporter`

3. **Register in runtime.yml** if the module needs to be part of an action group (check `meta/runtime.yml` — most modules are listed under `action_groups.pihole`).

4. **Write unit tests** in `tests/unit/module_utils/test_teleporter.py`. Mock `PiholeClient` and test the logic in the util.

---

## Critical patterns and pitfalls

### AAAA records and `unique`

`dns_record` has a `unique` parameter (default `true`) that removes all existing IPs for a hostname before adding the new one. When adding an AAAA record to a hostname that already has an A record, set `unique: false` — otherwise the A record is deleted. The conflict detection is address-family-aware (A and AAAA do not conflict with each other), but `unique: false` is still required to prevent deletion.

```yaml
- wzzrd.pihole.dns_record:
    ip: "fd00:dead:beef::10"
    name: "nas01.acme.lab"
    unique: false   # ← required when A record already exists
    state: present
```

### Molecule idempotence step

Molecule's built-in `idempotence` step in `test_sequence` **always re-runs `converge.yml`**. The `provisioner.playbooks.idempotence` key in `molecule.yml` is silently ignored — it does not redirect the step to a different playbook. If converge is intentionally non-idempotent (e.g., gravity update), remove `idempotence` from `test_sequence`. Custom idempotency checks belong in `verify.yml` using check mode + assert.

### Auth retry in verify.yml

After converge makes many API writes, Pi-hole's FTL process may briefly reload, causing the first auth attempt in verify to fail. Add retries:

```yaml
- name: Authenticate
  wzzrd.pihole.auth:
    pihole: "{{ pihole_url }}"
    password: "{{ pihole_password }}"
  register: auth_result
  retries: 5
  delay: 5
  until: auth_result is not failed
```

### DHCP tests require DHCP enabled

Pi-hole's DHCP server is disabled by default. Before testing DHCP reservations, enable it in `prepare.yml` via `PUT /api/config` with the `sid` header:

```yaml
- name: Enable DHCP
  uri:
    url: "{{ pihole_url }}/api/config"
    method: PUT
    headers:
      sid: "{{ pihole_sid }}"
    body_format: json
    body:
      dhcp:
        active: true
        ...
```

### Container hostname collision

Pi-hole containers set a DNS entry for their own hostname. When testing, use hostnames that do not collide with the container name.

---

## Molecule scenarios

### `dns_dhcp` (port 8080)

Tests: DHCP reservations, A records (IPv4, `unique: true`), AAAA records (IPv6, `unique: false`), CNAME records.

`prepare.yml` enables DHCP via the API before converge runs.

### `blocklists` (port 8081)

Tests: groups, clients, adlists (block and allow types), individual domain rules (deny exact, deny regex, allow exact).

---

## Building

```bash
ansible-galaxy collection build
# Produces wzzrd-pihole-<version>.tar.gz

ansible-galaxy collection install wzzrd-pihole-*.tar.gz --upgrade
```
