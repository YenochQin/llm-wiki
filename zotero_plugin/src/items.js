/* Additive item-to-collection assignment through Zotero's internal object API.
 * Existing memberships are read and preserved; item.saveTx() owns persistence
 * and sync bookkeeping. No SQLite writes are performed here.
 */

var WikiOrgItems = {
	MAX_ASSIGNMENTS: 2000,
	MAX_COLLECTIONS_PER_ITEM: 32,

	getItem: async function (libraryID, itemKey) {
		if (!Zotero.Items) {
			throw new WikiOrgNotReadyError("Zotero item services are unavailable");
		}
		let item;
		try {
			if (typeof Zotero.Items.getByLibraryAndKeyAsync === "function") {
				item = await Zotero.Items.getByLibraryAndKeyAsync(libraryID, itemKey);
			}
			else if (typeof Zotero.Items.getByLibraryAndKey === "function") {
				item = Zotero.Items.getByLibraryAndKey(libraryID, itemKey);
			}
			else {
				throw new WikiOrgNotReadyError("Zotero item services are unavailable");
			}
		}
		catch (e) {
			if (e && (e.name === "UnloadedDataException"
				|| e.constructor && e.constructor.name === "UnloadedDataException")) {
				throw new WikiOrgNotReadyError("Zotero item data is not loaded yet");
			}
			throw e;
		}
		if (!item) {
			throw new WikiOrgValidationError(
				"No item with key " + itemKey + " exists in the personal library"
			);
		}
		return item;
	},

	assign: async function (body) {
		await WikiOrgCollections.waitUntilReady();
		let libraryID = WikiOrgCollections.requireUserLibrary();
		if (!body || typeof body !== "object" || Array.isArray(body)) {
			throw new WikiOrgValidationError("POST body must be an object with an assignments array");
		}
		if (body.mode !== undefined && body.mode !== "add") {
			throw new WikiOrgValidationError("mode must be 'add' (the only mode supported in v1)");
		}
		let assignments = body.assignments;
		if (!Array.isArray(assignments) || !assignments.length) {
			throw new WikiOrgValidationError("assignments must be a non-empty array");
		}
		if (assignments.length > this.MAX_ASSIGNMENTS) {
			throw new WikiOrgValidationError("too many assignments (maximum " + this.MAX_ASSIGNMENTS + ")");
		}

		// Resolve all keys before writing any item to prevent malformed batches
		// from leaving a partially applied change.
		let collections = await Zotero.Collections.getByLibrary(libraryID, true);
		let byKey = new Map((collections || []).map((c) => [c.key, c]));
		let prepared = [];
		let resolvedItems = [];
		for (let assignment of assignments) {
			if (!assignment || typeof assignment !== "object" || Array.isArray(assignment)) {
				throw new WikiOrgValidationError("each assignment must be an object");
			}
			let itemKey = String(assignment.itemKey || "").trim().toUpperCase();
			if (!/^[A-Za-z0-9]{8}$/.test(itemKey)) {
				throw new WikiOrgValidationError("itemKey must be an 8-character Zotero item key");
			}
			let keys = assignment.collectionKeys;
			if (!Array.isArray(keys) || !keys.length || keys.length > this.MAX_COLLECTIONS_PER_ITEM) {
				throw new WikiOrgValidationError(
					"collectionKeys must be a non-empty array (maximum "
						+ this.MAX_COLLECTIONS_PER_ITEM + ")"
				);
			}
			let uniqueKeys = [...new Set(keys.map((key) => String(key || "").trim().toUpperCase()))];
			if (uniqueKeys.some((key) => !/^[A-Za-z0-9]{8}$/.test(key))) {
				throw new WikiOrgValidationError("collectionKeys must contain 8-character Zotero collection keys");
			}
			let targetCollections = uniqueKeys.map((key) => {
				let collection = byKey.get(key);
				if (!collection) {
					throw new WikiOrgValidationError(
						"No collection with key " + key + " exists in the personal library"
					);
				}
				return collection;
			});
			let item = await this.getItem(libraryID, itemKey);
			resolvedItems.push(item);
			prepared.push({ itemKey: itemKey, item: item, targetCollections: targetCollections });
		}
		if (typeof Zotero.Items.loadDataTypes === "function" && resolvedItems.length) {
			await Zotero.Items.loadDataTypes(resolvedItems, ["collections"]);
		}

		let results = [];
		for (let entry of prepared) {
			let item = entry.item;
			let beforeIDs = (item.getCollections && item.getCollections()) || [];
			let before = new Set(beforeIDs);
			let added = [];
			for (let collection of entry.targetCollections) {
				if (!before.has(collection.id)) {
					item.addToCollection(collection.id);
					added.push(collection);
				}
			}
			if (added.length) {
				await item.saveTx();
			}
			let afterIDs = (item.getCollections && item.getCollections()) || [];
			let byID = new Map(collections.map((c) => [c.id, c]));
			results.push({
				itemKey: entry.itemKey,
				addedCollectionKeys: added.map((c) => c.key),
				collectionKeys: afterIDs.map((id) => (byID.get(id) || {}).key).filter(Boolean),
				changed: !!added.length
			});
		}
		return { libraryID: libraryID, count: results.length, results: results };
	}
};
