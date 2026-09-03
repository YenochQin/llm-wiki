/* Collection lookup and idempotent creation through Zotero's internal API.
 *
 * Every write goes through Zotero.Collection.saveTx() so Zotero owns the
 * database transaction, object cache, version field, and sync queue; keys
 * are always the ones Zotero itself generated.
 *
 * The error classes at the top are shared with endpoint.js, which maps them
 * to the HTTP error model from docs/zotero-internal-api-plugin-plan.md §7.5:
 * 400 bad request / 409 conflict / 503 not ready / 500 internal.
 */

class WikiOrgValidationError extends Error {}
class WikiOrgConflictError extends Error {}
class WikiOrgNotReadyError extends Error {}

var WikiOrgCollections = {
	READY_TIMEOUT_MS: 10000,
	MAX_NAME_LENGTH: 255,
	_createQueue: Promise.resolve(),

	waitUntilReady: async function () {
		let ready = Zotero.uiReadyPromise || Zotero.initializationPromise || Promise.resolve();
		await Promise.race([
			ready,
			new Promise((resolve, reject) => {
				Zotero.Promise.delay(this.READY_TIMEOUT_MS).then(() => {
					reject(new WikiOrgNotReadyError(
						"Zotero did not finish starting up within "
							+ this.READY_TIMEOUT_MS + " ms"
					));
				});
			})
		]);
		if (!Zotero.Collections || !Zotero.Libraries) {
			throw new WikiOrgNotReadyError("Zotero object services are unavailable");
		}
	},

	requireUserLibrary: function () {
		let libraryID = Zotero.Libraries.userLibraryID;
		if (!libraryID) {
			throw new Error("No personal Zotero library was found on this machine");
		}
		return libraryID;
	},

	// Read-only counts through Zotero's own DB connection; one query for all
	// collections. Rows include trashed items, which matches what the
	// migration audit needs.
	itemCountMap: async function () {
		let rows = await Zotero.DB.queryAsync(
			"SELECT collectionID AS collectionID, COUNT(*) AS itemCount "
				+ "FROM collectionItems GROUP BY collectionID"
		);
		let map = new Map();
		for (let row of rows || []) {
			map.set(row.collectionID, row.itemCount);
		}
		return map;
	},

	list: async function () {
		await this.waitUntilReady();
		let libraryID = this.requireUserLibrary();
		let collections = await Zotero.Collections.getByLibrary(libraryID, true);
		let counts = await this.itemCountMap();
		let byKey = new Map();
		for (let c of collections) {
			byKey.set(c.key, c);
		}
		let records = collections.map((c) => {
			let parentKey = c.parentKey || null;
			let parent = parentKey ? byKey.get(parentKey) : null;
			return {
				collectionID: c.id,
				key: c.key,
				name: c.name,
				parentKey: parentKey,
				parentName: parent ? parent.name : null,
				version: c.version,
				itemCount: counts.get(c.id) || 0
			};
		});
		return {
			libraryID: libraryID,
			count: records.length,
			collections: this._sortedTree(records)
		};
	},

	// Depth-first ordering with children sorted by name for stable,
	// human-readable output. Records whose parent is missing (dangling rows
	// such as the historical direct-SQLite inserts) are kept at the end and
	// marked orphan=true instead of disappearing from the listing.
	_sortedTree: function (records) {
		let byKey = new Map(records.map((r) => [r.key, r]));
		let childrenOf = new Map();
		let roots = [];
		for (let r of records) {
			if (r.parentKey && byKey.has(r.parentKey)) {
				if (!childrenOf.has(r.parentKey)) {
					childrenOf.set(r.parentKey, []);
				}
				childrenOf.get(r.parentKey).push(r);
			}
			else {
				roots.push(r);
			}
		}
		let sortFn = (a, b) => a.name.localeCompare(b.name) || a.key.localeCompare(b.key);
		roots.sort(sortFn);
		let ordered = [];
		let seen = new Set();
		let visit = (r) => {
			if (seen.has(r.key)) {
				return;
			}
			seen.add(r.key);
			ordered.push(r);
			let kids = (childrenOf.get(r.key) || []).sort(sortFn);
			for (let kid of kids) {
				visit(kid);
			}
		};
		for (let r of roots) {
			visit(r);
		}
		for (let r of records) {
			if (!seen.has(r.key)) {
				r.orphan = true;
				ordered.push(r);
			}
		}
		return ordered;
	},

	// Resolve the parent for a create request. Accepts either a
	// '/'-separated name path ("Wiki Documents/Topic") or an explicit
	// collection key. Returns the parent Zotero.Collection, or null for
	// top-level. Unknown segments are validation errors (400); ambiguous
	// name segments are conflicts (409).
	resolveParent: async function (parentPath, parentKey) {
		let collections = await Zotero.Collections.getByLibrary(this.requireUserLibrary(), true);

		if (parentKey !== undefined && parentKey !== null && parentKey !== "") {
			if (!/^[A-Za-z0-9]{8}$/.test(String(parentKey))) {
				throw new WikiOrgValidationError(
					"parentKey must be an 8-character Zotero collection key"
				);
			}
			let key = String(parentKey).toUpperCase();
			let match = collections.find((c) => c.key === key);
			if (!match) {
				throw new WikiOrgValidationError(
					"No collection with key " + key + " exists in the personal library"
				);
			}
			return match;
		}

		if (parentPath === undefined || parentPath === null) {
			return null;
		}
		if (typeof parentPath !== "string" || !parentPath.trim()) {
			throw new WikiOrgValidationError(
				"parent must be a non-empty collection name or '/'-separated path"
			);
		}
		let segments = parentPath.split("/").map((s) => s.trim()).filter((s) => s.length);
		let current = null;
		for (let segment of segments) {
			let currentParentKey = current ? current.key : null;
			let matches = collections.filter(
				(c) => c.name === segment && (c.parentKey || null) === currentParentKey
			);
			if (!matches.length) {
				throw new WikiOrgValidationError(
					"Parent collection '" + segment
						+ "' was not found while resolving '" + parentPath + "'"
				);
			}
			if (matches.length > 1) {
				throw new WikiOrgConflictError(
					matches.length + " collections named '" + segment
						+ "' exist at the same level in '" + parentPath
						+ "'; pass parentKey to disambiguate"
				);
			}
			current = matches[0];
		}
		return current;
	},

	// Idempotent create: same name + same parent reuses the existing
	// collection; the same name under a different parent is never reused.
	getOrCreate: async function (options) {
		// Serialize the check-and-save sequence. Zotero has no uniqueness
		// constraint for name+parent, so a concurrent pair of requests could
		// otherwise create duplicates.
		this._createQueue = this._createQueue.then(
			() => this._getOrCreate(options),
			() => this._getOrCreate(options)
		);
		return this._createQueue;
	},

	_getOrCreate: async function (options) {
		await this.waitUntilReady();
		let libraryID = this.requireUserLibrary();

		let name = options.name;
		if (typeof name !== "string") {
			throw new WikiOrgValidationError("name must be a string");
		}
		name = name.trim();
		if (!name) {
			throw new WikiOrgValidationError("name must not be empty");
		}
		if (name.length > this.MAX_NAME_LENGTH) {
			throw new WikiOrgValidationError(
				"name must be at most " + this.MAX_NAME_LENGTH + " characters"
			);
		}

		let mode = (options.mode === undefined || options.mode === null)
			? "create-if-missing"
			: options.mode;
		if (mode !== "create-if-missing") {
			throw new WikiOrgValidationError(
				"mode must be 'create-if-missing' (the only mode supported in v1)"
			);
		}

		let parentCollection = await this.resolveParent(options.parent, options.parentKey);
		let parentKey = parentCollection ? parentCollection.key : null;

		let collections = await Zotero.Collections.getByLibrary(libraryID, true);
		let matches = collections.filter(
			(c) => c.name === name && (c.parentKey || null) === parentKey
		);
		if (matches.length) {
			return {
				collection: matches[0],
				created: false,
				duplicates: matches.length,
				parentCollection: parentCollection
			};
		}

		let collection = new Zotero.Collection();
		collection.libraryID = libraryID;
		collection.name = name;
		if (parentKey) {
			collection.parentKey = parentKey;
		}
		await collection.saveTx();
		// Re-read from Zotero's object cache so the returned key and
		// collectionID are exactly what Zotero persisted.
		let saved = Zotero.Collections.get(collection.id) || collection;
		return {
			collection: saved,
			created: true,
			duplicates: 0,
			parentCollection: parentCollection
		};
	}
};
