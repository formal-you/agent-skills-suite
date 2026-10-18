# 多语言 CI 参考模板（Stack Profiles）

> 适用对象：使用 `quality-engineering` skill 搭建/调整 CI 的 Agent 与工程师。
> 关联文档：[CI 门禁模板说明](../templates/ci/README.md)、[技能使用指南](skills-guide.zh-CN.md)、[门禁加固手册](skills-remediation.zh-CN.md)。

## 1. 为什么不是"一个 YAML 适配所有项目"

`templates/ci/quality-gate.yml` 是 **Python-first、GitHub Actions-first、spec-driven** 的参考实现，不是通用 CI 产品。它把门禁不变量（Gate 1/2/3、RBAC、证据、fail-closed、artifact、triage）固定下来，但栈相关命令仍是 Python 的：

- `setup-python`
- `--src-dir src`
- `pytest` / `unittest`
- `requirements.txt` / `pyproject.toml`
- `mutmut`

如果直接把它复制到 Node/Go/Java/Rust/.NET/C++ 项目，常见结果是"装了依赖但没跑该栈的测试"。

因此新增 `templates/ci/profiles/`：**每个栈一份参考片段**。项目保留不变量，只替换：

1. 工具链 setup；
2. 依赖安装；
3. 验收测试 + JUnit 报告；
4. 变异工具 + 归一化报告 adapter；
5. 真实中间件 services（如需要）。

## 2. Profile 目录

| 文件 | 栈 | 工具链 | 验收/JUnit | 变异工具 |
| :--- | :--- | :--- | :--- | :--- |
| `profiles/python.yml` | Python | `setup-python` | pytest `--junitxml` | mutmut |
| `profiles/node.yml` | Node.js / TS | `setup-node` | Cucumber.js JUnit / Jest | Stryker |
| `profiles/go.yml` | Go | `setup-go` | gotestsum JUnit | go-mutesting |
| `profiles/java.yml` | Java / Kotlin | `setup-java` + Maven | Surefire XML | PITest |
| `profiles/rust.yml` | Rust | rust-toolchain | cargo-nextest + cargo2junit | cargo-mutants |
| `profiles/dotnet.yml` | C# / .NET | `setup-dotnet` | JUnit logger / TRX adapter | Stryker.NET |
| `profiles/cpp.yml` | C / C++ | CMake + compiler | CTest `--output-junit` | Mull |

机器可读目录：`profiles/index.json`。  
配置形状示例：`quality-gate.config.example.json`。

> Profile 是**参考片段**，不是可直接运行的完整 workflow；`quality-gate.yml` 仍是 Python 的 canonical 参考。

## 3. 采纳步骤

1. 根据技术栈选择 profile。
2. 把 profile 的 `toolchain.setup`、`install`、`acceptance`、`mutation` 块复制进你的 `quality-gate.yml`（或项目自己的 CI）。
3. 为变异工具实现归一化报告 adapter（见 §4）。
4. 如果验收依赖真实中间件，增加 `services:` 或 testcontainers（见 §5）。
5. 保留 Gate 1、RBAC、complexity、Gate 3、artifact 上传/下载和 fail-closed 语义。
6. 先跑通本项目 CI，再把它设为 required status checks。

## 4. 变异报告 adapter 契约

所有 profile 最终都必须产出 `artifacts/mutation-report.json`：

```json
{
  "tool": "mutmut",
  "targets": [
    {
      "file": "src/auth/service.py",
      "total": 10,
      "killed": 8,
      "timed_out": 1,
      "equivalent": 1,
      "survived": 0
    }
  ]
}
```

`killed + timed_out + equivalent + survived <= total`。`tools/mutation_gate.py` 会重新计算 MSI，不信任报告里手填的 `msi`。

各栈的原始报告不同：

- Stryker: `reports/mutation/mutation.json`
- PITest: `target/pit-reports/mutations.xml`
- cargo-mutants: `mutants.out/` 文本
- Stryker.NET: `StrykerOutput/**/reports/mutation-report.json`
- Mull: `mull-report.sqlite` / stdout

Adapter 属于项目（或 profile 的使用者），不属于通用门禁；它只做格式转换，不改变击杀结果。

## 5. Mock 还是真实中间件

这与 `qa` 的黑盒策略一致：

- 外部第三方（支付、邮件、SaaS）→ mock/stub/fake + contract test；
- 被测系统本身 → 绝不 mock；
- 数据库/事务/唯一约束/队列/缓存/认证等契约关键边界 → 优先真实中间件；
- 本地 QA 可用 testcontainers/docker compose；CI 必须在 job 里显式 `services:` 或由测试自拉起，不能假设 runner 上已有服务；
- 环境必须在 `03-qa-verification.md` 记录：镜像/tag、启动方式、种子数据、mock 范围。

## 6. 当前模板能力与限制

**已具备**

- 门禁顺序、fail-closed 语义、artifact 交叉核验；
- Python 参考实现可直接用；
- 各栈 setup/install/验收/变异的参考片段；
- 归一化变异报告契约与 `mutation_gate.py`；
- `triage-routing.md` 错误码路由。

**仍不提供**

- 一个能自动识别所有栈并运行的统一 workflow；
- 内置 `services:` 或容器编排；
- 各栈 mutation adapter 的完整实现；
- 在真实多语言项目上的端到端验证。

这些限制是刻意保留的：通用的是**方法论与契约**，不是把 N 种栈硬编码进一个 YAML。

## 7. 推荐演进

1. 以 `profiles/` 为参考，按仓库实际栈裁剪 `quality-gate.yml`；
2. 把 mutation adapter 作为项目内小脚本维护，并加样本测试；
3. 多语言 monorepo 用 matrix 或 per-package job，不要在一个 job 里串所有栈；
4. 需要真实中间件时，优先 testcontainers（本地+CI 一致），其次 GitHub Actions `services:`；
5. 为 profile 增加一个 smoke-test fixture 仓库，验证 setup/acceptance/mutation 三段命令真实可跑。
