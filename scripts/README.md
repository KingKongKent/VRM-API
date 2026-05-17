# Scripts Boundary

Scripts in this directory are developer/operator helpers. They do not ship with the Home Assistant integration.

## Rules

- Keep local target details, HA IP addresses, usernames, and paths out of tracked scripts unless they are placeholders.
- Put environment-specific deploy helpers in ignored files such as `scripts/deploy_to_ha.ps1`.
- Do not store tokens, passwords, SSH keys, or Home Assistant long-lived access tokens here.
- Prefer placeholders such as `<HA_HOST>` and `<HA_USER>` in committed examples.
- After deployment scripts change, update [docs/security.md](../docs/security.md) if a new pitfall or mitigation was learned.

## Local Deploy Helper

The current local helper `scripts/deploy_to_ha.ps1` is intentionally ignored by git because it can contain machine-specific Home Assistant targets. Use it locally, but do not commit it unless it is converted to a generic, placeholder-only script.