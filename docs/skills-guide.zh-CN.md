# 技能使用指南（v2 基础 + v3 增量 + 现代质量工程）：从想法到交付验收

> 适用对象：使用 `.agents/skills/` 的开发者、Planner、Dev、QA、Reviewer Agent 与 CI/CD 运维工程师。  
> 对应版本：技能 `metadata.version` 2.x（基础流程）、3.x（brownfield/收敛/分发）与 4.x（现代质量工程：BDD + 圈复杂度 + 变异测试 + 4 阶段分层测试流水线）。  
> v3 用法见 [`brownfield-convergence.zh-CN.md`](brownfield-convergence.zh-CN.md)；CI 门禁与工作流模板见 [`templates/ci/README.md`](../templates/ci/README.md)。  
> **v3.2.0 加固**：Gate 3 与真实 AST artifact 交叉核验、变异测试 fail-closed、错误码注册表与 triage、证据 provenance 与 Appeal/仲裁；详见 [`skills-remediation.zh-CN.md`](skills-remediation.zh-CN.md)。
> **v3.3.0 新增**：`test-engineering` 全局测试方法学技能（测试策略、测试设计方法、数据/环境与 flakiness 策略、测试指标与独立测试设计评审）；它不接收单任务、不写测试与 `03`、不运行 CI 门禁，详见 §7.8。
> **v3.4.0 策略接线**：本仓库的测试策略示例落盘为 [`testing-strategy.md`](testing-strategy.md)，采用方应从技能内置模板生成自己的策略；QA 在测试设计前只读读取并在 `03` 记录测试设计摘要，`quality-engineering` 负责把策略映射为 CI 画像/作业选择/阈值/环境服务。该示例文件不属于技能安装包，单独安装 `test-engineering` 不依赖它。
> **v3.4.1 修复**：`qa` 自带 `scripts/verification_linter.py` 作为本地 Gate 3 预检，不再依赖 quality-engineering 安装；本地预检是 advisory，CI Gate 3 仍是权威。
> 本文系统说明十一个技能如何协同工作、现代质量工程三支柱如何落地、四阶段测试流水线与 CI 权威门禁如何运转。

---

## 1. 一句话结论

**技能本身是"提示词 + 模板 + 纯标准库小工具"的自包含包；现代质量工程三支柱（BDD 可执行契约、圈复杂度控制流分析、变异测试杀伤力审计）深度内嵌于任务生命周期中；本地提示词规则仅为辅助引导，CI 流水线是不可绕过的权威强制层。**

核心要点：

- **自包含与免安装**：脚手架、占位符校验、Gate 1 规划门禁（`plan_linter.py`）与 Gate 3 验收门禁（`verification_linter.py`）均为 **Python 标准库** 脚本；多语言复杂度检查（`complexity_check.py`）的 tree-sitter/lizard 是**可选依赖**，Python AST 是其标准库 fallback；
- **现代质量工程三支柱**：
  1. **BDD 行为驱动规格**：任务契约 `01-contract.md` 采用结构化 Given-When-Then 定义验收场景，QA 验收测试严格对齐；
  2. **圈复杂度控制流分析**：Dev 编码严格遵循单函数 McCabe $V(G) \le 10$；QA 遵循基本路径测试基线规则（用例数 $\ge V(G)$），数学上覆盖所有线性独立路径；
  3. **变异测试与 MSI 审计**：QA 必须对变更代码执行变异测试，变异得分 $\text{MSI} \ge 80\%$，彻底消除无断言与弱断言假阳性；
- **门禁职责解耦**：
  - **Gate 1（规划期门禁）**：`plan_linter.py` 专职审计任务切片、DAG 拓扑、规格锚点与 BDD 契约格式；
  - **Gate 2（语义审查门禁）**：只读 Reviewer Agent 审查正向覆盖率、反幻觉与 ADR 架构合规性；
  - **Gate 3（验收期门禁）**：`verification_linter.py` 专职审计 `03-qa-verification.md` 中的圈复杂度覆盖与变异测试杀伤力证据；
- **全局测试方法学（跨任务）**：`test-engineering` 负责仓库级测试策略、测试设计方法（等价类/边界值/判定表/状态迁移/成对组合等）与独立测试设计评审；其 `DESIGN_READY` / `DESIGN_GAPS` 仅是设计质量标记，不是任务裁决，单任务验收仍归 `qa`，CI 门禁仍归 `quality-engineering`；
- **四阶段分层测试流水线**：涵盖本地测试、测试环境、合并前 PR 权威门禁与合并后主干回归/规格收敛，提供开箱即用的 GitHub Actions 工作流模板（`templates/ci/quality-gate.yml`）。

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
├── task-decomposition/     # 规格 → 任务包（4 文档，BDD 可执行契约）
│   ├── SKILL.md
│   ├── assets/templates/   # 01-contract / 02-dev-workspace / 03-qa-verification / 04-process
│   ├── references/         # 黄金切片、反幻觉、BDD 场景推导规则
│   └── scripts/scaffold_task.py
├── change/                 # brownfield：增量 proposal + 单个任务包 + 归档
│   ├── SKILL.md
│   ├── assets/templates/proposal.template.md
│   ├── references/brownfield-protocol.md
│   └── scripts/            # scaffold_change.py / standards_extract.py / lint_change.py
├── plan-linter/            # Gate 1 确定性静态门禁（规划期：契约、BDD、DAG、切片）
│   ├── SKILL.md
│   ├── references/gate-2-review.md  # 未安装 review 时的自包含备用清单
│   └── scripts/plan_linter.py
├── review/                 # Gate 2 语义审查 / 变更审查
│   ├── SKILL.md
│   └── references/{plan-review,code-review}.md
├── dev/                    # 执行：按契约实现、控制 V(G) <= 10、自测、填 02、交接
│   ├── SKILL.md
│   └── references/dev-protocol.md
├── qa/                     # 本地开发阶段测试：集成测试、BDD E2E、变异测试、Lint、圈复杂度、自主 review
│   ├── SKILL.md
│   ├── references/qa-protocol.md
│   └── references/role-boundaries.md
├── quality-engineering/    # CI 质量工程：构建 CI 流水线、测试环境准备、代码合并前/后门禁与测试
│   ├── SKILL.md
│   ├── references/verification-protocol.md
│   └── scripts/            # complexity_check.py (圈复杂度门禁) / verification_linter.py (Gate 3 审计)
├── test-engineering/       # 全局测试体系：测试策略、测试设计方法、数据/环境/flakiness 策略、独立测试设计评审
│   ├── SKILL.md
│   ├── assets/templates/test-strategy.template.md
│   └── references/         # test-strategy / test-design-review / role-boundaries
└── converge/               # 收敛：QA_PASSED 后写回规格、归档任务包与 change
    ├── SKILL.md
    ├── references/convergence-protocol.md
    └── scripts/converge.py
