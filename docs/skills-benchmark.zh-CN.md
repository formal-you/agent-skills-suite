# 技能套件评分与开源对标（2026-10，v3.1.0 基线）

> **评分对象**：本仓库发布树（`skills/<category>/<name>/` 可安装布局：十一个 workflow 技能
> prd-generator、spec-generator、task-decomposition、change、plan-linter、review、dev、qa、quality-engineering、test-engineering、converge，
> 外加一个 platform 助手 diagnose-windows-sandbox-acl；同时提供 `.claude-plugin/` 插件与市场清单），
> 评审基线为 v3.1.0 发布包；`.agents/skills/` 是 AGENTS 发现机制的镜像布局。  
> **对比对象**：当前公开的知名 spec-driven / agent-workflow 开源项目。  
> **重要声明**：这不是严谨的 benchmark。分数是基于公开 README/文档、仓库元数据与本仓库实测结果
> 做出的**主观工程判断**；没有对竞品做同等深度的 hands-on 评测。星标数为 2026-10-18 的 GitHub
> API 快照，只代表关注度，不代表质量。  

> **v3.1.0 更新（2026-10-18）**：分发形态升级为可安装插件包，技能改为自包含（只引用自身目录内的
> 文件），角色规则迁移到 `.agents/rules/*.md`（含 `enforcement.md`）并降为可选套件层；评分与证据
> 相应更新，D6 4.4、D7 1.4，加权总分 4.16。
>
> **v3.2.0 更新（2026-10-19）**：门禁真实性加固（Gate 3 与真实 AST artifact 交叉核验、变异测试
> fail-closed、plan-linter 单一职责、错误码注册表与 triage 路由、证据 provenance、Appeal/仲裁）。
> 本文的评分口径与基线仍为 v3.1.0；v3.2.0 的加固作为"确定性/防作弊"维度的事实性提升，不重打分。
>
> **v3.3.0 更新（2026-10-19）**：新增 `test-engineering` 全局测试方法学技能（测试策略、风险驱动的
> 测试设计方法、测试数据/环境与 flakiness 策略、测试指标、独立测试设计评审）；它不接收单任务、
> 不写测试与 `03`、不运行 CI 门禁。本文的评分口径与基线仍为 v3.1.0，**不重新打分**；下面的组件
> 评分表仍只覆盖 v3.1.0 基线的十个技能，`test-engineering` 作为全局方法学技能不进入本表。
>
> **v3.4.x–v5.0.0 当前状态（2026-10-19）**：v3.4.0 接入全局测试策略，v3.4.1 QA 自带 Gate 3 预检，
> v3.4.2–v3.4.4 固化并升级 AGENTS.md 的 skill-change workflow；v5.0.0 硬约束 BDD 契约、Gate 3 交叉核验
> 真实变异报告、PR 阶段真实变异与单任务分支隔离。本文仍是 **v3.1.0 评分快照**，不重新打分；
> v4.0.1 为 **425 passed, 1 skipped**，v5.0.0 当前为 **500 passed, 1 skipped**（v3.1.0 基线为 301 passed, 1 skipped）。

---

## 1. 结论先行

在本套评分口径下：**本套件综合 4.16 / 5.0（v3.1.0），已进入头部区间：确定性、角色隔离与 QA 独立性领先，收敛闭环补齐；生态仍是结构性短板。**

> 2026-10-18 v3.1.0 更新：发布形态从"仓库快照"升级为"可安装插件包"，技能改为自包含，规则层变为可选。

- **插件分发**：`.claude-plugin/` 提供 Claude Code 插件与市场清单；Codex 插件市场、GitHub Copilot 插件、
  Gemini CLI `--path skills/workflow|platform`、`npx skills`、`tools/install_skills.py` 与
  `tools/quickstart.py` 覆盖其余宿主与采用路径；
- **自包含技能**：每个 `SKILL.md` 只引用自身技能目录内的文件；插件安装只加载技能目录，跨目录引用已移除；
- **规则层可选**：角色规则位于 `.agents/rules/*.md`（含 `enforcement.md`，替代旧的 `docs/agent-rules.md`），
  技能按"存在则遵循"的方式引用，没有规则层也能独立工作；
