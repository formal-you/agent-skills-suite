# 技能套件评分与开源对标（2026-10）

> **评分对象**：本仓库 v2.0.0 技能套件（`.agents/skills` 七个技能 + `tools/` + 可选引擎），
> 评审基线为提交 `ba50e01` 之后的 `develop` 快照。  
> **对比对象**：当前公开的知名 spec-driven / agent-workflow 开源项目。  
> **重要声明**：这不是严谨的 benchmark。分数是基于公开 README/文档、仓库元数据与本仓库实测结果
> 做出的**主观工程判断**；没有对竞品做同等深度的 hands-on 评测。星标数为 2026-10-18 的 GitHub
> API 快照，只代表关注度，不代表质量。  

---

## 1. 结论先行

在本套评分口径下：**本套件综合 4.12 / 5.0（v3），已进入头部区间：确定性、角色隔离与 QA 独立性领先，收敛闭环补齐；生态仍是结构性短板。**

> 2026-10-18 v3 更新：v2 的两个最大缺口（brownfield、收敛循环）已补齐。

- **新增 brownfield 增量**：`change` 技能（proposal → 单个任务包 → archive）+ standards 提取，不写 PRD 也能接小需求；
- **新增规格收敛**：`QA_PASSED` 后 `converge` 把实现偏差 append-only 写回 `.specs/02-tech-spec.md`，规格变成活文档；
- **Gate 2 启发式**：锚点覆盖率矩阵、真实路径拓扑、change proposal 一致性由 plan-linter 3.x 预先计算；
- **分发与 CI**：`tools/quickstart.py` 一条命令采用，`templates/ci/` 两个可直接复制的 GitHub Actions。

- **强项**：端到端流程完整（想法 → PRD → 规格 → 任务 → Gate 1/2 → Dev → QA → 收敛）；确定性
  Gate 1 + CI RBAC 审计；四文档契约与角色隔离；brownfield 增量与活规格；prompt-first、可迁移、无引擎依赖；测试基线扎实。
- **仍弱**：生态与公开采用接近零；没有插件市场 / `skills-ref validate` / 公开示例库；Gate 2 仍是
  人工提示词；没有 per-task 子代理编排；没有真实仓库上的公开 A/B 数据。
- **最接近的竞品**：GitHub Spec Kit（流程与生态）与 OpenSpec（brownfield 模型），cc-sdd（Agent Skills
  形态）。v3 之后我们在**确定性门禁、角色隔离、QA 独立性、收敛闭环**上更强或持平，在**生态、社区、
  分发市场、per-task 编排**上仍明显落后。

加权总分（同一口径，1–5）：

```text
本套件 (v3.0.0)      4.12  ████████▎
GitHub Spec Kit      4.05  ████████▏
cc-sdd               3.85  ███████▋
BMAD-METHOD          3.78  ███████▌
OpenSpec             3.70  ███████▍
Agent OS             3.23  ██████▍
Taskmaster           3.08  ██████▏
```

> 与 v2 相比：D1 +0.3（brownfield + 收敛）、D2 +0.2（启发式）、D5 +0.3（CI/分发/测试）、D6 +0.7（一键采用）、
> D7 +0.2（可被复制采用，但仍无公开社区）。这是自评，不是第三方基准；生态一项仍把上限压在 4.2 附近。

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

- 本套件：`.agents/skills` 九个技能、`tools/`、`templates/ci/`、`docs/`、`tests/`；实测 539 个单元测试
  （1 skip）、109 个 E2E；新增专项 change 30、converge 27、distribution 28、plan-linter v3 26
  （详见 [技能使用指南](skills-guide.zh-CN.md) 与 [v3 说明](brownfield-convergence.zh-CN.md)）。
- 竞品：GitHub README/官方文档（见文末"数据来源"）；星标/GitHub API 快照见 §6。
- 所有竞品都只做文档级对照，未在相同仓库、相同任务上做 A/B。

---

## 3. 维度评分矩阵

