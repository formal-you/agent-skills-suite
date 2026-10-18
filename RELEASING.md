# Releasing

This tree is the distributable skill package. It ships a Claude Code plugin
(`.claude-plugin/plugin.json`) and a one-plugin marketplace (`.claude-plugin/marketplace.json`).

The packaging tool (`tools/package_skills.py`) is **not** shipped in this tree. Run it from the
upstream development repository to regenerate this package; the upstream build also produces the
deterministic zip and `MANIFEST.sha256`.

## One-time publishing setup

1. Create a public GitHub repository, for example `agent-skills-suite`.
2. Replace the placeholder `OWNER` / repository URL in `README.md`, `.claude-plugin/plugin.json`
   and `.claude-plugin/marketplace.json` with your real repository URL (the upstream build
   accepts `--repo-url` when generating this tree).
3. `git init`, commit, push to `main`.
4. Settings -> Actions: allow workflows (the bundled `ci.yml` runs on push/PR).
5. Optional: publish to Anthropic's plugin directory by following the current submission
   instructions for Claude Code plugins.

## Install flow for users

```bash
# Claude Code plugin (marketplace lives in this repository)
/plugin marketplace add OWNER/agent-skills-suite
/plugin install agent-skills-suite@agent-skills

# Local plugin directory, without a marketplace
claude --plugin-dir /path/to/agent-skills-suite

# Other harnesses (Codex, DSH, Antigravity, Claude Code)
python tools/install_skills.py --dest ~/.agents/skills
```

## Version bump and release

1. Update `VERSION`, `.claude-plugin/plugin.json`, the marketplace entry and `CHANGELOG.md`
   to the same semantic version.
2. `python -m unittest discover -s tests/unit -p "test_*.py"`
3. `claude plugin validate .` (must pass; warnings should be fixed).
4. Commit, tag `vX.Y.Z`, push the tag. `.github/workflows/release.yml` attaches a source zip
   to the GitHub release.

## Compatibility matrix

| Consumer | Entry point |
| :--- | :--- |
| Claude Code | `.claude-plugin/plugin.json` (skills via `.agents/skills/`) |
| Other Claude Code users without marketplace | `--plugin-dir`, or zip + `/plugin` panel |
| Codex / DSH / Antigravity | `.agents/skills/` discovery or `tools/install_skills.py` |
| Any repo adopting the workflow | `python tools/quickstart.py --target <repo> --with-ci` |
