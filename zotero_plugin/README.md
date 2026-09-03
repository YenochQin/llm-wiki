# Zotero Wiki Organizer

A local-only Zotero plugin that lets the llm-wiki repository manage Zotero
collections through **Zotero's internal object API**. It exists to replace the
failed direct-`zotero.sqlite` approach recorded in
`docs/zotero-internal-api-plugin-plan.md` §2.2: every write goes through
`new Zotero.Collection()` + `await saveTx()`, so Zotero itself owns the
database transaction, object cache, version field, and sync queue, and the
collection keys are always the ones Zotero generated.

## Security model

- Endpoints ride on Zotero's built-in connector server (`127.0.0.1:23119`);
  the plugin never opens its own port.
- Zotero's server itself rejects non-loopback `Host` headers, and silently
  drops requests that look like a browser (Mozilla user agent or an `Origin`
  header) unless they carry `Zotero-Allowed-Request: 1`. The Python client
  sends that header but not a browser UA.
- All endpoints require a token in the `Authorization: Bearer <token>` header.
  Query-string tokens are deliberately not accepted because URLs may be logged.
  The token is generated at first startup (40 random
  alphanumerics), stored in the preference
  `extensions.zotero.wikiOrganizer.token` (see `about:config`; authoritative),
  and mirrored to `<Zotero data dir>/wiki-organizer-token.txt` (mode 0600 on
  platforms that support permission control) for pickup.
  The token never appears in the audit log.
- Responses carry collection metadata only — never item content or attachment
  paths.

## Layout

```text
zotero_plugin/
├── manifest.json        # manifest_version 2; applications.zotero requires
│                        #   id + update_url + strict_min/max_version on Zotero 10
├── bootstrap.js         # install/startup/shutdown lifecycle, loads src/
├── prefs.js             # default preferences (applied by Zotero on install)
├── src/
│   ├── auth.js          # token generation + request authentication
│   ├── audit.js         # append-only JSONL audit log
│   ├── collections.js   # lookup, idempotent create, shared error classes
│   ├── migration.js     # inspect and confirmation-gated erase of legacy keys
│   ├── items.js          # additive item-to-collection assignment
│   ├── endpoint.js      # HTTP endpoint registration and error mapping
│   └── plugin.js        # assembly; exposes Zotero.WikiOrganizer
├── package_xpi.py       # stdlib-only packager -> dist/*.xpi
└── README.md
```

No build step: `bootstrap.js` loads `src/*.js` with
`Services.scriptloader.loadSubScript` into the shared bootstrap scope.

The repository also contains optional Linux desktop integration helpers,
`launch-zotero.sh` and `zotero-wiki-organizer.desktop`. They are excluded from
the XPI and are installed separately only when the desktop entry needs the
`-url` wrapper described in [`docs/zotero-troubleshooting.md`](../docs/zotero-troubleshooting.md).

## Install / uninstall

```bash
uv run python -X utf8 zotero_plugin/package_xpi.py
# -> zotero_plugin/dist/zotero-wiki-organizer-<manifest version>.xpi
```

In Zotero: `Tools → Plugins → ⚙ → Install Plugin From File…` and pick the
`.xpi`. After startup, `<dataDir>/wiki-organizer-token.txt` appears. Rollback
is simply disabling or removing the plugin in the same dialog — it touches no
user data and unregisters its endpoints on shutdown.

## Endpoints (v1)

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/wiki-organizer/v1/health` | readiness, versions, collection count |
| GET  | `/wiki-organizer/v1/collections` | full collection tree of the personal library |
| POST | `/wiki-organizer/v1/collections` | idempotent create (`create-if-missing`) |
| POST | `/wiki-organizer/v1/items/assign` | add items to collections without removing existing memberships |
| GET  | `/wiki-organizer/v1/migration/inspect?keys=…` | **read-only** audit of legacy keys |
| POST | `/wiki-organizer/v1/migration/erase` | confirmation-gated removal of the seven legacy empty collections |

Create request (`parent` may be omitted for top-level; `parentKey` is the
8-char alternative; a `'/'`-separated path resolves nested parents):

```json
{ "name": "Relativistic Atomic Structure", "parent": "Wiki Documents", "mode": "create-if-missing" }
```

Item assignment request (only additive membership changes are supported):

```json
{ "mode": "add", "assignments": [
  { "itemKey": "XXXXXXXX", "collectionKeys": ["YYYYYYYY", "ZZZZZZZZ"] }
] }
```

The endpoint resolves items and collections through Zotero's internal object
API and calls `item.saveTx()`. Existing collection memberships are preserved;
repeating a request is idempotent and reports `changed: false` for unchanged
items.

Create response (repeat requests return `created: false` and the same key):

```json
{ "name": "Relativistic Atomic Structure", "parent": "Wiki Documents",
  "parentKey": "XXXXXXXX", "key": "YYYYYYYY", "collectionID": 123,
  "created": true, "version": 1, "libraryID": 1 }