```

每个技能的核心输入、输出与判定主体：

| 技能 | 输入 | 输出 | 判定/驱动主体 |
| :--- | :--- | :--- | :--- |
| `prd-generator` | 模糊创意、笔记、旧 PRD | `.specs/01-prd.md` + `.specs/01-prd/` | Agent（澄清、4 角色评审、收敛） |
| `spec-generator` | PRD | `.specs/adr/*.md` + `.specs/02-tech-spec.md` + `.specs/02-tech-spec/` | Agent（架构权衡、ADR 决策） |
| `task-decomposition` | PRD + ADR + Tech Spec | `tasks/<task-id>/` 四份文档（含 BDD Gherkin 契约） | Agent（垂直切片、BDD 行为规范、追溯） |
| `change` | 现有规格 + 一个有界变更 | `.specs/changes/<id>/proposal.md` + 1 个任务包 + standards 报告 | Agent（增量提案、隐式约束、升级判断） |
| `plan-linter` | `tasks/` | Gate 1 静态检查报告（含 BDD 场景校验） | 脚本（`plan_linter.py`，结构与格式） |
| `review` | 计划/任务包，或 diff + 证据 | 发现清单 + PASS/REQUEST CHANGES/BLOCKED | Agent（只读语义审查，防幻觉/违规） |
| `dev` | `01-contract.md` + 项目命令 | 代码变更（$V(G) \le 10$）、填好的 `02`、`WAITING_FOR_QA` | Agent（业务实现、重构自测、自证） |
| `qa` | `01`、填好的 `02`、测试命令 | `tests/acceptance/**`、`tests/integration/**`、填好的 `03`（本地测试与审计证据）、唯一裁决 | Agent（本地集成、BDD E2E、变异杀伤、静态 Lint/复杂度、自主 review） |
| `quality-engineering` | CI 触发事件、PR diff、`tasks/` 交付包、CI 模板 | CI 流水线状态、门禁报告（Gate 1、RBAC、圈复杂度、验收测试、Gate 3）、合并前/合并后测试结果 | CI / 脚本（`quality-gate.yml`、`complexity_check.py`、`verification_linter.py`） |
| `test-engineering` | 质量属性、现有测试套件、缺陷/事故历史、任务契约（只读） | 商定的测试策略文档、测试设计评审记录（`DESIGN_READY` / `DESIGN_GAPS`） | Agent（跨任务测试策略与设计标准；不参与单任务裁决） |
| `converge` | `01`、带偏差表的 `02`、勾选 `QA_PASSED` 的 `03` | 写回 `.specs/02-tech-spec.md`、`CONVERGED` 状态、归档任务包 | 脚本（`converge.py`，append-only 写回） |

---

## 3. 工作模型：判断 vs 确定性

整个研发流水线由“智能判断层”与“确定性门禁层”交织构成：

| 分层 | 负责内容 | 核心载体 | 判定机制 |
| :--- | :--- | :--- | :--- |
| **智能协商层 (Skill)** | 需求理解、架构权衡、BDD 设计、编码实现、黑盒设计 | `SKILL.md` + `references/` | Agent 提示词推理 |
| **数据契约层 (Template)** | 结构化、机器可解析的角色契约与证据表单 | `assets/templates/` | 标准 Markdown/YAML |
| **规划门禁 (Gate 1)** | 契约合法性、BDD 三段式格式、切片爆炸半径、DAG 无环 | `plan_linter.py` | 确定性脚本（exit 0/1） |
| **语义门禁 (Gate 2)** | 正向覆盖、反幻觉审查、ADR 架构红线对齐 | `review` 技能 | 只读 Reviewer Agent |
| **验收门禁 (Gate 3)** | 圈复杂度用例覆盖 $V(G) \le \text{用例数}$、变异测试得分 $\text{MSI} \ge 80\%$ | `verification_linter.py` | 确定性脚本（exit 0/1） |
| **权威强制层 (CI / L2)** | 角色 RBAC 边界审计、全量门禁串联、分支合并保护 | `tools/rbac_audit.py` + `quality-gate.yml` | GitHub Actions / 平台 CI |

> **关键原则**：本地提示词规则与 Agent 自律仅为辅助（L0），**权威强制层是 CI 与分支保护（L2）**。任何任务必须在 CI 中通过 RBAC 审计、Gate 1、Gate 3 及验收测试，才允许合入主干。

---

## 4. 快速开始（端到端实战流程）

以下命令均在目标仓库根目录执行。

### 4.1 生成并填写 PRD

```bash
# 1) 复制 PRD 模板到 .specs/
python .agents/skills/prd-generator/scripts/scaffold.py --out .specs

# 2) Agent 依据 SKILL.md 与 references/prd-format.md 编写：
#    .specs/01-prd.md 及 .specs/01-prd/*.md

# 3) 静态校验结构
python .agents/skills/prd-generator/scripts/lint_prd.py .specs
```

### 4.2 生成并填写技术规格与 ADR

```bash
# 1) 复制 ADR / Tech Spec 模板
python .agents/skills/spec-generator/scripts/scaffold.py --out .specs

# 2) 编写 .specs/adr/*.md、.specs/02-tech-spec.md 与 .specs/02-tech-spec/

# 3) 静态校验技术规格
python .agents/skills/spec-generator/scripts/lint_spec.py .specs
```

### 4.3 拆分任务并生成 BDD 契约

```bash
# 为任务生成标准四文档
python .agents/skills/task-decomposition/scripts/scaffold_task.py \
  --tasks-dir tasks \
  --task-id task-001-auth \
  --title "用户认证与凭据校验"
```

Planner 在 `01-contract.md` 中编写结构化的 BDD 验收场景：

```yaml
---
task_id: task-001-auth
title: "用户认证与凭据校验"
module: auth
dependencies: []
estimated_lines: 120
touch_files:
  - action: create
    path: src/auth/service.py
  - action: modify
    path: src/auth/routes.py
origin_spec_anchor: "#sec-auth"
adherence_adrs: [ADR-001]
dod:
  type_check: "npm run type-check"
  lint: "npm run lint"
  test_file: "tests/acceptance/test_auth.py"
  edge_cases:
    - "Given empty credentials, When login requested, Then return 400 with invalid parameters error"
    - "Given expired session token, When profile requested, Then return 401 unauthorized"
    - "Given locked account, When credentials submitted, Then return 403 account locked"
---
```

同时在 `01-contract.md` 第 4 节定义详细的 Gherkin Feature 行为不变量。

### 4.4 运行 Gate 1（规划门禁）

```bash
# 本地运行 Gate 1 静态检查（检查切片大小、BDD 格式、DAG 等）
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks

# 输出机器可读 JSON（CI 门禁模式）
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --json
```

### 4.5 运行 Gate 2（语义审查）

由只读 Reviewer Agent 执行，核对任务切片是否如实反映规格、是否发明未授权实体、是否遵循 ADR 架构红线。

### 4.6 开发、自测与独立验收（Dev & QA）

1. **Dev 实现与复杂度控制**：
   - 严格在 `touch_files` 白名单内编码；
   - 保持单函数圈复杂度 McCabe $V(G) \le 10$；若分支过深，应用提炼函数或策略模式重构；
   - 运行本地 `dod.type_check`、`dod.lint` 与单元自测；
   - 填写 `02-dev-workspace.md`，确认无误后勾选 `- [x] WAITING_FOR_QA` 交接。

2. **QA 本地开发阶段测试（集成测试、BDD E2E、变异测试、静态分析、自主 Review）**：
   - **集成测试**：在 `tests/integration/` 编写跨模块协作与接口集成用例；
   - **基于 BDD 模式的端到端测试**：基于 `01-contract.md` 的 Given-When-Then 场景，自主引入各技术栈知名开源 BDD 工具（Python `pytest-bdd`/`behave`、JS/TS `Cucumber.js`、Go `Godog`、Java `Cucumber-JVM` 等）在 `tests/acceptance/` 编写黑盒验收与 E2E 测试；
   - **代码静态分析**：使用跨语言 AST 引擎 **Tree-sitter** 与开源分析工具（`tree-sitter`、`lizard`、`radon`、`eslint` 等），审查变更函数的独立路径，确保用例数 $\ge V(G)$，严禁 $V(G) > 15$；
   - **自主调用 review 技能**：自行决定调用 `review` skill 评审变更代码规范（可读性、命名与可维护性）；
   - **引入知名开源工具与变异测试**：针对不同项目类型**必须优先引入知名开源变异测试工具**（`mutmut`、`Stryker`、`go-mutesting`、`PITest`、`cargo-mutants`、`Mull` 等），击杀存活弱断言，确保 $\text{MSI} \ge 80\%$；合成变异仅作为无开源工具环境的灾备后备方案；
   - 填写 `03-qa-verification.md` 中的复杂度表、变异审计表与执行证据，勾选 `- [x] QA_PASSED` 或 `REWORK_REQUIRED`。

3. **运行 Gate 3（验收门禁本地预检）**：

```bash
# 校验 03 文档中的圈复杂度与变异测试杀伤力证据（由 quality-engineering 提供并维护）
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir tasks --strict --json
```

### 4.7 规格收敛与归档（converge）

Gate 3 与 CI 均通过后，触发收敛技能：

```bash
# 预览收敛写回内容
python .agents/skills/converge/scripts/converge.py apply --task tasks/task-001-auth --dry-run

# 正式执行收敛（将 02 偏差表追加进 02-tech-spec.md 并将任务包移至 tasks/archive/）
python .agents/skills/converge/scripts/converge.py apply --task tasks/task-001-auth
```

---

## 5. 现代质量工程三支柱核心规范

现代质量工程的三大核心支柱贯穿从需求分解到最终收敛的全流程：

```text
               ┌─────────────────────────────────────────────────────┐
               │         现代质量工程三大核心支柱 (Quality Triad)         │
               └─────────────────────────────────────────────────────┘
                                          │
         ┌────────────────────────────────┼────────────────────────────────┐
         ▼                                ▼                                ▼
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│  BDD 行为驱动规格 │            │  圈复杂度控制流   │            │   变异测试与 MSI  │
│ Executable Spec  │            │ McCabe V(G) <= 10│            │   Kill Ratio >= 80% │
└──────────────────┘            └──────────────────┘            └──────────────────┘
│ • 01 edge_cases  │            │ • Dev 函数复杂度  │            │ • 6 步变异测试流程│
│ • Given-When-Then│            │ • 4 大重构设计模式│            │ • 多语言变异引擎   │
│ • Gherkin 场景   │            │ • QA 用例数 >= V(G│            │ • 5 大合成变异算子│
│ • Gate 1 静态门禁│            │ • Gate 3 静态审计 │            │ • 消除无力断言假阳│
└──────────────────┘            └──────────────────┘            └──────────────────┘
```

### 5.1 BDD 行为驱动规格与可执行契约

#### 核心理念
传统研发流程中，需求描述常因自然语言歧义导致实现与验收脱节。BDD（Behavior-Driven Development）将业务期望形式化为统一的领域行为规范（Given-When-Then），成为研发（Dev）、测试（QA）与业务方共同遵循的“可执行活文档”。

#### 契约规范与格式要求
1. **Frontmatter `dod.edge_cases` 结构化约束**：
   契约头部数组中的每个用例必须遵循严格的英文或中英文三段式结构：
   ```yaml
   dod:
     edge_cases:
       - "Given [前置条件], When [触发动作], Then [预期结果与副作用]"
   ```
   *有效示例*：
   - `"Given user with insufficient balance, When transfer initiated, Then return 402 and keep balance unchanged"`
   - `"Scenario: Rate limit exceeded | Given 100 requests in 1 minute, When 101st request sent, Then return 429 Too Many Requests"`

2. **Section 4 行为不变量（Behavioral Invariants）**：
   在 `01-contract.md` 正文中使用 Gherkin 语法详细定义主要场景（Happy Path）与异常场景（Corner Cases）：
   ```gherkin
   Feature: User Token Authentication
     Scenario: Successful token validation
       Given a valid and unexpired JWT token for user "alice"
       When the client requests protected resource "/api/v1/profile"
       Then response status is 200
       And response body contains user profile data
   ```

3. **Gate 1 静态校验**：
   `plan_linter.py` 内置 BDD 场景解析引擎，严格拦截：
   - `BDD_MISSING_PRECONDITION`：缺少 Given 前置条件声明；
   - `BDD_MISSING_ACTION`：缺少 When 动作声明；
   - `BDD_MISSING_OUTCOME`：缺少 Then 结果断言；
   - `BDD_EMPTY_SCENARIO`：场景包含未替换的 `[TBD]` 或空白字符串。

4. **各技术栈知名开源 BDD 工具推荐与运行范式**：
   QA 编写验收测试时，应将契约中的 Gherkin 场景映射为对应技术栈成熟的开源 BDD 框架测试：
   - **Python**: `pytest-bdd` (`pytest tests/acceptance/`) 或 `behave` (`behave tests/acceptance/features/`)
   - **JavaScript / TypeScript**: `Cucumber.js` (`npx cucumber-js tests/acceptance/features/*.feature`) 或 `playwright-bdd`
   - **Go**: `Godog` (`godog run tests/acceptance/features/`)
   - **Java**: `Cucumber-JVM` (`mvn test -Dcucumber.filter.tags="@acceptance"`)
   - **Rust**: `cucumber-rs` (`cargo test --test cucumber`)
   - **C# / .NET**: `Reqnroll` / `SpecFlow` (`dotnet test --filter Category=Acceptance`)

---

### 5.2 圈复杂度控制流分析与基本路径覆盖门禁

#### 核心理念与 McCabe 计算公式
圈复杂度（Cyclomatic Complexity，McCabe 度量衡）衡量程序控制流中的独立线性路径数量。控制流图表示为有向图 $G = (V, E)$，公式为：
$$V(G) = E - N + 2P$$
对于单函数（连通分量 $P = 1$），$V(G) = \text{判定节点数（if, while, for, case, &&, || 等）} + 1$。
高圈复杂度意味着极高的认知负荷、高缺陷率与极难完全测试的代码。

#### 复杂度阈值与红线标准
- **$V(G) \le 10$（健康 / STANDARD）**：单函数圈复杂度推荐上限。结构清晰，易于理解与测试。
- **$11 \le V(G) \le 15$（告警 / WARNING）**：黄色预警，Dev 需在 `02` 中详细说明控制流合理性，并考虑重构。
- **$V(G) > 15$（严重违规 / CRITICAL）**：红色门禁直接阻断！严禁合入代码库，必须通过设计模式进行函数拆解。

#### Dev 角色 4 大重构模式
当单函数圈复杂度逼近或超过 10 时，Dev 应当采用以下标准模式重构：
1. **提炼函数（Extract Method）**：将循环体内部复杂的条件分支逻辑抽取为独立命名的纯函数；
2. **策略模式 / 多态分发（Strategy / Dispatch Table）**：用字典表映射（Dictionary Dispatch）或多态子类替代深层嵌套的 `switch-case` 或多分支 `if-elif-else`；
3. **卫语句早期返回（Guard Clauses）**：在函数前部对非法参数、边界条件与错误状态执行 `return`，消除多层缩进嵌套；
4. **表驱动设计（Table-driven Design）**：将复杂的多条件映射关系提取为数据驱动规则表，将控制流复杂度转化为数据结构。

#### QA 基本路径测试基线规则（Basis Path Testing Baseline Rule）
- **数学覆盖铁律**：QA 设计的黑盒验收用例数量，在数学上**不得低于变更函数的基本路径数总和**：
  $$\text{Test Cases} \ge \sum V(G)_{\text{modified\_functions}}$$
- **03 产物证据**：在 `03-qa-verification.md` 的 `Section 3. Complexity and basis path coverage` 表格中，明确记录被测函数名、圈复杂度、独立路径描述及对应测试用例编号（如 `TC-001`, `TC-002`）。

#### 跨语言开源解析引擎（Tree-sitter 与知名开源工具）
圈复杂度计算必须覆盖实际项目的多种主流编程语言，严禁局限于 Python 单语言。体系采用知名开源项目 [Tree-sitter](https://github.com/tree-sitter/tree-sitter) 作为多语言抽象语法树（CST）统一分析引擎，并深度集成各语言生态的成熟工具：
- **通用跨语言引擎（内置）**：`quality-engineering` 提供的 `complexity_check.py` 基于 Tree-sitter 解析 Python、JavaScript、TypeScript、Go、Rust、Java、C、C++、C#，统一判定控制流分支并统计 $V(G)$；同时原生支持开源多语言复杂度工具 [Lizard](https://github.com/terryyin/lizard)；
- **Python**: `tree-sitter`、`lizard`、`radon cc`、`ruff`
- **JavaScript / TypeScript**: `tree-sitter`、`eslint`（`complexity` 规则）、`lizard`
- **Go**: `tree-sitter`、`gocyclo`、`gocognit`、`lizard`
- **Rust**: `tree-sitter`、`cargo clippy -- -D clippy::cognitive_complexity`、`lizard`
- **Java**: `tree-sitter`、`pmd`（`CyclomaticComplexity` 规则）、`checkstyle`
- **C / C++**: `tree-sitter`、`lizard`

---

### 5.3 变异测试杀伤力审计与假阳性消除

#### 为什么必须做变异测试？
代码行覆盖率（Line Coverage）与分支覆盖率（Branch Coverage）存在致命盲区：**只要代码被执行过，覆盖率即记为 100%，哪怕测试中没有写任何 `assert` 断言，或者只写了毫无约束力的弱断言**。
变异测试通过在被测代码中自动注入微小语法变异（如改写比较符、翻转布尔值、替换常量），检验测试套件能否及时报错失败。若变异注入后测试依然全部通过，证明存在严重的“无力断言”与“假阳性测试”。

#### 核心指标与计算公式
变异得分指示器（Mutation Score Indicator, MSI）定义为被杀伤或超时的变异体占有效变异体总数的百分比：
$$\text{MSI} = \frac{\text{Killed} + \text{TimedOut}}{\text{Total} - \text{Equivalent}} \times 100\%$$
- **门禁红线**：标准交付任务必须达到 **$\text{MSI} \ge 80\%$**；核心安全与高危模块推荐 **$\text{MSI} \ge 90\%$**。

#### 6 步变异测试标准工作流
```text
1. 选取目标 (touch_files) ──> 2. 注入变异体 ──> 3. 执行测试套件
                                                      │
                                                      ▼
6. 门禁审计 (MSI >= 80%) <── 5. 杀伤弱断言 <── 4. 变异分类 (K/S/T/E)
```
1. **限定目标**：仅针对本次任务 `touch_files` 中变更的代码函数进行变异测试，避免全仓运行的性能开销；
2. **注入变异**：调用变异引擎或由 QA Agent 注入变异算子；
3. **执行测试**：针对每个变异体运行黑盒验收用例；
4. **分类结果**：
   - **Killed（击杀）**：测试断言捕获错误并失败（优秀断言）；
   - **Survived（存活）**：测试全部通过（暴露弱断言或测试盲区）；
   - **TimedOut（超时）**：引发死循环或超时被强杀（视同有效击杀）；
   - **Equivalent（等价）**：变异后语义并未改变（如冗余边界条件），不计入分母；
5. **杀伤弱断言**：分析所有 Survived 变异体，精准补强或新增黑盒验收断言，直到将存活变异体彻底击杀；
6. **门禁审计**：将最终变异数据写入 `03-qa-verification.md`，由 Gate 3 静态门禁脚本校验。

#### 各技术栈知名开源变异测试工具（首选与强制执行标准）
进行变异测试时，**必须优先引入各技术栈成熟权威的开源变异测试工具**。开源工具具备标准变异算子库与严格的沙箱运行机制，确保变异杀伤证据客观真实：
- **Python**: `mutmut`（标准首选）或 `cosmic-ray`
  ```bash
  mutmut run --paths-to-mutate src/auth/service.py --runner "pytest tests/acceptance/"
  mutmut results
  ```
- **JavaScript / TypeScript**: `Stryker`（前端与 Node.js 工业标准）
  ```bash
  npx stryker run --mutate "src/auth/**/*.ts"
  ```
- **Go**: `go-mutesting`
  ```bash
  go-mutesting ./src/auth/...
  ```
- **Rust**: `cargo-mutants`
  ```bash
  cargo mutants --file src/auth/service.rs
  ```
- **Java / Kotlin**: `PITest (PIT)`
  ```bash
  mvn org.pitest:pitest-maven:mutationCoverage
  ```
- **C / C++**: `Mull` (`mull-runner`)
- **C# / .NET**: `Stryker.NET` (`dotnet stryker --mutate "src/auth/**"`)

#### 极端无工具环境下的合成变异灾备方案（Synthetic Mutation Disaster Fallback）
仅当项目技术栈属于极其罕见或无任何开源变异测试工具支持的极少数特殊场景时，才允许将合成变异作为灾备后备方案。QA Agent 必须严格按照 5 大标准变异算子执行手工/脚本注入与验证：
1. **ROR (Relational Operator Replacement)**：关系操作符替换（如 `>` 变 `<=`, `==` 变 `!=`）；
2. **AOR (Arithmetic Operator Replacement)**：算术操作符替换（如 `+` 变 `-`, `*` 变 `/`）；
3. **LCR (Logical Connector Replacement)**：逻辑连接词替换（如 `and` 变 `or`）；
4. **ABS (Absolute Value / Negation)**：正负值与空值反转（如 `count` 变 `-count`, `user` 变 `None`）；
5. **UOI (Unary Operator Insertion)**：一元操作符插入（如 `x` 变 `!x`, `x++` 变 `x--`）。

---

## 6. 四阶段分层测试流水线与 CI 权威门禁

为确保代码在从开发机到生产环境的每一层级均具备确定性的质量保障，体系定义了严格的四阶段分层测试流水线：

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        四阶段分层测试流水线 (4-Stage Layered Pipeline)                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ├─► 阶段 1：本地测试（Local Testing — Dev 与 QA 闭环）
   │    ├─ Dev 自测：dod.type_check / lint / test_file，单函数 V(G) <= 10
   │    ├─ QA 本地测试：集成测试 (tests/integration/)、BDD E2E 测试 (tests/acceptance/)
   │    ├─ QA 质量保障：变异测试 (MSI >= 80%)、静态分析 (Lint/圈复杂度)、自主调用 review 评审
   │    └─ 本地预检：运行 plan_linter.py (Gate 1) 与 verification_linter.py (Gate 3)
   │
   ├─► 阶段 2：测试环境（Test Environment — quality-engineering 负责）
   │    ├─ 环境配置与验证：容器沙箱隔离、运行时依赖验证、网络隔离与 Mock 就绪
   │    └─ 契约验证：验证真实拓扑连通性与 ADR 架构契约兼容性
   │
   ├─► 阶段 3：合并前测试（Pre-merge / PR Gate — quality-engineering 自动化门禁）
   │    ├─ 1. RBAC 越权审计：tools/rbac_audit.py (Dev 禁碰测试，QA 禁改源码)
   │    ├─ 2. Gate 1 静态门禁：plan_linter.py --json (BDD 格式、切片、DAG)
   │    ├─ 3. 圈复杂度门禁：检查增量函数 V(G) <= 10
   │    ├─ 4. 验收测试执行：运行全量 tests/acceptance/ 与 tests/integration/ 用例
   │    ├─ 5. 变异测试杀伤力审计：验证 MSI >= 80%
   │    ├─ 6. Gate 3 验证门禁：verification_linter.py --strict --json
   │    └─ 7. Gate 2 Reviewer 语义签署：人工或只读 Reviewer 签署 PASS
   │
   └─► 阶段 4：代码合并后测试（Post-merge & Staging/Release — quality-engineering 流水线）
        ├─ 主干全量回归：执行主干全套端到端回归用例，拦截并发冲突
        ├─ 自动化规格收敛：converge.py apply 回写 02-tech-spec.md 并归档
        └─ 基线更新：更新全仓变异测试基线与 Benchmark 性能指标
```

