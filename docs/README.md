# Docs / 文档索引

本目录面向**使用者**，说明如何安装、配置和使用本技能套件。历史设计与加固记录已移入
[`archive/`](archive/README.md)，不再作为当前行为依据；当前版本以
[`../VERSION`](../VERSION) 和 [`../CHANGELOG.md`](../CHANGELOG.md) 为准。

## 建议阅读顺序

| 你是 | 先读 | 再读 |
| :--- | :--- | :--- |
| 第一次接触套件 | [技能使用指南](skills-guide.zh-CN.md) | [宿主兼容与安装](skills-compatibility.md) |
| Dev / Planner | 指南 §3–§6 | [AGENTS.md](../AGENTS.md) 的任务流程与角色边界 |
| QA | 指南 §7.5 | [Gate 3 本地预检](gate3-precheck.zh-CN.md)、[测试策略](testing-strategy.md) |
| Quality Engineering | 指南 §7.6 | [CI 模板](../.agents/skills/quality-engineering/assets/templates/ci/README.md)、[多语言 Stack Profiles](ci-stack-profiles.zh-CN.md) |
| 维护技能本身 | [AGENTS.md](../AGENTS.md) §6 | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| 评估选型 | [评分与开源对标](skills-benchmark.zh-CN.md) | 注意它是 v3.1.0 基线快照，不是当前分数 |

## 当前文档

| 文档 | 作用 | 状态 |
| :--- | :--- | :--- |
| [skills-guide.zh-CN.md](skills-guide.zh-CN.md) | 从想法到交付的完整使用指南：角色、四文档、门禁、各技能用法 | 当前 |
| [skills-compatibility.md](skills-compatibility.md) | 宿主发现、安装、插件/自包含规则、可选 Python 引擎 | 当前 |
| [testing-strategy.md](testing-strategy.md) | 本套件自己的测试策略种子；采用方从技能模板生成自己的策略 | 当前 |
| [gate3-precheck.zh-CN.md](gate3-precheck.zh-CN.md) | QA 本地 Gate 3 预检：命令、参数、退出码、与 CI 的边界 | 当前 |
| [ci-stack-profiles.zh-CN.md](ci-stack-profiles.zh-CN.md) | Python/Node/Go/Java/Rust/.NET/C++ 的 CI profile 采纳说明 | 当前 |
| [brownfield-convergence.zh-CN.md](brownfield-convergence.zh-CN.md) | brownfield `change` 与 `converge` 的提案/归档流程 | 当前 |
| [agents-maintenance.zh-CN.md](agents-maintenance.zh-CN.md) | AGENTS.md 的单一事实源、长度预算与嵌套文件决策 | 维护者文档 |
| [skills-benchmark.zh-CN.md](skills-benchmark.zh-CN.md) | 与公开 spec-driven/agent-workflow 项目的评分对标 | v3.1.0 基线快照 |

## 归档

| 文档 | 说明 |
| :--- | :--- |
| [archive/skills-remediation.zh-CN.md](archive/skills-remediation.zh-CN.md) | v3.2.0 前后的加固工作包与评审记录；历史证据，不是当前规范 |
| [archive/README.md](archive/README.md) | 归档规则与索引 |

## 维护规则

- 面向用户的行为变化必须同时更新本索引、对应指南和 `CHANGELOG.md`。
- 不要把历史工作包、已废弃方案或旧版本评分留在当前文档里；移入 `archive/` 并在索引中说明。
- 文档中的命令应能在当前检出中执行；新增/删除文件时同步更新相对链接。
- 维护流程见 [AGENTS.md](../AGENTS.md) §6 和 [CONTRIBUTING.md](../CONTRIBUTING.md)。
