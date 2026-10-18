#!/usr/bin/env python3
"""Scaffold a brownfield change proposal and exactly one four-document task bundle.

A brownfield change needs an existing base specification: the proposal records the
base spec sha256, the impact anchors and the incremental diff, and the task bundle
reuses the task-decomposition templates so Gate 1 keeps working. The helper is
stdlib-only and never imports repository packages.

Exit codes: 0 success; 1 content-gate failure (reserved); 2 usage or refusal;
3 unexpected internal error.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

__version__ = "3.0.0"

EXIT_OK = 0
EXIT_GATE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

CHANGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ANCHOR_PATTERN = re.compile(r"^#sec-[a-z0-9-]+$")
ANCHOR_TOKEN_PATTERN = re.compile(r"#sec-[a-z0-9-]+")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[A-Z0-9_]+\}\}")
TOUCH_ENTRY_PATTERN = re.compile(r"^(create|modify):(.+)$")
SIZE_CLASSES = ("standard", "micro")
KINDS = ("add", "modify", "remove")
MAX_TOUCH_FILES = 3

PROPOSAL_TEMPLATE = Path("assets") / "templates" / "proposal.template.md"

BUNDLE_DOCUMENTS = (
    "01-contract.md",
    "02-dev-workspace.md",
    "03-qa-verification.md",
    "04-process.md",
)

INLINE_CONTRACT = """---
# Task contract scaffolded by the inline fallback of the change skill.
task_id: "{{TASK_ID}}"
title: "{{TASK_TITLE}}"
module: "{{MODULE_NAME}}"
dependencies: []
estimated_lines: {{ESTIMATED_LINES}}
touch_files:
  - action: create
    path: "{{TOUCH_FILE_1}}"
  - action: modify
    path: "{{TOUCH_FILE_2}}"
origin_spec_anchor: "#sec-{{MODULE_SLUG}}"
adherence_adrs: ["{{ADR_ID_1}}"]
dod:
  type_check: "{{TYPE_CHECK_COMMAND}}"
  lint: "{{LINT_COMMAND}}"
  test_file: "{{TEST_FILE_PATH}}"
  edge_cases:
    - "{{EDGE_CASE_1}}"
    - "{{EDGE_CASE_2}}"
---

# Task {{TASK_ID}}: {{TASK_TITLE}}

## 1. Goal and scope

{{GOAL_AND_SCOPE}}

## 2. Out of scope

{{OUT_OF_SCOPE}}

## 3. Blast radius

Only the paths declared in frontmatter touch_files may be created or modified.

## 4. Behavioral contract and invariants

1. Input validation: {{INVARIANT_INPUT_VALIDATION}}
2. State transitions: {{INVARIANT_STATE_TRANSITIONS}}
3. Idempotency and data consistency: {{INVARIANT_IDEMPOTENCY}}

## 5. Inherited architecture decisions

{{INHERITED_ADR_SUMMARY}}

## 6. Verifiability notes

Type check, lint, acceptance test file and edge cases are declared in the frontmatter dod object.

## 7. Notes and open questions

{{NOTES}}
"""

INLINE_DEV = """# Dev Workspace

> Owner: Dev agent; read-only for Planner and QA. Fill the tables and sections while
> implementing the task declared in 01-contract.md. Do not edit 01-contract.md,
> 03-qa-verification.md or 04-process.md.

## 1. Execution metadata

| Field | Value |
| :--- | :--- |
| Dev agent |  |
| Branch |  |
| Base commit |  |
| Handoff commit |  |
| Handoff time (UTC) |  |

## 2. Implementation notes

## 3. Actual changes

| Action (create/modify) | Path | Approx. lines |
| :--- | :--- | :--- |

## 4. Self-verification

- [ ] Type check passes
- [ ] Lint passes
- [ ] Existing project/unit tests pass
- [ ] Every declared edge case is covered
- [ ] No changed path falls outside touch_files

## 5. Handoff to QA

- [ ] WAITING_FOR_QA
"""

INLINE_QA = """# QA Verification

> Owner: QA agent; read-only for Planner and Dev. Fill the matrix and evidence while
> verifying the task declared in 01-contract.md. Do not edit 01-contract.md,
> 02-dev-workspace.md or 04-process.md.

## 1. Verification metadata

| Field | Value |
| :--- | :--- |
| QA agent |  |
| Reviewed commit |  |
| Environment |  |
| Attempt |  |
| Verdict time (UTC) |  |

## 2. Test matrix

| Case ID | Category | Scenario / attack vector | Expected result | Status |
| :--- | :--- | :--- | :--- | :--- |
| TC-01 | Normal path |  |  |  |
| TC-02 | Boundary |  |  |  |

