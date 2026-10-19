#!/usr/bin/env python3
"""Gate 3 acceptance audit linter for QA verification artifacts (03-qa-verification.md).

Deterministic static checker for QA verification signoff:
- Cyclomatic Complexity (Section 3): V(G) <= 10, warnings 11-15, errors > 15, Basis Path >= V(G)
- Mutation Testing and MSI Audit (Section 4): every populated table must be compliant and the
  populated tables must agree on MSI/totals; numeric MSI >= 80% (>= 90% for risk_level: core)
- Execution Evidence (Section 5): Command and Result fields must not be blank
- Cross-validation (--actual-complexity): reported V(G) values are checked against the actual
  AST complexity report produced by complexity_check.py (WP-04)
- Cross-validation (--actual-mutation): reported Section 4 aggregates and per-target rows are
  checked against the normalized mutation report produced by mutation_gate.py; a missing or
  unusable report fails when --require-actual-mutation is set
- Provenance (--require-provenance): Section 5 artifact path/SHA-256 are verified against real
  files and every equivalent mutant must carry a justification
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

VERSION = "1.1.0"
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
    "require_provenance": False,
    "repo_root": ".",
    "actual_functions": None,
    "actual_mutation": None,
    "require_actual_mutation": False,
}

_MSI_RE = re.compile(
    r"(?:MSI|mutation\s+score(?:\s+indicator)?)[^\d]*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_KILLED_RE = re.compile(r"killed[^\d]*(\d+)", re.IGNORECASE)
_TOTAL_MUT_RE = re.compile(r"(?:total|generated)[^\d]*(\d+)\s+mutant", re.IGNORECASE)
_QA_PASSED_RE = re.compile(r"^[-*+]\s*\[[xX]\]\s*QA_PASSED\b")
_COMPLEXITY_HEADING_RE = re.compile(
    r"^#{2,4}\s*(?:\d+\.\s*)?Complexity\s+and\s+basis\s+path\s+coverage\b",
    re.IGNORECASE,
)
_MUTATION_HEADING_RE = re.compile(
    r"^#{2,4}\s*(?:\d+\.\s*)?Mutation\s+testing\b",
    re.IGNORECASE,
)
_EVIDENCE_HEADING_RE = re.compile(
    r"^#{2,4}\s*(?:\d+\.\s*)?Execution\s+evidence\b",
    re.IGNORECASE,
)
_RISK_LEVEL_RE = re.compile(
    r"^risk_level\s*:\s*[\"']?(standard|core)[\"']?\s*(?:#.*)?$",
    re.IGNORECASE | re.MULTILINE,
)
_TOUCH_PATH_RE = re.compile(r"^\s*path\s*:\s*(.+?)\s*$")
_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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


# ---------------------------------------------------------------------------
# Generic Markdown helpers
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _qa_passed_line(qa_text: str) -> Optional[int]:
    """Return the 1-based line number of the checked QA_PASSED verdict, if any."""
    for idx, line in enumerate(qa_text.splitlines(), 1):
        if _QA_PASSED_RE.match(line):
            return idx
    return None


def _collect_section(
    qa_text: str, heading_re: "re.Pattern[str]"
) -> Tuple[Optional[int], List[Tuple[int, str]]]:
    """Collect the lines that belong to the first section matching heading_re."""
    lines = qa_text.splitlines()
    in_section = False
    sec_line_num: Optional[int] = None
    section_lines: List[Tuple[int, str]] = []
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_section:
            if heading_re.match(stripped):
                in_section = True
                sec_line_num = line_idx
                continue
        else:
            if stripped.startswith("## ") or (
                stripped.startswith("### ") and not stripped.startswith("#### ")
            ):
                break
            section_lines.append((line_idx, line))
    return sec_line_num, section_lines


def _split_table_cells(line: str) -> List[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


def _is_separator_row(cells: Sequence[str]) -> bool:
    non_empty = [c for c in cells if c]
    if not non_empty:
        return False
    return all(_SEPARATOR_CELL_RE.match(c) for c in non_empty)


def _split_pipe_blocks(
    section_lines: Sequence[Tuple[int, str]]
) -> List[List[Tuple[int, List[str]]]]:
    """Group contiguous Markdown table lines into blocks of parsed cells."""
    blocks: List[List[Tuple[int, List[str]]]] = []
    current: List[Tuple[int, List[str]]] = []
    for line_no, line in section_lines:
        if line.strip().startswith("|"):
            current.append((line_no, _split_table_cells(line)))
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks


# ---------------------------------------------------------------------------
# Path and contract helpers
# ---------------------------------------------------------------------------


def _normalize_posix_path(path: str) -> str:
    normalized = str(path).strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _normalize_actual_path(raw: Any, repo_root: Optional[Path]) -> str:
    """Normalize an AST report path to a POSIX repo-relative path."""
    text = str(raw).strip().replace("\\", "/")
    candidate = Path(text)
    if candidate.is_absolute() and repo_root is not None:
        try:
            return _normalize_posix_path(os.path.relpath(candidate.resolve(), repo_root.resolve()))
        except (OSError, ValueError):
            return _normalize_posix_path(text)
    return _normalize_posix_path(text)


def _load_actual_complexity(
    report_path: Path, repo_root: Path
) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Load the WP-04 AST complexity report.

    Returns (records, "") on success or (None, error_message) on failure.
    """
    if not report_path.is_file():
        return None, f"actual complexity report not found: {report_path}"
    text = _read_text(report_path)
    if text is None:
        return None, f"actual complexity report is unreadable: {report_path}"
    if not text.strip():
        return None, f"actual complexity report is empty: {report_path}"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"actual complexity report is not valid JSON: {exc}"
    if not isinstance(payload, dict) or not isinstance(payload.get("functions"), list):
        return None, (
            "actual complexity report must be a JSON object with a 'functions' list "
            f"(schema: {{'functions': [{{'file', 'line', 'function', 'vg'}}]}}): {report_path}"
        )
    records: List[Dict[str, Any]] = []
    for entry in payload["functions"]:
        if not isinstance(entry, dict):
            continue
        file_raw = entry.get("file")
        function_raw = entry.get("function")
        vg_raw = entry.get("vg")
        if not isinstance(file_raw, str) or not isinstance(function_raw, str):
            continue
        try:
            vg = int(vg_raw)
        except (TypeError, ValueError):
            continue
        function_name = function_raw.strip()
        if not function_name:
            continue
        records.append(
            {
                "file": _normalize_actual_path(file_raw, repo_root),
                "line": entry.get("line", 0),
                "function": function_name,
                "vg": vg,
            }
        )
    return records, ""