### 6.1 阶段一：本地测试（Local Testing）
- **目标**：在代码提交到远端分支前，完成开发者的局部自闭环与 QA 的本地端到端与集成验证。
- **Dev 自测**：
  - 运行 `01-contract.md` 中声明的 `dod.type_check`、`dod.lint`；
  - 检查自己编写的每个函数，通过 AST 分析或静态工具确认 $V(G) \le 10$；
  - 逐项自测 BDD `dod.edge_cases` 中的所有场景；
  - 填写 `02-dev-workspace.md`。
- **QA 本地开发阶段测试**：
  - **集成测试**：在 `tests/integration/**` 编写跨模块与服务边界集成用例；
  - **BDD 端到端测试**：依据 `01-contract.md` Section 4 BDD 场景在 `tests/acceptance/**` 编写黑盒验收测试；
  - **静态代码分析**：引入栈相关知名 Lint 工具与圈复杂度分析工具，确保用例数 $\ge V(G)$，拒绝 $V(G) > 15$；
  - **变异测试**：执行变异测试（`mutmut`、`Stryker` 等），确保 $\text{MSI} \ge 80\%$；
  - **自主代码评审**：自主调用 `review` skill 评估代码可读性与可维护性；
  - 填写 `03-qa-verification.md` 并签署本地裁决。
