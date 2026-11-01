# Project commands

Run from the project root. Root commands and scripts/*.py are compatibility entrypoints; implementations are grouped below.

- development/start-local.ps1: local startup, optionally rebuild portal/Mail.
- operations/online.py and start/stop-online.ps1: existing two Quick Tunnels; .online remains private at project root.
- maintenance/sync-design.py: packages/design-system to the three application targets.
- maintenance/patch-viewer.py: dry-run/apply/restore the pinned local Viewer compatibility patch.
- maintenance/rollback-ui.py: validate/revert/reapply UI images/theme, keep data/ports/current URLs.
- diagnostics/verify-ui.py: deployment, identity/count, source/baseline and local/public HTTP checks.

State directories .online and .unified-backup are intentionally not moved. Do not commit/share their contents. docker-compose.yml stays at root to preserve the current project and volume identity. Backward commands such as python online.py status and python scripts/patch-viewer.py continue to work.
