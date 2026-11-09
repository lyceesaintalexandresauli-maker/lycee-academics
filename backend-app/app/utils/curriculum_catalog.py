"""Curriculum options used by class and teacher assignment forms."""
import json
from pathlib import Path


_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "curriculum_modules.json"
with _CATALOG_PATH.open(encoding="utf-8") as catalog_file:
    _CURRICULUM = json.load(catalog_file)

_TRADE_ALIASES = {
    "fashionanddesign": "fashiondesign",
    "fashiondesign": "fashiondesign",
    "professionalaccountant": "accounting",
    "accounting": "accounting",
    "networkingandinternettechnology": "networkingandinternettechnologies",
    "networkingandinternettechnologies": "networkingandinternettechnologies",
}


def _key(value):
    return "".join(character for character in (value or "").casefold() if character.isalnum())


def _trade_key(value):
    key = _key(value)
    return _TRADE_ALIASES.get(key, key)


def curriculum_modules_for(department, trade, level):
    """Return catalog modules for the selected school structure and level."""
    department_key = _key(department)
    trade_key = _trade_key(trade)
    level_key = _key(level)
    modules = []
    seen = set()
    for item in _CURRICULUM:
        if (
            _key(item["department"]) != department_key
            or _trade_key(item["trade"]) != trade_key
            or _key(item["level"]) != level_key
        ):
            continue
        identity = (item["code"].casefold(), item["title"].casefold())
        if identity in seen:
            continue
        seen.add(identity)
        modules.append(item)
    return modules