- **本地静态预检**：
  ```bash
  python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks
  python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir tasks
  ```

### 6.2 阶段二：测试环境（Test Environment — quality-engineering 负责）
- **目标**：由 `quality-engineering` skill 负责测试环境的搭建、配置与就绪验证，在纯净沙箱或容器环境中验证分布式拓扑与依赖。
- **执行内容**：
  - 针对微服务、数据库、外部 API 依赖，拉起 Ephemeral / Sandbox 独立容器与环境；
  - 验证运行依赖、环境变量、网络连通性与服务 Mock，排除环境就绪缺陷；
  - 验证 ADR 中规定的架构约束与拓扑协议。
- **模板实际提供的能力**：`quality-gate.yml` 会安装项目声明的依赖并运行 `pytest --collect-only`（或 unittest discover）做就绪探针；网络隔离为 `advisory`，除非项目安装 `pytest-socket` 才会加 `--disable-socket`。不要把模板描述成完整的容器/网络沙箱。

### 6.3 阶段三：合并前测试（Pre-merge / PR Gate — quality-engineering 自动化门禁）
- **目标**：由 `quality-engineering` 构建的 CI 流水线作为拉取请求（PR）合入主干的绝对权威守门人，执行不可绕过的确定性门禁。
- **门禁清单**：
  1. **RBAC 角色越权审计**：
     ```bash
     python tools/rbac_audit.py --base origin/main --head HEAD --tasks-dir tasks --json
     ```
     严格拦截跨权限提交（如 Dev 修改了 `tests/acceptance/`，或 QA 修改了 `src/**`）。
  2. **Gate 1 规划与 BDD 契约检查**：
     ```bash
     python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --spec .specs/02-tech-spec.md --json
     ```
     验证切片大小（$\le 3$ 文件、50–250 行）、DAG 无环、Given-When-Then BDD 结构无缺失。
  3. **圈复杂度门禁**：
     ```bash
     python .agents/skills/quality-engineering/scripts/complexity_check.py --src-dir src --json
     ```
     由 `quality-engineering` 提供的静态分析脚本对源码执行控制流复杂度计算，若存在 $V(G) > 10$ 则告警，存在 $V(G) > 15$ 则直接构建失败。没有 `src/` 且未显式传 `--src-dir` 时退出码为 2（fail-closed），不会静默扫描 `.`。
  4. **验收与集成测试套件全量跑通**：模板先安装项目依赖并做 collection 探针，再执行 `tests/acceptance/**`；pytest 可用时产出 JUnit XML，否则回退 unittest。
  5. **变异测试硬门禁（MSI $\ge 80\%$）**：主干 push 时由 `tools/mutation_gate.py` 执行项目 `MUTATION_COMMAND` 并校验归一化报告；命令/报告缺失或 MSI 不足均 fail-closed。PR 阶段 Gate 3 仍审计 QA 记录的证据。
  6. **Gate 3 验收证据交叉核验**：
     ```bash
     python .agents/skills/quality-engineering/scripts/verification_linter.py \
       --tasks-dir tasks \
       --actual-complexity artifacts/complexity-report.json \
       --require-actual-complexity --strict --json
     ```
     将 `03` Section 3 的 V(G) 与真实 AST artifact 逐函数核对；缺失函数、伪造函数、V(G) 不一致都会失败。任一变异表不合规也会失败。
  7. **Gate 2 Reviewer 语义签署**：由具有审查权限的只读 Agent 或人工 Reviewer 审查后签署 PASS；这是人工/分支保护步骤，不是模板里的 CI job。

