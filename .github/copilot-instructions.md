# Copilot instructions for HARingv2

Project: Home Assistant custom integration for Ring (domain: `ring`).

## Architecture
- Core setup is in `__init__.py` with `RingDataCoordinator` and `RingListenCoordinator`.
- Entities derive from `RingEntity` or `RingBaseEntity` in `entity.py`.
- Data fetches use `RingDataCoordinator` (polling) and `RingListenCoordinator` (real‑time events).
- Keep all operations async; avoid blocking I/O.

## Coding conventions
- Follow Home Assistant async patterns and entity lifecycle.
- Use the existing coordinator patterns (avoid per-entity polling).
- When adding new entities, provide unique IDs matching existing patterns.
- Use translation keys in `strings.json` and avoid hard‑coded user‑facing strings.
- Prefer `exception_wrap` and `refresh_after` helpers for API calls.
- Keep deprecations consistent with `DeprecatedInfo` and `async_check_create_deprecated`.

## Files to touch
- `manifest.json`: update `version` when changing behavior.
- `strings.json`: add translations for new entity keys.
- `const.py`: new constants, platforms, or config schema values.
- `quality_scale.yaml`: update only if quality level changes.

## Safety
- Never log secrets (tokens, credentials).
- Redact diagnostics keys in `diagnostics.py` if new sensitive fields appear.
