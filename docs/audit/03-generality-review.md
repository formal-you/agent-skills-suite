# Generality & Portability Review — `.agents/` Skill Suite

> **Archived report (2026-10-18).** Preserved verbatim from the v2 audit. Original probe
> fixtures under `artifacts/skill-audit/` were temporary; captured evidence is under
> [`evidence/`](evidence/) and current behavior is defined by
> [`../skills-v2-spec.md`](../skills-v2-spec.md).

**Reviewer:** generality-review (teammate)
**Date:** 2026-10-18
**Scope:** `.agents/skills/{prd-generator,spec-generator,task-decomposition,plan-linter,diagnose-windows-sandbox-acl}`, `.agents/rules/`, `.agents/scripts/`, `.agents/hooks.json`, and the root engines `prd_generator/` + `spec_generator/`.
**Mode:** audit only. No source file was modified. All probes and downloaded references live under `artifacts/skill-audit/generality/`.
**Question:** what must change so this suite is a **general-purpose, reusable Agent Skill set** rather than Antigravity/repo-bound scaffolding?

---

## 0. Executive summary (opinionated)

The five skills are a well-engineered **Antigravity pipeline for this repository**, not a reusable Agent Skill set. The strongest asset is the *design discipline* (agent does judgment, scripts do structure; explicit anti-hallucination rules; a real deterministic linter). The weakest part is that almost every promise in the SKILL.md files is true only inside the repository with Python 3.12, the engine packages on disk, and Antigravity as the host.

Verdict per theme:

| Theme | Verdict |
|---|---|
| Directory and naming (`.agents/skills/<name>/SKILL.md`) | **Already portable** — Codex, Antigravity and DSH all discover this exact layout; Claude Code needs a `.claude/skills` adapter. Do not move it. |
| Frontmatter essentials (name + description) | **Valid but under-optimized** — no `license`, `compatibility`, `metadata`; 4/5 descriptions do not front-load English "Use when…" triggers. |
| Progressive disclosure | **Partially done** — SKILL.md files are 63–168 lines (fine), but protocol details, 4-role rules and command matrices are duplicated into SKILL.md and `references/`; templates use the non-spec `resources/` name instead of `assets/`. |
| Harness portability | **Low**. Antigravity primitives in prose, Antigravity-only hooks, undocumented `AGY_AGENT_ROLE`, no per-harness adapter docs. |
| Self-containment | **Claimed, not true**. Copied out of the repo, `prd-generator`/`spec-generator` `run.py` fail with `ModuleNotFoundError`; only `plan-linter` and `diagnose-windows-sandbox-acl` truly travel. |
| Deterministic gates | **Keep, but demote** from a hard skill dependency to an optional local helper + required CI. The gates are valuable; their coupling is not. |
| Language | **Blocker for universal reuse**. 36 of 45 `.agents` files contain Chinese; the Gate-1 parser matches Chinese field labels, so a semantically valid English contract receives **5 false violations** (proved in §4-C6). |
| Engines | **Do not vendor into skills**. `prd_generator/` + `spec_generator/` are 52 files / 13,657 lines / ~680 KB of domain-heuristic code (ecommerce/fintech/healthcare/auth/notification), with canned sample content. They belong in a separately installable optional package. |

**One-line recommendation:** *Prompts travel; gates stay home.* Make the skills prompt-first, template-vendored and harness-neutral; ship the Python engines as an optional installable tool and the RBAC enforcement as a per-harness adapter plus a harness-neutral CI audit.

**Do / Split / Vendor / Delete:**

- **Keep** `task-decomposition` (already mostly portable), `plan-linter` (after de-duplication and language-neutral parsing), `diagnose-windows-sandbox-acl` (as a *platform-specific* skill).
- **Split** `prd-generator` and `spec-generator` into **prompt skill + optional external engine**; vendor only their templates and two small stdlib helpers (scaffold + lint).
- **Vendor** all templates once, under each skill's `assets/templates/`; the skill directory is the single source of truth.
- **Delete** the duplicated copies and shims listed in §10.3 (root `spec-templates/`, `task-templates/`, `.agents/scripts/plan_linter.py`, `scripts/*.py` shims, `.agents/scripts/{prd,spec}_generator.py`, `spec-generator/resources/templates/01-prd.template.md`, the `parents[4]` `run.py` wrappers).

---

## 1. What the public Agent Skills conventions actually require

Method note: `web_search` returned canonical URLs but the `web_fetch` tool in this environment refused every public host ("resolves to a non-public IP address"). I fetched the markdown editions of the official pages with `curl` into `artifacts/skill-audit/generality/_sources/` and cite those URLs. Quotations below are from those downloaded pages.

### 1.1 Open Agent Skills specification — https://agentskills.io/specification

- A skill is a directory with a required `SKILL.md`: `scripts/` (executable code), `references/` (docs), `assets/` (templates/resources) are optional, and "any additional files or directories" are allowed.
- Frontmatter: `name` **required**, ≤64 chars, lowercase `a-z0-9-` only, no leading/trailing/consecutive hyphens, **must match the parent directory name**; `description` **required**, 1–1024 chars, "describe both what the skill does and when to use it"; optional `license`, `compatibility` (≤500 chars), `metadata` (string→string map), `allowed-tools` (experimental).
- Progressive disclosure: metadata (~100 tokens) at startup → full `SKILL.md` on activation (<5,000 tokens recommended, **keep under 500 lines**) → `scripts/`/`references/`/`assets/` on demand.
- File references: relative paths from the skill root, "keep file references one level deep from SKILL.md".
- Validation: `skills-ref validate ./my-skill`.

### 1.2 OpenAI Codex / ChatGPT — https://developers.openai.com/codex/skills

- Codex builds on agentskills.io and **scans `.agents/skills` in every directory from CWD up to the repo root**, plus `$HOME/.agents/skills`, `/etc/codex/skills`, and bundled skills. So the current location is already a Codex-native location.
- Discovery is description-driven; the initial list is capped (2% of context, or 8,000 chars when unknown) and "Codex shortens skill descriptions first" — front-load trigger words.
- Best practices include: "Prefer instructions over scripts unless you need deterministic behavior or external tooling"; keep each skill focused on one job; "write imperative steps with explicit inputs and outputs".

### 1.3 Anthropic Claude Code — https://code.claude.com/docs/en/skills