| 项目 | D1 流程 20% | D2 可验证 15% | D3 隔离 15% | D4 可移植 10% | D5 工程化 10% | D6 上手 10% | D7 生态 10% | D8 扩展 5% | D9 中立 5% | **加权** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **本套件 v3.0.0** | 4.8 | 4.7 | 4.0 | 4.5 | 4.3 | 4.2 | 1.2 | 4.2 | 4.5 | **4.12** |
| GitHub Spec Kit | 4.5 | 3.0 | 2.0 | 5.0 | 4.5 | 5.0 | 5.0 | 4.5 | 4.5 | **4.05** |
| cc-sdd | 4.5 | 3.5 | 3.0 | 5.0 | 4.0 | 4.0 | 3.0 | 3.5 | 4.0 | **3.85** |
| BMAD-METHOD | 4.5 | 2.5 | 3.5 | 4.0 | 4.0 | 3.0 | 4.5 | 4.5 | 4.0 | **3.78** |
| OpenSpec | 4.0 | 3.0 | 1.5 | 4.5 | 4.5 | 4.5 | 4.5 | 4.0 | 4.5 | **3.70** |
| Agent OS | 3.0 | 2.5 | 2.0 | 4.0 | 3.5 | 4.5 | 3.5 | 4.0 | 4.0 | **3.23** |
| Taskmaster | 2.5 | 2.5 | 1.0 | 4.0 | 4.0 | 4.5 | 4.0 | 3.5 | 4.5 | **3.08** |

读法：分数是相对排序，不是绝对能力证明。一个 3.0 的项目可能在某些单点上比 4.5 的更强。

---

## 4. 本套件的组件评分

组件分为定性 1–5，不与上表权重直接相加；用于回答"九个技能各自值多少"。

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
| `converge` | 4.1 | append-only 写回、幂等 marker、归档与指纹漂移检测 | 依赖 Dev 如实填偏差表；无自动语义冲突消解 |
| 可选引擎 | 3.0 | 确定性生成/回放对回归有价值 | 领域启发式与预制内容可能污染输出；默认不应依赖 |
| 工具/文档 | 4.5 | 兼容矩阵、中文指南、RBAC/安装工具、quickstart 分发 + CI 模板、539 测试 | 无 release/插件市场；已有单仓库试点，仍无公开 A/B |

**一句话**：最强的仍是 `plan-linter` 与 `task-decomposition`；v3 的 `change` / `converge` 把
流程与活规格补到可用；最需要继续补的是生态/公开采用，而不是再加技能。

---

## 5. 逐项目对比

### 5.1 GitHub Spec Kit — 4.05（流程与生态标杆）

- **强项**：`constitution → specify → plan → tasks → implement → converge` 的完整 SDD 流程；
  bug fixing / idea assessment / 自定义 process 多入口；CLI、扩展与 workflow overlay；
  多 coding agent 集成；成熟文档与巨大生态。
- **相对我们**：强在生态、分发、社区与多 agent 集成；v3 之后我们在 brownfield 与收敛上已基本对齐
  （`change` + `converge`），并在确定性 Gate、角色隔离、CI 防作弊、QA 独立性上领先；仍弱在插件/扩展
  生态与公开采用。
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
- **相对我们**：brownfield 模型与轻量体验仍更成熟（跨仓库 stores、大社区）；v3 的 `change` 已覆盖
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
  `skills-ref validate`、插件市场与公开示例库——这是生态分低的重要原因。

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
| 本套件 | 本地项目，暂无公开 star 数据 | MIT（本仓库） | 未发布到公开市场 |

> 星标来自 GitHub API 快照，会持续变化；它衡量关注度，不衡量工程质量或适用性。

---

## 7. 我们赢在哪、输在哪

### 7.1 明确领先

1. **确定性门禁**：Gate 1 是可执行脚本（frontmatter 契约、DAG、blast radius、DoD、占位符），并新增
   锚点覆盖率矩阵与反向路径拓扑；有 JSON/配置/退出码，不依赖模型"自觉"。
2. **角色隔离与防作弊**：四文档 + 写权限矩阵 + CI `rbac_audit.py`；Dev/QA 的"考生不能自己判分"
   在结构上成立。
3. **QA 独立性**：QA 技能强制黑盒矩阵、证据、唯一裁决与返工 trace；多数竞品没有同等的 QA 契约。
4. **活规格与收敛**：`converge` 以 append-only 记录 + marker + 指纹漂移检测把实现结果写回规格，
   并归档任务包与 change；这不是文档承诺，是可执行脚本 + 幂等语义。