### 6.4 阶段四：代码合并后测试（Post-merge & Staging / Release — quality-engineering 流水线）
- **目标**：合并入主干后的全局完整性维护与技术规格闭环。
- **执行内容**：
  1. **主干全量回归测试**：在主干执行全部服务、模块与集成验收用例，防止不同分支并发合并产生隐式破坏；
  2. **规格收敛（Converge，手动/可选）**：
     ```bash
     python .agents/skills/converge/scripts/converge.py apply --task tasks/<task-id>
     ```
     将 Dev 记录在 `02` 中的偏差表以追加模式写回 `.specs/02-tech-spec.md`，更新状态至 `CONVERGED`，并将任务包归档至 `tasks/archive/`。当前 `quality-gate.yml` **没有**自动 converge job，需要显式触发；
  3. **基线更新与性能跟踪**：全量更新仓库变异测试基线与 Benchmark 性能指标。

### 6.5 CI 权威强制门禁实战指南

仓库在 `templates/ci/` 提供了开箱即用的 GitHub Actions 门禁模板：

```yaml
# templates/ci/quality-gate.yml (simplified; see the template for full steps)
name: Quality Engineering Gate

on:
  pull_request:
    types: [opened, synchronize, reopened]
  push:
    branches: [main, master]

permissions:
  contents: read

jobs:
  gate1-plan-linter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --spec .specs/02-tech-spec.md --json

  rbac-audit:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - run: python tools/rbac_audit.py --base "${{ github.event.pull_request.base.sha }}" --head "${{ github.event.pull_request.head.sha }}" --tasks-dir tasks --json

  complexity-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python .agents/skills/quality-engineering/scripts/complexity_check.py --src-dir src --json > artifacts/complexity-report.json
      - uses: actions/upload-artifact@v4
        if: always()
        with: {name: complexity-report, path: artifacts/complexity-report.json}

  acceptance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python -m pip install -r requirements.txt   # when present
      - run: python -m pytest --collect-only -q tests/acceptance
      - run: python -m pytest tests/acceptance -q --junitxml=artifacts/acceptance-junit.xml

  gate3-verification:
    runs-on: ubuntu-latest
    needs: [gate1-plan-linter, rbac-audit, complexity-gate, acceptance-tests]
    if: |
      always() &&
      needs.gate1-plan-linter.result == 'success' &&
      needs.complexity-gate.result == 'success' &&
      needs.acceptance-tests.result == 'success' &&
      (needs.rbac-audit.result == 'success' || needs.rbac-audit.result == 'skipped')
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: {name: complexity-report, path: artifacts}
      - run: |
          python .agents/skills/quality-engineering/scripts/verification_linter.py \
            --tasks-dir tasks \
            --actual-complexity artifacts/complexity-report.json \
            --require-actual-complexity --strict --json
```

