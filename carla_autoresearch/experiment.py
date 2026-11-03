"""Fail closed for old machine-specific arguments; accept explicit new capture input."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Migrated CARLA experiment entrypoint")
    parser.add_argument("--profile")
    parser.add_argument("--recipe")
    args, old_args = parser.parse_known_args()
    if old_args or not args.profile or not args.recipe:
        print(json.dumps({"ok": False, "error": {"code": "migration_required", "message":
              "Old implicit build/server flags are not executed. Use carla-agent capture run --profile PROFILE --request REQUEST, or research start --plan PLAN. This wrapper accepts --profile PROFILE --recipe RECIPE only.", "details": {"unmapped_arguments": old_args}}}))
        return 2
    from carla_agent.cli import main as command
    from carla_agent.protocol import read_json, AgentError
    try:
        recipe = read_json(args.recipe)
    except AgentError as exc:
        print(json.dumps({"schema_version": 1, "ok": False, "error": exc.as_dict()}))
        return exc.exit_code
    return command(["capture", "run", "--profile", args.profile, "--params", json.dumps({"recipe": recipe})])


if __name__ == "__main__":
    raise SystemExit(main())
