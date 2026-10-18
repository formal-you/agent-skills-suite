# Brownfield 增量与规格收敛（v3）

> 适用对象：已有规格/代码库需要持续演进的团队与 Agent（Planner / Dev / QA / Reviewer / Orchestrator）。  
> 对应版本：change 3.0.0、converge 1.0.0、plan-linter 3.0.0。  
> 前置阅读：[技能使用指南（v2 基础流程）](skills-guide.zh-CN.md)、[v2 设计契约（含 v3 增补）](skills-v2-spec.md)。  
> 本文回答两个问题：**不改写 PRD 怎么接需求**（brownfield），以及**实现完怎么让规格保持真实**（收敛）。

---

## 1. 为什么需要 v3

v2 解决了"从零到交付"：想法 → PRD → 规格 → 任务 → Gate 1/2 → Dev → QA。但真实项目里大部分工作**不是新项目**，而是：

- 修一个 bug、加一个小功能、调一个行为、收一个 NFR；
- 已有 `.specs/02-tech-spec.md` 和代码，但规格与代码开始脱节；
- 为一个改动重写 PRD 成本过高，直接改代码又失去可追溯性与独立性保证。

对标 OpenSpec / Spec Kit 的 proposal → apply → archive 与 implement → converge，v3 补上四块：

| 缺口 | v3 方案 | 技能 |
| :--- | :--- | :--- |
| brownfield 没有轻量入口 | 增量提案（delta）+ 单个任务包 + 归档 | change |
| 规格是一次性交付物 | QA 通过后把确认的实现偏差 append-only 写回规格 | converge |
| Gate 2 完全靠人读 | 锚点覆盖率矩阵、真实路径拓扑、change proposal 一致性 | plan-linter 3.x |
| 只能手工拷贝采用 | 一条命令分发 + 可直接抄的 CI 工作流 | tools/quickstart.py、templates/ci/ |

设计原则与 v2 一致：**提示词负责判断，脚本只做确定性的事，CI 才是强制层。**

---

## 2. brownfield：change 技能

### 2.1 什么算一次 change

适合：

- 复用现有 `#sec-*` 锚点的 bugfix、小功能、行为调整、有界 NFR 收紧；
- 能在 micro（默认 1 文件 / 10–49 行）或 standard（1–3 文件 / 50–250 行）预算内完成。

不适合（要升级流程）：

- 需要**新章节/新锚点**、新组件边界、新 ADR 级决策、跨切面新不变量 → 回 spec-generator；
- 还没有任何规格（greenfield）→ prd-generator → spec-generator → task-decomposition；
- 只是把已批准规格切成任务 → task-decomposition；
- 只审查已有提案/任务包 → plan-linter / review。

硬规则：**一次 change = 一份 proposal + 恰好一个四文档任务包**。需要一个以上任务包时，说明它不是有界变更，应走规格流程。

### 2.2 产物与布局

```text
.specs/
├── 02-tech-spec.md                     # 基座规格（change 的输入，不在这里改写）
├── change-context/
│   └── standards.md                    # 工具生成：仓库约定与隐式约束（不要手改）
└── changes/
    └── CHG-001-rate-limit/
        ├── proposal.md                 # delta：motivation / [CHG-1] hunks / 回滚 / 验证
        └── convergence.md              # QA 通过后由 converge 写入
tasks/
└── CHG-001-rate-limit/                 # 任务包目录名 = change id
    ├── 01-contract.md                  # frontmatter 带 change_id / size_class
    ├── 02-dev-workspace.md
    ├── 03-qa-verification.md
    └── 04-process.md
```

proposal **不是 PRD，也不是规格的替代品**：它只描述相对现有规格的增量，并点名它触碰的现有锚点。

### 2.3 流程（6 步）

```text
standards_extract.py            ① 提取仓库约定（隐式约束）
        │
scaffold_change.py              ② 生成 proposal + 1 个任务包
        │
Planner 填写                     ③ proposal 的 hunk + 契约剩余字段
        │
plan-linter（Gate 1）→ review（Gate 2）   ④ 结构门禁 + 语义审查
        │
dev → qa                        ⑤ 只在 touch_files 内实现；独立验收出唯一裁决
        │
converge                        ⑥ 写回规格、04 置 CONVERGED、归档任务包与 proposal
```

### 2.4 命令

```bash
# ① 提取仓库约定（生成 .specs/change-context/standards.md）
python .agents/skills/change/scripts/standards_extract.py --repo-root . --json
python .agents/skills/change/scripts/standards_extract.py --repo-root . --check   # 报告过期则 exit 1

# ② 生成 proposal + 单个任务包（先 --dry-run 看计划）
python .agents/skills/change/scripts/scaffold_change.py \
  --change-id CHG-001-rate-limit \
  --title "Rate limit login attempts" \
  --anchor "#sec-auth-tokens" \
  --kind modify \
  --size-class micro \
  --estimated-lines 40 \
  --touch-files "modify:src/auth/rate_limit.py" \
  --repo-root .

# ④ Gate 1（同时校验提案是否处于 proposed/applied）+ 提案一致性
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
python .agents/skills/change/scripts/lint_change.py --change-id CHG-001-rate-limit --repo-root .
```

