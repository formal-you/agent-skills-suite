# Content Consistency Audit — .agents Skill Suite

> **Archived report (2026-10-18).** Preserved verbatim from the v2 audit. Original probe
> fixtures under `artifacts/skill-audit/` were temporary; captured evidence is under
> [`evidence/`](evidence/) and current behavior is defined by
> [`../skills-v2-spec.md`](../skills-v2-spec.md).

- **Task**: task-2 (Content consistency audit: SKILL.md, rules, templates, references)
- **Phase**: AUDIT (read-only; no source file was modified)
- **Auditor**: teammate `content-consistency`
- **Scope**: `.agents/skills/README.md`, 5 x `SKILL.md`, `references/*.md`, `resources/templates/**`, `.agents/rules/*.md`, `.agents/hooks.json`, `.agents/scripts/{rbac_guard,event_bus_logger}.py`, `AGENTS.md`, root `README.md` sections describing `.agents`, plus `task-templates/`, `spec-templates/` and `docs/specs/PLANNER_LINTER_DESIGN.md` where they contradict the above.
- **Write scope**: only `artifacts/skill-audit/content/`. Probe scripts and scratch task bundles live in `artifacts/skill-audit/content/_probe/`.
- **Method**: every path/command/flag/exit code was checked on this filesystem; duplicated files were SHA-256 compared; template copies were instantiated and run through the real `plan_linter.py`; `event_bus_logger.py` and `rbac_guard.py` were imported and exercised against template copies; the generators were run on a deliberately neutral idea.

## Verdict

The suite is a coherent **demo of an Antigravity-specific pipeline**, not a general-purpose reusable skill pack.

- **5 BLOCKERS**: the hook layer is dead/unenforced, templates contain live trigger markers, the audit template defeats its own logger, the "100% self-contained" claim is false, and RBAC is not physically enforced.
- **12 HIGH**: 3-vs-4 document contradiction, contract-field vocabulary that the validator cannot see, unfilled templates passing Gate 1, unimplemented SHA-256 audit chain, event/status name drift, hardcoded domain stack in "neutral" templates, overstated validator capabilities, contamination claim contradicted by the suite's own generator, a non-existent execution engine, false global-CLI claim, template duplication drift, and weak trigger frontmatter.
- **12 MEDIUM / 6 LOW**: language inconsistency, stale template examples, cwd-ambiguous copy instructions, role-roster drift, silent hook failure modes, weak PRD lint coverage, non-atomic generation, undocumented 5th skill, and small link/name nits.

Severity: **blocker** = must fix before this can be distributed or trusted; **high** = contradiction between documented contract and shipped artifact, likely to burn an agent/user; **medium** = drift/quality/usability; **low** = cosmetic.

---

## 1. Blockers

### BLK-01 — `.agents/hooks.json` points at scripts that do not exist
- **Evidence**
  - `.agents/hooks.json:9` — `"command": "python scripts/rbac_guard.py"`
  - `.agents/hooks.json:23` — `"command": "python scripts/event_bus_logger.py"`
  - Actual files: `.agents/scripts/rbac_guard.py`, `.agents/scripts/event_bus_logger.py`; `scripts/` contains only `prd_generator.py`, `spec_generator.py`, `plan_linter.py`.
  - Running the configured command from the workspace root: exit code **2**, `can't open file 'D:/WorkSpace/Agent研究/scripts/rbac_guard.py': [Errno 2] No such file or directory` (actual output used backslashes).
  - The design document itself uses the correct path: `docs/specs/PLANNER_LINTER_DESIGN.md:178` and `:192` (`python .agents/scripts/rbac_guard.py`, `python .agents/scripts/event_bus_logger.py`).
- **Impact**: both PreToolUse RBAC and PostToolUse audit hooks fail instantly. All "物理级强制拦截" / "自动审计" claims in `.agents/rules/README.md:21-28`, `task-templates/README.md:23-32` and `README.md:36` are false in the shipped artifact. Hook failures are silent (timeout 5, no fallback), so the pipeline appears to run while logging nothing.
- **Fix direction**: resolve commands relative to the hook file/workspace explicitly (no bare `scripts/...`), or move the files; add a startup smoke check; state the cwd contract in the README; align with the design doc. If hooks cannot run in the target harness, delete the claim instead of shipping a dead safety layer.

### BLK-02 — Literal trigger markers embedded in task templates cause immediate false handoffs
- **Evidence**
  - `task-templates/02-dev-workspace.template.md:47-51`: "当开发自测全部完成时，DevAgent 将下方复选框由 `[ ]` 改为 `[x]`" followed by `- [ ] **提测申请**：[x] WAITING_FOR_QA` — an unchecked row that already contains the literal trigger string.
  - `task-templates/03-qa-verification.template.md:58-64`: the verdict table contains both `[x] QA_PASSED` and `[x] REWORK_REQUIRED` as literals under unchecked boxes.
  - The logger matches raw substrings: `event_bus_logger.py:38` `if "[x] WAITING_FOR_QA" in ws_content ...`, `:68` `if "[x] QA_PASSED" in qa_content ...`.
  - Probe (template copies, zero development work, sample 04-process rows removed): the logger appended `EV-AUTO | HANDOFF_QA_REQUESTED` and set `macro_status: "VERIFYING"`. See Appendix A.3.
- **Impact**: any task created by copying the templates is instantly "waiting for QA" / "QA passed" from the first write. The state machine can never represent real progress.
- **Fix direction**: templates must contain `[ ]` only and no literal `[x]` string; use a single machine field (e.g. `handoff_state: NONE|WAITING_FOR_QA|...`) or an explicit placeholder token that the hook recognises; hooks should parse the checkbox state, not the presence of a string. Move the example marker into a comment/prose block.

### BLK-03 — The 04-process template's sample events defeat the logger's idempotency guards
- **Evidence**
  - `task-templates/04-process.template.md:33` ships an `EV-05` row containing `HANDOFF_QA_REQUESTED`; `:37` ships `EV-09` containing `TASK_TERMINATED_DONE`.
  - The logger guards on exactly those strings: `event_bus_logger.py:38` `"HANDOFF_QA_REQUESTED" not in process_content`, `:68` `"TASK_TERMINATED_DONE" not in process_content`.
  - Probe A (unmodified template copies): first hook invocation changed nothing — no `EV-AUTO` row, `macro_status` remained `{{CURRENT_MACRO_STATUS}}`. See Appendix A.3.
  - The same template also ships fake timestamps (`2026-10-10T08:00:00Z` ...) and a full 9-event "completed lifecycle" (`:29-37`), so every new task starts with a forged audit trail.
- **Impact**: after fixing BLK-02, the logger still never appends the two events it exists for; the audit file lies (a fabricated lifecycle) and is never updated. The entire post-tool audit feature is a no-op for template-derived tasks.
- **Fix direction**: ship an empty event table with an append marker; never include accepted state strings or fixed timestamps in a template; guard on event IDs (`EV-AUTO`) only; add an integration test that instantiates the template, runs the logger, and asserts exactly one appended row.

