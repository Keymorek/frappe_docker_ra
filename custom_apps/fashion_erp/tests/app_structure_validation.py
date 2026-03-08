from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


APP_CONTAINER_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = APP_CONTAINER_ROOT / "fashion_erp"
MODULES_FILE = APP_ROOT / "modules.txt"

NON_MODULE_PACKAGES = {
    "__pycache__",
    "config",
    "fixtures",
    "locale",
    "patches",
    "translations",
}

SEARCH_FIELDS_MAX_LENGTH = 140

# These package names are already occupied by standard Frappe / ERPNext modules.
RESERVED_STANDARD_MODULE_PACKAGES = {
    "accounts",
    "assets",
    "automation",
    "buying",
    "contacts",
    "core",
    "crm",
    "desk",
    "education",
    "email",
    "healthcare",
    "hr",
    "hospitality",
    "integrations",
    "maintenance",
    "manufacturing",
    "non_profit",
    "payment",
    "payments",
    "projects",
    "quality_management",
    "regional",
    "selling",
    "setup",
    "social",
    "stock",
    "subcontracting",
    "support",
    "telephony",
    "utilities",
    "website",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str | None = None

    def format(self) -> str:
        if self.path:
            return f"[{self.code}] {self.message}: {self.path}"
        return f"[{self.code}] {self.message}"


def scrub_module_name(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def load_declared_modules(app_root: Path) -> dict[str, str]:
    modules_file = app_root / "modules.txt"
    modules = [line.strip() for line in modules_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {scrub_module_name(module): module for module in modules}


def validate_app_structure(app_container_root: Path | None = None) -> list[ValidationIssue]:
    container_root = Path(app_container_root or APP_CONTAINER_ROOT)
    app_root = container_root / "fashion_erp"
    modules_file = app_root / "modules.txt"
    declared_modules = load_declared_modules(app_root)
    issues: list[ValidationIssue] = []

    for package_name, module_name in sorted(declared_modules.items()):
        package_dir = app_root / package_name
        if not package_dir.is_dir():
            issues.append(
                ValidationIssue(
                    code="missing-module-package",
                    message=f"模块 {module_name} 缺少对应的 Python 包目录 {package_name}",
                    path=package_dir.as_posix(),
                )
            )
        if package_name in RESERVED_STANDARD_MODULE_PACKAGES:
            issues.append(
                ValidationIssue(
                    code="reserved-module-package",
                    message=f"模块 {module_name} 使用了标准 Frappe/ERPNext 保留包名 {package_name}",
                    path=modules_file.as_posix(),
                )
            )

    for json_path in sorted(app_root.rglob("*.json")):
        relative = json_path.relative_to(app_root)
        parts = relative.parts
        if len(parts) < 4:
            continue

        package_name = parts[0]
        section_name = parts[1]
        if package_name in NON_MODULE_PACKAGES or section_name not in {"doctype", "report"}:
            continue

        folder = json_path.parent
        base_name = folder.name
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                ValidationIssue(
                    code="invalid-json",
                    message=f"JSON 解析失败: {exc.msg}",
                    path=json_path.as_posix(),
                )
            )
            continue
        module_name = str(data.get("module") or "").strip()

        if package_name not in declared_modules:
            issues.append(
                ValidationIssue(
                    code="undeclared-module-package",
                    message=f"目录 {package_name} 下存在 {section_name}，但 modules.txt 未声明该模块",
                    path=folder.as_posix(),
                )
            )

        if not module_name:
            issues.append(
                ValidationIssue(
                    code="missing-module-name",
                    message="JSON 缺少 module 字段",
                    path=json_path.as_posix(),
                )
            )
            continue

        if module_name not in declared_modules.values():
            issues.append(
                ValidationIssue(
                    code="unknown-module-name",
                    message=f"JSON 使用了未声明的模块 {module_name}",
                    path=json_path.as_posix(),
                )
            )
            continue

        search_fields = str(data.get("search_fields") or "").strip()
        if len(search_fields) > SEARCH_FIELDS_MAX_LENGTH:
            issues.append(
                ValidationIssue(
                    code="search-fields-too-long",
                    message=f"search_fields 长度 {len(search_fields)} 超过 Frappe Data 字段上限 {SEARCH_FIELDS_MAX_LENGTH}",
                    path=json_path.as_posix(),
                )
            )

        expected_package = scrub_module_name(module_name)
        if package_name != expected_package:
            issues.append(
                ValidationIssue(
                    code="module-package-mismatch",
                    message=f"模块 {module_name} 应位于包 {expected_package}，当前位于 {package_name}",
                    path=json_path.as_posix(),
                )
            )

        if section_name == "doctype":
            controller_path = folder / f"{base_name}.py"
            init_path = folder / "__init__.py"
            if not init_path.exists():
                issues.append(
                    ValidationIssue(
                        code="missing-doctype-init",
                        message="DocType 目录缺少 __init__.py",
                        path=folder.as_posix(),
                    )
                )
            if not controller_path.exists():
                issues.append(
                    ValidationIssue(
                        code="missing-doctype-controller",
                        message="DocType 目录缺少同名 Python 控制器文件",
                        path=folder.as_posix(),
                    )
                )

        if section_name == "report" and data.get("report_type") == "Script Report":
            backend_path = folder / f"{base_name}.py"
            frontend_path = folder / f"{base_name}.js"
            if not backend_path.exists():
                issues.append(
                    ValidationIssue(
                        code="missing-script-report-backend",
                        message="Script Report 缺少同名 Python 后端文件",
                        path=folder.as_posix(),
                    )
                )
            if not frontend_path.exists():
                issues.append(
                    ValidationIssue(
                        code="missing-script-report-frontend",
                        message="Script Report 缺少同名 JS 前端文件",
                        path=folder.as_posix(),
                    )
                )

    for package_dir in sorted(path for path in app_root.iterdir() if path.is_dir()):
        package_name = package_dir.name
        if package_name in NON_MODULE_PACKAGES or package_name.startswith("__"):
            continue
        if package_name not in declared_modules and any((package_dir / name).exists() for name in ("doctype", "report", "workspace")):
            issues.append(
                ValidationIssue(
                    code="unexpected-module-package",
                    message="存在未在 modules.txt 中声明的模块目录",
                    path=package_dir.as_posix(),
                )
            )

    return sorted(issues, key=lambda issue: (issue.code, issue.path or "", issue.message))


def main() -> int:
    issues = validate_app_structure()
    if not issues:
        print("fashion_erp static structure validation passed.")
        return 0

    print("fashion_erp static structure validation failed:")
    for issue in issues:
        print(f"- {issue.format()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
