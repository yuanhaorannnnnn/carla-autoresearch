#!/usr/bin/env python3
"""Build/check the offline discovery index from SKILL.md (requires dev PyYAML)."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from carla_agent.protocol import OPERATIONS

TARGET = ROOT / "src/carla_agent/skill_catalog.json"
MODES = {"cli", "native-api", "conditional", "workflow", "alias"}
CATEGORIES = {"runtime", "sensors", "engineering", "data", "learning", "research", "compatibility"}
RESEARCH = {"research." + action for action in ("start", "status", "stop", "resume", "report", "validate", "compare")}


def build():
    entries = []
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        raw = path.read_bytes()
        match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", raw.decode("utf-8"), re.S)
        if not match:
            raise ValueError(f"{path}: missing frontmatter")
        data = yaml.safe_load(match[1])
        if not isinstance(data, dict):
            raise ValueError(f"{path}: frontmatter must be an object")
        name, description = data.get("name"), data.get("description")
        if name != path.parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            raise ValueError(f"{path}: invalid name or directory mismatch")
        if not isinstance(description, str) or not description.strip() or len(description) > 1024:
            raise ValueError(f"{path}: invalid description")
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict) or metadata.get("execution") not in MODES or metadata.get("category") not in CATEGORIES:
            raise ValueError(f"{path}: missing/invalid execution/category metadata")
        declared = metadata.get("operations", "")
        if not isinstance(declared, str):
            raise ValueError(f"{path}: operations must be a comma separated string")
        operations = sorted(set(op.strip() for op in declared.split(",") if op.strip()))
        if set(operations) - set(OPERATIONS) - RESEARCH:
            raise ValueError(f"{path}: declares an unknown CLI operation")
        entry = {"name": name, "description": description.strip(), "category": metadata["category"],
                 "execution": metadata["execution"], "cli_operations": operations,
                 "file": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
        if metadata.get("blueprint"):
            if not isinstance(metadata["blueprint"], str):
                raise ValueError(f"{path}: blueprint must be a string")
            entry["blueprint"] = metadata["blueprint"]
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", raw.decode("utf-8")):
            destination = link.strip().strip("<>")
            url = urlsplit(destination)
            if url.scheme or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError(f"{path}: missing or nonportable skill link: {destination}")
        entries.append(entry)
    return {"schema_version": 1, "baseline": "sprint42@2075f526dec86362fe058a6fff939e6832876759", "skills": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the index without writing")
    args = parser.parse_args()
    try:
        result = build()
        expected = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != expected:
                raise ValueError("Skill index is stale; run scripts/update_skill_catalog.py")
        else:
            TARGET.write_text(expected, encoding="utf-8")
        print(json.dumps({"ok": True, "skills": len(result["skills"]), "check_only": args.check}))
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
