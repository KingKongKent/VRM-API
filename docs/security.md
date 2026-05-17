# Security, Boundaries, and Pitfalls

This file tracks repo safety rules, recurring mistakes, and security decisions. Keep it short, current, and honest.

## Hard Boundaries

| Boundary | Rule |
| :--- | :--- |
| Shipped code | Only [custom_components/victron_vrm_api/](../custom_components/victron_vrm_api/) ships to users |
| Secrets | Never commit `.env`, real VRM tokens, HA host secrets, SSH keys, or captured private payloads |
| Local deployment | Local targets belong in ignored scripts or local docs only |
| Tests | Test scripts must load secrets from environment variables or `.env` via `python-dotenv` |
| Captured data | `api_data_*/` is ignored; redact before sharing any capture |

## Secret Handling

- Use `.env` locally and [.env.example](../.env.example) for placeholders.
- Do not put real tokens in README examples, docs tables, screenshots, terminal output, or issue templates.
- Reconfigure forms must not prefill saved tokens back into the UI. Leave token blank to keep the stored value.
- Never log authorization headers, raw config entries, or full request objects.
- Before committing, scan staged changes for secret-shaped strings.

Suggested PowerShell check:

```powershell
git diff --cached | Select-String -Pattern "token|secret|password|X-Authorization|cf2e|VRM_TOKEN"
```

## Pitfalls Learned

| Pitfall | Prevention |
| :--- | :--- |
| Example token values look real and can be copied into releases | Use `vrm_token_placeholder` or `{your_vrm_token}` only |
| Reconfigure can expose a saved token if it is used as the default form value | Token field stays blank and preserves the old token when blank |
| VRM `formattedValue` can be stale | Resolve enums from `dataAttributeEnumValues` plus raw enum value first |
| `system-overview` may list stale and live instances at the same time | Use diagnostics timestamps to choose the freshest instance |
| VRM may collect tanks in diagnostics without listing them in `system-overview` | Discover tank instances from diagnostics and use diagnostics fallback sensors |
| Too many 20 second coordinators can trigger HTTP 429 | Keep scan intervals conservative and document any changes |
| Local deploy scripts can contain HA IPs or usernames | Keep target-specific scripts ignored; commit only generic script docs |
| HA config entry storage should not be treated as a public file | Avoid printing config data and keep HA backups protected |

## Security Review Checklist

- No hardcoded token, password, SSH key, local IP target, or private site ID in tracked files.
- No logs include `X-Authorization`, token values, or full config entry data.
- HTTP calls use HTTPS, HA managed aiohttp session, and a timeout.
- Non-200/204 responses fail cleanly through `UpdateFailed`; 429 guidance is documented.
- New sensor values handle missing data without exceptions.
- New enum/status sensors use raw enum mapping before formatted values.
- New deployment scripts are generic or ignored.
- Documentation examples use placeholders only.

## Risk Register

| ID | Risk | Status | Mitigation |
| :--- | :--- | :--- | :--- |
| SEC-001 | Real-looking token example in docs | Patched | Replaced with placeholder-only example and added this rule |
| SEC-002 | Reconfigure form displayed saved token as a default | Patched | Password selector field is blank by default; blank preserves existing token |
| SEC-003 | Local deploy scripts contain environment-specific targets | Accepted local-only | `scripts/deploy_to_ha.ps1` is ignored; [scripts/README.md](../scripts/README.md) documents the boundary |
| SEC-004 | Captured API payloads may include site/device metadata | Accepted local-only | `api_data_*/` is ignored; redact before sharing |
| SEC-005 | VRM API rate limiting from aggressive polling | Mitigated | Scan intervals live in [const.py](../custom_components/victron_vrm_api/const.py); 429 troubleshooting documented |

## When a Vulnerability Is Found

1. Patch the root cause in the shipped code or remove the risky tracked artifact.
2. Add or update an entry in the risk register above.
3. Update [.github/copilot-instructions.md](../.github/copilot-instructions.md) if future agents need the lesson.
4. Update docs and README if the user-facing behavior changed.
5. Run validation or explain why validation was not run.