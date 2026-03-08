from __future__ import annotations

import copy
import importlib
import sys
from datetime import date, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


class AttrDict(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


class FrappeThrow(Exception):
    pass


class FakeDB:
    def __init__(self) -> None:
        self.exists_map: dict[tuple[str, str], bool] = {}
        self.value_map: dict[tuple[object, ...], object] = {}
        self.sql_result: list[dict[str, object]] = []
        self.sql_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.set_value_calls: list[tuple[object, ...]] = []

    def exists(self, doctype: str, name: str) -> bool:
        return self.exists_map.get((doctype, name), False)

    def get_value(self, doctype: str, name: str, fieldname, as_dict: bool = False):
        frozen_field = _freeze_field(fieldname)
        keys = [
            (doctype, name, frozen_field, as_dict),
            (doctype, name, frozen_field),
        ]
        for key in keys:
            if key in self.value_map:
                return _clone(self.value_map[key])
        return None

    def sql(self, *_args, **_kwargs):
        self.sql_calls.append((_args, _kwargs))
        return _clone(self.sql_result)

    def set_value(self, *args, **kwargs):
        self.set_value_calls.append((*args, kwargs))


class FakeMeta:
    def __init__(self, fields: set[str] | None = None) -> None:
        self._fields = set(fields or [])

    def has_field(self, fieldname: str) -> bool:
        return fieldname in self._fields


class FakeDoc(SimpleNamespace):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not hasattr(self, "flags"):
            self.flags = SimpleNamespace()
        if not hasattr(self, "logs"):
            self.logs = []
        self.save_calls: list[dict[str, object]] = []
        self.insert_calls: list[dict[str, object]] = []

    def append(self, fieldname: str, value):
        rows = list(getattr(self, fieldname, []) or [])
        row = AttrDict(copy.deepcopy(value)) if isinstance(value, dict) else value
        rows.append(row)
        setattr(self, fieldname, rows)
        return row

    def save(self, **kwargs):
        self.save_calls.append(kwargs)
        return self

    def insert(self, **kwargs):
        self.insert_calls.append(kwargs)
        return self

    def get(self, fieldname: str, default=None):
        return getattr(self, fieldname, default)

    def set(self, fieldname: str, value):
        setattr(self, fieldname, value)


def _freeze_field(fieldname):
    if isinstance(fieldname, list):
        return tuple(fieldname)
    if isinstance(fieldname, tuple):
        return fieldname
    return fieldname


def _clone(value):
    if isinstance(value, dict):
        return AttrDict(copy.deepcopy(value))
    if isinstance(value, list):
        return [_clone(row) for row in value]
    return copy.deepcopy(value)


def _cint(value) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _flt(value) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _getdate(value=None):
    if value in (None, ""):
        return date(2026, 3, 7)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _get_datetime(value=None):
    if value in (None, ""):
        return datetime(2026, 3, 7, 12, 0, 0)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return datetime.fromisoformat(str(value).replace(" ", "T"))


def _whitelist(*args, **kwargs):
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]

    def decorator(fn):
        return fn

    return decorator


class FrappeEnv:
    def __init__(self) -> None:
        self.db = FakeDB()
        self.FrappeThrow = FrappeThrow
        self.get_all_handler = lambda *args, **kwargs: []
        self.get_cached_doc_handler = lambda *args, **kwargs: None
        self.get_doc_handler = lambda *args, **kwargs: None
        self.meta_fields: dict[str, set[str]] = {}
        self._saved_modules: dict[str, ModuleType | None] = {}
        self._install_modules()

    def _install_modules(self) -> None:
        self.frappe = ModuleType("frappe")
        self.frappe_utils = ModuleType("frappe.utils")
        self.frappe_model = ModuleType("frappe.model")
        self.frappe_naming = ModuleType("frappe.model.naming")

        def throw(message):
            raise FrappeThrow(str(message))

        def get_all(*args, **kwargs):
            return _clone(self.get_all_handler(*args, **kwargs))

        def get_cached_doc(*args, **kwargs):
            return self.get_cached_doc_handler(*args, **kwargs)

        def get_doc(*args, **kwargs):
            return self.get_doc_handler(*args, **kwargs)

        def get_meta(doctype):
            return FakeMeta(self.meta_fields.get(doctype, set()))

        self.frappe._ = lambda message: message
        self.frappe.bold = lambda value: str(value)
        self.frappe.throw = throw
        self.frappe.db = self.db
        self.frappe.session = SimpleNamespace(user="unit.tester@example.com")
        self.frappe.get_all = get_all
        self.frappe.get_cached_doc = get_cached_doc
        self.frappe.get_doc = get_doc
        self.frappe.get_meta = get_meta
        self.frappe.whitelist = _whitelist

        self.frappe_utils.cint = _cint
        self.frappe_utils.flt = _flt
        self.frappe_utils.nowdate = lambda: "2026-03-07"
        self.frappe_utils.now_datetime = lambda: datetime(2026, 3, 7, 12, 0, 0)
        self.frappe_utils.getdate = _getdate
        self.frappe_utils.get_datetime = _get_datetime

        self.frappe_naming.make_autoname = lambda pattern: pattern.replace("####", "0001")

    def install(self) -> None:
        replacements = {
            "frappe": self.frappe,
            "frappe.utils": self.frappe_utils,
            "frappe.model": self.frappe_model,
            "frappe.model.naming": self.frappe_naming,
        }
        for name, module in replacements.items():
            self._saved_modules[name] = sys.modules.get(name)
            sys.modules[name] = module

    def cleanup(self) -> None:
        for name in list(sys.modules):
            if name == "fashion_erp" or name.startswith("fashion_erp."):
                sys.modules.pop(name, None)

        for name, module in self._saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        self._saved_modules.clear()

    def load_module(self, module_name: str):
        for name in list(sys.modules):
            if name == "fashion_erp" or name.startswith("fashion_erp."):
                sys.modules.pop(name, None)
        return importlib.import_module(module_name)


def build_frappe_env() -> FrappeEnv:
    env = FrappeEnv()
    env.install()
    return env
