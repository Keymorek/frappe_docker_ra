from __future__ import annotations

import copy
import importlib
import sys
from datetime import date, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


APP_ROOT = Path(__file__).resolve().parents[1]
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
        return _clone(self.sql_result)

    def set_value(self, *args, **kwargs):
        self.set_value_calls.append((*args, kwargs))


class FakeMeta:
    def __init__(self, fields: set[str] | None = None) -> None:
        self._fields = set(fields or [])

    def has_field(self, fieldname: str) -> bool:
        return fieldname in self._fields


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


@pytest.fixture
def frappe_env(monkeypatch):
    fake_frappe = ModuleType("frappe")
    fake_utils = ModuleType("frappe.utils")
    fake_model = ModuleType("frappe.model")
    fake_naming = ModuleType("frappe.model.naming")
    fake_db = FakeDB()
    env = SimpleNamespace()

    env.db = fake_db
    env.FrappeThrow = FrappeThrow
    env.get_all_handler = lambda *args, **kwargs: []
    env.get_cached_doc_handler = lambda *args, **kwargs: None
    env.get_doc_handler = lambda *args, **kwargs: None
    env.meta_fields = {}

    def throw(message):
        raise FrappeThrow(str(message))

    def get_all(*args, **kwargs):
        return _clone(env.get_all_handler(*args, **kwargs))

    def get_cached_doc(*args, **kwargs):
        return env.get_cached_doc_handler(*args, **kwargs)

    def get_doc(*args, **kwargs):
        return env.get_doc_handler(*args, **kwargs)

    def get_meta(doctype):
        return FakeMeta(env.meta_fields.get(doctype, set()))

    fake_frappe._ = lambda message: message
    fake_frappe.bold = lambda value: str(value)
    fake_frappe.throw = throw
    fake_frappe.db = fake_db
    fake_frappe.session = SimpleNamespace(user="unit.tester@example.com")
    fake_frappe.get_all = get_all
    fake_frappe.get_cached_doc = get_cached_doc
    fake_frappe.get_doc = get_doc
    fake_frappe.get_meta = get_meta
    fake_frappe.whitelist = _whitelist

    fake_utils.cint = _cint
    fake_utils.flt = _flt
    fake_utils.nowdate = lambda: "2026-03-07"
    fake_utils.now_datetime = lambda: datetime(2026, 3, 7, 12, 0, 0)
    fake_utils.getdate = _getdate
    fake_utils.get_datetime = _get_datetime

    fake_naming.make_autoname = lambda pattern: pattern.replace("####", "0001")

    monkeypatch.setitem(sys.modules, "frappe", fake_frappe)
    monkeypatch.setitem(sys.modules, "frappe.utils", fake_utils)
    monkeypatch.setitem(sys.modules, "frappe.model", fake_model)
    monkeypatch.setitem(sys.modules, "frappe.model.naming", fake_naming)

    def load_module(module_name: str):
        for name in list(sys.modules):
            if name == "fashion_erp" or name.startswith("fashion_erp."):
                sys.modules.pop(name, None)
        return importlib.import_module(module_name)

    env.load_module = load_module
    return env
