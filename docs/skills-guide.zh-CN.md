# 技能使用指南（v2 基础 + v3 增量）：从想法到交付验收

> 适用对象：使用 `.agents/skills/` 的开发者、Planner、Dev、QA 与 Reviewer Agent。  
> 对应版本：技能 `metadata.version` 2.x（基础流程）与 3.x（brownfield/收敛/分发）；设计契约见 [`skills-v2-spec.md`](skills-v2-spec.md)，v3 用法见 [`brownfield-convergence.zh-CN.md`](brownfield-convergence.zh-CN.md)。  
> 本文说明九个技能（规划五个 + 审查一个 + 执行两个 + 收敛一个）**如何工作、如何使用**，以及**为什么已经不再依赖 `prd_generator` / `spec_generator` 源码**。

---

## 1. 一句话结论

**技能本身是"提示词 + 模板 + 纯标准库小工具"的自包含包；确定性引擎 `prd_generator` / `spec_generator` 已降级为可选加速器，不再是运行前提。**

具体来说：

- 技能不再通过 `run.py`、`parents[4]`、`sys.path.insert` 去 import 仓库根目录的引擎包；
- PRD、技术规格、任务契约的模板全部随技能放在 `assets/templates/`；
- 脚手架、结构校验、任务门禁都是 **Python 标准库** 脚本，路径从脚本自身位置解析；
- 没有 Python、没有引擎、没有网络时，仍可按 SKILL.md 的**手工降级路径**完成交付；
- 引擎只在需要"确定性生成/回放"时可选安装，缺失时 `engine.py` 以退出码 `2` 给出安装指引，不阻塞流程。

已通过"把技能目录复制到仓库外再运行"的迁移测试：技能仍可 `scaffold` / `lint` / `--help`，不会出现 `ModuleNotFoundError`。

---

## 2. 目录与职责

```text
.agents/skills/
├── prd-generator/          # 想法 → PRD 套件
│   ├── SKILL.md
│   ├── assets/templates/   # 01-prd.md + 01-prd/ 的模板
│   ├── references/         # 4 角色研讨协议、PRD 格式、中文参考
│   └── scripts/            # scaffold.py / lint_prd.py / engine.py(可选)
├── spec-generator/         # PRD → ADR + 技术规格
│   ├── SKILL.md
│   ├── assets/templates/   # adr + 02-tech-spec + 02-tech-spec/
│   ├── references/         # 架构评审协议、规格格式、团队约定、中文参考
│   └── scripts/            # scaffold.py / lint_spec.py / engine.py(可选)
├── task-decomposition/     # 规格 → 任务包（4 文档）
│   ├── SKILL.md
│   ├── assets/templates/   # 01-contract / 02-dev-workspace / 03-qa-verification / 04-process
│   ├── references/         # 黄金切片、反幻觉、门禁细则
│   └── scripts/scaffold_task.py
├── change/                 # brownfield：增量 proposal + 单个任务包 + 归档
│   ├── SKILL.md
│   ├── assets/templates/proposal.template.md
│   ├── references/brownfield-protocol.md
│   └── scripts/            # scaffold_change.py / standards_extract.py / lint_change.py
├── plan-linter/            # Gate 1 确定性静态门禁
│   ├── SKILL.md
│   ├── references/gate-2-review.md  # 未安装 review 时的自包含备用清单
│   └── scripts/plan_linter.py
├── review/                 # Gate 2 语义审查 / 变更审查
│   ├── SKILL.md
│   └── references/{plan-review,code-review}.md
├── dev/                    # 执行：按契约实现、自测、填 02、交接
│   ├── SKILL.md
│   └── references/dev-protocol.md
├── qa/                     # 执行：独立黑盒验收、证据、签署/退回
│   ├── SKILL.md
│   └── references/qa-protocol.md
└── converge/               # 收敛：QA_PASSED 后写回规格、归档任务包与 change
    ├── SKILL.md
    ├── references/convergence-protocol.md
    └── scripts/converge.py
```

每个技能只做一件事：

