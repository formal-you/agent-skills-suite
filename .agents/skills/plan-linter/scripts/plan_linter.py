#!/usr/bin/env python3
"""Plan Linter v2 - Gate 1 deterministic static checker for task bundles.

Contract format: YAML frontmatter first (a small stdlib YAML subset), with a
legacy Markdown-table fallback for pre-v2 Chinese/English contracts.

Exit codes:
  0  every bundle passed
  1  one or more violations
  2  usage or configuration error
  3  unexpected internal error

Standard library only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

VERSION = "3.0.0"

EXIT_PASS = 0
EXIT_VIOLATIONS = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

DEFAULT_CONFIG = {
    "max_touch_files": 3,
    "min_diff_lines": 50,
    "max_diff_lines": 250,
    "require_anchor": True,
    "require_adrs": True,
    "min_edge_cases": 2,
    "require_docs": [
        "02-dev-workspace.md",
        "03-qa-verification.md",
        "04-process.md",
    ],
    "forbidden_touch_prefixes": ["tests/acceptance/"],
    "scan_placeholders": True,
    "micro_min_diff_lines": 10,
    "micro_max_touch_files": 1,
    "check_topology": True,
    "strict_topology": False,
    "ignore_task_dirs": ["archive"],
}

CONFIG_TYPES = {
    "max_touch_files": int,
    "min_diff_lines": int,
    "max_diff_lines": int,
    "require_anchor": bool,
    "require_adrs": bool,
    "min_edge_cases": int,
    "require_docs": list,
    "forbidden_touch_prefixes": list,
    "scan_placeholders": bool,
    "micro_min_diff_lines": int,
    "micro_max_touch_files": int,
    "check_topology": bool,
    "strict_topology": bool,
    "ignore_task_dirs": list,
}

ANCHOR_RE = re.compile(r"#sec-[a-z0-9-]+$")
ANCHOR_TOKEN_RE = re.compile(r"#sec-[a-z0-9-]+")
CHANGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{[^}]*\}\}"),
    re.compile(r"\[TBD\]"),
    re.compile(r"\bTODO\b"),
]
GHERKIN_EDGE_CASE_RE = re.compile(
    r"^\s*Given\s+(?P<given>.+?),\s+When\s+(?P<when>.+?),\s+Then\s+(?P<then>.+?)\s*$",
    re.IGNORECASE,
)
GHERKIN_PREFIXED_RE = re.compile(
    r"^(?:Scenario:\s*(?P<scenario>.+?)\s*\|\s*)?Given\s+(?P<given>.+?),\s+When\s+(?P<when>.+?),\s+Then\s+(?P<then>.+?)$",
    re.IGNORECASE,
)


class UsageError(Exception):
    """A CLI or config problem: exit code 2."""


class YamlSubsetError(Exception):
    """The frontmatter is not parseable by the small YAML subset."""


# ---------------------------------------------------------------------------
# Minimal YAML subset
# ---------------------------------------------------------------------------


def _strip_comment(text):
    out = []
    quote = None
    for index, char in enumerate(text):
        if quote is not None:
            out.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            out.append(char)
        elif char == "#" and (index == 0 or text[index - 1].isspace()):
            break
        else:
            out.append(char)
    return "".join(out).rstrip()


def _split_key_value(text):
    quote = None
    for index, char in enumerate(text):
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == ":":
            return text[:index].strip(), text[index + 1 :].strip()
    return None


def _parse_scalar(text):
    value = text.strip()
    if value == "":
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [_parse_scalar(part) for part in body.split(",")]
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _tokenize(text):
    tokens = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        cleaned = _strip_comment(raw)
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        tokens.append((indent, cleaned.strip()))
    return tokens


def _parse_map(tokens, index, indent):
    result = {}
    while index < len(tokens) and tokens[index][0] == indent:
        pair = _split_key_value(tokens[index][1])
        if pair is None:
            raise YamlSubsetError("expected a key: value line, got: " + tokens[index][1])
        key, rest = pair
        key = key.strip().strip("'\"")
        index += 1
        if rest == "":
            if index < len(tokens) and tokens[index][0] > indent:
                value, index = _parse_node(tokens, index, tokens[index][0])
            else:
                value = None
        else:
            value = _parse_scalar(rest)
        result[key] = value
    return result, index


def _parse_list(tokens, index, indent):
    result = []
    while (
        index < len(tokens)
        and tokens[index][0] == indent
        and (tokens[index][1] == "-" or tokens[index][1].startswith("- "))
    ):
        content = tokens[index][1]
        rest = content[1:].strip() if content != "-" else ""
        index += 1
        if rest == "":
            if index < len(tokens) and tokens[index][0] > indent:
                value, index = _parse_node(tokens, index, tokens[index][0])
            else:
                value = None
            result.append(value)
            continue
        pair = _split_key_value(rest)
        if pair is None:
            result.append(_parse_scalar(rest))
            continue
        key, raw_value = pair
        item = {}
        item[key.strip().strip("'\"")] = _parse_scalar(raw_value) if raw_value != "" else None
        while index < len(tokens) and tokens[index][0] > indent and not tokens[index][1].startswith("- "):
            child = _split_key_value(tokens[index][1])
            if child is None:
                raise YamlSubsetError("expected an indented key: value line, got: " + tokens[index][1])
            child_key, child_value = child
            child_key = child_key.strip().strip("'\"")
            index += 1
            if child_value == "":
                if index < len(tokens) and tokens[index][0] > indent:
                    child_parsed, index = _parse_node(tokens, index, tokens[index][0])
                else:
                    child_parsed = None
            else:
                child_parsed = _parse_scalar(child_value)
            item[child_key] = child_parsed
        result.append(item)
    return result, index


def _parse_node(tokens, index, indent):
    if tokens[index][1] == "-" or tokens[index][1].startswith("- "):
        return _parse_list(tokens, index, indent)
    return _parse_map(tokens, index, indent)


def parse_yaml_subset(text):
    tokens = _tokenize(text)
    if not tokens:
        return {}
    value, index = _parse_node(tokens, 0, tokens[0][0])
    if index != len(tokens):
        raise YamlSubsetError("unexpected indentation near: " + tokens[index][1])
    if not isinstance(value, dict):
        raise YamlSubsetError("frontmatter must be a mapping")
    return value


def split_frontmatter(text):
    """Return (mapping, body_start_line) or (None, 0) when absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            body = "\n".join(lines[1:index])
            return parse_yaml_subset(body), index + 1
    return None, 0


