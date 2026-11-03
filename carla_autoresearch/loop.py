"""Deprecated loop entrypoint: no implicit restoration of old YAML state."""
import json


def main():
    print(json.dumps({"ok": False, "error": {"code": "migration_required", "message":
          "Use carla-agent research start/status/stop/resume/report. Legacy YAML has no trustworthy trial identity and is not resumed automatically.", "details": {}}}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
