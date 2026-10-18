# CI templates - Gate 1 and the RBAC audit

Two copy-paste GitHub Actions workflows that make the skill suite enforceable on pull
requests. They are deliberately small and stdlib-only: no marketplace action is required
except `actions/checkout` and `actions/setup-python`.

| File | Trigger | Command | Fails when |
| :--- | :--- | :--- | :--- |
| `rbac-gate.yml` | every `pull_request` | `python tools/rbac_audit.py --base <base.sha> --head <head.sha> --tasks-dir tasks --json` | a role touched files it may not touch (L1 audit) |
| `plan-gate.yml` | `pull_request` touching `tasks/**` or `.specs/**` | `python .agents/skills/plan-linter/scripts/plan_linter.py --tasks-dir tasks --spec .specs/02-tech-spec.md --json` | Gate 1 finds a structural violation |

The rows above describe the committed templates; the actual SHAs for the audit come from
the pull request event, not from the workflow file.

## Install

### Option A - one command with quickstart

```bash
# from the suite checkout
python tools/quickstart.py --target /path/to/your-repo --with-ci
```

If your platform refuses symlinks (Windows without Developer Mode), add `--copy` so the
adoption is committed as real files:

```bash
python tools/quickstart.py --target /path/to/your-repo --copy --with-ci
```

`--with-ci` copies both `.yml` files into `<target>/.github/workflows/` in addition to
the skills, rules and `tools/rbac_audit.py`.

### Option B - copy the two files manually

```bash
mkdir -p .github/workflows
cp templates/ci/rbac-gate.yml .github/workflows/rbac-gate.yml
cp templates/ci/plan-gate.yml .github/workflows/plan-gate.yml
```

```powershell
New-Item -ItemType Directory -Force .github/workflows | Out-Null
Copy-Item templates/ci/rbac-gate.yml .github/workflows/rbac-gate.yml
Copy-Item templates/ci/plan-gate.yml .github/workflows/plan-gate.yml
```

Commit the workflows and the suite files (`.agents/skills/`, `.agents/rules/`,
`tools/rbac_audit.py`) together so CI runs against the version you reviewed.

## Required permissions and repository settings

- **Workflow token**: both files declare `permissions: contents: read` at the top level.
  That is all they need: the audit reads git history, the linter reads repository files.
- **Secrets**: none. Do not add secrets to these workflows. Fork pull requests deliberately
  do not receive secrets, and the templates never ask for one.
- **Checkout depth**: `rbac-gate.yml` uses `fetch-depth: 0` because the audit diffs the
  pull request base and head SHAs, which are not present in a shallow clone.
- **Optional repository variable**: set `RBAC_ROLE` to `dev`, `qa` or `planner` to pin
  one role for every pull request. Leave it unset to use the commit trailer described below.
- **Branch protection**: require the two check names as required status checks before
  enabling auto-merge. The check names are `RBAC audit (authoritative)` and
  `Gate 1 - plan linter` (the `name:` fields of the jobs).
- **Actions policy**: allow GitHub Actions to run on `pull_request` events for the
  repository. No write permission and no repository secret are required or requested.

## Why the audit is authoritative

The repository rules themselves say the honest model, and these templates follow it:

| Layer | Mechanism | Guarantee |
| :--- | :--- | :--- |
| L0 | prompt rules (`AGENTS.md`, `.agents/rules/*.md`) | advisory |
| L1 | `tools/rbac_audit.py` in CI | authoritative for committed changes |
| L2 | branch protection / CODEOWNERS | authoritative, repository settings |

`rbac-gate.yml` is L1: it diffs the merged pull request range and fails the job when a
declared role crossed its write scope (for example Dev editing `tests/acceptance/**` or QA
editing `src/**`). `plan-gate.yml` is the deterministic half of Gate 1. No local hook
adapter is shipped; passing a local prompt-file workflow proves nothing about CI.

The audit is a **diff** audit: it judges the files in the range, not the identity of the
human merging. Do not describe prompt rules as physical enforcement, and do not weaken the
workflow to make a red pull request green.

## Roles and the audit CLI

- `--base` and `--head` are filled from the pull request event
  (`github.event.pull_request.base.sha` and `github.event.pull_request.head.sha`), so
  the audit covers every commit in the pull request even when the branch is out of date.
