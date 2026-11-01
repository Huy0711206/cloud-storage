# Legacy Docker specifications

These files are not services in the active Compose and do not publish retired ports. Their explicit source/build context, if investigated, is apps/portal (not this directory).

- Dockerfile.preview: historical reference only. Even the pre-refactor active main ignored VITE_UI_VARIANT; this file does not restore the old portal renderer as-is. No new preview entrypoint was introduced.
- Dockerfile.files-preview and Dockerfile.mail-preview: retained gateway build recipes reference the legacy frontend build configs and legacy/gateways. They are not the production Nextcloud/Mailpit applications and were not deployed or rebuilt during this refactor.

Use the root start-local command for the supported 8000 / 8080 / 8025 applications.

The gateway recipes preserve the source nesting `/srv/legacy/gateways/*.py` and place Vite outputs at `/srv/frontend/dist-files` or `/srv/frontend/dist-mail`. Their default source-layout anchor therefore works unchanged inside the image. Python namespace packages resolve `legacy.gateways.*` from `/srv`; no gateway logic or retired service is changed/enabled. These recipes were statically checked after relocation, not launched.
