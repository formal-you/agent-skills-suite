#!/usr/bin/env python3
"""Optional engine proxy for the spec-generator skill.

The engine is never required. This proxy checks whether the optional Python package is
installed; if it is absent it explains how to continue prompt-only and exits 2.

Usage:
    python scripts/engine.py [--check] [engine arguments...]
    python scripts/engine.py --help

Exit codes:
    0 engine ran, or --help/--version/--check succeeded
    2 optional engine not installed (guidance printed to stderr)
    3 unexpected internal error
"""

from __future__ import annotations

import importlib.util
import sys

VERSION = "2.0.0"
SKILL_NAME = "spec-generator"
ENGINE_MODULE = "spec_generator"
LINT_SCRIPT = "lint_spec.py"
INSTALL_HINT = "uv tool install agent-spec-suite   (or: pip install agent-spec-suite)"

GUIDANCE = f"""The optional {SKILL_NAME} engine is not installed.

Continue prompt-only (this is fully supported):
  1. python scripts/scaffold.py --out .specs
  2. Follow SKILL.md and fill the generated files.
  3. python scripts/{LINT_SCRIPT} .specs

Install the engine only if you want the deterministic generator:
  {INSTALL_HINT}
"""


def engine_available() -> bool:
    try:
        return importlib.util.find_spec(ENGINE_MODULE) is not None
    except (ImportError, ValueError):
        return False


def print_local_help() -> None:
    print(f"engine.py {VERSION} - optional engine proxy for {SKILL_NAME}")
    print()
    print("The engine is not installed in this environment. The skill still works:")
    print("  python scripts/scaffold.py --out .specs")
    print(f"  python scripts/{LINT_SCRIPT} .specs")
    print()
    print(f"Install the engine: {INSTALL_HINT}")
    print()
    print("Options:")
    print("  --check     exit 0 if the engine is importable, 2 otherwise")
    print("  --help      show this help (or the engine help when installed)")
    print("  --version   show this proxy version")
    print("  ...         any other arguments are forwarded to the engine")


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)

    if "--check" in arguments:
        if engine_available():
            print(f"{SKILL_NAME} engine is available ({ENGINE_MODULE}).")
            return 0
        print(GUIDANCE, file=sys.stderr)
        return 2

    if "--help" in arguments or "-h" in arguments:
        if not engine_available():
            print_local_help()
            return 0
        return _run_engine(arguments)

    if "--version" in arguments and not engine_available():
        print(f"engine.py {VERSION} ({SKILL_NAME}; optional engine not installed)")
        return 0

    if not engine_available():
        print(GUIDANCE, file=sys.stderr)
        return 2
    return _run_engine(arguments)


def _run_engine(arguments):
    try:
        module = __import__(f"{ENGINE_MODULE}.cli", fromlist=["main"])
        return int(module.main(arguments))
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:  # noqa: BLE001 - surface unexpected failures
        print(f"error: optional engine failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
