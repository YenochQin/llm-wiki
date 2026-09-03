/* Minimal append-only audit log for Wiki Organizer operations.
 *
 * JSON Lines at <dataDir>/wiki-organizer-audit.jsonl. Only metadata (names,
 * keys, ids, outcomes) is recorded — never tokens, and never item content.
 * Write failures degrade to Zotero.debug output instead of failing requests.
 */

var WikiOrgAudit = {
	_enabled: true,
	_writeFailed: false,
	_queue: Promise.resolve(),

	init: function () {
		try {
			this._enabled = Zotero.Prefs.get(
				"extensions.zotero.wikiOrganizer.auditLog", true
			) !== false;
		}
		catch (e) {
			this._enabled = true;
			Zotero.debug("[wiki-organizer] could not read auditLog preference: " + e, 2);
		}
	},

	path: function () {
		return WikiOrgFs.join(
			WikiOrgFs.dataDirPath(),
			"wiki-organizer-audit.jsonl"
		);
	},

	record: async function (entry) {
		if (!this._enabled) {
			return;
		}
		// Serialize appends so concurrent requests cannot
		// overwrite each other's audit records.
		this._queue = this._queue.then(
			() => this._record(entry),
			() => this._record(entry)
		);
		return this._queue;
	},

	_record: async function (entry) {
		entry.time = new Date().toISOString();
		let line = JSON.stringify(entry) + "\n";
		try {
			await WikiOrgFs.writeUTF8(this.path(), line, true);
			this._writeFailed = false;
		}
		catch (e) {
			if (!this._writeFailed) {
				// Log once per outage instead of on every request.
				this._writeFailed = true;
				Zotero.debug("[wiki-organizer] audit log write failed: " + e, 2);
			}
		}
	}
};
