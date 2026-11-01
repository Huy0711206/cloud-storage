# CloudBox maintainer context

Read README.md and PROGRESS.md first, then docs/architecture/PROJECT-STRUCTURE.md. Historical docs are under docs/history; their old ports/paths do not override current instructions.

- Runtime web ports are8000 portal,8080 native Nextcloud,8025 native Mailpit loopback.8001/8081/8026 are retired.
- The user selected local mode with tunnels OFF at the end of refactor01/11/2026. Do not restart/publicize tunnels unless requested. Keep .env and private .online/.unified-backup/.runtime state out of Git/output.
- Keep root docker-compose.yml and existing volume/network identity. Never down -v or recreate databases to solve source path issues.
- Portal: apps/portal/frontend and apps/portal/backend/app. Preserve package app.main:app, current route/form/session contracts and singleton integration modules.
- Features separate authentication/accounts/storage/billing/payments/administration. Billing owns plans/orders/expiry; payments owns signing/callback/idempotency and invokes billing.
- Legacy gateways/preview are intentionally retained for tests/reference under apps/portal/legacy and frontend/src/legacy; do not launch their old ports or delete them merely because they are not in Compose.
- Mailpit upstream stays intact under apps/mail/upstream. Canonical UI tokens/fonts: packages/design-system; use python scripts/sync-design.py then build.
- Viewer local patch has strict SHA/backup under apps/nextcloud/patches/viewer-close; use python scripts/patch-viewer.py dry-run/apply/restore, do not silence signature checks.
- Test with disposable SQLite/FakeNC/mock SMTP/payment only. Current commands and exact isolated Docker test invocation are in docs/development/DEVELOPMENT.md and artifacts/qa/refactor-backend-tests.json.
- Refactor source equivalence tools compare immutable snapshot to reviewed source. They may intentionally fail after new feature edits; review actual differences, never overwrite old evidence/hash merely to pass.
- Do not overwrite existing user changes. Before permanently deleting uncertain source/backup/docs, present exact candidates and ask the user per their refactor instruction. Inventory: docs/architecture/FILE-INVENTORY.md.
- Update PROGRESS/docs for material structural changes; evidence goes artifacts/qa, not root. Keep startup wrappers at root compatible.
