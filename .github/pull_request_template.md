## Summary

<!-- What skill/script/doc changes, and why. Keep this PR focused. -->

## Linked issue

Closes #

## Test evidence

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
# add targeted commands, install smoke, or plugin validation as applicable
```

## Risk and rollback

<!-- Behavior/security/CI risk, blast radius, and how to revert safely (PR revert or new patch). -->

## Release / tag

- [ ] No version bump needed (docs/process-only, not user-visible)
- [ ] `VERSION`, `CHANGELOG.md`, plugin manifests and skill metadata updated for `vX.Y.Z`
- [ ] Tag/release plan stated; tag will be created from merged `main` only

## Review

- [ ] Behavior/security/gate/CI change: independent reviewer (not the author) approved
- [ ] Docs-only: self-merge allowed by branch protection, or reviewer approval recorded

## Checklist

- [ ] One focused change; no unrelated reformatting.
- [ ] Canonical and mirror trees are byte-identical for changed skill files.
- [ ] `SKILL.md` stays under 200 lines; canonical English; self-contained.
- [ ] Helpers stay standard-library only and keep the exit-code convention.
- [ ] `CHANGELOG`, version and manifests agree when released.
- [ ] No gate, test or role boundary was weakened to make this change pass.
- [ ] No secrets, credentials or generated caches are committed.