scaffold_change.py 会拒绝不存在的锚点、缺失的基座规格和越界路径，计算 base_spec_sha256，并把任务包生成委托给 task-decomposition 的 scaffold_task.py --change-id ... --size-class ...；同目录兄弟技能不存在时退化为内置的最小四文档包并明确告警。

lint_change.py 检查：frontmatter 完整性、锚点是否存在于基座规格、base_spec_sha256 是否漂移、[CHG-n] 块是否合法、任务包的 change_id 是否与提案一致。

### 2.5 预算：micro 与 standard

| 级别 | size_class | 默认预算 | 额外约束 | 用途 |
| :--- | :--- | :--- | :--- | :--- |
| 微变更 | micro | 10–49 行 | 必须带 change_id，最多 1 个 touch file | 单文件 bugfix、文案/行为微调 |
| 常规变更 | standard | 50–250 行 | 1–3 个 touch file | 跨 1–3 文件的小功能、接口调整 |

阈值都在 plan-linter 的 config 里（min_diff_lines / max_diff_lines / micro_min_diff_lines / micro_max_touch_files）。micro **不是**绕过门禁：它仍然要求锚点、ADR、DoD、边界用例，以及独立的 QA。它只降低了"值得为它写一份完整规格吗"的摩擦。

### 2.6 proposal 格式

frontmatter（权威）：

| 字段 | 含义 |
| :--- | :--- |
| change_id | 提案 id，同时是 tasks/<id>/ 目录名 |
| title | 一句话说明 |
| status | proposed → applied → archived，由流程推进 |
| kind | add / modify / remove |
| base_spec | 基座规格路径 |
| base_spec_sha256 | 生成时的规格指纹，用于漂移检测 |
| impact_anchors | 受影响的现有 #sec-* 锚点 |
| created | 创建日期（YYYY-MM-DD） |

正文按 [CHG-1]、[CHG-2] 分块描述增量；每个块必须点名一个**真实存在**的锚点，并写清 before/after 与回滚方式。禁止在这里重新定义整个系统。

### 2.7 standards 报告 = 隐式约束

standards_extract.py 只报告**仓库里已有证据**的约定，不猜：

