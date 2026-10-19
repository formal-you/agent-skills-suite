# Gate 3 本地预检（QA 使用）

> 适用对象：执行单任务验收的 QA Agent / 工程师。  
> 结论先说：**本地预检是自检，不是权威门禁；CI 的 Gate 3 才是权威。**

## 1. 它解决什么问题

QA 填完 `03-qa-verification.md` 后，如果直接提交，常见失败是：

- Section 3 的 V(G) 或基路径用例数写错；
- Section 4 的变异表缺失、MSI 不达标或两张表不一致；
- Section 4 的自报聚合/逐目标数值与真实归一化变异报告对不上（CI Gate 3 用 `--actual-mutation` 交叉核验时）；
- Section 5 缺少命令/结果/artifact provenance（QA 还应记录真实 BDD runner 命令与机器可读报告 provenance）；
- `03` 里的 V(G) 与真实 AST artifact 对不上。

`verification_linter.py` 在本地先检查这些**证据完整性**问题，避免到 CI 才被打回。

## 2. 命令

`qa` 技能自带一份 stdlib 副本，单独安装 `qa` 也能用：

```bash
python .agents/skills/qa/scripts/verification_linter.py \
  --tasks-dir ./tasks --json
```

审计单个任务：

```bash
python .agents/skills/qa/scripts/verification_linter.py \
  --tasks-dir ./tasks --task TASK-001 --json
```

有真实复杂度/变异 artifact 时，做与 CI 一致的交叉核验（canonical 审计器支持全部 artifact 参数；QA 内置副本与它逐字节一致时同样可用）：

```bash
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir ./tasks \
  --actual-complexity artifacts/complexity-report.json \
  --require-actual-complexity \
  --actual-mutation artifacts/mutation-report.json \
  --require-actual-mutation --strict --json
```

> `quality-engineering` 维护 canonical 版本；QA 副本与它逐字节一致，并由测试保证不漂移。
> 安装位置不同时，把 `.agents/skills/qa/scripts/` 换成实际技能目录即可。

## 3. 常用参数

| 参数 | 作用 |
| :--- | :--- |
| `--tasks-dir PATH` | 任务包目录，默认 `./tasks` |
| `--task ID` | 只审计一个任务 |
| `--json` | 输出机器可读结果，适合 Agent/CI 解析 |
| `--strict` | 把 warning 当 Gate 3 错误 |
| `--actual-complexity PATH` | 用 `complexity_check.py` 的真实 AST 报告交叉核验 V(G) |
| `--require-actual-complexity` | 没有报告就失败，禁止只信 `03` 自报值 |
| `--actual-mutation PATH` | 用 `mutation_gate.py` 产出的归一化变异报告（`targets[]`）交叉核验 Section 4 的聚合与逐目标计数/MSI |
| `--require-actual-mutation` | 没有可用报告就失败（`MUTATION_REPORT_MISSING`），禁止只信 `03` 自报 MSI |
| `--require-provenance` | 要求 Section 5 的 artifact 路径/SHA-256 与等价变异理由 |
| `--min-msi N` | MSI 阈值，默认 80（core 任务 90） |
| `--no-mutation` / `--no-evidence` | 跳过对应检查，仅用于调试，不应作为验收捷径 |

## 4. 退出码

| 退出码 | 含义 | QA 动作 |
| :--- | :--- | :--- |
| `0` | 预检通过 | 仍需确认测试真实通过，再考虑 `QA_PASSED` |
| `1` | 存在违规/超阈值 | 修复 `03` 或测试，重新执行；不得降低阈值 |
| `2` | 参数/输入错误 | 修正命令或路径 |
| `3` | 内部错误 | 记录并升级，不要伪造通过 |

## 5. 它不做什么

- **不执行测试**、不跑变异；测试与变异仍由 QA 自己执行；
- **不证明行为正确**；测试失败时即使预检通过也必须 `REWORK_REQUIRED`；
- **不读取测试策略**；策略由 QA 在设计阶段应用到 `03` §2.1；
- **不替代 CI Gate 3**：本地预检只审计 Markdown 证据。CI Gate 3 在提供 `--actual-mutation` 时会把 `03` Section 4 的聚合与逐目标证据同真实归一化变异报告交叉核验，伪造的 `MSI: 92%` 会以 `MUTATION_MISMATCH_WITH_REPORT` 失败；真实变异由 PR 与主干 push 上的 mutation job（`mutation_gate.py`）执行，不再是“PR 只审自报、主干才真跑”。

## 6. 与 CI 的分工

| 层 | 谁运行 | 作用 |
| :--- | :--- | :--- |
| 本地预检 | QA | 提前发现证据问题，快速反馈 |
| Gate 3（PR） | CI | 权威审计 `03` + 真实复杂度 artifact + 真实变异报告（`--actual-complexity` / `--actual-mutation`） |
| Mutation gate（PR + trunk） | CI | 在 PR 与主干 push 都真正执行项目变异命令（`quality-gate.config.json` 或 `MUTATION_COMMAND` 回退），fail-closed |
| RBAC audit / branch guard | CI | 检查角色越权与分支隔离 |

本地预检通过 ≠ 任务通过；**CI 绿灯 + 测试通过 + QA 裁决**才构成验收。

## 7. 相关文档

- [`qa` SKILL](../.agents/skills/qa/SKILL.md) 与 [`qa-protocol`](../.agents/skills/qa/references/qa-protocol.md)
- [`quality-engineering` 的 Gate 3 协议](../.agents/skills/quality-engineering/references/verification-protocol.md)
- [`AGENTS.md`](../AGENTS.md) 的 Gates 与 skill change workflow
- [测试策略](testing-strategy.md) 与 [文档索引](README.md)
