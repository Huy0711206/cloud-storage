# CloudBox Mail native skin
The complete Mailpit v1.32.0 source is vendored in upstream, licensed MIT (upstream/LICENSE). Its package-lock.json, go.mod and go.sum are unchanged. CloudBox React continues to use its existing pnpm lockfile. Vue/Bootstrap is retained for Mailpit, not rewritten as a partial React gateway.

Changes are limited to: original CloudBox design assets, CSS import, header brand/classes, a native Vue theme radio group and sharing its existing mp-theme preference with Settings. Existing deep-dark remains in native Settings. All upstream message, search, tags, attachment/CID, websocket, raw/HTML/text, link/HTML/spam testing, API docs, notifications, chaos, relay configuration and safety controls remain. Availability still depends on existing server configuration. No SMTP relay is enabled by this change.

The source archive SHA256 and full upstream file differences are in UPSTREAM.json. Upgrade requires deliberately choosing a new version and reviewing this short patch. No HTML response injection or compiled vendor bundle patch.

The runtime base is a local tag of the previous installed Mailpit image. Keep it for rollback. The main service uses a persistent mailpit_data volume and the original SMTP service name/port. Web UI binds only 127.0.0.1:8025. No public mail tunnel.
