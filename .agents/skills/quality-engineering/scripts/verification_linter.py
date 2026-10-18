#!/usr/bin/env python3
"""Gate 3 acceptance audit linter for QA verification artifacts (03-qa-verification.md).

Deterministic static checker for QA verification signoff:
- Cyclomatic Complexity (Section 3): V(G) <= 10, warnings 11-15, errors > 15, Basis Path >= V(G)
- Mutation Testing and MSI Audit (Section 4): Non-empty table, numeric MSI >= 80%
- Execution Evidence (Section 5): Command and Result fields must not be blank
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION = "1.0.0"
EXIT_PASS = 0
EXIT_VIOLATIONS = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

DEFAULT_CONFIG: Dict[str, Any] = {
    "min_msi": 80,
    "max_vg_standard": 10,
    "max_vg_warning": 15,
    "require_mutation_section": True,
    "require_execution_evidence": True,
}

_MSI_RE = re.compile(
    r"(?:MSI|mutation\s+score(?:\s+indicator)?)[^\d]*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_KILLED_RE = re.compile(r"killed[^\d]*(\d+)", re.IGNORECASE)
_TOTAL_MUT_RE = re.compile(r"(?:total|generated)[^\d]*(\d+)\s+mutant", re.IGNORECASE)


class Finding:
    """Represents a deterministic verification violation."""

    __slots__ = ("task", "code", "message", "file", "line")

    def __init__(
        self,
        task: str,
        code: str,
        message: str,
        file: str = "03-qa-verification.md",
        line: int = 0,
    ) -> None:
        self.task = task
        self.code = code
        self.message = message
        self.file = file
        self.line = line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }

    def __repr__(self) -> str:
        return f"Finding({self.task!r}, {self.code!r}, {self.message!r}, {self.file!r}, {self.line})"


def _lint_qa_complexity(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    warnings: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Audit Section 3: Cyclomatic complexity and basis path coverage."""
    qa_path = task_dir / "03-qa-verification.md"
    if not qa_path.is_file():
        return
    try:
        qa_text = qa_path.read_text(encoding="utf-8")
    except OSError:
        return

    qa_passed_match = re.search(r"^[-*+]\s*\[[xX]\]\s*QA_PASSED\b", qa_text, re.MULTILINE)
    if not qa_passed_match:
        return

    verdict_line_num = 1
    for idx, line in enumerate(qa_text.splitlines(), 1):
        if re.search(r"^[-*+]\s*\[[xX]\]\s*QA_PASSED\b", line):
            verdict_line_num = idx
            break

    sec_match = re.search(
        r"^#{2,4}\s*(?:\d+\.\s*)?Complexity\s+and\s+basis\s+path\s+coverage\b.*$",
        qa_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not sec_match:
        findings.append(
            Finding(
                task_name,
                "COMPLEXITY_MISSING_SECTION",
                "03-qa-verification.md is signed off with QA_PASSED but missing 'Complexity and basis path coverage' section",
                "03-qa-verification.md",
                verdict_line_num,
            )
        )
        return

    lines = qa_text.splitlines()
    sec_line_num = 1
    in_section = False
    section_lines: List[Tuple[int, str]] = []
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_section:
            if re.match(r"^#{2,4}\s*(?:\d+\.\s*)?Complexity\s+and\s+basis\s+path\s+coverage\b", stripped, re.IGNORECASE):
                in_section = True
                sec_line_num = line_idx
                continue
        else:
            if stripped.startswith("## ") or (stripped.startswith("### ") and not stripped.startswith("#### ")):
                break
            section_lines.append((line_idx, line))

    header_idx = -1
    col_headers: List[str] = []
    separator_found = False
    data_rows: List[Tuple[int, List[str]]] = []

    for idx, (line_no, line) in enumerate(section_lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if header_idx == -1:
            lowered = [c.lower() for c in cells]
            if any("complexity" in c or "v(g)" in c for c in lowered):
                header_idx = idx
                col_headers = lowered
                continue
        elif not separator_found:
            if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                separator_found = True
                continue
        else:
            if any(c for c in cells):
                data_rows.append((line_no, cells))

    if not data_rows:
        findings.append(
            Finding(
                task_name,
                "COMPLEXITY_MISSING_SECTION",
                "03-qa-verification.md is signed off with QA_PASSED but Section 3 'Complexity and basis path coverage' table has no data rows",
                "03-qa-verification.md",
                sec_line_num,
            )
        )
        return

    func_col = 0
    vg_col = 1
    cases_col = 3
    for i, h in enumerate(col_headers):
        if "function" in h or "module" in h or "target" in h:
            func_col = i
        elif "v(g)" in h or "cyclomatic" in h or "complexity" in h:
            vg_col = i
        elif "test case" in h or "mapped test" in h or "test case id" in h or "test cases" in h:
            cases_col = i

    cfg = config or DEFAULT_CONFIG
    max_std = cfg.get("max_vg_standard", 10)
    max_warn = cfg.get("max_vg_warning", 15)

    for line_no, cells in data_rows:
        fn_name = cells[func_col] if func_col < len(cells) else ""
        fn_name = fn_name.strip("`\"' ")
        if not fn_name:
            fn_name = "unknown"

        vg_raw = cells[vg_col] if vg_col < len(cells) else ""
        vg_match = re.search(r"\b(\d+)\b", vg_raw)
        if not vg_match:
            continue
        vg = int(vg_match.group(1))

        cases_raw = cells[cases_col] if cases_col < len(cells) else ""
        cleaned_cases = cases_raw.strip()
        if cleaned_cases.lower() in ("none", "n/a", "-", ""):
            test_count = 0
        else:
            tc_tokens = re.findall(r"\b(?:TC|test|case)[-\w]*\b", cleaned_cases, re.IGNORECASE)
            comma_items = [item.strip() for item in re.split(r"[,;\n]+", cleaned_cases) if item.strip()]
            test_count = max(len(tc_tokens), len(comma_items))

        if vg > max_warn:
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_EXCEEDS_MAX_THRESHOLD",
                    f"Function {fn_name!r} has cyclomatic complexity V(G)={vg} exceeding maximum threshold of {max_warn}",
                    "03-qa-verification.md",
                    line_no,
                )
            )
        elif max_std < vg <= max_warn:
            if warnings is not None:
                warnings.append(
                    {
                        "task": task_name,
                        "code": "COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD",
                        "message": (
                            f"Function {fn_name!r} has cyclomatic complexity V(G)={vg} exceeding standard threshold of {max_std}"
                            " (requires architectural justification in 02-dev-workspace.md)"
                        ),
                        "file": "03-qa-verification.md",
                        "line": line_no,
                    }
                )

        if test_count < vg:
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_BASIS_PATH_INSUFFICIENT",
                    f"Function {fn_name!r} has V(G)={vg} but only {test_count} test case(s) provided (basis path testing requires >= V(G))",
                    "03-qa-verification.md",
                    line_no,
                )
            )


