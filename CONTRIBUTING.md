# Contributing

Thanks for helping improve the Agent Skills Suite. This repository is the distributed
skill package: eleven workflow skills (plus the platform helper), their rules, helper scripts, docs
and tests.

## Prerequisites

- Python 3.9+ (helpers are standard-library only, except the optional multi-language engines in
  `complexity_check.py`).
- Optional: a Claude Code install (`claude` CLI) to validate the plugin manifest.
- Optional: Node 22+ only if you exercise examples that use a TypeScript project.

## Layout

```text
.agents/skills/<name>/SKILL.md   # one skill; frontmatter name MUST equal the directory name
.agents/skills/<name>/references/
.agents/skills/<name>/assets/templates/   # incl. quality-engineering's CI workflows and profiles
.agents/skills/<name>/scripts/   # optional helpers, --help/--version, exit 0/1/2/3
                                 # stdlib-only except complexity_check.py's optional tree-sitter/lizard engines
.agents/rules/                   # role rules + enforcement model
tools/                           # maintainer installers (quickstart, install_skills)
docs/                            # user guides, harness compatibility, benchmark report
tests/unit/                      # black-box tests for the skills and tools
```

`tools/package_skills.py` is maintainer-only and stays in the upstream development repository;
this tree is its generated output. Do not add packaging logic here.

## Adding or changing a skill

1. Keep the package self-contained: no imports from a parent repository, no network, no
   third-party Python dependency in `scripts/`.
2. `SKILL.md` frontmatter must contain `name` (equal to the directory name), `description`
   with a "Use when" and a "Do not use when" sentence, `license`, `compatibility` and
   `metadata.version` / `metadata.category`.
3. Provide a manual fallback: every script is optional, and the prompt workflow must still
   work without Python.
4. Do not leave `TODO`, `[TBD]` or double-brace tokens in templates that are scanned by
   Gate 1.
5. Add or update a black-box test under `tests/unit/` that invokes the script via
   `subprocess` (see existing tests for the pattern).
6. Keep the skill directory self-contained: `SKILL.md` and its `references/` may reference only
   files inside that skill directory. Repository rules (`AGENTS.md`, `.agents/rules/`), `docs/` and
   `tools/` are optional context, never required runtime files — plugin and per-skill installs only
   ship the skill directory.
7. Compose with other skills by name, never by copying their scripts. A downstream helper (for
   example Gate 1 from `plan-linter`) is invoked with the project-root path
   `.agents/skills/<skill>/scripts/<script>`, marked as conditional on that skill being installed,
   and paired with a manual fallback. `python scripts/x.py` is only valid when the user is already
   inside the skill directory, so do not use it in instructions.

## Run the checks

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
python -m compileall -q .agents tools
python tools/gen_manifest.py --check
claude plugin validate .          # optional; validates plugin.json + marketplace.json
```

All tests must pass on Windows and Linux. CI runs the matrix in `.github/workflows/ci.yml`.

## Git flow

The canonical workflow is in [`AGENTS.md`](AGENTS.md#skill-change-workflow-authoring---optimization---tests---git-flow).
In short: risk-based issue -> branch from `main` -> author/optimize -> tests + evidence -> conventional
commit -> PR (`Closes #<issue>`) -> green checks + independent review where required -> merge ->
watch post-merge CI -> sync `main` -> annotated `vX.Y.Z` tag and release with SemVer. Do not commit
directly to `main`, do not force-push shared branches, and never move or delete a published tag; a bad
release gets a new patch release.

## Pull requests

- One focused change per PR; keep unrelated reformatting out.
- Fill the PR template: `Closes #<issue>`, summary, test evidence, risk/rollback and release/tag plan.
- Behavior, security, gate or CI changes need an independent reviewer (not the author); docs-only
  changes may self-merge only if branch protection permits it.
- Update `CHANGELOG.md`, `VERSION`, plugin manifests and skill metadata for user-visible releases.
- Do not weaken a gate or test to make a change pass; fix the artifact instead.

## Reporting issues

Use the issue templates. For security problems, follow `SECURITY.md` instead of a public
issue.