- **brownfield 增量**：`change` 技能（proposal → 单个任务包 → archive）+ standards 提取，不写 PRD 也能接小需求；
- **规格收敛**：`QA_PASSED` 后 `converge` 把实现偏差 append-only 写回 `.specs/02-tech-spec.md`，规格变成活文档；
- **Gate 2 启发式**：锚点覆盖率矩阵、真实路径拓扑、change proposal 一致性由 plan-linter 3.x 预先计算；
- **分发与 CI**：`tools/quickstart.py` 一条命令采用，`.agents/skills/quality-engineering/assets/templates/ci/` 三个可直接复制的 GitHub Actions（`quality-gate.yml`、`plan-gate.yml`、`rbac-gate.yml`）。

- **强项**：端到端流程完整（想法 → PRD → 规格 → 任务 → Gate 1/2 → Dev → QA → 收敛）；确定性
  Gate 1 + CI RBAC 审计；四文档契约与角色隔离；brownfield 增量与活规格；自包含技能与插件分发；
  prompt-first、可迁移、无引擎依赖；v3.1.0 基线发布包 301 个黑盒单元测试（1 skip），v4.0.1
  为 425 个（1 skip），当前 v5.0.0 为 500 个（1 skip）。
- **仍弱**：生态与公开采用接近零；插件清单已就绪，但尚未进入公开市场，没有公开示例库 / 社区 /
  `skills-ref validate`；Gate 2 仍是人工提示词；没有 per-task 子代理编排；没有真实仓库上的公开 A/B 数据。
- **最接近的竞品**：GitHub Spec Kit（流程与生态）与 OpenSpec（brownfield 模型），cc-sdd（Agent Skills
  形态）。v3.1.0 之后我们在**确定性门禁、角色隔离、QA 独立性、收敛闭环**上更强或持平，在**生态、社区、
  公开市场采用、per-task 编排**上仍明显落后。

加权总分（同一口径，1–5）：

```text
本套件 (v3.1.0)      4.16  ████████▍
GitHub Spec Kit      4.05  ████████▏
cc-sdd               3.85  ███████▋
BMAD-METHOD          3.78  ███████▌
OpenSpec             3.70  ███████▍
Agent OS             3.23  ██████▍
Taskmaster           3.08  ██████▏
```

> 与 v2 相比：D1 +0.3（brownfield + 收敛）、D2 +0.2（启发式）、D5 +0.3（CI/分发/测试）；
> 与 v3.0 相比：D6 +0.2（插件安装与文档）、D7 +0.2（可安装、可被发现），加权分提升 0.04。
> 这是自评，不是第三方基准；生态一项仍把上限压在 4.2 附近。

> Anthropic `skills` 仓库（181k stars）不是流程框架，而是 Agent Skills 格式与生态的基准，
> 不参与同一张流程榜；它在"格式兼容/发现机制"上是我们必须对齐的对象。

---

## 2. 评分口径

### 2.1 维度与权重

| 维度 | 权重 | 评什么 |
| :--- | ---: | :--- |
| D1 流程完整度 | 20% | 是否覆盖想法/变更 → 需求 → 规格 → 任务 → 实施 → 验收的闭环 |
| D2 确定性可验证性 | 15% | 是否有机器可执行的契约、门禁、证据与退出码，而不是只靠提示词 |
| D3 角色隔离与防作弊 | 15% | Dev/QA/Planner 写权限是否分离，是否有 CI/权限层的强约束 |
| D4 宿主可移植性 | 10% | 是否跨 Codex/Antigravity/Claude Code/DSH，是否依赖某宿主私有原语 |
| D5 工程化质量 | 10% | 测试、版本、安装、目录规范、可维护性 |
| D6 上手与文档 | 10% | 首次使用成本、文档清晰度、示例与安装体验 |
| D7 生态与采用度 | 10% | 公开采用、插件/技能市场、社区、集成数量 |
| D8 扩展与定制 | 5% | 模板、阈值、工作流、角色/产物是否可替换 |
| D9 领域中立性 | 5% | 是否把电商/某技术栈/某云厂商当作默认答案 |

### 2.2 分值锚点

| 分值 | 含义 |
| ---: | :--- |
| 1 | 基本缺失或只适用于单一场景 |
| 2 | 有概念，但不可靠/难用/高度绑定 |
| 3 | 可用，达到同类项目的中位水平 |
| 4 | 明显优于多数同类，仍有清晰短板 |
| 5 | 同类最佳，且经过大规模验证 |

### 2.3 数据与证据

