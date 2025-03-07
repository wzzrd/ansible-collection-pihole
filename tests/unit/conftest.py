"""
Set up the ansible_collections namespace so that module_utils can be imported
in a plain pytest run without a full Ansible installation.

Modules are loaded from the actual source tree using importlib, registered
under their canonical ansible_collections.wzzrd.pihole.* names, and remain
available for the entire test session.
"""

import importlib.util
import sys
import types
from pathlib import Path

COLLECTION_ROOT = Path(__file__).parent.parent.parent
MODULE_UTILS_DIR = COLLECTION_ROOT / "plugins" / "module_utils"


def _ensure_namespace(dotted_name: str) -> types.ModuleType:
    """Return (or create) a namespace package for *dotted_name*."""
    if dotted_name in sys.modules:
        return sys.modules[dotted_name]
    mod = types.ModuleType(dotted_name)
    mod.__path__ = []  # mark as package
    mod.__package__ = dotted_name
    sys.modules[dotted_name] = mod
    return mod


def _load_module_util(short_name: str) -> types.ModuleType:
    """Load a module_utils file and register it under the collection namespace."""
    full_name = f"ansible_collections.wzzrd.pihole.plugins.module_utils.{short_name}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    file_path = MODULE_UTILS_DIR / f"{short_name}.py"
    spec = importlib.util.spec_from_file_location(full_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "ansible_collections.wzzrd.pihole.plugins.module_utils"
    # Register before exec so that intra-package imports resolve correctly.
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Build the namespace hierarchy.
for _ns in [
    "ansible_collections",
    "ansible_collections.wzzrd",
    "ansible_collections.wzzrd.pihole",
    "ansible_collections.wzzrd.pihole.plugins",
    "ansible_collections.wzzrd.pihole.plugins.module_utils",
]:
    _ensure_namespace(_ns)

# Load modules in dependency order (api_errors first, no deps).
for _mod in [
    "api_errors",
    "api_client",
    "auth",
    "dns",
    "cname",
    "dhcp",
    "groups",
    "adlist",
    "domain",
    "client",
    "blocking",
    "action",
]:
    _load_module_util(_mod)
