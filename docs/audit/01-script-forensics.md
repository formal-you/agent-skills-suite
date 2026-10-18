# Script Forensics Audit — .agents skills suite

> **Archived report (2026-10-18).** Preserved verbatim from the v2 audit. Original probe
> fixtures under `artifacts/skill-audit/` were temporary; captured evidence is under
> [`evidence/`](evidence/) and current behavior is defined by
> [`../skills-v2-spec.md`](../skills-v2-spec.md).

Auditor: script-forensics (task-1)
Date: 2026-10-18 (Asia/Shanghai)
Target: D:\WorkSpace\Agent研究\.agents (5 skills + rules + scripts + hooks.json)
Mode: read-only audit. No source file was modified (git status: no tracked changes). All fixtures/evidence live under artifacts/skill-audit/scripts/.

Environment observed empirically:
- Python 3.12.14 (D:\DEV\uv\python\cpython-3.12-windows-x86_64-none\python.exe)
- PowerShell (pwsh), Windows
- Harness: DeepSeek Harness (DSH), GUI http://127.0.0.1:56240
- DSH package: C:\Users\formal\AppData\Local\Programs\DeepSeek Harness\resources\app.asar (182,794,869 bytes), scanned as text for schema evidence.
- The session skill catalog DID load the five .agents/skills/* SKILL.md files (they are available skills in this session), so DSH reads .agents/skills/. It does NOT read .agents/hooks.json (see F-01).

Evidence artifacts (all reproducible):
- artifacts/skill-audit/scripts/run_plan_linter_matrix.py -> evidence/plan_linter_evidence.txt (24 cases)
- artifacts/skill-audit/scripts/run_rbac_payloads.py -> evidence/rbac_evidence.txt (27 payloads)
- artifacts/skill-audit/scripts/run_event_bus_experiments.py -> evidence/event_bus_evidence.txt (11 experiments)
- artifacts/skill-audit/scripts/run_portability_and_cli.py -> evidence/portability_cli_evidence.txt (portability + CLI matrix)
- Fixtures: artifacts/skill-audit/scripts/fixtures/**, copies: artifacts/skill-audit/scripts/portability/**

---

## 0. Severity summary

| ID | Sev | Finding | Affected |
| :--- | :--- | :--- | :--- |
| F-01 | BLOCKER | hooks.json is not a DSH hook config; its command path does not exist from the workspace root; matcher/payload/decision schemas are Antigravity-only | .agents/hooks.json:5,9,20,23; rbac_guard.py:17-27; event_bus_logger.py:104-112 |
| F-02 | BLOCKER | event_bus_logger never logs for tasks scaffolded from the shipped templates: template example rows already contain the idempotency markers | 04-process.template.md:33,37 |
| F-03 | HIGH | event_bus_logger falsely logs HANDOFF and then TASK_TERMINATED_DONE from literal [x] markers that sit under unchecked empty boxes in 02/03 templates | 02-dev-workspace.template.md:51; 03-qa-verification.template.md:63-64 |
| F-04 | HIGH | REWORK_REQUIRED handling is documented but completely absent from the code | event_bus_logger.py:8 |
| F-05 | HIGH | plan_linter does not enforce 6 of the 9 rules its SKILL.md claims (ADR inheritance, lint command, 4-doc presence, Task-ID/dir match, duplicate IDs, placeholder/invalid anchor) | plan_linter.py:60-137 |
| F-06 | HIGH | DAG cycle gate is bypassable by declaring dependencies outside the one hardcoded table row; dangling-dependency reporting stops after the first hit | plan_linter.py:44-52, 145-150 |
| F-07 | HIGH | plan_linter rejects semantically valid contracts written in any format other than the exact Chinese template strings (5 false-positive errors on an English equivalent) | plan_linter.py:39-93 |
| F-08 | HIGH | rbac_guard's documented Dev/QA protections fail on workspace-relative paths (tests/acceptance/, src/) | rbac_guard.py:54, 67 |
| F-09 | HIGH | rbac_guard role protections vanish when AGY_AGENT_ROLE is unset (it is never set by hooks.json or the repo) | rbac_guard.py:38-71 |
| F-10 | MEDIUM | rbac_guard false positives (04-process.template.md, docs/04-process.md.notes.txt) and unhandled arg-key names | rbac_guard.py:22, 30, 54, 67 |
| F-11 | MEDIUM | event_bus_logger silent no-ops: hardcoded ./tasks, missing append anchor loses the event while still mutating status, missing section/file ignored | event_bus_logger.py:43-47, 72-76, 94 |
| F-12 | MEDIUM | plan_linter swallows the only diagnostics when every dir lacks 01-contract.md (reports no task bundles instead) | plan_linter.py:186-201 |
| F-13 | MEDIUM | prd-generator global CLI command is NOT on PATH although SKILL.md says it is; spec-generator's global exe is a uv-tool snapshot, not workspace code | prd-generator/SKILL.md:32; spec-generator/SKILL.md:37 |
| F-14 | MEDIUM | skills are not self-contained: prd/spec run.py raise ModuleNotFoundError when the skill folder is copied outside the repo, contradicting the README 100% self-contained claim | .agents/skills/README.md:5; prd-generator/scripts/run.py:11-15; spec-generator/scripts/run.py:10-14 |
| F-15 | LOW | docs claim SHA-256 audit chain and PermissionError from hooks; neither exists | .agents/rules/README.md:24,28 |
| F-16 | LOW | hygiene: duplicate byte-identical linter copies; parsed-but-unused fields; unused imports; tool_name never used | plan_linter.py:16,28,81-83; rbac_guard.py:18 |

Positive controls (verified working) are listed in section 5.

---

## F-01 (BLOCKER) The whole RBAC hook layer is inert in this environment, and its configured command path is broken

Claim (.agents/rules/README.md:21-28): hooks are mounted through .agents/hooks.json and enforce rules at the physical level.

Evidence 1 — the configured commands do not exist at the documented working directory:
`
PS> python scripts/rbac_guard.py
python.exe: can't open file 'D:\WorkSpace\Agent研究\scripts\rbac_guard.py': [Errno 2] No such file or directory
exit=2
PS> python scripts/event_bus_logger.py
python.exe: can't open file 'D:\WorkSpace\Agent研究\scripts\event_bus_logger.py': [Errno 2] No such file or directory
exit=2
`
Root scripts/ contains only plan_linter.py, prd_generator.py, spec_generator.py (no rbac_guard.py, no event_bus_logger.py). The commands succeed only if the hook runner's CWD happens to be .agents/ (verified: Push-Location .agents; $null | python scripts/rbac_guard.py -> {"decision": "allow"}). Nothing documents that CWD, so the wiring is at best ambiguous, at worst dead.

Evidence 2 — DSH has no Antigravity hook support at all:
- Scanned the DSH app.asar: occurrences of PreToolUse = 0, write_to_file = 0, replace_file_content = 0, AGY_AGENT_ROLE = 0, .agents/hooks.json = 0.
- The only hook bridge plugins shipped are dsh-hooks-claude-code and dsh-hooks-codex (asar lines 324837-324838: Bridge plugin: run a Claude Code hooks.json / settings hook config on the DeepSeek Harness interception seams). Their config schema is the Claude Code {"hooks":{"PreToolUse":[...]}} shape; .agents/hooks.json instead has arbitrary top-level hook names (rbac-security-guard, event-bus-audit-logger) each containing PreToolUse.

Evidence 3 — the payload schema does not exist here; a DSH-shaped PreToolUse payload is allowed:
`
stdin: {"tool_name": "write", "tool_input": {"file_path": "tasks/task-001/04-process.md", "content": "x"}}
exit_code: 0  stdout: {"decision": "allow"}
stdin: {"hook_event_name": "PreToolUse", "tool_name": "edit", "tool_input": {"file_path": "tasks/task-001/04-process.md"}}
exit_code: 0  stdout: {"decision": "allow"}
`
rbac_guard.py:17-23 reads payload["toolCall"]["args"]["TargetFile" or "target_file"] only. DSH/Claude-Code tool names are Write/Edit/write/edit, and payloads use tool_name/tool_input; neither is handled.

Root cause: an Antigravity 2.0-only hook contract (matcher names, toolCall schema, decision JSON, timeout unit) was copied into a repo whose skills are loaded by DSH; there is no adapter, no documentation of the required runner, and the command uses a CWD-relative path that is wrong from the workspace root.

Impact: no physical enforcement of any RBAC rule. Everything in the section titled 强制安全与防作弊机制 (RBAC) is documentation-only. A Dev or QA agent can write 01-contract.md / tests/acceptance/ / src/ / 04-process.md with no interception.

Fix direction (not applied): either (a) delete the hook claim and present RBAC as prompt-only, or (b) ship a DSH-native hook config/bridge with DSH tool names and payload schema, and resolve script paths relative to the config file, not to an assumed CWD.

---

## F-02 (BLOCKER) event_bus_logger can never log for a task scaffolded from the shipped templates

Claim: 04-process.template.md is rendered per task and the bus appends HANDOFF/DONE rows. The script idempotency guards are string-presence checks:

event_bus_logger.py:38  if "[x] WAITING_FOR_QA" in ws_content and "HANDOFF_QA_REQUESTED" not in process_content:
event_bus_logger.py:68  if "[x] QA_PASSED" in qa_content and "TASK_TERMINATED_DONE" not in process_content:

But the example event rows shipped inside 04-process.template.md already contain both markers:
- 04-process.template.md:33  EV-05 ... HANDOFF_QA_REQUESTED ...
- 04-process.template.md:37  EV-09 ... TASK_TERMINATED_DONE ...

Experiment (e01): scaffold all four docs from the templates, run the real hook through stdin:
`
$ python .agents/scripts/event_bus_logger.py   (cwd = case root with tasks/task-001)
exit_code: 0  stdout: {}
RESULT: no file changed
`
Experiment (e06): same scaffold, and genuinely check 03's acceptance box, then run:
`
RESULT: no file changed
`
For the canonical scaffold the audit trail is permanently frozen: neither a real handoff nor a real QA pass ever appends an event. 04-process.md stays the sample template forever.

Root cause: string presence is used as a has-this-already-happened flag, but the template itself contains those strings as documentation/examples.

Impact: the automatic event-bus audit trail is dead on arrival for the intended task bundle format; 04-process.md never accumulates real history.

---

## F-03 (HIGH) Fresh/minimal scaffolds produce FALSE audit events from unchecked checkboxes

The templates ship the trigger token literally even though the real checkbox is unchecked:
- 02-dev-workspace.template.md:51  - [ ] 提测申请: [x] WAITING_FOR_QA
- 03-qa-verification.template.md:63  - [ ] 验收通过: [x] QA_PASSED
- 03-qa-verification.template.md:64  - [ ] 退回重修: [x] REWORK_REQUIRED

Experiment (e02): 02/03 straight from templates (nothing checked), 04-process minimal (status card + section 2 + note, without the sample EV rows). Run the hook once:
`
RESULT: 04-process.md CHANGED
- macro_status: "{{CURRENT_MACRO_STATUS}}"
+ macro_status: "VERIFYING"
- current_lock_holder: "{{CURRENT_LOCK_HOLDER}}"
+ current_lock_holder: "QAAgent"
+| EV-AUTO | 2026-10-17T21:34:03Z | HANDOFF_QA_REQUESTED | DevAgent | 提测申请发起，触发QA进场 | 1s |
`
No agent checked anything; the bus asserts Dev requested QA and moved the task to VERIFYING.

Experiment (e03): run the same hook a second time (again, no agent action):
`
RESULT: 04-process.md CHANGED
- macro_status: "VERIFYING"
+ macro_status: "DONE"
- current_lock_holder: "QAAgent"
+ current_lock_holder: "None"
+| EV-AUTO | 2026-10-17T21:34:03Z | TASK_TERMINATED_DONE | QAAgent | 验收测试全绿，签发完成 | 1s |
`
So two consecutive writes with zero human/agent intent mark the task DONE.

Root cause: same template-marker contamination as F-02, on the input side: substring matching cannot distinguish the documentation line that contains the token from a ticked checkbox.

Impact: fabricated audit records in the append-only event log; a task can be auto-completed without tests. This violates the objective-audit claim in event_bus_logger.py:1-9.

---

## F-04 (HIGH) REWORK_REQUIRED handling is documented but not implemented

event_bus_logger.py:7-8 documents: 捕获 03-qa-verification.md 的 [x] REWORK_REQUIRED -> 追加 REWORK_TRIGGERED 事件.
`
$ grep -n "REWORK" .agents/scripts/event_bus_logger.py
8:3. 捕获 03-qa-verification.md 的 [x] REWORK_REQUIRED -> 追加 REWORK_TRIGGERED 事件
`
The only occurrence is the docstring. Experiment (e04): 03 has REWORK_REQUIRED ticked, 04 minimal; run -> the script instead appends a (false) HANDOFF row from the 02 marker and never emits REWORK_TRIGGERED. No retry_count update, no macro_status rollback.

Root cause: update_process_file has only two branches (HANDOFF at :33-61, QA_PASSED at :63-89); the REWORK branch was never written.

Impact: failed QA is invisible to the audit bus; the retry/circuit-breaker story in 04-process.template.md:16 is not implemented.

---

## F-05 (HIGH) plan_linter does not enforce 6 of the 9 rules its SKILL.md promises

SKILL.md:103 claims: (1) touch_files <=3; (2) 50-250 lines; (3) origin_spec_anchor (#sec-*) AND adherence_adrs present with no unresolved placeholders; (4) type-check command, lint command and acceptance test file declared + at least 2 edge cases; (5) DAG acyclic.

Observed Gate 1 decisions (full outputs in plan_linter_evidence.txt):

| Case | Expected per SKILL.md | Observed | Verdict |
| :--- | :--- | :--- | :--- |
| c04 remove lint command line | FAIL | exit 0 Gate 1 PASSED | FALSE NEGATIVE |
| c05 remove both ADR inheritance lines | FAIL | exit 0 PASSED | FALSE NEGATIVE |
| c06 anchor = 02-tech-spec.md#{{SPEC_ANCHOR}} | FAIL (placeholder) | exit 0 PASSED | FALSE NEGATIVE |
| c06b anchor = foobar (no #sec-*) | FAIL | exit 0 PASSED | FALSE NEGATIVE |
| c07 only 01-contract.md, no 02/03/04 | FAIL | exit 0 PASSED (scanned 1 bundle) | FALSE NEGATIVE |
| c08 dir task-999-auth, contract Task ID task-001 | FAIL | exit 0 PASSED | FALSE NEGATIVE |
| c09 two dirs both declare task-001; one depends on nonexistent task-002 | FAIL | exit 0 PASSED (scanned 2 bundles) | FALSE NEGATIVE |
| c21 Task ID left as task-{{TASK_ID}} | FAIL | exit 0 PASSED (silently uses dir name) | FALSE NEGATIVE |
| c18 edge cases are 必须覆盖 {{SCENARIO_EDGE_1}} | FAIL (placeholder) | exit 0 PASSED | FALSE NEGATIVE |

Root cause (file:line):
- plan_linter.py:71-74 parses adherence_adrs but check_task_granularity (:98-137) never reads it.
- plan_linter.py:81-83 parses lint_cmd but it is never validated.
- plan_linter.py:66-68 accepts any token not starting with the mustache prefix as an anchor; no #sec-* format check and no placeholder search inside the token.
- plan_linter.py:185-188 only requires 01-contract.md; 02/03/04 are never checked.
- plan_linter.py:192 uses the contract Task ID as graph key and never compares it to the directory name.
- plan_linter.py:193 assigns task_dep_graph[task_id] and silently overwrites duplicate Task IDs (which also makes dangling deps disappear).
- plan_linter.py:90-92 only filters edge cases that START with the mustache prefix (c18 keeps counting placeholders embedded in prose).
- plan_linter.py:101 task_id = contract["task_id"] or dirname silently swallows an unparsable ID.

Impact: a task bundle full of placeholders, missing ADR inheritance, foreign directory IDs and duplicate IDs gets a green Gate 1 stamp. The zero-hallucination / zero-template-contamination promise (SKILL.md:3,8) is not backed by the deterministic gate.

---

## F-06 (HIGH) DAG cycle detection is bypassable by formatting; dangling deps are under-reported

plan_linter.py:44-52 only recognises dependencies written exactly as the bolded 前置依赖 label followed by a table pipe and a bracketed list. Any other spelling means no dependencies.

Experiment (c23): two bundles, Task IDs task-001-a and task-002-b, mutually dependent, with the dependency declared as plain text Dependencies: task-002-b / Dependencies: task-001-a instead of the table row:
`
exit_code: 0
[Gate 1 PASSED] 静态门禁全部通过！
   已扫描 2 个任务包 ...
`
A true mutual cycle passes Gate 1.

Also plan_linter.py:147-150 returns on the first non-existent dependency inside check_dag_cycles, so a bundle with multiple dangling deps only reports one (c10 reports exactly one error). Each task is checked independently before the graph is built, and nothing cross-validates that a dependency refers to a task whose directory/ID is consistent.

Impact: the headline DAG anti-deadlock gate (SKILL.md:105) only holds for one exact serialization of the dependency row.

---

## F-07 (HIGH) plan_linter rejects semantically valid contracts that do not use the exact Chinese template strings

Experiment (c22): an English contract with identical semantics (Task ID task-001, 120 lines, 2 touch files, anchor 02-tech-spec.md#sec-auth, ADR-001, mypy+ruff commands, acceptance test path, 2 boundary cases) but English field labels:
`
exit_code: 1
[Gate 1 FAILED] 质检未通过，共发现 5 项违规：
  1. [task-001] 粒度过小：预估代码量 0 行（下限 50 行）...
  2. [task-001] 缺失来源锚点：未指定 Tech Spec 对应章节...
  3. [task-001] DoD 静态门禁缺失：未提供具体的类型检查命令。
  4. [task-001] DoD 测试文件缺失：未绑定具体的验收测试文件路径。
  5. [task-001] DoD 边缘场景不足：...（当前提供: 0 个）。
`
The contract is materially compliant; only the labels differ. Root cause: every field is extracted by matching Chinese literals (Task ID label, 前置依赖, 预估代码量, 类型检查命令通过, 对应验收测试文件, 反向/边界场景用例). For a general-purpose reusable skill this hardcodes one language and one template dialect. English or restructured contracts are false-positive rejected, while the same contract with placeholders passes (F-05): the gate is simultaneously too strict on form and too lax on substance.

Impact: the skill cannot be reused outside this exact Chinese template dialect without editing the linter.

---

## F-08 (HIGH) rbac_guard documented Dev/QA protections fail on relative paths

Claim (rules/README.md:24-25): Dev writes to tests/acceptance/ are blocked; QA writes to src/ are blocked.

Observed (rbac_evidence.txt):
`
### p05 DEV writes tests/acceptance/ RELATIVE path
stdin: {"toolCall":{"name":"write_to_file","args":{"TargetFile":"tests/acceptance/test_auth.ts"}}}
AGY_AGENT_ROLE='DevAgent'
exit_code: 0  stdout: {"decision": "allow"}          <-- documented deny NOT enforced

### p06 DEV writes tests/acceptance/ ABSOLUTE path
TargetFile: "D:/WorkSpace/Agent研究/tests/acceptance/test_auth.ts"
stdout: {"decision": "deny", "reason": "【物理 RBAC 拦截】DevAgent 严禁篡改 tests/acceptance/ ..."}

### p13 QA writes src/ RELATIVE path
TargetFile: "src/auth.py"; AGY_AGENT_ROLE='QAAgent'
stdout: {"decision": "allow"}                          <-- documented deny NOT enforced

### p14 QA writes src/ ABSOLUTE path
stdout: {"decision": "deny", ...}

### p17 DEV tests/acceptance with WINDOWS backslashes (relative)
TargetFile: "tests\acceptance\test_auth.ts"; AGY_AGENT_ROLE='DevAgent'
stdout: {"decision": "allow"}
`
Root cause: rbac_guard.py:54 checks for the substring slash-tests-slash-acceptance-slash and :67 checks for slash-src-slash. The leading slash requires a parent directory; a workspace-relative path such as tests/acceptance/x.ts or src/a.py has no leading slash. The guard only fires for absolute paths (or paths under another directory), while Antigravity-style tool payloads normally carry workspace-relative TargetFile values. Windows backslashes are normalised (:27) but the missing leading slash remains.

Impact: the two flagship anti-cheat rules (Dev must not edit acceptance tests; QA must not edit src) are bypassed by the most natural path spelling. The protections that hold are 04-process.md (pure substring, no slash) and 01-contract / 03-qa / 02-dev (also pure substring).

---

## F-09 (HIGH) role-based protections are skipped entirely when AGY_AGENT_ROLE is unset

rbac_guard.py:38 reads os.environ.get("AGY_AGENT_ROLE", "").lower(); every role check (:41, :48, :61) is guarded by agent_role in [...].

Observed:
`
p10 NO ROLE writes 01-contract.md (documented immutable)
stdin: {"toolCall":{"name":"write_to_file","args":{"TargetFile":"tasks/task-001/01-contract.md"}}}
AGY_AGENT_ROLE=None
exit_code: 0  stdout: {"decision": "allow"}

p12 NO ROLE writes tests/acceptance/
AGY_AGENT_ROLE=None
stdout: {"decision": "allow"}

p11 role=planner writes 01-contract.md
stdout: {"decision": "allow"}
`
Nothing in hooks.json, the repo, or the skill docs sets AGY_AGENT_ROLE (DSH asar has 0 occurrences; repo-wide grep finds it only in rbac_guard.py). The 01-contract global-immutable rule therefore only applies if an out-of-band Antigravity runner injects that variable, and even then PlannerAgent may edit a contract after the fact (contradicting the IMMUTABLE wording in 01-contract.template.md:4).

Impact: the whole role model is opt-in and unenforced by the repository itself.

---

## F-10 (MEDIUM) rbac_guard false positives and schema gaps

Observed:
`
p03 the 04-process TEMPLATE source file
TargetFile: ".agents/skills/task-decomposition/resources/templates/04-process.template.md"
stdout: {"decision": "deny", ...}      <-- editing the source template is blocked

p04 harmless file that merely contains the name
TargetFile: "docs/04-process.md.notes.txt"
stdout: {"decision": "deny", ...}      <-- substring match, not a path-component match

p21 args has file_path only
{"toolCall":{"name":"write_to_file","args":{"file_path":"tasks/task-001/04-process.md"}}}
stdout: {"decision": "allow"}          <-- the file_path arg key is not read

p26 malformed JSON
stdout: {"decision": "ask", "reason": "RBAC 校验发生内部异常: ..."}
`
- :30 checks for the 04-process.md substring and also 04-process.template.md; any path containing that substring is denied, including the skill own template and unrelated .notes.txt files.
- :22 accepts only TargetFile/target_file. DSH/Claude-Code-style file_path is ignored (p21).
- :18 reads tool_name but never uses it.
- :88-90 emits a decision of ask on any internal error; ask is not part of the documented Antigravity allow/deny vocabulary and was not verified against any runner.
- :79-82 fail-open: empty stdin or an empty object returns allow.

Impact: legitimate edits of the template are blocked while renamed paths get through; the guard is a substring filter, not an RBAC engine.

---

## F-11 (MEDIUM) event_bus_logger silent failure modes

- Hardcoded CWD-relative tasks root (event_bus_logger.py:94 tasks_root = "./tasks"). Experiment e10: run the hook from the repo root while the task bundle lives elsewhere:
`
exit_code: 0  stdout: {}
RESULT: no file changed
`
The hook reports success (empty JSON, exit 0) even though it examined nothing; a runner cannot distinguish nothing-to-do from wrong working directory.
- Append anchor is a literal prose fragment (:43-47, :72-76 require the section-2 heading and the literal note line that starts with *(注：若验收失败). Experiment e07: remove the note line -> status card is rewritten but the event row is silently lost:
`
RESULT: 04-process.md CHANGED
- macro_status: "{{CURRENT_MACRO_STATUS}}"
+ macro_status: "VERIFYING"
... (no EV-AUTO row appended)
`
- If the section heading or 04-process.md is absent, the function returns silently (e08/e09: no change, exit 0).
- The handoff branch returns at :61, so a QA_PASSED transition is only noticed on the next hook invocation; the two events can never be written in one run.
- Timestamps come from datetime.now(timezone.utc) (:18-19), contradicting rules/README.md:28 which promises a SHA-256 audit chain; no hash is computed anywhere (grep finds only the REWORK docstring).

Impact: audit rows can be dropped with no error signal; the hook is unauditable itself.

---

## F-12 (MEDIUM) plan_linter swallows the only diagnostics when no bundle is valid

Experiment (c13): tasks/ contains one task dir with 02/03/04 but no 01-contract.md:
`
exit_code: 1
⚠️ 未发现任何任务包。
`
Expected (from plan_linter.py:187): [task-001] 缺失 01-contract.md 核心契约文件。
Root cause: errors are appended to all_errors, but at plan_linter.py:199-201 task_count == 0 returns False before the error list is printed (:208-213).
Related: an empty tasks dir also returns exit 1 (no task bundles, c12) and the default ./tasks on this repo root is empty, so the documented example command exits 1 out of the box (default_tasks_dir_on_repo_root case).

Impact: the most common bootstrap mistake (files in the wrong place / forgot the contract) produces a misleading message and hides the actionable error.

---

## F-13 (MEDIUM) Documented global CLI commands: prd-generator is missing; spec-generator is a snapshot

prd-generator/SKILL.md:32 and .agents/skills/README.md:63 claim prd-generator / prd_generator are registered on the system PATH and executable from any terminal.
`
### B01 global prd-generator on PATH
$ prd-generator --version
exit_code: 127(not found)   stderr: [WinError 2] 系统找不到指定的文件。

### B02 global prd_generator on PATH
$ prd_generator --version
exit_code: 127(not found)

### C01 global spec-generator on PATH
$ spec-generator --version
exit_code: 0  stdout: spec_generator 0.1.0
`
PATH resolution: Get-Command prd-generator, prd_generator -> nothing; spec-generator.exe and spec_generator.exe exist in C:\Users\formal\.local\bin. uv tool list shows spec-generator v0.1.0 installed as a uv tool (launcher dated 2026/10/10), i.e. a separate installed snapshot, not this workspace; python -m pip show agent-spec-suite says not found. .venv/Scripts contains prd-generator.exe but .venv is not on PATH.

All non-global entrypoints work: .agents/scripts/prd_generator.py, .agents/skills/*/scripts/run.py, scripts/*.py (B03-B05, C02-C03), and exit codes propagate (B14, C04, C11, D1-D3).

Impact: the documented copy-paste command fails for prd-generator on a fresh machine; the spec-generator path is environment-specific and may drift from the workspace source.

---

## F-14 (MEDIUM) The 100% self-contained / extractable claim is false for 2 of 3 scripted skills

Claim (.agents/skills/README.md:5): all skill packs follow a 100% self-contained standard and support whole-package extraction/distribution as generic plugins.

Experiment A: copy each skill dir to artifacts/skill-audit/scripts/portability/ and run its run.py:
`
### plan-linter run.py OUTSIDE repo
exit_code: 0  (help printed)                       -> self-contained

### prd-generator run.py OUTSIDE repo
exit_code: 1
Traceback ... File ".../portability/prd-generator/scripts/run.py", line 15, in <module>
  from prd_generator.cli import main
ModuleNotFoundError: No module named 'prd_generator'

### spec-generator run.py OUTSIDE repo
exit_code: 1
Traceback ... line 14, in <module>
  from spec_generator.cli import main
ModuleNotFoundError: No module named 'spec_generator'
`
Inside the repo both work (A3: --version OK even from a foreign CWD), because run.py computes Path(__file__).resolve().parents[4] (prd-generator/scripts/run.py:11, spec-generator/scripts/run.py:10), which is the repo root only for the canonical nesting .agents/skills/<name>/scripts/run.py. Copying the skill or any re-nesting breaks it.

Root cause: the skill delegates to the top-level engine package (prd_generator/, spec_generator/) instead of carrying or installing it; the self-contained claim only covers templates, not code.

Impact: the skills cannot be published/extracted as claimed; distribution must mention the engine package and the exact directory depth.

---

## F-15 (LOW) Documentation overclaims in the RBAC section

rules/README.md:24 says the guard immediately raises PermissionError; the script only returns JSON decisions and no PermissionError exists (grep). rules/README.md:28 promises a SHA-256 audit chain; no hashing exists (grep in event_bus_logger.py finds only the REWORK docstring at line 8). Doc-vs-code drift, not a new bug.

---

## F-16 (LOW) Hygiene / drift risks

- .agents/scripts/plan_linter.py and .agents/skills/plan-linter/scripts/plan_linter.py are byte-identical (SHA-256 prefix B225987DC09A5D6B) but stored twice; nothing enforces sync. tests/unit/test_plan_linter.py only asserts both exist.
- plan_linter.py:16 imports Set, Tuple unused; :28 max_touch_files never read; :81-83 lint_cmd parsed but never validated; :98 task_dir parameter only used for the fallback name.
- rbac_guard.py:18 tool_name read but never used.
- tests/unit/test_plan_linter.py:23-73 builds contracts in a synthetic layout that differs from the shipped template; none of the six tests exercises a template-scaffolded bundle, an unfilled template, ADR absence, lint-command absence, 02/03/04 absence, duplicate IDs, or English contracts. All 6 tests pass while F-05/F-06/F-07 are undetected by the suite (python -m unittest tests.unit.test_plan_linter -v: Ran 6 tests, OK).

---

## 5. What was verified to work (positive controls)

1. plan_linter, all four entrypoints (.agents/scripts/plan_linter.py, skill copy, skill run.py, root scripts/plan_linter.py) give identical PASS/FAIL and exit codes on a valid Chinese-format bundle (c03_*). CRLF bundles also pass (c20).
2. plan_linter correctly rejects: 4 touch files (c15: 爆炸半径超标：允许修改 4 个文件), 30/300 lines (c16), missing Tech Spec anchor (c17), dangling dependency (c10), a true cycle expressed in the canonical table row (c11: DAG 检测到循环依赖死锁！涉及任务: ['task-001-a', 'task-002-b']), and a mixed dir missing 01-contract (c14).
3. plan_linter is genuinely portable: the copied skill passes/fails the same fixtures (A2), and run.py resolves its own script without the repo.
4. rbac_guard correctly denies: 04-process.md by substring for absolute/relative/uppercase paths (p01,p02,p19), 01-contract.md for dev/qa (p07), 03-qa-verification.md for dev (p08), 02-dev-workspace.md for qa (p15), and absolute-path tests/acceptance (p06) / absolute-path src (p14). It fails open only on empty/malformed input.
5. event_bus_logger works on a hand-written minimal 04-process.md without the poisoned example rows: handoff is logged with a timestamp and status VERIFYING (e02 diff), and a subsequent genuine QA_PASSED appends TASK_TERMINATED_DONE (e05). HANDOFF logging is idempotent (no duplicate row).
6. CLI: both engines documented subcommands/flags exist and work — prd-generator run --idea / --idea-file / --dry-run / --mode / --answers, lint (file + dir, exit 1 on mustache placeholders and TBD stubs); spec-generator run --prd / --prd DIR -r / --dry-run / --mode, top-level and subcommand forms, both global spec-generator and in-repo wrappers. Dry-run writes nothing (0 disk mutations verified by file listing). Exit codes propagate through run.py wrappers.
7. diagnose-windows-sandbox-acl: PowerShell AST parse reports 0 syntax errors (parse-only; no repair executed). This skill is the only one written for DSH; it references DSH sandbox semantics while the other four are Antigravity-specific.

---

## 6. Priority recommendations (for the remediation owner)

P0 (before calling the suite reusable):
1. Remove or replace .agents/hooks.json: either delete the physical-enforcement claim, or port rbac_guard/event_bus_logger to the target harness (DSH hook schema, DSH tool names, absolute script paths). Verify with one end-to-end interception test per rule.
2. Strip trigger markers out of the templates (use a distinct token or a fenced example block that the logger ignores), and make the logger detect the checkbox state structurally, not by substring. Add a regression fixture that scaffolds from the templates and asserts 0 events, then 1 real event after a genuine checkbox change.
3. Fix rbac_guard path matching: match path components (tests/acceptance/ anywhere, src/ at the workspace root) instead of leading-slash substrings; root the role explicitly; add tests for relative paths.

P1:
4. Implement the plan_linter rules its SKILL.md advertises (ADR presence, lint cmd, 02/03/04 files, Task ID vs directory, duplicate IDs, placeholder/anchor format) or delete those claims from SKILL.md. Add a self-test that runs the linter against the shipped templates.
5. Move dependency parsing to a documented machine-readable block and detect cycles regardless of bullet/table spelling; report all dangling deps, not just the first.
6. Make event_bus_logger anchor insertion structural (find the section-2 table end / parse it) instead of literal-note replace; fail loudly on missing files/CWD.

P2:
7. De-fragment entrypoints: single implementation plus thin wrappers; test behavior equality.
8. Make prd/spec skills genuinely self-contained (vendor the engine or document the install), fix or remove the PATH claim, and pin the exact invocation in SKILL.md.
9. Localise the linter field vocabulary (accept English and Chinese labels) or declare the contract language as a hard requirement.

---

## 7. Compliance / cleanup

- No file outside artifacts/skill-audit/scripts/ was written. git status --porcelain shows no tracked modifications; the only added path is untracked artifacts/skill-audit/ (plus pre-existing untracked .agents/skills/diagnose-windows-sandbox-acl/, agent-core/, etc. that were present before this audit).
- No temp copies outside the scope: portability copies and CLI outputs are under artifacts/skill-audit/scripts/{portability,fixtures/cli-out}.
- The repo tasks/ directory is empty and was used read-only by the e10 CWD experiment; no task files were created there.
