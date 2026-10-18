#!/usr/bin/env python3
"""Deterministic mutation testing gate (fail-closed).

This helper is intentionally small and dependency-free. It either runs a project
provided mutation command and then validates the normalized report, or validates
an existing report. A missing or malformed report is a failure, never a skip.

Normalized report schema::

    {
      "tool": "mutmut",
      "targets": [
        {
          "file": "src/auth/service.py",
          "total": 10,
          "killed": 8,
          "timed_out": 1,
          "equivalent": 1,
          "survived": 0
        }
      ]
    }

MSI = (killed + timed_out) / (total - equivalent) * 100.

Exit codes:
  0  gate passed
  1  gate failed (low MSI, missing/invalid report, command failure)
  2  usage or configuration error
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

VERSION = "1.0.0"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

REQUIRED_TARGET_FIELDS = ("file", "total", "killed", "timed_out", "equivalent", "survived")


def _as_count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("target field %r must be an integer" % field)
    if value < 0:
        raise ValueError("target field %r must be non-negative" % field)
    return value


def _load_report(report_path: Path) -> Dict[str, Any]:
    if not report_path.is_file():
        raise FileNotFoundError("mutation report not found: %s" % report_path)
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("mutation report is not valid JSON: %s" % exc) from exc
    if not isinstance(data, dict):
        raise ValueError("mutation report root must be a JSON object")
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("mutation report must contain a non-empty 'targets' list")
    return data


def _validate_targets(targets: Iterable[Any]) -> Tuple[int, int, int, int, int]:
    totals = [0, 0, 0, 0, 0]
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise ValueError("targets[%d] must be an object" % index)
        missing = [name for name in REQUIRED_TARGET_FIELDS if name not in target]
        if missing:
            raise ValueError("targets[%d] missing fields: %s" % (index, ", ".join(missing)))
        if not isinstance(target["file"], str) or not target["file"].strip():
            raise ValueError("targets[%d].file must be a non-empty string" % index)
        counts = [_as_count(target[name], name) for name in REQUIRED_TARGET_FIELDS[1:]]
        total, killed, timed_out, equivalent, survived = counts
        if killed + timed_out + equivalent + survived > total:
            raise ValueError(
                "targets[%d] has killed+timed_out+equivalent+survived greater than total" % index
            )
        for i, value in enumerate(counts):
            totals[i] += value
    return tuple(totals)  # type: ignore[return-value]


def compute_msi(total: int, killed: int, timed_out: int, equivalent: int, survived: int) -> float:
    denominator = total - equivalent
    if denominator <= 0:
        return 100.0 if survived == 0 else 0.0
    return (killed + timed_out) / denominator * 100.0


def evaluate(report_path: Path, min_msi: float) -> Dict[str, Any]:
    data = _load_report(report_path)
    targets = data["targets"]
    total, killed, timed_out, equivalent, survived = _validate_targets(targets)
    msi = compute_msi(total, killed, timed_out, equivalent, survived)

    declared_msi = data.get("msi")
    notes: List[str] = []
    if declared_msi is not None:
        try:
            declared = float(declared_msi)
        except (TypeError, ValueError):
            raise ValueError("report field 'msi' must be numeric when present")
        if abs(declared - msi) > 0.1:
            notes.append(
                "declared msi %.1f differs from computed msi %.1f; using computed value"
                % (declared, msi)
            )

    passed = msi >= min_msi
    result: Dict[str, Any] = {
        "tool": data.get("tool") or "unknown",
        "report": str(report_path),
        "total": total,
        "killed": killed,
        "timed_out": timed_out,
        "equivalent": equivalent,
        "survived": survived,
        "msi": round(msi, 1),
        "min_msi": min_msi,
        "passed": passed,
        "notes": notes,
        "errors": [],
    }
    if not passed:
        result["errors"].append(
            {
                "code": "MUTATION_THRESHOLD_FAILED",
                "message": "Mutation Score Indicator %.1f%% is below required %.1f%%"
                % (msi, min_msi),
            }
        )
    if survived > 0:
        # Survived mutants are reported for triage; the hard gate is the MSI
        # threshold. Critical-module zero-survivor policy belongs to Gate 3.
        result["notes"].append(
            "%d mutant(s) survived; strengthen assertions or remove dead code" % survived
        )
    return result


def _run_command(command: str) -> int:
    # Keep stdout reserved for the machine-readable JSON result.
    sys.stderr.write("Running mutation command: %s\n" % command)
    completed = subprocess.run(command, shell=True, text=True)
    return completed.returncode


def _print_result(result: Dict[str, Any], json_output: bool) -> None:
    if json_output:
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return
    print("Mutation Report: %s" % result.get("report", "unknown"))
    if "tool" in result:
        print("Tool           : %s" % result["tool"])
    if "total" in result:
        print("Mutants        : total=%d killed=%d timed_out=%d equivalent=%d survived=%d"
              % (result["total"], result["killed"], result["timed_out"],
                 result["equivalent"], result["survived"]))
        print("MSI            : %.1f%% (minimum %.1f%%)" % (result["msi"], result["min_msi"]))
    for note in result.get("notes", []):
        print("Note           : %s" % note)
    for error in result.get("errors", []):
        print("Error          : %s: %s" % (error["code"], error["message"]))
    print("Result         : %s" % ("PASSED" if result.get("passed") else "FAILED"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mutation_gate",
        description="Fail-closed mutation testing gate for CI.",
    )
    subparsers = parser.add_subparsers(dest="action")

    run_parser = subparsers.add_parser("run", help="run the mutation command, then evaluate its report")
    run_parser.add_argument("--command", required=True, help="shell command that produces the normalized report")
    run_parser.add_argument("--report", required=True, help="path to the normalized mutation report")
    run_parser.add_argument("--min-msi", type=float, default=80.0, help="minimum MSI percentage (default: 80)")
    run_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    check_parser = subparsers.add_parser("check", help="evaluate an existing normalized report")
    check_parser.add_argument("--report", required=True, help="path to the normalized mutation report")
    check_parser.add_argument("--min-msi", type=float, default=80.0, help="minimum MSI percentage (default: 80)")
    check_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    parser.add_argument("--version", action="version", version="mutation_gate " + VERSION)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.action not in ("run", "check"):
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    if not (0.0 <= args.min_msi <= 100.0):
        sys.stderr.write("error: --min-msi must be between 0 and 100\n")
        return EXIT_USAGE

    report_path = Path(args.report)

    if args.action == "run":
        if not args.command.strip():
            sys.stderr.write("error: --command must not be empty\n")
            return EXIT_USAGE
        code = _run_command(args.command)
        if code != 0:
            sys.stderr.write("error: mutation command failed with exit code %d\n" % code)
            result = {
                "passed": False,
                "report": str(report_path),
                "errors": [
                    {
                        "code": "MUTATION_COMMAND_FAILED",
                        "message": "mutation command exited with code %d" % code,
                    }
                ],
            }
            _print_result(result, args.json)  # type: ignore[arg-type]
            return EXIT_FAIL

    try:
        result = evaluate(report_path, args.min_msi)
    except FileNotFoundError as exc:
        result = {
            "passed": False,
            "report": str(report_path),
            "errors": [{"code": "MUTATION_REPORT_MISSING", "message": str(exc)}],
        }
        _print_result(result, args.json)  # type: ignore[arg-type]
        return EXIT_FAIL
    except ValueError as exc:
        result = {
            "passed": False,
            "report": str(report_path),
            "errors": [{"code": "MUTATION_REPORT_INVALID", "message": str(exc)}],
        }
        _print_result(result, args.json)  # type: ignore[arg-type]
        return EXIT_FAIL

    _print_result(result, args.json)
    return EXIT_PASS if result["passed"] else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
