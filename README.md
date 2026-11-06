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