- 本套件（发布树）：`skills/` 可安装布局（十一个 workflow 技能 + `diagnose-windows-sandbox-acl`）、
  `.claude-plugin/` 插件与市场清单、`tools/`、`.agents/skills/quality-engineering/assets/templates/ci/`、`docs/`、`tests/unit/`；本文引用的
  v3.1.0 基线为 **301 个黑盒单元测试（1 skip）**，v4.0.1 为 **425 个（1 skip）**，当前 v5.0.0 为 **500 个（1 skip）**。
- 上游开发仓库另有完整测试套件（历史数据：539 个单元测试 + 109 个 E2E），**不随发布包分发**，
  仅作上游证据，不计入发布基线（详见 [技能使用指南](skills-guide.zh-CN.md)、[brownfield 与收敛](brownfield-convergence.zh-CN.md)、
  [宿主兼容性](skills-compatibility.md) 与 [技能布局说明](../.agents/skills/README.md)）。
- 竞品：GitHub README/官方文档（见文末"数据来源"）；星标/GitHub API 快照见 §6。
- 所有竞品都只做文档级对照，未在相同仓库、相同任务上做 A/B。

---

## 3. 维度评分矩阵

| 项目 | D1 流程 20% | D2 可验证 15% | D3 隔离 15% | D4 可移植 10% | D5 工程化 10% | D6 上手 10% | D7 生态 10% | D8 扩展 5% | D9 中立 5% | **加权** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **本套件 v3.1.0** | 4.8 | 4.7 | 4.0 | 4.5 | 4.3 | 4.4 | 1.4 | 4.2 | 4.5 | **4.16** |
| GitHub Spec Kit | 4.5 | 3.0 | 2.0 | 5.0 | 4.5 | 5.0 | 5.0 | 4.5 | 4.5 | **4.05** |
| cc-sdd | 4.5 | 3.5 | 3.0 | 5.0 | 4.0 | 4.0 | 3.0 | 3.5 | 4.0 | **3.85** |
| BMAD-METHOD | 4.5 | 2.5 | 3.5 | 4.0 | 4.0 | 3.0 | 4.5 | 4.5 | 4.0 | **3.78** |
| OpenSpec | 4.0 | 3.0 | 1.5 | 4.5 | 4.5 | 4.5 | 4.5 | 4.0 | 4.5 | **3.70** |
| Agent OS | 3.0 | 2.5 | 2.0 | 4.0 | 3.5 | 4.5 | 3.5 | 4.0 | 4.0 | **3.23** |
| Taskmaster | 2.5 | 2.5 | 1.0 | 4.0 | 4.0 | 4.5 | 4.0 | 3.5 | 4.5 | **3.08** |

读法：分数是相对排序，不是绝对能力证明。一个 3.0 的项目可能在某些单点上比 4.5 的更强。

---

## 4. 本套件的组件评分

组件分为定性 1–5，不与上表权重直接相加；用于回答"v3.1.0 基线中的十个 workflow 技能各自值多少"
（`diagnose-windows-sandbox-acl` 只做环境诊断，不参与流程评分）。

| 组件 | 分数 | 理由 | 主要短板 |
| :--- | ---: | :--- | :--- |
| `prd-generator` | 4.0 | 输入/输出清晰、模板与 lint 完整、可选引擎 | 没有 brownfield/变更入口；确定性引擎有领域预制风险 |
| `spec-generator` | 3.8 | ADR + 技术规格结构完整、模板中立化 | 语义校验弱；没有"实现→收敛"回路 |
| `task-decomposition` | 4.4 | frontmatter 契约、四文档、角色生命周期、脚手架 | 强依赖 01 质量；无自动 scope 检查 |
| `plan-linter` | 4.7 | 可执行的 Gate 1、JSON/config、覆盖率矩阵与真实路径拓扑启发式 | Gate 2 仍是人工；解析器是 YAML 子集；覆盖率是锚点级 |
| `review` | 4.3 | 明确 plan/code 两种模式、分级发现与唯一裁决、只读边界 | 语义审查无法自动化；依赖 reviewer 独立性 |
| `dev` | 4.0 | 职责与交接边界清楚、可与任意项目命令配合 | 无自动 `git diff` 越界检查；依赖项目测试栈 |
| `qa` | 4.0 | 独立黑盒、证据、裁决、返工清晰 | 无证据采集/覆盖率工具；无 per-task reviewer 编排 |
| `change` | 4.2 | brownfield proposal→apply→archive、standards 隐式约束、micro 预算 | delta 仍需 Planner 手写；standards 是启发式而非语义理解 |
| `quality-engineering` | 4.6 | CI 流水线构建、环境治理、合并前/后自动化门禁、Gate 3 审计（`verification_linter.py`）与圈复杂度检查（`complexity_check.py`） | 分布式复杂环境调度与混沌工程待深入 |
| `converge` | 4.1 | append-only 写回、幂等 marker、归档与指纹漂移检测 | 依赖 Dev 如实填偏差表；无自动语义冲突消解 |
| 可选引擎 | 3.0 | 确定性生成/回放对回归有价值 | 领域启发式与预制内容可能污染输出；默认不应依赖 |
| 工具/文档 | 4.5 | 插件清单（Claude Code/Codex/Copilot）、自包含技能、兼容矩阵、中文指南、RBAC/安装工具、quickstart 分发 + CI 模板、301/425 单元测试（基线/当前） | 公开市场采用与社区仍为零；无公开 A/B；示例库待补 |

