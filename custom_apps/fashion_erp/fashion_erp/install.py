import frappe

from fashion_erp.patches.v1_0.seed_phase1_master_data import execute


def after_install() -> None:
    execute()
    frappe.clear_cache()


def after_migrate() -> None:
    frappe.clear_cache()