### BLK-04 — "100% self-contained (整包单独抽离分发)" is false for 3 of 5 skills
- **Evidence**
  - Claim: `.agents/skills/README.md:5` "所有技能包均遵循 **"100% 自包含（Self-Contained）"** 标准设计 ... 支持**整包单独抽离分发或发布为通用插件**".
  - `.agents/skills/prd-generator/scripts/run.py:11` `project_root = Path(__file__).resolve().parents[4]`, `:15` `from prd_generator.cli import main` — imports the repository-level package, not a bundled engine.
  - `.agents/skills/spec-generator/scripts/run.py:10,14` — same pattern.
  - `.agents/skills/task-decomposition/SKILL.md:34` makes Gate 1 depend on a sibling skill: `[.agents/skills/plan-linter/scripts/plan_linter.py](../../.agents/skills/plan-linter/scripts/plan_linter.py)`; no linter is bundled inside `task-decomposition/`.
  - All documented invocations are repository-root-relative, e.g. `prd-generator/SKILL.md:33-35,72-78`, `spec-generator/SKILL.md:38-41,77-84`, `plan-linter/SKILL.md:35-38`, `task-decomposition/SKILL.md:115-118`.
  - Probe: copying `prd-generator/` outside `.agents/` and running its `run.py` with an interpreter without the editable install fails with `ModuleNotFoundError: No module named 'prd_generator'`. It only works in this repo because `.venv` has an editable `.pth` for `agent-spec-suite` and both packages resolve to `D:/WorkSpace/Agent研究/prd_generator` / `spec_generator` (`_probe/standalone`).
  - Only `plan-linter` and `diagnose-windows-sandbox-acl` genuinely bundle what they need.
- **Impact**: the stated distribution model ("extract the folder or publish it as a generic plugin") breaks for the two headline skills and for task-decomposition's gate. This is the single biggest obstacle to the owner's general-purpose goal.
- **Fix direction**: either bundle the engine (or a thin vendored subset) inside each skill, or explicitly declare a package dependency and remove the self-contained claim; resolve the repo root via an install-time path/config instead of `parents[4]`; add a packaging test that copies a skill to a temp dir and runs its documented command with a clean interpreter.

### BLK-05 — RBAC guard is not enforced, and its only rule set contradicts the Planner workflow
- **Evidence**
  - Role comes from an ambient env var that nothing in the repo sets: `rbac_guard.py:38` `agent_role = os.environ.get("AGY_AGENT_ROLE", "").lower()`; a repo-wide grep finds `AGY_AGENT_ROLE` only in the guard itself (plus audit scratch scripts under `artifacts/skill-audit/`). With the variable unset the guard returns allow for every path.
  - Relative paths bypass the two most important rules because the checks look for a leading slash: `:54` `if "/tests/acceptance/" in normalized_path`, `:67` `if "/src/" in normalized_path`. Probe: DevAgent writing `tests/acceptance/test_login.py` -> allow; QAAgent writing `src/app.py` -> allow; the same paths in absolute form -> deny.
  - The docs promise `PermissionError` and physical blocking (`.agents/rules/README.md:23-26`), but the script only prints a JSON `{"decision": "deny"}`; whether that is honoured depends entirely on an unverifiable Antigravity hook protocol.
  - `:30` denies **any** write to `04-process.md` (and `04-process.template.md`), while the task-decomposition SOP orders the Planner to create it: `task-decomposition/SKILL.md:118` "复制 ... 04-process.template.md -> tasks/task-xxx/04-process.md"; the design doc also says the Planner "初始化 04-process.md" (`PLANNER_LINTER_DESIGN.md:110`). No code creates `04-process.md` — the logger only appends if it already exists (`event_bus_logger.py:27-28`).
- **Impact**: the advertised security property is fiction. If the hook ever runs, Dev can still edit acceptance tests and QA can still edit `src/` via relative paths; if the guard is strict, the Planner cannot create the fourth document. Either way the documented lifecycle is broken.
- **Fix direction**: pass the agent role through the hook payload/config (documented, deterministic), normalise with `os.path.normpath`/resolved absolute paths and compare path segments; allow the Planner's one-time 04 creation (or let the bus create it); align `rules/README.md` with the actual JSON protocol; add unit tests for relative/absolute/bypass cases.

---

## 2. High-severity findings

### HIGH-01 — The suite contradicts itself on 3 vs 4 documents
- **Evidence**
  - Says **4**: `AGENTS.md:3,5-9`; `.agents/skills/README.md:41` ("tasks/task-xxx/ 4 份文档"); `.agents/rules/planner.md:4`; `README.md:53` ("4-文档任务规划"); `docs/specs/PLANNER_LINTER_DESIGN.md:54,242`.
  - Says **3**: `task-templates/04-process.template.md:29` ("任务由 Planner/Linter 完成三份模板初始化"); `docs/specs/PLANNER_LINTER_DESIGN.md:64` ("初始化任务三份文档") and `:91-95` (`THREE-ARTIFACT SCAFFOLDING`, listing only 01/02/03).
- **Impact**: a Planner following the design doc/template creates only 3 files; the logger then skips the task (`event_bus_logger.py:27-28` returns when `04-process.md` is absent), so no audit trail ever exists. It also contradicts `AGENTS.md`, which is the global instruction file.
- **Fix**: make 4 authoritative everywhere; fix the template row and the design doc's two "three" statements; add a lint/check that every task bundle contains 01-04.

### HIGH-02 — Documented contract fields (`origin_spec_anchor`, `adherence_adrs`) do not exist in the template and are not validated
- **Evidence**
  - Rules require the field names: `task-decomposition/SKILL.md:51` ("必须 ... 声明 `origin_spec_anchor` ... 与 `adherence_adrs`"); `references/decomposition-rules.md:28-29`; `docs/specs/PLANNER_LINTER_DESIGN.md:84`.
  - The template has no such fields. It has a `PRD 溯源锚点` row and a `Tech Spec 锚点` row (`task-templates/01-contract.template.md:17-18`); the linter only parses the latter (`plan_linter.py:66-68`), and it accepts the literal template cell `02-tech-spec.md#{{SPEC_ANCHOR}}` because the string does not start with `{{` (`:67`).
  - Probe task-002 (contract written exactly with `origin_spec_anchor:` / `adherence_adrs:` fields, everything else valid) is rejected with `[task-002] 缺失来源锚点`. See Appendix A.1.
  - `adherence_adrs` is parsed (`plan_linter.py:71-74`) but **never checked**; a task with zero ADRs passes. The lint command parsed at `:81-83` is never checked either, although the docs require it (`task-decomposition/SKILL.md:53`, `plan-linter/SKILL.md:22`, `:104`).
- **Impact**: an agent that follows the written rules produces a contract the validator rejects; an agent that follows the template silently loses the named traceability fields and ADR-lint enforcement.
- **Fix**: pick one vocabulary. Best: put explicit rows in the template (`Origin Spec Anchor`, `Adherence ADRs`) and make the linter parse those exact labels; validate `adherence_adrs` non-empty and placeholder-free, and validate the lint command; require the anchor cell to contain `#sec-` and no `{{` anywhere.

### HIGH-03 — An unfilled contract template can pass Gate 1; placeholder scanning is not implemented
- **Evidence**
  - Probe task-003: started from `01-contract.template.md`, filled only Task ID, dependencies, estimated lines, whitelist, DoD commands/test/edge cases; left `Tech Spec 锚点 = 02-tech-spec.md#{{SPEC_ANCHOR}}`, `{{CODE_INTERFACE_DEFINITION}}`, `{{INVARIANT_1|...}}`, `{{ADR_ID_1}}`, etc. The linter reported **no violation for task-003** (only task-001/002 failed). See Appendix A.2.
  - The parser has no generic mustache scan; only two fields are checked for `{{` (`type_check_cmd`, `test_file`; `plan_linter.py:128-131`). `origin_spec_anchor` is protected only by the `startswith("{{")` condition (`:67`).
  - The same instantiated template counts `{{FILE_PATH_1}}` as a real whitelist file (`plan_linter.py:60-63`), so "explosion radius" can be satisfied by placeholders.