**一句话**：最强的仍是 `plan-linter` 与 `task-decomposition`；v3.1.0 的插件分发与自包含技能
把"装得上、可独立加载"补齐；最需要继续补的是生态/公开采用，而不是再加技能。

---

## 5. 逐项目对比

### 5.1 GitHub Spec Kit — 4.05（流程与生态标杆）

- **强项**：`constitution → specify → plan → tasks → implement → converge` 的完整 SDD 流程；
  bug fixing / idea assessment / 自定义 process 多入口；CLI、扩展与 workflow overlay；
  多 coding agent 集成；成熟文档与巨大生态。
- **相对我们**：强在生态、分发、社区与多 agent 集成；v3.1.0 之后我们在 brownfield 与收敛上已基本对齐
  （`change` + `converge`），并在确定性 Gate、角色隔离、CI 防作弊、QA 独立性上领先；仍弱在公开市场、
  插件/扩展生态与公开采用。
- **可借鉴**：`converge` 回路、bug/idea 入口、扩展/插件模型、`specify init` 式一键初始化。

### 5.2 cc-sdd — 3.85（Agent Skills 形态最接近）

- **强项**：17 个 Agent Skills 覆盖 discovery → requirements → design → tasks → implementation；
  8 个宿主（Claude Code、Codex、Cursor、Copilot、Windsurf、OpenCode、Gemini CLI、Antigravity）；
  有 per-task implementer/reviewer、TDD（RED→GREEN）、boundary-first 设计、多 spec 批量。
- **相对我们**：强在多 agent 编排、宿主覆盖与分发；弱在确定性 Gate 1、四文档 RBAC 与 QA 签署
  的可执行约束。我们是"契约 + 门禁优先"，它是"技能 + 自主实现优先"。
- **可借鉴**：per-task 独立 reviewer、边界检查、宿主安装体验。

### 5.3 BMAD-METHOD — 3.78（角色/敏捷最完整）

- **强项**：产品、架构、UX、开发、测试的专业视角；结构化工作流、角色协作、模块与 Builder、
  Test Architect 等扩展；社区成熟；v6 稳定 / v7 skills 预览。
- **相对我们**：角色深度与生态强；确定性验证与 CI 强制弱；体系更重、上手更陡。
- **可借鉴**：角色研讨的深度、模块化扩展、企业测试插件思路。

### 5.4 OpenSpec — 3.70（brownfield 与迭代最强）

- **强项**：specs/changes/archive 的增量模型；`/opsx:propose → apply → archive`；
  对 brownfield 友好；stores 支持跨仓库规格共享；轻量、易上手；生态增长快。
- **相对我们**：brownfield 模型与轻量体验仍更成熟（跨仓库 stores、大社区）；v3.1.0 的 `change` 已覆盖
  proposal → apply → archive 的核心，但生态与工具成熟度仍落后；角色隔离、确定性门禁、QA 独立性我们更强。
- **可借鉴**：change proposal / archive 模型、brownfield 默认路径。

### 5.5 Agent OS — 3.23（标准注入强，流程短）

- **强项**：从代码库提取 standards、按任务注入 standards、shape spec；与 Claude Code/Cursor/
  Antigravity 配合；上手轻。
- **相对我们**：standards discovery 强；生命周期只到 spec，没有实施/验收门禁。
- **可借鉴**：standards 发现/部署机制，可补我们的 brownfield 短板。

### 5.6 Taskmaster — 3.08（任务管理强，流程短）

- **强项**：PRD 解析、任务树、复杂度分析、expand、next-task、15 个标准工具；任何 AI chat 可用。
- **相对我们**：任务 UX 与复杂度分析强；没有规格/架构/QA 闭环与角色隔离。
- **可借鉴**：复杂度分析、任务状态 UX、编辑器集成。

