from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from app_structure_validation import validate_app_structure


class TestAppStructureValidation(unittest.TestCase):
    def test_repo_has_no_install_structure_issues(self):
        issues = validate_app_structure()
        self.assertEqual([], issues, "\n".join(issue.format() for issue in issues))

    def test_validator_reports_missing_doctype_controller(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            container_root = Path(tmpdir)
            app_root = container_root / "fashion_erp"
            (app_root / "style" / "doctype" / "craft_sheet_log").mkdir(parents=True)
            (app_root / "style" / "__init__.py").write_text("", encoding="utf-8")
            (app_root / "modules.txt").write_text("Style\n", encoding="utf-8")
            (app_root / "style" / "doctype" / "craft_sheet_log" / "__init__.py").write_text("", encoding="utf-8")
            (app_root / "style" / "doctype" / "craft_sheet_log" / "craft_sheet_log.json").write_text(
                json.dumps({"name": "Craft Sheet Log", "module": "Style"}),
                encoding="utf-8",
            )

            issues = validate_app_structure(container_root)

            self.assertTrue(any(issue.code == "missing-doctype-controller" for issue in issues))

    def test_validator_reports_reserved_module_package_collision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            container_root = Path(tmpdir)
            app_root = container_root / "fashion_erp"
            (app_root / "stock").mkdir(parents=True)
            (app_root / "stock" / "__init__.py").write_text("", encoding="utf-8")
            (app_root / "modules.txt").write_text("Stock\n", encoding="utf-8")

            issues = validate_app_structure(container_root)

            self.assertTrue(any(issue.code == "reserved-module-package" for issue in issues))

    def test_validator_reports_too_long_search_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            container_root = Path(tmpdir)
            app_root = container_root / "fashion_erp"
            folder = app_root / "style" / "doctype" / "style_category_template"
            folder.mkdir(parents=True)
            (app_root / "style" / "__init__.py").write_text("", encoding="utf-8")
            (app_root / "modules.txt").write_text("Style\n", encoding="utf-8")
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "style_category_template.py").write_text("from frappe.model.document import Document\n", encoding="utf-8")
            (folder / "style_category_template.json").write_text(
                json.dumps(
                    {
                        "name": "Style Category Template",
                        "module": "Style",
                        "search_fields": ",".join(f"field_{index:02d}" for index in range(20)),
                    }
                ),
                encoding="utf-8",
            )

            issues = validate_app_structure(container_root)

            self.assertTrue(any(issue.code == "search-fields-too-long" for issue in issues))


if __name__ == "__main__":
    unittest.main()
