# PRD Generator - 中文速查（可选）

本文件是 `SKILL.md` 的简体中文摘要，便于中文用户快速理解；以英文 `SKILL.md` 为准。

## 何时使用

- 用户要 PRD、产品需求、功能范围、MVP 边界或 PRD 修订。
- 一句想法、零散笔记或残缺草稿需要变成结构化需求文档。
- 下游需要稳定的 `REQ/CON/NFR/FORK` 编号与 `#sec-*` 锚点。

## 何时不用

- 架构决策、ADR、技术规格：先完成 PRD，再用 `spec-generator`。
- 只需要总结现有文档，或任务是实现、测试设计、任务切片。

## 产物

- `.specs/01-prd.md`（权威聚合文档）
- `.specs/01-prd/`（模块化副本：overview、features、constraints、nfr、forks）

## 流程

1. 需求摄入与澄清，只向用户询问真正阻塞决策的问题。
2. 四角色评审（产品架构、商业合规、用户体验、可行性/YAGNI）。宿主支持子代理工具时派发独立评审；否则在同一会话中按角色逐一评审。合规角色仅对用户明确给出的硬约束拥有一票否决。
3. 收敛并记录 `FORK-*`（至少两个可行方案与决策动因），不在 PRD 中预选方案。
4. 可选：在仓库根目录执行 `python .agents/skills/prd-generator/scripts/scaffold.py --out .specs` 生成骨架。
5. 按 `references/prd-format.md` 撰写产物；替换所有 `{{UPPER_SNAKE}}` 占位符。
6. 可选：`python .agents/skills/prd-generator/scripts/lint_prd.py .specs` 做结构校验，全部通过再交接。
7. 交接给 `spec-generator`。

## 底线

- 不脑补用户未提供的实体、角色、集成或合规要求。
- 模板只是骨架，示例值不得写入产物。
- 最终产物不得残留 `{{...}}`、`[TBD]`、`TODO`。
