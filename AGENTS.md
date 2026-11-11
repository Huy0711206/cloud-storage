# CloudBox maintainer context

Read README.md and PROGRESS.md first. Production moved to AWS Academy EC2 on 10/11/2026 after explicit user approval; see docs/operations/AWS-ACADEMY.md. EC2 /opt/cloudbox uses infrastructure/aws Compose sources (db/portal/tunnel), with secrets entered directly by the user on EC2. Laptop Portal is stopped and its data is a retained cutover source, not an active replica. Do not restart it or switch DNS back without migrating newer AWS writes. Academy session/budget limits still apply. The user's approved 09/11/2026 native-storage migration supersedes historical Nextcloud/tunnel-off design decisions.

- One public CloudBox origin: cloudbox.rachiba.top. Portal owns native file operations and uses PostgreSQL + persistent cloudbox_data. No iframe/proxy/SSO dependency on Nextcloud.
- Preserve root Compose project/volume/network identity and all identities, hashes, plans, orders and payment history. Never down -v or recreate a database to solve paths.
- Legacy Nextcloud/Mailpit/gateway SOURCE and tooling were retired by explicit user approval on10/11/2026. Retain original data/volumes/database read-only; never start old services to solve CloudBox issues.
- Do not enable Docker/CloudBox autostart, purchase services or deploy AWS without user instructions.
- Features separate auth/accounts/storage/billing/payments/admin. Billing owns price/expiry, payments owns signing/idempotency and atomic activation, storage enforces current plan directly.
- Runtime entrypoint app.main:app. API file routes enforce server-side ownership and source-origin checks; OTP/reset codes and credentials must never reach logs/output.
- Keep private .env/.online/.runtime/.unified-backup out of Git/output. Never overwrite user environment settings with examples.
- Use disposable SQLite/fake mail/payment for default tests; concurrency tests only on an explicitly disposable cloudbox_qa PostgreSQL database. Production migration source is read-only and requires checksum/ownership/commerce proof before cutover.
- Preserve pricing UI and DB prices. Canonical design tokens/fonts: packages/design-system. Do not change dependencies merely to silence warnings.
- Keep migration/rehearsal/models/source-data tests; legacy gateway-specific tests were retired with their features. Do not delete uncertain remaining code or original source volumes; no new backups.
- Update PROGRESS/docs and artifacts/qa for material changes; distinguish real SMTP acceptance from user-confirmed inbox delivery and real transactions from mocks.

- 09/11/2026 plan-benefits approval: latest user request restores catalog quotas 5/100/500/2048 GiB for existing users too; prices unchanged. Compose shared STORAGE_POOL_LIMIT_BYTES=20 GiB. Preserve data on limit/downgrade, deny growth; do not infer host capacity from Docker virtual df. New version policies are additive and do not expire imported history. Team sponsor personal+team data share the same plan quota; personal APIs must reject all group namespaces. Keep test-only PostgreSQL cloudbox_qa isolated.

- Current layout: apps/portal only; main frontend build only. No legacy source/build/compatibility CLI remains. One-off quota restoration remains scripts/operations/one-off/restore-plan-quotas.py; never run as QA. See artifacts/qa/deadcode-cleanup-2026-11-10.md.

- Current operating/development instructions: docs/operations/OPERATIONS.md and docs/development/DEVELOPMENT.md; rollback/refactor/design snapshots with history banners are not runnable current instructions. Dependency locking and a consolidated pre-deploy command are proposed only, not implemented.
