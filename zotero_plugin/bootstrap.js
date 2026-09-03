/* Zotero Wiki Organizer — bootstrap lifecycle entry.
 *
 * Zotero loads this file for install/startup/shutdown/uninstall events
 * (WebExtensions-style bootstrap plugin, manifest_version 2). It only wires
 * up module loading; all logic lives in src/.
 *
 * Loaded modules share this bootstrap scope, so each src/*.js file defines a
 * single top-level `var WikiOrg…` namespace and may reference Zotero,
 * Services, and namespaces defined by previously loaded modules.
 */

function install() {
	Zotero.debug("[wiki-organizer] installed");
}

function startup({ id, version, resourceURI, rootURI = resourceURI.spec }) {
	// Plain scripts + Services.scriptloader keep the plugin build-free.
	Services.scriptloader.loadSubScript(rootURI + "src/fs.js");
	Services.scriptloader.loadSubScript(rootURI + "src/auth.js");
	Services.scriptloader.loadSubScript(rootURI + "src/audit.js");
	Services.scriptloader.loadSubScript(rootURI + "src/collections.js");
	Services.scriptloader.loadSubScript(rootURI + "src/items.js");
	Services.scriptloader.loadSubScript(rootURI + "src/migration.js");
	Services.scriptloader.loadSubScript(rootURI + "src/endpoint.js");
	Services.scriptloader.loadSubScript(rootURI + "src/plugin.js");
	Zotero.WikiOrganizer.init({ id, version, rootURI });
}

function shutdown({ id, version, resourceURI, rootURI = resourceURI.spec }) {
	if (Zotero.WikiOrganizer) {
		Zotero.WikiOrganizer.cleanup();
		delete Zotero.WikiOrganizer;
	}
}

function uninstall() {
	Zotero.debug("[wiki-organizer] uninstalled");
}
