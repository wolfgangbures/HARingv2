# HARing v2 (Ring)

Custom Home Assistant integration for Ring devices using the `ring-doorbell` Python library.

## Features
- Cameras: live view and last recording.
- Events: ding, motion, intercom unlock.
- Sensors: battery, signal strength, last activity, volumes, etc.
- Binary sensors: motion and ding (deprecated in favor of events).
- Switches: motion detection, in‑home chime, siren (deprecated in favor of siren).
- Siren entity for compatible devices.
- Numbers for volume controls.
- Button to open intercom doors (supported devices).

## Requirements
- Home Assistant Core (recent version recommended).
- `ffmpeg` integration installed and working.
- Ring account credentials (2FA supported).

## Installation
### Option A: Manual
1. Create the folder `custom_components/ring` in your Home Assistant config directory.
2. Copy all files from this repository into that folder.
3. Restart Home Assistant.

### Option B: HACS (custom repository)
1. In HACS, add this repository as a custom integration.
2. Install it and restart Home Assistant.

## Setup
1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Ring**.
3. Enter your username and password. If 2FA is enabled, follow the prompt.

## Notes
- This integration uses cloud polling plus a real‑time event listener.
- Some legacy entities are deprecated in favor of newer platforms and will be removed in future HA versions.

## Support
- Issues: https://github.com/wolfgangbures/HARingv2/issues

### Missing real-time events
Device polling and push delivery are separate. A health check with `started=True`
does not prove that incoming push messages can be decrypted. Repeated
`FCM message skipped` warnings mean messages are arriving but failing processing;
`Invalid EC key` points to EC key validation, not a polling or DNS failure.
One reproduced cause is a `crypto-key` header containing both `dh` and
`p256ecdsa`: the upstream parser decodes both values together, producing a
137-byte value instead of a 65-byte P-256 point. This integration isolates the
key and salt values from trailing semicolon-separated parameters before decoding,
while retaining the existing missing-padding and raw 64-byte point fixes.

Enable integration debug logging from **Settings → Devices & Services → Ring →
Enable debug logging**, reproduce a doorbell/unlock event, then disable logging
to download the log. Alternatively, add this to `configuration.yaml` and restart:

```yaml
logger:
  default: info
  logs:
    custom_components.ring: debug
```

Look for `Applied firebase_messaging compatibility patches`, `FCM decrypt`,
`FCM payload decrypted successfully`, `Ring event received`, and the traceback
after `FCM message processing failure`. The decryption metadata records public-key
length/point prefix and salt/payload lengths, not key values, credentials, or
payload contents. It also indicates whether trailing header parameters were
removed. The traceback distinguishes local private-key loading from
remote public-key validation and later decryption failures. Listener health logs
also show subscription state, event count, and seconds since the last event
(`None` means no event has reached this coordinator since setup).

Do not enable firebase-messaging's `log_debug_verbose` option: it can expose
tokens and message contents. Review and redact logs before sharing, especially
when enabling additional dependency loggers. Do not delete stored credentials
based only on `Invalid EC key`; first capture the traceback to identify which
key failed validation.
