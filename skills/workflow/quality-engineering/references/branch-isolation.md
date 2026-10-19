# Branch Isolation for Task Delivery

One task, one dedicated branch. The protected trunks (`main`, `master`) are integration
targets, never a working branch: Dev implements on a task branch, QA verifies the same
branch, and only green CI gates allow the branch to merge.

This reference covers the branch lifecycle, the `branch_guard.py` guard, how CI consumes
it, and a migration runbook for tasks that were already committed on trunk. The script is
bundled with this skill:
[`../scripts/branch_guard.py`](../scripts/branch_guard.py).

## 1. Lifecycle

| Stage | Branch state and action | Owner | Recorded evidence |
| :--- | :--- | :--- | :--- |
| 1. Derive | Create `feat/<task-id>` (or `task/<task-id>`) from an up-to-date base: `git switch -c feat/<task-id> origin/main`. Never branch from or reuse a protected trunk as the working branch. | Dev | `Branch` row in `02-dev-workspace.md` |
| 2. Implement | Commit only on that branch. Do not switch branches mid-task; if the branch is wrong, stop and recreate the work on the correct branch. | Dev | `02-dev-workspace.md` |
| 3. Handoff | Run the guard, then check `WAITING_FOR_QA`; the handoff commit must exist on the task branch. | Dev | `02-dev-workspace.md` |
| 4. QA checkout | `git switch feat/<task-id>` and verify the handoff commit is in history: `git merge-base --is-ancestor <handoff-commit> HEAD`. | QA | `03-qa-verification.md` |
| 5. Verify | Run integration, BDD end-to-end, mutation and static analysis on the recorded branch only. | QA | `03-qa-verification.md` |
| 6. Sign | Check `QA_PASSED` on the same branch; never sign off a different branch. | QA | `03-qa-verification.md` |
| 7. Push / PR | Push the task branch and open the pull request against the protected trunk. | Branch owner (repository policy) | Pull request |
| 8. CI gates | The branch guard plus RBAC, Gate 1, Gate 3 and mutation checks must pass; they are required status checks. | CI (`quality-engineering`) | CI run and reports |
| 9. Merge | Merge only with all required checks green, then delete the branch and sync the trunk. | Repository owner / reviewer | Trunk history |

The orchestrator dispatches Dev and QA with the task branch in the prompt and rejects a
handoff whose `02-dev-workspace.md` does not record a branch.

## 2. The guard

```bash
# Local check from the repository root (human-readable)
python .agents/skills/quality-engineering/scripts/branch_guard.py check \
  --repo . --task-dir tasks/task-001 --require-declared

# Machine-readable report with an explicit protected list and pattern
python .agents/skills/quality-engineering/scripts/branch_guard.py check \
  --task-dir tasks/task-001 --require-declared --protected main master --json

# CI check: the branch comes from the event, so git is not queried
python .agents/skills/quality-engineering/scripts/branch_guard.py check \
  --branch "${HEAD_BRANCH}" --protected main master --json
```

| Option | Meaning |
| :--- | :--- |
| `--repo PATH` | Repository to inspect; must be a directory (default `.`). |
| `--task-dir PATH` | Task bundle directory containing `02-dev-workspace.md`. |
| `--branch NAME` | Branch override; bypasses git entirely (CI passes the event branch). |
| `--protected LIST` | Protected names, comma- or space-separated (default `main,master`, case-insensitive). |
| `--pattern REGEX` | Required branch-name pattern applied with `re.fullmatch` (default `^(feat\|fix\|task\|change\|docs\|chore\|security)/[A-Za-z0-9._-]+$`). |
| `--require-declared` | Fail when the `Branch` row is blank or missing. |
| `--json` | Emit the machine-readable report. |

The guard resolves the branch with `git -C <repo> rev-parse --abbrev-ref HEAD` when
`--branch` is absent. It is read-only: it never mutates git state and never builds a shell
command string.

### Error codes

| Code | Trigger |
| :--- | :--- |
| `BRANCH_PROTECTED` | The resolved branch is one of `--protected` (case-insensitive). |
| `BRANCH_PATTERN_INVALID` | The resolved branch does not match `--pattern`. |
| `BRANCH_DETACHED` | Git reports `HEAD` (detached HEAD). |
| `BRANCH_DECLARED_MISSING` | The `Branch` cell is blank or absent with `--require-declared`. |
| `BRANCH_MISMATCH` | The declared branch differs from the resolved branch. |
| `TASK_DOC_MISSING` | `--task-dir` has no readable `02-dev-workspace.md`. |
| `BRANCH_NOT_DECLARED` (warning) | The `Branch` cell is blank or absent without `--require-declared`. |

Exit codes: `0` pass, `1` violation, `2` usage error (invalid arguments, non-directory
`--repo`, or git failure). JSON output is
`{"passed": bool, "branch": str, "declared": str|null, "protected": [..], "errors": [..], "warnings": [..]}`
where every error and warning is `{"code": ..., "message": ...}`.

## 3. How CI consumes it

The bundled `rbac-gate.yml` template adds one step after checkout and before the RBAC
audit. It passes the pull request head branch, fails closed, and prints the JSON report:

```yaml
run: |
  set -uo pipefail
  status=0
  python .agents/skills/quality-engineering/scripts/branch_guard.py check \
    --branch "$HEAD_BRANCH" --protected main master --json \
    > branch-guard-report.json 2> branch-guard-error.log || status=$?
  exit "$status"
```

The step exits non-zero on any violation, so the job fails. Make it a required status
check in branch protection so a pull request from a protected-named or undeclared branch
cannot merge. This is layer L1 of the enforcement model; branch protection and CODEOWNERS
are the authoritative L2 layer.

## 4. Migration runbook: work already committed on trunk

Use this when a task was committed directly on `main` or `master`:

1. **Freeze.** Stop new work on the task and record the current trunk SHA
   (`git rev-parse HEAD`).
2. **Locate the task commits.** Use the handoff commit recorded in `02-dev-workspace.md`
   and `git log --oneline <base>..HEAD`; confirm the touched files against the contract.
3. **Create the branch from the correct base and re-apply the work.**
   ```bash
   git switch -c feat/<task-id> <base-commit>
   git cherry-pick <task-commit-1> <task-commit-2>
   ```
   If the commits are already merged and the cherry-pick is empty, create the branch at
   the current trunk only to record history, and rely on step 5 for cleanup.
4. **Update the record.** Set the `Branch` cell in `02-dev-workspace.md` to
   `feat/<task-id>` and commit that change on the branch. Run
   `branch_guard.py check --task-dir tasks/<task-id> --require-declared --json` and confirm
   it passes.
5. **Keep trunk clean.** If the direct commits are pushed but unreleased, revert them on
   the trunk through a reviewed pull request (`git revert <commit>`) instead of
   force-pushing, then land `feat/<task-id>` through a normal pull request with the CI
   gates. If the change is already released, record the exception in the task bundle and
   apply the branch convention to all future work; rewriting shared trunk history needs
   explicit repository-owner approval.
6. **Prevent recurrence.** Enable branch protection with the guard as a required check,
   so the trunk stops accepting direct pushes and CI rejects protected-branch pull
   requests.

## 5. Honest limits

Prompt rules and these guard commands are advisory: a harness can ignore them, and the
local run only describes the current checkout. The authoritative barrier is CI: the
branch guard plus the other required checks, enforced by branch protection and CODEOWNERS.
The guard cannot prove that work was performed on the branch before it was pushed, and it
cannot stop a direct push by someone with permission to bypass protection; only repository
settings close that gap.