#### 一键集成到新仓库
```bash
# 使用 quickstart 一键集成全套技能、规则、审计工具与 CI 门禁
python tools/quickstart.py --target ../my-new-repo --copy --with-ci
```

#### 多语言项目：使用 Stack Profiles

`quality-gate.yml` 是 **Python 参考实现**，不是跨栈通用 YAML。其他技术栈从 `templates/ci/profiles/`
选择参考片段（Python、Node/TS、Go、Java、Rust、.NET、C/C++），只替换工具链、安装、验收/JUnit、
变异工具和 adapter，保留 Gate 1/3、RBAC、artifact、fail-closed 不变量。
配置形状见 `templates/ci/quality-gate.config.example.json`；完整采纳说明见
[多语言 CI 参考模板](ci-stack-profiles.zh-CN.md)。

---

## 7. 各技能详解

### 7.1 `task-decomposition`
- **输入**：PRD、ADR 与技术规格。
- **职责**：将架构规格拆解为小步可控的任务包（1–3 个 touch_files，50–250 行变更）。
- **现代质量工程升级**：
  - 从 PRD 业务需求与 ADR 架构契约推导出结构化的 Given-When-Then BDD 场景，写入 `01-contract.md` 的 `dod.edge_cases` 与 Section 4 行为不变量；
  - 自动脚手架生成规范四文档，02 与 03 保持标准空白表单，04 保持派生状态。

### 7.2 `plan-linter`（Gate 1 规划期静态门禁）
- **核心定位**：专职单一职责的规划期确定性静态门禁。在代码开发开始前，核查任务契约是否结构完整、尺寸合规、DAG 无环、Given-When-Then BDD 格式有效。
- **职责边界与非目标**：
  - **单一职责**：只负责 Gate 1 静态任务包契约验证；
  - **明确不负责**：不执行业务代码或测试命令；不构建或维护 CI 流水线；不进行 AST/代码圈复杂度分析（非源码复杂度分析工具）；不审计测试执行证据与变异测试杀伤力。所有 CI 流水线编排、环境配置与门禁脚本资产均归属 `quality-engineering`，本地测试由 `qa` 负责。
- **检查项**：
  1. `touch_files` 数量与目录白名单（默认 $\le 3$，严禁包含 `tests/acceptance/`）；
  2. `estimated_lines` 切片尺寸（50–250 行，micro 模式 10–50 行）；
  3. `origin_spec_anchor`（合法 `#sec-*`）与 `adherence_adrs`（非空）；
  4. `dod` 中 `type_check`、`lint`、`test_file` 齐全且无占位符；
  5. `dod.edge_cases` 至少 2 个，且全部符合 Given-When-Then 结构；
  6. 四文档齐全性、`task_id` 目录名一致性、依赖图无环；
  7. 真实拓扑检查（`modify` 路径必须存在，`create` 路径不能已存在）。

### 7.3 `review`（Gate 2 语义审查门禁）
- **核心定位**：只读 Reviewer 独立执行防幻觉、正向覆盖率与 ADR 红线审查。
- **模式**：
  - **Plan Review**：审查任务切片是否完整覆盖 PRD/规格，是否发明未定义实体；
  - **Code Review**：审查 Dev 提交的代码变更是否超出契约爆炸半径，是否遵守 ADR；
  - **Arbitration**：当 Dev 在 `02` Section 6 提交 Appeal Request 时，独立裁决 `CODE_BUG` / `TEST_BUG` / `SPEC_AMBIGUITY`（见 `review/references/arbitration.md`）。
- **裁决**：输出包含行号证据的审计发现；普通审查给出 `PASS` / `REQUEST CHANGES` / `BLOCKED`，仲裁给出上述三类之一。

### 7.4 `dev`（开发角色）
- **核心职责**：在契约白名单内高质量实现业务，控制复杂度。
- **核心铁律**：
  - 严禁越界修改 `touch_files` 之外的文件；严禁修改 `tests/acceptance/**`；
  - **单函数圈复杂度必须控制在 $V(G) \le 10$ 以内**；超标必须运用重构模式拆分；
  - 跑通 `dod` 自测命令，填写 `02-dev-workspace.md`；
  - 全部自测通过后，勾选 `- [x] WAITING_FOR_QA` 触发交接。

