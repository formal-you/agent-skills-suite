# CI Stack Profiles

`quality-gate.yml` is a **reference implementation**, not a universal pipeline. It is Python-first
and GitHub Actions-first. This directory provides per-stack reference profiles so a project can keep
the invariant gates (Gate 1/2/3, RBAC, evidence, fail-closed mutation, artifacts, triage) while
replacing only the stack-specific commands.

## Important

- Profiles are **reference fragments**, not standalone workflows. Merge the relevant blocks into
  your adapted `quality-gate.yml`, or use them as an adoption checklist. Copying the shipped
  Python workflow unchanged and stopping there is not adoption.
- `quality-gate.yml` remains the canonical Python reference. Each adopting project must merge its
  stack profile's real BDD/acceptance and mutation commands into that workflow (for example
  Cucumber.js + Stryker for Node, Godog + go-mutesting for Go, cargo-mutants for Rust).
- PR-stage mutation is **mandatory and fail-closed**. The mutation job runs on every
  `pull_request` and on `push` to trunk; a missing command, command failure, missing report or
  MSI below the floor fails the PR. Do not move mutation back to a post-merge-only job.
- The real mutation command is config-driven: copy `../quality-gate.config.example.json` or the
  matching `*.config.json` in this directory to `quality-gate.config.json` with
  `mutation.command`, `mutation.report`, `mutation.min_msi` and `mutation.core_min_msi`, and the
  workflow passes it via `mutation_gate.py run --config`. This replaces
  the empty `MUTATION_COMMAND` repository variable; the variable remains a fallback only.
- A profile is not validated against a real project in this repository. Treat it as a starting
  point; run it in your own CI and adjust tool versions, paths, services and report adapters.
- Do not wrap gate commands in `|| true` or make them non-blocking.

## Available profiles and ready-to-copy configs

Seven reference fragments cover the stack-specific blocks. Four of them also ship a
**ready-to-copy config file** with real, executable commands (no empty placeholders): copy the
`*.config.json` to `quality-gate.config.json` at the adopting repository root and pass it to
`mutation_gate.py run --config` / `verification_linter.py`.

| Stack | Profile fragment | Ready-to-copy config | Acceptance / BDD (industry standard) | Mutation (industry standard) | Why this pair |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Python | `python.yml` | [`python.config.json`](python.config.json) | pytest-bdd / behave -> pytest JUnit XML | mutmut | Standard open-source stack for BDD acceptance and Python mutation testing. |
| Node.js / TypeScript | `node.yml` | [`node.config.json`](node.config.json) | Cucumber.js -> JUnit XML | Stryker | Cucumber.js is the reference BDD runner for JS/TS; Stryker is the reference mutation framework. |
| Go | `go.yml` | [`go.config.json`](go.config.json) | Godog -> JUnit XML (gotestsum fallback) | go-mutesting | Godog is the Cucumber-compatible BDD runner for Go; go-mutesting is the standard OSS mutation tool. |
| Java / Kotlin | `java.yml` | [`java.config.json`](java.config.json) | Cucumber-JVM -> JUnit XML | PITest | Cucumber-JVM is the JVM reference BDD runner; PITest is the JVM reference mutation system. |
| Rust | `rust.yml` | — | nextest/cargo2junit (adapter) | cargo-mutants | Native Rust test runner plus the standard mutation tool. |
| C# / .NET | `dotnet.yml` | — | JUnit logger / TRX adapter | Stryker.NET | The .NET port of the same mutation framework. |
| C / C++ | `cpp.yml` | — | CTest JUnit XML | Mull | CTest is the CMake-native runner; Mull is the LLVM mutation engine. |

Every config sets complexity via the bundled `complexity_check.py` (Tree-sitter/Lizard engines,
Python AST fallback) and records the **fail-closed mutation floor**: `min_msi: 80`,
`core_min_msi: 90`. `mutation_gate.py --config` validates that `core_min_msi` is numeric, is
`<= 100` and is `>= min_msi`; Gate 3 enforces the same floors through `risk_level: core`
(MSI >= 80%, >= 90% for core tasks). Missing configuration, a command failure, a missing or
malformed report, or an MSI below the floor fails the PR - it never skips.

The machine-readable catalog is [`index.json`](index.json); each entry for the four config-bearing
stacks carries a `config` field. The profile/config shape is documented by
[`../quality-gate.config.example.json`](../quality-gate.config.example.json).

## Mutation report adapter contract

Every profile ultimately writes the normalized report consumed by the bundled
`scripts/mutation_gate.py` (at the skill root) and Gate 3:

```json
{
  "tool": "mutmut",
  "targets": [
    {"file": "src/auth/service.py", "total": 10, "killed": 8,
     "timed_out": 1, "equivalent": 1, "survived": 0}
  ]
}
```

Use the stack tool's native report (Stryker JSON, PIT XML, cargo-mutants output, etc.) and a small
adapter to produce this shape. The adapter belongs to the project (or the CI profile), not to the
generic gate.

## Services and real middleware

Profiles deliberately do not start databases, queues or caches. If acceptance tests require real
middleware:

- prefer testcontainers or a compose fixture owned by the test suite; or
- add GitHub Actions `services:` to the acceptance/mutation jobs.

Do not assume a service is already available on the runner. Record the environment, image tag and
seed data in `03-qa-verification.md`.

## Adoption steps

1. Choose a profile from the table above.
2. Merge its toolchain setup, install, acceptance/JUnit and mutation blocks into your adapted
   `quality-gate.yml`; keep the invariant jobs (Gate 1, RBAC, complexity, Gate 3, fail-closed
   mutation) and the artifact upload/download between the mutation job and Gate 3.
3. Implement the mutation report adapter for the chosen tool and copy the matching
   `profiles/<stack>.config.json` (or `../quality-gate.config.example.json`) to
   `quality-gate.config.json`; verify `mutation.command`, keep `mutation.report` at
   `artifacts/mutation-report.json`, and keep `min_msi: 80` / `core_min_msi: 90`.
4. Add `services:` or testcontainers if the contract depends on real middleware.
5. Set `--actual-mutation artifacts/mutation-report.json --require-actual-mutation` on the Gate 3
   step so the reported MSI is cross-validated against the real report.
6. Run the suite's unit tests and your own CI smoke test before enabling required checks. Verify
   the mutation job is a required PR status check, not a post-merge-only job.
