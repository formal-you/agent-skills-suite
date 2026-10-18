# v3 试点：在真实仓库跑通 brownfield → 收敛 全流程

> 状态：**已完成**（2026-10-18）。本文记录示例定义、全部证据、暴露的问题与复现步骤；下个 session 可直接按第 7 节接手。  
> 试点在**隔离副本**中执行（`D:\WorkSpace\v3-pilot-eaap`），没有改动主仓库的产品代码；主仓库只新增本文与 v3.1 修复。

---

## 1. 结论摘要

| 项目 | 结果 |
| :--- | :--- |
| 真实仓库 | 本仓库 HEAD（AutoSpec 仓库内的 EAAP 子项目：`.specs/` 规格 + `agent-core/` 实现，均受 git 跟踪） |
| 变更 | brownfield 新增 MCP/JSON-Schema 工具注册适配器，锚点 `#sec-tool-registry-sandbox`（REQ-004） |
| 规模 | 2 个 touch file（1 create + 1 modify），实际 +400/−0 行（计划估计 120 行） |
| Gate 1 | PASS，0 errors / 0 warnings；覆盖率矩阵 1/23（单锚点变更，符合预期） |
| Gate 2 | 第一轮 **REQUEST CHANGES**（5 条发现）→ Planner 修订 → 第二轮 **PASS** |
| Dev | 2 文件；`pnpm typecheck`、build-config tsc、`pnpm test`（52/52）全绿；偏差表 `None` |
| QA | 独立验收 **17/17**；全量 **69/69**（52 既有 + 17 验收）；typecheck 0 诊断 |
| Converge | `CONVERGED` + marker + 任务包归档 + proposal `archived` + 规格追加记录 |
| 结论 | v3 闭环在真实代码上可运行；暴露 5 个工程问题，其中 3 个已在 **v3.1** 修复 |

---

## 2. 具体示例是哪个

**仓库**：本仓库（`D:\WorkSpace\Agent研究`）的 EAAP 子项目——基座规格 `.specs/02-tech-spec.md` 与实现 `agent-core/` 在同一个 git 仓库里。

| 维度 | 取值 |
| :--- | :--- |
| 基座规格 | `.specs/02-tech-spec.md`（23 个 `#sec-*` 锚点） |
| 继承 ADR | `ADR-004`（动态工具代码执行沙箱环境选型） |
| 变更锚点 | `#sec-tool-registry-sandbox`（REQ-004：工具动态注册、MCP 协议兼容与安全沙箱执行） |
| 变更内容 | 新增 `agent-core/src/adapters/json-schema-tool.ts`：`defineJsonSchemaTool()` 接受纯 JSON Schema（MCP/OpenAPI 导入工具的形态），构造期 fail-closed 校验关键字白名单，运行期用同一份 schema 校验入参；从 `agent-core/src/adapters/index.ts` 导出；不新增依赖 |
| 为什么是 brownfield | 既有 `ToolRegistry` 端口、内存注册表、zod 适配器与完整测试；本次只复用端口、补一种注册方式，没有新组件边界、没有新锚点 |
| 为什么不是 PRD | 需求已由 REQ-004 与 ADR-004 授权，范围 2 个文件、可单次评审 —— 正是 `change` 技能的适用区间 |

---

## 3. 执行方式（隔离副本 + 角色分离）

- 用 `git archive HEAD` 把仓库导出到 `D:\WorkSpace\v3-pilot-eaap`，通过 junction 复用 `agent-core/node_modules`；副本没有 `.git`（因此提交审计改由行数、导出面与目录状态替代）。
- 角色由独立的 fresh-context subagent 执行，Lead 只做编排、门禁与收敛：
  - **Planner**：只写 `proposal.md` 与 `01-contract.md`；
  - **Gate 2 Reviewer**：只读，不写任何文件；
  - **Dev**：只写 `touch_files` + `02-dev-workspace.md`；
  - **QA**：只写 `agent-core/tests/acceptance/**` + `03-qa-verification.md`；
  - **Lead**：跑 Gate、`converge`、汇总证据。