- The role comes from `--role` (the `RBAC_ROLE` variable above) or, when it is unset,
  from the `Agent-Role: dev|qa|planner` trailer on the head commit.
- One pull request range has **one** role. If a pull request mixes roles, split it, or set
  `RBAC_ROLE` only when the whole range belongs to one role.
- `--tasks-dir tasks` tells the audit where task contracts live; change both the
  invocation and the workflow if your repository uses another root.
- `--json` makes the full report machine-readable; the workflow appends it to the job
  step summary so reviewers see the evidence without opening the log.
- Exit codes: `0` pass, `1` violations (or a Gate 1 failure), `2` usage or git
  environment error. A `2` is an infrastructure problem, not a permission violation -
  read the log before asking anyone to change code.

## Pinning the suite version

The workflows are plain repository files, so the version they enforce is the version you
commit:

1. Adopt from a tagged release or a recorded commit SHA of the suite repository, not from a
   moving branch: `git checkout <release-tag-or-sha>` in the suite checkout, then run
   `quickstart.py --copy --with-ci`.
2. Commit the resulting `.agents/skills/`, `.agents/rules/`, `tools/rbac_audit.py` and
   `.github/workflows/` files in one reviewable pull request.
3. Record the versions in that pull request: `python tools/quickstart.py --version`,
   `python tools/rbac_audit.py --version`, `python
   .agents/skills/plan-linter/scripts/plan_linter.py --version`, and the
   `metadata.version` values in each `SKILL.md`.
4. To upgrade, re-adopt from the new tag with `--force` (`quickstart.py --target . --copy
   --force --with-ci`) and review the diff. The diff is the audit trail.
5. For a stricter supply chain, pin `actions/checkout` and `actions/setup-python` to a
   full commit SHA instead of `v4` / `v5`. Dependabot-style upgrades are then explicit.

Do not edit the copied workflows without recording why; they are the enforcement layer
from Section "Why the audit is authoritative".

## Troubleshooting

**The workflow did not run.** `plan-gate.yml` only runs when the pull request changes
`tasks/**` or `.specs/**`. A pull request that only touches source shows the check as
skipped - that is expected. `rbac-gate.yml` has no path filter and runs on every pull
request; if it is missing, check the Actions policy for the repository.

**Fork pull requests.** Pull requests from forks run with a read-only token and no secrets.
Both workflows are compatible with that because they only read history. `fetch-depth: 0`
is still required: an `unknown revision` or `bad object` diff error means the base or
head SHA was not fetched. If your organization forbids workflows on fork pull requests,
rely on branch protection and run the audit on the merge queue instead.

**The plan gate reports NO_TASKS.** The linter exits `1` when no task bundle exists
under `tasks/`. That is expected while a repository is still authoring its first spec. Add
the contracts with task-decomposition, or narrow the `plan-gate.yml` path filter to
`tasks/**` while the spec is still being written.

**The plan gate reports a missing spec file.** The linter exits `2` when
`--spec .specs/02-tech-spec.md` does not exist. Commit the tech spec first, or, if the
repository only uses task bundles without a spec, drop the `--spec` flag from
`plan-gate.yml` and keep the rest of the command unchanged.

**The audit says "no role available".** The head commit has no `Agent-Role:` trailer and
the `RBAC_ROLE` repository variable is unset. Add the trailer
(`Agent-Role: dev` in the commit message body) or set the variable for single-role
repositories.

**The audit reports a violation that looks intentional.** The contract and the role rules
define the write scopes; a deliberate exception needs a contract change and review, not a
weakened workflow. Never add `--role planner` just to pass.

**A symlinked adoption fails in CI.** Commits do not carry symlinks that point outside the
checkout. Use `quickstart.py --copy` (or `tools/install_skills.py --copy` for per-user
installs) and commit the real files.

**Windows contributors cannot parse the workflow locally.** The jobs run on
`ubuntu-latest` with `bash`. To run the same commands locally, use Git Bash or WSL, or
invoke the Python commands directly with `python` from the repository root.

## Verify locally before enabling branch protection

```bash
# Gate 1 exactly as CI runs it
python .agents/skills/plan-linter/scripts/plan_linter.py \
  --tasks-dir tasks --spec .specs/02-tech-spec.md --json

# RBAC audit over the same range the workflow will use
git fetch origin
python tools/rbac_audit.py --base origin/main --head HEAD --role dev --json
```
