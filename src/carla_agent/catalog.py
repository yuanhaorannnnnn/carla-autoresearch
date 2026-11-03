"""Offline skill discovery; no CARLA import, connection, or simulator mutation."""

import json
from importlib.resources import files

from .protocol import AgentError


def skill_catalog():
    try:
        return json.loads(files("carla_agent").joinpath("skill_catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AgentError("skill_catalog_unavailable", "Installed skill index is missing or invalid", 3) from exc


def discover(query="", category=None, execution=None):
    catalog = skill_catalog()
    words = query.casefold().split()
    selected = []
    for skill in catalog["skills"]:
        if category and skill["category"] != category:
            continue
        if execution and skill["execution"] != execution:
            continue
        searchable = " ".join((skill["name"], skill["description"], skill.get("blueprint", ""))).casefold()
        if all(word in searchable for word in words):
            selected.append(skill)
    return {"baseline": catalog["baseline"], "count": len(selected), "skills": selected,
            "search_mode": "all_keywords",
            "search_hint": "Use short domain keywords or a blueprint (e.g. dvs, mems, sensor.camera.stereo); the host agent routes full natural-language requests.",
            "execution_note": "Execution is the primary workflow, not runtime verification; cli_operations are the wrapped subset."}


def describe(name):
    for skill in skill_catalog()["skills"]:
        if skill["name"] == name:
            return skill
    raise AgentError("unknown_skill", name, 2)
