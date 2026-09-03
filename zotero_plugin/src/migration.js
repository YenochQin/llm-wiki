/* Read-only inspection of historically broken collection keys.
 *
 * docs/zotero-internal-api-plugin-plan.md §9 requires auditing the seven
 * collections that were once inserted directly into zotero.sqlite before
 * any cleanup decision. Inspection remains read-only; deletion (eraseTx) is
 * exposed only through a confirmation-gated, legacy-key allowlist below.
 */

var WikiOrgMigration = {
	// Plan §2.2: keys inserted via direct SQLite writes.
	DEFAULT_KEYS: [
		"TSTCOL01",
		"DIEOX30F",
		"PBY5ON8P",
		"0IHICR0L",
		"6AQC6W6L",
		"I6HRY16Y",
		"I4B2NBPP"
	],
	EXPECTED_NAMES: {
		"TSTCOL01": "test",
		"DIEOX30F": "Wiki Documents",
		"PBY5ON8P": "Relativistic Atomic Structure",
		"0IHICR0L": "Open-Shell Spectroscopy",
		"6AQC6W6L": "Hyperfine and Nuclear Structure",
		"I6HRY16Y": "Isotope Shifts and King Plots",
		"I4B2NBPP": "Astrophysical and Plasma Applications"
	},
	ERASE_CONFIRMATION: "ERASE_LEGACY_COLLECTIONS",

	_loadByKeys: async function (libraryID, keys) {
		if (!keys.length) return [];
		let placeholders = keys.map(() => "?").join(",");
		let ids = await Zotero.DB.columnQueryAsync(
			"SELECT collectionID FROM collections WHERE libraryID=? AND key IN ("
				+ placeholders + ")",
			[libraryID].concat(keys)
		);
		return await Zotero.Collections.getAsync(ids || []);
	},

	inspect: async function (keys) {
		await WikiOrgCollections.waitUntilReady();
		let requested = (Array.isArray(keys) && keys.length ? keys : this.DEFAULT_KEYS)
			.map((k) => String(k).trim().toUpperCase())
			.filter((k) => k.length);

		let counts = await WikiOrgCollections.itemCountMap();

		// Collection keys are unique per library, not globally; search the
		// user library first, then other libraries.
		let userLibrary = null;
		let otherLibraries = [];
		for (let library of Zotero.Libraries.getAll()) {
			if (library.libraryType === "user") {
				userLibrary = library;
			}
			else {
				otherLibraries.push(library);
			}
		}
		let orderedLibraries = userLibrary ? [userLibrary].concat(otherLibraries) : otherLibraries;

		let all = [];
		for (let library of orderedLibraries) {
			try {
				let collections = await Zotero.Collections.getByLibrary(library.libraryID, true);
				let loadedKeys = new Set((collections || []).map((c) => c.key));
				let missingKeys = requested.filter((key) => !loadedKeys.has(key));
				if (missingKeys.length) {
					collections = (collections || []).concat(
						await this._loadByKeys(library.libraryID, missingKeys)
					);
				}
				all = all.concat(collections || []);
			}
			catch (e) {
				Zotero.debug("[wiki-organizer] could not list collections of library "
					+ library.libraryID + ": " + e, 2);
			}
		}

		let found = [];
		let missing = [];
		for (let key of requested) {
			let c = all.find((x) => x.key === key);
			if (!c) {
				missing.push(key);
				continue;
			}
			let library = Zotero.Libraries.get(c.libraryID);
			let parentKey = c.parentKey || null;
			let parent = parentKey
				? all.find((x) => x.key === parentKey && x.libraryID === c.libraryID)
				: null;
			found.push({
				key: c.key,
				collectionID: c.id,
				name: c.name,
				libraryID: c.libraryID,
				libraryName: library ? library.name : null,
				libraryType: library ? library.libraryType : null,
				parentKey: parentKey,
				parentName: parent ? parent.name : null,
				version: c.version,
				itemCount: counts.get(c.id) || 0
			});
		}
		return {
			readOnly: true,
			requestedKeys: requested,
			found: found,
			missing: missing
		};
	},

	// Permanently erase only the seven collections created by the old direct
	// SQLite script. The caller must provide an exact confirmation string; keys
	// outside DEFAULT_KEYS and collections containing items are rejected.
	eraseLegacy: async function (keys, confirmation) {
		await WikiOrgCollections.waitUntilReady();
		if (confirmation !== this.ERASE_CONFIRMATION) {
			throw new WikiOrgValidationError(
				"confirmation must exactly equal " + this.ERASE_CONFIRMATION
			);
		}
		let requested = (Array.isArray(keys) && keys.length ? keys : this.DEFAULT_KEYS)
			.map((k) => String(k).trim().toUpperCase())
			.filter((k) => k.length);
		let allowed = new Set(this.DEFAULT_KEYS);
		let unknown = requested.filter((k) => !allowed.has(k));
		if (unknown.length) {
			throw new WikiOrgValidationError(
				"refusing to erase non-legacy collection key(s): " + unknown.join(", ")
			);
		}
		requested = [...new Set(requested)];
		let libraryID = WikiOrgCollections.requireUserLibrary();
		let collections = await Zotero.Collections.getByLibrary(libraryID, true);
		let loadedKeys = new Set((collections || []).map((c) => c.key));
		let missingKeys = requested.filter((key) => !loadedKeys.has(key));
		if (missingKeys.length) {
			collections = (collections || []).concat(
				await this._loadByKeys(libraryID, missingKeys)
			);
		}
		let byKey = new Map((collections || []).map((c) => [c.key, c]));
		let pending = [];
		let missing = [];
		for (let key of requested) {
			let c = byKey.get(key);
			if (!c) {
				missing.push(key);
				continue;
			}
			let expectedName = this.EXPECTED_NAMES[key];
			if (expectedName && c.name !== expectedName) {
				throw new WikiOrgValidationError(
					"refusing to erase " + key + ": expected name "
						+ JSON.stringify(expectedName) + ", found " + JSON.stringify(c.name)
				);
			}
			pending.push(c);
		}
		// getAsync() loads primary fields only. Load both child data types before
		// calling getChild*() or eraseTx(), whose descendant traversal requires
		// the parent object's child-collection cache to be initialized.
		if (pending.length) {
			await Zotero.Collections.loadDataTypes(pending, ["childCollections", "childItems"]);
		}
		// Check item membership only after childItems has been loaded. Include
		// trashed items: eraseTx() removes collection memberships even when the
		// item itself is in the trash.
		for (let c of pending) {
			let items = c.getChildItems(true, true) || [];
			if (items.length) {
				throw new WikiOrgValidationError(
					"refusing to erase " + c.key + ": it contains " + items.length
						+ " item(s); no items will be removed"
				);
			}
		}
		let requestedSet = new Set(requested);
		for (let c of pending) {
			// getChildCollections(true) returns numeric IDs. Use the descendant
			// object API so arbitrary-depth legacy trees can be checked by key.
			let descendants = c.getDescendents(false, "collection", true) || [];
			let outside = descendants.filter((d) => !requestedSet.has(d.key));
			if (outside.length) {
				throw new WikiOrgValidationError(
					"refusing to erase " + c.key + ": it has non-legacy child collection(s)"
				);
			}
		}

		let removed = [];
		while (pending.length) {
			let leafIndex = pending.findIndex((c) => {
				let childKeys = (c.getChildCollections(false) || []).map((d) => d.key);
				return !childKeys.some((key) => pending.some((p) => p.key === key));
			});
			if (leafIndex < 0) {
				throw new Error("legacy collection hierarchy contains a cycle");
			}
			let c = pending.splice(leafIndex, 1)[0];
			await c.eraseTx();
			removed.push({ key: c.key, collectionID: c.id, name: c.name });
		}
		return { destructive: true, confirmation: this.ERASE_CONFIRMATION, removed, missing };
	}
};