# ---------------------------------------------------------------------------
# Contract model
# ---------------------------------------------------------------------------


def _empty_contract():
    return {
        "task_id": None,
        "title": None,
        "module": None,
        "dependencies": [],
        "estimated_lines": None,
        "touch_files": [],
        "origin_spec_anchor": None,
        "adherence_adrs": [],
        "dod": {},
        "size_class": "standard",
        "change_id": None,
        "format": None,
    }


def _as_string(value):
    if isinstance(value, str):
        return value.strip()
    return None


def _line_of(text, key):
    pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*:")
    for index, line in enumerate(text.splitlines(), 1):
        if pattern.match(line):
            return index
    return 0


def contract_from_frontmatter(mapping, text, warnings):
    contract = _empty_contract()
    contract["format"] = "frontmatter"

    contract["task_id"] = _as_string(mapping.get("task_id"))
    contract["title"] = _as_string(mapping.get("title"))
    contract["module"] = _as_string(mapping.get("module"))

    deps = mapping.get("dependencies")
    if deps is None:
        deps = []
    if isinstance(deps, list):
        contract["dependencies"] = [_as_string(item) for item in deps if _as_string(item)]
    elif isinstance(deps, str) and deps.strip():
        contract["dependencies"] = [deps.strip()]

    estimated = mapping.get("estimated_lines")
    if isinstance(estimated, bool):
        estimated = None
    if isinstance(estimated, int):
        contract["estimated_lines"] = estimated

    touch = mapping.get("touch_files")
    if isinstance(touch, list):
        entries = []
        for item in touch:
            if isinstance(item, dict):
                entries.append(
                    {
                        "action": _as_string(item.get("action")) or "",
                        "path": _as_string(item.get("path")) or "",
                    }
                )
            elif isinstance(item, str):
                entries.append({"action": "create", "path": item.strip()})
        contract["touch_files"] = entries

    contract["origin_spec_anchor"] = _as_string(mapping.get("origin_spec_anchor"))
    contract["size_class"] = _as_string(mapping.get("size_class")) or "standard"
    contract["change_id"] = _as_string(mapping.get("change_id"))

    adrs = mapping.get("adherence_adrs")
    if isinstance(adrs, list):
        contract["adherence_adrs"] = [_as_string(item) for item in adrs if _as_string(item)]
    elif isinstance(adrs, str) and adrs.strip():
        contract["adherence_adrs"] = [adrs.strip()]

    dod = mapping.get("dod")
    if isinstance(dod, dict):
        edge_cases = dod.get("edge_cases")
        if isinstance(edge_cases, list):
            edge_cases = [_as_string(item) for item in edge_cases if _as_string(item)]
        elif isinstance(edge_cases, str):
            edge_cases = [edge_cases]
        else:
            edge_cases = []
        contract["dod"] = {
            "type_check": _as_string(dod.get("type_check")),
            "lint": _as_string(dod.get("lint")),
            "test_file": _as_string(dod.get("test_file")),
            "edge_cases": edge_cases,
        }
    return contract


LEGACY_REGEX = {
    "task_id": re.compile(r"\*\*Task\s*ID\*\*\s*\|\s*\x60?(task-[A-Za-z0-9_.-]+)\x60?"),
    "dependencies": re.compile(
        r"\*\*(?:前置依赖|Dependencies)\*\*\s*\|\s*\x60?\[(.*?)\]\x60?"
    ),
    "estimated_lines": re.compile(
        r"\*\*(?:预估代码量|Estimated\s+Lines|Estimated\s+Diff\s+Lines)\*\*\s*\|\s*\x60?(\d+)\s*(?:行|lines?)\x60?",
        re.IGNORECASE,
    ),
    "touch": re.compile(r"^\s*[-*]\s*\x60?\[(CREATE|MODIFY)\]\x60?\s*\x60?([^\s\x60]+)\x60?", re.IGNORECASE),
    "anchor": re.compile(
        r"\*\*(?:Tech\s*Spec\s*锚点|Tech\s*Spec\s+Anchor|Spec\s+Anchor|PRD\s*溯源锚点|PRD\s+Anchor)\*\*\s*\|\s*\x60?([^|\s\x60]+)\x60?",
        re.IGNORECASE,
    ),
    "adrs": re.compile(
        r"^\s*[-*]\s*\[\s*\]\s*\*\*(?:继承|Inherit(?:ed)?)\s*\[(ADR-[A-Za-z0-9_.-]+)\]",
        re.IGNORECASE,
    ),
    "type_check": re.compile(
        r"(?:类型检查命令通过|Type\s+check\s+(?:command\s+)?passes|Type\s+check\s+command)\s*[:：]\s*\x60([^\x60]+)\x60",
        re.IGNORECASE,
    ),
    "lint": re.compile(
        r"(?:代码风格检查通过|Lint\s+(?:command\s+)?passes|Lint\s+command)\s*[:：]\s*\x60([^\x60]+)\x60",
        re.IGNORECASE,
    ),
    "test_file": re.compile(
        r"(?:对应验收测试文件|Acceptance\s+test\s+file)\s*[:：]\s*\x60([^\x60]+)\x60",
        re.IGNORECASE,
    ),
    "edge_case": re.compile(
        r"^\s*[-*]\s*\[\s*\]\s*\*\*(?:反向/边界场景用例|Negative/boundary\s+case|Boundary\s+case)[^*]*\*\*\s*[:：]\s*(.+)$",
        re.IGNORECASE,
    ),
}


