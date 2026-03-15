# Changelog

## v1.0.3 (2026-03-15)

### Maintenance
- Add copyright headers to all module and module_utils files
- Remove executable bit and shebangs from plugin files
- Remove unused imports across modules and module_utils
- Refactor `api_client.py` for clarity and test coverage
- Expand unit tests for `api_client`
- Add Makefile targets for common development tasks
- Ignore `tests/output/` in `.gitignore`

## v1.0.2 (2026-02-24)

### Testing
- Molecule updates: add cleanup
- Molecule update: remove removals from converge (dns_dhcp)
- Add collection level requirements to shut up molecule
- Add --report and --command-borders to molecule command in ci

## v1.0.1 (2026-02-24)

### Improvements

- Add black code-formatting checks to CI
- Add CLAUDE.md with developer guidance
- Improve README with realistic examples and contributing guide

## v1.0.0 (2026-02-24)

### Initial release

- Modules for managing Pi-hole DNS records, CNAME records, DHCP reservations, adlists, domains, groups, clients, and blocking status via the Pi-hole v6 API