- **Impact**: Gate 1 can certify a contract full of unfilled instructions, contradicting "零占位符" / "机器可执行契约" messaging (`plan-linter/SKILL.md:21`, `task-decomposition/SKILL.md:19`).
- **Fix**: add one strict pass over the whole `01-contract.md` rejecting any remaining `{{...}}`/`[TBD]`/`<TODO>` and any whitelist entry containing placeholder characters; add the actual template as a failing fixture in tests.

### HIGH-04 — "SHA-256 audit chain" is claimed but does not exist
- **Evidence**
  - `.agents/rules/README.md:28`: "自动在 `04-process.md` 追加写入时间戳与 SHA-256 审计链条".
  - `event_bus_logger.py` imports only `sys/json/os/re/datetime` (`:11-15`) and writes plain timestamp rows (`:40`, `:70`); no hash anywhere in the file or in `04-process.template.md`.
  - The QA signature field `{{QA_SIGNATURE_HASH}}` (`03-qa-verification.template.md:69`) is never written or validated.
- **Impact**: the advertised tamper-evident audit trail is a plain text append; the security/governance claim is unsupported.
- **Fix**: implement the chain (hash of previous row + payload) in the logger, or remove the claim and the `QA_SIGNATURE_HASH` field.

### HIGH-05 — Event names and statuses drift across four documents
- **Evidence** (all exact strings)
  - Handoff event: `HANDOFF_QA_REQUESTED` in `04-process.template.md:33` and `event_bus_logger.py:40`; `QA_REQUESTED` in `event_bus_logger.py:6` (module docstring) and `PLANNER_LINTER_DESIGN.md:214`.
  - Completion event: `TASK_TERMINATED_DONE` in `04-process.template.md:37` and `event_bus_logger.py:70`; `TASK_DONE` in `PLANNER_LINTER_DESIGN.md:218`.
  - Status: `VERIFYING` in `04-process.template.md:13` and `event_bus_logger.py:51`; `QA_VERIFYING` in `PLANNER_LINTER_DESIGN.md:215`.
  - Rework: `REWORK_TRIGGERED` promised in `event_bus_logger.py:8`; never implemented; `[x] REWORK_REQUIRED` is required by `qa.md:6` but has no consumer.
- **Impact**: any consumer (dashboard, CI, another agent) matching the design doc's names will never see events; rework loops are invisible. It also makes the sample 04 template internally inconsistent with the code.
- **Fix**: define one event/status enum in a single file (or a shared constant imported by logger/docs); generate the template/doc tables from it; add a contract test for each event name.

### HIGH-06 — "Neutral" templates hardcode domain assumptions
- **Evidence**
  - Tech-spec topology template: `spec-templates/02-tech-spec/01-topology.template.md:42-44` hardcodes `PostgreSQL 16+`, `Redis 7.2+`, `Apache Kafka / RabbitMQ` and `#sec-database-storage`, `#sec-cache-clustering`, `#sec-messaging-broker` even though the same table has `{{DATABASE_TYPE}}`, `{{CACHE_TYPE}}`, `{{MESSAGE_BROKER_TYPE}}`.
  - DB template: `spec-templates/02-tech-spec/02-database-schema.template.sql:12` mandates "核心表必须包含多租户隔离键 (tenant_id)"; `:49-59` unconditionally adds an `idempotency_records` table.
  - API template: `03-api-contracts.template.ts:41-46` hardcodes `tenantId`, `actorId`, `idempotencyKey`; `:59-67` adds a `/verify` endpoint with `verificationToken`.
  - Aggregate tech spec: `02-tech-spec.template.md:70-84` same `tenant_id`/`idempotency_key` DDL; `:89-100` same tenant contract.
  - Invariants template: `04-system-invariants.template.md:14` mentions "卡号凭据" (card credentials) and `:34` "财务、库存" — e-commerce/finance residue in a supposedly domain-neutral template.
  - QPS defaults contradict each other: aggregate template says 2,000/5,000 QPS, read P99 < 30 ms, availability 99.95% (`02-tech-spec.template.md:33-36`, `01-prd/03-nfr.template.md:17-26`), while the modular README says 3,000/6,000 QPS, read P99 < 20 ms, availability 99.99% (`02-tech-spec/README.template.md:18-21`).
  - Task templates: `01-contract.template.md:73` hardcodes a `.ts` acceptance test; `03-qa-verification.template.md:15` hardcodes `Docker / Node.js / Python`; `02-dev-workspace.template.md:55` uses an "库存为负数" (inventory) example, i.e. exactly the e-commerce residue the rules forbid.
- **Impact**: agents copy these defaults into every domain (a CLI tool gets `tenant_id`, Redis, Kafka, QPS targets); the anti-contamination rules become impossible to obey; the 2k/3k QPS split means two generated documents disagree on the same requirement.
- **Fix**: convert every product/entity/threshold into a placeholder with **no default**, or a clearly labelled non-authoritative comment; move examples to `references/`; require the generator to source NFRs from the PRD; add a contamination test for the template text itself.

### HIGH-07 — Validator capability claims are far ahead of implementation
- **Evidence**
  - `.agents/skills/README.md:24-25`: "Mermaid 语法 **AST 树解析**校验" / "SQL DDL 语法 / 外键引用完整性校验".
  - Mermaid "validation" is regex extraction plus bracket counting (`mermaid_validator.py:153-178`), no AST and no parser dependency.
  - SQL "foreign-key integrity" is parentheses balance after comment stripping (`spec_linter.py:269-278`); no FK/type/schema check.
  - TypeScript "强类型闭环" is regex extraction of `type/interface`, bracket balance, and a warning for `interface`/`any` (`interface_validator.py:190-223`); no compiler/type-checker.
  - PRD lint claims: `prd-generator/SKILL.md:24` promises anchor "命名与唯一性" checks and NFR/FORK format checks; `:111-113` promises NFR coverage. `prd_linter.py:77` defines `NFR_REGEX` and never uses it; anchors are checked by "any anchor exists" (`:113-123`), not per-REQ or kebab-case. Probe: generated PRD contains `#sec-单机离线番茄钟桌面应用无网络无多租户无后端-core` (non-kebab, non-ASCII) and still passes `prd-generator lint`.
  - `plan-linter/SKILL.md:22` and `task-decomposition/SKILL.md:22` claim "自动统计代码量" / "代码风格 Lint 命令" checks; the linter only reads the planner's declared `预估代码量` (`plan_linter.py:54-57`) and never validates `lint_cmd`.
- **Impact**: users and downstream agents trust "machine gates" that are regex heuristics; invalid Mermaid/SQL/TS/PRD output can pass. The product makes quality guarantees it cannot keep.
- **Fix**: either implement the checks (mermaid parser, SQL parser/schema, `tsc`/mypy/ruff invocation) or restate the docs as "heuristic lint (regex/bracket balance)" and add limitations to each SKILL; add a test proving an invalid artifact is rejected.

### HIGH-08 — "Zero template contamination / 100% PRD-derived" is contradicted by the shipped generator
- **Evidence**
  - Claims: `spec-generator/SKILL.md:29` "强制校验所有实体与字段 100% 来源于 PRD 输入或识别的领域"; `.agents/skills/README.md:35`; `.agents/rules/architect.md:19-29`.
  - The deterministic generator has a fixed domain catalogue in code: `spec_generator/synthesis/tech_spec_synthesizer.py:183-206` (`agent/ecommerce/auth/notif/calc/generic` tables and route prefixes), selected by keyword detection. This is the source of the Postgres/Redis/Kafka/tenant content in generated specs.
  - Probe: a genuinely neutral idea ("单机离线番茄钟桌面应用，无网络、无多租户、无后端") generated a PRD containing multi-tenant auth, QPS 1,000, PostgreSQL and document-store forks (`_probe/generated/01-prd.md:34-37,51,60,70-71`), then spec-generator generated an agent-platform topology with PostgreSQL/Redis/Kafka and **failed its own contamination gate** on `HSM tokenization` / `Credit card tokenization` while the invalid files remained on disk (Appendix A.4).
  - The contamination gate only checks a small word list and only when the text matches a fixed set of non-ecommerce domain words (`spec_linter.py:65-107`).
