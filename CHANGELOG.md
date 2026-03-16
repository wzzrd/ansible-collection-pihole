# Changelog

## v1.0.4 (2026-03-16)

### Bug Fixes
- Fix silent fallback GET in `update_client` that masked errors
- Remove redundant `type` field from `add_adlist()` JSON body
- Replace hardcoded `%20` in `dns.py` with `urllib.parse.quote()`
- Fix stale entry in `runtime.yml` and various doc issues
- Fix two code quality issues in `groups.py`
- Fix `dns_record` parameter description

### Improvements
- Move DNS conflict-resolution logic into `module_utils` for better testability
- Remove redundant auth code
- Add missing unit tests for module_utils
- Add lean module-layer tests
- Consolidate test helpers and fix mock specs
- Add more Molecule scenarios
- Add yamllint config for consistent line length
- Clean up minor style issues across all plugin files
- Update license fields

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
