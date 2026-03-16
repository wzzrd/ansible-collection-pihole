# TODO — Pending improvement points

## Medium

- **Simplify `group_names_to_ids()` deduplication (groups.py:332–338)**
  The 6-line set+list loop is the verbose form of `list(dict.fromkeys(group_ids))`.

- **Fix `delete_group()` exception re-raise losing traceback (groups.py:223–224)**
  `except PiholeNotFoundError: raise PiholeNotFoundError(...)` creates a new exception,
  dropping the original chain. Use bare `raise` or `raise ... from exc`.

- **Remove silent fallback API call in `update_client()` (client.py:108–112)**
  When `group_ids` is `None`, `update_client()` silently issues an extra `GET` to fetch
  the current client. The comment acknowledges it "should not happen." Side-effects
  should be explicit, not hidden fallback behavior.

- **Clarify `adlist.py` type parameter (adlist.py:121,131)**
  `add_adlist()` sends `"type"` in both the JSON body and as a `?type=` query parameter.
  GET/DELETE use only the query param. Determine which the API actually requires and
  remove the redundant one.

## Minor

- **Remove `str(e)` wrapping in f-strings — 89 occurrences across 20 files**
  `f"...: {str(e)}"` should be `f"...: {e}"`. F-strings call `__str__` implicitly.

- **Replace `typing.Dict/List/Optional` imports with builtins**
  All `module_utils/` files already have `from __future__ import annotations`, making
  `dict[str, Any]`, `list[str]`, and `X | None` valid. The `typing` generics are
  holdovers and can be dropped.

- **Remove trailing bare `#` comments in module `main()` functions**
  Lines like `api_client = PiholeApiClient(pihole_url, sid)  #` appear in several
  modules (`dns_record.py`, `group.py`, etc.). Leftover from removed inline notes.

- **Add missing docstring Args/Returns/Raises sections to `client.py`**
  `client.py` functions have one-liner docstrings only. Every other `module_utils/`
  file uses full structured docstrings.

- **Add `from __future__ import annotations` to `modules/*.py`**
  All `module_utils/` files have it; none of the `modules/` files do. Minor consistency
  gap.
