from markupsafe import escape

from app.utils.constants import DEPARTMENTS, SCHOOL_STRUCTURE


def is_valid_academic_placement(department, trade, level, class_name):
    classes = SCHOOL_STRUCTURE.get(department, {}).get(trade, {}).get(level, ())
    return class_name in classes


def get_academic_placement(class_name):
    for department, trade_map in SCHOOL_STRUCTURE.items():
        for trade, level_map in trade_map.items():
            for level, class_names in level_map.items():
                if class_name in class_names:
                    return {
                        "department": department,
                        "trade": trade,
                        "level": level,
                        "class_name": class_name,
                    }
    return {}


def render_academic_placement_fields(
    prefix,
    values=None,
    column_class="col-md-3",
    class_names=None,
    required=True,
):
    values = values or {}
    department = values.get("department", "")
    trade = values.get("trade", "")
    level = values.get("level", "")
    class_name = values.get("class_name", "")

    departments = list(DEPARTMENTS)
    if department and department not in departments:
        departments.append(department)

    trades = [
        (trade_name, department_name)
        for department_name, trade_map in SCHOOL_STRUCTURE.items()
        for trade_name in trade_map
    ]
    if trade and not any(name == trade and owner == department for name, owner in trades):
        trades.append((trade, department))

    levels = [
        (level_name, department_name, trade_name)
        for department_name, trade_map in SCHOOL_STRUCTURE.items()
        for trade_name, level_map in trade_map.items()
        for level_name in level_map
    ]
    if level and not any(
        name == level and owner == department and trade_name == trade
        for name, owner, trade_name in levels
    ):
        levels.append((level, department, trade))

    allowed_classes = set(class_names) if class_names is not None else None
    classes = [
        (class_label, department_name, trade_name, level_name)
        for department_name, trade_map in SCHOOL_STRUCTURE.items()
        for trade_name, level_map in trade_map.items()
        for level_name, candidate_classes in level_map.items()
        for class_label in candidate_classes
        if allowed_classes is None or class_label in allowed_classes
    ]
    if class_name and not any(
        name == class_name and owner == department and trade_name == trade and level_name == level
        for name, owner, trade_name, level_name in classes
    ) and (allowed_classes is None or class_name in allowed_classes):
        classes.append((class_name, department, trade, level))

    def option(label, selected="", attributes=""):
        selected_attr = " selected" if label == selected else ""
        return (
            f'<option value="{escape(label)}"{attributes}{selected_attr}>'
            f"{escape(label)}</option>"
        )

    department_options = "".join(option(name, department) for name in departments)
    trade_options = "".join(
        option(name, trade, f' data-department="{escape(owner)}"')
        for name, owner in trades
    )
    level_options = "".join(
        option(name, level, f' data-department="{escape(owner)}" data-trade="{escape(trade_name)}"')
        for name, owner, trade_name in levels
    )
    class_options = "".join(
        option(
            name,
            class_name,
            f' data-department="{escape(owner)}" data-trade="{escape(trade_name)}" '
            f'data-level="{escape(level_name)}"',
        )
        for name, owner, trade_name, level_name in classes
    )

    fields = (
        ("department", "Department", "Choose department...", department_options, False),
        ("trade", "Trade", "Choose trade...", trade_options, not department),
        ("level", "Level", "Choose level...", level_options, not trade),
        ("class_name", "Class", "Choose a class...", class_options, not level),
    )
    controls = []
    for field, label, placeholder, options, disabled in fields:
        disabled_attr = " disabled" if disabled else ""
        field_id = "class" if field == "class_name" else field
        controls.append(
            f'<div class="{column_class}"><label class="form-label" for="{prefix}-{field_id}">'
            f'{label}</label><select class="form-select" id="{prefix}-{field_id}" name="{field}" '
            f'{"required" if required else ""}{disabled_attr}><option value="">{placeholder}</option>{options}</select></div>'
        )

    return (
        '<div class="col-12"><div class="row g-3 academic-placement-fields">'
        + "".join(controls)
        + "</div></div>"
    )