- **Impact**: the core differentiator ("no hallucinated domain content") is false for the default deterministic mode; generated artifacts will systematically over-engineer and mis-domain generic requests.
- **Fix**: either make the deterministic backend domain-agnostic (entity extraction from the idea only) or document it as a bounded demo with a fixed set of supported domains; strengthen the contamination gate to PRD-derived allow-lists, not a small blocklist; do not write invalid output before the gate passes.

### HIGH-09 — The state machine described in templates has no execution engine
- **Evidence**
  - `task-templates/README.md:38-67` sequence diagram has `Bus (Code Engine)`, `Sandbox`, "Bus 捕获提测标记", "Bus 更新 04-process", "广播下游任务解锁"; `:26-32` RBAC matrix lists "调度代码总线 (Python/Go)", "Git 变更监控", "沙箱运行执行"; `:76` "由调度总线系统代码根据模板格式自动渲染".
  - `02-dev-workspace.template.md:49` promises "自动加锁保护代码，并唤醒 QAAgent"; `03-qa-verification.template.md:59` promises archiving/unlocking; `04-process.template.md:3-5` promises a system event-bus engine.
  - Repository reality: only `rbac_guard.py` and `event_bus_logger.py` exist. Grep finds no `SandboxRunner`/`EventBus`/lock/queue/git-monitor implementation; `event_bus_logger.py` only appends rows and rewrites two YAML keys; it has no locking, no dependency unlocking, no retry counting, no timeout/circuit-breaker, no telemetry.
- **Impact**: Dev/QA wait for wake-ups and locks that never happen; the 04 telemetry fields (retry count, circuit breaker, token budget) are never written.
- **Fix**: either implement the missing orchestrator or rewrite the templates as a manual protocol and remove the "automatic" guarantees; mark the rest as roadmap.

### HIGH-10 — Global CLI claim is false for `prd-generator` in this workspace
- **Evidence**
  - `prd-generator/SKILL.md:32` and `spec-generator/SKILL.md:37`: "已注册至系统 PATH，任何终端均可直接执行".
  - `Get-Command prd-generator` / `prd_generator` -> not found; `Get-Command spec-generator` -> found at `C:/Users/formal/.local/bin/spec-generator.exe`. `.venv/Scripts/` has all four launchers, but the venv is not the "system PATH". `pyproject.toml:16-20` defines them, but that only helps after `uv tool install`/`pip install`.
- **Impact**: the first command a new user copies from the SKILL fails; it also hides that `prd-generator` requires the editable install / repo package.
- **Fix**: document the install step per skill ("or use `python .agents/skills/.../run.py`"), mark CLI availability as environment-dependent, and add a preflight check to the SOP.

### HIGH-11 — Template duplication is already drifting; three copies of the same "contract"
- **Evidence**
  - SHA-256 comparisons: all 5 task-template files are byte-identical between `task-templates/` and `task-decomposition/resources/templates/`; 15 spec-template file pairs are byte-identical across `spec-templates/`, the prd-generator bundle and the spec-generator bundle.
  - Already diverged: `spec-templates/README.md` vs `.agents/skills/spec-generator/resources/templates/README.md` — the bundled copy keeps the root tree (`01-prd/` entries) it does not contain, lists `README.md` as if it were at the repo root, and its `../task-templates/` link is broken. `.agents/skills/prd-generator/resources/templates/` has **no README at all**.
  - No sync/generation script exists (root `scripts/` has 3 files, none touches templates); copies are maintained by hand.
- **Impact**: any template fix (BLK-02, HIGH-06) must be applied in 2-3 places; the first drift already happened. Skill bundles are supposed to be "independent template libraries" (`README.md:5`) but root copies are the de-facto source.
- **Fix**: choose one canonical source and generate the bundles (or copy in CI with a checksum test); delete redundant root copies if bundles are canonical; add a "templates in sync" test.

### HIGH-12 — SKILL frontmatter is not good enough for automatic selection
- **Evidence** (details in section 6)
  - Four pipeline descriptions are English while bodies are Chinese; none uses an explicit "Use when ..." trigger; `spec-generator` repeats the skill name ("Multi-agent deliberation and spec-generator skill to ingest PRD documents ...").
  - `task-decomposition` / `plan-linter` descriptions are written for internal roles/jargon (`PlannerAgent`, Gate 1/Gate 2), not for an end user asking "break this PRD into tasks".
  - No description states input/output shape or differentiates the overlapping PRD-vs-spec-vs-task pipeline (all three claim "multi-agent"/"4-role" brainstorming).
  - The 5th skill's description is 303 chars and contains an approval recipe that belongs in the body; it is the only one following the "Use when" style.
- **Impact**: an automatic skill router sees four similar "multi-agent ... engine" blobs and one long Windows-specific blob; wrong-skill activation or non-activation is likely for general-purpose users.
- **Fix**: rewrite each description as 1-2 sentences with a leading trigger, explicit inputs/outputs, and the distinguishing boundary; keep harness coupling out of the description; move the diagnose approval recipe into the body.

---

## 3. Medium-severity findings

### MED-01 — Language inconsistency across rules and skills
- `.agents/rules/pm.md` (30 lines, Chinese) and `architect.md` (35 lines, Chinese) are detailed specs; `planner.md` (6 lines), `dev.md` (6), `qa.md` (7) are terse English checklists. `AGENTS.md` is English. Four SKILL bodies are Chinese; `diagnose-windows-sandbox-acl/SKILL.md` is English. Template READMEs are Chinese; frontmatter descriptions are English.
- Impact: for a redistributable suite the language of authoritative constraints is unpredictable; auto-injection and human review both suffer.
- Fix: pick one normative language (English is the safer default for OSS) and one for examples, or ship paired translations with stated precedence.

### MED-02 — Stale/contradictory template examples
- `task-templates/README.md:73` refers to a global `tech-spec.md`; the actual file is `02-tech-spec.md`.
- `01-contract.template.md:73` hardcodes `tests/acceptance/test_{{TASK_ID}}.ts`; `decomposition-rules.md:42` suggests `tests/unit/test_xxx.py`; `rules/README.md:14` says `tests/` generally. Language (.ts vs .py) and directory (unit vs acceptance) disagree.
- `04-process.template.md:29-37` ships fake `2026-10-10` timestamps and a completed event history (see BLK-03).
- `adr.template.md:40-58` hardcodes specialist scores (8.5/9.0/7.5/4.0 etc.) and always exactly two options; `pm.md:17` requires MCDA weights summing to 1.0000 and a deterministic tie-break, but the ADR template has no weights/tie-break fields and no validator.
- `03-qa-verification.template.md:15` hardcodes `Docker / Node.js / Python`, excluding e.g. .NET/Rust/Go-only services.

### MED-03 — Template copy instructions are cwd-ambiguous
- `task-decomposition/SKILL.md:113-118` says "复制 `./resources/templates/01-contract.template.md`" — from the skill directory this works; from the workspace root (where every other command in the suite runs) it does not. `diagnose-windows-sandbox-acl/SKILL.md:21` shows the better pattern: `<skill-directory>/scripts/...`.
- Fix: use an explicit `<skill-directory>` convention in all copy/run steps.

