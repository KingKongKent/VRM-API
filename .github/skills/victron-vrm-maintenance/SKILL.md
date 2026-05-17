---
name: victron-vrm-maintenance
description: "Use when: maintaining the Victron VRM Home Assistant integration, adding sensors, editing docs, reviewing boundaries, updating architecture, checking secrets, or preparing releases. Covers shipped-code boundaries, VRM enum pitfalls, instance remap rules, docs inventory, and security checklist."
---

# Victron VRM Maintenance Skill

Use this workflow for changes to the Victron VRM API integration.

## First Checks

1. Read [.github/copilot-instructions.md](../../copilot-instructions.md).
2. Confirm whether the change touches shipped code, docs, scripts, tests, or captured data.
3. Treat only [custom_components/victron_vrm_api/](../../../custom_components/victron_vrm_api/) as shipped code.
4. Check [docs/security.md](../../../docs/security.md) before handling tokens, deployment, API captures, or config flows.
5. Check [docs/architecture.md](../../../docs/architecture.md) before changing endpoints, coordinators, config keys, or device flows.

## Required Guardrails

- Never hardcode real VRM tokens, HA tokens, passwords, SSH keys, or local-only deployment targets in tracked files.
- Use `.env` for local secrets and [.env.example](../../../.env.example) for placeholders.
- Keep local deploy helpers ignored unless they are fully generic.
- Resolve enum/status values from raw enum values plus `dataAttributeEnumValues` before formatted strings.
- Preserve configured instance IDs for Home Assistant identity; use live remapped IDs only for API calls.
- Create sensors only when the VRM API returns the relevant data.
- Keep aiohttp calls async, through HA's managed session, with a 15 second timeout.

## Before Finishing

1. Update [INVENTORY.md](../../../INVENTORY.md) if files, shipped boundaries, or docs changed.
2. Update [README.md](../../../README.md) and [docs/documentation.md](../../../docs/documentation.md) for user-facing changes.
3. Add new pitfalls or vulnerabilities to [docs/security.md](../../../docs/security.md).
4. Add architecture changes to [docs/architecture.md](../../../docs/architecture.md).
5. Run validation or document why it was not run.