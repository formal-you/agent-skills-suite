# CI Stack Profiles

`quality-gate.yml` is a **reference implementation**, not a universal pipeline. It is Python-first
and GitHub Actions-first. This directory provides per-stack reference profiles so a project can keep
the invariant gates (Gate 1/2/3, RBAC, evidence, fail-closed mutation, artifacts, triage) while
replacing only the stack-specific commands.

## Important

- Profiles are **reference fragments**, not standalone workflows. Copy the relevant blocks into your
  adapted `quality-gate.yml`, or use them as an adoption checklist.
- `quality-gate.yml` remains the canonical Python reference.
- A profile is not validated against a real project in this repository. Treat it as a starting
  point; run it in your own CI and adjust tool versions, paths, services and report adapters.
- Do not wrap gate commands in `|| true` or `continue-on-error`.

## Available profiles

| File | Stack | Acceptance report | Mutation tool |
| :--- | :--- | :--- | :--- |
| `python.yml` | Python | pytest JUnit XML | mutmut |
| `node.yml` | Node.js / TypeScript | Cucumber.js / pytest-style JUnit | Stryker |
| `go.yml` | Go | gotestsum JUnit XML | go-mutesting |
| `java.yml` | Java / Kotlin | Surefire XML | PITest |
| `rust.yml` | Rust | nextest/cargo2junit (adapter) | cargo-mutants |
| `dotnet.yml` | C# / .NET | JUnit logger / TRX adapter | Stryker.NET |
| `cpp.yml` | C / C++ | CTest JUnit XML | Mull |

The machine-readable catalog is [`index.json`](index.json). The profile shape is documented by
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
2. Copy its toolchain setup, install, acceptance/JUnit and mutation blocks into your adapted
   `quality-gate.yml`.
3. Implement the mutation report adapter for the chosen tool.
4. Add `services:` or testcontainers if the contract depends on real middleware.
5. Keep the invariant jobs (Gate 1, RBAC, complexity, Gate 3) and artifact upload/download.
6. Run the suite's unit tests and your own CI smoke test before enabling required checks.