### MED-04 — Role roster drift
- `PlanReviewerAgent` exists only in `plan-linter/SKILL.md:24,111,115`; no rule file for it. `PLANNER_LINTER_DESIGN.md:51-52` references `.agents/subagents/planner.json` and `.agents/subagents/plan_reviewer.json`, and `:55` references `.agents/rules/workspace.md` — none exist. `task-templates/README.md:25-32` has a 5-entity matrix without PlanReviewer; `rules/README.md:9-15` lists 5 role docs excluding the bus. Agent names drift (`DevAgent` vs `Dev Agent`, `QAAgent` vs `QA Agent`).
- Fix: one role/agent manifest referenced by rules, skills, templates and design; create the missing files or delete the references.

### MED-05 — Hook robustness / operability
- `event_bus_logger.py:94-95` hardcodes `tasks_root = "./tasks"`; it scans every task on every write (`:92-101`).
- Appending depends on finding the exact note string `"*(注：若验收失败"` (`:43-47`, `:72-76`); if a user edits that prose the row is silently skipped.
- No telemetry/retry/micro-phase updates (only `macro_status`, `current_lock_holder`).
- Exceptions are swallowed (`:109-110`) and the script prints `{}`; failures are invisible; hook timeout is 5 s with no kill/notification path.
- No tests cover either hook (grep of `tests/` finds no references).
- Fix: take the tasks root from config/env, update a fixed machine block (not prose anchors), surface errors on stderr, add unit tests with temp task bundles.

### MED-06 — PRD lint coverage claims exceed code
- See HIGH-07. Additional detail: "necessary section coverage" (`prd-generator/SKILL.md:113`) is not enforced for overview/features; CON/FORK checks only run when a specific heading text is present (`prd_linter.py:125-147`); the stub regex does not match an enum like `[TODO | IN_PROGRESS]` (and 04-process is not scanned at all).
- Fix: either implement section coverage or reduce the claim to the three checks actually performed (mustache, stub tokens, presence of any anchor).

### MED-07 — Templates are not consumed by any script
- No generator or linter reads `resources/templates/`; the only mentions are docstrings (`prd_generator/synthesis/master_synthesizer.py:4`, `prd_generator/models/prd.py:374`). `plan_linter.py` parses only a hand-written subset of `01-contract.md`; `02-dev-workspace`, `03-qa-verification` and `04-process` are read only for trigger/marker strings by the logger.
- The claim "模板作为格式契约" is therefore aspirational; any template edit can silently diverge from what the validator expects (it already has: HIGH-02).
- Fix: make templates the single source for generator output (render placeholders programmatically) or generate a schema/field list from the validator and test the template against it.

### MED-08 — Non-atomic generation leaves invalid artifacts after a failed gate
- Probe: `spec-generator run --prd <neutral idea PRD> --output-dir _probe/generated_spec` exited 1 with two contamination errors but had already written `02-tech-spec.md`, `02-tech-spec/*` and `adr/*.md`. The SKILL says "确保退出码为 0，杜绝任何语法或类型破损" (`spec-generator/SKILL.md:136`), but the failure path leaves the invalid bundle on disk for downstream consumers. `prd_generator` has the same pattern (synthesis then lint).
- Fix: synthesize into a temp dir, lint, then atomically move; or delete on failure.

### MED-09 — Empty/invalid task directory exit-code semantics are undocumented
- `plan_linter.py:199-201` returns failure (exit 1) with "⚠️ 未发现任何任务包", but the SKILLs define exit 1 exclusively as "存在违规项" (`plan-linter/SKILL.md:82-86`, `task-decomposition/SKILL.md:85-87`). A crash also exits 1. CI cannot distinguish "no work" from "violations".
- Fix: document exit codes 0/1/2 (or use distinct codes) and the empty-directory behaviour.

### MED-10 — The 5th skill is orphaned from the suite docs and framing
- `.agents/skills/README.md` describes only the 4 Antigravity pipeline skills; `README.md:40-43` lists only those 4; `diagnose-windows-sandbox-acl` is absent from both. Its body is English, DSH/Windows-specific, and unrelated to the Antigravity pipeline, while `skills/README.md:3-5` claims the directory is an Antigravity 2.0 skill centre.
- Fix: add a "Utility skills" section documenting it (scope, why it exists, how it differs), or move it out of the suite; adjust the "all Antigravity native" claim.

### MED-11 — Portability assumptions are hidden
- Hooks assume Antigravity tool names (`write_to_file|replace_file_content`) and a payload with `toolCall.args.TargetFile` (`rbac_guard.py:16-22`); docs assume `src/`, `tests/acceptance/`, `tasks/`, `.specs/` layout and `python`/PowerShell. Nothing states these as assumptions or makes them configurable.
- Fix: add a "Harness & layout requirements" section per skill; make paths configurable; mark Antigravity-only features.

### MED-12 — `plan-linter`/Gate 2 "automated" framing
- `plan-linter/SKILL.md:3,109-134` describes Gate 2 as a review step; it is a prompt template with no script, and the "终审判定输出" strings are not produced by any tool. The description reads as if a runnable Gate 2 exists.
- Fix: label Gate 2 as an agent prompt/checklist, not a command; if automation is intended, ship a script that checks the audit report.

---

## 4. Low-severity nits

- **LOW-01** Root `README.md` asset inventory is stale: `:31-33` lists only `scripts/prd_generator.py` and `scripts/spec_generator.py` (also `scripts/plan_linter.py` exists); `:38` omits `.agents/scripts/event_bus_logger.py`; `:40-43` omits the 5th skill.
- **LOW-02** `skills/README.md:61-66` lists "全局命令" unconditionally; tie it to the install step and add a fallback row (`python .agents/skills/.../run.py`).
- **LOW-03** Broken relative link in the bundled spec README: `.agents/skills/spec-generator/resources/templates/README.md:3` -> `../task-templates/` (does not exist there). Other "broken" template-relative links point to produced files (`00-overview.md` etc.) and are acceptable as instance links.
- **LOW-04** Task directory naming drifts: `task-templates/README.md:12` uses `tasks/task-{{TASK_ID}}/` (no slug), while SKILLs and design use `tasks/task-001-xxx/`; `01-contract.template.md:12` expects Task ID `task-{{TASK_ID}}`. Pick one convention.
- **LOW-05** `skills/README.md:37` calls the PRD template directory "自包含模板库" but the bundle lacks a README, so extracting the skill loses the template guidance.
- **LOW-06** Minor docstring/version drift: `run.py` says "Self-contained runner" (BLK-04); `prd-generator` reports `0.1.0` from a hardcoded argparse string (`prd_generator/cli.py:48`) while `spec-generator` uses `spec_generator.__version__` (`spec_generator/cli.py:24,102`).

---

## 5. Claims-vs-artifacts matrix

Legend: **FAIL** = claim contradicted by artifact; **PARTIAL** = true only in a narrower sense; **OK** = verified; **UNVERIFIABLE** = cannot be checked from this repo (external harness).