def contract_from_legacy(text, warnings):
    contract = _empty_contract()
    contract["format"] = "legacy"
    task_match = LEGACY_REGEX["task_id"].search(text)
    if task_match:
        contract["task_id"] = task_match.group(1)

    deps_match = LEGACY_REGEX["dependencies"].search(text)
    if deps_match:
        raw = deps_match.group(1).strip()
        if raw:
            contract["dependencies"] = [
                part.strip().strip("\x60").strip("'").strip('"')
                for part in raw.split(",")
                if part.strip()
            ]

    lines_match = LEGACY_REGEX["estimated_lines"].search(text)
    if lines_match:
        contract["estimated_lines"] = int(lines_match.group(1))

    touch_files = []
    for line in text.splitlines():
        match = LEGACY_REGEX["touch"].match(line)
        if match:
            touch_files.append({"action": match.group(1).lower(), "path": match.group(2)})
    contract["touch_files"] = touch_files

    anchor_match = LEGACY_REGEX["anchor"].search(text)
    if anchor_match:
        contract["origin_spec_anchor"] = anchor_match.group(1)

    adrs = []
    for line in text.splitlines():
        match = LEGACY_REGEX["adrs"].match(line)
        if match:
            adrs.append(match.group(1))
    contract["adherence_adrs"] = adrs

    dod = {}
    for key in ("type_check", "lint", "test_file"):
        match = LEGACY_REGEX[key].search(text)
        if match:
            dod[key] = match.group(1).strip()
    edge_cases = []
    for line in text.splitlines():
        match = LEGACY_REGEX["edge_case"].match(line)
        if match:
            edge_cases.append(match.group(1).strip())
    dod["edge_cases"] = edge_cases
    contract["dod"] = dod
    return contract


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class Finding(object):
    def __init__(self, task, code, message, file="", line=0):
        self.task = task
        self.code = code
        self.message = message
        self.file = file
        self.line = line

    def to_dict(self):
        return {
            "task": self.task,
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }


def _line_of_edge_case(text, ec_str):
    for idx, line in enumerate(text.splitlines(), 1):
        if ec_str in line:
            return idx
    return _line_of(text, "edge_cases") or 1


def _lint_bdd_edge_cases(task_name, contract_file, text, edge_cases, findings, warnings):
    if not isinstance(edge_cases, list):
        return
    for idx, ec in enumerate(edge_cases, 1):
        if not isinstance(ec, str):
            continue
        line_num = _line_of_edge_case(text, ec)
        cleaned = ec.strip().strip('"').strip("'")
        if not cleaned:
            continue

        match = GHERKIN_PREFIXED_RE.match(cleaned) or GHERKIN_EDGE_CASE_RE.match(cleaned)
        if match:
            given = (match.group("given") or "").strip()
            when = (match.group("when") or "").strip()
            then = (match.group("then") or "").strip()
            if not given:
                findings.append(
                    Finding(
                        task_name,
                        "BDD_MISSING_PRECONDITION",
                        "Edge case %d missing Given precondition: %r" % (idx, ec),
                        contract_file,
                        line_num,
                    )
                )
            if not when:
                findings.append(
                    Finding(
                        task_name,
                        "BDD_MISSING_ACTION",
                        "Edge case %d missing When action: %r" % (idx, ec),
                        contract_file,
                        line_num,
                    )
                )
            if not then:
                findings.append(
                    Finding(
                        task_name,
                        "BDD_MISSING_OUTCOME",
                        "Edge case %d missing Then outcome: %r" % (idx, ec),
                        contract_file,
                        line_num,
                    )
                )
        else:
            has_given = bool(re.search(r"\bGiven\b", cleaned, re.IGNORECASE))
            has_when = bool(re.search(r"\bWhen\b", cleaned, re.IGNORECASE))
            has_then = bool(re.search(r"\bThen\b", cleaned, re.IGNORECASE))
            if has_given or has_when or has_then:
                if not has_given:
                    findings.append(
                        Finding(
                            task_name,
                            "BDD_MISSING_PRECONDITION",
                            "Edge case %d missing Given precondition: %r" % (idx, ec),
                            contract_file,
                            line_num,
                        )
                    )
                else:
                    g_match = re.search(r"\bGiven\s+(.*?)(?=,\s*When\b|,\s*Then\b|$)", cleaned, re.IGNORECASE)
                    if not g_match or not g_match.group(1).strip():
                        findings.append(
                            Finding(
                                task_name,
                                "BDD_MISSING_PRECONDITION",
                                "Edge case %d has empty Given precondition: %r" % (idx, ec),
                                contract_file,
                                line_num,
                            )
                        )

                if not has_when:
                    findings.append(
                        Finding(
                            task_name,
                            "BDD_MISSING_ACTION",
                            "Edge case %d missing When action: %r" % (idx, ec),
                            contract_file,
                            line_num,
                        )
                    )
                else:
                    w_match = re.search(r"\bWhen\s+(.*?)(?=,\s*Then\b|$)", cleaned, re.IGNORECASE)
                    if not w_match or not w_match.group(1).strip():
                        findings.append(
                            Finding(
                                task_name,
                                "BDD_MISSING_ACTION",
                                "Edge case %d has empty When action: %r" % (idx, ec),
                                contract_file,
                                line_num,
                            )
                        )

                if not has_then:
                    findings.append(
                        Finding(
                            task_name,
                            "BDD_MISSING_OUTCOME",
                            "Edge case %d missing Then outcome: %r" % (idx, ec),
                            contract_file,
                            line_num,
                        )
                    )
                else:
                    t_match = re.search(r"\bThen\s+(.*?)$", cleaned, re.IGNORECASE)
                    if not t_match or not t_match.group(1).strip():
                        findings.append(
                            Finding(
                                task_name,
                                "BDD_MISSING_OUTCOME",
                                "Edge case %d has empty Then outcome: %r" % (idx, ec),
                                contract_file,
                                line_num,
                            )
                        )
            else:
                if warnings is not None:
                    warnings.append(
                        {
                            "task": task_name,
                            "code": "BDD_INVALID_SCENARIO",
                            "message": "Edge case %d does not follow Given-When-Then BDD format: %r" % (idx, ec),
                            "file": contract_file,
                            "line": line_num,
                        }
                    )


