from frappe import _


def get_data():
    return [
        {
            "module_name": "Style",
            "color": "blue",
            "icon": "octicon octicon-tag",
            "type": "module",
            "label": _("款号主数据"),
        },
        {
            "module_name": "Channel",
            "color": "green",
            "icon": "octicon octicon-broadcast",
            "type": "module",
            "label": _("渠道管理"),
        },
        {
            "module_name": "Garment Mfg",
            "color": "orange",
            "icon": "octicon octicon-tools",
            "type": "module",
            "label": _("服装生产"),
        },
    ]