### 5.7 Anthropic `skills` — 生态基准，不参与流程排名

- 定义了 Agent Skills 的目录/发现/渐进披露标准；大量生产级技能示例（Apache 2.0）。
- 我们与它在格式上对齐（SKILL.md frontmatter、references、assets、scripts），但没有配套的
  `skills-ref validate`、公开插件市场与公开示例库——这是生态分低的重要原因。

---

## 6. 生态规模快照（2026-10-18）

| 项目 | Stars | 许可证（README/API） | 备注 |
| :--- | ---: | :--- | :--- |
| anthropics/skills | 181,784 | 多数 Apache-2.0 | Agent Skills 生态基准 |
| github/spec-kit | 141,675 | MIT | SDD 流程与 CLI |
| Fission-AI/OpenSpec | 72,249 | MIT | brownfield spec 变更 |
| bmad-code-org/BMAD-METHOD | 54,269 | MIT（README 标注） | 敏捷角色/工作流 |
| eyaltoledano/claude-task-master | 28,237 | MIT + Commons Clause | 任务管理 |
| buildermethods/agent-os | 5,513 | MIT | standards + spec |
| gotalab/cc-sdd | 3,720 | MIT | Agent Skills + 8 宿主 |
| 本套件 | 本地项目，暂无公开 star 数据 | MIT（本仓库） | v5.0.0 插件清单就绪；未发布到公开市场 |

> 星标来自 GitHub API 快照，会持续变化；它衡量关注度，不衡量工程质量或适用性。

---

## 7. 我们赢在哪、输在哪

### 7.1 明确领先

1. **确定性门禁**：Gate 1 是可执行脚本（frontmatter 契约、DAG、blast radius、DoD、占位符），并新增
   锚点覆盖率矩阵与反向路径拓扑；有 JSON/配置/退出码，不依赖模型"自觉"。
2. **角色隔离与防作弊**：四文档 + 写权限矩阵 + CI `rbac_audit.py`；角色规则集中在 `.agents/rules/*.md`
   （含 `enforcement.md`），作为可选套件层，技能自身不依赖它也能工作。
3. **QA 独立性**：QA 技能强制黑盒矩阵、证据、唯一裁决与返工 trace；多数竞品没有同等的 QA 契约。
4. **活规格与收敛**：`converge` 以 append-only 记录 + marker + 指纹漂移检测把实现结果写回规格，
   并归档任务包与 change；这不是文档承诺，是可执行脚本 + 幂等语义。
5. **自包含技能 + 插件分发**：每个 `SKILL.md` 只引用自身目录内的文件，插件安装只加载技能目录；
   发布包同时提供 `.claude-plugin/`（Claude Code 插件与市场清单）、Codex 插件市场、GitHub Copilot
   插件、Gemini CLI `--path skills/workflow|platform`、`npx skills`、`tools/install_skills.py` 与
   `tools/quickstart.py`。
6. **prompt-first 可迁移**：技能不 import 引擎、可复制到仓库外；引擎可选；无 Python 也有手工路径。

### 7.2 明确落后

1. **生态与公开采用**：插件清单已交付，但还没有发布到公共插件市场，没有公开示例库、社区与
   `skills-ref validate`；`quickstart` / `install_skills.py` 只解决"能不能装"，不解决"有多少人在用"。
2. **多 agent 编排**：没有 per-task implementer/reviewer 的独立子代理编排（cc-sdd/BMAD 更强）。
3. **上手成本**：需要理解四文档、十一个 workflow 技能（外加一个 platform 助手）、两层门禁与配置阈值；仍比 OpenSpec/Taskmaster 重。
4. **真实证据**：上游开发仓库有内部单仓库试点记录（未随发布包分发），但仍没有公开任务集 A/B、
   跨项目返工率数据；当前评分仍以自评为主。
5. **brownfield 深度**：`change` 的 delta 仍需 Planner 手写，standards 提取是确定性启发式而非代码语义
   理解；OpenSpec 的跨仓库 stores 与迭代体验仍更成熟。

---

## 8. v3.1.0 交付情况与剩余路线

> 下列"提分"是同一评分口径下的粗略估计，不是承诺。