def _lint_bdd_section4_scenarios(task_name, contract_file, text, findings):
    lines = text.splitlines()
    in_sec4 = False
    sec4_lines = []
    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("## 4."):
            in_sec4 = True
            continue
        if in_sec4:
            if stripped.startswith("## ") and not stripped.startswith("## 4."):
                break
            sec4_lines.append((line_no, line))

    scenarios = []
    current = None
    for line_no, line in sec4_lines:
        s = line.strip()
        if re.match(r"^#{3,5}\s+Scenario\b", s, re.IGNORECASE):
            if current:
                scenarios.append(current)
            current = {"title": s, "line": line_no, "given": None, "when": None, "then": None}
        elif current is not None:
            g_match = re.search(r"^[-*+]\s*(?:\*\*)?Given\s*(?::?\s*\*\*)?:?\s*(.*)$", s, re.IGNORECASE)
            w_match = re.search(r"^[-*+]\s*(?:\*\*)?When\s*(?::?\s*\*\*)?:?\s*(.*)$", s, re.IGNORECASE)
            t_match = re.search(r"^[-*+]\s*(?:\*\*)?Then\s*(?::?\s*\*\*)?:?\s*(.*)$", s, re.IGNORECASE)
            if g_match:
                val = g_match.group(1).strip().lstrip("*: ").rstrip("*: ").strip()
                if val:
                    current["given"] = val
            elif w_match:
                val = w_match.group(1).strip().lstrip("*: ").rstrip("*: ").strip()
                if val:
                    current["when"] = val
            elif t_match:
                val = t_match.group(1).strip().lstrip("*: ").rstrip("*: ").strip()
                if val:
                    current["then"] = val
    if current:
        scenarios.append(current)

    for sc in scenarios:
        sc_title = sc["title"]
        sc_line = sc["line"]
        if not sc.get("given"):
            findings.append(
                Finding(
                    task_name,
                    "BDD_MISSING_PRECONDITION",
                    "Scenario %r in Section 4 is missing Given clause" % sc_title,
                    contract_file,
                    sc_line,
                )
            )
        if not sc.get("when"):
            findings.append(
                Finding(
                    task_name,
                    "BDD_MISSING_ACTION",
                    "Scenario %r in Section 4 is missing When clause" % sc_title,
                    contract_file,
                    sc_line,
                )
            )
        if not sc.get("then"):
            findings.append(
                Finding(
                    task_name,
                    "BDD_MISSING_OUTCOME",
                    "Scenario %r in Section 4 is missing Then clause" % sc_title,
                    contract_file,
                    sc_line,
                )
            )







