# Agent Skills v3 加固改造执行手册

> **读者**：执行型 LLM Agent（低级/中等能力模型）。读完本文后，你应当直接修改仓库，而不是再写一份设计方案。
> **基线**：`VERSION` = `3.1.0`；单元测试基线 `312 passed, 1 skipped`。
> **输入材料**：[技能使用指南](skills-guide.zh-CN.md)（现状介绍）与 [其他 Agent 点评结果](../其他agent点评结果.md)（待评估的外部点评）。
> **注意**：`其他agent点评结果.md` 当前是工作区输入文件，尚未纳入 git；若你要提交本手册，请不要让构建/链接检查强依赖该文件，或同时把它纳入版本库。
> **目标**：把"文档上存在门禁"改造成"门禁不可跳过、证据不可伪造、失败可路由到正确角色"。
> **执行状态（2026-10-19，v3.2.0）**：WP-01～WP-09、WP-11 已落地；WP-10（QA 读隔离 Runner）与
> WP-12（属性测试/幂等探针）仍为 P2 后续项，未在本版本强行实施，文档中的诚实限制已同步。

---

## 0. 执行契约（先读这一页）

### 0.0 如果只做三件事

按顺序做，不要跳步：

1. **WP-01**：修掉 push 时 Gate 3 被静默跳过的 DAG 缺陷（最小、最高收益）。
2. **WP-03 → WP-04 → WP-05**：先统一错误码，再让复杂度扫描有正确范围，最后让 Gate 3 用真实产物交叉核验。
3. **WP-06 → WP-07**：变异测试真跑并硬门禁；验收测试真装依赖、真跑 BDD runner。

其余 WP 按 §4 顺序补齐。**不要一次改完所有内容**；每完成一个 WP 就运行 §0.4 的全量测试。

### 0.1 你的角色

你是**执行者**，不是架构评审员。你的工作是按本文的工作包（WP）顺序做小步、可验证的修改。不要新增技能包，不要重命名技能，不要重写整个脚本，不要为了让测试变绿而删除断言。

### 0.2 绝对禁止（违反任一条即回滚该 WP）

