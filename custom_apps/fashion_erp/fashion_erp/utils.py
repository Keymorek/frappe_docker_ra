from __future__ import annotations

import frappe


def has_app_permission() -> bool:
    user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return False

    has_permission = getattr(frappe, "has_permission", None)
    if callable(has_permission):
        try:
            if has_permission("Workspace", "read", "Fashion ERP"):
                return True
        except TypeError:
            # Older Frappe versions may not accept the same signature.
            pass

    get_roles = getattr(frappe, "get_roles", None)
    if callable(get_roles):
        roles = set(get_roles(user) or [])
        if roles.intersection({"System Manager", "Stock Manager", "Item Manager"}):
            return True

    return user == "Administrator"