def _validate_contract(task_dir, contract, text, config, findings, warnings=None):
    task_name = contract.get("task_id") or task_dir.name
    contract_file = "01-contract.md"

    touch_files = contract.get("touch_files") or []
    valid_touch = [entry for entry in touch_files if entry.get("path")]
    for entry in touch_files:
        action = (entry.get("action") or "").lower()
        if action not in ("create", "modify"):
            findings.append(
                Finding(
                    task_name,
                    "INVALID_TOUCH_ACTION",
                    "touch_files action must be create or modify, got: " + repr(entry.get("action")),
                    contract_file,
                    _line_of(text, "touch_files"),
                )
            )
    if not valid_touch:
        findings.append(
            Finding(
                task_name,
                "NO_TOUCH_FILES",
                "touch_files must list at least one file",
                contract_file,
                _line_of(text, "touch_files"),
            )
        )
    elif len(valid_touch) > config["max_touch_files"]:
        findings.append(
            Finding(
                task_name,
                "TOO_MANY_TOUCH_FILES",
                "touch_files has %d entries; the limit is %d"
                % (len(valid_touch), config["max_touch_files"]),
                contract_file,
                _line_of(text, "touch_files"),
            )
        )

    forbidden = [prefix.lower().lstrip("./") for prefix in config["forbidden_touch_prefixes"]]
    for entry in valid_touch:
        normalized = entry["path"].replace("\\", "/").lstrip("./").lower()
        for prefix in forbidden:
            if prefix and normalized.startswith(prefix):
                findings.append(
                    Finding(
                        task_name,
                        "FORBIDDEN_TOUCH_FILE",
                        "touch_files may not include a path under the forbidden prefix %r: %s"
                        % (prefix, entry["path"]),
                        contract_file,
                        _line_of(text, "touch_files"),
                    )
                )
                break

    size_class = contract.get("size_class") or "standard"
    if size_class not in ("standard", "micro"):
        findings.append(
            Finding(
                task_name,
                "INVALID_SIZE_CLASS",
                "size_class must be standard or micro, got: " + repr(size_class),
                contract_file,
                _line_of(text, "size_class"),
            )
        )
        size_class = "standard"

    change_id = contract.get("change_id")
    if change_id and not CHANGE_ID_RE.fullmatch(change_id):
        findings.append(
            Finding(
                task_name,
                "INVALID_CHANGE_ID",
                "change_id %r must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}" % change_id,
                contract_file,
                _line_of(text, "change_id"),
            )
        )

    min_lines = config["min_diff_lines"]
    max_lines = config["max_diff_lines"]
    too_small_code = "DIFF_TOO_SMALL"
    too_large_code = "DIFF_TOO_LARGE"
    budget_label = "estimated_lines"
    if size_class == "micro":
        min_lines = config["micro_min_diff_lines"]
        max_lines = config["min_diff_lines"] - 1
        too_small_code = "MICRO_DIFF_TOO_SMALL"
        too_large_code = "MICRO_DIFF_TOO_LARGE"
        budget_label = "estimated_lines (size_class micro)"
        if not change_id:
            findings.append(
                Finding(
                    task_name,
                    "MICRO_REQUIRES_CHANGE_ID",
                    "size_class micro requires change_id pointing at a change proposal",
                    contract_file,
                    _line_of(text, "size_class"),
                )
            )
        if len(valid_touch) > config["micro_max_touch_files"]:
            findings.append(
                Finding(
                    task_name,
                    "MICRO_TOO_MANY_TOUCH_FILES",
                    "size_class micro touches %d files; the limit is %d"
                    % (len(valid_touch), config["micro_max_touch_files"]),
                    contract_file,
                    _line_of(text, "touch_files"),
                )
            )

    estimated = contract.get("estimated_lines")
    if not isinstance(estimated, int):
        findings.append(
            Finding(
                task_name,
                "MISSING_ESTIMATED_LINES",
                "estimated_lines is required and must be an integer",
                contract_file,
                _line_of(text, "estimated_lines"),
            )
        )
    elif estimated < min_lines:
        findings.append(
            Finding(
                task_name,
                too_small_code,
                "%s is %d; the minimum is %d" % (budget_label, estimated, min_lines),
                contract_file,
                _line_of(text, "estimated_lines"),
            )
        )
    elif estimated > max_lines:
        findings.append(
            Finding(
                task_name,
                too_large_code,
                "%s is %d; the maximum is %d" % (budget_label, estimated, max_lines),
                contract_file,
                _line_of(text, "estimated_lines"),
            )
        )

    anchor = contract.get("origin_spec_anchor")
    if config["require_anchor"]:
        if not anchor:
            findings.append(
                Finding(
                    task_name,
                    "MISSING_ANCHOR",
                    "origin_spec_anchor is required (format: #sec-[a-z0-9-]+)",
                    contract_file,
                    _line_of(text, "origin_spec_anchor"),
                )
            )
        elif not ANCHOR_RE.search(anchor):
            findings.append(
                Finding(
                    task_name,
                    "INVALID_ANCHOR",
                    "origin_spec_anchor %r does not match #sec-[a-z0-9-]+" % anchor,
                    contract_file,
                    _line_of(text, "origin_spec_anchor"),
                )
            )

    if config["require_adrs"] and not contract.get("adherence_adrs"):
        findings.append(
            Finding(
                task_name,
                "MISSING_ADRS",
                "adherence_adrs must list at least one ADR id",
                contract_file,
                _line_of(text, "adherence_adrs"),
            )
        )

    dod = contract.get("dod") or {}
    for field, code, label in (
        ("type_check", "MISSING_TYPE_CHECK", "dod.type_check"),
        ("lint", "MISSING_LINT", "dod.lint"),
        ("test_file", "MISSING_TEST_FILE", "dod.test_file"),
    ):
        value = dod.get(field)
        if not value or not str(value).strip():
            findings.append(
                Finding(
                    task_name,
                    code,
                    label + " is required",
                    contract_file,
                    _line_of(text, "dod"),
                )
            )
    edge_cases = dod.get("edge_cases") or []
    if len(edge_cases) < config["min_edge_cases"]:
        findings.append(
            Finding(
                task_name,
                "TOO_FEW_EDGE_CASES",
                "dod.edge_cases has %d entries; at least %d are required"
                % (len(edge_cases), config["min_edge_cases"]),
                contract_file,
                _line_of(text, "dod"),
            )
        )
    _lint_bdd_edge_cases(task_name, contract_file, text, edge_cases, findings, warnings)
    _lint_bdd_section4_scenarios(task_name, contract_file, text, findings)

    for doc_name in config["require_docs"]:
        if not (task_dir / doc_name).is_file():
            findings.append(
                Finding(
                    task_name,
                    "MISSING_DOC",
                    "required task document is missing: " + doc_name,
                    doc_name,
                    0,
                )
            )

    if contract.get("task_id") and contract["task_id"] != task_dir.name:
        findings.append(
            Finding(
                task_name,
                "TASK_ID_MISMATCH",
                "task_id %r does not equal the directory name %r"
                % (contract["task_id"], task_dir.name),
                contract_file,
                _line_of(text, "task_id"),
            )
        )
    if not contract.get("task_id"):
        findings.append(
            Finding(
                task_name,
                "MISSING_TASK_ID",
                "task_id is required",
                contract_file,
                _line_of(text, "task_id"),
            )
        )


def _scan_placeholders(task_name, task_dir, config, findings):
    if not config["scan_placeholders"]:
        return
    for doc_name in ("01-contract.md", "02-dev-workspace.md", "03-qa-verification.md"):
        path = task_dir / doc_name
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for number, line in enumerate(content.splitlines(), 1):
            for pattern in PLACEHOLDER_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append(
                        Finding(
                            task_name,
                            "PLACEHOLDER",
                            "unresolved placeholder %r in %s" % (match.group(0), doc_name),
                            doc_name,
                            number,
                        )
                    )
                    break


def _topology_message(code, path, target):
    if code == "TOUCH_FILE_MISSING":
        return "touch_files declares a modify path that does not exist: " + path
    if code == "TOUCH_FILE_EXISTS":
        return "touch_files declares a create path that already exists: " + path
    return "touch_files path does not resolve inside the repository root: " + path


def _check_topology(task_name, contract, text, config, repo_root, findings, warnings):
    """Reverse topology check: declared modify paths must exist; create paths must not.

    Severity is a warning by default (the plan can legitimately be authored before
    files exist for create entries) and becomes an error under strict_topology.
    """
    if not config["check_topology"] or repo_root is None:
        return
    strict = config["strict_topology"]
    line = _line_of(text, "touch_files")
    for entry in contract.get("touch_files") or []:
        raw = (entry.get("path") or "").strip()
        if not raw:
            continue
        action = (entry.get("action") or "").lower()
        normalized = raw.replace("\\", "/")
        outside = (
            normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized) is not None
            or ".." in normalized.split("/")
        )
        target = None
        if not outside:
            try:
                candidate = (Path(repo_root) / normalized).resolve()
                candidate.relative_to(Path(repo_root).resolve())
                target = candidate
            except (OSError, ValueError):
                outside = True
        if outside or target is None:
            code = "TOUCH_PATH_OUTSIDE_ROOT"
            exists = False
        else:
            exists = target.exists()
            code = ""
            if action == "modify" and not exists:
                code = "TOUCH_FILE_MISSING"
            elif action == "create" and exists:
                code = "TOUCH_FILE_EXISTS"
        if not code:
            continue
        message = _topology_message(code, raw, target)
        if strict:
            findings.append(Finding(task_name, code, message, "01-contract.md", line))
        else:
            warnings.append(
                {
                    "task": task_name,
                    "code": code,
                    "message": message,
                    "file": "01-contract.md",
                    "line": line,
                }
            )