| # | Claim (file:line) | Artifact check | Status | Evidence |
|---|---|---|---|---|
| C01 | "100% 自包含 ... 整包单独抽离分发" (`.agents/skills/README.md:5`) | Extract prd-generator/spec-generator/task-decomposition | **FAIL** | BLK-04 probe; `run.py:11,15`; `task-decomposition/SKILL.md:34` |
| C02 | "已注册至系统 PATH" (`prd-generator/SKILL.md:32`, `spec-generator/SKILL.md:37`) | `Get-Command` | **FAIL/PARTIAL** | prd not found; spec found in user `.local/bin`; venv only has all four |
| C03 | Documented `prd-generator run` flags exist (`prd-generator/SKILL.md:82-90`) | `prd_generator/cli.py:55-104` | **OK** | All defined; `--mode` choices match |
| C04 | Documented `spec-generator` flags exist (`spec-generator/SKILL.md:87-93`) | `spec_generator/cli.py:55-91` | **OK** | Also works before/after `run` because options are on the root parser |
| C05 | `plan_linter` supports `--tasks-dir` / `-t` / `--help` (`plan-linter/SKILL.md:76-80`) | `plan_linter.py:220-233` + smoke tests | **OK** | All four entrypoints exit 0 with `-h` |
| C06 | Exit code 0 = pass, 1 = violation (`plan-linter/SKILL.md:82-86`) | `plan_linter.py:233` | **PARTIAL** | Empty dir/crash also exit 1 (MED-09) |
| C07 | "Mermaid AST 树解析" (`skills/README.md:24`) | `mermaid_validator.py:153-178` | **FAIL** | Regex + bracket count |
| C08 | "SQL DDL 语法 / 外键引用完整性校验" (`skills/README.md:25`, `spec-generator/SKILL.md:27`) | `spec_linter.py:269-288` | **FAIL** | Only `CREATE TABLE` presence + parentheses balance |
| C09 | "TypeScript 强类型闭环校验" (`skills/README.md:26`, `spec-generator/SKILL.md:28`) | `interface_validator.py:190-223` | **FAIL** | Regex/warnings; no type checker |
| C10 | "反占位符 ... 零占位符残留" (`prd-generator/SKILL.md:24,111`) | `prd_linter.py:73-107` + template lint probe | **PARTIAL** | Works for PRD output; anchor uniqueness/NFR not checked (HIGH-07) |
| C11 | PRD lint checks NFR/necessary sections (`prd-generator/SKILL.md:113`) | `prd_linter.py:77,109-147` | **FAIL** | `NFR_REGEX` unused; no overview/NFR section check |
| C12 | `plan_linter` validates `origin_spec_anchor` + `adherence_adrs` "无占位符" (`plan-linter/SKILL.md:21`) | `plan_linter.py:66-74,124-135` | **PARTIAL** | Anchor parsed from a template row, placeholder prefix accepted; ADRs never checked |
| C13 | DoD must contain code-style lint command (`plan-linter/SKILL.md:22,104`) | `plan_linter.py:81-83` | **FAIL** | Parsed but never validated |
| C14 | "自动统计代码量" / "白名单文件数" (`task-decomposition/SKILL.md:22`) | `plan_linter.py:54-63` | **PARTIAL** | Counts whitelist items (including placeholders); reads declared estimate, does not measure actual lines |
| C15 | DAG Kahn cycle detection / hard block (`plan-linter/SKILL.md:23,105`) | `plan_linter.py:140-167` | **OK** | Genuine Kahn sort; cycle/unknown-dep errors |
| C16 | 4-document spec (`AGENTS.md:3-9`, `planner.md:4`) | `04-process.template.md:29`, design `:64,91` | **FAIL** | 3-vs-4 contradiction (HIGH-01) |
| C17 | Hooks physically block RBAC (`rules/README.md:23-26`) | `rbac_guard.py`, `hooks.json` | **FAIL** | Dead hook + unset role + relative-path bypass (BLK-01/05) |
| C18 | Event logger appends SHA-256 audit chain (`rules/README.md:28`) | `event_bus_logger.py:11-15,40,70` | **FAIL** | No hashing (HIGH-04) |
| C19 | `QA_PASSED` triggers completion (`task-templates/README.md:29`) | `event_bus_logger.py:68-71` | **PARTIAL** | Guard blocked by template sample (BLK-03); false-positive without sample (BLK-02) |
| C20 | `[x] REWORK_REQUIRED` triggers rework (`qa.md:6`) | no consumer; logger docstring `:8` only | **FAIL** | No rework handling |
| C21 | Template copies identical / drift-free | SHA-256 24 comparisons | **PARTIAL** | Identical today; README already diverged; 3 locations; no sync (HIGH-11) |
| C22 | Four-role brainstorm (`pm.md:10-14`, `prd-generator/SKILL.md:18`) | role lists | **OK** (names) | Four product roles consistent; four spec roles consistent; minor English naming drift |
| C23 | MCDA weights sum 1.0000, tie-break rules (`pm.md:17-18`, `architect.md:11`) | `adr.template.md:39-58`; no validator | **FAIL** | Template has only 4 scores, no weights/tie-break |
| C24 | "3 轮结构化研讨" (`pm.md:10`) | no artefact enforces rounds | **UNVERIFIABLE** | Prose only |
| C25 | Skill names match directories; frontmatter YAML valid | 5 x SKILL.md parsed | **OK** | `name` equals directory; delimiters valid |
| C26 | Relative links in SKILL/rules resolve | 37 markdown files link-checked | **OK** (one exception) | Only bundled spec README `../task-templates/` broken; template-instance links expected |
| C27 | `plan-linter` self-contained | `scripts/{plan_linter,run}.py` present + probe | **OK** | Runs from copied folder |
| C28 | `diagnose` command exists | `scripts/diagnose-windows-sandbox-acl.ps1` present | **OK** | Path placeholder is clear |
| C29 | Generation is safe on failure (`spec-generator/SKILL.md:136`) | probe | **FAIL** | Invalid files written before exit 1 (MED-08) |
| C30 | Templates describe an existing engine (`task-templates/README.md:38-76`) | repo code | **FAIL** | No bus/sandbox/lock/git monitor (HIGH-09) |

---

## 6. SKILL.md frontmatter assessment (automatic selection)

| Skill | name/dir | Description size | Trigger style | Role/harness coupling | Body/description match | Verdict |
|---|---|---|---|---|---|---|
| `prd-generator` | OK | 141 chars | "Multi-agent product brainstorming ... engine" (no "Use when") | Body Antigravity 2.0-specific; desc generic | Desc says "engine"; deterministic script does not brainstorm multi-agent | **Needs rewrite** |
| `spec-generator` | OK | 166 chars | "Multi-agent deliberation and spec-generator skill to ingest PRD documents" (awkward, redundant) | Body Antigravity-specific; desc promises 4-specialist debate not run by CLI | Partially; deterministic mode bypasses debate | **Needs rewrite** |
| `task-decomposition` | OK | 212 chars | "Standard operating procedure for PlannerAgent to ..." (role jargon) | Assumes PlannerAgent + 4-doc/Goldilocks vocabulary | Matches body, but body's field names contradict template/linter | **Needs rewrite + fix contract** |
| `plan-linter` | OK | 227 chars | "Run the Gate 1 ... and Gate 2 ..." (jargon; implies runnable Gate 2) | Gate terminology suite-internal | Gate 2 is a manual prompt, not a tool | **Needs rewrite** |
| `diagnose-windows-sandbox-acl` | OK | 303 chars | "Use on Windows for unexpected DSH sandbox access denials..." (good trigger, too long) | DSH-specific (correctly stated) but unrelated to suite framing | Body matches; details belong in body | **Trim, keep trigger** |

Suite-level issues:
1. No description uses the recommended explicit activation sentence ("Use when ...") except `diagnose`; none states output artifact names/paths except `prd-generator`.
2. Three of four pipeline descriptions start with "Multi-agent" and mention 4 roles, so the router cannot distinguish PRD vs spec vs tasks; add inputs/outputs/boundaries.
3. Language: descriptions English, bodies Chinese; mixed signals for users.
4. No metadata field for version/license/author, no "requires" or harness note, no portability statement (diagnose is the only platform-stating skill).
5. `prd-generator` / `spec-generator` descriptions omit that deterministic mode is a bounded catalog/offline demo, the largest expectation gap.

