## Summary

<!-- What skill/script/doc changes, and why. -->

## Evidence

```bash
python -m unittest discover -s tests/unit -p "test_*.py"
claude plugin validate .   # if manifests changed
```

## Checklist

- [ ] One focused change; no unrelated reformatting.
- [ ] `SKILL.md` frontmatter `name` equals the directory name (new/renamed skills).
- [ ] Helpers stay standard-library only and keep the exit-code convention.
- [ ] CHANGELOG updated under `## [Unreleased]`.
- [ ] No gate was weakened to make this change pass.
