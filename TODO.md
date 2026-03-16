# TODO — Pending improvement points

## Medium

- **Remove silent fallback API call in `update_client()` (client.py:108–112)**
  When `group_ids` is `None`, `update_client()` silently issues an extra `GET` to fetch
  the current client. The comment acknowledges it "should not happen." Side-effects
  should be explicit, not hidden fallback behavior.

## Minor

_(all items resolved)_