def _read_risk_level(task_dir: Path) -> str:
    """Read the optional contract risk_level (standard | core). Default: standard."""
    contract_text = _read_text(task_dir / "01-contract.md")
    if not contract_text:
        return "standard"
    match = _RISK_LEVEL_RE.search(contract_text)
    if not match:
        return "standard"
    risk_level = match.group(1).lower()
    return risk_level if risk_level in ("standard", "core") else "standard"


def _read_touch_files(
    task_name: str,
    task_dir: Path,
    warnings: Optional[List[Dict[str, Any]]],
) -> Optional[Set[str]]:
    """Read touch_files[].path values from 01-contract.md.

    Returns a set of POSIX repo-relative paths, or None when the contract cannot
    be read. None is accompanied by a TOUCH_FILES_UNREADABLE warning so the
    cross-check never fails silently.
    """
    def _warn(message: str) -> None:
        if warnings is not None:
            warnings.append(
                {
                    "task": task_name,
                    "code": "TOUCH_FILES_UNREADABLE",
                    "message": message,
                    "file": "01-contract.md",
                    "line": 0,
                }
            )

    contract_text = _read_text(task_dir / "01-contract.md")
    if contract_text is None:
        _warn(
            "01-contract.md is missing or unreadable; the complexity cross-check cannot "
            "restrict the actual report to touch_files"
        )
        return None

    block_match = re.search(r"^touch_files\s*:\s*(?:#.*)?$", contract_text, re.MULTILINE)
    if not block_match:
        empty_match = re.search(
            r"^touch_files\s*:\s*\[\s*\]\s*(?:#.*)?$", contract_text, re.MULTILINE
        )
        if empty_match:
            return set()
        _warn(
            "01-contract.md has no readable touch_files block; the complexity cross-check "
            "cannot restrict the actual report to touch_files"
        )
        return None

    paths: Set[str] = set()
    for raw_line in contract_text[block_match.end():].splitlines():
        if not raw_line.strip():
            continue
        if not raw_line[:1].isspace():
            break
        path_match = _TOUCH_PATH_RE.match(raw_line)
        if not path_match:
            continue
        value = re.sub(r"\s+#.*$", "", path_match.group(1)).strip()
        value = value.strip("`\"' ")
        if value and not value.startswith("{{"):
            paths.add(_normalize_posix_path(value))
    if not paths:
        _warn(
            "01-contract.md touch_files block has no 'path:' entries; the complexity "
            "cross-check cannot restrict the actual report to touch_files"
        )
        return None
    return paths


# ---------------------------------------------------------------------------
# Section 3: complexity and basis path coverage
# ---------------------------------------------------------------------------


def _count_test_cases(cases_raw: str) -> int:
    cleaned = cases_raw.strip()
    if cleaned.lower() in ("none", "n/a", "-", ""):
        return 0
    tc_tokens = re.findall(r"\b(?:TC|test|case)[-\w]*\b", cleaned, re.IGNORECASE)
    comma_items = [item.strip() for item in re.split(r"[,;\n]+", cleaned) if item.strip()]
    return max(len(tc_tokens), len(comma_items))


def _parse_complexity_section(
    qa_text: str,
) -> Tuple[Optional[int], List[Dict[str, Any]]]:
    """Parse Section 3 rows: [{line, function, vg, test_count}]."""
    sec_line_num, section_lines = _collect_section(qa_text, _COMPLEXITY_HEADING_RE)
    if sec_line_num is None:
        return None, []

    header_idx = -1
    col_headers: List[str] = []
    separator_found = False
    data_rows: List[Tuple[int, List[str]]] = []

    for idx, (line_no, line) in enumerate(section_lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_table_cells(stripped)
        if header_idx == -1:
            lowered = [c.lower() for c in cells]
            if any("complexity" in c or "v(g)" in c for c in lowered):
                header_idx = idx
                col_headers = lowered
                continue
        elif not separator_found:
            if _is_separator_row(cells):
                separator_found = True
                continue
        else:
            if any(c for c in cells):
                data_rows.append((line_no, cells))

    if not data_rows:
        return sec_line_num, []

    func_col = 0
    vg_col = 1
    cases_col = 3
    for i, header in enumerate(col_headers):
        if "function" in header or "module" in header or "target" in header:
            func_col = i
        elif "v(g)" in header or "cyclomatic" in header or "complexity" in header:
            vg_col = i
        elif (
            "test case" in header
            or "mapped test" in header
            or "test case id" in header
            or "test cases" in header
        ):
            cases_col = i

    rows: List[Dict[str, Any]] = []
    for line_no, cells in data_rows:
        function_name = cells[func_col] if func_col < len(cells) else ""
        function_name = function_name.strip("`\"' ")
        if not function_name:
            function_name = "unknown"

        vg_raw = cells[vg_col] if vg_col < len(cells) else ""
        vg_match = re.search(r"\b(\d+)\b", vg_raw)
        vg = int(vg_match.group(1)) if vg_match else None

        cases_raw = cells[cases_col] if cases_col < len(cells) else ""
        rows.append(
            {
                "line": line_no,
                "function": function_name,
                "vg": vg,
                "test_count": _count_test_cases(cases_raw),
            }
        )
    return sec_line_num, rows


def _index_actual_vg(actual_functions: Optional[List[Dict[str, Any]]]) -> Dict[str, List[int]]:
    index: Dict[str, List[int]] = {}
    for record in actual_functions or []:
        index.setdefault(record["function"], []).append(record["vg"])
    return index


def _lint_qa_complexity(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    warnings: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
    actual_vg_by_function: Optional[Dict[str, List[int]]] = None,
) -> None:
    """Audit Section 3: Cyclomatic complexity and basis path coverage."""
    qa_text = _read_text(task_dir / "03-qa-verification.md")
    if qa_text is None:
        return

    verdict_line_num = _qa_passed_line(qa_text)
    if verdict_line_num is None:
        return

    sec_line_num, rows = _parse_complexity_section(qa_text)
    if sec_line_num is None:
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

    if not rows:
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

    cfg = config or DEFAULT_CONFIG
    max_std = cfg.get("max_vg_standard", 10)
    max_warn = cfg.get("max_vg_warning", 15)

    for row in rows:
        fn_name = row["function"]
        vg = row["vg"]

        if vg is not None:
            if vg > max_warn:
                findings.append(
                    Finding(
                        task_name,
                        "COMPLEXITY_EXCEEDS_MAX_THRESHOLD",
                        f"Function {fn_name!r} has cyclomatic complexity V(G)={vg} exceeding maximum threshold of {max_warn}",
                        "03-qa-verification.md",
                        row["line"],
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
                            "line": row["line"],
                        }
                    )

        # Basis path coverage must be measured against the ACTUAL AST V(G) when available.
        basis_vg = vg
        actual_vgs = (actual_vg_by_function or {}).get(fn_name)
        if actual_vgs:
            basis_vg = max(actual_vgs)

        test_count = row["test_count"]
        if basis_vg is not None and test_count < basis_vg:
            message = (
                f"Function {fn_name!r} has V(G)={basis_vg} but only {test_count} test case(s) "
                "provided (basis path testing requires >= V(G))"
            )
            if actual_vgs and vg is not None and basis_vg != vg:
                message += " [basis path measured against actual AST V(G)]"
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_BASIS_PATH_INSUFFICIENT",
                    message,
                    "03-qa-verification.md",
                    row["line"],
                )
            )