## 3. Execution evidence

| Field | Value |
| :--- | :--- |
| Command |  |
| Result |  |
| Tests (total / passed / failed) |  |

## 4. Boundary and anti-cheat audit

- [ ] Every changed path is listed in 01-contract.md touch_files
- [ ] Dev did not modify tests/acceptance/ or 01-contract.md

## 5. Verdict

Check exactly one box:

- [ ] QA_PASSED
- [ ] REWORK_REQUIRED

## 6. Verdict notes
"""

INLINE_PROCESS = """# Task {{TASK_ID}}: Process and Audit Trail (derived)

> Derived file. Do not hand-edit; repository tooling appends events. The authoritative
> audit trail is git history plus the repository CI audit.

## 1. Status

```yaml
task_id: "{{TASK_ID}}"
macro_status: "TODO"
micro_phase: "UNASSIGNED"
current_lock_holder: "None"
retry_count: 0
last_heartbeat: ""
```

## 2. Event Log

| Event ID | Timestamp (UTC) | Event Code | Actor | Payload / Evidence | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |

## 3. Notes
"""


class ChangeError(Exception):
    """Error carrying the process exit code to use."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def skill_dir():
    """Return the change skill directory (never the repository root)."""
    return Path(__file__).resolve().parent.parent


def proposal_template_path():
    return skill_dir() / PROPOSAL_TEMPLATE


def sibling_scaffold_path():
    """The task-decomposition scaffolder, resolved relative to this script."""
    return Path(__file__).resolve().parent.parent.parent / "task-decomposition" / "scripts" / "scaffold_task.py"


def relative_posix(path, root):
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.resolve().as_posix()


def resolve_path(value, root):
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def sanitize_title(raw):
    title = " ".join(raw.split())
    return title.replace('"', "'")


def parse_touch_files(raw):
    entries = []
    warnings = []
    if not raw:
        return entries, warnings
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        match = TOUCH_ENTRY_PATTERN.match(item)
        if not match:
            raise ChangeError(
                "invalid --touch-files entry " + repr(item) + ": expected create:<path> or modify:<path>",
                EXIT_USAGE,
            )
        action = match.group(1)
        path = match.group(2).strip().replace("\\", "/")
        if not path:
            raise ChangeError("--touch-files entry has an empty path: " + repr(item), EXIT_USAGE)
        absolute = path.startswith("/") or re.match(r"^[A-Za-z]:", path) is not None
        if absolute or ".." in path.split("/"):
            raise ChangeError(
                "--touch-files path must stay inside the repository: " + path, EXIT_USAGE
            )
        entries.append({"action": action, "path": path})
    if len(entries) > MAX_TOUCH_FILES:
        warnings.append(
            "touch_files has %d entries; the plan-linter default limit is %d"
            % (len(entries), MAX_TOUCH_FILES)
        )
    return entries, warnings


def render_proposal(template_text, values):
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    leftovers = sorted(set(PLACEHOLDER_PATTERN.findall(rendered)))
    if leftovers:
        raise ChangeError(
            "proposal template has unmapped placeholders: " + ", ".join(leftovers), EXIT_INTERNAL
        )
    return rendered