---

## 4. 全流程证据

### 4.1 standards 提取（隐式约束）

```bash
python .agents/skills/change/scripts/standards_extract.py --repo-root . --json
```

- 检出：`agent-core/package.json`、`agent-core/tsconfig.json`、`pyproject.toml`；测试文件 `agent-core/tests/**`；23 个锚点。
- **发现**：报告第 6 节命令为空（旧版只读根 `package.json`），因此 Planner 依据 `agent-core/package.json` 的真实 scripts 填写 DoD，并在契约中写明该差异。该缺陷已在 v3.1 修复（见 §6）。

### 4.2 生成 proposal + 单个任务包

```bash
python .agents/skills/change/scripts/scaffold_change.py \
  --change-id CHG-001-mcp-tool \
  --title "Register MCP/JSON-Schema tools with schema validation" \
  --anchor "#sec-tool-registry-sandbox" --kind modify --size-class standard \
  --estimated-lines 120 \
  --touch-files "create:agent-core/src/adapters/json-schema-tool.ts,modify:agent-core/src/adapters/index.ts" \
  --repo-root .
```

生成：`.specs/changes/CHG-001-mcp-tool/proposal.md` + `tasks/CHG-001-mcp-tool/01..04`；`lint_change.py` 当时提示 `GUIDANCE_REMAINS`（模板引导语待 Planner 替换），替换后归零。

### 4.3 Gate 1（确定性）

```bash
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks \
  --repo-root . --spec .specs/02-tech-spec.md --changes-dir .specs/changes --json
```

```text
Gate 1 PASSED: scanned 1 task bundle(s).
Coverage: 1/23 spec anchors covered (4.3%); 22 uncovered.
```

JSON：`passed: true`、`errors: []`、`warnings: []`、`covered: ["#sec-tool-registry-sandbox"]`、`contract_anchors_missing_from_spec: []`。

### 4.4 Gate 2（独立语义审查，两轮）

第一轮 **REQUEST CHANGES**，5 条发现（全部成立，Planner 据此修订）：

| # | 发现 | 证据 | 修订 |
| :--- | :--- | :--- | :--- |
| 1 | 配置键 `handler` 是虚构的，仓库惯例是 `run`（`zod-tool.ts` / `tool.ts`） | 仓库无 `handler` 字段 | 全部改名 `run` |
| 2 | 声称支持"类型数组联合"，但 `JsonSchema.type` 是单值；2 文件 scope 无法类型安全实现 | `core/json.ts` 单值 union | 删除该声明，限定声明类型 |
| 3 | 未执行的关键字（`const`/`oneOf`/`pattern`/`minimum` 等）会被静默放过，违背"invoke 只拿已校验入参" | `json.ts` 定义这些关键字 | 构造期 fail-closed：白名单外抛错 |
| 4 | 递归与路径格式未定义，边界用例只覆盖根级，QA 无法验证 | 契约 §4/§6 | 明确递归 + `payload.user.id` / `items[0].f` / `(root)`，补第 4 个边界用例 |
| 5 | `ToolError` 必填 `retryable` 未规定 | `core/errors.ts` | 明确 `retryable: false` |

第二轮 **PASS**：0 omissions、0 hallucinations、0 ADR violations；Reviewer 逐条复核修订行并确认 2 文件 scope 未变。

这是 v3 试点里最有价值的一步：**Gate 2 真的抓到了 5 个会污染实现的问题**，而不是形式化盖章。

### 4.5 Dev 实现

```bash
cd agent-core && pnpm typecheck                       # exit 0
cd agent-core && pnpm exec tsc -p tsconfig.build.json --noEmit   # exit 0
cd agent-core && pnpm test                           # 7 files / 52 tests passed
```

- 变更：`json-schema-tool.ts` 399 行（含说明注释）+ `adapters/index.ts` +1 行；`02-dev-workspace.md` 记录实际行数、自测结果与一行 `None` 偏差。
- 偏离：无功能偏离；行数 400 对估计 120（3.3x）被记为估算问题（见 §6）。

