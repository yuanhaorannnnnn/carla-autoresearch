"""Domain commands and machine-readable contracts for skills and humans."""

import argparse
import json
import sys

from . import __version__
from .bridge import run_operation
from .protocol import AgentError, OPERATIONS, read_json, schema


def parser():
    root = argparse.ArgumentParser(prog="carla-agent", description="Atomic CARLA operations; external matching PythonAPI required")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="domain", required=True)
    describe = commands.add_parser("schema", help="Inspect one operation's actual input contract")
    describe.add_argument("operation", nargs="?", help="e.g. actors.spawn; omit to list operations")
    skills = commands.add_parser("skills", help="Discover domain skills offline; no simulator connection")
    skill_actions = skills.add_subparsers(dest="action", required=True)
    listing = skill_actions.add_parser("list")
    listing.add_argument("--query", default="", help="Keywords or an exact blueprint; all space-separated terms must match (not semantic search)")
    listing.add_argument("--category")
    listing.add_argument("--execution", choices=("cli", "native-api", "conditional", "workflow", "alias"))
    showing = skill_actions.add_parser("show")
    showing.add_argument("name")
    domains = {}
    for operation in OPERATIONS:
        domain, action = operation.split(".")
        if domain not in domains:
            domains[domain] = commands.add_parser(domain).add_subparsers(dest="action", required=True)
        item = domains[domain].add_parser(action, help=f"{operation}; see schema for parameters")
        item.add_argument("--profile", required=True)
        source = item.add_mutually_exclusive_group()
        source.add_argument("--request", help="JSON file containing operation parameters")
        source.add_argument("--params", help="Inline JSON object")
        item.add_argument("--json", action="store_true", help="JSON is always the output format")
    research = commands.add_parser("research", help="Bounded experiments sharing the operation layer")
    actions = research.add_subparsers(dest="action", required=True)
    for name in ("validate", "start", "status", "stop", "resume", "report", "compare"):
        item = actions.add_parser(name)
        if name in ("start", "validate"):
            item.add_argument("--plan", required=True)
            if name == "start":
                item.add_argument("--foreground", action="store_true")
        else:
            item.add_argument("--run", required=True, help="Absolute run directory")
        if name == "resume":
            item.add_argument("--retry-interrupted", action="store_true")
            item.add_argument("--foreground", action="store_true")
        item.add_argument("--json", action="store_true")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.domain == "skills":
            from . import catalog
            result = catalog.describe(args.name) if args.action == "show" else catalog.discover(args.query, args.category, args.execution)
        elif args.domain == "schema":
            if args.operation and args.operation.startswith("research."):
                from . import research
                action = args.operation.split(".", 1)[1]
                if action in ("start", "validate"):
                    result = {"operation": args.operation, "cli": f"research {action} --plan FILE" + (" [--foreground]" if action == "start" else ""),
                              "mutates_world": action == "start", "plan": research.plan_schema()}
                elif action in ("status", "stop", "resume", "report", "compare"):
                    result = {"operation": args.operation, "run": "absolute run directory", "retry_interrupted_required": action == "resume",
                              "mutates_world": action in ("stop", "resume"), "read_only": action in ("status", "report", "compare")}
                else:
                    raise AgentError("unknown_operation", args.operation, 2)
            else:
                result = schema(args.operation) if args.operation else {"operations": sorted(OPERATIONS) + ["research." + a for a in ("validate", "start", "status", "stop", "resume", "report", "compare")]}
        elif args.domain == "research":
            from . import research
            result = research.dispatch(args)
        else:
            params = read_json(args.request) if args.request else json.loads(args.params or "{}")
            result = run_operation(args.profile, f"{args.domain}.{args.action}", params)
        print(json.dumps({"schema_version": 1, "ok": True, "result": result}, ensure_ascii=False, allow_nan=False))
        return 0
    except AgentError as exc:
        print(json.dumps({"schema_version": 1, "ok": False, "error": exc.as_dict()}, ensure_ascii=False, allow_nan=False))
        return exc.exit_code
    except (ValueError, TypeError) as exc:
        print(json.dumps({"schema_version": 1, "ok": False, "error": {"code": "invalid_input", "message": str(exc), "details": {}}}))
        return 2
    except KeyboardInterrupt:
        print(json.dumps({"schema_version": 1, "ok": False, "error": {"code": "interrupted", "message": "Check session cleanup before retry", "details": {}}}))
        return 130


if __name__ == "__main__":
    sys.exit(main())