```

Error model: `401` bad/missing token · `400` invalid name / unknown parent /
bad body (`application/json` required) · `409` ambiguous same-name parent ·
`404` plugin missing · `503` Zotero still starting · `500` internal failure
(do **not** blind-retry writes — run `list` first).

Semantics worth knowing:

- Idempotency is scoped to name **and** parent; the same name under a
  different parent is never reused.
- If several existing collections already share the requested name+parent,
  the first one is reused and the response carries an explanatory `note`.
- Listing marks collections whose parent key is missing as `orphan: true`
  (relevant to the legacy rows) instead of hiding them.
- `migration/inspect` is deliberately read-only. Deletion (`eraseTx`) is
  exposed separately at `migration/erase` and requires the exact confirmation
  string plus the legacy-key/name/empty-collection checks described in plan §9.

## Python client

`tools/zotero_client.py` in the repository root never touches the SQLite
file; it refuses non-loopback endpoints by default, sets connect/read
timeouts, maps server errors to readable messages, and re-reads the tree
after every create to verify the returned key.

Token resolution order: `--token` → `ZOTERO_WIKI_ORGANIZER_TOKEN` →
`--token-file` / `ZOTERO_WIKI_ORGANIZER_TOKEN_FILE` → **automatic fallback
reading `extensions.zotero.wikiOrganizer.token` from
  `~/.zotero/zotero/*/prefs.js`** on Linux, the standard Zotero Profiles path
on macOS, or `%APPDATA%/Zotero/Zotero/Profiles/*/prefs.js` on Windows. In
practice the client works with no configuration when the profile is found.

> Troubleshooting note (v0.1.0 → v0.1.10): the startup task that writes
> `wiki-organizer-token.txt` and `wiki-organizer-audit.jsonl` into the data
> directory failed silently in 0.1.0/0.1.1. Root cause (verified against the
> local Zotero 10 build's `dataDirectory.js`): `Zotero.DataDirectory.dir` is
> a plain **string** path, so accessing `.dir.path` yields `undefined` and
> the joined path becomes invalid. 0.1.2 fixed that and exposed
> `startupError` in the health response; it also revealed that IOUtils'
> append mode (`{ mode: "append" }`) fails on some builds; current versions
> use `appendOrCreate` and retain a compatibility fallback for older builds.

```bash
uv run python -X utf8 tools/zotero_client.py health
uv run python -X utf8 tools/zotero_client.py list
uv run python -X utf8 tools/zotero_client.py create --name "Wiki Documents"
uv run python -X utf8 tools/zotero_client.py create \
  --name "Relativistic Atomic Structure" --parent "Wiki Documents"
uv run python -X utf8 tools/zotero_client.py inspect
uv run python -X utf8 tools/zotero_client.py find-doi 10.1103/PhysRevA.109.042811
uv run python -X utf8 tools/zotero_client.py erase-legacy \
  --confirm ERASE_LEGACY_COLLECTIONS
```

Exit codes: `0` success · `1` client/config error · `2` server error or
failed post-write verification.

## Verified Zotero API contract (Phase A)

Confirmed against the Zotero main-branch source (`server.js`,
`xpcom/data/collections.js`, `prefs.js`) before implementation:

1. Endpoints must be constructor functions assigned to
   `Zotero.Server.Endpoints["/path"]` with `supportedMethods`/`init` on the
   prototype; the server instantiates them with `new`.
2. `init` declared with exactly one parameter receives
   `{ method, pathname, searchParams, headers, data }` and may return a
   promise of `[status, contentType, body]`; `application/json` POST bodies
   arrive pre-parsed.
3. `Zotero.Collections.getByLibrary(libraryID)`, `collection.parentKey`, and
   `await collection.saveTx()` behave as the plan's pseudocode assumes.
4. `Zotero.Prefs.get/set(name, true)` addresses absolute pref paths.
5. **Manifest requirements are stricter than the Zotero 7 docs say** (this
   was learned the hard way: the first build failed to install with "may not
   be compatible with this version of Zotero"). Zotero 10 main's patched
   `Extension.sys.mjs` rejects any extension whose `applications.zotero`
   block lacks `id`, `update_url`, or `strict_max_version`. Cross-checked
   against the manifests of plugins installed and working on this exact
   build (Better BibTeX, PDF Translate, Format Metadata), which all set
   `strict_max_version: "10.999"`-style caps. Our `update_url` points at a
   GitHub release feed that does not exist yet: Zotero's periodic update
   checks will simply fail silently until one is published.

## Audit log

`<dataDir>/wiki-organizer-audit.jsonl` (append-only JSON Lines) records
`plugin_started`/`plugin_stopped`, every `collection_create` (with `created`,
key, ids), and `migration_inspect` runs. Tokens and item content are never
written.

## Test checklist (plan §11, run after install)

- [ ] `health` returns `ready: true` once Zotero is up; 503 while starting.
- [ ] Request without token → 401; wrong token → 401.
- [ ] `create` top-level → `created: true`; repeat → `created: false`, same key.
- [ ] Same name under a different parent → separate collection.
- [ ] Empty `--name` → 400; unknown `--parent` → 400; ambiguous parent → 409.
- [ ] After `create`, `list` shows the same key and the count did not grow.
- [ ] Restart Zotero → collection persists, plugin re-registers endpoints.
- [ ] Sync completes without `invalid collection key` / upload stalls.
- [ ] `inspect` reports the seven legacy keys' state without changing them.

Known limitation: requests arriving during plugin shutdown may hit
already-unregistered endpoints and simply get 404; there is no in-flight
request draining in v1.

The `erase-legacy` command is intentionally narrow: it accepts only the seven
keys recorded in `src/migration.js`, verifies their historical names, refuses
any collection containing items or non-legacy child collections, and calls
Zotero's `eraseTx()` from inside the Zotero process. It never edits
`zotero.sqlite` directly.
