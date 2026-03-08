from __future__ import annotations

import unittest
from types import SimpleNamespace

from helpers import build_frappe_env


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_has_app_permission_allows_workspace_reader(self):
        self.env.frappe.session = SimpleNamespace(user="tester@example.com")
        self.env.frappe.has_permission = lambda doctype, ptype, doc=None: (
            doctype,
            ptype,
            doc,
        ) == ("Workspace", "read", "Fashion ERP")

        module = self.env.load_module("fashion_erp.utils")

        self.assertTrue(module.has_app_permission())

    def test_has_app_permission_falls_back_to_roles(self):
        self.env.frappe.session = SimpleNamespace(user="item.manager@example.com")
        self.env.frappe.has_permission = lambda *args, **kwargs: False
        self.env.frappe.get_roles = lambda user=None: ["Item Manager"]

        module = self.env.load_module("fashion_erp.utils")

        self.assertTrue(module.has_app_permission())

    def test_has_app_permission_rejects_guest(self):
        self.env.frappe.session = SimpleNamespace(user="Guest")
        self.env.frappe.has_permission = lambda *args, **kwargs: True

        module = self.env.load_module("fashion_erp.utils")

        self.assertFalse(module.has_app_permission())


if __name__ == "__main__":
    unittest.main()