| 优先级 | 改进 | 状态 | 实际效果 |
| :--- | :--- | :--- | :--- |
| P0 | 插件分发 | **已交付 v3.1.0** | `.claude-plugin/` 清单 + Claude Code / Codex / GitHub Copilot 市场安装；D6 增益 |
| P0 | 自包含技能 | **已交付 v3.1.0** | 每个 `SKILL.md` 只引用自身目录；插件安装不再依赖跨目录文件 |
| P0 | brownfield / change 入口 | **已交付 v3** | `change` 技能 + standards 提取 + micro/standard 预算；D1 +0.3 |
| P0 | 分发与安装 | **已交付 v3** | `tools/quickstart.py` 一条命令 + `.agents/skills/quality-engineering/assets/templates/ci/` 三个 workflow；D6 +0.7 |
| P1 | 收敛循环 | **已交付 v3** | `converge` append-only 写回 + 归档 + 指纹检测；D1/D2 增益 |
| P1 | Gate 2 机器辅助 | **已交付 v3** | 覆盖率矩阵、反向拓扑、change 一致性；D2 +0.2 |
| P1 | 规则层迁移 | **已交付 v3.1.0** | `.agents/rules/*.md`（含 `enforcement.md`）替代 `docs/agent-rules.md`，成为可选套件层 |
| P2 | QA 自动化增强 | 未做 | 证据采集、覆盖率、scope diff、per-task reviewer 编排；约 +0.05 |
| P2 | 生态/公开采用 | 部分交付，公开采用未做（真正瓶颈） | 公开市场发布、示例库、社区、公开 A/B 仍未做；D7 需要 1.4 → 3+ |
| P2 | 评测基线 | 未做 | 真实仓库任务集上的 pass/失败/返工率与 A/B |

v3.1.0 的交付项已经做完：**3.90 → 4.16**。  
继续加技能最多到约 4.2；要冲 **4.3+**，必须让 D7（生态与采用）从 1.4 升到 3 左右——这靠公开
市场发布、示例库、真实采用与社区，不靠再写一个技能。这是评分结构决定的。

---

## 9. 最终判断

**v3.1.0 之后，本套件已经是一套可安装、自包含的 SDD 工具链，而不是 demo 技能集**：契约优先、
门禁可执行、角色可隔离、brownfield 可增量、实现结果可收敛、技能自包含且可插件安装、引擎可替换。
它当前最像"Spec Kit 的确定性门禁版 + OpenSpec 的增量模型 + 更严格的 QA 契约"；与头部的差距
已经从"功能缺失"收敛为"生态与采用"。

- **今天适合谁**：重视契约、可追溯、CI 防作弊的团队/仓库；已有规格需要持续演进、又不想每次重写 PRD
  的项目；希望以插件方式安装、同时保留确定性门禁的团队。
- **今天不适合谁**：需要成熟公共插件市场、大量现成示例与社区支持的团队；只想要轻量 prompt、快速
  原型、或不愿接受四文档与角色分工成本的用户。
- **下一步最值得做的一件事**：把 v5.0.0 发布到公共插件市场，配一个公开示例仓库，并持续公开真实
  任务上的通过/返工/收敛数据——先让 D7 从 1.4 往上走，这是 4.3+ 的门槛。

---

## 10. 数据来源与免责声明

- 本套件（发布树）：`skills/`（十一个 workflow + platform 可安装布局）、`.claude-plugin/`、`.agents/skills/`、
  `.agents/rules/`、`tools/`、`.agents/skills/quality-engineering/assets/templates/ci/`、`tests/unit/`；[技能使用指南](skills-guide.zh-CN.md)、
  [brownfield 与收敛](brownfield-convergence.zh-CN.md)、[宿主兼容性](skills-compatibility.md)、
  [技能布局说明](../.agents/skills/README.md)、[发布测试基线](../tests/unit/)。
- GitHub Spec Kit：https://github.com/github/spec-kit
- BMAD-METHOD：https://github.com/bmad-code-org/BMAD-METHOD
- Agent OS：https://github.com/buildermethods/agent-os
- OpenSpec：https://github.com/Fission-AI/OpenSpec
- Taskmaster：https://github.com/eyaltoledano/claude-task-master
- cc-sdd：https://github.com/gotalab/cc-sdd
- Anthropic Skills：https://github.com/anthropics/skills
- Agent Skills 标准：https://agentskills.io/specification
- 星标/许可证：GitHub REST API 快照（2026-10-18）。

**免责声明**：本文是工程判断，不是第三方认证或基准测试。竞品能力以其官方文档为准；本套件分数
包含作者对自己作品的批判性评估，但仍是主观打分。建议在真实任务集上做同口径 A/B 后再下结论。

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