- Loads skills from `.claude/skills/<name>/SKILL.md` (enterprise/personal/project/nested) and plugin skills; **symlinked skill folders are supported** ("a `<skill-name>` entry … can be a symlink to a directory elsewhere on disk").
- Follows the open standard, and when exchanging outside Claude Code restricts frontmatter to the spec's six fields: `name, description, license, compatibility, metadata, allowed-tools` (docs warn that extra keys produce "Unexpected key(s) in SKILL.md frontmatter").
- Claude-specific additions: `when_to_use`, `disable-model-invocation`, `allowed-tools`, etc. `description` + `when_to_use` share a **1,536-character cap**; put the key use case first.

### 1.4 Google Antigravity — https://antigravity.google/docs/skills, /docs/rules, /docs/hooks

- Skills: defaults to `.agents/skills` (legacy `.agent/skills`), global `~/.gemini/config/skills/` (App/IDE) or `~/.gemini/antigravity-cli/skills/` (CLI); progressive disclosure; optional `scripts/`, `examples/`, `resources/`.
- Rules: **"Every `.md` file inside `rules/` must start with YAML frontmatter declaring a valid `trigger`"**; missing/invalid frontmatter is **silently discarded**. The current five rule files have no frontmatter (§4-C5).
- Hooks: workspace `.agents/hooks.json`; `PreToolUse`/`PostToolUse` with tool-name regex matchers; stdin JSON `{toolCall:{name,args}, …}`, stdout decision JSON (`allow|deny|ask|auto_approve|force_ask|deny_unless_prior_grant`). This is an **Antigravity-specific contract**, not a portable one.
- Antigravity tool names are `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `run_command`, and subagent primitives `define_subagent`/`invoke_subagent`/`send_message`.

### 1.5 DSH (this harness)

No public skill-format page was checked; empirically this session loads exactly the five `.agents/skills` directories from the workspace (the skill catalog matches the directories one-to-one). Treat DSH as "reads `.agents/skills`, no documented hook contract".

### 1.6 What this means for the suite

The location, names and basic frontmatter are already conformant. The portability failures are **content-level** (language, harness primitives, repo paths, runtime dependencies), not structural. That is good news: no directory migration is required.

---

## 2. Assessment against the spec, per skill

| Skill | Lines | Name/dir | Description (spec) | Progressive disclosure | Self-contained? | Verdict |
|---|---:|---|---|---|---|---|
| prd-generator | 168 | OK (`prd-generator`) | 1 sentence, no explicit "Use when…", no trigger keywords for PRDs | SKILL.md holds the whole 4-role protocol + CLI matrix; no separate reference for the protocol | **No** — `run.py` imports root `prd_generator`; engine not in skill | **Split** prompt + optional engine |
| spec-generator | 157 | OK | Same weakness | Same; plus a stray PRD template | **No** — same import; engine not in skill | **Split** prompt + optional engine |
| task-decomposition | 125 | OK | Mentions "PlannerAgent"; jargon-bound but clear | Good: `references/decomposition-rules.md` + 4 templates | **Mostly** — pure Python linter via sibling skill path; templates vendored | **Keep**, fix cross-skill reference |
| plan-linter | 134 | OK | Long but trigger-rich | Good: script + Gate-2 prompt inline | **Yes** — 233-line stdlib script survives relocation (proved) | **Keep**, dedupe + make language-neutral |
| diagnose-windows-sandbox-acl | 63 | OK | Excellent ("Use on Windows for…") | Good; single PS1 black box | **Yes** (PowerShell) | **Keep**, but classify as platform-specific |

None of the SKILL.md files exceeds the 500-line guidance. None declares `license`, `compatibility` or `metadata`. Only `diagnose-windows-sandbox-acl` reads like a spec-era skill; the other four read like internal Antigravity runbooks.

---

## 3. Portability matrix

| Capability | Codex | Antigravity | Claude Code | DSH (this session) | Generic LLM |
|---|---|---|---|---|---|
| Native discovery path | `.agents/skills` ✅ | `.agents/skills` ✅ | `.claude/skills` ❌ (needs adapter) | `.agents/skills` ✅ (observed) | manual paste |
| Rules / persistent policy | `AGENTS.md` | `AGENTS.md` + `.agents/rules/*.md` (frontmatter required) | `CLAUDE.md` (not present) | `AGENTS.md` ✅ (loaded here) | prompt |
| Hook contract | none documented | `.agents/hooks.json` | `.claude/settings.json` hooks (different schema) | none documented | none |
| Subagent primitives | none | `define_subagent`/`invoke_subagent`/`send_message` | Task/Agent tools (different names) | `spawn_teammate` (this session) | none |
| Python engine discovery | user installs | user installs | user installs | user installs | must degrade |
| Global CLI on PATH | not guaranteed | not guaranteed | not guaranteed | not guaranteed | not guaranteed |

**Consequence:** any sentence in a SKILL.md that says "Antigravity 2.0 native instruction" or "already registered to system PATH" is a false portability claim outside one machine. Skills must describe *intent* ("spawn independent reviewers if the host supports subagents; otherwise simulate in-context") and detect tools rather than assume them.

---

## 4. Hard couplings, ranked (evidence-backed)

### C1 — Repo-root projection in `run.py` (severity: high)
`prd-generator/scripts/run.py` and `spec-generator/scripts/run.py` do `Path(__file__).resolve().parents[4]` to import `prd_generator`/`spec_generator` from the repo root. That index is only correct for `.agents/skills/<name>/scripts/run.py` in this repository; in `~/.agents/skills/` or `~/.claude/skills/` it resolves to the wrong ancestor or beyond root.

**Proof (run today):** copied `.agents/skills/prd-generator` to `artifacts/skill-audit/generality/_probe/prd-generator`; `python run.py --version` →
`ModuleNotFoundError: No module named 'prd_generator'` (exit 1), while the in-repo copy prints `prd-generator 0.1.0`. `plan-linter/scripts/plan_linter.py` copied the same way still prints `--help` (exit 0): only the linter is genuinely relocatable.

**Fix:** replace `run.py` with (a) a `find_spec("prd_generator")` probe and an explicit `exit 2` + fallback instructions, or (b) delete it and document `python -m prd_generator` for installed usage. Never insert a repo root into `sys.path`.

### C2 — Global CLI claim is environment-dependent (severity: medium)
SKILL.md says the CLI "已注册至系统 PATH". In a fresh shell here `Get-Command prd-generator` is empty; `.venv/Scripts/prd-generator.exe` exists but the venv is not on PATH. The claim is true only after `uv tool install --editable .` or venv activation.
**Fix:** document the install command and provide detection: use `python -m prd_generator` (module form) as the canonical invocation, or `uvx --from agent-spec-suite prd-generator`; state "if not installed, the workflow still works prompt-only".

### C3 — Engines live outside the skills, are large and domain-opinionated (severity: high)
`prd_generator/` = 24 files / 5,590 lines / 271 KB; `spec_generator/` = 28 files / 8,067 lines / 409 KB (≈13,657 lines, 680 KB). They contain hardcoded domain heuristics and canned content: `clarification/clarifier.py` ships ecommerce/fintech/healthcare/devtools vocabularies and example PRD text ("High-concurrency e-commerce ordering…", PCI-DSS, flash-sale QPS); `spec_generator/synthesis/tech_spec_synthesizer.py` (2,025 lines) detects domains and embeds ecommerce TypeScript payloads (`CheckoutOrderRequest`, `PaymentPreAuthRequest`), with a lint rule enumerating forbidden ecommerce artifacts (`spec_linter.py`). This is exactly the "template contamination" the skills warn against, displaced into the engine.
**Fix:** do not vendor the engines. Publishing them as a **separate optional distribution** (`agent-spec-suite`, stdlib-only, console scripts) is fine; skills must not require them. If a content synthesizer contradicts the "Agent writes, scripts scaffold/lint" boundary, deprecate the synthesis path for skill use (see §7).

### C4 — Antigravity-only subagent primitives in normative prose (severity: high)
`prd-generator` and `spec-generator` tell the model to dispatch "独立 SubAgent（`define_subagent` / `invoke_subagent` / `send_message`）". Those tool names exist only in Antigravity; Codex/Claude/DSH have different primitives or none. The instruction becomes hallucinated tool calls or a silent no-op.
**Fix:** express as a capability branch: "If the host provides subagent tools (names vary by harness), spawn independent reviewers; otherwise run the four roles as an explicit in-context CoT round and keep the same scoring/veto rules." Keep harness-specific names in an adapter note, not in the main workflow.

### C5 — Hooks + rules are Antigravity-specific and currently ineffective (severity: high)
- `.agents/hooks.json` matches `write_to_file|replace_file_content` (not `multi_replace_file_content`, not shell writes via `run_command`), and invokes `python scripts/rbac_guard.py`, but the file is at `.agents/scripts/rbac_guard.py` and no root `scripts/rbac_guard.py` exists. Unless the host runs hook commands with CWD=`.agents`, the hook command fails.
- `rbac_guard.py` reads `os.environ["AGY_AGENT_ROLE"]`, an **undocumented** Antigravity variable. If it is unset (the default), every role-based denial is skipped; only the role-independent `04-process.md` denial remains.
- Antigravity docs require YAML frontmatter with `trigger` in every `.agents/rules/*.md`; the five rule files (and `rules/README.md`) have none, so Antigravity **silently discards** all of them. The rules only "work" where the model happens to read files, or via the 3 lines in `AGENTS.md`.
**Fix:** treat hooks/rules as a **project governance adapter**, not part of the skill suite (§8). Add frontmatter, fix the command path, broaden the matcher, and replace `AGY_AGENT_ROLE` with an explicit `AGENT_ROLE` + per-harness adapter.

### C6 — Gate 1 parses Chinese labels, not structure (severity: high)
`plan_linter.py` extracts `**前置依赖**`, `**预估代码量**`, `**Tech Spec 锚点**`, `类型检查命令通过:`, `代码风格检查通过:`, `对应验收测试文件:`, `反向/边界场景用例`. Its output messages are Chinese-only.

**Proof (run today):** a semantically valid English `01-contract.md` (YAML-free, with `**Estimated Lines**`, `**Tech Spec Anchor**`, `Type check passes:`, etc.) produced **5 false violations**: estimated lines 0, missing anchor, missing type-check command, missing test file, 0/2 edge cases (exit 1). The linter is unusable outside the Chinese template dialect, and non-Chinese users see only Chinese error text.
**Fix (v2):** parse a YAML frontmatter block first (machine-readable, language-neutral), fall back to the legacy Chinese regex for one release; make thresholds configurable; emit English (or `--json`) messages. This is the single highest-leverage technical fix for universality.

### C7 — Duplicated entrypoints and templates (severity: medium, but drift risk)
- `plan_linter.py` exists as a 593-byte shim in root `scripts/`, and as **two byte-identical 8,197-byte copies** in `.agents/scripts/` and `.agents/skills/plan-linter/scripts/` (SHA-256 equal).
- 16 template files are byte-identical between root `spec-templates/`/`task-templates/` and the skills' `resources/templates/` (checked by SHA-256). Sizes: e.g. `01-contract` 3,651 B, `adr` 3,388 B.
- `spec-generator/resources/templates/01-prd.template.md` is a 5,206-byte duplicate of the PRD template that belongs to `prd-generator` — a stray file in the wrong skill.
- `spec-generator/resources/templates/README.md` differs from `spec-templates/README.md` (2,076 vs 2,734 B) — already drifted.
**Fix:** exactly one canonical copy of each file; delete/symlink the rest; add a CI duplicate check.

### C8 — Hardcoded repo paths and 5-way command matrices (severity: medium)
Every SKILL.md documents 3–5 absolute-from-repo-root invocation paths (`.agents/skills/.../run.py`, `.agents/scripts/...`, `scripts/...`, global CLI). This bloats context (progressive disclosure violation), goes stale, and teaches the model to depend on repo layout. `task-decomposition` reaches into a *sibling skill* (`../plan-linter/scripts/plan_linter.py`), a cross-skill dependency that breaks when skills are installed independently.
**Fix:** one canonical command per skill (`python scripts/<tool>.py` relative to the skill root), and a harness/install note in references. Cross-skill script references: either vendor the linter into the skill or document optional invocation via installed console script.

### C9 — Language and locale (severity: high for "general-purpose")
36 of 45 files under `.agents` contain CJK; the SKILL.md bodies, templates, linter messages and rule files are Chinese-first. Even if a non-Chinese user can run the workflow, outputs and gate errors are Chinese, and Gate 1 depends on Chinese headings (C6).
**Fix:** English canonical docs/templates with optional `references/zh-CN/` translations; output language is the user's language (the model already does this); machine gates parse structure, never prose.

### C10 — Python/runtime assumptions and platform syntax (severity: low-medium)
- `pyproject.toml` requires Python `>=3.12`; the code only needs `typing.Self` (**3.11+**) and PEP 604 annotations; no 3.12-only syntax was found. The 3.12 claim narrows reuse unnecessarily.
- Scripts are invoked as `python …` everywhere; macOS/Linux often expose only `python3`/`py -3`; Windows-only PowerShell skill is fine but needs `compatibility`.
- No absolute paths were found in `.agents` (good).
**Fix:** target `>=3.11` for the engine, `>=3.9` for vendored skill scripts; document the interpreter probe; add `compatibility` frontmatter.

### C11 — "Self-contained" is over-claimed (severity: medium, trust)
`.agents/skills/README.md` claims all skills are "100% 自包含（Self-Contained）" and can be "整包单独抽离分发". For `prd-generator`/`spec-generator` this is false (C1/C3). Over-claiming harms adoption more than a smaller honest scope.
**Fix:** per-skill "Requirements" section and `compatibility` field; state exactly what remains when the engine/Python is absent.

---

## 5. Per-skill disposition

### 5.1 prd-generator — **SPLIT** (prompt workflow + optional engine)
- Keep the name and the 4-role model; rewrite SKILL.md in English, target ≤200 lines.
- Move the deliberation protocol (roles, scoring/MCDA, veto, tie-break) and output contract (`01-prd.md` + `01-prd/`) into `references/`.
- Move templates to `assets/templates/01-prd/`.
- Vendored helpers (stdlib, no engine): `scripts/scaffold.py` (copy templates, refuse to overwrite, `--dry-run`), `scripts/lint_prd.py` (placeholders, `#sec-*` anchors, CON/NFR/FORK presence, `--json`).
- Optional: `scripts/engine.py` that proxies `prd_generator` only if `find_spec` succeeds, exiting 2 with install instructions otherwise.
- Delete `references/agent-platform-patterns.md` from this skill (or move it to a repo `docs/domain-notes/`): it is a narrow domain note, not PRD methodology, and it violates "each skill one job".
- Remove all global-CLI/PATH claims and Antigravity subagent names.

### 5.2 spec-generator — **SPLIT** (prompt workflow + optional engine)
- Same treatment; keep ADR + `02-tech-spec/` templates, **delete the stray `01-prd.template.md`**.
- Move the architecture-review protocol and the Gate checklist into `references/`.
- Make project opinions explicit instead of universal: "TypeScript `type` over `interface`" and the "no ecommerce artifacts" deny-list are team conventions → put them in `references/project-conventions.md` (or repo rules), not in the core workflow.
- Vendored helpers: `scaffold.py`, `lint_spec.py` (Mermaid fence/AST-lite check, SQL/TS placeholder scan, anchor coverage; `--json`). Optional engine proxy as above.

### 5.3 task-decomposition — **KEEP** (best-in-class portability)
- Keep pure prompt + references + templates (no engine).
- Replace the cross-skill linter path with: "run the plan-linter skill if installed; otherwise run its vendored copy / perform the manual Gate-1 checklist."
- Generalize role naming ("the agent acting as planner"), make thresholds configurable (3 files / 50–250 lines are team policy, not universal truth), and mark `04-process.md` as derived/optional.
- Add YAML frontmatter to `01-contract.template.md` (see §6.6) so the gate is language-neutral.

### 5.4 plan-linter — **KEEP + REWRITE PARSING**
- De-duplicate to one file; delete the other two copies/shims.
- v2: parse frontmatter first, legacy regex fallback; configurable thresholds via `--config` or `.agents/plan-linter.json`; `--json`; English messages; `--version`.
- Keep Gate 2 as an English review prompt in `references/gate2-review.md` (semantic review is inherently a prompt, which is good: it travels).
- Keep exit codes `0/1/2` and document them.

### 5.5 diagnose-windows-sandbox-acl — **KEEP, classify as platform-specific**
- This is the model to imitate: English, trigger-rich description, one bundled black-box script, explicit "when not to use it".
- Add `compatibility: Windows; DSH sandbox` and `metadata.category: platform`. Exclude it from the "universal" release bundle (install as a separate platform skill).
- Note: it is currently **untracked** in git (`?? .agents/skills/diagnose-windows-sandbox-acl/`); decide whether the repo owns it or it is a DSH-provided skill.

---

## 6. Target universal architecture

### 6.1 Principles
1. **Skill = prompt + optional tools.** Every step must be executable by a model with only file tools; scripts accelerate, never gate.
2. **Location is already right.** Keep `.agents/skills/` canonical (Codex + Antigravity + DSH native); add `.claude/skills` links for Claude Code.
3. **One canonical file per artifact.** Templates and scripts live exactly once, in the owning skill.
4. **Machine-readable before human-readable.** Structural gates read frontmatter/JSON, never localized prose.
5. **Project policy ≠ skill.** RBAC, 4-document format, thresholds, "type over interface" are repo conventions shipped as adapters/templates, not as universal claims.
6. **English canonical, localized by output, not by tooling.**

### 6.2 Target tree

~~~text
<repo>/
├─ .agents/
│  ├─ skills/                          # CANONICAL source of truth (Codex/Antigravity/DSH)
│  │  ├─ prd-generator/
│  │  │  ├─ SKILL.md                   # English, <=200 lines, triggers + workflow + fallback
│  │  │  ├─ references/
│  │  │  │  ├─ deliberation-protocol.md
│  │  │  │  ├─ prd-output-contract.md
│  │  │  │  └─ zh-CN.md                # optional translation, not required at runtime
│  │  │  ├─ assets/templates/          # vendored: 01-prd.template.md + 01-prd/*
│  │  │  └─ scripts/
│  │  │     ├─ scaffold.py             # stdlib, works with no engine
│  │  │     ├─ lint_prd.py             # stdlib, works with no engine
│  │  │     └─ engine.py               # optional proxy: find_spec -> exit 2 + guidance
│  │  ├─ spec-generator/               # same shape; templates: adr + 02-tech-spec/*
│  │  ├─ task-decomposition/
│  │  │  ├─ SKILL.md
│  │  │  ├─ references/decomposition-rules.md
│  │  │  ├─ assets/templates/01-contract..04-process.template.md
│  │  │  └─ scripts/                   # none required; optional check_plan.py pointer
│  │  ├─ plan-linter/
│  │  │  ├─ SKILL.md
│  │  │  ├─ references/gate2-review.md
│  │  │  ├─ scripts/plan_linter.py     # THE only copy
│  │  │  └─ config.example.json        # thresholds, severity policy
│  │  └─ diagnose-windows-sandbox-acl/ # platform-specific; compatibility: Windows/DSH
│  ├─ rules/                           # project governance (frontmatter + English)
│  ├─ hooks.json                       # Antigravity adapter only (optional)
│  └─ scripts/                         # project adapters: rbac_guard.py, event_bus_logger.py, rbac_audit.py
├─ .claude/
│  └─ skills/                          # symlinks or installer-generated (Claude Code)
├─ tools/
│  ├─ install_skills.py                # link/copy .agents/skills -> ~/.agents/skills, .claude/skills
│  └─ rbac_audit.py                    # harness-neutral git-based enforcement (CI)
├─ packages/
│  └─ agent-spec-engine/               # optional; prd_generator/ + spec_generator/ + pyproject
│     └─ pyproject.toml                # console scripts; requires-python >=3.11
└─ docs/
   └─ skills-compatibility.md          # matrix + install per harness + what degrades
~~~

Notes:
- `packages/agent-spec-engine` is a **move, not a rewrite**; it can be done last (or skipped if the repo keeps the engines at root — what matters is that skills do not import them via `sys.path` hacks).
- `assets/templates/` replaces `resources/templates/`: `assets` is the name in the open spec; Antigravity also accepts `resources/`, but one name is better than two.
- Keep the five flat skill directories. Do **not** nest them (e.g. `skills/spec/prd-generator`) — discovery is by direct child.

### 6.3 Frontmatter template (all skills)

~~~yaml
---
name: prd-generator
description: Turn a vague product idea into a modular PRD bundle (01-prd.md and 01-prd/). Use when the user asks for a PRD, product requirements, feature scoping, MVP definition, or a PRD revision.
license: Apache-2.0
compatibility: Harness-agnostic prompt workflow. Optional Python 3.9+ for deterministic scaffolding and structural linting; every step also has a manual fallback.
metadata:
  version: "2.0.0"
  category: spec-pipeline
  optional_engine: "agent-spec-suite>=0.1"
  outputs: "01-prd.md, 01-prd/"
---
~~~

Rules:
- `name` = directory name, lowercase, hyphens only.
- `description`: English, one sentence of *what* + one of *when*, trigger keywords first, ≤1024 chars (≤1,536 combined with Claude's `when_to_use`); avoid "engine" or harness jargon until later in the sentence.
- `compatibility` for platform/engine needs (≤500 chars). `metadata` for version/category/engine.
- Omit `allowed-tools` unless every target harness supports it; it is experimental.

### 6.4 SKILL.md skeleton

~~~markdown
---
(name/description/frontmatter as above)
---
# <Skill name>

One-paragraph outcome statement + when to use / when not to use.

## Inputs / Outputs
Concrete paths, file names, and the contract each artifact must satisfy.

## Workflow
Numbered imperative steps. Judgment steps name the roles and the decision rule.
Capability branches: "If the host has subagent tools, …; otherwise …".

## Tooling (optional)
Decision tree:
    python scripts/scaffold.py --out .specs        # always available
    python scripts/lint_prd.py .specs/01-prd.md    # always available; exit 1 = fix and rerun
    python scripts/engine.py run ...               # only if agent-spec-suite is installed
If Python is unavailable or a script is missing, do these steps manually: <checklist>.

## Quality gate
What must be true before declaring done. State which checks are deterministic vs judgment.

## References
- references/… (one level deep)
~~~

Keep `SKILL.md` under ~200 lines; move protocols, examples and long examples to `references/`.

### 6.5 Script contract (all bundled tools)
- Resolve paths from `Path(__file__).resolve().parent`, never from the repository root.
- Python ≥3.9 syntax, standard library only, no network, no writes outside `--out`.
- `--help`, `--version`, `--json`; deterministic output; exit codes: **0** success, **1** gate/content failure, **2** optional dependency unavailable, **3** usage error.
- No locale-dependent parsing; read YAML frontmatter from a tiny built-in parser (no PyYAML) or a strict line-based format.
- Idempotent scaffolding: refuse to overwrite unless `--force`; print the list of created/skipped files.
- Black-box friendly: the host may run `--help` instead of reading the source (Antigravity best practice).

### 6.6 Template ownership and machine-readable contracts

Canonical template owners:
- `01-prd*` → `prd-generator/assets/templates/`
- `adr.template.md`, `02-tech-spec*` → `spec-generator/assets/templates/`
- `01-contract`, `02-dev-workspace`, `03-qa-verification`, `04-process` → `task-decomposition/assets/templates/`

Delete root `spec-templates/` and `task-templates/` (or make them generated symlinks). Do not keep two copies.

Make `01-contract.template.md` start with machine-readable frontmatter; keep the existing human tables below it for one migration window:

~~~yaml
---
task_id: task-001
dependencies: []
estimated_lines: 120
touch_files:
  - {action: create, path: src/feature.py}
origin_spec_anchor: "#sec-feature"
adherence_adrs: [ADR-001]
dod:
  type_check: "mypy src/feature.py"
  lint: "ruff check src/feature.py"
  test_file: tests/unit/test_feature.py
  edge_cases:
    - "empty input returns a validation error"
    - "duplicate id is rejected"
---
~~~

The v2 linter parses this first, then falls back to today's regex. This decouples the gate from language and template wording in one change.

### 6.7 Language strategy
- **English** is canonical for `SKILL.md`, `references/`, script messages and templates.
- Keep Chinese as `references/zh-CN.md` (and optionally `assets/templates/zh-CN/`) for users who want it; never require it at runtime.
- Output documents are written in the user's language regardless; the templates' *headings* can stay English because the gate reads frontmatter, not headings.

### 6.8 Discovery / installation matrix
- Native (Codex, Antigravity, DSH): do nothing; `.agents/skills` is discovered.
- Claude Code: `.claude/skills/<name>` → symlink/junction to `../../.agents/skills/<name>` (supported by Claude Code); on Windows a symlink needs Developer Mode, so the installer should fall back to a copy and print a warning.
- Personal reuse: `~/.agents/skills/` (Codex) and `~/.claude/skills/` (Claude).
- Distribution: package the four pipeline skills as a plugin/skill bundle (Codex plugins or a git repo users add as a skill directory); the engine is a separate pip/uv tool.
- Add `docs/skills-compatibility.md`: one table of harness → discovery path → rules file → enforcement level.

### 6.9 Configurability of "Goldilocks" policy
The 3-file / 50–250-line rule is a team heuristic, not a universal law. Put it in `references/decomposition-rules.md` **and** a config the linter reads:

~~~json
{
  "max_touch_files": 3,
  "min_diff_lines": 50,
  "max_diff_lines": 250,
  "require_anchor": true,
  "min_edge_cases": 2,
  "language": "en"
}
~~~

Default to the current values; other teams can change them without editing code.

---

## 7. Optional Python engines: keep, but degrade gracefully

**Decision table**

| Environment | Behavior |
|---|---|
| No Python, no engine | Full prompt workflow. Templates are copied by the agent (or read directly). Self-check checklist in SKILL.md. No failure state. |
| Python, no engine installed | `scaffold.py` and `lint_*.py` work (stdlib). `engine.py` exits `2` with one-line install guidance. |
| Python + `agent-spec-suite` installed | Optional acceleration: `prd-generator run/lint`, `spec-generator run`; still validate with the vendored lint script. |
| CI | Gates run there, always, with the engine installed (or with the small lint scripts). |

**Why not vendor the engines:** ~13.7k lines / 680 KB, hardcoded domain heuristics and canned sample content, Chinese strings, and a deterministic synthesizer whose output is template-shaped — the opposite of the "agent authors, scripts check" contract the skills advertise. Vendoring would make each skill unmaintainable and would put domain bias *inside* a universal package.

**What to vendor instead:** two small stdlib helpers per skill, plus templates. The current PRD linter is 174 lines and the spec linter 437 lines with model imports; extract the checks (placeholders, anchors, section presence, Mermaid fence, dangling refs) into a ~200-line standalone `lint_*.py` with no package imports. That is cheaper than keeping the engine as a skill dependency.

**Engine invocation contract (replacement for `run.py`):**

~~~python
#!/usr/bin/env python3
"""Optional engine proxy. Exit 2 when the engine is not installed."""
import importlib.util, sys
from pathlib import Path

def main() -> int:
    if importlib.util.find_spec("prd_generator") is None:
        sys.stderr.write(
            "Optional engine 'agent-spec-suite' is not installed.\n"
            "Continue with the prompt workflow: run scripts/scaffold.py, then scripts/lint_prd.py.\n"
            "Install with: uv tool install agent-spec-suite\n")
        return 2
    from prd_generator.cli import main as engine_main
    return engine_main()

if __name__ == "__main__":
    sys.exit(main())
~~~

Additionally add `--mode scaffold` to the engine's `run` (templates only, no content synthesis) and point the SKILL.md default at scaffolding + lint. Deprecate `--mode deterministic` for skill use: deterministic *content* generation is where template contamination and domain bias come from, and it contradicts the skills' own philosophy.

---

## 8. The 4-document RBAC workflow across harnesses (the real conflict)

### 8.1 The conflict
The suite claims "物理级强制拦截" (physical enforcement) via hooks. That is achievable on **exactly one harness** (Antigravity, and currently broken — C5). Codex, Claude Code and DSH use different hook schemas or none; a skill cannot ship a universal hook. If the suite promises RBAC as part of the skills, it is not portable. If it drops enforcement, the anti-cheat posture weakens.

### 8.2 Layered model (recommended)

| Layer | Mechanism | Portability | Guarantee |
|---|---|---|---|
| L0 | Prompt policy in `AGENTS.md`/`CLAUDE.md` + role rules injected by the skill | universal | advisory |
| L1 | Tool hooks (Antigravity `hooks.json`, Claude Code `settings.json`) | per-harness | best-effort, bypassable (shell writes, alternate tools) |
| L2 | Post-hoc **git-based audit** (`tools/rbac_audit.py`) in CI | universal | strong for commits, not live |
| L3 | Branch protection / required reviewers / CODEOWNERS / separate workspaces | universal | strong |

Recommendation: keep L0 and L1, but **make L2/L3 the authoritative answer** and say so. "Physical enforcement" becomes "enforced in CI and by repository permissions; hooks are a local speed bump."

### 8.3 Per-harness adapters
- **Antigravity**: keep `.agents/hooks.json` as an adapter. Fix the command path (`.agents/scripts/rbac_guard.py`), add `multi_replace_file_content` and `run_command`, replace `AGY_AGENT_ROLE` with a documented `AGENT_ROLE` set by the workspace, and add the required `trigger` frontmatter to `.agents/rules/*.md`.
- **Claude Code**: ship an optional `.claude/settings.json` snippet with `PreToolUse` matchers for `Edit|Write` calling the same guard; document that it is not installed by default.
- **Codex / DSH / generic**: no adapter; rely on L0 + L2/L3.

### 8.4 `tools/rbac_audit.py` (harness-neutral)
Inputs: `--base <git-ref>`, `--tasks-dir tasks`, optional `--role-source` (commit trailer, task file field, or explicit `--role`). Checks:
1. `tests/acceptance/**` changed in a commit whose declared role is `dev` → fail.
2. `src/**` changed by a `qa` commit → fail.
3. `01-contract.md` changed after planning (i.e. after the commit that created `tasks/task-*/`) → fail unless the commit is the planner's and is the initial creation.
4. `04-process.md` hand-edited (diff is not append-only by the event tool) → fail or warn.
5. `03-qa-verification.md` signed off by the same commit that touched `src/` → warn.
6. Missing sign-off → warn (policy).

This runs anywhere Git runs — CI, a pre-push hook, or an agent-invoked command. It is the only way to make the 4-document RBAC claim honest across harnesses.

### 8.5 What to do with the 4-document pipeline and the event bus
- Keep the **4-document format** as a project convention (templates + rules). It is good.
- Make `04-process.md` **derived**: generated/verified by `rbac_audit.py` or the hooks, marked `generated: do not edit by hand`. Without hooks, the agent may append events via `tools/emit_event.py` as a *convenience*, but CI regenerates/verifies.
- Skills should reference the 4-document workflow as "when the target repo uses this convention", not as a universal requirement. `task-decomposition` keeps the templates but lands them in `assets/templates/`, never hardcodes `tasks/` as the only allowed location (default `tasks/`, allow `--tasks-dir`).

### 8.6 Minimal honest wording for README/SKILL.md
> "These skills follow the repo's 4-document convention. RBAC is enforced by the repository's CI audit and branch protections. On Antigravity, optional workspace hooks add a local pre-write guard; other harnesses rely on the audit."

---

## 9. Tradeoff: "universal prompt workflow" vs "deterministic machine gates"

| Property | Prompt workflow | Deterministic gate |
|---|---|---|
| Portability | any harness | needs interpreter + script + file conventions |
| Context cost | one SKILL.md read | one short command + parsed errors |
| Reliability | judgment; can skip steps | reproducible, exact |
| Failure mode | silent degradation, hallucinated steps | false failures on localization/format drift (C6), brittle coupling |
| Maintenance | prose edits | code + tests, versioning |
| Semantic judgment | strong | impossible |
| Enforcement | advisory | strong when wired into CI |

**Recommendation: hybrid, with explicit ownership.**
- The **skill** owns judgment (roles, tradeoffs, ADR content, hallucination review) and *describes* the gate. It must remain complete without scripts.
- The **repo/CI** owns determinism (structure, placeholders, DAG, language). Gates are required in CI, optional locally.
- **Gate 2 (semantic anti-hallucination review) is inherently prompt-only**; keep it as a reference prompt. Do not pretend a script can do it.
- **Gate 1** stays a script, but is a *repo tool* invoked by the skill if present; the skill also ships a manual checklist with identical criteria.
- Do not put "must run `python …`" as a precondition for the workflow to succeed; that is the line between a reusable skill and a project runbook.

---

## 10. Phased migration plan

### Phase 0 — Baseline & guardrails (0.5–1 day)
- Add `skills-ref validate` (or an equivalent local check) to CI; record the current state.
- Freeze new template copies; announce "one canonical copy" rule.
- Exit: CI validates all five SKILL.md files; no new duplicates.

### Phase 1 — Low-risk de-duplication and frontmatter (2–3 days)
- Delete `.agents/scripts/plan_linter.py` (keep the skill copy) or invert; delete root `scripts/*.py` shims.
- Delete `spec-generator/resources/templates/01-prd.template.md`.
- Delete root `spec-templates/` and `task-templates/` or convert to generated pointers.
- Delete `.agents/scripts/{prd,spec}_generator.py` (keep console scripts / module invocation).
- Add golden frontmatter to all five SKILL.md (`license`, `compatibility`, `metadata`) and rewrite descriptions with English "Use when…" triggers.
- Add `trigger: model_decision` frontmatter to `.agents/rules/*.md`; move `rules/README.md` out of `rules/`.
- Exit: `sha256` duplicate scan clean; all skills validate; rule files recognized by Antigravity; no behavior change for users.

### Phase 2 — Engine decoupling and script contract (4–6 days)
- Add `scripts/scaffold.py` + `scripts/lint_prd.py` / `lint_spec.py` to the two engine-backed skills (stdlib, no package imports).
- Replace `run.py` with the `find_spec` proxy (exit 2 + guidance); remove `parents[4]`.
- Make `prd-generator`/`spec-generator` CLI optional in SKILL.md; document install; add `--mode scaffold`.
- Move engines to `packages/agent-spec-engine/` (or keep at root but out of the skill dependency path); lower `requires-python` to `>=3.11`.
- Add `tools/install_skills.py` and `.claude/skills` linking.
- Exit: delete the repo copy of a skill into a temp dir, run its documented commands — scaffolding and lint still work; `--version` works; engine absent path prints helpful text.

### Phase 3 — Language-neutral machine gate (3–5 days)
- Add YAML frontmatter to `01-contract.template.md`; update linter v2 to parse frontmatter first, legacy regex fallback.
- Add config file for thresholds; add `--json`, `--lang`, English messages.
- Expand lint scripts to PRD/spec checks; add tests for English and Chinese contracts.
- Exit: the English contract probe passes; the existing Chinese tasks still pass; a deliberately bad contract still fails with actionable English output.

### Phase 4 — Governance adapters and docs (2–3 days)
- Implement `tools/rbac_audit.py` + CI job; regenerate/verify `04-process.md`.
- Fix Antigravity hook adapter (path, matcher, `AGENT_ROLE`); add optional Claude Code settings snippet.
- Rewrite `.agents/skills/README.md` and root README sections to the honest per-harness matrix; move the 4-document/RBAC rationale to `docs/`.
- Exit: removing `hooks.json` does not break any skill; CI audit catches a simulated Dev→tests edit.

### Phase 5 — i18n and cleanup (2–3 days)
- Translate SKILL.md/references to English canonical; add `references/zh-CN.md`; translate templates (frontmatter first, prose later).
- Remove `resources/` in favor of `assets/`; update all links; verify one-level-deep references.
- Update `AGENTS.md` (point to docs/skills); final `skills-ref validate`; tag a release.
- Exit: external reviewer with no repo context can install and run each skill from the README alone.

Total: roughly **2–3 focused weeks** for one developer; Phases 1 and 3 deliver most of the portability value and can ship independently. Rollback: each phase is file-additive except deletions in Phase 1 — do those on a branch with a duplicate-check CI job.

### 10.1 Explicit delete/dedupe list
1. `.agents/scripts/plan_linter.py` (8,197 B duplicate).
2. `scripts/plan_linter.py` (593 B shim), `scripts/prd_generator.py`, `scripts/spec_generator.py` (repo-root shims).
3. `.agents/scripts/prd_generator.py`, `.agents/scripts/spec_generator.py` (duplicate wrappers).
4. `.agents/skills/prd-generator/scripts/run.py`, `.agents/skills/spec-generator/scripts/run.py` (`parents[4]`), and `.agents/skills/plan-linter/scripts/run.py` (redundant with the script).
5. `.agents/skills/spec-generator/resources/templates/01-prd.template.md` (stray).
6. Root `spec-templates/` and `task-templates/` (16 duplicate files) — delete or generate.
7. `.agents/rules/README.md` — move to `docs/` (it is not a rule; Antigravity would discard it).
8. `.agents/skills/README.md` — replace with a short English index or move the long pipeline map to `docs/`.
9. Optional: `prd-generator/references/agent-platform-patterns.md` (domain-specific; move to `docs/domain-notes/`).

---

## 11. Risks and the three riskiest decisions

### R1 (riskiest) — Decoupling the deterministic engines
The engines are the project's largest deliverable (13.7k lines, tests, demo). Making them optional changes the advertised experience ("run this one command") and risks breaking the 300 unit / 104 e2e tests and `uv tool install`. Mitigation: do not delete or rewrite engines; only stop *requiring* them in skills, add vendored scaffold/lint first, and keep the CLI functional. Treat the move to `packages/` as optional Phase 2b.

### R2 (riskiest) — Frontmatter-first contracts + English templates
This touches every existing task, the linter regex, the demo project and the tests; templates are the interface between phases. Mitigation: dual-parse (frontmatter first, legacy regex fallback) for at least one release; keep Chinese templates in `zh-CN/`; add a migration script; gate the change behind linter tests for both languages.

### R3 (riskiest) — Demoting hooks/RBAC from "physical" to "best-effort + CI"
If the owner values the anti-cheat guarantee, this reads as a regression. Mitigation: implement L2 `rbac_audit.py` **before** removing any hook wording; demonstrate it catching a Dev-edits-tests violation; then rewrite the docs. Keep the Antigravity hook as an optional enhancement, not a promise.

**Other risks**
- **Windows symlinks** for `.claude/skills`: require Developer Mode/admin; installer must fall back to copy and warn.
- **Description truncation** in Codex (2%/8k chars): long Chinese descriptions with the trigger at the end may never be shown; front-load English triggers.
- **Duplicate drift** returns: add a CI hash check across `assets/templates` and scripts.
- **Chinese-first users** may see the English rewrite as a loss: keep `zh-CN.md` references and let the agent answer in Chinese.
- **Distribution**: `.agents/skills` works in-repo for Codex/Antigravity/DSH; outside a repo, users need `~/.agents/skills` or a plugin; document both.
- **Gate 2 cannot be automated**: keep it as a prompt and be honest about it; do not let "Gate 1 passed" imply semantic correctness.

---

## 12. Citations

1. Agent Skills specification — https://agentskills.io/specification (name/description/optional fields, directory layout, progressive disclosure, 500-line guidance, relative references, `skills-ref`).
2. Agent Skills home — https://agentskills.io/home (open standard referenced by Codex and Antigravity).
3. OpenAI Codex — Build skills — https://developers.openai.com/codex/skills (`.agents/skills` discovery up to repo root, `$HOME/.agents/skills`, description truncation budget, "prefer instructions over scripts").
4. Claude Code — Extend Claude with skills — https://code.claude.com/docs/en/skills (`.claude/skills` scopes, symlinked folders, six-field spec frontmatter, 1,536-char description cap, `when_to_use`).
5. Antigravity — Agent skills — https://antigravity.google/docs/skills (`.agents/skills`, legacy `.agent/skills`, progressive disclosure, `scripts/`/`resources/`).
6. Antigravity — Rules — https://antigravity.google/docs/rules (frontmatter `trigger` required in `.agents/rules/*.md`; missing frontmatter silently discarded).
7. Antigravity — Hooks — https://antigravity.google/docs/hooks (`.agents/hooks.json`, matchers, stdin/stdout JSON contract, tool names).

Downloaded copies for audit reproducibility: `artifacts/skill-audit/generality/_sources/`.

---

## Appendix A — Empirical evidence (commands run today)

~~~text
1) Relocation probe (self-containment)
   Copy .agents/skills/prd-generator -> artifacts/.../_probe/prd-generator
   python _probe/prd-generator/scripts/run.py --version
     -> ModuleNotFoundError: No module named 'prd_generator'   (exit 1)
   python .agents/skills/prd-generator/scripts/run.py --version
     -> prd-generator 0.1.0                                     (exit 0)
   Copy .agents/skills/plan-linter -> artifacts/.../_probe/plan-linter
   python _probe/plan-linter/scripts/plan_linter.py --help     (exit 0)
     -> usage: plan_linter.py [-h] [--tasks-dir TASKS_DIR]

2) English contract probe (language coupling)
   artifacts/.../_probe/tasks/task-001/01-contract.md written with English labels
   python .agents/skills/plan-linter/scripts/plan_linter.py -t _probe/tasks
     -> Gate 1 FAILED, 5 violations (lines=0, missing anchor, missing type-check,
        missing test file, 0/2 edge cases), exit 1

3) CLI availability
   Get-Command prd-generator  -> not found in this shell
   .venv/Scripts/prd-generator.exe exists (venv not on PATH)

4) Duplicate inventory (SHA-256)
   .agents/scripts/plan_linter.py == .agents/skills/plan-linter/scripts/plan_linter.py (8,197 B)
   scripts/plan_linter.py = 593 B shim
   16 template pairs identical root vs skill; spec-generator/01-prd.template.md stray duplicate

5) Language inventory
   36 of 45 files under .agents/ contain CJK; SKILL.md bodies are Chinese-first

6) Scale
   prd_generator: 24 files, 5,590 lines, 271,477 B
   spec_generator: 28 files, 8,067 lines, 408,956 B
~~~

## Appendix B — Files inspected
`.agents/skills/*/SKILL.md` (5), `.agents/skills/*/scripts/*.py` (5), `.agents/skills/*/references/*.md` (2), `.agents/skills/*/resources/templates/**` (all), `.agents/scripts/*.py` (4), `.agents/rules/*.md` (6), `.agents/hooks.json`, `AGENTS.md`, `README.md`, `.agents/skills/README.md`, `pyproject.toml`, `scripts/*.py` (3), root `spec-templates/` + `task-templates/` (hash-compared), `prd_generator/cli.py`, `prd_generator/validation/prd_linter.py`, `prd_generator/synthesis/modular_synthesizer.py`, `prd_generator/clarification/clarifier.py` (spot), `spec_generator/cli.py`, `spec_generator/validation/spec_linter.py`, `spec_generator/synthesis/tech_spec_synthesizer.py` (spot), plus official docs in `_sources/`.

*End of report.*