| 技能 | 输入 | 输出 | 由谁判断 |
| :--- | :--- | :--- | :--- |
| `prd-generator` | 模糊创意、笔记、旧 PRD | `.specs/01-prd.md` + `.specs/01-prd/` | Agent（澄清、4 角色评审、收敛） |
| `spec-generator` | PRD | `.specs/adr/*.md` + `.specs/02-tech-spec.md` + `.specs/02-tech-spec/` | Agent（架构权衡、ADR） |
| `task-decomposition` | PRD + ADR + Tech Spec | `tasks/<task-id>/` 四份文档 | Agent（垂直切片、追溯、DoD） |
| `change` | 现有规格 + 一个有界变更 | `.specs/changes/<id>/proposal.md` + 1 个任务包 + standards 报告 | Agent（增量提案、隐式约束、升级判断） |
| `plan-linter` | `tasks/` | Gate 1 报告 | 脚本（结构） |
| `review` | 计划/任务包，或 diff + 证据 | 发现清单 + PASS/REQUEST CHANGES/BLOCKED | Agent（只读语义审查） |
| `dev` | `01-contract.md` + 项目命令 | 代码变更、填好的 `02`、`WAITING_FOR_QA` | Agent（实现与自测） |
| `qa` | `01`、填好的 `02`、测试命令 | `tests/acceptance/**`、填好的 `03`、唯一裁决 | Agent（独立验证） |
| `converge` | `01`、带偏差表的 `02`、勾选 `QA_PASSED` 的 `03` | 写回 `.specs/02-tech-spec.md`、`CONVERGED` 状态、归档任务包 | 脚本 + Agent（append-only 写回） |

前五个技能负责"规划与门禁"（`change` 是 brownfield 入口，复用 `task-decomposition` 的模板），`dev` / `qa` 负责"执行与验收"，`converge` 负责"实现结果回写规格"。

---

## 3. 工作模型：判断 vs 确定性

改造后的分层非常明确：

| 层 | 负责什么 | 载体 |
| :--- | :--- | :--- |
| **Skill** | 业务理解、角色博弈、权衡、写作 | `SKILL.md` + `references/` |
| **Template** | 机器可解析的格式契约 | `assets/templates/` |
| **Script** | 脚手架、占位符/锚点/DAG/结构校验 | `scripts/*.py`（仅标准库） |
| **CI** | 真正强制的 RBAC 与质量门禁 | `tools/rbac_audit.py` + 分支保护 |

- **Gate 1** 是确定性脚本，检查结构；**Gate 2** 是只读 Reviewer 的语义审查，不做自动化承诺。
- `.agents/hooks.json` 只是 Antigravity 的**可选本地适配器**（L1），DSH/Claude Code 不加载它；**权威强制层是 CI**（`tools/rbac_audit.py`）。

---

## 4. 快速开始（不安装引擎）

以下命令都在目标仓库根目录执行。首次使用建议先复制模板、再填写、最后校验。

### 4.1 生成并填写 PRD

```bash
# 1) 复制 PRD 模板到 .specs/（默认输出目录就是 .specs）
python .agents/skills/prd-generator/scripts/scaffold.py --out .specs

# 2) Agent 按 SKILL.md 与 references/prd-format.md 填写：
#    .specs/01-prd.md
#    .specs/01-prd/00-overview.md ... 04-forks.md

# 3) 结构校验（会拦截未替换的 {{...}}、[TBD]、缺失 #sec-* 等）
python .agents/skills/prd-generator/scripts/lint_prd.py .specs/01-prd.md
# 或校验整个目录
python .agents/skills/prd-generator/scripts/lint_prd.py .specs
```

> 刚 scaffold 完直接 lint 会失败，这是预期行为：模板里的 `{{UPPER_SNAKE}}` 必须由 Agent 替换。

### 4.2 生成并填写技术规格

```bash
# 1) 复制 ADR / Tech Spec 模板
python .agents/skills/spec-generator/scripts/scaffold.py --out .specs

# 2) 填写 .specs/adr/*.md、.specs/02-tech-spec.md 与 .specs/02-tech-spec/

# 3) 结构校验
python .agents/skills/spec-generator/scripts/lint_spec.py .specs
```