### 4.6 QA 独立验收

```bash
cd agent-core && pnpm exec vitest run tests/acceptance/json-schema-tool.acceptance.spec.ts  # 17/17
cd agent-core && pnpm exec vitest run                                                       # 8 files / 69 tests
cd agent-core && pnpm typecheck                                                             # exit 0
```

- 验收测试覆盖：合法输入执行、required 缺失、`additionalProperties:false`（根/嵌套）、点号路径、`items[0].f`、enum、integer、`const` 构造期抛错（根/嵌套）、根类型非 object、`additionalProperties` 为 schema、默认值、显式透传、注册表集成。
- 裁决：`QA_PASSED`（唯一勾选）；记录 1 条非阻断观察：估计行数与实际偏差。

### 4.7 收敛（converge）

```bash
python .agents/skills/converge/scripts/converge.py check --tasks-dir tasks --json
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-mcp-tool --dry-run
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-mcp-tool --json
```

```json
{ "status": "converged",
  "archive": "tasks/archive/CHG-001-mcp-tool",
  "proposal_archived": true,
  "event_appended": true,
  "marker": "sha256:9b22994694492fb190e87611cb639b5cf4b5ceb671b53e2331294584fcfd13c7",
  "spec_sha256_before": "sha256:4e604b4f...",
  "spec_sha256_after":  "sha256:e8fc1e54..." }
```

实际写入：

- 规格末尾新增 `## Converged changes` + `### CHG-001-mcp-tool: ...` + 偏差表 + marker；
- `04-process.md`：`macro_status: "CONVERGED"`，追加 `TASK_CONVERGED / ConvergeTool` 事件（含 marker 与 spec 指纹）；
- 任务包移动到 `tasks/archive/CHG-001-mcp-tool/`；
- `proposal.md` 状态改为 `archived`，并生成 `.specs/changes/CHG-001-mcp-tool/convergence.md`。

converge 后再次 `check`：`tasks: []`（活动区已空）——收敛成功；注意 `check` 不会回读归档区，若要审计历史请直接看 `tasks/archive/` 与规格记录（§6 已记录）。

---

## 5. 指标

| 指标 | 值 |
| :--- | :--- |
| 计划 → 收敛总耗时（含 4 个独立 agent 的推理时间） | 约 25 分钟 |
| Gate 2 轮次 | 2（1 次退回，5 条有效发现） |
| 变更文件 / 行数 | 2 / +400（计划 120） |
| 既有测试 | 52 全过（未回归） |
| 新增验收测试 | 17，全部通过 |
| 全量测试 | 69/69 |
| 契约是否被削弱 | 否（Gate 2 第二轮 PASS，无豁免） |
| 收敛后规格 | 追加 1 条记录 + marker，原文逐字节保留 |

---

## 6. 发现的问题与处理

| # | 发现 | 影响 | 状态 |
| :--- | :--- | :--- | :--- |
| A | `standards_extract --check` 在生成报告后立即变红：`tasks/` 被当成源码目录、`.specs/changes/*/proposal.md` 被当成规格锚点来源 | 任何进行中的 change 都会让报告显示过期 | **已修复（v3.1）**：排除 `tasks/` 与 `.specs/changes/`，+2 回归测试 |
| B | 第 6 节命令永远为空：只解析根目录 `package.json` | monorepo 无法给出 DoD 命令证据 | **已修复（v3.1）**：扫描所有 manifest，输出 `cd pkg && pnpm run typecheck` 等，并读嵌套 `engines.node`；+2 回归测试 |
| C | 仓库没有 lint 命令，而契约强制 `dod.lint` | 只能用 build-config tsc 替代并明确记录 | 建议 v3.2：允许 `dod.lint: none` + 理由字段（未做） |
| D | `estimated_lines: 120` 实际 400（3.3x，超过 Goldilocks 250 上限） | 评审成本估算失真 | 建议：计划阶段对估算偏差做提示，或把注释行与代码行分开统计（未做） |
| E | 副本无 `.git`，无法做 diff/commit 级审计 | 试点限制，真实使用不适用 | 记录在案；真实流程用 `tools/rbac_audit.py` + git |
| F | converge 归档后 `check` 返回 `tasks: []`，无法从 check 看到历史收敛 | 审计需看归档区/规格 | 建议：`check --include-archive` 或在摘要计入已归档（未做） |
| G | pnpm 对 junction `node_modules` 打印 hoist 警告 | 仅噪音，exit code 正常 | 环境限制，记录 |
| H | standards 报告把未跟踪目录（如 `deepseek-Harnes修复/`）列为 source dir | 轻微噪音 | 未修（可选：只统计 git 跟踪目录） |