---

## 7. Cross-document contradiction matrix

| Topic | Doc A (says) | Doc B (says) | Resolution needed |
|---|---|---|---|
| Number of task documents | `AGENTS.md:3-9`, `planner.md:4`, `skills/README.md:41` = 4 | `04-process.template.md:29`, design `:64,91` = 3 | Make 4 authoritative; fix two "three" texts |
| Traceability field names | `decomposition-rules.md:28-29`, `task-decomposition/SKILL.md:51`, design `:84` = `origin_spec_anchor`/`adherence_adrs` | Template has `PRD 溯源锚点`/`Tech Spec 锚点`; linter parses only `Tech Spec 锚点` | Add explicit rows and parse them; validate both |
| Handoff event name | template `:33`, logger `:40` = `HANDOFF_QA_REQUESTED` | logger docstring `:6`, design `:214` = `QA_REQUESTED` | One enum |
| Completion event name | template `:37`, logger `:70` = `TASK_TERMINATED_DONE` | design `:218` = `TASK_DONE` | One enum |
| QA status | template `:13`, logger `:51` = `VERIFYING` | design `:215` = `QA_VERIFYING` | One enum |
| Rework trigger | `qa.md:6` requires `[x] REWORK_REQUIRED` | logger docstring `:8` promises `REWORK_TRIGGERED`; no implementation | Implement or remove |
| Template directory naming | Root: `task-templates/`, `spec-templates/` | Bundles: `resources/templates/`; bundled spec README still calls itself `spec-templates/` | State canonical source per distribution mode |
| Role roster | `plan-linter/SKILL.md:24` adds `PlanReviewerAgent` | `rules/README.md:9-15` has 5 docs, no reviewer; design `:51-55` references nonexistent files | Add or remove the role |
| Language | `pm.md`/`architect.md` Chinese, detailed | `planner/dev/qa` English, terse; diagnose English | Unify or declare precedence |
| Hook command path | design `:178,192` = `.agents/scripts/...` | `hooks.json:9,23` = `scripts/...` | Fix hooks |
| Suite scope | `skills/README.md:3` = all Antigravity 2.0 native | `diagnose-windows-sandbox-acl` = DSH/Windows utility | Document the utility category |
| Spec filename | SKILLs/root README = `02-tech-spec.md` | `task-templates/README.md:73` = `tech-spec.md` | Use `02-tech-spec.md` everywhere |
| Test path/type | template `:73` = `tests/acceptance/test_{{TASK_ID}}.ts` | `decomposition-rules.md:42` = `tests/unit/test_xxx.py`; `rules/README.md:14` = `tests/` | Pick a convention or make it a placeholder |

---

## 8. Duplication / drift map

| Family | Canonical-looking location | Bundled copies | Current state | Drift risk |
|---|---|---|---|---|
| Task contract templates (5 files) | `task-templates/` | `task-decomposition/resources/templates/` | SHA-256 identical | High: 2 copies, no sync |
| PRD templates (7 files) | `spec-templates/` (root) | `prd-generator/resources/templates/` | 7 files identical; bundle **missing README** | High |
| PRD + tech-spec templates (9 files) | `spec-templates/` (root) | `spec-generator/resources/templates/` | 8 files identical; **README already diverged** | Already drifting |
| `plan_linter.py` | `.agents/scripts/plan_linter.py` | `plan-linter/scripts/plan_linter.py`; `scripts/plan_linter.py` wrapper | First two identical; wrapper delegates | Low |
| `run.py` entrypoints | per skill | — | prd/spec import repo package (BLK-04); plan-linter local | Blocker for prd/spec |

Counts: 15 root spec-template files + 7 PRD-bundle copies + 9 spec-bundle copies = **31 spec-template files in 3 locations**, plus 5 task templates in 2 locations = **41 duplicated template files**, zero sync/generation script.

---

## 9. Template field-consumption matrix (what any script actually reads)

| File | Field | Consumed by | Validation |
|---|---|---|---|
| `01-contract.md` | `**Task ID**` | `plan_linter.py:39` | regex only |
| `01-contract.md` | `**前置依赖**` | `:44` | parsed, DAG-checked |
| `01-contract.md` | `**预估代码量**` | `:55` | range check (declared value) |
| `01-contract.md` | `[CREATE]/[MODIFY]` whitelist | `:60-63` | count <= 3 (includes placeholders) |
| `01-contract.md` | `**Tech Spec 锚点**` | `:66-68` | non-empty, not starting with `{{` |
| `01-contract.md` | `继承 [ADR-...]` | `:71-74` | parsed, **never checked** |
| `01-contract.md` | `类型检查命令通过` | `:77-79` | non-empty, no `{{` |
| `01-contract.md` | `代码风格检查通过` | `:81-83` | parsed, **never checked** |
| `01-contract.md` | `对应验收测试文件` | `:85-87` | non-empty, no `{{` |
| `01-contract.md` | `反向/边界场景用例` | `:90-93` | >= 2 non-placeholder |
| `01-contract.md` | `PRD 溯源锚点` | nothing | NOT validated |
| `01-contract.md` | `爆炸半径限制` | nothing | NOT validated (only whitelist count) |
| `01-contract.md` | `CODE_INTERFACE_DEFINITION`, `INVARIANT_*`, `SCENARIO_*` | nothing | generic placeholder scan absent |
| `02-dev-workspace.md` | `[x] WAITING_FOR_QA` substring | `event_bus_logger.py:38` | false-positive/inversion (BLK-02/03) |
| `02-dev-workspace.md` | everything else | nothing | NOT validated |
| `03-qa-verification.md` | `[x] QA_PASSED` substring | `event_bus_logger.py:68` | false-positive (BLK-02) |
| `03-qa-verification.md` | `[x] REWORK_REQUIRED` | nothing | promised trigger has no consumer |
| `03-qa-verification.md` | test matrix, coverage, verdict comments | nothing | NOT validated |
| `04-process.md` | `macro_status`, `current_lock_holder` (YAML) | `event_bus_logger.py:49-58,78-87` | only these two keys; 5+ others never updated |
| `04-process.md` | event table rows | logger appends | guard broken by template sample (BLK-03) |
| `04-process.md` | retry/telemetry/breaker/human-ops sections | nothing | NOT updated |

---

## 10. Fix directions (priority order)

1. **Decide what ships.** Either (a) fix the hooks + engine claims, or (b) remove `hooks.json`, the RBAC/audit paragraphs, the sequence diagram and the "automatic" wording. Dead safety code is worse than none.
2. **Fix hook paths and add tests** (BLK-01); make failures loud.
3. **Make templates trigger-free and event-table-free** (BLK-02/03); add one integration test per template.
4. **Resolve 3 vs 4 docs everywhere** (HIGH-01).
5. **Unify the contract vocabulary** (`origin_spec_anchor`, `adherence_adrs`, lint command, PRD/Tech-Spec anchors) across template, rules, SKILL and linter; reject any unfilled placeholder in the whole contract (HIGH-02/03).
6. **Remove or parameterise every domain default** (HIGH-06): Postgres/Redis/Kafka/tenant_id/QPS/NFR thresholds/.ts/Docker; move examples to references; add a "no default" rule to the anti-contamination gate.
7. **Choose the packaging model** (BLK-04): bundle the engine or declare the dependency; delete the "self-contained/100% portable" claim if the former; add a copy-and-run packaging test.
8. **Single-source the templates** (HIGH-11): generate bundles from one tree in CI; checksum test; fix the already-diverged spec README.
9. **Rewrite the 5 frontmatter descriptions** for routing (HIGH-12) and normalize the language strategy (MED-01).
10. **Align validator claims with reality** (HIGH-07): implement or downgrade wording; add negative tests with known-bad Mermaid/SQL/TS/PRD.
11. **Document the utility skill** (MED-10) and the harness/layout assumptions (MED-11).
12. **Non-atomic writes** (MED-08): temp-dir + atomic move; delete failed outputs.

