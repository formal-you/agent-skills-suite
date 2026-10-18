# Spec Generator - 中文速查（可选）

本文件是 `SKILL.md` 的简体中文摘要，便于中文用户快速理解；以英文 `SKILL.md` 为准。

## 何时使用

- 用户提供 PRD，要求架构设计、ADR 或技术规格。
- PRD 中存在 `FORK-*` 需要形成明确决策。
- 下游任务拆解需要稳定的 `#sec-*` 锚点、`NFR-###` 指标与 `INV-###` 不变量。

## 何时不用

- 需求还模糊或缺少 PRD：先用 `prd-generator`。
- 任务是实现或任务切片；或用户只需要解释现有规格。

## 产物

- `.specs/adr/NNN-title.md`（每个已接受决策一份 ADR）
- `.specs/02-tech-spec.md`（权威聚合文档）
- `.specs/02-tech-spec/`（topology、database-schema、api-contracts、system-invariants）

## 流程

1. 摄入 PRD，复用全部 `REQ/CON/NFR/FORK` 与 `#sec-*` 锚点，不重命名下游消费的锚点。
2. 四角色架构评审（架构、安全合规、性能、YAGNI/极简）。支持子代理工具时派发独立评审；否则同会话逐一评审。仅安全合规角色对用户明确的硬约束拥有一票否决。
3. 每个 `FORK-*` 形成 ADR：至少两个方案、决策理由、后果与接受的权衡。未决分歧必须上报，不得静默选择。
4. 可选：`python scripts/scaffold.py --out .specs` 生成骨架。
5. 按 `references/spec-format.md` 与 `references/project-conventions.md` 撰写；替换全部 `{{UPPER_SNAKE}}`。
6. 可选：`python scripts/lint_spec.py .specs` 校验，全部通过再交接。
7. 交接给 `task-decomposition`。

## 底线

- 不引入 PRD/ADR 未要求的组件、数据表或接口。
- 模板中的基础设施、数据库、语言与数值都是示例，不是默认答案。
- 不把多租户、特定框架或协议当作通用假设。
- ADR 必须包含 Status、Context、Considered Options、Decision、Consequences。