| 报告内容 | 来自 |
| :--- | :--- |
| 语言/运行时版本 | pyproject.toml 的 requires-python、package.json 的 engines |
| Lint / 类型检查 / 测试命令 | 已声明的配置（ruff/mypy/eslint/…） |
| 测试目录布局 | tests/unit、tests/e2e、tests/acceptance、*_test.go、*.test.ts |
| 顶层源码目录 | 排除 .git、.venv、node_modules、__pycache__ |
| 现有规格锚点 | .specs/**.md 中的 #sec-* |

Planner 必须据此填契约的 dod：**只写报告能佐证的命令**。报告是生成的，不手改；改了配置就重新生成（--check 会告诉你是否过期）。

### 2.8 没有 Python 时

手工执行同样六步：手抄仓库约定 → 复制 change/assets/templates/proposal.template.md 并填 token、计算 sha256 → 复制四个任务模板并补 change_id/size_class → 按 plan-linter 与 review 的清单人工过门禁 → 实现/验收 → 按 converge 的手工步骤 append 写回并归档。技能不依赖 Python，只是没有脚本时更慢。

---

## 3. 收敛：converge 技能

### 3.1 状态机

```text
WAITING_FOR_QA ──(Dev 勾选)──▶ QA_PASSED ──(converge apply)──▶ CONVERGED
                                    │                              │
                          REWORK_REQUIRED                    任务包归档 + proposal archived
                                    ▼
                             Dev 修复后重新交接
```

converge 只在 QA_PASSED 之后运行。它做的是**把已确认的事实写回规格**，不是重新设计、不是美化文档，更不是给失败的任务补一个通过。

### 3.2 Dev 的偏差日志（02 的新章节）

02-dev-workspace.md 末尾新增 Implementation deviations 表：

| Deviation ID | Spec anchor | Operation | Confirmed behavior |
| :--- | :--- | :--- | :--- |
| DEV-001 | #sec-auth-tokens | modify | 登录失败计数按 IP+账号双维度，阈值 5 次/15 分钟 |
| DEV-002 | #sec-auth-tokens | add | 超限返回 429 并带 Retry-After 头 |

没有偏差时写一行 None（四列都写 None），**不要留空**：空表会被 converge 判定为不可收敛。Dev 只写这张表，**永远不直接编辑 .specs/02-tech-spec.md**。

### 3.3 check → apply → verify

```bash
# 1) 分类：converged / pending / blocked（blocked 会给出原因）
python .agents/skills/converge/scripts/converge.py check --tasks-dir ./tasks --json
python .agents/skills/converge/scripts/converge.py check --tasks-dir ./tasks --fail-on-pending   # CI 用

# 2) 先 dry-run 看计划写入，再执行一个任务包
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-rate-limit --dry-run
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-rate-limit --json

# 3) 漂移检测：CI 记录/比对规格指纹
python .agents/skills/converge/scripts/converge.py --spec .specs/02-tech-spec.md --spec-sha256
```

apply 的实际效果：

1. 在规格末尾**追加**（已有则复用）`## Converged changes` 章节，写入一条 `### <task-id>` 记录：偏差表 + 标记
   ```text
   <!-- converged: CHG-001-rate-limit sha256:<block-hash> -->
   ```
2. 04-process.md：macro_status: "CONVERGED"，追加一条 TASK_CONVERGED / ConvergeTool 事件；
3. 任务包移动到 tasks/archive/<task-id>/（**只移动，不删除**）；
4. 若契约带 change_id：写 .specs/changes/<id>/convergence.md，proposal status: archived。

重复执行是幂等的：第二次 apply 检测到标记后直接 exit 0，不产生新内容。

### 3.4 写回规则

- **只追加，不改写历史**：现有规格正文与其他收敛记录保持逐字节稳定；
- **日期 + 归属**：每条记录带任务 id、来源裁决与 ConvergeTool 身份；
- **冲突不覆盖**：两个任务触碰同一锚点时各写一条记录，冲突写进 convergence.md，由 Planner 决定合并方式；
- **结构性偏差升级**：新模块/新边界/新 ADR 级决策 → 回 spec-generator，不允许悄悄收敛。

### 3.5 拒绝条件（exit 1，附原因）

- 03 没有勾选 QA_PASSED，或 REWORK_REQUIRED 仍处于激活状态；
- 02 没有偏差表，或既无 DEV 行也无 None 行；
- 偏差指向的 modify/remove 锚点在规格中不存在（默认 warning；--strict 时拒绝，CI 建议开）；
- 目标归档目录已存在且没有 --force；
- 04-process.md 缺失（apply 需要更新它）。

### 3.6 归档布局

```text
tasks/archive/CHG-001-rate-limit/          # 已收敛任务包（四文档 + 证据原样保留）
.specs/changes/CHG-001-rate-limit/
├── proposal.md                            # status: archived
└── convergence.md                         # 本次写回了什么、指纹是什么
.specs/02-tech-spec.md                     # 末尾追加 Converged changes 记录
```

归档保留完整审计链：谁实现、谁验收、写了什么回规格、指纹是否漂移。

---

## 4. Gate 2 启发式：plan-linter 3.x

Gate 2 依然是**只读 Reviewer 的语义判断**，不是脚本。3.x 的脚本只负责把"机器能确定的线索"提前算好：

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes \
  --coverage-out artifacts/coverage.json --json
```

| 启发式 | 发现什么 | 默认严重度 | 收紧方式 |
| :--- | :--- | :--- | :--- |
| 锚点覆盖率矩阵 | 规格里没有任何任务引用的 #sec-*（正向完整性候选清单） | 报告（JSON coverage） | --require-full-coverage |
| 反向拓扑 | modify 路径在磁盘上不存在 / create 路径已存在（虚构路径信号） | warning | --strict-topology |
| 锚点溯源 | 契约的 origin_spec_anchor 不在规格里 | warning | --strict-anchor |
| change 一致性 | 契约 change_id 没有对应且未归档的 proposal | error | --changes-dir |
| micro 预算 | micro 超行数/touch 数/缺 change_id | error | config |

coverage 对象（--spec 时出现，--coverage-out 可单独落盘给 Reviewer 或 CI diff）：

```json
{
  "spec": ".specs/02-tech-spec.md",
  "spec_anchors": 3,
  "covered": ["#sec-alpha", "#sec-beta"],
  "uncovered": ["#sec-gamma"],
  "contract_anchors_missing_from_spec": [],
  "coverage_ratio": 0.6667
}
```

Reviewer 的使用方式：把 uncovered 当作**正向完整性**的起点，把 contract_anchors_missing_from_spec 与 TOUCH_FILE_MISSING 当作**反幻觉**的起点；**结论仍由 Reviewer 给出**，脚本不宣布 Gate 2 通过。--strict-* 只在规格/覆盖率被持续维护的仓库里开启，否则会制造噪音。

---

## 5. 分发与 CI 采纳

### 5.1 一条命令采用到别的仓库

```bash
# 默认安装：.agents/skills、.agents/rules、.agents/scripts、hooks.json、tools/rbac_audit.py
python tools/quickstart.py --target ../another-repo --copy --with-ci

# 有 uv 时可直接运行 PEP 723 脚本（无需安装本仓库）
uv run tools/quickstart.py --target ../another-repo --with-ci

# 只装几个技能 / 只预览 / 机器可读
python tools/quickstart.py --target ../r --skills change,converge,plan-linter --copy
python tools/quickstart.py --target ../r --dry-run
python tools/quickstart.py --target ../r --json
```

退出码：0 成功、1 安装失败、2 用法或路径不安全。所有目标路径都做包含性检查，默认不覆盖已有文件（--force 才替换）。

### 5.2 两个可直接抄的 GitHub Actions

| 模板 | 触发 | 作用 |
| :--- | :--- | :--- |
| templates/ci/rbac-gate.yml | pull_request | 用 tools/rbac_audit.py 按事件 base/head 检查角色越权（L2 权威层） |
| templates/ci/plan-gate.yml | pull_request（tasks/**、.specs/**） | 跑 Gate 1 + 覆盖率矩阵，JSON 写进 step summary |

两者只需 permissions: contents: read；rbac-gate 还需要 fetch-depth: 0，角色取自仓库变量 RBAC_ROLE 或提交 trailer Agent-Role:。安装、权限、版本固定与排错见 [templates/ci/README.md](../templates/ci/README.md)。

CI 是强制层；.agents/hooks.json 仍只是 Antigravity 的尽力而为适配器。采用时请固定到 tag/commit 并提交复制结果，让升级成为可审查的 diff。

---

## 6. 端到端示例

### 6.1 一次 micro bugfix（已有规格）

```bash
python .agents/skills/change/scripts/standards_extract.py --repo-root .
python .agents/skills/change/scripts/scaffold_change.py --change-id CHG-002-429-retry \
  --title "Return 429 with Retry-After on rate limit" --anchor "#sec-auth-tokens" \
  --kind modify --size-class micro --estimated-lines 35 \
  --touch-files "modify:src/auth/rate_limit.py" --repo-root .

# Planner 填 proposal + 契约 → 门禁
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes
# Gate 2：review 技能（plan-review 模式）

# dev → qa 完成后
python .agents/skills/converge/scripts/converge.py check --tasks-dir tasks --json
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-002-429-retry --dry-run
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-002-429-retry
```

### 6.2 把整条流水线装进另一个仓库

```bash
python tools/quickstart.py --target ../another-repo --copy --with-ci
# 目标仓库里：git add .agents tools templates .github && git commit -m "adopt agent-spec suite"
# 之后每个 PR：rbac-gate（角色越权）+ plan-gate（Gate 1 / 覆盖率）自动运行
```

---

## 7. 与 v2 的兼容性

| 变化 | 影响 | 迁移动作 |
| :--- | :--- | :--- |
| 技能 7 → 9（新增 change、converge） | 旧任务流程不受影响 | 无需动作；可按需逐步采用 |
| 02-dev-workspace.md 新增偏差表 | 旧模板生成的任务包没有该表 | 新任务用新模板；旧任务收敛前由 Dev 补一行 None 或按手工步骤写回 |
| plan-linter 3.0 默认新增拓扑 warning | 通过/失败语义不变，只是多 warning | 需要严格时用 --strict-topology；不需要时 --no-topology |
| --spec / --coverage-out / --changes-dir 默认不启用 | 旧 CI 命令行为不变 | 需要覆盖率矩阵时显式加参数 |
| size_class: micro 是可选字段 | 不写就是 standard | 只有 micro 变更需要写 |

---

## 8. 诚实边界

- 覆盖率矩阵是**锚点级记账**，不是语义覆盖：任务引用了一个锚点，不代表它真的实现了该章节；
- change 不替代 spec-generator：需要新章节、新 ADR、新边界时必须升级流程；
- converge 不授予写权限、不强制执行角色隔离；权威强制仍来自 CI（tools/rbac_audit.py）+ 分支保护；
- quickstart 是**复制/链接式分发**，不是包管理器或插件市场；它不解决版本注册表、自动升级与联邦发现；
- 所有脚本都是可选的：没有 Python 时按各 SKILL.md 的手工降级路径执行，证据与 marker 仍然是契约。

---

## 9. 相关文档

- [技能索引（英文）](../.agents/skills/README.md)
- [技能使用指南（v2 基础流程）](skills-guide.zh-CN.md)
- [v2 设计契约（含 v3 增补）](skills-v2-spec.md)
- [宿主兼容 / 安装 / 分发](skills-compatibility.md)
- [真实仓库试点与证据](v3-pilot.zh-CN.md)
- [评分与开源对标](skills-benchmark.zh-CN.md)
- [CI 模板说明](../templates/ci/README.md)

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