### 7.5 `qa`（本地开发阶段测试）
- **核心职责**：专注本地开发阶段测试，涵盖集成测试、基于 BDD 模式的端到端测试、变异测试（MSI $\ge 80\%$）、代码静态分析（本地 Lint 与圈复杂度分析）、自主决定调用 `review` skill 评审代码规范（可读性与可维护性）、针对不同项目类型自主引入知名开源工具，并在 `03-qa-verification.md` 记录本地测试证据与裁决。
- **核心铁律**：
  - 严禁修改业务源码 `src/**`；可写范围为 `tests/acceptance/**`、`tests/integration/**` 与 `tasks/<task-id>/03-qa-verification.md`；
  - **集成测试**：在 `tests/integration/` 编写验证跨模块接口契约与协作行为的集成用例；
  - **BDD 端到端测试**：依据 `01-contract.md` Section 4 BDD 场景与 `dod.edge_cases` 在 `tests/acceptance/` 编写黑盒验收与 E2E 测试；
  - **静态分析与圈复杂度**：本地引入代码检查工具（flake8、ruff、eslint 等）与复杂度分析工具（lizard、radon 等），确保修改函数单函数 $V(G) \le 10$，严禁 $V(G) > 15$，且严格执行基本路径测试基线（$\text{Test Cases} \ge V(G)$）；
  - **自主调用 review 技能**：自行决定调用 `review` skill 评估代码可读性、代码规范与可维护性；
  - **变异测试杀伤力基线**：针对不同项目栈自主引入知名工具（`mutmut`、`Stryker`、`go-mutesting`、`PITest`、`cargo-mutants`），击杀存活弱断言，确保 $\text{MSI} \ge 80\%$（核心模块 $\ge 90\%$）且无关键逻辑变异体存活；
  - 在 `03` 中记录完整执行证据与度量表，二选一勾选 `QA_PASSED` 或 `REWORK_REQUIRED`；
  - **证据 provenance**：Section 5 记录真实 artifact 路径与 SHA-256；`Equivalent > 0` 时填写等价理由；`01-contract.md` 的 `risk_level: core` 任务使用 90% MSI 阈值；
  - **本地 Gate 3 预检**：`qa` skill 自带 `scripts/verification_linter.py`（与 quality-engineering 审计器逐字节一致的 stdlib 副本）；在填完 `03` 后、下裁决前运行：
    ```bash
    python .agents/skills/qa/scripts/verification_linter.py --tasks-dir ./tasks --json
    ```
    有真实复杂度 artifact 时可加 `--actual-complexity <report> --require-actual-complexity` 做交叉核验；本地预检是 advisory，CI Gate 3 仍是权威。收到 Appeal 时先等待仲裁，不要单方面再次 `REWORK_REQUIRED`。
  - **与 `test-engineering` 的边界**：跨任务的测试策略、测试设计方法与数据/环境/flakiness 策略由 `test-engineering` 维护；`qa` 只负责当前任务的验收测试执行、证据记录与唯一裁决。
  - **读取项目测试策略**：测试设计前先只读读取项目测试策略（默认路径由角色规则固定；文件不存在时从 `test-engineering` 技能内置模板创建，不能假设仓库已带该文件），在 `03` 的测试设计摘要中记录 `strategy:` 引用；策略缺失时按 `baseline` 标注并沿用现有约定，不得凭空发明测试标准。

### 7.6 `quality-engineering`（CI 流水线构建与多阶段测试门禁）
- **核心职责**：构建 CI 流水线，确保测试环境隔离与就绪，管理代码合并前测试与合并后测试，权威拥有并维护全套 CI 工作流模板与 CI 门禁脚本（`complexity_check.py`、`verification_linter.py`、`quality-gate.yml` 等）。
- **核心任务**：
  - **测试环境就绪**：搭建与验证隔离、可复现的测试容器/沙箱环境，验证外部依赖、运行时版本、服务 Mock 与网络拓扑；
  - **代码合并前测试（Pre-merge PR 自动化门禁）**：在拉取请求阶段编排执行权威流水线：
    1. Gate 1 Plan Linter 任务契约与 BDD 规范检查；
    2. RBAC 角色越权审计（拦截 Dev 改测试、QA 改源码）；
    3. 圈复杂度静态门禁（调用基于 Tree-sitter / Lizard 多语言解析的 `complexity_check.py` 严格校验 $V(G) \le 10$，拦截 $V(G) > 15$）；
    4. 验收与集成测试套件执行（100% 通过要求）；
    5. Gate 3 验收交叉审查（调用 `verification_linter.py --actual-complexity ... --require-actual-complexity`，将 `03` 的 V(G) 与真实 AST artifact 核对，并核查基本路径覆盖与 MSI $\ge 80\%$，core 为 90%）。
  - **代码合并后测试（Post-merge 流水线）**：主干合入后执行全量主干回归测试、按需手动触发规格收敛（Converge）、持续追踪变异基线与性能 Benchmark；
  - **CI 资产与工具唯一归属**：权威维护 CI 工作流模板（`quality-gate.yml`、`plan-gate.yml`、`rbac-gate.yml`）与确定性门禁检查工具（`complexity_check.py`、`verification_linter.py`、`tools/mutation_gate.py`）。
- **与 `test-engineering` 的边界**：仓库级测试策略、测试设计方法与测试数据/环境/flakiness 策略由 `test-engineering` 维护；`quality-engineering` 负责把这些标准落成 CI 流水线、环境与门禁，不改写测试方法学本身。

### 7.7 `converge`（规格收敛）
- **核心职责**：在任务达到 `QA_PASSED` 后，闭环写回规格并归档。
- **机制**：
  - 读取 `02-dev-workspace.md` 中的偏差表，以 append-only 方式追加至 `.specs/02-tech-spec.md` 末尾的 Converged changes 章节；
  - 更新 `04-process.md` 状态为 `CONVERGED`；
  - 将任务包安全归档至 `tasks/archive/<task-id>/`。

### 7.8 `test-engineering`（全局测试体系）
- **核心定位**：跨任务的全局测试方法学与独立测试设计评审，不进入单任务执行链路。
- **使用时机**：
  - 建立、修订或批准仓库级测试策略与质量属性；
  - 针对某类风险、技术栈或功能域选择测试层级（unit / integration / contract / acceptance / E2E）与设计方法（等价类、边界值、判定表、状态迁移、成对组合等）；
  - 定义测试数据、测试环境、测试替身与 flakiness 治理策略；
  - 在 QA 执行前，独立评审某个任务或特性的**测试设计**（设计评审，不是验收）；
  - 定义测试指标、测试证据口径并向 `qa` 与 `quality-engineering` 交接。
- **不该使用的时机**：单任务验收、证据采集与唯一裁决（归 `qa`）；CI 流水线、门禁与运行环境（归 `quality-engineering`）；Gate 2 语义审查与代码审查（归 `review`）；实现与任务切片（归 `dev` 与规划技能）。
- **产出**：
  - 商定的测试策略文档：目标、质量属性、风险矩阵、测试层级与技术选型、数据/环境/替身/flakiness 策略、指标、RACI 与落地路线图。默认输出路径由角色规则固定（本仓库示例为 [`testing-strategy.md`](testing-strategy.md)，采用方可覆盖为规格链路径）；若项目还没有策略文件，必须从技能内置的 `assets/templates/test-strategy.template.md` 生成，不能假设安装包已附带某个策略文件；
  - 独立测试设计评审记录：分级发现 + 唯一标记 `DESIGN_READY`（无 blocker/major）或 `DESIGN_GAPS`（存在阻塞/重要缺口）。
- **边界**：`test-engineering` 只写商定的测试策略文档与测试设计评审记录；不接收单任务、不写测试或 `03-qa-verification.md`、不改源码、不运行或替代 CI 门禁。`DESIGN_READY` / `DESIGN_GAPS` 是设计质量意见，**不是** `QA_PASSED` / `REWORK_REQUIRED`，也不是 CI 门禁结果。
- **诚实边界**：该技能仅提示词驱动，无法强制实施标准或角色隔离；权威门禁仍来自 CI 与分支保护。

---

## 8. 四文档与角色边界