1. 禁止把任何失败命令包进 `|| true`、`continue-on-error: true`、`set +e` 后不检查退出码。
2. 禁止删除、跳过、弱化测试来"通过"；只能因为行为迁移而**移动**测试，且必须保留等价覆盖。
3. 禁止在 `skills/**`、`.agents/skills/**`、`templates/**`、`AGENTS.md` 中写中文；这些是 canonical English 文件。
4. 禁止只改一棵树：`skills/workflow/<name>/` 与 `.agents/skills/<name>/` 必须逐字节一致。
5. 禁止在 `SKILL.md` 中堆细节：每个 `SKILL.md` 必须 `< 200` 行，长内容放 `references/`。
6. 禁止使用绝对路径（`D:\`、`C:\`、`/home/`、`/Users/`）；链接必须能在仓库内解析。
7. 禁止把"提示词约定"写成"物理隔离/强制门禁"；做不到就写 `advisory` 或 `manual`。
8. 禁止发明 PRD/规格中不存在的实体、字段、错误码或命令；所有新错误码必须先写入错误码注册表（WP-03）。
9. 禁止在同一个 WP 中同时改 CI、脚本、模板和文档；一个 WP 只解决一类问题，便于回滚。
10. 禁止改动 `tasks/` 下的历史任务包来"修历史数据"；只改模板、脚本、CI 和文档。

### 0.3 语言、目录与双树规则

- **canonical English**：`skills/**`、`.agents/skills/**`、`templates/**`、`AGENTS.md`、`tools/**` 的注释与文档。
- **中文**：仅允许 `docs/*.zh-CN.md`、根目录中文说明文件。
- **双树映射**：
  - `skills/workflow/<name>/` ↔ `.agents/skills/<name>/`（11 个技能）
  - `skills/platform/diagnose-windows-sandbox-acl/` ↔ `.agents/skills/diagnose-windows-sandbox-acl/`
  - 任一文件改动后，两边 SHA-256 必须相同（`tests/unit/test_modern_quality_engineering.py::test_f18_dual_tree_mirror_synchronization`）。
- **脚本也在双树中**：`plan_linter.py`、`verification_linter.py`、`complexity_check.py` 改一份就要同步另一份。

### 0.4 基线命令（在每个 WP 开始与结束各跑一次）

```bash
# 全量单元测试（当前基线：312 passed, 1 skipped，约 40s）
python -m unittest discover -s tests/unit -p "test_*.py"

# 双树一致性
python -m unittest tests.unit.test_modern_quality_engineering.Tier1FeatureCoverageTests.test_f18_dual_tree_mirror_synchronization

# Gate 1 / Gate 3（本地预检）
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --json
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir tasks --strict --json
```

> ⚠️ 已知基线异常：本套件仓库没有 `src/`，`complexity_check.py --json` 当前会扫描 `.`（包括 `skills/`、`tools/`），在自身仓库上报 29 个 `V(G) > 15` 并以 exit 1 结束。这是 WP-04 要修的缺陷，**不要**把它当作"改造后仍应失败"的基线。

### 0.5 推荐阅读顺序（不要跳读）

1. `AGENTS.md`
2. `docs/skills-guide.zh-CN.md`
3. `其他agent点评结果.md`（只信第 2 部分，见 §1）
4. `.agents/rules/enforcement.md`
5. `.agents/skills/quality-engineering/SKILL.md`
6. `templates/ci/quality-gate.yml` + `templates/ci/README.md`
7. `.agents/skills/quality-engineering/scripts/verification_linter.py`
8. `.agents/skills/quality-engineering/scripts/complexity_check.py`
9. `.agents/skills/plan-linter/scripts/plan_linter.py`
10. `.agents/skills/task-decomposition/assets/templates/03-qa-verification.template.md`

### 0.6 工作方式

- 一次只做一个 WP；做完、验证、记录后，再做下一个。
- 先写/改测试，再改实现；至少保证新增行为有测试。
- 每个 WP 结束后运行 §0.4 的全量测试；失败先修当前 WP，不要继续下一个。
- 连续两次修复失败，停止并按 §6 上报，不要扩大改动范围。

---

## 1. 点评可靠性裁定

### 1.1 总体结论

| 部分 | 可靠性 | 结论 |
| :--- | :--- | :--- |
| 第 1 部分：多 Agent 架构 / 防幻觉 / 仲裁 | **中等偏低（约 55%）** | 方向正确，但多处事实错误、把"提示词要求"当成"已实现"，并对现状有明显高估。可当假设清单，不能当验收依据。 |
| 第 2 部分：CI 模板 6 个漏洞 | **高（约 85%–90%）** | 逐条基本能在代码中复现，是本次改造最有价值的部分；但个别措辞夸大，且遗漏了更严重的缺陷。 |
| 改造建议 | **方向可用，细节需重写** | "交叉核验、去掉 `\|\| true`、补环境、补路由、补产物"都应做；"QA 禁止读 src""隐藏 03 数据"需要先修工具链，否则会破坏现有 QA 职责。 |

一句话：**把这份点评当作"缺陷线索"是可靠的；把它当作"现状审计报告"是不可靠的。**

### 1.2 第 1 部分逐条裁定

| ID | 点评主张 | 裁定 | 证据（v3.1.0） | 对改造的含义 |
| :--- | :--- | :--- | :--- | :--- |
| A1 | QA 上下文可读 `src/**`，仅提示词约定，未物理隔离 | **成立（作为风险）** | `.agents/rules/qa.md` 第 9 行 `Read-only: src/**`；`qa/references/qa-protocol.md` 要求"先写黑盒断言再读实现"，但同文件第 3/5 步要求 QA 对源码做静态分析与变异测试 | 不能直接删读权限；先做工具中介（WP-10），再把"读"降级为"看脱敏摘要" |
| A2 | `rbac_audit.py` 只约束写、不限制读 | **成立** | `tools/rbac_audit.py` 顶部说明与 `audit()` 都基于 git diff 的路径，只能拦截"改了哪些文件" | RBAC 不是读隔离；不要把"写边界"说成"物理隔离" |
| A3 | 变异测试应由外部 Runner 运行，只给 QA 脱敏摘要 | **未实现** | 仓库没有 Runner；`qa` 是 prompt-only，`03` 由 QA 手填 | 这是 P2 设计，不是现状；先做 WP-06 的真实 CI 变异门禁 |
| A4 | 三层仲裁，第一层已具备 | **部分成立** | CI 有 Gate 1/3 与 lint；但没有 Spec-Judge，`review` 只有 `PASS / REQUEST CHANGES / BLOCKED` | 第一层成立；第二层要新增仲裁模式（WP-09） |
| A5 | Dev 没有结构化申诉通道 | **成立** | `.agents/skills/task-decomposition/assets/templates/02-dev-workspace.template.md` 只有 1–5 节 + 偏差表，无 Appeal；全仓 grep `appeal` 无命中 | 加模板字段 + review 仲裁 + 编排路由（WP-09） |
| A6 | 生命周期已有 attempt 计数，第三层"部分具备" | **夸大** | `04-process.template.md` 有 `retry_count: 0`，但 `tools/` 只有 quickstart/install/rbac，没有工具会递增它；`03` 的 Attempt 也是手填 | 只能算"模板字段"；熔断需要显式规则与人工出口（WP-09） |
| A7 | BDD 已完整落地、完全达标 | **不成立（高估）** | `plan_linter` 只校验 Given/When/Then 文本；CI 的 acceptance job 跑 `python -m unittest discover`（`quality-gate.yml` 第 213–226 行），不跑 pytest-bdd/Cucumber，也不安装项目依赖 | BDD 目前是"文本格式"，不是"可执行契约"；WP-07 修真实执行 |
| A8 | 缺少属性测试（Hypothesis/fast-check） | **成立（但属增强项）** | `qa/references/qa-protocol.md` 无属性测试内容 | 放 WP-12，不作为门禁 |
| A9 | 需要强化等价变异体甄别规则 | **成立** | `qa-protocol.md` 只定义了 `Equivalent` 并把它从分母剔除，没有判定标准、证据要求或上限 | WP-08 要求等价变异体必须有 justification，并与 MSI 一起审计 |
| A10 | 契约模板定义了 `INVARIANT_IDEMPOTENCY`，但缺系统性自动化探测 | **成立** | `task-decomposition/assets/templates/01-contract.template.md` 第 59–62 行有 `INVARIANT_IDEMPOTENCY_GIVEN/WHEN/THEN` 占位符；`qa-protocol.md` 没有幂等性探针流程 | 作为可选增强（WP-12）；不要把"有占位符"说成"有自动探测" |
| A11 | `03` 第 5 节直接贴原始日志，导致上下文爆炸 | **部分成立** | 模板第 5 节是 `Command / Result / Tests / Coverage` 表（`03-qa-verification.template.md` 第 59–66 行），不是原始日志；但 QA protocol 要求失败时给完整 trace，实践中会膨胀 | 需要"摘要 + 结构化产物"而不是"禁止 trace"；WP-08 加 provenance |
| A12 | Dev 看到具体测试数据后会写特判 | **成立，但渠道说错了** | 真正的读通道是 `.agents/rules/dev.md` 第 9 行 `Read-only: tests/acceptance/**`；Dev 可以直接读 QA 测试源码。`03` 脱敏并不能阻止这一点 | WP-08 做证据绑定与变异交叉核验；WP-10 才谈读隔离；不要声称 03 脱敏能解决 |

### 1.3 第 2 部分 6 个漏洞逐条裁定

| ID | 点评主张 | 裁定 | 证据（v3.1.0） | 对应 WP |
| :--- | :--- | :--- | :--- | :--- |
| B1 | push 到主干时 `gate3-verification` 因 `rbac-audit` skipped 而被连带跳过 | **成立** | `templates/ci/quality-gate.yml` 第 96 行 `if: github.event_name == 'pull_request'`；第 253 行 `needs: [gate1-plan-linter, rbac-audit, complexity-gate, acceptance-tests]`；`gate3` 无 `if:` | WP-01 |
| B2 | Gate 3 是"纸面审计"，未与前序真实产物交叉核对 | **成立，且比点评更严重** | `verification_linter.py` 只解析 `03` Markdown；`--tasks-dir/--json/--strict/--min-msi/--no-mutation`，没有 `--actual-*`；`_lint_qa_mutation` 在第 549 行只要**任一**表格 `compliant` 就整体返回；`tests/unit/test_verification_linter.py` 甚至明确测试"表 1 填、表 2 空也通过" | WP-05 |
| B3 | Stage 2 测试环境在 CI 模板中缺失；acceptance 不装依赖、无就绪探针、无禁网 | **成立** | `quality-gate.yml` 第 201–241 行只有 checkout + setup-python + unittest；`templates/ci/README.md` 第 59–63 行却宣称容器/依赖/Mock/网络隔离 | WP-07 |
| B4 | post-merge 缺 converge，变异测试因 `\|\| true` 变成无牙老虎 | **成立** | `quality-gate.yml` 第 303–328 行：`pip install mutmut \|\| true`、`mutmut run ... \|\| true`、`mutmut results \|\| true`；没有解析 MSI，没有阈值，没有 converge job | WP-06、WP-11 |
| B5 | `Standard library only` 与 CI `pip install tree-sitter` 自相矛盾 | **成立（限定于 complexity_check）** | `quality-engineering/SKILL.md` 第 5 行 compatibility、第 145 行 references 都写 stdlib-only；但 `complexity_check.py` 第 95–110 行可选导入 `tree_sitter_languages`/`tree_sitter`/`lizard`，CI 第 158–161 行安装它们 | WP-03、WP-04、WP-11 |
| B6 | SKILL.md 像 CLI 说明书，缺 Agent 排障/路由 SOP；没有聚合 JSON artifact | **成立** | `quality-engineering/SKILL.md` 只有错误码表，没有"错误码 → 责任角色 → 动作"；`quality-gate.yml` 只写 `$GITHUB_STEP_SUMMARY`，全文件无 `actions/upload-artifact` | WP-03、WP-05 |

### 1.4 点评遗漏的关键缺陷（本手册新增）

| ID | 缺陷 | 证据 | 严重度 | 对应 WP |
| :--- | :--- | :--- | :--- | :--- |
| C1 | `plan-linter` 复制了 Gate 3 的 QA 复杂度/变异审计逻辑，违反"单一职责" | `.agents/skills/plan-linter/scripts/plan_linter.py` 定义并在 `lint()` 中调用 `_lint_qa_complexity`、`_lint_qa_mutation`（约第 1039/1202/1774 行）；`docs/skills-guide.zh-CN.md` §7.2 却明确说它"不审计测试执行证据与变异测试杀伤力" | P1 | WP-02 |
| C2 | 文档错误码与脚本实际错误码不一致，Agent 无法按文档路由 | 文档写 `BASIS_PATH_INSUFFICIENT`、`MUTATION_MISSING_SECTION`、`MUTATION_NO_SCORE`、`MUTATION_SCORE_BELOW_THRESHOLD`、`MUTATION_SCORE_MARGINAL`；脚本实际为 `COMPLEXITY_BASIS_PATH_INSUFFICIENT`、`QA_MISSING_MUTATION_EVIDENCE`、`QA_INVALID_MSI_SCORE`，且没有 marginal warning | P0 | WP-03 |
| C3 | 单元测试里的 `QualityEngineeringTriadAuditor` 只存在于测试文件，却"证明"了生产不存在的零存活关键变异体门禁 | `tests/unit/test_modern_quality_engineering.py` 第 836 行定义；第 996 行测试"survived critical mutant → REWORK"；生产 `verification_linter.py` 无此逻辑 | P0 | WP-05 |
| C4 | 复杂度检查器默认扫描 `.`，排除列表不含 `skills/`、`tools/`、`templates/`、`tasks/`；无 `src/` 的仓库会误报 | `complexity_check.py` 第 49–52 行 `DEFAULT_EXCLUDE_DIRS`；第 410–421 行 `collect_source_files`；在本套件仓库实测 exit 1、29 个 critical violations | P0 | WP-04 |
| C5 | 无 tree-sitter/lizard 时，非 Python 文件被静默跳过（`return []`），门禁"零结果通过" | `complexity_check.py` 第 283–306 行：无第三方引擎且非 `.py` 时返回空列表 | P0 | WP-04 |
| C6 | `03` 的测试用例 ID 是自由文本，没有与真实测试函数/执行报告绑定 | `03-qa-verification.template.md` 第 24–29 行；`verification_linter.py` 只统计 `TC-*` token 数量 | P1 | WP-05、WP-08 |
| C7 | core 模块 MSI ≥ 90% 与"零关键存活变异体"在文档中反复出现，但 Gate 3 不检测 core、不检测 survived critical | `qa/references/qa-protocol.md` 第 127–130 行；`templates/ci/README.md` 第 143–148 行；`verification_linter.py` 无 `core`/`survived` 判定 | P1 | WP-08 |
| C8 | CI 的 acceptance 用 `unittest discover`，与文档宣称的 pytest-bdd/Cucumber 不一致；pytest-bdd 测试可能根本不被收集 | `quality-gate.yml` 第 213–226 行；`docs/skills-guide.zh-CN.md` 第 203–206、543–549 行；`templates/ci/README.md` 第 127–138 行 | P0 | WP-07 |
| C9 | 文档宣称 Gate 2 Reviewer 是 CI 第 7 道门禁，但 `quality-gate.yml` 没有 Gate 2 job | `docs/skills-guide.zh-CN.md` 第 426、486 行；`templates/ci/README.md` 第 74 行；`quality-gate.yml` 只有 6 个 job | P1 | WP-11 |
| C10 | `retry_count` 没有生产工具递增；`04` 事件表没有自动写入者；没有熔断 | 只有 `04-process.template.md` 与测试引用 `retry_count`；`tools/` 无流程工具 | P1 | WP-09 |

### 1.5 你应当如何使用这份点评

- **可信**：B1–B6 的具体 CI 漏洞；A1/A2/A5/A9/A10（作为线索）以及"提示词不是强制层"的判断。
- **不可直接照抄**：A7（BDD 已完成）、A11（03 第 5 节是原始日志）、A12（只靠 03 脱敏就能防作弊）、A6（attempt 已实现）。A10 的事实成立，但"补自动化探针"只是增强项，不是当前门禁缺陷。
- **不要现在做**：A1 的"QA 完全禁读 src"、A3 的"外部 Runner 脱敏摘要"、A12 的"物理级隔离"。这些需要先有工具中介；在工具不存在时直接删读权限，只会让 QA 无法完成现有静态分析/变异测试职责，制造新的造假空间（见 WP-10 的前置条件）。

---

## 2. 真实痛点台账

### 2.1 P0：门禁会"亮绿灯但没守住"

| ID | 痛点 | 证据 | 后果 | WP |
| :--- | :--- | :--- | :--- | :--- |
| P0-1 | push 到 main/master 时 Gate 3 被静默跳过 | `quality-gate.yml` 第 96、253 行 | 主干合并可绕过 Gate 3 | WP-01 |
| P0-2 | Gate 3 只读 QA 自己写的 Markdown，数字可伪造 | `verification_linter.py` 全文；无 `--actual-*` | "假账真审" | WP-05 |
| P0-3 | 变异测试在 CI 中从未真正阻止失败（`\|\| true`） | `quality-gate.yml` 第 322–325 行 | MSI 可以跌到 0% 仍绿 | WP-06 |
| P0-4 | 验收测试不装项目依赖、不跑 BDD runner | `quality-gate.yml` 第 201–241 行 | 测试可能根本没执行/没收集 | WP-07 |
| P0-5 | 复杂度检查器扫描范围错误，且无依赖时静默跳过非 Python | `complexity_check.py` 第 49–52、283–306 行 | 误报或零结果通过 | WP-04 |
| P0-6 | 文档错误码与脚本实际错误码不一致 | 见 C2 | 修复路由必然失败 | WP-03 |
| P0-7 | Gate 3 的"任一表格合规即通过"漏洞 | `verification_linter.py` 第 549–554 行；测试明确覆盖 | 一个漂亮文件可掩盖其他失败 | WP-05 |
| P0-8 | 测试用 `QualityEngineeringTriadAuditor` 证明生产不存在的门禁 | `test_modern_quality_engineering.py` 第 836、996 行 | 测试给人虚假信心 | WP-05 |

### 2.2 P1：防作弊闭环不完整

| ID | 痛点 | 证据 | 后果 | WP |
| :--- | :--- | :--- | :--- | :--- |
| P1-1 | `plan-linter` 越权审计 `03`，与 Gate 3 职责重叠且实现会漂移 | `plan_linter.py` 约第 1039/1202/1774 行 | 两个工具对同一份证据给出不同结论 | WP-02 |
| P1-2 | Dev 可读 `tests/acceptance/**`，可直接针对测试写特判 | `.agents/rules/dev.md` 第 9 行；RBAC 只管写 | Reward Hacking 的真实通道 | WP-08、WP-10 |
| P1-3 | 03 证据没有 artifact 路径/哈希/工具版本，无法绑定真实产物 | `03-qa-verification.template.md` 第 59–66 行 | 手填数字无法证伪 | WP-08 |
| P1-4 | 等价变异体由 QA 自己申报，可用来抬高 MSI | `qa-protocol.md` 第 110–125 行；无 justification | MSI 可被"等价"注水 | WP-08 |
| P1-5 | 没有 Dev→QA 结构化申诉，REWORK 只能改代码 | `02` 模板无 Appeal；全仓 grep 无命中 | 乒乓或迎合式补丁 | WP-09 |
| P1-6 | `retry_count` 不自动递增，无熔断到人的规则 | 模板有字段、工具无实现 | 无限重试 | WP-09 |
| P1-7 | Gate 2 在文档中是 CI 门禁，在模板中不存在 | `quality-gate.yml` 无 Gate 2 job；文档有 | 文档承诺 > 实际保护 | WP-11 |
| P1-8 | core 90% / 零关键存活变异体只写在文档，Gate 3 不检测 | `verification_linter.py` 无 core/survived 逻辑 | 高风险模块保护是纸面的 | WP-08 |

### 2.3 P2：增强项（先不要抢跑）

| ID | 痛点 | 说明 | WP |
| :--- | :--- | :--- | :--- |
| P2-1 | QA 直接读 `src/**`，存在注意力锚定 | 需要先有工具中介（Runner），否则删读权限会破坏 QA 职责 | WP-10 |
| P2-2 | 缺少属性测试（Hypothesis/fast-check） | 增强测试强度，不作为硬门禁 | WP-12 |
| P2-3 | 缺少幂等性/资源清理探针 | 契约有 `INVARIANT_IDEMPOTENCY_*` 场景占位符，但没有自动探测；不要伪造"已自动验证" | WP-12 |
| P2-4 | 没有 held-out 测试集 | 真正防"针对测试硬编码"需要仓库外测试；成本高，先做 P0/P1 | 暂不做 |
| P2-5 | 没有独立 Spec-Judge Agent | 先用 `review` 的仲裁模式与编排路由，避免新增运行时 | WP-09 |

---

## 3. 改造不变量（10 条）

1. **真实性优先于绿色**：能被跳过、被 `|| true` 吞掉、只读自报 Markdown 的门禁，不算门禁。
2. **单一事实源**：错误码、阈值、测试命令、证据 schema 各只有一个权威定义，其余文档引用它。
3. **证据必须可追溯**：任何"通过"都要能指向 `artifact path + SHA-256 + command + tool version`。
4. **提示词不是强制层**：L0 只写 `advisory`；L1/L2 要写清楚能拦住什么、拦不住什么。
5. **职责单一**：Gate 1 不审计 `03` 的复杂度/变异证据（占位符与存在性检查除外）；Gate 3 不做源码分析；CI 不替 QA 写测试。
6. **失败要可路由**：每个错误码必须映射到 owner、动作、升级条件。
7. **双树 + 测试同步**：改技能文件必须双写；改行为必须加/改测试。
8. **Canonical English + 自包含**：技能内引用只能指向自己目录内的文件；`SKILL.md < 200` 行。
9. **向后兼容**：新增字段用可选 + 默认值；不得让历史任务包因模板升级而突然失败。
10. **不夸大**：做不到的隔离/自动化，写成 `manual` 或 `advisory`，不要写成 `physical` 或 `enforced`。

---

## 4. 工作包（严格按顺序执行）

> **状态记录**：每完成一个 WP，把该 WP 标题后的 `[ ]` 改为 `[x]`，并记录验证命令与结果。
> **通用完成判据**：目标测试通过 + 全量单元测试通过 + 双树一致 + 文档同步 + 无新增 `|| true`。

### WP-00 [ ] 基线冻结（不改代码）

**目的**：记录改造前状态，避免把既有失败误判为本次改动引入。

**步骤**
1. 运行 §0.4 的四条命令，保存输出到 `artifacts/baseline/`（该目录不提交，或按 `.gitignore` 处理）。
2. 记录：git commit SHA、Python 版本、单元测试数量、`complexity_check.py` 是否 exit 1（预期 exit 1）、双树是否一致。
3. 检查 `git status` 必须干净；若有未提交改动，先停止并报告。

**完成判据**：`artifacts/baseline/report.md` 存在，包含上述 5 项。

---

### WP-01 [ ] 修复 push 时 Gate 3 被跳过

**优先级**：P0 | **依赖**：无 | **写入范围**：`templates/ci/quality-gate.yml`、`tests/unit/test_modern_quality_engineering.py`

**目标**：`rbac-audit` 在 push 事件 skipped 时，`gate3-verification` 仍然执行。

**步骤**
1. 在 `gate3-verification` job 上新增 `if:`，内容必须同时满足：
   - 使用 `always()`，避免 GitHub Actions 的默认 "needs 里有 skipped 就 skip" 行为；
   - 显式检查 `gate1-plan-linter`、`complexity-gate`、`acceptance-tests` 为 `success`；
   - 允许 `rbac-audit` 为 `success` 或 `skipped`。
2. 保留原有 `needs` 列表不变。
3. 新增测试 `test_gate3_runs_when_rbac_skipped_on_push`（放在 `Tier1` 的 CI 结构测试附近），用字符串/正则解析 YAML，断言 `gate3-verification` job 块内同时出现 `always()`、`needs.rbac-audit.result == 'skipped'`、`needs.acceptance-tests.result == 'success'`。

**关键片段**

```yaml
  gate3-verification:
    name: Gate 3 - Acceptance & MSI Audit
    runs-on: ubuntu-latest
    needs: [gate1-plan-linter, rbac-audit, complexity-gate, acceptance-tests]
    if: |
      always() &&
      needs.gate1-plan-linter.result == 'success' &&
      needs.complexity-gate.result == 'success' &&
      needs.acceptance-tests.result == 'success' &&
      (needs.rbac-audit.result == 'success' || needs.rbac-audit.result == 'skipped')
```

**验证**

```bash
python -m unittest tests.unit.test_modern_quality_engineering -v
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：测试覆盖 push 场景；`quality-gate.yml` 的 Gate 3 job 不会再因 `rbac-audit` skipped 而整体 skip。

**禁止**：不要给 `rbac-audit` 加 `always()` 来"绕过"——那会让它在 push 时执行并因 `pull_request` 字段为空而报错。修 Gate 3 的 `if`，不是改 RBAC 的触发条件。

---

### WP-02 [ ] 让 Gate 1 回到单一职责（移除 plan-linter 中的 Gate 3 逻辑）

**优先级**：P1 | **依赖**：WP-00 | **写入范围**：`plan_linter.py`（双树）、`tests/unit/test_plan_linter.py`、`tests/unit/test_verification_linter.py`、`plan-linter/SKILL.md`（双树）

**目标**：`plan_linter.py` 不再读取 `03-qa-verification.md` 的复杂度/变异表；Gate 3 证据只由 `verification_linter.py` 审计。

**步骤**
1. 在 `plan_linter.py` 中删除 `_lint_qa_complexity`、`_lint_qa_mutation` 两个函数，以及 `lint()` 中对它们的调用（基线约第 1774–1785 行）。
2. 更新模块 docstring：明确 "Gate 1 never audits QA complexity/mutation evidence in 03; that is Gate 3. Placeholder scanning of 03 and existence checks are allowed."（保留 `_scan_placeholders` 对 03 的占位符扫描与四文档存在性检查，不要把它们一起删掉。）
3. 删除 `tests/unit/test_plan_linter.py` 顶部的 `from plan_linter import _lint_qa_mutation, Finding` 中不再需要的导入，并删除 `PlanLinterComplexityTests`（约 862–1038 行）与 `PlanLinterMutationTests`（约 1039–1335 行）。
4. **先确认覆盖迁移**：逐条对照 `tests/unit/test_verification_linter.py`。若以下场景缺失，先补到 verification 测试再删：
   - `QA_PASSED` 未勾选时跳过审计；
   - Section 3 缺失/空表；
   - `V(G) > 15`、`11–15` warning；
   - `Test Cases < V(G)`；
   - Section 4 缺失/空表/低 MSI；
   - 双表（per-file + summary）兼容。
5. 新增回归测试：构造一个 Gate 1 结构合法、但 `03` 中 `QA_PASSED` + 低 MSI 的任务包；断言 `plan_linter.py` exit 0（Gate 1 不越权），而 `verification_linter.py` exit 1。
6. 更新 `plan-linter/SKILL.md`：在 "Do not use when / Responsibilities" 中明确不审计 `03` 的复杂度/变异证据（占位符与存在性检查除外）；删除错误码表中不属于 Gate 1 的 `COMPLEXITY_*`/`QA_*` 码。

**验证**

```bash
python -m unittest tests.unit.test_plan_linter tests.unit.test_verification_linter -v
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir <fixture-dir> --json  # exit 0
python .agents/skills/quality-engineering/scripts/verification_linter.py --tasks-dir <fixture-dir> --strict --json  # exit 1
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：`grep -n "_lint_qa_\|QA_INVALID_MSI_SCORE\|COMPLEXITY_BASIS_PATH_INSUFFICIENT" plan_linter.py` 无命中；Gate 1/Gate 3 行为边界有测试锁定。

**禁止**：不要直接把两个测试类删掉而不迁移覆盖；不要从 `verification_linter.py` 反向 import `plan_linter`（技能必须自包含）。

---

### WP-03 [ ] 建立唯一错误码注册表与 Agent 路由 SOP

**优先级**：P0 | **依赖**：WP-02 | **写入范围**：`quality-engineering/SKILL.md`、`quality-engineering/references/triage-routing.md`（新建，双树）、`plan-linter/SKILL.md`、`docs/skills-guide.zh-CN.md`、`tests/unit/test_error_code_consistency.py`（新建）

**目标**：脚本实际发出的每个错误码都在文档中；文档中的每个错误码都能被脚本发出；每个码都有 owner 与动作。

**步骤**
1. 以脚本为准，统一现有错误码（**不要**改脚本去迎合错误文档）：
   - Gate 3：`COMPLEXITY_MISSING_SECTION`、`COMPLEXITY_EXCEEDS_MAX_THRESHOLD`、`COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD`（warning）、`COMPLEXITY_BASIS_PATH_INSUFFICIENT`、`QA_MISSING_MUTATION_EVIDENCE`、`QA_INVALID_MSI_SCORE`、`EVIDENCE_MISSING_COMMAND`、`EVIDENCE_MISSING_RESULT`。
   - 删除/改写文档中不存在的：`BASIS_PATH_INSUFFICIENT`、`MUTATION_MISSING_SECTION`、`MUTATION_NO_SCORE`、`MUTATION_SCORE_BELOW_THRESHOLD`、`MUTATION_SCORE_MARGINAL`。
   - Gate 1：以 `plan_linter.py` 实际码为准，修正 `TOUCH_FILE_FORBIDDEN` → `FORBIDDEN_TOUCH_FILE`、`BDD_EMPTY_SCENARIO` → `BDD_INVALID_SCENARIO`（若文档有）。
   - RBAC：`QA_EDITED_SOURCE_FILES` → `QA_EDITED_SOURCE`。
2. 新建 `quality-engineering/references/triage-routing.md`（English），表头：
   `Code | Emitted by | Owner | First action | Escalate after | Never do`
   - 至少覆盖 Gate 3 全部代码，以及 `DEV_EDITED_ACCEPTANCE_TESTS`、`QA_EDITED_SOURCE`、`CONTRACT_EDITED_BY_NON_PLANNER`。
3. 在 `quality-engineering/SKILL.md` 增加 `## Failure Triage & Routing`（≤ 15 行），链接该 reference；错误码表改成真实码。
4. 更新 `docs/skills-guide.zh-CN.md` §10 故障排查表与 §7.6 错误码名称。
5. 新增 `tests/unit/test_error_code_consistency.py`：
   - 用正则从 `verification_linter.py`、`plan_linter.py`、`tools/rbac_audit.py` 提取形如 `"[A-Z][A-Z0-9_]{3,}"` 的码；
   - 过滤已知非错误字符串（如 `"STRICT_WARNING"` 可作为 warning code 保留）；
   - 断言：脚本码 ⊆ 对应 SKILL.md 文档码 ∪ 允许的 `LEGACY_` 列表；文档码 ⊆ 脚本码 ∪ 明确标注 `planned` 的列表；
   - 断言：`triage-routing.md` 覆盖所有 Gate 3 码。

**验证**

```bash
python -m unittest tests.unit.test_error_code_consistency -v
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：新增测试通过；`docs/skills-guide.zh-CN.md` 与 `quality-engineering/SKILL.md` 不再出现不存在的码；路由表存在且被链接。

**禁止**：不要新增一个"看起来合理"但脚本不发的码来凑表；不要改脚本错误码只为让旧文档通过（会破坏已有 CI 配置）。

---

### WP-04 [ ] 修正复杂度检查器的扫描范围与"静默零结果"

**优先级**：P0 | **依赖**：WP-03 | **写入范围**：`complexity_check.py`（双树）、`tests/unit/test_complexity_check.py`、`quality-engineering/SKILL.md`、`templates/ci/quality-gate.yml`

**目标**：
- 没有 `src/` 且未显式指定目录时，**报 usage 错误（exit 2）**，而不是扫描 `.` 误报；
- 支持只扫描变更文件；
- 无第三方引擎且非 Python 时，不再静默通过，而是给出明确 warning/error；
- JSON 中包含**全部函数**记录，供 Gate 3 交叉核验。

**步骤**
1. 在 `parse_args()` 增加：
   - `--changed-files PATH`：读取换行分隔路径，只保留这些文件；
   - `--include-all`：保留（可选）；建议默认 JSON 始终输出 `"functions": [...]`。
2. 修改 `main()` / `collect_source_files()`：
   - 若 `args.src_dirs` 为空：仅当 `src/` 存在时使用 `src/`；否则 `sys.stderr.write(...)` 并 `return EXIT_USAGE`；
   - 若提供 `--changed-files`，只扫描列表中的文件（先做 `resolve()` 与 `relative_to(repo_root)` 归一化）；
   - `DEFAULT_EXCLUDE_DIRS` 增加 `"skills"`, `"tools"`, `"templates"`, `"tasks"`, `"docs"`, `"specs"`（即使显式 `src/` 也不应扫到技能脚本）。
3. 修改 `build_report()`：
   - 增加 `"functions": records`（每条含 `file`、`line`、`function`、`vg`）；
   - 保留 `violations`/`warnings`/`passed` 兼容字段。
4. 修改 `scan_file()`：当没有引擎且扩展名非 `.py` 时，返回一个特殊记录或在 `main()` 汇总 `engine_unavailable` 警告；**禁止**静默 `return []` 后整体 `passed=True`。建议：
   - 在报告增加 `"skipped_unsupported": [files]`；
   - 若请求了 `--engine tree-sitter` 但不可用，直接 exit 2。
5. 更新 CI 的 `complexity-gate`：显式传 `--src-dir src`（或项目配置的目录），并把 `artifacts/complexity-report.json` 用 `actions/upload-artifact@v4` 上传（WP-05 使用）。

**关键片段**

```bash
python .agents/skills/quality-engineering/scripts/complexity_check.py \
  --src-dir src \
  --json > artifacts/complexity-report.json
```

**必加测试**

> 若既有 `tests/unit/test_complexity_check.py` 假设"无参数扫描 `.`"或 JSON 只有 `violations/warnings`，按新契约更新这些测试；不要为了让旧测试通过而放弃 fail-closed 行为。

- `test_no_src_and_no_src_dir_returns_usage_error`；
- `test_explicit_src_dir_scans_only_that_tree`；
- `test_changed_files_filters_records`；
- `test_report_contains_all_functions`；
- `test_non_python_without_engine_is_not_silently_passed`（至少断言 `skipped_unsupported` 或 exit 2）。

**验证**

```bash
python -m unittest tests.unit.test_complexity_check -v
python .agents/skills/quality-engineering/scripts/complexity_check.py --json ; echo "exit=$?"  # 本套件仓库应 exit 2
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：本套件仓库不再出现 29 个误报；Gate 3 能拿到包含全部函数的 JSON。

**禁止**：不要用 `|| true` 包住 complexity check；不要为了"让本仓库通过"而把阈值从 15 调到 100。

---

### WP-05 [ ] Gate 3 交叉核验 + 堵住 linter 漏洞

**优先级**：P0 | **依赖**：WP-03、WP-04 | **写入范围**：`verification_linter.py`（双树）、`templates/ci/quality-gate.yml`、`tests/unit/test_verification_linter.py`、`quality-engineering/references/verification-protocol.md`

**目标**：
1. Gate 3 用 CI 真实产物核对 `03` 中的 V(G)，而不是只读 Markdown；
2. 任一表格不合规就失败，不能"任一合规即整体通过"；
3. 双表（per-file 与 summary）数字必须一致。

**步骤**
1. 给 `verification_linter.py` 增加参数：
   - `--actual-complexity PATH`：读取 WP-04 的 JSON；
   - `--repo-root PATH`（默认 `.`）：用于路径归一化；
   - `--require-provenance`（WP-08 使用，可先预留）。
2. 新增 `_read_touch_files(task_dir)`：从 `01-contract.md` 用简单正则读取 `touch_files` 的 `path:` 值；解析失败时返回空集合并发出 `TOUCH_FILES_UNREADABLE` warning（不要静默跳过交叉核验）。
3. 新增 `--require-actual-complexity`：只要该 flag 出现却没有 `--actual-complexity`，直接 `COMPLEXITY_REPORT_MISSING` 失败，避免"本地纸面审计"绕过。新增交叉核验 `_cross_check_complexity(...)`：
   - 建立 actual map：`(posix(file), function) -> vg`；
   - 对 actual report 中属于该 task `touch_files` 的每个函数：
     - 03 的 Section 3 没有对应行 → `COMPLEXITY_FUNCTION_MISSING_IN_03`；
     - V(G) 不一致 → `COMPLEXITY_MISMATCH_WITH_AST`；
   - 对 03 的每一行：actual 中不存在该函数 → `COMPLEXITY_PHANTOM_FUNCTION`（03 伪造/拼错函数）；
   - basis path 判定改用 actual V(G)；
   - 若 `--actual-complexity` 文件缺失/空 → `COMPLEXITY_REPORT_MISSING`。
4. 修复 `_lint_qa_mutation` 的通过逻辑：
   - 现有 `if any(t["compliant"] for t in table_results): return` 改为：**所有含数据的表都必须 compliant**；
   - 若存在双表，要求两表计算出的 MSI/总数一致，否则 `MUTATION_TABLE_INCONSISTENT`；
   - 若某个 per-target 行缺 MSI，整体失败，不能被另一个 100% 的行掩盖。
5. 更新 CI：
   - `complexity-gate` 上传 `complexity-report` artifact；
   - `gate3-verification` 先 `actions/download-artifact@v4` 下载，再运行：
     ```bash
     python .agents/skills/quality-engineering/scripts/verification_linter.py \
       --tasks-dir tasks \
       --actual-complexity artifacts/complexity-report.json \
       --require-actual-complexity \
       --strict --json
     ```
   - 若 Gate 3 失败，上传 `verification-report.json`（便于下游 Agent 读取）。
6. 更新 `verification-protocol.md`：说明 Gate 3 现在需要 `--actual-complexity`，并列出新错误码。
7. 更新/删除测试：
   - 反转 `test_cli_passed_dual_table_table1_filled_table2_blank_passes` 为 `..._fails`；
   - 反转 `test_cli_passed_dual_table_table1_blank_table2_filled_passes`（若两表数字不一致）；
   - 新增 mismatch/missing/phantom 三组测试；
   - 新增 `test_actual_complexity_report_missing_fails`。
8. 删除或改造只存在于测试中的 `QualityEngineeringTriadAuditor`（C3）：
   - 若它只是测试辅助，明确标注 "test-only, not production"；
   - 若要保留"零关键存活变异体"行为，必须在生产 `verification_linter.py` 实现（WP-08），否则删除该测试的误导性名称，避免"测试证明生产行为"。

**验证**

```bash
python -m unittest tests.unit.test_verification_linter -v
python -m unittest discover -s tests/unit -p "test_*.py"
# 手工 fixture：把 03 中 V(G) 改小、或删掉一个高复杂度函数，Gate 3 必须失败
```

**完成判据**：伪造 V(G) 会失败；漏报函数会失败；任一表不合规会失败；CI 真正下载并传入真实复杂度报告。

**禁止**：不要把 `--actual-complexity` 做成"可选且缺失就跳过"（那等于没修）；不要用 Markdown 里的数字反过来"校正"actual 报告。

---

### WP-06 [ ] 变异测试硬门禁（删除 `|| true`）

**优先级**：P0 | **依赖**：WP-03、WP-05 | **写入范围**：`tools/mutation_gate.py`（新建）、`templates/ci/quality-gate.yml`、`tests/unit/test_mutation_gate.py`（新建）、`quality-engineering/SKILL.md`

**目标**：CI 在 push 到 main/master 时真实执行变异测试；MSI < 阈值直接失败；工具缺失/报告缺失也失败（fail closed），不再静默通过。

**步骤**
1. 新建 `tools/mutation_gate.py`（标准库）：
   - 子命令 `run`：执行 `--command`；执行后要求 `--report` 指定的 normalized JSON 存在；
   - 子命令 `check`：只校验已有报告；
   - 参数：`--min-msi 80`、`--report PATH`、`--command "..."`、`--json`；
   - 报告 schema（固定）：
     ```json
     {
       "tool": "mutmut",
       "targets": [
         {"file": "src/auth/service.py", "total": 10, "killed": 8,
          "timed_out": 1, "equivalent": 1, "survived": 0}
       ],
       "msi": 90.0
     }
     ```
   - 计算 MSI = `(killed + timed_out) / (total - equivalent)`；`total - equivalent <= 0` 时按 100%（若 survived=0）或 0%；
   - 退出码：0 pass，1 gate/内容失败，2 用法错误。
   - 缺失报告 → `MUTATION_REPORT_MISSING`；命令非零 → 直接失败；MSI 不足 → `MUTATION_THRESHOLD_FAILED`。
2. 改 `quality-gate.yml` 的 `mutation-active-check`：
   - 删除所有 `|| true`；
   - 从仓库变量 `MUTATION_COMMAND` 读取命令；未配置则失败并提示；
   - 运行 `python tools/mutation_gate.py run --command "$MUTATION_COMMAND" --report artifacts/mutation-report.json --min-msi 80`；
   - 上传 `mutation-report` artifact（`if: always()`）。
3. 提供各栈 adapter 说明（不强制实现所有）：
   - Python：`mutmut run --paths-to-mutate <changed files>` + 生成 normalized JSON 的小脚本；
   - JS/TS：Stryker JSON reporter；
   - 其他栈：由项目提供 `MUTATION_COMMAND` 与报告转换器。
4. 更新 `quality-engineering/SKILL.md`：删除 "optional sequence" 措辞；明确 fail-closed 与 `MUTATION_COMMAND` 配置。
5. 新增 `tests/unit/test_mutation_gate.py`：
   - MSI 90% pass；79.9% fail；
   - missing report fail；
   - invalid JSON fail；
   - `equivalent` 全量导致分母为 0 的边界；
   - 命令行非零退出 fail。

**验证**

```bash
python -m unittest tests.unit.test_mutation_gate -v
grep -n "|| true" templates/ci/quality-gate.yml   # 期望：mutation 段无命中
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：变异路径无 `|| true`；低于阈值必失败；报告 artifact 上传；文档不再把它描述成 optional。

**禁止**：不要把 `MUTATION_COMMAND` 缺失时的行为写成"跳过"；不要用 `continue-on-error` 代替退出码检查。

---

### WP-07 [ ] 验收测试真实可跑（依赖、BDD runner、JUnit、环境探针）

**优先级**：P0 | **依赖**：WP-03、WP-05 | **写入范围**：`templates/ci/quality-gate.yml`、`templates/ci/README.md`、`docs/skills-guide.zh-CN.md`、`tests/unit/test_modern_quality_engineering.py`

**目标**：CI 的 acceptance job 能安装项目依赖、用项目实际的 BDD runner 执行、产出 JUnit/日志 artifact，并在依赖缺失时失败而不是"绿着跳过"。

**步骤**
1. 在 `acceptance-tests` job 中新增 "Install project dependencies" 步骤：
   - `requirements.txt` → `python -m pip install -r requirements.txt`；
   - `pyproject.toml` → `python -m pip install -e .`（若可行）；
   - `package.json` + lock → `npm ci`；
   - `go.mod` → `go mod download`；
   - `Cargo.toml` → `cargo fetch`；
   - 没有声明依赖文件时，输出明确 warning，不假装已安装。
2. 新增 "Environment readiness" 步骤：
   - Python：`python -m pytest --collect-only -q tests/acceptance`（收集失败即失败，能捕获缺依赖/导入错误）；
   - 若无 pytest，退回 `python -m unittest discover -s tests/acceptance -v`。
3. 运行验收测试：
   - 优先 `python -m pytest tests/acceptance -q --junitxml=artifacts/acceptance-junit.xml`（pytest-bdd 测试可被收集）；
   - 否则 `unittest discover` 并 `tee` 日志；
   - 用 `set -o pipefail`，禁止 `|| true`。
4. 网络隔离：
   - 若 `pytest-socket` 已安装，追加 `--disable-socket`；
   - 否则输出 `NETWORK_ISOLATION=advisory`，**不要**在文档中宣称已强制隔离。
5. 上传 `acceptance-test.log` 与 `acceptance-junit.xml`（`if: always()`）。
6. 更新 `templates/ci/README.md` 与 `docs/skills-guide.zh-CN.md`：
   - 把 "pytest-bdd in CI" 改成实际命令；
   - 把 Stage 2 的"容器/网络隔离"改为"模板提供依赖安装与收集探针；网络隔离为 advisory，除非项目启用 pytest-socket"；
   - 删除"100% pass on clean source"这类未经验证的保证，改成"collection + execution 均失败即 fail"。
7. 新增测试（字符串断言）：
   - `quality-gate.yml` 含 `pip install -r requirements.txt` 或依赖安装步骤；
   - 含 `--junitxml`；
   - 不再含 `python -m unittest discover -s tests/acceptance` 作为唯一执行路径（允许作为 fallback）。

**验证**

```bash
python -m unittest tests.unit.test_modern_quality_engineering -v
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：依赖缺失/收集失败会让 job 失败；BDD 测试可被收集；JUnit artifact 存在；文档不再夸大 Stage 2。

**禁止**：不要把 "没有 tests/acceptance 就跳过" 继续写成绿色通过；至少输出 `skipped(no acceptance tests)` 并让 Gate 3 知道。

---

### WP-08 [ ] 证据 provenance、等价变异体与 core profile

**优先级**：P1 | **依赖**：WP-05 | **写入范围**：`03-qa-verification.template.md`、`01-contract.template.md`、`plan_linter.py`（双树，仅接受可选 `risk_level`）、`verification_linter.py`（双树）、`qa-protocol.md`、`verification-protocol.md`、测试

**目标**：`03` 不再只是自报数字；每条关键证据绑定 artifact 与哈希；等价变异体必须有理由；core 任务自动用 90% 阈值。

**步骤**
1. `03` 模板：
   - Section 4 的 KV 表增加一行 `| Equivalent mutant justification |  |`；
   - Section 5 增加 `Artifact path`、`Artifact SHA-256`、`Tool version`、`Timestamp (UTC)`；
   - 不要改 Section 3/4 主表列，避免破坏现有 parser。
2. `01-contract` 模板（可选字段）：
   - 增加 `risk_level: standard`（`standard | core`，默认 `standard`）；
   - `plan_linter.py` 接受该字段，不因缺失而失败；
   - 若模板测试断言 exact frontmatter，更新测试。
3. `verification_linter.py` 增加 `--require-provenance`：
   - 要求 Section 5 的 artifact 路径非空、文件存在（相对 `--repo-root`）、SHA-256 匹配；错误码：
     `EVIDENCE_MISSING_ARTIFACT`、`EVIDENCE_HASH_INVALID`；
   - `Equivalent > 0` 时要求 justification 非空，否则 `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING`；
   - 读取 `01` 的 `risk_level`：`core` 时 `min_msi=90`，错误码沿用 `QA_INVALID_MSI_SCORE`（消息中标注 core）。
4. CI 的 Gate 3 命令加 `--require-provenance`；本地可选。
5. 更新 `qa-protocol.md`：QA 必须把真实 artifact 路径写入 03；等价变异体必须写明为什么语义不变；core 模块清单由 contract 的 `risk_level` 指定。
6. 测试：
   - 缺 artifact → fail；
   - 哈希不符 → fail；
   - `Equivalent=2` 且无 justification → fail；
   - core + MSI 85% → fail，standard + 85% → pass；
   - 历史任务包（无 provenance 字段）在未加 `--require-provenance` 时仍 pass（向后兼容）。

**验证**

```bash
python -m unittest tests.unit.test_verification_linter -v
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：03 的"通过"必须能追到真实文件与哈希；core 阈值生效；旧任务不被误伤。

**禁止**：不要把 `risk_level` 默认成 `core`（会让所有任务变成 90%）；不要要求所有历史 03 立即补哈希。

---

### WP-09 [ ] Appeal 与三层仲裁（不新增运行时）

**优先级**：P1 | **依赖**：WP-02、WP-03 | **写入范围**：`02-dev-workspace.template.md`、`dev-protocol.md`、`review/SKILL.md` + `review/references/arbitration.md`（新建）、`orchestrator.md`、`qa-protocol.md`、`task-decomposition/references/role-lifecycle.md`、测试

**目标**：Dev 面对 `REWORK_REQUIRED` 可以结构化申诉；编排层把申诉路由给独立仲裁者，而不是让 Dev 继续改代码；Spec 歧义升级到 Planner/人。

**步骤**
1. `02-dev-workspace.template.md` 增加 `## 6. Appeal Request`（放在偏差表之后），包含可选 YAML：
   ```yaml
   appeal:
     appeal_id: "AP-001"
     target_case: "TC-02"
     spec_anchor: "#sec-auth-tokens"
     reason: "QA expects 404 for expired tokens; Spec 3.2 specifies 401."
     evidence: "tests/acceptance/test_auth.py::test_expired_returns_401"
     requested_verdict: "TEST_BUG"
   ```
   `requested_verdict` 只能是 `CODE_BUG | TEST_BUG | SPEC_AMBIGUITY`。
2. `dev-protocol.md` 增加 "When to appeal / When not to appeal"：
   - 可以申诉：QA 断言与 contract/spec 明确冲突、测试要求超出 touch_files、Spec 自相矛盾；
   - 不可以申诉：只是实现困难、想绕过 DoD、没有 spec anchor 的主观偏好；
   - **禁止**：为了让测试通过而在业务代码中写针对测试值的特判。
3. `review/SKILL.md` 增加 `## Arbitration mode`，并新增 `references/arbitration.md`（English）：
   - 输入：contract、spec anchor、03 失败证据、Appeal Request；
   - 输出：恰好一个 `CODE_BUG | TEST_BUG | SPEC_AMBIGUITY` + 证据行号 + 动作；
   - 不编辑任何文件；不与 Dev/QA 同源。
4. `orchestrator.md` 增加路由：
   - 检测到 Appeal → 不派给 Dev；派给独立 Reviewer 仲裁；
   - `CODE_BUG` → Dev；`TEST_BUG` → QA；`SPEC_AMBIGUITY` → Planner/人；
   - 同一任务第 3 次 REWORK（或第 2 次 Appeal）→ 熔断到 Planner/人，禁止继续乒乓。
5. `qa-protocol.md` 增加：收到 Appeal 后，QA 不得直接再次 `REWORK_REQUIRED`，必须等待仲裁结果。
6. `role-lifecycle.md` 增加事件码 `APPEAL_RAISED`、`APPEAL_RESOLVED`；**不要**把这些示例事件写进 `04` 模板（现有测试明确禁止模板含示例事件）。
7. 测试：
   - 02 模板包含 Appeal 字段且不破坏现有模板测试；
   - `review/SKILL.md` 的相对链接能解析；
   - `orchestrator.md` 含 `Appeal` 与 `SPEC_AMBIGUITY`；
   - 04 模板仍无示例事件码。

**验证**

```bash
python -m unittest tests.unit.test_task_templates tests.unit.test_review_skill -v
python -m unittest discover -s tests/unit -p "test_*.py"
```

**完成判据**：申诉有模板、有仲裁角色、有路由、有熔断；不新增运行时依赖。

**禁止**：不要新建一个 `spec-judge` 技能目录（会破坏 "11 个技能" 的测试与分发契约）；仲裁作为 `review` 的一种模式实现。

---

### WP-10 [ ] QA 读隔离：先做工具中介 Runner（P2，必须后置）

**优先级**：P2 | **依赖**：WP-05、WP-06 | **写入范围**：`tools/qa_runner.py`（新建）、`qa/SKILL.md`、`qa/references/qa-protocol.md`、`qa/references/role-boundaries.md`、`.agents/rules/qa.md`、测试

**目标**：为"QA 不直接读 `src/**`"提供可行路径；在 Runner 可用前，**不得**直接删除 QA 的读权限。

**步骤**
1. 新建 `tools/qa_runner.py`（标准库），子命令：
   - `complexity --task <dir> --out artifacts/qa-complexity.json`；
   - `mutation --task <dir> --command "..." --out artifacts/qa-mutation.json`；
   - `summarize --complexity ... --mutation ... --out artifacts/qa-tool-summary.json`。
2. 摘要只包含：文件路径、函数名、行号、V(G)、变异算子/位置、killed/survived 计数、失败测试名；**禁止**包含源码行、测试数据、断言体。
3. `qa/SKILL.md` / `qa-protocol.md` 改为：
   - "若 `tools/qa_runner.py` 可用，优先用它；只读 summary，不直接打开 `src/**`"；
   - "若 Runner 不可用，允许直接读源码，但必须在 `03` 的 Evidence 中记录原因，并标注 `ADVISORY_READ_ISOLATION`"。
4. `role-boundaries.md` / `.agents/rules/qa.md` 改成"默认不直接读；例外需记录"，并保留"不能写 src"的硬边界。
5. 测试：
   - summary 不含源码文本（用 sentinel 字符串断言）；
   - 缺 Runner 时提示信息正确；
   - 不改变 QA 写边界。

**完成判据**：Runner 可用、输出脱敏、文档更新；没有 Runner 时，仍明确 "prompt-only / advisory"。

**禁止**：不要在 Runner 未实现时把 `.agents/rules/qa.md` 的 `Read-only: src/**` 删掉；那会让 QA 既不能读也不能完成变异/复杂度分析。

---

### WP-11 [ ] 文档 / CI / 技能一致性清理

**优先级**：P1 | **依赖**：WP-01 至 WP-09 | **写入范围**：`docs/skills-guide.zh-CN.md`、`templates/ci/README.md`、`.agents/skills/README.md` + `skills/README.md`、`AGENTS.md`、`quality-engineering/SKILL.md`、`verification-protocol.md`、`qa-protocol.md`

**目标**：删除所有"文档承诺 > 实际实现"的表述；让文档、脚本、CI 三者的命令/错误码/阶段定义一致。

**必须修正的清单**

| 位置 | 当前问题 | 改为 |
| :--- | :--- | :--- |
| `docs/skills-guide.zh-CN.md` 第 16 行 | Gate 1 / Gate 3 说成 stdlib-only 本身没错，但同段容易被误读为 `complexity_check` 也 stdlib（非错误，属澄清项） | 保留 Gate 1/Gate 3 的 stdlib 描述；在 §5.2/§5.3 明确 `complexity_check` 的 tree-sitter/lizard 是可选依赖，Python AST 只是 fallback |
| `docs/skills-guide.zh-CN.md` 第 203–206 行 | 宣称 CI 使用 pytest-bdd/Cucumber | 写清"本地 QA 使用；CI 模板在 WP-07 后使用 pytest/JUnit，其他栈用项目命令" |
| `docs/skills-guide.zh-CN.md` 第 213、483 行 | `--strict` 出现在文档，CI 未传 | WP-05 后 CI 命令加 `--strict`，文档与之一致 |
| `docs/skills-guide.zh-CN.md` §6.2 | Stage 2 说容器/网络隔离已由 quality-engineering 提供 | 改为"模板提供依赖安装/收集探针；容器与网络隔离为项目责任/advisory" |
| `docs/skills-guide.zh-CN.md` §6.3 第 7 项 | Gate 2 被列为 CI 门禁 | 改为"人工/Reviewer 步骤；CI 模板不包含 Gate 2 job"或补 Gate 2 job |
| `docs/skills-guide.zh-CN.md` §6.4 | converge 被说成自动触发 | 改为"manual/optional workflow；未配置时不会自动运行" |
| `docs/skills-guide.zh-CN.md` §10 | 错误码与脚本不一致 | 按 WP-03 的注册表改写 |
| `templates/ci/README.md` 第 4–6 行 | "deliberately minimal and stdlib-only; no marketplace action" | 若 WP-05 使用 `upload-artifact/download-artifact`，改为"uses actions/checkout, setup-python, upload-artifact, download-artifact"；stdlib 限定到脚本 |
| `templates/ci/README.md` 第 59–63 行 | Stage 2 容器/网络隔离已提供 | 同 guide，改为诚实描述 |
| `templates/ci/README.md` 第 74 行 | Gate 2 在 CI 中 | 删除或标注 manual |
| `templates/ci/README.md` 第 220–231 行 | required checks 列 Gate 3 | 保留，但补 `if: always()` 说明 |
| `.agents/skills/README.md` 第 137 行 | 路径 `qa/scripts/verification_linter.py` 不存在 | 改为 `quality-engineering/scripts/verification_linter.py` |
| `.agents/skills/README.md` 第 12–15 行 | "single source of truth" 与双树并存 | 改为"two mirrored distributions; `.agents/skills` is the runtime tree" |
| `AGENTS.md` | `plan-linter` 单一职责描述与代码不符（WP-02 后一致） | 补 "Gate 3 cross-validates real artifacts; mutation gate is fail-closed" |
| `quality-engineering/SKILL.md` 第 5 行 | compatibility stdlib-only | 改为"Core linters standard library only; multi-language complexity uses optional tree-sitter/lizard with Python AST fallback" |
| `quality-engineering/SKILL.md` 第 145 行 | references 把 `complexity_check.py` 说成 stdlib-only | 改为"stdlib fallback for Python; optional tree-sitter/lizard for other languages" |
| `quality-engineering/SKILL.md` 第 151–156 行 | Honest limits 已承认 Gate 3 依赖 03 | 补充"CI 现在交叉核验 actual artifact；仍不能替代人工评审" |
| `verification-protocol.md` | 只说三个 section | 补 provenance、actual artifact、core profile、新错误码 |

**步骤**
1. 先完成 WP-01 至 WP-09，再按上表逐项修改；不要提前把未实现的 CI 写成已实现。
2. 同步 `skills/README.md` 与 `.agents/skills/README.md`（两文件当前 byte-identical）。
3. 新增 `tests/unit/test_docs_consistency.py`：
   - 断言 `docs/skills-guide.zh-CN.md` 不出现 `qa/scripts/verification_linter.py`；
   - 断言 `templates/ci/README.md` 若出现 `upload-artifact`，则不再出现 "no marketplace action"；
   - 断言 `quality-engineering/SKILL.md` 的 compatibility 含 `optional` 或 `fallback`；
   - 断言 `quality-gate.yml` 的 Gate 3 命令含 `--actual-complexity`（WP-05 后）。
4. 运行全量测试。

**完成判据**：文档不承诺未实现的能力；命令、错误码、阶段名称与代码一致；一致性测试通过。

**禁止**：不要为了通过一致性测试而改测试断言去容忍旧错误；先修文档/代码。

---

### WP-12 [ ] 可选增强（P2，做完 P0/P1 再考虑）

**优先级**：P2 | **依赖**：WP-08 | **写入范围**：`qa-protocol.md`、`spec-generator` 模板、`verification_linter.py`

**候选（逐项独立提交，不要打包）**
1. **属性测试**：在 `qa-protocol.md` 增加 "When the stack supports it, add property-based tests (Hypothesis / fast-check) for invariants; property tests supplement, never replace BDD/mutation."
2. **幂等性探针**：在 `qa-protocol.md` 增加重复调用/超时/状态回滚的轻量探针模板；`INVARIANT_IDEMPOTENCY_*` 占位符存在不等于已有自动探测。
3. **等价变异体规则**：定义"语义等价"的判定证据（覆盖、人工复核、工具标记），要求 reviewer 抽查；可增加 `Equivalent / Total` 上限 warning，但不要直接当硬错误。
4. **linter strict 语义**：`--strict` 已在；补 `MUTATION_SCORE_MARGINAL` warning（若需要）或删除文档中的该码；保证不复现"文档有、脚本无"。

**完成判据**：每项有独立测试/文档；不改变 P0/P1 的门禁语义。

---

### WP-13 [ ] 最终回归与发布

**优先级**：P0 | **依赖**：全部 P0/P1 | **写入范围**：`CHANGELOG.md`、`VERSION`、`docs/skills-compatibility.md`、最终报告

**步骤**
1. 运行 §0.4 全部命令；额外运行：
   ```bash
   python -m unittest discover -s tests/unit -p "test_*.py"
   python -m unittest tests.unit.test_modern_quality_engineering -v
   ```
2. 检查禁止项：
   ```bash
   grep -R "|| true" templates/ci tools .agents/skills/quality-engineering/scripts
   grep -R "continue-on-error" templates/ci
   grep -R "Standard library only" .agents/skills/quality-engineering
   ```
   `|| true` 在 mutation/acceptance/gate 路径必须为 0；`continue-on-error` 必须为 0 或有明确说明。
3. 检查双树：
   ```bash
   python -m unittest tests.unit.test_modern_quality_engineering.Tier1FeatureCoverageTests.test_f18_dual_tree_mirror_synchronization
   ```
4. 检查 `SKILL.md` 行数 < 200、canonical 文件无 CJK、相对链接可解析。
5. 更新 `CHANGELOG.md`（Added/Changed/Fixed 对应 WP）；`VERSION` 建议 `3.1.1`（若只做修复）或 `3.2.0`（若新增错误码/schema）；更新 `docs/skills-compatibility.md`。
6. 写最终报告：每个 WP 的改动文件、测试结果、未完成项（若有）与诚实限制。

**完成判据**：全量测试通过；双树一致；无 `|| true` 关键路径；文档与代码一致；最终报告存在。

---

## 5. 最终验收矩阵

| 验收项 | 通过条件 | 验证命令 |
| :--- | :--- | :--- |
| Gate 3 不再被 push 跳过 | Gate 3 job 有 `always()` + skipped 分支 | 读 `quality-gate.yml`；WP-01 测试 |
| Gate 3 交叉核验 | `--actual-complexity` 存在且 CI 传入 | WP-05 测试 + CI 文件断言 |
| 变异测试硬门禁 | 无 `\|\| true`；MSI < 阈值 exit 1 | WP-06 测试；`grep` |
| 验收测试真实执行 | 依赖安装 + 收集探针 + JUnit | WP-07 测试；CI 文件断言 |
| 复杂度扫描范围正确 | 无 `src/` 时 exit 2；显式目录才扫描 | WP-04 测试 |
| 错误码唯一 | 脚本码 ↔ 文档码一致；路由表覆盖 | WP-03 测试 |
| 单一职责 | `plan_linter.py` 不含 `_lint_qa_*` | `grep` + WP-02 测试 |
| 证据可追溯 | 03 含 artifact/hash；core 90% | WP-08 测试 |
| 申诉与仲裁 | 02 模板 + review 仲裁 + orchestrator 路由 | WP-09 测试 |
| 文档诚实 | 无未实现承诺；一致性测试通过 | WP-11 测试 |
| 回归 | 312+ tests passed；双树一致 | §0.4 |

---

## 6. 卡住时的处理（不要硬猜）

1. **测试与文档冲突**：以 `VERSION` 对应的代码行为为准，先修文档；如果代码行为本身就是缺陷（本文已列出），先修代码并补测试。
2. **双树同步冲突**：先修改 `.agents/skills`，再逐字节复制到 `skills/workflow`（或反之），最后运行 `test_f18`；不要手工"近似"。
3. **CI YAML 语义不确定**：不要凭记忆写 GitHub Actions 表达式；在 PR 上用最小改动验证，或保留 `if:` 的字符串测试。无法验证时，把行为写成 `manual`，不要声称已强制。
4. **需要新增第三方依赖**：只能用于 CI job（如 tree-sitter、pytest），不能成为 `plan_linter` / `verification_linter` 的硬依赖；脚本必须保留 stdlib fallback 或明确 exit 2。
5. **连续两次修复失败**：停止，输出：失败的 WP、命令、完整错误、已尝试的改动、怀疑的根因。不要继续扩大 diff。
6. **发现本文之外的严重漏洞**：记录到最终报告，不要在本 WP 中顺手修；除非它导致当前 WP 无法验证。

---

## 附录 A：文件地图与双树映射

| 逻辑对象 | 运行时树（Agent 读取） | 分发树（插件/npx） |
| :--- | :--- | :--- |
| 技能 | `.agents/skills/<name>/` | `skills/workflow/<name>/` |
| 平台技能 | `.agents/skills/diagnose-windows-sandbox-acl/` | `skills/platform/diagnose-windows-sandbox-acl/` |
| 技能索引 | `.agents/skills/README.md` | `skills/README.md` |
| CI 模板 | `templates/ci/` | 同左（不分发树） |
| 工具 | `tools/` | 同左 |
| 测试 | `tests/unit/` | 同左 |
| 文档 | `docs/` | 同左 |

**关键文件职责**
- `templates/ci/quality-gate.yml`：唯一 CI 主流水线模板。
- `templates/ci/plan-gate.yml` / `rbac-gate.yml`：独立门禁模板。
- `.agents/skills/quality-engineering/scripts/complexity_check.py`：源码复杂度扫描。
- `.agents/skills/quality-engineering/scripts/verification_linter.py`：Gate 3 证据审计。
- `.agents/skills/plan-linter/scripts/plan_linter.py`：Gate 1 契约审计。
- `tools/rbac_audit.py`：基于 git diff 的写边界审计。
- `tools/mutation_gate.py`（WP-06 新建）：变异测试硬门禁。
- `tools/qa_runner.py`（WP-10 新建）：QA 脱敏工具中介。

---

## 附录 B：目标错误码注册表（改造后）

> 用途：WP-03 的对照表；实现时以脚本为准，文档引用此表。`Owner` 是首个责任角色；`Escalate` 是升级条件。

| Code | 来源 | Owner | First action | Escalate |
| :--- | :--- | :--- | :--- | :--- |
| `COMPLEXITY_MISSING_SECTION` | Gate 3 | qa | 填 Section 3 表 | 第二次仍缺 → lead |
| `COMPLEXITY_EXCEEDS_MAX_THRESHOLD` | Gate 3 | dev | 重构拆分函数 | 无法拆分 → planner 拆任务 |
| `COMPLEXITY_EXCEEDS_STANDARD_THRESHOLD` | Gate 3 warning | dev | 在 02 写架构理由 | `--strict` 时视为错误 |
| `COMPLEXITY_BASIS_PATH_INSUFFICIENT` | Gate 3 | qa | 补独立路径用例 | 路径不可测 → dev/planner |
| `QA_MISSING_MUTATION_EVIDENCE` | Gate 3 | qa | 补 Section 4 证据 | 工具不可用 → quality-engineering |
| `QA_INVALID_MSI_SCORE` | Gate 3 | qa/dev | 补强断言或删死代码 | MSI 仍低 → planner |
| `EVIDENCE_MISSING_COMMAND` | Gate 3 | qa | 填真实命令 | — |
| `EVIDENCE_MISSING_RESULT` | Gate 3 | qa | 填真实结果 | — |
| `COMPLEXITY_REPORT_MISSING` *(new)* | Gate 3 | quality-engineering | 检查 artifact 上传/下载 | CI 配置错误 → lead |
| `COMPLEXITY_MISMATCH_WITH_AST` *(new)* | Gate 3 | qa | 用 actual 值重填 03 | 重复伪造 → lead |
| `COMPLEXITY_FUNCTION_MISSING_IN_03` *(new)* | Gate 3 | qa | 补列所有 touch_files 函数 | 漏列第二次 → lead |
| `COMPLEXITY_PHANTOM_FUNCTION` *(new)* | Gate 3 | qa | 删除不存在的函数行 | 伪造 → lead |
| `MUTATION_REPORT_MISSING` *(new)* | mutation gate | quality-engineering | 配置 `MUTATION_COMMAND` 并生成报告 | 无可用工具 → lead 决策 |
| `MUTATION_THRESHOLD_FAILED` *(new)* | mutation gate | dev/qa | 击杀存活变异体或删死代码 | 仍低 → planner |
| `MUTATION_TABLE_INCONSISTENT` *(new)* | Gate 3 | qa | 统一 per-file 与 summary | 重复 → lead |
| `EVIDENCE_MISSING_ARTIFACT` *(new)* | Gate 3 | qa | 填 artifact 路径 | — |
| `EVIDENCE_HASH_INVALID` *(new)* | Gate 3 | qa/quality-engineering | 重新生成/核对哈希 | 重复 → lead |
| `MUTATION_EQUIVALENT_JUSTIFICATION_MISSING` *(new)* | Gate 3 | qa | 写明等价理由 | 滥用 → lead |
| `DEV_EDITED_ACCEPTANCE_TESTS` | RBAC | dev | revert 测试改动 | 重复 → lead |
| `QA_EDITED_SOURCE` | RBAC | qa | revert 源码改动 | 重复 → lead |
| `CONTRACT_EDITED_BY_NON_PLANNER` | RBAC | planner | 由 Planner 重写契约 | 重复 → lead |

---

## 附录 C：命令速查

```bash
# 全量单元测试
python -m unittest discover -s tests/unit -p "test_*.py"

# 单模块
python -m unittest tests.unit.test_verification_linter -v
python -m unittest tests.unit.test_plan_linter -v
python -m unittest tests.unit.test_complexity_check -v

# 双树一致性
python -m unittest tests.unit.test_modern_quality_engineering.Tier1FeatureCoverageTests.test_f18_dual_tree_mirror_synchronization

# Gate 1
python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --json

# Gate 3（改造后）
python .agents/skills/quality-engineering/scripts/verification_linter.py \
  --tasks-dir tasks \
  --actual-complexity artifacts/complexity-report.json \
  --require-actual-complexity \
  --require-provenance \
  --strict --json

# 复杂度（改造后，显式目录）
python .agents/skills/quality-engineering/scripts/complexity_check.py \
  --src-dir src --json > artifacts/complexity-report.json

# 变异硬门禁（改造后）
python tools/mutation_gate.py run \
  --command "$MUTATION_COMMAND" \
  --report artifacts/mutation-report.json \
  --min-msi 80
```

---

## 附录 D：点评速查（哪些信、哪些不信）

**可信（按此改造）**
- CI 6 漏洞：push 跳过 Gate 3、纸面审计、Stage 2 缺失、`|| true`、stdlib 矛盾、缺路由/产物。
- "提示词不是强制层；CI 才是"。
- "QA 可能读 src、Dev 可能读测试"这一风险方向。

**不可信/需校正**
- "BDD 已完整落地" → 实际只有文本校验，CI 不跑 BDD。
- "03 第 5 节是原始日志" → 实际是表格；但 trace 膨胀风险存在。
- "契约有 `INVARIANT_IDEMPOTENCY`" → 点评这句是对的（占位符存在），但重点应是"没有自动探测"；只能算增强项。
- "attempt 计数已具备" → 只有模板字段，无工具。
- "隐藏 03 数据就能防 Dev 特判" → 真正的读通道是 `tests/acceptance/**`，需另做隔离。
- "QA 完全禁读 src 即可" → 会破坏 QA 的静态分析/变异职责；需先做 Runner。

**点评没看到、但更严重的**
- `plan-linter` 复制 Gate 3 逻辑（C1）。
- 错误码文档与脚本漂移（C2）。
- 测试专用 `QualityEngineeringTriadAuditor` 证明生产不存在的门禁（C3）。
- 复杂度扫描器默认扫 `.`、静默跳过非 Python（C4/C5）。
- `03` 证据无 artifact 绑定、无 core 90% 检测（C6/C7）。
- CI 用 unittest 而非 BDD（C8）。
- Gate 2 在文档中但不在 CI（C9）。

---

**文档版本**：1.0（2026-10-19）  
**适用基线**：Agent Skills v3.1.0  
**维护者**：执行本手册的 Agent 在每次 WP 完成后更新 §4 的复选框与最终报告。