模板是中立的：不再默认 PostgreSQL/Redis/Kafka/Envoy、`tenant_id` 或 TypeScript 专属假设；技术栈必须来自当前 PRD 与 ADR。

### 4.3 拆任务并填契约

```bash
# 为每个任务生成一个目录和四份文档
python .agents/skills/task-decomposition/scripts/scaffold_task.py \
  --tasks-dir tasks \
  --task-id task-001-auth \
  --title "用户认证"

# 只填写 01-contract.md；02/03 保持空白表单；04 已初始化，不要手改
```

- `--task-id` 会同时作为目录名和契约的 `task_id`，两者必须一致；
- `02-dev-workspace.md` / `03-qa-verification.md` 是**无占位符的空白角色表单**，由 Dev/QA 后续填写；
- `04-process.md` 是派生文件，模板已初始化为 `macro_status: TODO`、`micro_phase: UNASSIGNED`、`current_lock_holder: None`、`retry_count: 0`，事件表只有表头；由可选事件工具或 CI 维护；
- 脚手架结束时会打印 `remaining placeholders to fill`：**只有 01 的占位符需要 Planner 填完**；02/03 没有 token，04 不需要手工填。

### 4.4 运行 Gate 1

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks
# 机器可读
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --json
```

只有 `01-contract.md`、`02-dev-workspace.md`、`03-qa-verification.md` 会被占位符扫描，`04-process.md` 不扫描。

### 4.5 Gate 2（语义审查）

Gate 1 通过后，由**只读 Reviewer Agent** 使用 `review` 技能的 **plan-review 模式**执行
（[`review/SKILL.md`](../.agents/skills/review/SKILL.md)）：

1. 正向覆盖率：PRD/规格中的接口与需求是否都有任务承接；
2. 反向反幻觉：任务是否脑补了上游不存在的实体；
3. ADR 红线：实现是否违背架构决策。

若未安装 review 技能，可用 `plan-linter/references/gate-2-review.md` 作为自包含的备用清单。
Gate 2 的结论必须由 Reviewer 输出，不能写成"脚本已自动验证"。

### 4.6 开发与验收（dev / qa）

Gate 2 通过后，任务进入执行阶段：

- **Dev**：按 `.agents/skills/dev/SKILL.md` 实现 `01-contract.md` 定义的切片；只改 `touch_files`，跑 `dod`，填 `02-dev-workspace.md`，全部通过后勾选 `WAITING_FOR_QA`。
- **QA**：按 `.agents/skills/qa/SKILL.md` 独立设计黑盒测试，写 `tests/acceptance/**`，填 `03-qa-verification.md`，二选一勾选 `QA_PASSED` 或 `REWORK_REQUIRED`。
- 返工循环：QA 退回 → Dev 在契约内修复并重新交接 → QA 更新尝试轮次后重验。

---

### 4.7 brownfield 增量（change）

不用重写 PRD，直接对现有规格做有界变更：

```bash
python .agents/skills/change/scripts/standards_extract.py --repo-root .
python .agents/skills/change/scripts/scaffold_change.py --change-id CHG-001-rate-limit \
  --title "Rate limit login attempts" --anchor "#sec-auth-tokens" \
  --size-class micro --estimated-lines 40 \
  --touch-files "modify:src/auth/rate_limit.py" --repo-root .
```

之后走同样的 Gate 1 / Gate 2 / dev / qa；QA 通过后由 `converge` 写回。完整流程、proposal 格式与 micro/standard 预算见 [brownfield-convergence.zh-CN.md](brownfield-convergence.zh-CN.md)。

### 4.8 收敛（converge）

```bash
# 1) 分类：哪些任务包可以收敛
python .agents/skills/converge/scripts/converge.py check --tasks-dir ./tasks --json
# 2) 先预览，再执行（幂等；只追加，不改写历史）
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-rate-limit --dry-run
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-rate-limit
```

`apply` 会把 `02` 的 Implementation deviations 表追加进 `.specs/02-tech-spec.md` 的 Converged changes 章节，把 `04` 置为 `CONVERGED`，并把任务包移动到 `tasks/archive/`。

---

## 5. 各技能详解

### 5.1 `prd-generator`

- **何时用**：用户要 PRD、功能范围、MVP 边界、需求修订；还处于"想清楚要做什么"的阶段。
- **何时不用**：要做架构决策/ADR/工程规格（→ `spec-generator`）；只是实现或改代码。
- **流程**：澄清 → 4 角色评审（宿主支持 SubAgent 就独立评审，否则同一上下文内显式模拟）→ 收敛 → 可选 scaffold → 填写 → 可选 lint → 交给 spec-generator。
- **输出**：`.specs/01-prd.md`（权威聚合版）+ `.specs/01-prd/`（模块化副本）。
- **脚本**：
  - `scaffold.py --out .specs [--dry-run] [--force] [--json]`
  - `lint_prd.py [文件或目录] [--json]`
  - `engine.py ...`（可选，未安装时 exit 2）
- **Lint 拦截**：未替换占位符、缺失/非法 `#sec-*`、必需的 REQ/CON/NFR/FORK 结构、无效内部链接；重复锚点给 warning。

### 5.2 `spec-generator`

- **何时用**：已有 PRD，需要 ADR、拓扑、接口/数据契约、技术规格。
- **何时不用**：需求还在发散（→ `prd-generator`）；已进入实现。
- **流程**：摄入 PRD → 4 角色架构评审 → 对每个 `FORK-*` 形成 ADR → 设计拓扑/数据/接口/不变量 → 可选 scaffold → 填写 → 可选 lint → 交给 task-decomposition。
- **输出**：`.specs/adr/*.md`、`.specs/02-tech-spec.md`、`.specs/02-tech-spec/`。
- **脚本**：`scaffold.py`、`lint_spec.py`、`engine.py`（可选）。
- **Lint 拦截**：占位符、缺失锚点、Mermaid 围栏/括号不平衡、ADR 必需章节、失效链接；重复锚点 warning。

### 5.3 `task-decomposition`

- **何时用**：规格已经评审通过，需要切成可独立开发、可独立验收的任务。
- **何时不用**：规格还在设计；改动小到单文件；只是审查已有任务（→ `plan-linter`）。
- **流程**：建立追溯矩阵 → 规划垂直切片与 DAG → 用 `scaffold_task.py` 生成四文档 → 填 01 → Gate 1 → Gate 2。
- **黄金切片默认值**：1–3 个 touch files、50–250 行预估变更；阈值可在 linter config 覆盖。
- **契约 frontmatter（01 的权威部分）**：

```yaml
---
task_id: task-001-auth          # 必须等于目录名
title: "User authentication"
module: auth
dependencies: []                # 或 [task-000-bootstrap]
estimated_lines: 120
touch_files:
  - action: create              # create | modify
    path: src/auth/service.py
  - action: modify
    path: src/auth/routes.py
origin_spec_anchor: "#sec-auth" # 必填，#sec-[a-z0-9-]+
adherence_adrs: [ADR-001]       # 至少一个
dod:
  type_check: "npm run type-check"
  lint: "npm run lint"
  test_file: "tests/acceptance/test_auth.ts"
  edge_cases:
    - "空凭据返回 400"
    - "过期 token 返回 401"
---
```

- 01 必须没有未替换占位符；02/03 是空白角色表单；04 初始化为 `TODO/UNASSIGNED/None/0`，不手写、由工具/CI 更新。

### 5.4 `plan-linter`（Gate 1）

- **Gate 1 检查项**：
  1. `touch_files` 数量（默认 ≤3）与禁止前缀（默认 `tests/acceptance/`）；
  2. `estimated_lines` 区间（默认 50–250）；
  3. `origin_spec_anchor` 必须是合法 `#sec-*`；
  4. `adherence_adrs` 非空；
  5. `dod.type_check` / `lint` / `test_file` 齐全且无占位符；
  6. `edge_cases` 至少 2 个；
  7. 02/03/04 文档存在；
  8. `task_id` 与目录名一致、无重复 ID；
  9. 依赖图无环、无悬空依赖；
  10. 01/02/03 无占位符（04 除外）；
11. `size_class: micro` 的预算与 `change_id`（v3）；
12. change proposal 处于 `proposed`/`applied`（传 `--changes-dir` 时）。
- **CLI**：
  ```bash
  python .agents/skills/plan-linter/scripts/plan_linter.py \
    --tasks-dir ./tasks [--config plan-linter.json] [--json] [--legacy] [--no-placeholder-scan] \
    [--repo-root .] [--spec .specs/02-tech-spec.md] [--changes-dir .specs/changes] \
    [--coverage-out artifacts/coverage.json] [--strict-topology] [--strict-anchor] \
    [--require-full-coverage]
  ```
- **Gate 2 启发式（v3）**：`--spec` 输出锚点覆盖率矩阵（JSON `coverage`），`--repo-root` 做真实路径拓扑检查（`modify` 必须存在、`create` 不能已存在），`--changes-dir` 校验 proposal 是否存在且未关闭。它们只提供线索，Gate 2 结论仍由只读 Reviewer 给出。
- **退出码**：`0` 通过；`1` 违规；`2` 用法/配置错误；`3` 未预期错误。
- **JSON 形状**：`{"gate":"1","passed":bool,"tasks_scanned":n,"errors":[{task,code,message,file,line}],"warnings":[...]}`。
- 旧的中文表格契约可通过 `--legacy` 或自动回退解析，但会输出 `LEGACY_FORMAT` warning；新任务应使用 frontmatter。

### 5.5 `review`

- **何时用**：Gate 1 已通过、需要 Gate 2 语义审查；或 Dev 提交变更后需要代码/变更审查。
- **何时不用**：你本人是作者；Gate 1 未通过；需要实现或 QA 验证；被要求改代码来让它通过。
- **两种模式**：plan review（PRD/ADR/规格 ↔ 任务契约）与 code review（契约 ↔ diff/测试证据）。
- **流程**：确认独立性 → 选模式 → 先读上游 → 按清单审查 → 分级（blocker/major/minor/nit）→ 给出唯一裁决。
- **输出**：带文件/行号证据的发现清单；`PASS` / `REQUEST CHANGES` / `BLOCKED`；**不修改任何产物**。
- **细节**：[`review/references/plan-review.md`](../.agents/skills/review/references/plan-review.md)、
  [`review/references/code-review.md`](../.agents/skills/review/references/code-review.md)。

### 5.6 `dev`

- **何时用**：`01-contract.md` 已完成、你被指派为 Dev，需要实现并交接。
- **何时不用**：契约缺失/有争议；你被要求规划或验收；所需改动超出 `touch_files`。
- **流程**：读契约 → 确认爆炸半径 → 只改白名单文件 → 跑类型检查/Lint/已有测试 → 填 `02` → 全部通过后勾 `WAITING_FOR_QA`（验收测试由 QA 运行）。
- **输出**：代码变更；`02-dev-workspace.md`；唯一交接标记；不改 `01/03/04` 与 `tests/acceptance/`。
- **细节**：[`dev/references/dev-protocol.md`](../.agents/skills/dev/references/dev-protocol.md)。

### 5.7 `qa`

- **何时用**：`02` 中 `- [x] WAITING_FOR_QA` 已勾选，需要独立验收。
- **何时不用**：尚未交接；被要求实现/规划；契约或上游规格缺失。
- **流程**：验证交接 → 设计黑盒矩阵（正常/边界/回放/安全）→ 只写 `tests/acceptance/**` → 执行并记录证据 → 审计爆炸半径 → 二选一裁决。
- **输出**：验收测试；`03-qa-verification.md`；`QA_PASSED` 或 `REWORK_REQUIRED`；不改源码 `01/02/04`。
- **细节**：[`qa/references/qa-protocol.md`](../.agents/skills/qa/references/qa-protocol.md)。

### 5.8 `change`

- **何时用**：已有规格/代码库要做有界增量（bugfix、小功能、行为调整），不值得重写 PRD。
- **何时不用**：greenfield（→ `prd-generator`）；需要新章节/新组件/新 ADR（→ `spec-generator`）；只是切片任务（→ `task-decomposition`）。
- **流程**：standards 提取 → proposal + 1 个任务包 → Planner 填字段 → Gate 1/Gate 2 → dev/qa → converge 归档。
- **输出**：`.specs/changes/<id>/proposal.md`、`tasks/<id>/` 四文档、`.specs/change-context/standards.md`。
- **细节**：[`change/SKILL.md`](../.agents/skills/change/SKILL.md)、[`brownfield-protocol.md`](../.agents/skills/change/references/brownfield-protocol.md)、[v3 使用说明](brownfield-convergence.zh-CN.md)。

### 5.9 `converge`

- **何时用**：`03` 已勾选 `QA_PASSED`，且 `02` 的偏差表已写好（无偏差写一行 `None`）。
- **何时不用**：实现/验收仍在进行；偏差表为空（打回 Dev，而不是猜）；需要发明规格内容（那是重新规划）。
- **流程**：`check` 分类 → `apply --dry-run` → `apply` → 复跑 `check` 与 `--spec-sha256` 验证。
- **输出**：规格末尾的 Converged changes 记录 + marker；`04` 的 `CONVERGED`；`tasks/archive/<task-id>/`；proposal `archived`。
- **细节**：[`converge/SKILL.md`](../.agents/skills/converge/SKILL.md)、[v3 使用说明](brownfield-convergence.zh-CN.md)。

---

## 6. 四文档与角色边界

`tasks/<task-id>/`：

| 文档 | 归属 | 规则 |
| :--- | :--- | :--- |
| `01-contract.md` | Planner | 权威 frontmatter + 人类可读契约；对 Dev/QA 只读 |
| `02-dev-workspace.md` | Dev | 实施记录、实际变更、自测；全部通过后勾选 `- [x] WAITING_FOR_QA` 交接 |
| `03-qa-verification.md` | QA | 独立黑盒用例、执行证据、爆炸半径审计；二选一勾选 `QA_PASSED` 或 `REWORK_REQUIRED` |
| `04-process.md` | 工具/CI | 派生状态与审计；初始 `TODO/UNASSIGNED/None/0`，Agent 不手写 |

> v3 起 `02` 末尾有 `Implementation deviations` 表（`DEV-001 / #sec-* / add|modify|remove / 确认行为`）。无偏差时写一行 `None`，供 `converge` 写回规格使用；Dev 仍不直接编辑规格。

### 6.1 DevAgent 如何工作

1. **读契约**：读 `01-contract.md` 的 frontmatter（权威）、继承的 ADR 与对应 `#sec-*` 规格；不改 01。
2. **在爆炸半径内实现**：只创建/修改 `touch_files` 列出的路径；需要越界时停下来升级/拆任务。
3. **跑 DoD**：执行 `dod.type_check`、`dod.lint` 与项目已有测试，逐条考虑 `dod.edge_cases`；`dod.test_file` 是 QA 所有，若尚未创建则在 02 中注明交给 QA，Dev 只运行、不创建/不改 `tests/acceptance/`。
4. **填写 02**：记录分支/提交、实现说明、逐文件实际变更与行数、自测勾选。
5. **只在全部通过后交接**：把 `- [ ] WAITING_FOR_QA` 改成 `- [x] WAITING_FOR_QA`；这是唯一交接触发信号。
6. **不动 03/04**：03 归 QA，04 由工具派生。

### 6.2 QAAgent 如何工作

1. **读契约与交接**：读 01 的 DoD/ADR 和 02 的交接声明；黑盒设计用例，尽量不先读实现。
2. **写验收测试**：只允许写 `tests/acceptance/**` 与 `03-qa-verification.md`。
3. **执行并记录**：填测试矩阵（正常/边界/重复回放/安全）、执行命令、通过/失败数、覆盖率与失败 trace。
4. **审计**：确认实际变更都在 `touch_files` 内、Dev 没改测试或 01、实现遵守 `adherence_adrs`。
5. **给出唯一裁决**：全部通过才勾 `- [x] QA_PASSED`；否则勾 `- [x] REWORK_REQUIRED` 并附完整失败痕迹与修复期望。
6. **不动源码/01/02/04**：缺陷退回 Dev 修，QA 只更新 03 的下一轮尝试与证据。

### 6.3 `04-process.md` 初始记录与事件映射

初始文件由模板生成，只包含状态卡和空事件表：

```yaml
task_id: "task-001-auth"
macro_status: "TODO"
micro_phase: "UNASSIGNED"
current_lock_holder: "None"
retry_count: 0
last_heartbeat: ""
```

- **不写初始化事件、不写示例行、不写假时间戳**；第一条真实事件出现在角色勾选生命周期框后；
- 只有真正勾选的 `- [x]` 行才触发，事件按任务+事件码幂等追加；
- 映射：

| 勾选标记 | 事件码 | macro_status | current_lock_holder | retry |
| :--- | :--- | :--- | :--- | :--- |
| `- [x] WAITING_FOR_QA`（02） | `HANDOFF_QA_REQUESTED` | `VERIFYING` | `QAAgent` | 不变 |
| `- [x] QA_PASSED`（03） | `TASK_TERMINATED_DONE` | `DONE` | `None` | 不变 |
| `- [x] REWORK_REQUIRED`（03） | `REWORK_TRIGGERED` | `REWORKING` | `DevAgent` | +1（有上限） |

- 没有事件工具时，保持 04 初始化状态，以 git/CI 为权威；**不要手写事件**。
- 细节见 [`.agents/skills/task-decomposition/references/role-lifecycle.md`](../.agents/skills/task-decomposition/references/role-lifecycle.md)。

补充角色规则：[`.agents/rules/reviewer.md`](../.agents/rules/reviewer.md)（Gate 2 只读审查）与
[`.agents/rules/orchestrator.md`](../.agents/rules/orchestrator.md)（编排、门禁顺序与单一 owner）。规则总览见
[`agent-rules.md`](agent-rules.md)。

---

## 7. 可选引擎：保留，但不再被依赖

仓库里仍然保留 `prd_generator/` 与 `spec_generator/`，它们只是**可选的确定性生成器**：

```bash
# 可选安装（会注册 prd-generator / spec-generator 命令）
uv tool install --editable .
# 或
pip install agent-spec-suite
```

安装后可以用：

```bash
prd-generator run --idea "你的构想" --output-dir .specs --mode deterministic
spec-generator run --prd .specs/01-prd.md --output-dir .specs --mode deterministic
```

也可以通过技能内的 `engine.py` 代理调用：

```bash
python .agents/skills/prd-generator/scripts/engine.py run --idea "..." --output-dir .specs
```

- 未安装时：`engine.py` **exit 2**，打印"继续 prompt-only / 如何安装"的指引；技能流程不受影响；
- 不安装、甚至删除这两个引擎目录，`scaffold` / `lint` / `plan_linter` 仍然可用；
- 引擎的 `--mode deterministic` 适合快速骨架与回归基线；真实业务判断仍应按 SKILL.md 由 Agent 完成。

> 注意：`engine.py` 不做 `sys.path` 注入，所以即使引擎源码就在仓库里，没有安装时它也检测不到——这是有意的隔离。

---

## 8. 安装到不同宿主

| 宿主 | 原生发现路径 | 说明 |
| :--- | :--- | :--- |
| Codex | `.agents/skills/<name>/` | 从当前目录向上到仓库根、以及 `~/.agents/skills` |
| Antigravity | `.agents/skills/<name>/` | 全局为 `~/.gemini/config/skills/` |
| DeepSeek Harness | `.agents/skills/<name>/` | 直接加载工作区技能 |
| Claude Code | `.claude/skills/<name>/` | 用安装工具链接或复制 |

```bash
# 预览
python tools/install_skills.py --dry-run

# 装到 Claude Code（Windows 无符号链接权限时用 --copy）
python tools/install_skills.py --dest .claude/skills --copy

# 只装指定技能
python tools/install_skills.py --dest ~/.agents/skills --skills prd-generator,task-decomposition,plan-linter

# 整仓采用到另一个仓库：技能 + 规则 + 审计脚本 + CI 工作流
python tools/quickstart.py --target ../another-repo --copy --with-ci
```

更完整的矩阵与降级说明见 [`skills-compatibility.md`](skills-compatibility.md)。

---

## 9. 强制与安全（诚实模型）

| 层 | 机制 | 适用 | 保证 |
| :--- | :--- | :--- | :--- |
| L0 | `AGENTS.md` / 角色规则 / SKILL.md | 所有宿主 | 提示性 |
| L1 | `.agents/hooks.json`（Antigravity） | 仅 Antigravity | 尽力而为，可绕过 |
| L2 | `tools/rbac_audit.py` + CI | 所有 git 仓库 | 对已提交变更强约束 |
| L3 | 分支保护 / CODEOWNERS | 仓库设置 | 强约束 |

```bash
# CI 示例：检查 base 之后的提交里，dev 是否碰了验收测试
python tools/rbac_audit.py --base origin/main --role dev

# 角色也可以来自 commit trailer：Agent-Role: dev
python tools/rbac_audit.py --base HEAD~1 --json
```

- `04-process.md` 是派生文件；不要把它当作手工台账；
- 可选事件工具（`.agents/scripts/event_bus_logger.py`）只识别真正勾选的 `- [x]`，不会再把模板里的说明文字当成事件。

---

## 10. 故障排查

| 现象 | 原因 / 处理 |
| :--- | :--- |
| `lint_prd.py` / `lint_spec.py` 刚 scaffold 就失败 | 预期：模板占位符还没替换。填完后重跑 |
| `engine.py` 退出 2 | 可选引擎未安装。继续 prompt-only，或按提示安装 |
| Gate 1 报缺 02/03/04 | 用 `scaffold_task.py` 生成完整四文档，或补齐文件 |
| Gate 1 报 `task_id` 与目录不一致 | 把契约 frontmatter 的 `task_id` 改成目录名 |
| 事件总线不写 `04` | 04 是派生文件；优先用工具/CI，不要手改 |
| hooks 在 DSH/Claude 下不生效 | 预期：hooks 是 Antigravity 适配器；用 CI 的 `rbac_audit.py` |
| Windows 下安装技能失败 | 加 `--copy` 避免符号链接权限问题 |
| `converge` 拒绝执行（exit 1） | 检查 `03` 是否勾选 `QA_PASSED`、`02` 偏差表是否有 DEV 行或 `None` 行、归档目录是否已存在（需 `--force`） |
| `scaffold_change.py` 拒绝锚点 | 锚点必须已存在于基座规格；需要新章节请走 `spec-generator` |
| Gate 1 报 `CHANGE_PROPOSAL_MISSING` / `CHANGE_NOT_OPEN` | 提案不存在或已关闭；用 `change` 重新生成，或先归档/新开一个提案 |
| `standards_extract.py --check` 退出 1 | 报告已过期；重新生成 `.specs/change-context/standards.md` |
| Gate 1 把 `tasks/archive/` 当任务包 | 升级到 plan-linter 3.x；默认 `ignore_task_dirs: ["archive"]` 会跳过归档目录 |

所有脚本统一退出码：`0` 成功、`1` 内容/门禁失败、`2` 可选依赖或用法不可用、`3` 未预期错误。先跑 `--help`，把脚本当黑盒使用。

---

## 11. 验证你的改动

```bash
# 技能与门禁测试
python -m unittest discover -s tests/unit -p "test_*.py"

# 引擎 E2E（可选）
python -m unittest discover -s tests/e2e -p "test_*.py"

# 目录迁移自检：把技能拷到仓库外，确认仍可 --help / scaffold / lint
```

当前基线：`539` 个单元测试（1 skip）、`109` 个 E2E 全部通过；新增专项：change 32、converge 27、distribution 28、plan-linter v3 26。

---

## 12. 相关文档

- [技能索引（英文）](../.agents/skills/README.md)
- [v3：brownfield 增量与规格收敛](brownfield-convergence.zh-CN.md)
- [v2 设计契约（含 v3 增补）](skills-v2-spec.md)
- [宿主兼容与安装](skills-compatibility.md)
- [角色规则与强制模型](agent-rules.md)
- [审计归档](audit/README.md)

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