```text
tasks/<task-id>/
├── 01-contract.md          # Planner 拥有：只读契约（权威 frontmatter + BDD 场景）
├── 02-dev-workspace.md     # Dev 拥有：实现说明、自测记录、偏差表、交接标记
├── 03-qa-verification.md   # QA 拥有：黑盒用例、复杂度表、变异得分、唯一裁决
└── 04-process.md           # 工具/CI 拥有：派生状态与审计日志（禁止手工编辑）
```

### 8.1 角色职责与读写隔离矩阵

| 角色 | 可写路径 | 严禁触碰路径 | 核心质量指标 |
| :--- | :--- | :--- | :--- |
| **Planner** | `tasks/<id>/01-contract.md` | `src/**`, `tests/**`, `04` | 黄金切片、Given-When-Then BDD 规范 |
| **Dev** | `src/**` (白名单), `02-dev-workspace.md` | `tests/acceptance/**`, `01`, `03`, `04` | 单函数圈复杂度 $V(G) \le 10$, DoD 全通 |
| **QA** | `tests/acceptance/**`, `tests/integration/**`, `03-qa-verification.md` | `src/**`, `01`, `02`, `04` | 本地集成/BDD E2E、用例数 $\ge V(G)$, 变异得分 $\text{MSI} \ge 80\%$ |
| **Quality Engineering** | CI 工作流 (`.github/workflows/*`, `templates/ci/*`) | `tasks/`, `src/`, `tests/` (CI 中只读门禁与回归) | 测试环境就绪、CI 门禁与回归全绿、Gate 3 审计全通 |
| **Test Engineering** | 商定的测试策略文档、测试设计评审记录 | `tasks/`, `src/`, `tests/`, CI 产物（只读） | 测试策略覆盖、设计方法与风险匹配、`DESIGN_READY`/`DESIGN_GAPS` |
| **Reviewer** | 只读（输出 Review 报告至独立终端/文件） | 任何工程与任务产物 | 反幻觉、正向覆盖率、ADR 架构红线 |

---

## 9. 强制与安全（诚实模型）

系统采用诚实的四层防护模型（L0–L3）：

| 级别 | 机制 | 适用环境 | 防护力度与保证 |
| :--- | :--- | :--- | :--- |
| **L0** | 提示词规则（`AGENTS.md`、角色 rules、SKILL.md） | 所有 AI Agent / 宿主 | 建议性引导；Agent 易产生幻觉或越界 |
| **L1** | 本地静态预检脚本（`plan_linter.py`、`verification_linter.py`） | 本地开发环境 | 快速排错；可被开发者手动跳过 |
| **L2** | CI 自动化门禁流水线（`tools/rbac_audit.py` + `quality-gate.yml`） | Git 托管平台（GitHub/GitLab） | **绝对权威强制**；基于 commit diff，不可篡改 |
| **L3** | 分支保护规则（Protected Branches & Required Checks） | 代码仓库设置 | 最终安全屏障；无绿标禁止 Merge |

> **严禁声称**：切勿宣称本地提示词能实现“物理强制隔离”。团队的绝对安全必须建立在 L2 CI RBAC 审计与 L3 分支保护之上。

---

## 10. 故障排查

| 故障现象 | 根因分析 | 推荐处理步骤 |
| :--- | :--- | :--- |
| Gate 1 报 `BDD_MISSING_PRECONDITION` / `BDD_MISSING_ACTION` | `01-contract.md` 中 `edge_cases` 未严格遵循 Given-When-Then 格式 | 检查每条 edge_case，修正为 `"Given ..., When ..., Then ..."` 三段式 |
| Gate 1 报 `FORBIDDEN_TOUCH_FILE` | `touch_files` 中包含了 `tests/acceptance/` | 移除验收测试路径，验收测试专属于 QA 角色 |
| Gate 3 报 `COMPLEXITY_MISSING_SECTION` | 勾选了 `QA_PASSED` 但 `03` 未包含或未填复杂度表 | 在 `03` 第 3 节填写修改函数的圈复杂度与路径映射 |
| Gate 3 报 `COMPLEXITY_BASIS_PATH_INSUFFICIENT` | 验收测试用例数量少于函数圈复杂度 $V(G)$ | 补充独立路径的黑盒测试用例，使 $\text{用例数} \ge V(G)$ |
| Gate 3 报 `COMPLEXITY_MISMATCH_WITH_AST` / `COMPLEXITY_FUNCTION_MISSING_IN_03` | `03` 的 V(G) 与真实 AST 不一致，或漏列了 touch_files 中的函数 | 用 `complexity_check.py --json` 的 `functions` 重填 Section 3 |
| Gate 3 报 `QA_INVALID_MSI_SCORE` | 变异得分低于 80%（core 为 90%） | 检查未杀伤的变异体，消除弱断言，补充强校验断言并重新变异 |
| Gate 3 报 `EVIDENCE_MISSING_ARTIFACT` / `EVIDENCE_HASH_INVALID` | 开启了 provenance 但 artifact 路径/哈希缺失或不匹配 | 在 `03` Section 5 写入真实 artifact 路径与 SHA-256 |
| CI RBAC 报 `DEV_EDITED_ACCEPTANCE_TESTS` / `QA_EDITED_SOURCE` | Dev 改了验收测试或 QA 改了源码 | revert 越权改动，按角色边界重新提交 |
| 变异 job 报 `MUTATION_REPORT_MISSING` / `MUTATION_THRESHOLD_FAILED` | `MUTATION_COMMAND` 未配置/未生成报告，或 MSI 不足 | 配置归一化报告；击杀存活变异体直到 MSI 达标 |
| `converge` 拒绝执行（exit 1） | `03` 未勾选 `QA_PASSED`，或 `02` 偏差表为空 | 确保 QA 验收通过，并在 `02` 偏差表中写明偏差记录（无偏差填 `None` 行） |

---

## 11. 验证你的改动

在向代码库提交变更前，运行以下确定性验证套件：

```bash
# 1. 运行现代质量工程与全部核心单元测试
python -m unittest discover -s tests/unit -p "test_*.py"

# 2. 运行 Gate 1 规划期静态检查
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --json

# 3. 运行圈复杂度静态检查（McCabe V(G) <= 10；无 src/ 时需显式传 --src-dir）
python .agents/skills/quality-engineering/scripts/complexity_check.py --src-dir src --json

# 4. 运行 Gate 3 验收期静态检查（--actual-complexity 用于交叉核验）
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir tasks --actual-complexity artifacts/complexity-report.json \
  --require-actual-complexity --strict --json

# 5. 运行 RBAC 角色边界审计
python tools/rbac_audit.py --base HEAD~1 --role dev --tasks-dir tasks

# 6. 运行变异硬门禁（需要项目提供 MUTATION_COMMAND 与归一化报告）
python tools/mutation_gate.py check --report artifacts/mutation-report.json --min-msi 80
```

---

## 12. 相关文档

- [英文技能索引与流水线说明（README.md）](../.agents/skills/README.md)
- [技能类别索引（skills/README.md）](../skills/README.md)
- [Brownfield 增量变更与规格收敛指南](brownfield-convergence.zh-CN.md)
- [CI 自动化门禁配置与工作流模板](../templates/ci/README.md)
- [多语言 CI 参考模板（Stack Profiles）](ci-stack-profiles.zh-CN.md)
- [门禁加固改造执行手册](skills-remediation.zh-CN.md)
- [宿主兼容性与工具安装指南](skills-compatibility.md)
- [角色规则与权威强制模型](../.agents/rules/enforcement.md)

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