5. **prompt-first 可迁移**：技能不 import 引擎、可复制到仓库外；引擎可选；无 Python 也有手工路径。

### 7.2 明确落后

1. **生态与公开采用**：没有公开示例库、release 节奏、插件市场、`skills-ref validate`；社区为 0。
   v3 的 `quickstart` 只解决"能不能装"，不解决"有多少人在用"。
2. **多 agent 编排**：没有 per-task implementer/reviewer 的独立子代理编排（cc-sdd/BMAD 更强）。
3. **上手成本**：需要理解四文档、九个技能、两层门禁与配置阈值；仍比 OpenSpec/Taskmaster 重。
4. **真实证据**：已有单仓库试点（[v3-pilot](v3-pilot.zh-CN.md)：2 文件 / +400 行、Gate 2 退回 1 次、69/69 测试），但仍没有公开任务集 A/B、跨项目返工率数据；当前评分仍以自评为主。
5. **brownfield 深度**：`change` 的 delta 仍需 Planner 手写，standards 提取是确定性启发式而非代码语义
   理解；OpenSpec 的跨仓库 stores 与迭代体验仍更成熟。

---

## 8. v3 交付情况与剩余路线

> 下列"提分"是同一评分口径下的粗略估计，不是承诺。

| 优先级 | 改进 | 状态 | 实际效果 |
| :--- | :--- | :--- | :--- |
| P0 | brownfield / change 入口 | **已交付 v3** | `change` 技能 + standards 提取 + micro/standard 预算；D1 +0.3 |
| P0 | 分发与安装 | **已交付 v3** | `tools/quickstart.py` 一条命令 + `templates/ci/` 两个 workflow；D6 +0.7 |
| P1 | 收敛循环 | **已交付 v3** | `converge` append-only 写回 + 归档 + 指纹检测；D1/D2 增益 |
| P1 | Gate 2 机器辅助 | **已交付 v3** | 覆盖率矩阵、反向拓扑、change 一致性；D2 +0.2 |
| P2 | QA 自动化增强 | 未做 | 证据采集、覆盖率、scope diff、per-task reviewer 编排；约 +0.05 |
| P2 | 生态/公开采用 | 未做（真正瓶颈） | 公开示例库、release tag、changelog、issue/PR 模板、社区；D7 需要 1.2 → 3+ |
| P2 | 评测基线 | 未做 | 真实仓库任务集上的 pass/失败/返工率与 A/B |

v3 的功能项已经做完：**3.90 → 4.12**。  
继续加技能最多到约 4.15–4.2；要冲 **4.3+**，必须让 D7（生态与采用）从 1.2 升到 3 左右——这靠公开
采用、示例库、release 与社区，不靠再写一个技能。这是评分结构决定的。

---

## 9. 最终判断

**v3 之后，本套件已经是一套完整的 SDD 工具链，而不是 demo 技能集**：契约优先、门禁可执行、
角色可隔离、brownfield 可增量、实现结果可收敛、引擎可替换。它当前最像"Spec Kit 的确定性门禁版 +
OpenSpec 的增量模型 + 更严格的 QA 契约"；与头部的差距已经从"功能缺失"收敛为"生态与采用"。

- **今天适合谁**：重视契约、可追溯、CI 防作弊的团队/仓库；已有规格需要持续演进、又不想每次重写 PRD
  的项目；愿意接受四文档与角色分工的成本。
- **今天不适合谁**：只想要轻量 prompt、快速原型、或需要开箱即用插件市场的用户。
- **下一步最值得做的一件事**：拿一个真实仓库跑完整 v3 流程并公开结果（通过/返工/收敛条目），
  同时发首个 release 与示例库——这是 D7 从 1.2 往上走的唯一路径，也是 4.3+ 的门槛。

---

## 10. 数据来源与免责声明

- 本套件：仓库内 `.agents/skills`、`tools/`、`templates/ci/`、`tests/`、[技能使用指南](skills-guide.zh-CN.md)、
  [v3 说明](brownfield-convergence.zh-CN.md)、[v2 设计契约](skills-v2-spec.md)、[审计归档](audit/README.md)。
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