def _cross_check_complexity(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    warnings: Optional[List[Dict[str, Any]]],
    actual_functions: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Cross-check Section 3 against the actual AST complexity report."""
    qa_text = _read_text(task_dir / "03-qa-verification.md")
    if qa_text is None or _qa_passed_line(qa_text) is None:
        return

    sec_line_num, rows = _parse_complexity_section(qa_text)
    if not rows:
        # Missing/empty Section 3 is already reported by the complexity audit.
        return

    touch_files = _read_touch_files(task_name, task_dir, warnings)

    actual_by_function: Dict[str, List[Dict[str, Any]]] = {}
    for record in actual_functions:
        actual_by_function.setdefault(record["function"], []).append(record)

    if touch_files is not None:
        reported_names = {row["function"] for row in rows}
        reported_missing: Set[str] = set()
        for record in actual_functions:
            fn_name = record["function"]
            if record["file"] not in touch_files:
                continue
            if fn_name in reported_names or fn_name in reported_missing:
                continue
            reported_missing.add(fn_name)
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_FUNCTION_MISSING_IN_03",
                    f"Actual AST report lists function {fn_name!r} in touch_files path {record['file']!r} "
                    "(V(G)="
                    f"{record['vg']}) but Section 3 has no row for it",
                    "03-qa-verification.md",
                    sec_line_num,
                )
            )

    for row in rows:
        fn_name = row["function"]
        matches = actual_by_function.get(fn_name)
        if not matches:
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_PHANTOM_FUNCTION",
                    f"Section 3 row for function {fn_name!r} does not exist in the actual AST complexity report",
                    "03-qa-verification.md",
                    row["line"],
                )
            )
            continue
        actual_vgs = sorted({record["vg"] for record in matches})
        if row["vg"] is None or row["vg"] not in actual_vgs:
            source_files = ", ".join(sorted({record["file"] for record in matches}))
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_MISMATCH_WITH_AST",
                    f"Section 3 reports V(G)={row['vg']} for function {fn_name!r} but the actual AST report "
                    f"reports V(G)={actual_vgs} ({source_files})",
                    "03-qa-verification.md",
                    row["line"],
                )
            )


# ---------------------------------------------------------------------------
# Section 4: mutation testing and MSI audit
# ---------------------------------------------------------------------------


def _parse_float_cell(raw: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)", raw or "")
    return float(match.group(1)) if match else None


def _parse_int_cell(raw: str) -> Optional[int]:
    match = re.search(r"(\d+)", raw or "")
    return int(match.group(1)) if match else None


def _kv_metrics(values: Dict[str, str]) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "msi": None,
        "total": None,
        "killed": None,
        "timed_out": None,
        "equivalent": None,
        "survived": None,
    }
    for key, value in values.items():
        if "justif" in key or "reason" in key:
            continue
        if "msi" in key or "mutation score" in key:
            metrics["msi"] = _parse_float_cell(value)
        elif "total" in key:
            metrics["total"] = _parse_int_cell(value)
        elif "killed" in key or "kill" in key:
            metrics["killed"] = _parse_int_cell(value)
        elif "timed" in key or "timeout" in key:
            metrics["timed_out"] = _parse_int_cell(value)
        elif "equivalent" in key:
            metrics["equivalent"] = _parse_int_cell(value)
        elif "survived" in key:
            metrics["survived"] = _parse_int_cell(value)
    return metrics


def _per_target_metrics(
    col_headers: List[str], rows: List[List[str]]
) -> Dict[str, Any]:
    columns: Dict[str, int] = {}
    for idx, header in enumerate(col_headers):
        if "total" in header and "total" not in columns:
            columns["total"] = idx
        elif ("killed" in header or "kill" in header) and "killed" not in columns:
            columns["killed"] = idx
        elif "survived" in header and "survived" not in columns:
            columns["survived"] = idx
        elif ("timeout" in header or "timed" in header) and "timed_out" not in columns:
            columns["timed_out"] = idx
        elif "equivalent" in header and "equivalent" not in columns:
            columns["equivalent"] = idx
        elif ("msi" in header or "score" in header) and "msi" not in columns:
            columns["msi"] = idx

    totals: Dict[str, Optional[int]] = {key: None for key in columns if key != "msi"}
    for cells in rows:
        for key, idx in columns.items():
            if key == "msi":
                continue
            if idx >= len(cells):
                continue
            value = _parse_int_cell(cells[idx])
            if value is None:
                continue
            totals[key] = (totals[key] or 0) + value

    metrics: Dict[str, Any] = {"msi": None}
    for key in ("total", "killed", "timed_out", "equivalent", "survived"):
        metrics[key] = totals.get(key)

    total = metrics.get("total")
    killed = metrics.get("killed")
    timed_out = metrics.get("timed_out")
    equivalent = metrics.get("equivalent")
    survived = metrics.get("survived")
    if total is not None and killed is not None:
        denominator = total - (equivalent or 0)
        if denominator > 0:
            metrics["msi"] = round((killed + (timed_out or 0)) / denominator * 100, 4)
        elif (survived or 0) == 0:
            metrics["msi"] = 100.0
        else:
            metrics["msi"] = 0.0
    return metrics


def _parse_mutation_table_block(
    block: Sequence[Tuple[int, str]]
) -> Optional[Tuple[str, List[str], List[Tuple[int, List[str]]]]]:
    """Parse one contiguous Markdown table into (format, headers, data_rows)."""
    header_idx = -1
    col_headers: List[str] = []
    separator_found = False
    data_rows: List[Tuple[int, List[str]]] = []

    for idx, (line_no, line) in enumerate(block):
        stripped = line.strip()
        cells = _split_table_cells(stripped)
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
                next_cells = _split_table_cells(block[idx + 1][1].strip())
                if next_cells and _is_separator_row(next_cells):
                    header_idx = idx
                    col_headers = lowered
                    continue
        elif not separator_found:
            if _is_separator_row(cells):
                separator_found = True
                continue
        else:
            data_rows.append((line_no, cells))

    if not col_headers or not separator_found:
        return None

    is_kv_format = (
        len(col_headers) == 2
        and any("metric" in c or "field" in c for c in col_headers)
        and any("value" in c for c in col_headers)
    )
    return ("kv" if is_kv_format else "per_target"), col_headers, data_rows


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

    qa_text = _read_text(task_dir / "03-qa-verification.md")
    if qa_text is None:
        return

    verdict_line_num = _qa_passed_line(qa_text)
    if verdict_line_num is None:
        return

    sec_line_num, section_lines = _collect_section(qa_text, _MUTATION_HEADING_RE)
    if sec_line_num is None:
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

    raw_tables: List[List[Tuple[int, str]]] = []
    current_block: List[Tuple[int, str]] = []
    for line_no, line in section_lines:
        if line.strip().startswith("|"):
            current_block.append((line_no, line))
        else:
            if current_block:
                raw_tables.append(current_block)
                current_block = []
    if current_block:
        raw_tables.append(current_block)

    risk_level = _read_risk_level(task_dir)
    base_min_msi = float(cfg.get("min_msi", 80))
    if risk_level == "core":
        min_msi = max(base_min_msi, 90.0)
        threshold_label = f"{min_msi:.0f}% threshold for core module (risk_level: core)"
    else:
        min_msi = base_min_msi
        threshold_label = f"{min_msi:.0f}% threshold"

    table_results: List[Dict[str, Any]] = []

    for block in raw_tables:
        parsed = _parse_mutation_table_block(block)
        if parsed is None:
            continue
        table_format, col_headers, data_rows = parsed
        table_line = block[0][0]

        table_findings: List[Finding] = []
        compliant_rows = 0

        if table_format == "kv":
            kv_data_rows = [
                (line_no, cells)
                for line_no, cells in data_rows
                if len(cells) >= 2 and cells[1].strip()
            ]
            values: Dict[str, str] = {}
            for line_no, cells in data_rows:
                if len(cells) < 2:
                    continue
                values[cells[0].lower()] = cells[1].strip()
            metrics = _kv_metrics(values)

            if not kv_data_rows:
                table_results.append(
                    {
                        "format": "kv",
                        "has_data": False,
                        "compliant": False,
                        "findings": [],
                        "metrics": metrics,
                        "line": table_line,
                    }
                )
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
                        table_findings.append(
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
                            table_findings.append(
                                Finding(
                                    task_name,
                                    "QA_INVALID_MSI_SCORE",
                                    f"Mutation Score Indicator (MSI) {msi_score:.1f}% is below required {threshold_label}",
                                    "03-qa-verification.md",
                                    line_no,
                                )
                            )
                        else:
                            compliant_rows += 1
            if not msi_found:
                table_findings.append(
                    Finding(
                        task_name,
                        "QA_INVALID_MSI_SCORE",
                        "Missing Mutation Score Indicator (MSI) metric in mutation audit table",
                        "03-qa-verification.md",
                        sec_line_num,
                    )
                )

            table_results.append(
                {
                    "format": "kv",
                    "has_data": True,
                    "compliant": len(table_findings) == 0 and compliant_rows > 0,
                    "findings": table_findings,
                    "metrics": metrics,
                    "line": table_line,
                }
            )
        else:
            file_col = 0
            msi_col = -1
            for i, header in enumerate(col_headers):
                if "file" in header or "target" in header or "source" in header:
                    file_col = i
                elif "msi" in header or "score" in header:
                    msi_col = i
            if msi_col == -1:
                msi_col = 7 if len(col_headers) > 7 else len(col_headers) - 2

            target_data_rows = []
            for line_no, cells in data_rows:
                target_file = (
                    cells[file_col].strip("`\"' ") if file_col < len(cells) else ""
                )
                msi_raw = cells[msi_col].strip() if msi_col < len(cells) else ""
                if any(c.strip() for c in cells) and (bool(target_file) or bool(msi_raw)):
                    target_data_rows.append((line_no, cells, target_file, msi_raw))

            metrics = _per_target_metrics(
                col_headers, [cells for _, cells, _, _ in target_data_rows]
            )

            if not target_data_rows:
                table_results.append(
                    {
                        "format": "per_target",
                        "has_data": False,
                        "compliant": False,
                        "findings": [],
                        "metrics": metrics,
                        "line": table_line,
                    }
                )
                continue

            for line_no, cells, target_file, msi_raw in target_data_rows:
                tf_display = target_file if target_file else "unknown"
                score_match = re.search(r"(\d+(?:\.\d+)?)\s*%?", msi_raw)
                if not score_match:
                    table_findings.append(
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
                        table_findings.append(
                            Finding(
                                task_name,
                                "QA_INVALID_MSI_SCORE",
                                f"Target file {tf_display!r} has MSI score {score:.1f}% below required {threshold_label}",
                                "03-qa-verification.md",
                                line_no,
                            )
                        )
                    else:
                        compliant_rows += 1

            table_results.append(
                {
                    "format": "per_target",
                    "has_data": True,
                    "compliant": len(table_findings) == 0 and compliant_rows > 0,
                    "findings": table_findings,
                    "metrics": metrics,
                    "line": table_line,
                }
            )

    data_tables = [t for t in table_results if t["has_data"]]
    if not data_tables:
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
                        f"Mutation Score Indicator (MSI) {msi_score:.1f}% is below required {threshold_label}",
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
                        f"Derived MSI {msi_score:.1f}% ({killed}/{total}) is below required {threshold_label}",
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

    # Every populated mutation table must be compliant; a compliant table can no
    # longer mask a failing or blank one (dual-table loophole).
    blank_tables = [t for t in table_results if not t["has_data"]]
    if blank_tables and len(table_results) >= 2:
        findings.append(
            Finding(
                task_name,
                "MUTATION_TABLE_INCONSISTENT",
                "Section 4 contains multiple mutation tables but at least one table has no data rows; "
                "fill every mutation table (or delete the unused scaffold) so the evidence can be cross-checked",
                "03-qa-verification.md",
                blank_tables[0].get("line", sec_line_num),
            )
        )

    if len(data_tables) >= 2:
        base_table = data_tables[0]
        for other_table in data_tables[1:]:
            base_msi = base_table["metrics"].get("msi")
            other_msi = other_table["metrics"].get("msi")
            if base_msi is not None and other_msi is not None:
                if abs(float(base_msi) - float(other_msi)) > 0.1:
                    findings.append(
                        Finding(
                            task_name,
                            "MUTATION_TABLE_INCONSISTENT",
                            "Section 4 mutation tables disagree on MSI: "
                            f"{float(base_msi):.1f}% vs {float(other_msi):.1f}%",
                            "03-qa-verification.md",
                            base_table.get("line", sec_line_num),
                        )
                    )
            base_total = base_table["metrics"].get("total")
            other_total = other_table["metrics"].get("total")
            if base_total is not None and other_total is not None:
                if int(base_total) != int(other_total):
                    findings.append(
                        Finding(
                            task_name,
                            "MUTATION_TABLE_INCONSISTENT",
                            "Section 4 mutation tables disagree on total mutants: "
                            f"{int(base_total)} vs {int(other_total)}",
                            "03-qa-verification.md",
                            base_table.get("line", sec_line_num),
                        )
                    )

    for table in data_tables:
        if table["compliant"]:
            continue
        if table["findings"]:
            findings.extend(table["findings"])
        else:
            findings.append(
                Finding(
                    task_name,
                    "QA_MISSING_MUTATION_EVIDENCE",
                    "Section 4 mutation table is incomplete or non-compliant",
                    "03-qa-verification.md",
                    table.get("line", sec_line_num),
                )
            )


# ---------------------------------------------------------------------------
# Section 4 cross-validation: normalized mutation report
# ---------------------------------------------------------------------------

_MUTATION_COUNT_FIELDS = ("total", "killed", "timed_out", "equivalent", "survived")

_MUTATION_FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "total": ("total", "total_mutants", "mutants"),
    "killed": ("killed", "killed_mutants"),
    "timed_out": ("timed_out", "timeout", "timedout"),
    "equivalent": ("equivalent", "equivalent_mutants"),
    "survived": ("survived", "survived_mutants"),
}

_MSI_FIELD_KEYS = ("msi", "mutation_score", "mutation_score_indicator", "score")


def _parse_report_count(raw: Any) -> Optional[int]:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw if raw >= 0 else None
    if isinstance(raw, str):
        match = re.search(r"(\d+)", raw)
        return int(match.group(1)) if match else None
    return None


def _parse_report_msi(raw: Any) -> Optional[float]:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        match = re.search(r"(\d+(?:\.\d+)?)", raw)
        return float(match.group(1)) if match else None
    return None


def _compute_mutation_msi(values: Dict[str, Optional[int]]) -> Optional[float]:
    """MSI = (killed + timed_out) / (total - equivalent) * 100 (None when undefined)."""
    total = values.get("total")
    killed = values.get("killed")
    if total is None or killed is None:
        return None
    equivalent = values.get("equivalent") or 0
    timed_out = values.get("timed_out") or 0
    survived = values.get("survived") or 0
    denominator = total - equivalent
    if denominator <= 0:
        return 100.0 if survived == 0 else 0.0
    return round((killed + timed_out) / denominator * 100.0, 4)


def _target_identity(entry: Dict[str, Any], repo_root: Path) -> str:
    """Read a report target identity from file/path/name and normalize it."""
    for key in ("file", "path", "name", "target"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_actual_path(value, repo_root)
    return ""


def _target_basename(identity: str) -> str:
    return identity.rsplit("/", 1)[-1]


def _load_actual_mutation(
    report_path: Path, repo_root: Path
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Load the normalized mutation report produced by mutation_gate.py.

    Returns (report, "") on success or (None, error_message) on failure. The report
    contains the normalized ``targets`` list; per-target counts are optional as long
    as an MSI (or counts) can be recovered, and ``timeout``/``timed_out`` are aliases.
    """
    if not report_path.is_file():
        return None, f"actual mutation report not found: {report_path}"
    text = _read_text(report_path)
    if text is None:
        return None, f"actual mutation report is unreadable: {report_path}"
    if not text.strip():
        return None, f"actual mutation report is empty: {report_path}"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"actual mutation report is not valid JSON: {exc}"
    if not isinstance(payload, dict) or not isinstance(payload.get("targets"), list):
        return None, (
            "actual mutation report must be a JSON object with a 'targets' list "
            "(schema: {'targets': [{'file', 'total', 'killed', 'timed_out', "
            "'equivalent', 'survived'}]}): " + str(report_path)
        )
    if not payload["targets"]:
        return None, (
            "actual mutation report 'targets' list is empty; the mutation tool produced no "
            f"evidence: {report_path}"
        )

    records: List[Dict[str, Any]] = []
    for index, entry in enumerate(payload["targets"]):
        if not isinstance(entry, dict):
            return None, f"actual mutation report targets[{index}] must be an object"
        identity = _target_identity(entry, repo_root)
        if not identity:
            return None, (
                f"actual mutation report targets[{index}] must carry a non-empty "
                "'file'/'path'/'name' identity"
            )
        counts: Dict[str, Optional[int]] = {}
        for field in _MUTATION_COUNT_FIELDS:
            raw: Any = None
            for alias in _MUTATION_FIELD_ALIASES[field]:
                if alias in entry:
                    raw = entry[alias]
                    break
            counts[field] = _parse_report_count(raw)
        msi: Optional[float] = None
        for key in _MSI_FIELD_KEYS:
            if key in entry:
                msi = _parse_report_msi(entry[key])
                break
        if msi is None:
            msi = _compute_mutation_msi(counts)
        records.append({"target": identity, "counts": counts, "msi": msi})

    aggregate: Dict[str, Optional[float]] = {}
    for field in _MUTATION_COUNT_FIELDS:
        values = [record["counts"][field] for record in records]
        aggregate[field] = sum(values) if all(v is not None for v in values) else None
    aggregate["msi"] = _compute_mutation_msi(
        {field: aggregate[field] for field in _MUTATION_COUNT_FIELDS}  # type: ignore[arg-type]
    )
    if aggregate["msi"] is None:
        declared_msi = _parse_report_msi(payload.get("msi"))
        if declared_msi is not None:
            aggregate["msi"] = declared_msi
        elif len(records) == 1:
            aggregate["msi"] = records[0]["msi"]

    return {"targets": records, "aggregate": aggregate}, ""


def _mutation_table_columns(headers: Sequence[str]) -> Dict[str, int]:
    columns: Dict[str, int] = {}
    for idx, header in enumerate(headers):
        if "total" in header and "total" not in columns:
            columns["total"] = idx
        elif ("killed" in header or "kill" in header) and "killed" not in columns:
            columns["killed"] = idx
        elif "survived" in header and "survived" not in columns:
            columns["survived"] = idx
        elif ("timeout" in header or "timed" in header) and "timed_out" not in columns:
            columns["timed_out"] = idx
        elif "equivalent" in header and "equivalent" not in columns:
            columns["equivalent"] = idx
        elif ("msi" in header or "score" in header) and "msi" not in columns:
            columns["msi"] = idx
    return columns


def _parse_reported_mutation_evidence(
    section_lines: Sequence[Tuple[int, str]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Parse Section 4 into per-target rows and summary (kv) metrics."""
    target_rows: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {field: None for field in _MUTATION_COUNT_FIELDS}
    summary["msi"] = None

    raw_tables: List[List[Tuple[int, str]]] = []
    current_block: List[Tuple[int, str]] = []
    for line_no, line in section_lines:
        if line.strip().startswith("|"):
            current_block.append((line_no, line))
        elif current_block:
            raw_tables.append(current_block)
            current_block = []
    if current_block:
        raw_tables.append(current_block)

    for block in raw_tables:
        parsed = _parse_mutation_table_block(block)
        if parsed is None:
            continue
        table_format, headers, data_rows = parsed
        if table_format == "kv":
            values: Dict[str, str] = {}
            for _line_no, cells in data_rows:
                if len(cells) >= 2:
                    values[cells[0].lower()] = cells[1].strip()
            metrics = _kv_metrics(values)
            for key, value in metrics.items():
                if value is not None and summary.get(key) is None:
                    summary[key] = value
            continue

        columns = _mutation_table_columns(headers)
        file_col = 0
        for idx, header in enumerate(headers):
            if "file" in header or "target" in header or "source" in header:
                file_col = idx
                break
        msi_col = columns.get("msi")
        if msi_col is None:
            msi_col = 7 if len(headers) > 7 else len(headers) - 2

        for line_no, cells in data_rows:
            name = cells[file_col].strip("`\"' ") if file_col < len(cells) else ""
            msi_raw = cells[msi_col].strip() if 0 <= msi_col < len(cells) else ""
            if not any(cell.strip() for cell in cells) or (not name and not msi_raw):
                continue
            counts: Dict[str, Optional[int]] = {}
            for field in _MUTATION_COUNT_FIELDS:
                idx = columns.get(field)
                counts[field] = (
                    _parse_int_cell(cells[idx])
                    if idx is not None and idx < len(cells)
                    else None
                )
            msi = _parse_float_cell(msi_raw) if msi_raw else None
            if msi is None:
                msi = _compute_mutation_msi(counts)
            target_rows.append(
                {
                    "line": line_no,
                    "target": _normalize_posix_path(name),
                    "counts": counts,
                    "msi": msi,
                }
            )
    return target_rows, summary


def _cross_check_mutation(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    actual_report: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Cross-check Section 4 against the normalized mutation report (--actual-mutation)."""
    qa_text = _read_text(task_dir / "03-qa-verification.md")
    if qa_text is None or _qa_passed_line(qa_text) is None:
        return

    sec_line_num, section_lines = _collect_section(qa_text, _MUTATION_HEADING_RE)
    if sec_line_num is None:
        # The missing/blank Section 4 is already reported by the mutation audit.
        return

    target_rows, summary = _parse_reported_mutation_evidence(section_lines)
    report_targets = actual_report.get("targets") or []
    report_aggregate = actual_report.get("aggregate") or {}

    if target_rows:
        reported_aggregate: Dict[str, Any] = {}
        for field in _MUTATION_COUNT_FIELDS:
            values = [row["counts"].get(field) for row in target_rows]
            reported_aggregate[field] = sum(values) if all(v is not None for v in values) else None
        reported_aggregate["msi"] = _compute_mutation_msi(
            {field: reported_aggregate[field] for field in _MUTATION_COUNT_FIELDS}  # type: ignore[arg-type]
        )
    else:
        reported_aggregate = summary

    differences: List[str] = []
    for field in _MUTATION_COUNT_FIELDS:
        reported_value = reported_aggregate.get(field)
        actual_value = report_aggregate.get(field)
        if reported_value is None or actual_value is None:
            continue
        if int(reported_value) != int(actual_value):
            differences.append(f"{field}: 03 reports {int(reported_value)}, report has {int(actual_value)}")
    reported_msi = reported_aggregate.get("msi")
    actual_msi = report_aggregate.get("msi")
    if reported_msi is not None and actual_msi is not None:
        if abs(float(reported_msi) - float(actual_msi)) > 0.1:
            differences.append(
                f"MSI: 03 reports {float(reported_msi):.1f}%, report computed {float(actual_msi):.1f}%"
            )
    if differences:
        findings.append(
            Finding(
                task_name,
                "MUTATION_MISMATCH_WITH_REPORT",
                "Section 4 aggregate mutation evidence does not match the actual mutation report ("
                + "; ".join(differences)
                + ")",
                "03-qa-verification.md",
                sec_line_num,
            )
        )

    # Per-target rows must exist in and agree with the report.
    report_by_identity = {record["target"]: record for record in report_targets}
    matched_identities: Set[str] = set()
    for row in target_rows:
        identity = row["target"]
        record = report_by_identity.get(identity)
        if record is None:
            basename = _target_basename(identity)
            candidates = [
                candidate
                for candidate in report_targets
                if candidate["target"] not in matched_identities
                and _target_basename(candidate["target"]) == basename
            ]
            if len(candidates) == 1:
                record = candidates[0]
        if record is None:
            findings.append(
                Finding(
                    task_name,
                    "MUTATION_PHANTOM_TARGET",
                    f"Section 4 lists mutation target {identity or 'unknown'!r} that does not exist "
                    "in the actual mutation report",
                    "03-qa-verification.md",
                    row["line"],
                )
            )
            continue

        matched_identities.add(record["target"])
        target_differences: List[str] = []
        for field in _MUTATION_COUNT_FIELDS:
            reported_value = row["counts"].get(field)
            actual_value = (record.get("counts") or {}).get(field)
            if reported_value is None or actual_value is None:
                continue
            if int(reported_value) != int(actual_value):
                target_differences.append(
                    f"{field}: 03 reports {int(reported_value)}, report has {int(actual_value)}"
                )
        if (
            row["msi"] is not None
            and record.get("msi") is not None
            and abs(float(row["msi"]) - float(record["msi"])) > 0.1
        ):
            target_differences.append(
                f"MSI: 03 reports {float(row['msi']):.1f}%, report computes "
                f"{float(record['msi']):.1f}%"
            )
        if target_differences:
            findings.append(
                Finding(
                    task_name,
                    "MUTATION_MISMATCH_WITH_REPORT",
                    f"Section 4 row for target {identity!r} does not match the actual mutation "
                    "report (" + "; ".join(target_differences) + ")",
                    "03-qa-verification.md",
                    row["line"],
                )
            )

    for record in report_targets:
        if record["target"] in matched_identities:
            continue
        findings.append(
            Finding(
                task_name,
                "MUTATION_TARGET_MISSING_IN_03",
                f"Actual mutation report lists target {record['target']!r} but Section 4 has no "
                "row for it",
                "03-qa-verification.md",
                sec_line_num,
            )
        )


# ---------------------------------------------------------------------------
# Section 4 provenance: equivalent mutants + Section 5 artifact provenance
# ---------------------------------------------------------------------------


def _parse_kv_rows(
    section_lines: Sequence[Tuple[int, str]]
) -> List[Tuple[int, str, str]]:
    """Parse table rows as (line_no, key, value) pairs; skip separators."""
    rows: List[Tuple[int, str, str]] = []
    for line_no, line in section_lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_table_cells(stripped)
        if len(cells) < 2:
            continue
        if _is_separator_row(cells):
            continue
        key = cells[0].strip().strip("`* ")
        value = cells[1].strip().strip("`\"' ")
        rows.append((line_no, key, value))
    return rows


def _equivalent_mutant_total(
    section_lines: Sequence[Tuple[int, str]]
) -> Optional[int]:
    """Return the reported equivalent-mutant count from Section 4, if determinable."""
    for _line_no, key, value in _parse_kv_rows(section_lines):
        lowered = key.lower()
        if "equivalent" not in lowered or "justif" in lowered or "reason" in lowered:
            continue
        count = _parse_int_cell(value)
        if count is not None:
            return count

    total: Optional[int] = None
    for block in _split_pipe_blocks(section_lines):
        header: Optional[List[str]] = None
        equivalent_col: Optional[int] = None
        for _line_no, cells in block:
            lowered = [c.lower() for c in cells]
            if header is None:
                if any("equivalent" in c for c in lowered) and any(
                    "total" in c for c in lowered
                ):
                    header = lowered
                    equivalent_col = next(
                        (i for i, c in enumerate(lowered) if "equivalent" in c), None
                    )
                continue
            if _is_separator_row(cells) or equivalent_col is None:
                continue
            if equivalent_col >= len(cells):
                continue
            count = _parse_int_cell(cells[equivalent_col])
            if count is not None:
                total = (total or 0) + count
    return total


def _audit_provenance(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Verify evidence provenance (--require-provenance) and equivalent-mutant justifications."""
    cfg = config or DEFAULT_CONFIG
    if not cfg.get("require_provenance", False):
        return

    qa_text = _read_text(task_dir / "03-qa-verification.md")
    if qa_text is None:
        return
    verdict_line_num = _qa_passed_line(qa_text)
    if verdict_line_num is None:
        return

    repo_root = Path(cfg.get("repo_root", "."))

    # --- Section 5: artifact path + SHA-256 ---------------------------------
    sec_line_num, evidence_lines = _collect_section(qa_text, _EVIDENCE_HEADING_RE)
    if sec_line_num is None:
        findings.append(
            Finding(
                task_name,
                "EVIDENCE_MISSING_ARTIFACT",
                "Section 5 'Execution evidence' is required by --require-provenance to record "
                "'Artifact path' and 'Artifact SHA-256'",
                "03-qa-verification.md",
                verdict_line_num,
            )
        )
    else:
        kv_rows = _parse_kv_rows(evidence_lines)
        artifact_row = next(
            (
                row
                for row in kv_rows
                if "artifact" in row[1].lower() and "path" in row[1].lower()
            ),
            None,
        )
        hash_row = next(
            (
                row
                for row in kv_rows
                if "artifact" in row[1].lower()
                and ("sha" in row[1].lower() or "hash" in row[1].lower())
            ),
            None,
        )

        artifact_path: Optional[Path] = None
        if artifact_row is None or not artifact_row[2]:
            findings.append(
                Finding(
                    task_name,
                    "EVIDENCE_MISSING_ARTIFACT",
                    "Section 5 must contain a non-empty 'Artifact path' row (--require-provenance)",
                    "03-qa-verification.md",
                    artifact_row[0] if artifact_row else sec_line_num,
                )
            )
        else:
            raw_path = artifact_row[2]
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = repo_root / candidate
            if not candidate.is_file():
                findings.append(
                    Finding(
                        task_name,
                        "EVIDENCE_MISSING_ARTIFACT",
                        f"Artifact path {raw_path!r} does not exist relative to repo root {str(repo_root)!r}",
                        "03-qa-verification.md",
                        artifact_row[0],
                    )
                )
            else:
                artifact_path = candidate

        if hash_row is None or not hash_row[2]:
            findings.append(
                Finding(
                    task_name,
                    "EVIDENCE_HASH_INVALID",
                    "Section 5 must contain a non-empty 'Artifact SHA-256' row (--require-provenance)",
                    "03-qa-verification.md",
                    hash_row[0] if hash_row else sec_line_num,
                )
            )
        else:
            digest = hash_row[2].strip().lower()
            if digest.startswith("sha256:"):
                digest = digest[len("sha256:"):].strip()
            digest = digest.strip("`'\" ")
            if not _SHA256_HEX_RE.match(digest):
                findings.append(
                    Finding(
                        task_name,
                        "EVIDENCE_HASH_INVALID",
                        f"Artifact SHA-256 {hash_row[2]!r} is not a 64-character hexadecimal digest",
                        "03-qa-verification.md",
                        hash_row[0],
                    )
                )
            elif artifact_path is not None:
                try:
                    actual_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                except OSError:
                    actual_digest = ""
                if actual_digest != digest:
                    findings.append(
                        Finding(
                            task_name,
                            "EVIDENCE_HASH_INVALID",
                            f"Artifact SHA-256 mismatch: 03 records {digest} but the file digest is "
                            f"{actual_digest or 'unreadable'}",
                            "03-qa-verification.md",
                            hash_row[0],
                        )
                    )

    # --- Section 4: equivalent-mutant justification --------------------------
    mut_sec_line, mut_lines = _collect_section(qa_text, _MUTATION_HEADING_RE)
    if mut_sec_line is not None:
        equivalent_total = _equivalent_mutant_total(mut_lines)
        if equivalent_total is not None and equivalent_total > 0:
            justification_row = next(
                (
                    row
                    for row in _parse_kv_rows(mut_lines)
                    if "equivalent" in row[1].lower()
                    and ("justif" in row[1].lower() or "reason" in row[1].lower())
                ),
                None,
            )
            if justification_row is None or not justification_row[2]:
                findings.append(
                    Finding(
                        task_name,
                        "MUTATION_EQUIVALENT_JUSTIFICATION_MISSING",
                        f"Section 4 reports {equivalent_total} equivalent mutant(s) but no non-empty "
                        "'Equivalent mutant justification' row",
                        "03-qa-verification.md",
                        justification_row[0] if justification_row else mut_sec_line,
                    )
                )


# ---------------------------------------------------------------------------
# Section 5: execution evidence
# ---------------------------------------------------------------------------


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

    qa_text = _read_text(task_dir / "03-qa-verification.md")
    if qa_text is None:
        return

    if _qa_passed_line(qa_text) is None:
        return

    sec_line_num, section_lines = _collect_section(qa_text, _EVIDENCE_HEADING_RE)
    if sec_line_num is None:
        return  # Execution evidence section is optional if omitted

    body_text = "\n".join(line for _, line in section_lines)
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


# ---------------------------------------------------------------------------
# Task bundle orchestration
# ---------------------------------------------------------------------------


def lint_task_bundle(
    task_dir: Path,
    findings: List[Finding],
    warnings: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Run all Gate 3 verification audits on a single task bundle."""
    cfg = config or DEFAULT_CONFIG
    task_name = task_dir.name
    actual_functions = cfg.get("actual_functions")
    actual_vg_by_function = (
        _index_actual_vg(actual_functions) if actual_functions is not None else None
    )

    _lint_qa_complexity(
        task_name, task_dir, findings, warnings, cfg, actual_vg_by_function
    )
    if actual_functions is not None:
        _cross_check_complexity(
            task_name, task_dir, findings, warnings, actual_functions, cfg
        )
    _lint_qa_mutation(task_name, task_dir, findings, warnings, cfg)
    actual_mutation = cfg.get("actual_mutation")
    if actual_mutation is not None and cfg.get("require_mutation_section", True):
        _cross_check_mutation(task_name, task_dir, findings, actual_mutation, cfg)
    _audit_execution_evidence(task_name, task_dir, findings, cfg)
    _audit_provenance(task_name, task_dir, findings, cfg)


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
            [
                d
                for d in tasks_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".") and d.name != "archive"
            ]
        )

    for task_dir in task_dirs:
        qa_file = task_dir / "03-qa-verification.md"
        if qa_file.is_file():
            scanned += 1
            lint_task_bundle(task_dir, findings, warnings, config)

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
        "--actual-complexity",
        default=None,
        metavar="PATH",
        help="path to the actual AST complexity report (JSON with a 'functions' list) produced by complexity_check.py",
    )
    parser.add_argument(
        "--require-actual-complexity",
        action="store_true",
        help="fail when --actual-complexity is missing so Gate 3 cannot rely on self-reported V(G) values",
    )
    parser.add_argument(
        "--actual-mutation",
        default=None,
        metavar="PATH",
        help="path to the actual normalized mutation report (JSON with a 'targets' list) produced by mutation_gate.py",
    )
    parser.add_argument(
        "--require-actual-mutation",
        action="store_true",
        help="fail when --actual-mutation is missing or unusable so Gate 3 cannot rely on self-reported MSI",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        metavar="PATH",
        help="repository root used to resolve artifact paths and normalize report paths (default: .)",
    )
    parser.add_argument(
        "--require-provenance",
        action="store_true",
        help="require Section 5 artifact path/SHA-256 provenance and equivalent-mutant justifications",
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

    repo_root = Path(args.repo_root).expanduser()
    if not repo_root.is_dir():
        sys.stderr.write(f"error: repository root does not exist: {repo_root}\n")
        return EXIT_USAGE

    config = dict(DEFAULT_CONFIG)
    if args.min_msi is not None:
        config["min_msi"] = args.min_msi
    if args.no_mutation:
        config["require_mutation_section"] = False
    if args.no_evidence:
        config["require_execution_evidence"] = False
    config["require_provenance"] = bool(args.require_provenance)
    config["repo_root"] = str(repo_root)

    global_findings: List[Finding] = []
    actual_functions: Optional[List[Dict[str, Any]]] = None
    if args.require_actual_complexity and not args.actual_complexity:
        global_findings.append(
            Finding(
                "",
                "COMPLEXITY_REPORT_MISSING",
                "--require-actual-complexity was set but --actual-complexity PATH was not provided; "
                "Gate 3 cannot cross-check reported V(G) values against the AST report",
                "actual-complexity-report.json",
                0,
            )
        )
    elif args.actual_complexity:
        report_path = Path(args.actual_complexity).expanduser()
        records, load_error = _load_actual_complexity(report_path, repo_root)
        if load_error:
            global_findings.append(
                Finding(
                    "",
                    "COMPLEXITY_REPORT_MISSING",
                    load_error,
                    str(report_path),
                    0,
                )
            )
        else:
            actual_functions = records
    config["actual_functions"] = actual_functions

    actual_mutation: Optional[Dict[str, Any]] = None
    if args.require_actual_mutation and not args.actual_mutation:
        global_findings.append(
            Finding(
                "",
                "MUTATION_REPORT_MISSING",
                "--require-actual-mutation was set but --actual-mutation PATH was not provided; "
                "Gate 3 cannot cross-check the reported MSI and mutant counts against the mutation report",
                "mutation-report.json",
                0,
            )
        )
    elif args.actual_mutation:
        mutation_report_path = Path(args.actual_mutation).expanduser()
        actual_mutation, load_error = _load_actual_mutation(mutation_report_path, repo_root)
        if load_error:
            global_findings.append(
                Finding(
                    "",
                    "MUTATION_REPORT_MISSING",
                    load_error,
                    str(mutation_report_path),
                    0,
                )
            )
    config["actual_mutation"] = actual_mutation

    tasks_dir = Path(args.tasks_dir).expanduser()
    if not tasks_dir.is_dir():
        sys.stderr.write(f"error: tasks directory does not exist: {tasks_dir}\n")
        return EXIT_USAGE

    try:
        findings, warnings, scanned = lint_tasks(tasks_dir, args.task, config)
    except Exception as exc:
        sys.stderr.write(f"error: {exc}\n")
        return EXIT_USAGE

    errors = list(global_findings) + list(findings)
    if args.strict:
        for warning in warnings:
            errors.append(
                Finding(
                    task=warning.get("task", ""),
                    code=warning.get("code", "STRICT_WARNING"),
                    message=warning.get("message", ""),
                    file=warning.get("file", "03-qa-verification.md"),
                    line=warning.get("line", 0),
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
            for finding in errors:
                loc = f"{finding.file}:{finding.line}" if finding.line else finding.file
                sys.stdout.write(f"  [{finding.task}] {finding.code}: {finding.message} ({loc})\n")
        else:
            sys.stdout.write(f"Gate 3 PASSED: verified {scanned} task(s) with signoff.\n")

        for warning in warnings:
            loc = f"{warning.get('file', '03-qa-verification.md')}:{warning.get('line', 0)}"
            sys.stdout.write(
                f"  warning [{warning.get('code', 'WARNING')}] {warning.get('message', '')} ({loc})\n"
            )

    return EXIT_PASS if passed else EXIT_VIOLATIONS


if __name__ == "__main__":
    sys.exit(main())