---

## Appendix A — Probe evidence

### A.1 Gate 1 rejects the field vocabulary the rules mandate
Command: `.venv/Scripts/python.exe .agents/skills/plan-linter/scripts/plan_linter.py -t artifacts/skill-audit/content/_probe/tasks`

Output (excerpt):
```text
❌ [Gate 1 FAILED] 质检未通过，共发现 6 项违规：
  1. [task-001] 粒度过小：预估代码量 0 行（下限 50 行）...
  5. [task-002] 缺失来源锚点：未指定 Tech Spec 对应章节，存在幻觉/虚构风险。
  6. 任务 [task-001] 依赖了不存在的任务 [{{DEPENDENCY_TASK_IDS}}]。
```
- task-001 = unmodified 4-document template copy.
- task-002 = contract using `origin_spec_anchor`/`adherence_adrs` exactly as `decomposition-rules.md:28-29` requires, with a valid Tech Spec anchor `02-tech-spec.md#sec-probe`; still rejected as "缺失来源锚点".
- task-001 passed the whitelist check with placeholder file names and failed only on line count/DoD/deps.

### A.2 Unfilled contract passes Gate 1
- task-003 = template with only Task ID/deps/lines/whitelist/DoD filled; `Tech Spec 锚点 = 02-tech-spec.md#{{SPEC_ANCHOR}}`, `{{CODE_INTERFACE_DEFINITION}}`, `{{INVARIANT_*}}`, `{{ADR_ID_*}}` left.
- The linter listed **no task-003 violation**; Gate 1 failed only because of task-001/task-002. This proves the "no placeholders" contract is not enforced and that the template anchor passes the `startswith("{{")` guard.

### A.3 Event logger on template copies
Probe imports `.agents/scripts/event_bus_logger.py`, copies `02/03/04` templates into a temp task dir, then calls `update_process_file()`.

Case A (unmodified 04-process template with sample EV-05/EV-09 rows):
```text
02 template literal [x] WAITING_FOR_QA present: True
03 template literal [x] QA_PASSED present: True
04-process changed by hook: False
EV-AUTO appended: False
macro_status now: {{CURRENT_MACRO_STATUS}}
```

Case B (same, after manually removing the two sample event rows, still zero dev work):
```text
04-process changed by hook: True
EV-AUTO appended: True
macro_status now: VERIFYING
```
- Conclusion: (1) with the shipped template the audit log is permanently inert; (2) without the sample rows the literal markers cause a false handoff immediately after task creation.

### A.4 Neutral-idea generation exposes hardcoded domains
- `python -m prd_generator run --idea "单机离线番茄钟桌面应用，无网络、无多租户、无后端" --output-dir ... --mode deterministic` -> exit 0; output contains multi-tenant auth (`_probe/generated/01-prd.md:34-37`), QPS 1,000 (`:60`), PostgreSQL/document-store forks (`:70-71`), and a non-kebab Chinese anchor (`:31`).
- `python -m spec_generator run --prd <that PRD> --output-dir ...` -> exit 1 with:
```text
Zero Template Contamination Violation: Non-ecommerce system contains hardcoded ecommerce scaffold artifact: HSM tokenization scaffold
Zero Template Contamination Violation: Non-ecommerce system contains hardcoded ecommerce scaffold artifact: Credit card tokenization scaffold
```
but it had already written `02-tech-spec.md`, `02-tech-spec/*` and ADRs; the generated topology contains `PostgreSQL`, `Redis Cluster`, `Apache Kafka`, `Envoy` (`_probe/generated_spec/02-tech-spec/01-topology.md:13,22-24`) despite the input being a single-user offline app. Direct evidence against "100% PRD-derived" and "zero contamination".

### A.5 Standalone packaging probe
```text
copy .agents/skills/prd-generator -> artifacts/skill-audit/content/_probe/standalone/prd-generator
python .../standalone/prd-generator/scripts/run.py --version
-> ModuleNotFoundError: No module named 'prd_generator'
```
(It succeeds under `.venv` only because that venv has an editable install pointing at the repo's `prd_generator/`.)

### A.6 Hook path probe
```text
python scripts/rbac_guard.py
-> can't open file 'D:/WorkSpace/Agent研究/scripts/rbac_guard.py': [Errno 2] No such file or directory
EXIT=2
Test-Path scripts/rbac_guard.py -> False
Test-Path .agents/scripts/rbac_guard.py -> True
```

### A.7 RBAC bypass probe (imported module, payload `toolCall.args.TargetFile`)
```text
dev      tests/acceptance/test_login.py                      -> allow
dev      D:/WorkSpace/Agent研究/tests/acceptance/test_login.py -> deny
qa       src/app.py                                          -> allow
qa       D:/WorkSpace/Agent研究/src/app.py                    -> deny
<unset>  tasks/task-001/01-contract.md                       -> allow
```
`AGY_AGENT_ROLE` is set nowhere in the repo, so in normal operation every role check is skipped.

### A.8 CLI availability probe
```text
prd-generator     NOT FOUND on PATH
prd_generator     NOT FOUND on PATH
spec-generator    FOUND: C:/Users/formal/.local/bin/spec-generator.exe
spec_generator    FOUND: C:/Users/formal/.local/bin/spec_generator.exe
.venv/Scripts/ has prd-generator.exe, prd_generator.exe, spec-generator.exe, spec_generator.exe
```

### A.9 Template hash summary
- IDENTICAL: 5/5 task-template pairs; 15/15 spec-template pairs across root/prd-bundle/spec-bundle (checked `01-prd.template.md`, `02-tech-spec.template.md`, `adr.template.md`, `01-prd/*`, `02-tech-spec/*`).
- DIFF: `spec-templates/README.md` vs `spec-generator/resources/templates/README.md`.
- MISSING: `prd-generator/resources/templates/README.md`.

### A.10 Verification that no source file was modified
All probes wrote only under `artifacts/skill-audit/content/_probe/`; `.agents/`, `task-templates/`, `spec-templates/`, `docs/`, `scripts/`, `prd_generator/`, `spec_generator/`, `tests/` were read-only. Generated probe outputs live under `_probe/generated*`.

---

## Appendix B — Files inspected

- `.agents/skills/README.md`; `.agents/skills/*/SKILL.md` (5); `.agents/skills/*/scripts/run.py` (3); `.agents/skills/task-decomposition/references/decomposition-rules.md`; `.agents/skills/prd-generator/references/agent-platform-patterns.md`.
- `.agents/skills/*/resources/templates/**` (all files; hashed).
- `.agents/rules/{README,pm,architect,planner,dev,qa}.md`.
- `.agents/hooks.json`; `.agents/scripts/{rbac_guard,event_bus_logger,prd_generator,spec_generator,plan_linter}.py`.
- `AGENTS.md`; `README.md`; `task-templates/**`; `spec-templates/**`; `docs/specs/PLANNER_LINTER_DESIGN.md`.
- Implementation cross-checks: `prd_generator/cli.py`, `prd_generator/validation/prd_linter.py`; `spec_generator/cli.py`, `validation/{spec_linter,mermaid_validator,interface_validator}.py`, `synthesis/tech_spec_synthesizer.py`; `tests/unit/test_plan_linter.py`, `tests/e2e/test_tier4_scenarios.py`.
- Probe artifacts: `artifacts/skill-audit/content/_probe/` (this audit's scratch; no source files modified).