def apply_contract_context(text, change_id, size_class, anchor, estimated_lines, dependencies, touch_files):
    """Fill the scaffolded contract frontmatter and the unambiguous body placeholders."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ChangeError("generated contract has no YAML frontmatter", EXIT_INTERNAL)
    close = None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            close = index
            break
    if close is None:
        raise ChangeError("generated contract has unterminated YAML frontmatter", EXIT_INTERNAL)

    output = [lines[0]]
    seen = set()
    index = 1
    while index < close:
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            output.append(line)
            index += 1
            continue
        top_level = not line[:1].isspace()
        key = stripped.split(":", 1)[0] if top_level and ":" in stripped else None
        if key == "touch_files" and touch_files is not None:
            output.append("touch_files:\n")
            for entry in touch_files:
                output.append("  - action: " + entry["action"] + "\n")
                output.append('    path: "' + entry["path"] + '"\n')
            index += 1
            # consume the template's placeholder touch-file entries
            while index < close and lines[index][:1].isspace() and lines[index].strip():
                index += 1
            continue
        if key == "change_id":
            output.append('change_id: "' + change_id + '"\n')
            seen.add("change_id")
            index += 1
            continue
        if key == "size_class":
            output.append('size_class: "' + size_class + '"\n')
            seen.add("size_class")
            index += 1
            continue
        if key == "origin_spec_anchor":
            output.append('origin_spec_anchor: "' + anchor + '"\n')
            index += 1
            continue
        if key == "estimated_lines" and estimated_lines is not None:
            output.append("estimated_lines: " + str(estimated_lines) + "\n")
            index += 1
            continue
        if key == "dependencies" and dependencies is not None:
            rendered_deps = ", ".join('"' + dependency + '"' for dependency in dependencies)
            output.append("dependencies: [" + rendered_deps + "]\n")
            index += 1
            continue
        output.append(line)
        index += 1

    missing = [key for key in ("change_id", "size_class") if key not in seen]
    if missing:
        for position, line in enumerate(output):
            if line.startswith("title:"):
                additions = []
                if "change_id" in missing:
                    additions.append('change_id: "' + change_id + '"\n')
                if "size_class" in missing:
                    additions.append('size_class: "' + size_class + '"\n')
                output[position + 1 : position + 1] = additions
                break
        else:
            raise ChangeError("cannot locate the title field in the generated contract", EXIT_INTERNAL)

    rendered = "".join(output) + "".join(lines[close:])
    rendered = rendered.replace(
        "{{GOAL_AND_SCOPE}}",
        "Implement the bounded incremental change described by the change proposal; keep the scope "
        "to the declared touch files and the existing specification anchor.",
    )
    rendered = rendered.replace(
        "{{OUT_OF_SCOPE}}",
        "Any path outside touch_files, any new specification section or anchor, and any architecture "
        "change (escalate to the spec-generator skill instead).",
    )
    rendered = rendered.replace(
        "{{NOTES}}",
        "No open questions recorded at scaffold time; append Planner open questions here instead of "
        "inventing behavior.",
    )
    return rendered


def create_inline_bundle(task_target, change_id, title, force):
    """Minimal stdlib fallback used when the task-decomposition scaffolder is absent."""
    task_target.mkdir(parents=True, exist_ok=True)
    documents = {
        "01-contract.md": INLINE_CONTRACT.replace("{{TASK_ID}}", change_id).replace("{{TASK_TITLE}}", title),
        "02-dev-workspace.md": INLINE_DEV,
        "03-qa-verification.md": INLINE_QA,
        "04-process.md": INLINE_PROCESS.replace("{{TASK_ID}}", change_id),
    }
    for name, content in documents.items():
        destination = task_target / name
        if destination.exists() and not force:
            raise ChangeError(str(destination) + " already exists; pass --force to overwrite", EXIT_USAGE)
        destination.write_text(content, encoding="utf-8")
    return task_target / "01-contract.md"


def create_bundle_with_sibling(sibling, tasks_dir, change_id, title, size_class, force, repo_root):
    command = [
        sys.executable,
        str(sibling),
        "--task-id",
        change_id,
        "--title",
        title,
        "--tasks-dir",
        str(tasks_dir),
        "--change-id",
        change_id,
        "--size-class",
        size_class,
    ]
    if force:
        command.append("--force")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            cwd=str(repo_root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ChangeError("cannot run " + str(sibling) + ": " + str(exc), EXIT_INTERNAL)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ChangeError(
            "task-decomposition scaffolder failed with exit %d: %s" % (result.returncode, detail),
            EXIT_INTERNAL,
        )
    contract = tasks_dir / change_id / "01-contract.md"
    if not contract.is_file():
        raise ChangeError(
            "task-decomposition scaffolder did not create " + str(contract), EXIT_INTERNAL
        )
    return contract, (result.stdout or "")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="scaffold_change.py",
        description="Scaffold a brownfield change proposal plus exactly one four-document task bundle.",
        epilog=(
            "Exit codes: 0 success, 1 content-gate failure, 2 usage/refusal, 3 unexpected error. "
            "Example: python scaffold_change.py --change-id CHG-001-rate-limit "
            "--title \"Rate limit login attempts\" --anchor \"#sec-auth-tokens\" "
            "--touch-files \"modify:src/auth/rate_limit.py\" --size-class micro "
            "--estimated-lines 40 --repo-root ."
        ),
    )
    parser.add_argument("--change-id", required=True, help="Change id; also the proposal and task-bundle directory name.")
    parser.add_argument("--title", required=True, help="Short human title of the change.")
    parser.add_argument("--anchor", required=True, help="Existing spec anchor the change modifies, e.g. #sec-auth-tokens.")
    parser.add_argument(
        "--kind",
        default="modify",
        choices=KINDS,
        help="Kind of change: add, modify or remove (default: modify).",
    )
    parser.add_argument(
        "--touch-files",
        default=None,
        help="Comma separated create:<path>,modify:<path> entries; 1-3 entries.",
    )
    parser.add_argument("--estimated-lines", type=int, default=None, help="Estimated net diff lines for the contract.")
    parser.add_argument("--dependencies", default=None, help="Comma separated task ids the bundle depends on.")
    parser.add_argument(
        "--size-class",
        default="standard",
        choices=SIZE_CLASSES,
        help="Diff budget class: standard (default) or micro.",
    )
    parser.add_argument("--spec", default=None, help="Base specification (default: .specs/02-tech-spec.md under --repo-root).")
    parser.add_argument("--changes-dir", default=None, help="Change root (default: .specs/changes under --repo-root).")
    parser.add_argument("--tasks-dir", default=None, help="Task root (default: tasks under --repo-root).")
    parser.add_argument("--repo-root", default=".", help="Repository root; all relative paths resolve under it (default: .).")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing change directory and task bundle.")
    parser.add_argument("--dry-run", action="store_true", help="List the files that would be created; write nothing.")
    parser.add_argument("--json", action="store_true", help="Print a single machine-readable JSON object.")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser


def run(args):
    repo_root = resolve_path(args.repo_root, Path.cwd())
    if not repo_root.is_dir():
        raise ChangeError("--repo-root is not a directory: " + str(repo_root), EXIT_USAGE)

    change_id = args.change_id.strip()
    if not CHANGE_ID_PATTERN.fullmatch(change_id):
        raise ChangeError(
            "invalid --change-id: use letters, digits, '.', '_' or '-', starting with a letter or digit",
            EXIT_USAGE,
        )
    title = sanitize_title(args.title)
    if not title:
        raise ChangeError("--title must not be empty", EXIT_USAGE)
    anchor = args.anchor.strip()
    if not ANCHOR_PATTERN.fullmatch(anchor):
        raise ChangeError(
            "invalid --anchor " + repr(args.anchor) + ": expected #sec-[a-z0-9-]+", EXIT_USAGE
        )

    spec_path = resolve_path(args.spec or ".specs/02-tech-spec.md", repo_root)
    if not spec_path.is_file():
        raise ChangeError(
            "base spec not found: "
            + str(spec_path)
            + " (brownfield changes require an existing spec; run spec-generator first)",
            EXIT_USAGE,
        )

    try:
        spec_text = spec_path.read_text(encoding="utf-8", errors="replace")
        spec_sha256 = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ChangeError("cannot read the base spec: " + str(exc), EXIT_INTERNAL)
    spec_anchors = set(ANCHOR_TOKEN_PATTERN.findall(spec_text))
    if anchor not in spec_anchors:
        raise ChangeError(
            "anchor "
            + anchor
            + " is not present in "
            + relative_posix(spec_path, repo_root)
            + "; reuse an existing #sec-* anchor instead of inventing one",
            EXIT_USAGE,
        )

    changes_root = resolve_path(args.changes_dir or ".specs/changes", repo_root)
    tasks_root = resolve_path(args.tasks_dir or "tasks", repo_root)
    change_target = (changes_root / change_id).resolve()
    task_target = (tasks_root / change_id).resolve()
    if change_target.parent != changes_root:
        raise ChangeError("--change-id escapes --changes-dir", EXIT_USAGE)
    if task_target.parent != tasks_root:
        raise ChangeError("--change-id escapes --tasks-dir", EXIT_USAGE)

    if change_target.exists() and not args.force:
        raise ChangeError(
            str(change_target) + " already exists; pass --force to overwrite", EXIT_USAGE
        )
    if task_target.exists() and not args.force:
        raise ChangeError(
            str(task_target) + " already exists; pass --force to overwrite", EXIT_USAGE
        )

    touch_files, warnings = parse_touch_files(args.touch_files)
    if args.size_class == "micro":
        if len(touch_files) > 1:
            warnings.append(
                "size_class micro targets exactly one touch file; the Gate 1 default micro_max_touch_files is 1"
            )
        if args.estimated_lines is not None and not (10 <= args.estimated_lines <= 49):
            warnings.append(
                "size_class micro has a default budget of 10-49 estimated lines;"
                " the plan-linter config is authoritative"
            )
    if args.estimated_lines is not None and args.estimated_lines < 1:
        raise ChangeError("--estimated-lines must be a positive integer", EXIT_USAGE)

    dependencies = None
    if args.dependencies is not None:
        dependencies = []
        for chunk in args.dependencies.split(","):
            dependency = chunk.strip()
            if not dependency:
                continue
            if not CHANGE_ID_PATTERN.fullmatch(dependency):
                raise ChangeError("invalid --dependencies entry: " + repr(dependency), EXIT_USAGE)
            dependencies.append(dependency)

    template_path = proposal_template_path()
    if not template_path.is_file():
        raise ChangeError("missing proposal template: " + str(template_path), EXIT_USAGE)
    values = {
        "CHANGE_ID": change_id,
        "TITLE": title,
        "KIND": args.kind,
        "BASE_SPEC": relative_posix(spec_path, repo_root),
        "BASE_SPEC_SHA256": spec_sha256,
        "ANCHOR": anchor,
        "CREATED": datetime.date.today().isoformat(),
        "TOUCH_FILES_LINE": (
            ", ".join(chr(96) + entry["path"] + chr(96) + " (" + entry["action"] + ")" for entry in touch_files)
            if touch_files
            else chr(96) + "<repo-relative path>" + chr(96) + " (create or modify)"
        ),
        "AFFECTED_PATHS": (
            "\n".join("- " + chr(96) + entry["path"] + chr(96) + " (" + entry["action"] + ")" for entry in touch_files)
            if touch_files
            else "- " + chr(96) + "<repo-relative path>" + chr(96) + " (create or modify)"
        ),
    }
    proposal_text = render_proposal(template_path.read_text(encoding="utf-8"), values)

    proposal_path = change_target / "proposal.md"
    contract_path = task_target / "01-contract.md"
    sibling = sibling_scaffold_path()
    if sibling.is_file():
        bundle_source = "sibling"
    else:
        bundle_source = "inline-fallback"

    if args.dry_run:
        planned = [proposal_path] + [task_target / name for name in BUNDLE_DOCUMENTS]
        payload = {
            "tool": "scaffold_change",
            "dry_run": True,
            "change_id": change_id,
            "size_class": args.size_class,
            "bundle_source": bundle_source,
            "would_create": [relative_posix(path, repo_root) for path in planned],
            "warnings": warnings,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            for path in planned:
                print("[dry-run] would create " + relative_posix(path, repo_root))
            print("[dry-run] no files written (bundle source: " + bundle_source + ")")
        return EXIT_OK

    created_change_dir = not change_target.exists()
    created_task_dir = not task_target.exists()
    bundled_output = ""
    try:
        change_target.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(proposal_text, encoding="utf-8")
        if sibling.is_file():
            contract_path, bundled_output = create_bundle_with_sibling(
                sibling, tasks_root, change_id, title, args.size_class, args.force, repo_root
            )
        else:
            if not args.json:
                print(
                    "warning: sibling task-decomposition scaffolder not found at "
                    + str(sibling)
                    + "; using the inline four-document fallback",
                    file=sys.stderr,
                )
            contract_path = create_inline_bundle(task_target, change_id, title, args.force)
        contract_text = contract_path.read_text(encoding="utf-8")
        contract_text = apply_contract_context(
            contract_text,
            change_id=change_id,
            size_class=args.size_class,
            anchor=anchor,
            estimated_lines=args.estimated_lines,
            dependencies=dependencies,
            touch_files=touch_files or None,
        )
        contract_path.write_text(contract_text, encoding="utf-8")
    except ChangeError:
        if created_change_dir:
            shutil.rmtree(change_target, ignore_errors=True)
        if created_task_dir:
            shutil.rmtree(task_target, ignore_errors=True)
        raise
    except OSError as exc:
        if created_change_dir:
            shutil.rmtree(change_target, ignore_errors=True)
        if created_task_dir:
            shutil.rmtree(task_target, ignore_errors=True)
        raise ChangeError("writing the change scaffold failed: " + str(exc), EXIT_INTERNAL)

    remaining = sorted(set(PLACEHOLDER_PATTERN.findall(contract_text)))
    payload = {
        "tool": "scaffold_change",
        "change_id": change_id,
        "title": title,
        "kind": args.kind,
        "size_class": args.size_class,
        "anchor": anchor,
        "base_spec": relative_posix(spec_path, repo_root),
        "base_spec_sha256": spec_sha256,
        "proposal": relative_posix(proposal_path, repo_root),
        "task_bundle": relative_posix(task_target, repo_root),
        "bundle_source": bundle_source,
        "remaining_placeholders": remaining,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if bundled_output:
            sys.stdout.write(bundled_output)
        print("created proposal: " + relative_posix(proposal_path, repo_root))
        print("created task bundle: " + relative_posix(task_target, repo_root) + " (" + bundle_source + ")")
        for warning in warnings:
            print("warning: " + warning)
        if remaining:
            print("remaining contract placeholders for the Planner: " + ", ".join(remaining))
        else:
            print("no contract placeholders remain")
    return EXIT_OK


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ChangeError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return exc.code
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        print("error: unexpected failure: " + str(exc), file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
