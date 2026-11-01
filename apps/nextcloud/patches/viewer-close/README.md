# Viewer close guard — Nextcloud 35.0.2 / Viewer 8.0.0

Scope: the native viewer's `close()` checks only `OCA.Files.Sidebar` before calling `setFullScreenMode(false)`. Files can expose a Sidebar without that legacy method. The resulting TypeError occurs after `OCA.Viewer.close()` and prevents the following fullscreen exit. The opening path already checks the method. This patch checks `typeof ... === "function"` on close and retains the subsequent fullscreen exit. No fake method, suppression of global errors, account/data or backend changes.

This is a locally maintained compatibility patch, **not an official upstream release**. Official source endpoints for the installed version were unavailable during investigation. The exact shipped source is embedded in `viewer-main.mjs.map`; its Viewer.vue close method matches the deployed code. Provenance is the installed pinned image and four SHA256 hashes in the script. Original license remains applicable (AGPL-3.0-or-later).

## Operation from project root

```powershell
python scripts/patch-viewer.py           # dry-run, hashes must match
node --test apps/nextcloud/patches/viewer-close/viewer-close.test.mjs
python scripts/patch-viewer.py --apply
docker compose exec -T nextcloud php -l apps/viewer/lib/Listener/LoadViewerScript.php
docker compose exec -T -u www-data nextcloud php occ integrity:check-app viewer
```

The original module/source-map/info.xml are not modified. The patched module uses a content-hashed basename, and only the Viewer listener's script name changes, avoiding stale browser copies. The new module deliberately has no sourceMappingURL: the old map's generated columns would be inaccurate. The original map and recovered original Vue source are saved, alongside the original loader, in `backup/` on apply. Read `close-guard.patch` for the human-readable source change. A source-level rebuild is preferable when a verified exact upstream source/lock becomes available.

Expected signed app integrity findings: modified `lib/Listener/LoadViewerScript.php` and one extra `js/viewer-main-cloudbox-<hash>.mjs`. **Do not disable integrity verification or call the signed app clean.** Core integrity remains separate. No app version or signature file is changed. Record actual findings and confirm they contain no other modifications.

The script is strict/idempotent. Unknown source hashes, unknown loader changes, altered backups or altered patched modules stop the operation. Writes use a temporary file and atomic rename. Apply writes the new module before switching the loader; restore switches back before deleting the exact patched module. This is not a multi-file filesystem transaction; if interrupted, rerun dry-run and inspect before proceeding.

## Rollback and updates

```powershell
python scripts/patch-viewer.py --restore
docker compose exec -T -u www-data nextcloud php occ integrity:check-app viewer
```

Restoring keeps all accounts/files/configuration and uses the original loader/module. If PHP opcache still serves the old loader, restart Nextcloud only; keep current Compose override/tunnels. Normal Docker restart retains the patch because the app resides on nextcloud_data. An upstream upgrade can replace app files; do not automatically reapply. Review/dry-run must fail if the upstream bytes changed, and the patch should be removed once a compatible official fix is verified.

Regression tests execute the **actual extracted close body**, rather than a duplicate implementation. They reproduce the original failure, then check missing Files, missing Sidebar, missing/non-callable method and callable method with correct receiver; all with fullscreen off/on. The valid path must call native Sidebar, and fullscreen exit must continue even when the method is unavailable. Browser end-to-end verification remains required by the caller.


## Additional native Sidebar.open compatibility finding

Opening the Viewer with a sidebar already visible also calls `Sidebar.open` after emitting `viewer:sidebar:open`. Nextcloud35 Files has the actual event consumer in `apps/files/src/sidebar/providers/filesStore.ts` (verified from shipped dist/files-main.js.map; see sidebar-event-evidence.json). It resolves the Node and invokes `useSidebarStore(pinia).open(node)`. Therefore the event is the supported working path; the old method call is an optional legacy fallback retained for apps mocking the Files API.

The same managed patch now checks `typeof Sidebar.open === 'function'` only for that legacy fallback, preserving the node event unconditionally whenever sidebar is enabled, and preserving callable legacy hooks. This prevents the newly reproduced `Sidebar.open is not a function` without disabling the sidebar. Seventeen tests cover both guarded calls; browser verification should open a file while details/sidebar are already visible and then close the Viewer, verifying details still works.
