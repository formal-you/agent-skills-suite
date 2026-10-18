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
.agents/skills/<name>/assets/templates/
.agents/skills/<name>/scripts/   # optional helpers, --help/--version, exit 0/1/2/3
                                 # stdlib-only except complexity_check.py's optional tree-sitter/lizard engines
.agents/rules/                   # role rules + enforcement model
tools/                           # install, adoption, audit helpers
templates/ci/                    # copy-paste GitHub Actions
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

## Run the checks

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
python -m compileall -q .agents tools templates
claude plugin validate .          # optional; validates plugin.json + marketplace.json
```

All tests must pass on Windows and Linux. CI runs the matrix in `.github/workflows/ci.yml`.

## Git flow

The canonical workflow is in [`AGENTS.md`](AGENTS.md#skill-change-workflow-authoring---optimization---tests---git-flow).
In short: issue -> branch from `main` -> author/optimize -> test -> conventional commit -> PR
(`Closes #<issue>`) -> green checks -> merge -> sync `main` -> annotated `vX.Y.Z` tag and release
when a version is published. Do not commit directly to `main` and do not force-push shared branches.

## Pull requests

- One focused change per PR; keep unrelated reformatting out.
- Link the issue with `Closes #<issue>` and describe the skill/script affected.
- Include the evidence (test command + result) and any risk/rollback notes.
- Update `CHANGELOG.md`, `VERSION` and plugin manifests for user-visible releases.
- Do not weaken a gate to make a test pass; fix the artifact instead.

## Reporting issues

Use the issue templates. For security problems, follow `SECURITY.md` instead of a public
issue.