---

## 7. 复现与交接（给下个 session）

### 7.1 现成证据

试点产物保留在 `D:\WorkSpace\v3-pilot-eaap`：

```text
.specs/changes/CHG-001-mcp-tool/{proposal.md,convergence.md}
.specs/02-tech-spec.md                      # 末尾 Converged changes 记录
tasks/archive/CHG-001-mcp-tool/              # 已收敛任务包（四文档）
agent-core/src/adapters/json-schema-tool.ts # 实现
agent-core/tests/acceptance/json-schema-tool.acceptance.spec.ts
evidence/gate1.json, evidence/lint_change.json
```

### 7.2 从零复现

```bash
# 1) 隔离副本
git archive HEAD | tar -x -C /tmp/v3-pilot
# 2) 复用依赖（Windows）
mklink /J /tmp/v3-pilot/agent-core/node_modules agent-core/node_modules
# 3) standards + 提案/任务包
cd /tmp/v3-pilot
python .agents/skills/change/scripts/standards_extract.py --repo-root .
python .agents/skills/change/scripts/scaffold_change.py --change-id CHG-001-mcp-tool \
  --title "Register MCP/JSON-Schema tools with schema validation" \
  --anchor "#sec-tool-registry-sandbox" --kind modify --size-class standard \
  --estimated-lines 120 \
  --touch-files "create:agent-core/src/adapters/json-schema-tool.ts,modify:agent-core/src/adapters/index.ts"
# 4) Planner 填 proposal + 01；然后
python .agents/skills/change/scripts/lint_change.py --repo-root .
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --repo-root . \
  --spec .specs/02-tech-spec.md --changes-dir .specs/changes
# 5) review 技能做 Gate 2 → dev 技能实现 → qa 技能验收（prompt 流程，见各 SKILL.md）
# 6) 收敛
python .agents/skills/converge/scripts/converge.py apply --task tasks/CHG-001-mcp-tool
```

### 7.3 可选下一步

1. **把试点实现合入真实 `agent-core`**（需要正常的 git 分支 + `pnpm install`，并按仓库 Git Flow 提 PR/合并）；本报告不自动合入，避免未经评审的产品变更。
2. 处理 §6 的 C/D/F：`dod.lint: none` 支持、估算偏差提示、`converge check --include-archive`。
3. 清理 `D:\WorkSpace\v3-pilot-eaap`（约 100 MB，含 junction）或保留作为证据。

---

## 8. 结论

- **v3 的 brownfield 与收敛闭环在真实代码、真实测试、真实规格上跑通了**，不是演示脚本。
- Gate 2 的独立性有实际价值：第一轮抓到 5 个若直接实现会留下"schema 声明了但运行期不校验"的隐患。
- 试点的最大工程短板不是流程，而是**估算与工具边界**：`estimated_lines` 失真、lint 约定缺失、standards 报告的 monorepo 盲区。前两项已在 v3.1 修复，第三项留作后续。
- 生态仍是 4.3+ 的门槛：这次试点证明了"能跑"，但要让 D7 从 1.2 上升，还需要公开采用与示例库。

[![](https://img.shields.io/badge/powered_by-dsh-4D6BFE?style=flat-square&logo=deepseek&logoColor=white)](https://github.com/deepseek-ai/deepseek-harness)
