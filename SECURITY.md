# Security Policy

## Supported versions

| Version | Supported |
| :--- | :--- |
| 3.1.x | yes |
| < 3.1 | no |

## Reporting a vulnerability

Please do **not** open a public issue for a security problem. Use GitHub private
vulnerability reporting ("Report a vulnerability" on the Security tab) or email the
maintainers listed in the repository profile. Include:

- affected skill or script and version;
- a minimal reproduction;
- impact (for example, a helper writes outside its output path or misclassifies a path).

## Scope and honest limits

- The bundled helpers are optional and local: they read files under `--repo-root`/`--out`
  and never call the network.
- The authoritative enforcement layer is CI (`tools/rbac_audit.py`) plus branch protection;
  prompt rules are advisory and bypassable.
- Generated reports and convergence markers are evidence, not a signature chain: verify
  with git history and CI.