def _lint_qa_mutation(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    warnings: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Audit Section 4: Mutation testing and MSI audit."""
    cfg = config or DEFAULT_CONFIG
    if not cfg.get("require_mutation_section", True):
        return

    qa_path = task_dir / "03-qa-verification.md"
    if not qa_path.is_file():
        return
    try:
        qa_text = qa_path.read_text(encoding="utf-8")
    except OSError:
        return

    qa_passed_match = re.search(r"^[-*+]\s*\[[xX]\]\s*QA_PASSED\b", qa_text, re.MULTILINE)
    if not qa_passed_match:
        return

    verdict_line_num = 1
    for idx, line in enumerate(qa_text.splitlines(), 1):
        if re.search(r"^[-*+]\s*\[[xX]\]\s*QA_PASSED\b", line):
            verdict_line_num = idx
            break

    sec_match = re.search(
        r"^#{2,4}\s*(?:\d+\.\s*)?Mutation\s+testing\b.*$",
        qa_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not sec_match:
        findings.append(
            Finding(
                task_name,
                "QA_MISSING_MUTATION_EVIDENCE",
                "03-qa-verification.md is signed off with QA_PASSED but missing 'Mutation testing and MSI audit' section",
                "03-qa-verification.md",
                verdict_line_num,
            )
        )
        return

    lines = qa_text.splitlines()
    sec_line_num = 1
    in_section = False
    section_lines: List[Tuple[int, str]] = []
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_section:
            if re.match(r"^#{2,4}\s*(?:\d+\.\s*)?Mutation\s+testing\b", stripped, re.IGNORECASE):
                in_section = True
                sec_line_num = line_idx
                continue
        else:
            if stripped.startswith("## ") or (stripped.startswith("### ") and not stripped.startswith("#### ")):
                break
            section_lines.append((line_idx, line))

    raw_tables: List[List[Tuple[int, str]]] = []
    current_block: List[Tuple[int, str]] = []

    for line_no, line in section_lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            current_block.append((line_no, line))
        else:
            if current_block:
                raw_tables.append(current_block)
                current_block = []
    if current_block:
        raw_tables.append(current_block)

    min_msi = float(cfg.get("min_msi", 80))
    table_results: List[Dict[str, Any]] = []

    for block in raw_tables:
        header_idx = -1
        col_headers: List[str] = []
        separator_found = False
        data_rows: List[Tuple[int, List[str]]] = []

        for idx, (line_no, line) in enumerate(block):
            stripped = line.strip()
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if header_idx == -1:
                lowered = [c.lower() for c in cells]
                if any(
                    "mutation" in c
                    or "msi" in c
                    or "file" in c
                    or "metric" in c
                    or "target" in c
                    or "field" in c
                    or "value" in c
                    or "tool" in c
                    for c in lowered
                ):
                    header_idx = idx
                    col_headers = lowered
                    continue
                if idx + 1 < len(block):
                    next_stripped = block[idx + 1][1].strip()
                    next_cells = [c.strip() for c in next_stripped.split("|")[1:-1]]
                    if next_cells and all(re.match(r"^:?-+:?$", c) for c in next_cells if c):
                        header_idx = idx
                        col_headers = lowered
                        continue
            elif not separator_found:
                if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                    separator_found = True
                    continue
            else:
                if any(c for c in cells):
                    data_rows.append((line_no, cells))

        if not col_headers or not separator_found:
            continue

        is_kv_format = (
            len(col_headers) == 2
            and any("metric" in c or "field" in c for c in col_headers)
            and any("value" in c for c in col_headers)
        )

        tbl_findings: List[Finding] = []
        compliant_rows = 0

        if is_kv_format:
            kv_data_rows = [
                (lno, cells)
                for lno, cells in data_rows
                if len(cells) >= 2 and cells[1].strip() != ""
            ]
            if not kv_data_rows:
                table_results.append({
                    "format": "kv",
                    "has_data": False,
                    "compliant": False,
                    "findings": [],
                })
                continue

            msi_found = False
            for line_no, cells in data_rows:
                if len(cells) < 2:
                    continue
                key_cell = cells[0].lower()
                val_cell = cells[1].strip()
                if "msi" in key_cell or "mutation score" in key_cell:
                    msi_found = True
                    score_match = re.search(r"(\d+(?:\.\d+)?)\s*%?", val_cell)
                    if not score_match:
                        tbl_findings.append(
                            Finding(
                                task_name,
                                "QA_INVALID_MSI_SCORE",
                                f"Invalid or non-numeric MSI score {val_cell!r} in mutation audit table",
                                "03-qa-verification.md",
                                line_no,
                            )
                        )
                    else:
                        msi_score = float(score_match.group(1))
                        if msi_score < min_msi:
                            tbl_findings.append(
                                Finding(
                                    task_name,
                                    "QA_INVALID_MSI_SCORE",
                                    f"Mutation Score Indicator (MSI) {msi_score:.1f}% is below required {min_msi:.0f}% threshold",
                                    "03-qa-verification.md",
                                    line_no,
                                )
                            )
                        else:
                            compliant_rows += 1
            if not msi_found:
                tbl_findings.append(
                    Finding(
                        task_name,
                        "QA_INVALID_MSI_SCORE",
                        "Missing Mutation Score Indicator (MSI) metric in mutation audit table",
                        "03-qa-verification.md",
                        sec_line_num,
                    )
                )

            table_results.append({
                "format": "kv",
                "has_data": True,
                "compliant": len(tbl_findings) == 0 and compliant_rows > 0,
                "findings": tbl_findings,
            })
        else:
            file_col = 0
            msi_col = -1
            for i, h in enumerate(col_headers):
                if "file" in h or "target" in h or "source" in h:
                    file_col = i
                elif "msi" in h or "score" in h:
                    msi_col = i

            if msi_col == -1:
                msi_col = 7 if len(col_headers) > 7 else len(col_headers) - 2

            target_data_rows = []
            for line_no, cells in data_rows:
                target_file = cells[file_col].strip("`\"' ") if file_col < len(cells) else ""
                msi_raw = cells[msi_col].strip() if msi_col < len(cells) else ""
                if any(c.strip() for c in cells) and (bool(target_file) or bool(msi_raw)):
                    target_data_rows.append((line_no, cells, target_file, msi_raw))

            if not target_data_rows:
                table_results.append({
                    "format": "per_target",
                    "has_data": False,
                    "compliant": False,
                    "findings": [],
                })
                continue

            for line_no, cells, target_file, msi_raw in target_data_rows:
                tf_display = target_file if target_file else "unknown"
                score_match = re.search(r"(\d+(?:\.\d+)?)\s*%?", msi_raw)
                if not score_match:
                    tbl_findings.append(
                        Finding(
                            task_name,
                            "QA_INVALID_MSI_SCORE",
                            f"Target file {tf_display!r} has invalid or missing MSI score {msi_raw!r} in 03-qa-verification.md",
                            "03-qa-verification.md",
                            line_no,
                        )
                    )
                else:
                    score = float(score_match.group(1))
                    if score < min_msi:
                        tbl_findings.append(
                            Finding(
                                task_name,
                                "QA_INVALID_MSI_SCORE",
                                f"Target file {tf_display!r} has MSI score {score:.1f}% below required {min_msi:.0f}% threshold",
                                "03-qa-verification.md",
                                line_no,
                            )
                        )
                    else:
                        compliant_rows += 1

            table_results.append({
                "format": "per_target",
                "has_data": True,
                "compliant": len(tbl_findings) == 0 and compliant_rows > 0,
                "findings": tbl_findings,
            })

    if not any(t["has_data"] for t in table_results):
        # Fallback: check freeform text if no structured table with data rows
        body_text = "\n".join(line for _, line in section_lines)
        msi_match = _MSI_RE.search(body_text)
        if msi_match:
            msi_score = float(msi_match.group(1))
            if msi_score < min_msi:
                findings.append(
                    Finding(
                        task_name,
                        "QA_INVALID_MSI_SCORE",
                        f"Mutation Score Indicator (MSI) {msi_score:.1f}% is below required {min_msi:.0f}% threshold",
                        "03-qa-verification.md",
                        sec_line_num,
                    )
                )
            return

        killed_m = _KILLED_RE.search(body_text)
        total_m = _TOTAL_MUT_RE.search(body_text)
        if killed_m and total_m:
            killed = int(killed_m.group(1))
            total = int(total_m.group(1))
            msi_score = (killed / total * 100) if total else 0.0
            if msi_score < min_msi:
                findings.append(
                    Finding(
                        task_name,
                        "QA_INVALID_MSI_SCORE",
                        f"Derived MSI {msi_score:.1f}% ({killed}/{total}) is below required {min_msi:.0f}% threshold",
                        "03-qa-verification.md",
                        sec_line_num,
                    )
                )
            return

        findings.append(
            Finding(
                task_name,
                "QA_MISSING_MUTATION_EVIDENCE",
                "03-qa-verification.md is signed off with QA_PASSED but Section 4 'Mutation testing and MSI audit' table has no data rows",
                "03-qa-verification.md",
                sec_line_num,
            )
        )
        return

    if any(t["compliant"] for t in table_results):
        return

    for t in table_results:
        if t["has_data"]:
            findings.extend(t["findings"])


def _audit_execution_evidence(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Audit Section 5: Execution evidence (Command and Result must not be blank)."""
    cfg = config or DEFAULT_CONFIG
    if not cfg.get("require_execution_evidence", True):
        return

    qa_path = task_dir / "03-qa-verification.md"
    if not qa_path.is_file():
        return
    try:
        qa_text = qa_path.read_text(encoding="utf-8")
    except OSError:
        return

    qa_passed_match = re.search(r"^[-*+]\s*\[[xX]\]\s*QA_PASSED\b", qa_text, re.MULTILINE)
    if not qa_passed_match:
        return

    sec_match = re.search(
        r"^#{2,4}\s*(?:\d+\.\s*)?Execution\s+evidence\b.*$",
        qa_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not sec_match:
        return  # Execution evidence section is optional if omitted

    lines = qa_text.splitlines()
    sec_line_num = 1
    in_section = False
    section_lines: List[str] = []
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_section:
            if re.match(r"^#{2,4}\s*(?:\d+\.\s*)?Execution\s+evidence\b", stripped, re.IGNORECASE):
                in_section = True
                sec_line_num = line_idx
                continue
        else:
            if stripped.startswith("## ") or (stripped.startswith("### ") and not stripped.startswith("#### ")):
                break
            section_lines.append(line)

    body_text = "\n".join(section_lines)
    command_re = re.compile(r"^\|\s*Command\s*\|\s*([^|\r\n]*)\|", re.IGNORECASE | re.MULTILINE)
    result_re = re.compile(r"^\|\s*Result\s*\|\s*([^|\r\n]*)\|", re.IGNORECASE | re.MULTILINE)
    cmd_m = command_re.search(body_text)
    res_m = result_re.search(body_text)
    cmd_empty = not cmd_m or not cmd_m.group(1).strip()
    res_empty = not res_m or not res_m.group(1).strip()
    if cmd_empty:
        findings.append(
            Finding(
                task_name,
                "EVIDENCE_MISSING_COMMAND",
                "Execution evidence 'Command' field is blank — a claim without a command is not evidence",
                "03-qa-verification.md",
                sec_line_num,
            )
        )
    if res_empty:
        findings.append(
            Finding(
                task_name,
                "EVIDENCE_MISSING_RESULT",
                "Execution evidence 'Result' field is blank — record the actual test runner output",
                "03-qa-verification.md",
                sec_line_num,
            )
        )


def lint_task_bundle(
    task_dir: Path,
    findings: List[Finding],
    warnings: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Run all Gate 3 verification audits on a single task bundle."""
    task_name = task_dir.name
    _lint_qa_complexity(task_name, task_dir, findings, warnings, config)
    _lint_qa_mutation(task_name, task_dir, findings, warnings, config)
    _audit_execution_evidence(task_name, task_dir, findings, config)


def lint_tasks(
    tasks_dir: Path,
    target_task: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Finding], List[Dict[str, Any]], int]:
    """Scan and verify tasks under tasks_dir."""
    findings: List[Finding] = []
    warnings: List[Dict[str, Any]] = []
    scanned = 0

    if target_task:
        candidate = tasks_dir / target_task
        if not candidate.is_dir():
            raise FileNotFoundError(f"Specified task directory not found: {candidate}")
        task_dirs = [candidate]
    else:
        task_dirs = sorted(
            [d for d in tasks_dir.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name != "archive"]
        )

    for td in task_dirs:
        qa_file = td / "03-qa-verification.md"
        if qa_file.is_file():
            scanned += 1
            lint_task_bundle(td, findings, warnings, config)

    return findings, warnings, scanned


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verification_linter",
        description="Gate 3 deterministic static acceptance checker for QA verification artifacts.",
    )
    parser.add_argument(
        "--tasks-dir",
        default="./tasks",
        help="directory containing task bundles (default: ./tasks)",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="specific task ID to audit (default: audit all tasks)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output machine-readable JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as Gate 3 errors",
    )
    parser.add_argument(
        "--min-msi",
        type=int,
        default=80,
        help="minimum Mutation Score Indicator %% (default: 80)",
    )
    parser.add_argument(
        "--no-mutation",
        action="store_true",
        help="skip the mutation testing section check",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        help="skip the execution evidence completeness check",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="verification_linter " + VERSION,
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.min_msi is not None and not (0 <= args.min_msi <= 100):
        sys.stderr.write("error: --min-msi must be between 0 and 100\n")
        return EXIT_USAGE

    config = dict(DEFAULT_CONFIG)
    if args.min_msi is not None:
        config["min_msi"] = args.min_msi
    if args.no_mutation:
        config["require_mutation_section"] = False
    if args.no_evidence:
        config["require_execution_evidence"] = False

    tasks_dir = Path(args.tasks_dir).expanduser()
    if not tasks_dir.is_dir():
        sys.stderr.write(f"error: tasks directory does not exist: {tasks_dir}\n")
        return EXIT_USAGE

    try:
        findings, warnings, scanned = lint_tasks(tasks_dir, args.task, config)
    except Exception as exc:
        sys.stderr.write(f"error: {exc}\n")
        return EXIT_USAGE

    errors = list(findings)
    if args.strict:
        for w in warnings:
            errors.append(
                Finding(
                    task=w.get("task", ""),
                    code=w.get("code", "STRICT_WARNING"),
                    message=w.get("message", ""),
                    file=w.get("file", "03-qa-verification.md"),
                    line=w.get("line", 0),
                )
            )

    passed = len(errors) == 0

    if args.json:
        payload = {
            "gate": "3",
            "passed": passed,
            "tasks_scanned": scanned,
            "tasks_audited": scanned,
            "errors": [f.to_dict() for f in errors],
            "warnings": warnings,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        if errors:
            sys.stdout.write(f"Gate 3 FAILED: {len(errors)} violation(s) in {scanned} task(s).\n")
            for f in errors:
                loc = f"{f.file}:{f.line}" if f.line else f.file
                sys.stdout.write(f"  [{f.task}] {f.code}: {f.message} ({loc})\n")
        else:
            sys.stdout.write(f"Gate 3 PASSED: verified {scanned} task(s) with signoff.\n")

        for w in warnings:
            loc = f"{w.get('file', '03-qa-verification.md')}:{w.get('line', 0)}"
            sys.stdout.write(f"  warning [{w.get('code', 'WARNING')}] {w.get('message', '')} ({loc})\n")

    return EXIT_PASS if passed else EXIT_VIOLATIONS


if __name__ == "__main__":
    sys.exit(main())
