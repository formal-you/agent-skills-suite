#!/usr/bin/env python3
"""McCabe Cyclomatic Complexity static checker (quality-engineering gate).

Multi-language static complexity analyzer powered by Tree-sitter
(https://github.com/tree-sitter/tree-sitter), with support for open-source
multi-language analyzers (Lizard) and standard Python AST fallback.

Supported languages:
  - Python (.py)
  - JavaScript / TypeScript (.js, .mjs, .cjs, .jsx, .ts, .tsx, .mts, .cts)
  - Go (.go)
  - Rust (.rs)
  - Java (.java)
  - C / C++ (.c, .cc, .cpp, .cxx, .h, .hpp)
  - C# (.cs)

Thresholds:
  V(G) <= 10       — standard (approved)
  11 <= V(G) <= 15 — warning (architectural justification required in 02)
  V(G) > 15        — critical (strictly prohibited; blocks gate)

Exit codes:
  0  all functions satisfy V(G) <= 15 (no critical violations)
  1  one or more critical violations (V(G) > 15)
  2  usage or configuration error
  3  unexpected internal error
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import warnings
from pathlib import Path

# Suppress deprecation warnings from third-party C-extensions if present
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Constants & Language Maps
# ---------------------------------------------------------------------------

STANDARD_THRESHOLD = 10
WARNING_THRESHOLD = 15

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".agents",
    "tests", ".github", "node_modules", "build", "dist",
}

EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
}

DECISION_NODE_TYPES = {
    "if_statement", "if_expression", "elif_clause", "else_if_clause",
    "for_statement", "for_expression", "for_in_statement",
    "while_statement", "while_expression", "loop_expression", "do_statement",
    "switch_case", "case_clause", "match_case", "match_arm", "case_statement",
    "expression_case", "type_case", "communication_case", "switch_rule",
    "catch_clause", "except_clause",
    "conditional_expression", "ternary_expression",
}

FUNCTION_NODE_TYPES = {
    "function_definition", "function_declaration", "function_expression",
    "arrow_function", "method_definition", "method_declaration",
    "function_item", "constructor_declaration",
}

LOGICAL_OPERATORS = {"&&", "||", "and", "or", "??"}

# Check library availability
_TREE_SITTER_AVAILABLE = False
try:
    import tree_sitter_languages  # type: ignore
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    try:
        import tree_sitter  # type: ignore
        _TREE_SITTER_AVAILABLE = True
    except ImportError:
        _TREE_SITTER_AVAILABLE = False

_LIZARD_AVAILABLE = False
try:
    import lizard  # type: ignore
    _LIZARD_AVAILABLE = True
except ImportError:
    _LIZARD_AVAILABLE = False


# ---------------------------------------------------------------------------
# Tree-sitter Engine Logic
# ---------------------------------------------------------------------------

def _extract_tree_sitter_fn_name(node: any) -> str:
    name_node = node.child_by_field_name("name")
    if not name_node and node.child_by_field_name("declarator"):
        decl = node.child_by_field_name("declarator")
        while decl:
            if decl.child_by_field_name("name"):
                name_node = decl.child_by_field_name("name")
                break
            inner = decl.child_by_field_name("declarator")
            if inner:
                decl = inner
            elif decl.type == "identifier":
                name_node = decl
                break
            else:
                for c in decl.children:
                    if c.type == "identifier":
                        name_node = c
                        break
                break
    if not name_node and node.parent and node.parent.type == "variable_declarator":
        name_node = node.parent.child_by_field_name("name")
    if name_node:
        try:
            return name_node.text.decode("utf-8")
        except Exception:
            return str(name_node.text)
    return "<anonymous>"


def _compute_tree_sitter_vg(fn_node: any) -> int:
    decisions = 0

    def walk(curr: any, is_root: bool = False) -> None:
        nonlocal decisions
        if not is_root and curr.type in FUNCTION_NODE_TYPES:
            # Nested function will be recorded as its own unit
            return
        if curr.type in DECISION_NODE_TYPES:
            decisions += 1
        elif curr.type in LOGICAL_OPERATORS:
            decisions += 1
        for child in curr.children:
            walk(child, is_root=False)

    walk(fn_node, is_root=True)
    return decisions + 1


def scan_file_tree_sitter(path: Path, lang: str) -> list[dict]:
    try:
        content_bytes = path.read_bytes()
    except Exception as exc:
        return [{"file": str(path), "line": 1, "function": "<read-error>", "vg": -1, "error": str(exc)}]

    try:
        # Resolve parser
        parser = None
        if "tree_sitter_languages" in sys.modules:
            # Handle tsx vs typescript fallback
            try:
                parser = tree_sitter_languages.get_parser(lang)
            except Exception:
                if lang == "tsx":
                    parser = tree_sitter_languages.get_parser("typescript")
        if not parser:
            return scan_file_fallback_ast(path) if lang == "python" else []

        tree = parser.parse(content_bytes)
    except Exception as exc:
        return [{"file": str(path), "line": 1, "function": "<parse-error>", "vg": -1, "error": str(exc)}]

    records: list[dict] = []

    def visit(node: any) -> None:
        if node.type in FUNCTION_NODE_TYPES:
            name = _extract_tree_sitter_fn_name(node)
            line = node.start_point[0] + 1
            vg = _compute_tree_sitter_vg(node)
            records.append({
                "file": str(path),
                "line": line,
                "function": name,
                "vg": vg,
            })
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return records


# ---------------------------------------------------------------------------
# Lizard Engine Logic
# ---------------------------------------------------------------------------

def scan_file_lizard(path: Path) -> list[dict]:
    if not _LIZARD_AVAILABLE:
        return []
    try:
        file_info = lizard.analyze_file(str(path))
        records = []
        for fn in file_info.function_list:
            records.append({
                "file": str(path),
                "line": fn.start_line,
                "function": fn.name,
                "vg": fn.cyclomatic_complexity,
            })
        return records
    except Exception as exc:
        return [{"file": str(path), "line": 1, "function": "<lizard-error>", "vg": -1, "error": str(exc)}]


# ---------------------------------------------------------------------------
# Python Standard AST Fallback Logic
# ---------------------------------------------------------------------------

def _compute_ast_vg(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    decisions = 0
    for child in ast.walk(node):
        if isinstance(child, (
            ast.If,
            ast.While,
            ast.For,
            ast.AsyncFor,
            ast.ExceptHandler,
            ast.Assert,
            ast.IfExp,
        )):
            decisions += 1
        elif isinstance(child, ast.BoolOp):
            decisions += len(child.values) - 1
        elif hasattr(ast, "Match") and isinstance(child, ast.Match):
            decisions += len(getattr(child, "cases", []))
    return decisions + 1


def scan_file_fallback_ast(path: Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [{
            "file": str(path),
            "line": exc.lineno or 1,
            "function": "<syntax-error>",
            "vg": -1,
            "error": str(exc),
        }]
    records = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            records.append({
                "file": str(path),
                "line": node.lineno,
                "function": node.name,
                "vg": _compute_ast_vg(node),
            })
    return records


# ---------------------------------------------------------------------------
# Universal File Scanner
# ---------------------------------------------------------------------------

def scan_file(path: Path, engine: str = "auto") -> list[dict]:
    ext = path.suffix.lower()
    lang = EXT_TO_LANG.get(ext)

    if engine == "ast":
        if ext == ".py":
            return scan_file_fallback_ast(path)
        return []

    if engine == "lizard" and _LIZARD_AVAILABLE:
        return scan_file_lizard(path)

    if engine == "tree-sitter" and _TREE_SITTER_AVAILABLE and lang:
        return scan_file_tree_sitter(path, lang)

    # Auto mode resolution
    if _TREE_SITTER_AVAILABLE and lang:
        return scan_file_tree_sitter(path, lang)
    if _LIZARD_AVAILABLE:
        return scan_file_lizard(path)
    if ext == ".py":
        return scan_file_fallback_ast(path)

    return []


def collect_source_files(roots: list[Path], exclude_dirs: set[str], engine: str = "auto") -> list[Path]:
    allowed_exts = set(EXT_TO_LANG.keys())
    if engine == "ast":
        allowed_exts = {".py"}

    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in allowed_exts:
                files.append(root)
            continue
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in allowed_exts:
                continue
            if any(part in exclude_dirs for part in candidate.parts):
                continue
            files.append(candidate)
    return files


def build_report(records: list[dict], active_engine: str = "auto") -> dict:
    violations = [r for r in records if r.get("vg", 0) > WARNING_THRESHOLD]
    warnings = [r for r in records if STANDARD_THRESHOLD < r.get("vg", 0) <= WARNING_THRESHOLD]
    return {
        "engine": active_engine,
        "total_functions_scanned": len(records),
        "warnings_count": len(warnings),
        "violations_count": len(violations),
        "violations": violations,
        "warnings": warnings,
        "passed": len(violations) == 0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="complexity_check",
        description="McCabe cyclomatic complexity static checker (quality-engineering gate).",
    )
    parser.add_argument(
        "--src-dir",
        dest="src_dirs",
        metavar="DIR",
        action="append",
        default=[],
        help="Source directory or file to scan (repeatable). Default: src/ or . if src/ absent.",
    )
    parser.add_argument(
        "--exclude",
        dest="exclude_dirs",
        metavar="NAME",
        action="append",
        default=[],
        help="Directory name to exclude (repeatable). Default: %(default)s.",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "tree-sitter", "lizard", "ast"],
        default="auto",
        help="Parsing engine (default: auto; prefers tree-sitter, then lizard, then python ast).",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit machine-readable JSON to stdout.",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit 0 even when critical violations are found (only warns).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="complexity_check 2.0.0 (multi-language Tree-sitter / Lizard / AST)",
    )
    return parser.parse_args(argv)


def resolve_active_engine(requested_engine: str) -> str:
    if requested_engine != "auto":
        return requested_engine
    if _TREE_SITTER_AVAILABLE:
        return "tree-sitter"
    if _LIZARD_AVAILABLE:
        return "lizard"
    return "ast"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    exclude = DEFAULT_EXCLUDE_DIRS | set(args.exclude_dirs)

    if args.src_dirs:
        roots = [Path(d) for d in args.src_dirs]
    else:
        default = Path("src")
        roots = [default] if default.is_dir() else [Path(".")]

    active_engine = resolve_active_engine(args.engine)

    try:
        files = collect_source_files(roots, exclude, engine=args.engine)
        all_records: list[dict] = []
        for f in files:
            all_records.extend(scan_file(f, engine=args.engine))

        report = build_report(all_records, active_engine=active_engine)

        if args.json_output:
            print(json.dumps(report, indent=2))
        else:
            print(f"Complexity Engine : {report['engine']}")
            print(f"Functions scanned : {report['total_functions_scanned']}")
            print(f"Warnings (V(G) 11-15): {report['warnings_count']}")
            print(f"Violations (V(G) >15): {report['violations_count']}")
            if report["warnings"]:
                print("\nWarnings:")
                for w in report["warnings"]:
                    print(f"  {w['file']}:{w['line']} {w['function']}  V(G)={w['vg']}")
            if report["violations"]:
                print("\nCritical violations:")
                for v in report["violations"]:
                    print(f"  {v['file']}:{v['line']} {v['function']}  V(G)={v['vg']}")
            status_str = "PASSED" if report["passed"] else "FAILED"
            print(f"\nResult: {status_str}")

        if args.warn_only:
            return 0
        return 0 if report["passed"] else 1

    except Exception as exc:  # noqa: BLE001
        print(f"Internal error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