def _lint_qa_complexity(
    task_name: str,
    task_dir: Path,
    findings: List[Finding],
    warnings: Optional[List[Dict[str, Any]]] = None,
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

        if vg > 15:
            findings.append(
                Finding(
                    task_name,
                    "COMPLEXITY_EXCEEDS_MAX_THRESHOLD",
                    f"Function {fn_name!r} has cyclomatic complexity V(G)={vg} exceeding maximum threshold of 15",
                    "03-qa-verification.md",
                    line_no,
                )
            )
        elif 11 <= vg <= 15:
            if warnings is not None:
                warnings.append(
                    {
                        "task": task_name,
                        "code": "COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD",
                        "message": (
                            f"Function {fn_name!r} has cyclomatic complexity V(G)={vg} exceeding standard threshold of 10"
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
) -> None:
    """Audit Section 4: Mutation testing and MSI audit."""
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
        r"^#{2,4}\s*(?:\d+\.\s*)?Mutation\s+testing\s+and\s+MSI\s+audit\b.*$",
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
            if re.match(r"^#{2,4}\s*(?:\d+\.\s*)?Mutation\s+testing\s+and\s+MSI\s+audit\b", stripped, re.IGNORECASE):
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
                        if msi_score < 80.0:
                            tbl_findings.append(
                                Finding(
                                    task_name,
                                    "QA_INVALID_MSI_SCORE",
                                    f"Mutation Score Indicator (MSI) {msi_score:.1f}% is below required 80% threshold",
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
                    if score < 80.0:
                        tbl_findings.append(
                            Finding(
                                task_name,
                                "QA_INVALID_MSI_SCORE",
                                f"Target file {tf_display!r} has MSI score {score:.1f}% below required 80% threshold",
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

def _collect_spec_anchors(spec_path):
    try:
        text = Path(spec_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return sorted(set(ANCHOR_TOKEN_RE.findall(text)))


def _build_coverage(spec_path, contracts):
    """Machine-readable anchor coverage matrix between the spec and the contracts."""
    spec_anchors = _collect_spec_anchors(spec_path)
    declared = set()
    for _task_name, contract in contracts:
        anchor = contract.get("origin_spec_anchor")
        if anchor and ANCHOR_RE.search(anchor):
            declared.add(anchor)
    covered = [anchor for anchor in spec_anchors if anchor in declared]
    uncovered = [anchor for anchor in spec_anchors if anchor not in declared]
    missing = sorted(anchor for anchor in declared if anchor not in spec_anchors)
    total = len(spec_anchors)
    ratio = round(float(len(covered)) / total, 4) if total else 0.0
    return {
        "spec": str(spec_path),
        "spec_anchors": total,
        "covered": covered,
        "uncovered": uncovered,
        "contract_anchors_missing_from_spec": missing,
        "coverage_ratio": ratio,
    }


def _check_change_proposals(contracts, changes_dir, findings, warnings):
    """A brownfield contract must have an open proposal under the change directory."""
    if changes_dir is None:
        return
    root = Path(changes_dir)
    for task_name, contract in contracts:
        change_id = contract.get("change_id")
        if not change_id:
            continue
        proposal = root / change_id / "proposal.md"
        if not proposal.is_file():
            findings.append(
                Finding(
                    task_name,
                    "CHANGE_PROPOSAL_MISSING",
                    "change_id %r has no proposal at %s" % (change_id, proposal),
                    "01-contract.md",
                    0,
                )
            )
            continue
        try:
            text = proposal.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        mapping, _start = split_frontmatter(text)
        status = _as_string((mapping or {}).get("status")) or ""
        if status == "archived":
            warnings.append(
                {
                    "task": task_name,
                    "code": "CHANGE_ALREADY_ARCHIVED",
                    "message": "change proposal %r is already archived; a pending task bundle"
                               " still references it" % change_id,
                    "file": str(proposal),
                    "line": 1,
                }
            )
        elif status and status not in ("proposed", "applied"):
            findings.append(
                Finding(
                    task_name,
                    "CHANGE_NOT_OPEN",
                    "change proposal %r has status %r; reopen it or archive the task"
                    % (change_id, status),
                    str(proposal),
                    1,
                )
            )


def _check_graph(contracts, findings):
    graph = {}
    for task_name, contract in contracts:
        task_id = contract.get("task_id")
        if not task_id:
            continue
        if task_id in graph:
            findings.append(
                Finding(
                    task_id,
                    "DUPLICATE_TASK_ID",
                    "task_id %r is declared by more than one task bundle" % task_id,
                    "01-contract.md",
                    0,
                )
            )
            continue
        graph[task_id] = [dep for dep in contract.get("dependencies") or [] if dep]

    for task_id in sorted(graph):
        for dependency in graph[task_id]:
            if dependency not in graph:
                findings.append(
                    Finding(
                        task_id,
                        "DEPENDENCY_NOT_FOUND",
                        "dependency %r is not a known task_id" % dependency,
                        "01-contract.md",
                        0,
                    )
                )

    in_degree = {}
    edges = {}
    for task_id in graph:
        in_degree[task_id] = 0
        edges[task_id] = []
    for task_id, dependencies in graph.items():
        for dependency in dependencies:
            if dependency in graph:
                edges[dependency].append(task_id)
                in_degree[task_id] += 1
    queue = sorted(task_id for task_id, degree in in_degree.items() if degree == 0)
    visited = 0
    while queue:
        current = queue.pop(0)
        visited += 1
        for neighbour in edges[current]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)
    if visited != len(graph):
        unresolved = sorted(task_id for task_id, degree in in_degree.items() if degree > 0)
        findings.append(
            Finding(
                ",".join(unresolved),
                "DAG_CYCLE",
                "dependency graph contains a cycle among: " + ", ".join(unresolved),
                "01-contract.md",
                0,
            )
        )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_config(path):
    config = dict(DEFAULT_CONFIG)
    config["require_docs"] = list(DEFAULT_CONFIG["require_docs"])
    config["forbidden_touch_prefixes"] = list(DEFAULT_CONFIG["forbidden_touch_prefixes"])
    warnings = []
    if not path:
        return config, warnings
    config_path = Path(path)
    if not config_path.is_file():
        raise UsageError("config file not found: " + str(config_path))
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UsageError("config file is not valid JSON: " + str(exc))
    if not isinstance(raw, dict):
        raise UsageError("config file must contain a JSON object")
    for key, value in raw.items():
        if key not in DEFAULT_CONFIG:
            warnings.append(
                {
                    "task": "",
                    "code": "UNKNOWN_CONFIG_KEY",
                    "message": "unknown config key: " + key,
                    "file": str(config_path),
                    "line": 0,
                }
            )
            continue
        expected = CONFIG_TYPES[key]
        valid = isinstance(value, expected)
        if expected is int and isinstance(value, bool):
            valid = False
        if not valid:
            raise UsageError("config key %r must be of type %s" % (key, expected.__name__))
        if isinstance(value, list):
            value = list(value)
        config[key] = value
    if config["min_diff_lines"] > config["max_diff_lines"]:
        raise UsageError("config min_diff_lines must not exceed max_diff_lines")
    if "micro_min_diff_lines" not in raw and config["micro_min_diff_lines"] >= config["min_diff_lines"]:
        config["micro_min_diff_lines"] = max(1, config["min_diff_lines"] - 1)
    if config["max_touch_files"] < 1:
        raise UsageError("config max_touch_files must be at least 1")
    if config["micro_min_diff_lines"] < 1:
        raise UsageError("config micro_min_diff_lines must be at least 1")
    if config["micro_min_diff_lines"] >= config["min_diff_lines"]:
        raise UsageError("config micro_min_diff_lines must be smaller than min_diff_lines")
    if config["micro_max_touch_files"] < 1:
        raise UsageError("config micro_max_touch_files must be at least 1")
    if not isinstance(config["ignore_task_dirs"], list):
        raise UsageError("config ignore_task_dirs must be a list")
    return config, warnings


def _iter_task_dirs(tasks_root, ignored=()):
    """Task bundle directories, excluding dot/underscore dirs and archive roots.

    Converged bundles live under tasks/archive/ and are historical records, not
    pending plans, so they must never be treated as Gate 1 inputs.
    """
    skip = {name.lower() for name in ignored}
    entries = []
    for item in sorted(os.listdir(tasks_root)):
        path = tasks_root / item
        if not path.is_dir() or item.startswith(".") or item.startswith("_"):
            continue
        if item.lower() in skip:
            continue
        entries.append(path)
    return entries


def lint(
    tasks_root,
    config,
    force_legacy=False,
    repo_root=None,
    spec_path=None,
    changes_dir=None,
    require_full_coverage=False,
    strict_anchor=False,
):
    findings = []
    warnings = []
    contracts = []
    task_dirs = _iter_task_dirs(tasks_root, config.get("ignore_task_dirs") or [])
    if not task_dirs:
        findings.append(
            Finding("", "NO_TASKS", "no task bundles found under: " + str(tasks_root), str(tasks_root), 0)
        )
        return findings, warnings, 0, None

    for task_dir in task_dirs:
        contract_path = task_dir / "01-contract.md"
        if not contract_path.is_file():
            findings.append(
                Finding(
                    task_dir.name,
                    "MISSING_CONTRACT",
                    "01-contract.md is required in every task bundle",
                    "01-contract.md",
                    0,
                )
            )
            continue
        try:
            text = contract_path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    task_dir.name,
                    "CONTRACT_UNREADABLE",
                    "cannot read 01-contract.md: " + str(exc),
                    "01-contract.md",
                    0,
                )
            )
            continue

        contract = None
        if not force_legacy:
            mapping, body_start = split_frontmatter(text)
            if mapping is not None:
                contract = contract_from_frontmatter(mapping, text, warnings)
        if contract is None:
            contract = contract_from_legacy(text, warnings)
            warnings.append(
                {
                    "task": contract.get("task_id") or task_dir.name,
                    "code": "LEGACY_FORMAT",
                    "message": "01-contract.md has no YAML frontmatter; parsed with the legacy table fallback",
                    "file": "01-contract.md",
                    "line": 1,
                }
            )
        contract["_text"] = text
        contracts.append((contract.get("task_id") or task_dir.name, contract))
        _validate_contract(task_dir, contract, text, config, findings, warnings)
        _scan_placeholders(contract.get("task_id") or task_dir.name, task_dir, config, findings)
        _check_topology(
            contract.get("task_id") or task_dir.name,
            contract,
            text,
            config,
            repo_root,
            findings,
            warnings,
        )
        _lint_qa_complexity(
            contract.get("task_id") or task_dir.name,
            task_dir,
            findings,
            warnings,
        )
        _lint_qa_mutation(
            contract.get("task_id") or task_dir.name,
            task_dir,
            findings,
            warnings,
        )


    _check_graph(contracts, findings)
    _check_change_proposals(contracts, changes_dir, findings, warnings)

    coverage = None
    if spec_path is not None:
        coverage = _build_coverage(spec_path, contracts)
        if not coverage["spec_anchors"]:
            warnings.append(
                {
                    "task": "",
                    "code": "SPEC_ANCHORS_EMPTY",
                    "message": "no #sec-* anchors found in the upstream spec: " + str(spec_path),
                    "file": str(spec_path),
                    "line": 0,
                }
            )
        for anchor in coverage["uncovered"]:
            if not require_full_coverage:
                continue
            findings.append(
                Finding(
                    "",
                    "SPEC_SECTION_UNCOVERED",
                    "spec anchor " + anchor + " is not referenced by any task contract",
                    str(spec_path),
                    0,
                )
            )
        for anchor in coverage["contract_anchors_missing_from_spec"]:
            message = "contract anchor " + anchor + " does not exist in the upstream spec"
            if strict_anchor:
                findings.append(Finding("", "ANCHOR_NOT_IN_SPEC", message, str(spec_path), 0))
            else:
                warnings.append(
                    {
                        "task": "",
                        "code": "ANCHOR_NOT_IN_SPEC",
                        "message": message,
                        "file": str(spec_path),
                        "line": 0,
                    }
                )

    return findings, warnings, len(contracts), coverage


def _write_result(errors, warnings, tasks_scanned, as_json, coverage=None):
    if as_json:
        payload = {
            "gate": "1",
            "passed": not errors,
            "tasks_scanned": tasks_scanned,
            "errors": [finding.to_dict() for finding in errors],
            "warnings": warnings,
        }
        if coverage is not None:
            payload["coverage"] = coverage
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return
    if errors:
        sys.stdout.write("Gate 1 FAILED: %d violation(s) in %d task bundle(s).\n" % (len(errors), tasks_scanned))
        for finding in errors:
            location = finding.file or "01-contract.md"
            if finding.line:
                location = location + ":" + str(finding.line)
            sys.stdout.write(
                "  [%s] %s: %s (%s)\n" % (finding.task or "-", finding.code, finding.message, location)
            )
    else:
        sys.stdout.write("Gate 1 PASSED: scanned %d task bundle(s).\n" % tasks_scanned)
    if coverage is not None:
        total = coverage["spec_anchors"]
        covered = len(coverage["covered"])
        sys.stdout.write(
            "Coverage: %d/%d spec anchors covered (%.1f%%); %d uncovered.\n"
            % (covered, total, coverage["coverage_ratio"] * 100, len(coverage["uncovered"]))
        )
        if coverage["uncovered"]:
            shown = coverage["uncovered"][:20]
            suffix = "" if len(shown) == len(coverage["uncovered"]) else " (+%d more)" % (
                len(coverage["uncovered"]) - len(shown)
            )
            sys.stdout.write("  uncovered: " + ", ".join(shown) + suffix + "\n")
        missing = coverage["contract_anchors_missing_from_spec"]
        if missing:
            sys.stdout.write("  anchors not in spec: " + ", ".join(missing[:20]) + "\n")
    for warning in warnings:
        sys.stdout.write(
            "  warning [%s] %s\n" % (warning.get("code", "WARNING"), warning.get("message", ""))
        )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="plan_linter",
        description="Gate 1 deterministic static checker for task bundles.",
    )
    parser.add_argument("--tasks-dir", default="./tasks", help="directory containing task bundles (default: ./tasks)")
    parser.add_argument("--config", default=None, help="path to a JSON config file that overrides the defaults")
    parser.add_argument("--json", action="store_true", help="print a single machine-readable JSON object")
    parser.add_argument("--legacy", action="store_true", help="parse every contract with the legacy table fallback")
    parser.add_argument("--no-placeholder-scan", action="store_true", help="disable the placeholder scan")
    parser.add_argument("--repo-root", default=None,
                        help="repository root used by the reverse topology check (default: current directory)")
    parser.add_argument("--no-topology", action="store_true", help="disable the reverse topology check")
    parser.add_argument("--strict-topology", action="store_true",
                        help="report reverse topology findings as Gate 1 errors instead of warnings")
    parser.add_argument("--spec", default=None,
                        help="upstream tech spec used to build the anchor coverage matrix")
    parser.add_argument("--require-full-coverage", action="store_true",
                        help="fail when any #sec-* spec anchor is not referenced by a task contract")
    parser.add_argument("--strict-anchor", action="store_true",
                        help="fail when a contract anchor does not exist in the upstream spec")
    parser.add_argument("--changes-dir", default=None,
                        help="brownfield change directory (default: proposals are not checked)")
    parser.add_argument("--coverage-out", default=None,
                        help="write the coverage matrix as JSON to this path (requires --spec)")
    parser.add_argument("--version", action="version", version="plan_linter " + VERSION)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config, config_warnings = load_config(args.config)
        if args.no_placeholder_scan:
            config["scan_placeholders"] = False
        if args.no_topology:
            config["check_topology"] = False
        if args.strict_topology:
            config["strict_topology"] = True
        tasks_root = Path(args.tasks_dir).expanduser()
        if not tasks_root.is_dir():
            sys.stderr.write("error: tasks directory does not exist: " + str(tasks_root) + "\n")
            return EXIT_USAGE
        repo_root = Path(args.repo_root).expanduser() if args.repo_root else Path.cwd()
        if not repo_root.is_dir():
            sys.stderr.write("error: --repo-root is not a directory: " + str(repo_root) + "\n")
            return EXIT_USAGE
        spec_path = None
        if args.spec:
            spec_path = Path(args.spec).expanduser()
            if not spec_path.is_file():
                sys.stderr.write("error: --spec file does not exist: " + str(spec_path) + "\n")
                return EXIT_USAGE
        changes_dir = Path(args.changes_dir).expanduser() if args.changes_dir else None
        if args.coverage_out and spec_path is None:
            sys.stderr.write("error: --coverage-out requires --spec\n")
            return EXIT_USAGE
        errors, warnings, scanned, coverage = lint(
            tasks_root,
            config,
            force_legacy=args.legacy,
            repo_root=repo_root,
            spec_path=spec_path,
            changes_dir=changes_dir,
            require_full_coverage=args.require_full_coverage,
            strict_anchor=args.strict_anchor,
        )
        warnings = config_warnings + warnings
        if args.coverage_out and coverage is not None:
            coverage_out = Path(args.coverage_out).expanduser()
            try:
                coverage_out.parent.mkdir(parents=True, exist_ok=True)
                coverage_out.write_text(
                    json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            except OSError as exc:
                sys.stderr.write("error: cannot write coverage report: " + str(exc) + "\n")
                return EXIT_USAGE
        _write_result(errors, warnings, scanned, args.json, coverage)
        return EXIT_PASS if not errors else EXIT_VIOLATIONS
    except UsageError as exc:
        sys.stderr.write("error: " + str(exc) + "\n")
        return EXIT_USAGE
    except YamlSubsetError as exc:
        sys.stderr.write("error: cannot parse 01-contract.md frontmatter: " + str(exc) + "\n")
        return EXIT_VIOLATIONS
    except Exception as exc:  # pragma: no cover - defensive
        sys.stderr.write("error: unexpected internal error: " + str(exc) + "\n")
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
