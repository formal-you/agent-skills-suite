# AGENTS.md 维护与单一事实源

> 适用对象：维护技能套件、规则层和 CI 的贡献者。  
> 本文解释 [`AGENTS.md`](../AGENTS.md) 的写法与边界；它不是 always-loaded 规则，不需要每个 Agent 都读。

## 1. 设计目标

`AGENTS.md` 是 **always-loaded 操作契约**，不是完整文档。它应让一个刚进入仓库的 Agent 在很短时间内知道：

- 仓库怎么分区、任务属于哪条流程；
- 写权限和冲突处理原则；
- 门禁、证据和完成标准；
- 常用命令与安全边界；
- 详细内容去哪个单一事实源查看。

因此它优先保证：**短、准、可执行、可验证、无重复、可维护**。

## 2. 单一事实源（Source of Truth）

| 内容 | 权威来源 | AGENTS.md 的处理 |
| :--- | :--- | :--- |
| 角色、写作用域、read-only 区域 | [`.agents/rules/enforcement.md#role-matrix`](../.agents/rules/enforcement.md#role-matrix) | 只链接，不复制表格 |
| 单角色权限细节 | `.agents/rules/<role>.md` | 只引用目录约定 |
| Gate 1 行为 | `plan-linter` 技能 / `plan_linter.py` | 一句话职责说明 |
| Gate 2 行为 | `review` 技能 / `.agents/rules/reviewer.md` | 一句话职责说明 |
| Gate 3 行为 | `quality-engineering` / `verification_linter.py` | 一句话职责说明；细节链接 CI 文档 |
| 4 文档任务包、Goldilocks、生命周期 | `enforcement.md` + `task-decomposition` 模板 | 只保留摘要 |
| CI 流水线、门禁配置 | [`.agents/skills/quality-engineering/assets/templates/ci/README.md`](../.agents/skills/quality-engineering/assets/templates/ci/README.md) | 只链接 |
| 技能变更 / Git Flow | `AGENTS.md` §4 + [`CONTRIBUTING.md`](../CONTRIBUTING.md) + PR 模板 | 保留可执行步骤 |
| 用户文档入口 | [`docs/README.md`](README.md) | 只链接 |
| 历史设计 | [`docs/archive/`](archive/README.md) | 明确标注历史，不作当前规范 |

原则：**同一个事实只在一个地方定义；AGENTS.md 只保留“入口 + 约束 + 命令”，细节靠链接。**

## 3. 长度与上下文预算

- 当前软上限：**155 行**。
- 行数不是目标，上下文成本才是；但行数失控通常意味着把细节复制进了 always-loaded 文件。
- 新增内容前先问：这是每次任务都必须知道的，还是只在改技能/改 CI 时需要？
- 后者应放到 role rule、skill reference、`.agents/skills/quality-engineering/assets/templates/ci/README.md` 或本文。

## 4. 技能之间的调用约定（组合，不复制）

宿主只注入 `.agents/skills/<name>/SKILL.md` 和 `.agents/rules/*.md`，所以每个技能目录是一个独立安装单元。技能之间组合时遵循：

- **按技能名组合，不复制脚本**。`change` / `task-decomposition` 需要 Gate 1 时，调用的是 `plan-linter` 技能（由该技能拥有 `plan_linter.py`），而不是在自己的目录里再放一份脚本，也不是硬编码一条无法解析的相对路径。
- **跨技能命令必须可解析**：使用项目根目录形式（如 `python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir ./tasks ...`），并显式标注“仅在已安装 `plan-linter` 技能时可用”；同时保留手工检查清单作为 fallback。
- **本技能自己的脚本也用项目根目录形式**：`python scripts/x.py` 只有在 cwd 恰好是技能目录时成立，Agent 通常在仓库根目录工作，因此统一写 `.agents/skills/<name>/scripts/x.py`。
- **不复制、不转售别人的脚本**：重复副本会漂移；确定性门禁的归属固定（Gate 1 = `plan-linter`，Gate 3/CI = `quality-engineering`）。
- **声明而非隐藏依赖**：软依赖写入 `compatibility` 或正文说明；安装器（`quickstart.py --with-ci`）对 CI 必需的 `quality-engineering` 做自动补选。

守卫：`tests/unit/test_distribution.py` 同时检查裸 `scripts/...` 路径、跨技能引用（仅允许带“已安装”说明的 `plan-linter`）和仓库级 `templates/ci/` 回潮。

## 5. 为什么暂不拆嵌套 AGENTS.md

嵌套 `AGENTS.md`（如 `.agents/skills/AGENTS.md`、`tests/AGENTS.md`）是 monorepo 的一种最佳实践，但当前**不拆**：

- 本仓库是单一技能包，不存在多个独立子项目；
- 不同宿主对嵌套 AGENTS 的加载范围支持不一致，拆了可能反而“写了但没被加载”；
- 根文件去重后已控制在 155 行内，暂时没有必须拆的上下文压力；
- 拆分需要同时验证每个宿主的加载行为，属于独立改造，不应和文档去重混在一起。

**重新评估条件**：出现独立子项目、根文件超过约 200 行、或某类规则只在特定子树适用时，再拆。

## 6. 修改 AGENTS.md 的检查清单

- [ ] 新内容是否是 always-loaded 必需？能否链接到单一事实源？
- [ ] 是否复制了角色矩阵、门禁表、完整命令或版本号？
- [ ] 是否更新了受影响的单一事实源，而不是只改 AGENTS？
- [ ] `python -m unittest tests.unit.test_agents_workflow -v` 通过。
- [ ] 全量测试、`git diff --check`、CI 矩阵通过。
- [ ] 变更走 issue -> branch -> PR -> merge -> tag 流程。

相关守卫：[`tests/unit/test_agents_workflow.py`](../tests/unit/test_agents_workflow.py) 检查结构、行数预算、必需链接和不重复角色/门禁表。
