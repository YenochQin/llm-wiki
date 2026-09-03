/* Local HTTP endpoints served by Zotero's connector server (127.0.0.1:23119).
 *
 * Verified against the Zotero main-branch server.js: each endpoint must be a
 * constructor function whose prototype carries supportedMethods/init, and
 * init is dispatched with a single requestData object when it is declared
 * with exactly one parameter ({ method, pathname, searchParams, headers,
 * data }). init may return (a promise of) [status, contentType, body]; POST
 * bodies with Content-Type application/json arrive pre-parsed in
 * requestData.data.
 *
 * Error model (plan §7.5): 401 auth, 400 validation, 409 conflict,
 * 503 not ready, 500 internal (clients must not blindly retry writes).
 */

var WikiOrgEndpoint = {
	PREFIX: "/wiki-organizer/v1",
	_registered: {},
	meta: {},

	register: function (meta) {
		this.meta = meta || {};

		function WikiOrgHealthEndpoint() {}
		WikiOrgHealthEndpoint.prototype = {
			supportedMethods: ["GET"],
			init: async function (requestData) {
				return WikiOrgEndpoint.handle(requestData, WikiOrgEndpoint.health);
			}
		};

		function WikiOrgCollectionsEndpoint() {}
		WikiOrgCollectionsEndpoint.prototype = {
			supportedMethods: ["GET", "POST"],
			supportedDataTypes: ["application/json"],
			init: async function (requestData) {
				return WikiOrgEndpoint.handle(requestData, WikiOrgEndpoint.collections);
			}
		};

		function WikiOrgMigrationInspectEndpoint() {}
		WikiOrgMigrationInspectEndpoint.prototype = {
			supportedMethods: ["GET"],
			init: async function (requestData) {
				return WikiOrgEndpoint.handle(requestData, WikiOrgEndpoint.migrationInspect);
			}
		};

		function WikiOrgMigrationEraseEndpoint() {}
		WikiOrgMigrationEraseEndpoint.prototype = {
			supportedMethods: ["POST"],
			supportedDataTypes: ["application/json"],
			init: async function (requestData) {
				return WikiOrgEndpoint.handle(requestData, WikiOrgEndpoint.migrationErase);
			}
		};

		function WikiOrgItemAssignEndpoint() {}
		WikiOrgItemAssignEndpoint.prototype = {
			supportedMethods: ["POST"],
			supportedDataTypes: ["application/json"],
			init: async function (requestData) {
				return WikiOrgEndpoint.handle(requestData, WikiOrgEndpoint.itemAssign);
			}
		};

		this._registered = {
			[this.PREFIX + "/health"]: WikiOrgHealthEndpoint,
			[this.PREFIX + "/collections"]: WikiOrgCollectionsEndpoint,
			[this.PREFIX + "/migration/inspect"]: WikiOrgMigrationInspectEndpoint,
			[this.PREFIX + "/migration/erase"]: WikiOrgMigrationEraseEndpoint,
			[this.PREFIX + "/items/assign"]: WikiOrgItemAssignEndpoint
		};
		for (let path of Object.keys(this._registered)) {
			Zotero.Server.Endpoints[path] = this._registered[path];
		}
	},

	unregister: function () {
		for (let path of Object.keys(this._registered)) {
			// Remove only endpoints this plugin instance registered, so a
			// reload never wipes someone else's endpoint.
			if (Zotero.Server.Endpoints[path] === this._registered[path]) {
				delete Zotero.Server.Endpoints[path];
			}
		}
		this._registered = {};
	},

	handle: async function (requestData, handler) {
		try {
			// Auth runs before anything else so no state leaks without a token.
			if (!WikiOrgAuth.authorize(requestData)) {
				return WikiOrgEndpoint.json(401, {
					error: "unauthorized",
					message: "Missing or invalid token. Send 'Authorization: Bearer <token>'."
				});
			}
			// Read-only diagnostics remain callable while startup is degraded, but
			// write operations must not run until startup side effects succeeded.
			if (requestData.method !== "GET"
				&& WikiOrgEndpoint.meta.plugin
				&& (WikiOrgEndpoint.meta.plugin.startupReady === false
					|| WikiOrgEndpoint.meta.plugin.startupError)) {
				return WikiOrgEndpoint.json(503, {
					error: "not_ready",
					message: "Zotero Wiki Organizer startup has not completed"
				});
			}
			return await handler.call(WikiOrgEndpoint, requestData);
		}
		catch (e) {
			if (e instanceof WikiOrgValidationError) {
				return WikiOrgEndpoint.json(400, { error: "bad_request", message: e.message });
			}
			if (e instanceof WikiOrgConflictError) {
				return WikiOrgEndpoint.json(409, { error: "conflict", message: e.message });
			}
			if (e instanceof WikiOrgNotReadyError) {
				return WikiOrgEndpoint.json(503, { error: "not_ready", message: e.message });
			}
			Zotero.debug("[wiki-organizer] request failed: " + e, 1);
			return WikiOrgEndpoint.json(500, {
				error: "internal_error",
				message: "Zotero Wiki Organizer request failed"
			});
		}
	},

	json: function (status, payload) {
		return [status, "application/json", JSON.stringify(payload, null, 2)];
	},

	health: async function () {
		let objectReady = true;
		let libraryID = null;
		let collectionCount = null;
		try {
			await WikiOrgCollections.waitUntilReady();
			libraryID = Zotero.Libraries.userLibraryID || null;
			if (libraryID) {
				let collections = await Zotero.Collections.getByLibrary(libraryID, true);
				collectionCount = collections.length;
			}
		}
		catch (e) {
			objectReady = false;
		}
		let startupError = (this.meta.plugin && this.meta.plugin.startupError) || null;
		let startupReady = !(this.meta.plugin && this.meta.plugin.startupReady === false);
		let ready = objectReady && startupReady && !startupError;
		return WikiOrgEndpoint.json(ready ? 200 : 503, {
			status: ready ? "ok" : (startupError ? "degraded" : "starting"),
			ready: ready,
			plugin: "zotero-wiki-organizer",
			pluginVersion: this.meta.version || null,
			zoteroVersion: Zotero.version,
			libraryID: libraryID,
			collectionCount: collectionCount,
			startupError: startupError ? "startup task failed; see Zotero debug log" : null
		});
	},

	collections: async function (requestData) {
		if (requestData.method === "GET") {
			return WikiOrgEndpoint.json(200, await WikiOrgCollections.list());
		}
		if (requestData.method === "POST") {
			let body = requestData.data;
			if (!body || typeof body !== "object" || Array.isArray(body)) {
				return WikiOrgEndpoint.json(400, {
					error: "bad_request",
					message: "POST body must be a JSON object with at least a 'name' field."
				});
			}
			if (body.parent !== undefined && body.parentKey !== undefined) {
				return WikiOrgEndpoint.json(400, {
					error: "bad_request",
					message: "Pass either 'parent' (name or '/'-separated path) or 'parentKey', not both."
				});
			}
			let result = await WikiOrgCollections.getOrCreate({
				name: body.name,
				parent: body.parent,
				parentKey: body.parentKey,
				mode: body.mode
			});
			let collection = result.collection;
			let response = {
				name: collection.name,
				parent: result.parentCollection ? result.parentCollection.name : null,
				parentKey: collection.parentKey || null,
				key: collection.key,
				collectionID: collection.id,
				created: result.created,
				version: collection.version,
				libraryID: collection.libraryID
			};
			if (result.duplicates > 1) {
				response.note = result.duplicates
					+ " collections already share this name and parent; the first one was"
					+ " reused and nothing new was created.";
			}
			await WikiOrgAudit.record({
				action: "collection_create",
				name: collection.name,
				parentKey: response.parentKey,
				key: collection.key,
				collectionID: collection.id,
				created: result.created,
				duplicates: result.duplicates
			});
			return WikiOrgEndpoint.json(200, response);
		}
		// Unreachable in practice: the server rejects unlisted methods itself.
		return WikiOrgEndpoint.json(400, {
			error: "bad_request",
			message: "Unsupported method."
		});
	},

	migrationInspect: async function (requestData) {
		let keysParam = requestData.searchParams ? requestData.searchParams.get("keys") : null;
		let keys = keysParam
			? keysParam.split(",").map((k) => k.trim()).filter((k) => k.length)
			: null;
		let result = await WikiOrgMigration.inspect(keys);
		await WikiOrgAudit.record({
			action: "migration_inspect",
			requested: result.requestedKeys,
			found: result.found.length,
			missing: result.missing.length
		});
		return WikiOrgEndpoint.json(200, result);
	},

	migrationErase: async function (requestData) {
		let body = requestData.data;
		if (!body || typeof body !== "object" || Array.isArray(body)) {
			return WikiOrgEndpoint.json(400, {
				error: "bad_request",
				message: "POST body must be an object with confirmation and optional keys."
			});
		}
		let keys = body.keys;
		if (keys !== undefined && (!Array.isArray(keys) || keys.some((k) => typeof k !== "string"))) {
			return WikiOrgEndpoint.json(400, {
				error: "bad_request",
				message: "keys must be an array of strings"
			});
		}
		let result = await WikiOrgMigration.eraseLegacy(keys, body.confirmation);
		await WikiOrgAudit.record({
			action: "legacy_collections_erase",
			requested: keys || WikiOrgMigration.DEFAULT_KEYS,
			removed: result.removed.map((r) => r.key),
			missing: result.missing
		});
		return WikiOrgEndpoint.json(200, result);
	},

	itemAssign: async function (requestData) {
		let result = await WikiOrgItems.assign(requestData.data);
		await WikiOrgAudit.record({
			action: "item_collection_assign",
			count: result.count,
			changed: result.results.filter((r) => r.changed).length,
			items: result.results.map((r) => ({
				itemKey: r.itemKey,
				addedCollectionKeys: r.addedCollectionKeys
			}))
		});
		return WikiOrgEndpoint.json(200, result);
	}
};
