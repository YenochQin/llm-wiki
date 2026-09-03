/* Plugin assembly: token setup, endpoint registration, audit trail.
 *
 * bootstrap.js loads all modules first, then calls init() here. startup must
 * stay synchronous, so async side effects run detached in _runStartupTasks.
 */

var WikiOrganizerPlugin = {
	id: null,
	version: null,
	rootURI: null,
	// Last startup-task error (token file / audit log writing), surfaced
	// through the health endpoint so failures are diagnosable remotely.
	startupError: null,
	startupReady: false,
	_shuttingDown: false,

	init: function ({ id, version, rootURI }) {
		this.id = id;
		this.version = version;
		this.rootURI = rootURI;
		this._shuttingDown = false;

		WikiOrgAuth.init();
		WikiOrgAudit.init();
		let enabled = true;
		try {
			enabled = Zotero.Prefs.get("extensions.zotero.wikiOrganizer.enabled", true) !== false;
		}
		catch (e) {
			Zotero.debug("[wiki-organizer] could not read enabled preference: " + e, 2);
		}
		if (!enabled) {
			this.startupReady = true;
			Zotero.debug("[wiki-organizer] disabled by preference");
			return;
		}
		WikiOrgEndpoint.register({ version: version, plugin: this });
		this._runStartupTasks();
		Zotero.debug("[wiki-organizer] started (version " + version + ")");
	},

	_runStartupTasks: async function () {
		let attempt = async () => {
			// File writes wait for full startup so the data directory is
			// guaranteed initialized; when the plugin is installed while
			// Zotero is already running, the promise is already resolved.
			await (Zotero.uiReadyPromise || Zotero.initializationPromise || Promise.resolve());
			if (this._shuttingDown) return;
			await WikiOrgAuth.writeTokenFile();
			if (this._shuttingDown) return;
			await WikiOrgAudit.record({
				action: "plugin_started",
				pluginVersion: this.version,
				zoteroVersion: Zotero.version
			});
		};
		try {
			await attempt();
			this.startupError = null;
			this.startupReady = true;
		}
		catch (e) {
			this.startupError = String((e && e.stack) || e);
			Zotero.debug("[wiki-organizer] startup task failed: " + e, 2);
			try {
				await Zotero.Promise.delay(15000);
				await attempt();
				this.startupError = null;
				this.startupReady = true;
				Zotero.debug("[wiki-organizer] startup task succeeded on retry");
			}
			catch (e2) {
				this.startupError = String((e2 && e2.stack) || e2);
				this.startupReady = false;
				Zotero.debug("[wiki-organizer] startup retry failed: " + e2, 2);
			}
		}
	},

	cleanup: function () {
		this._shuttingDown = true;
		WikiOrgEndpoint.unregister();
		Promise.resolve()
			.then(() => WikiOrgAudit.record({ action: "plugin_stopped" }))
			.catch(() => {});
		Zotero.debug("[wiki-organizer] stopped");
	}
};

Zotero.WikiOrganizer = WikiOrganizerPlugin;
