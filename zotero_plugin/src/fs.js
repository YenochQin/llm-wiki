/* File-system helpers for the plugin.
 *
 * bootstrap.js injects IOUtils and PathUtils into this plugin scope. If a
 * target build lacks either global, retain an explicit degraded state instead
 * of importing unavailable resource URLs.
 */

var WikiOrgFs = {
	IOUtils: (typeof IOUtils !== "undefined") ? IOUtils : null,
	PathUtils: (typeof PathUtils !== "undefined") ? PathUtils : null,

	// Zotero.DataDirectory.dir is a plain string path on current Zotero
	// (built with OS.Path.join); treat nsIFile-shaped values defensively
	// for older builds. Verified against dataDirectory.js in the local
	// Zotero 10 build — accessing .dir.path yields undefined.
	dataDirPath: function () {
		let dir = Zotero.DataDirectory.dir;
		return (dir && typeof dir.path === "string") ? dir.path : String(dir);
	},

	join: function (dir, name) {
		if (this.PathUtils && this.PathUtils.join) {
			try {
				return this.PathUtils.join(dir, name);
			}
			catch (e) {}
		}
		// POSIX-style fallback; Windows accepts forward slashes too.
		return String(dir).replace(/[\\/]+$/, "") + "/" + name;
	},

	// append=true uses appendOrCreate. Keep a read/rewrite fallback for older
	// Zotero builds that do not implement that mode.
	writeUTF8: async function (path, content, append) {
		if (append) {
			if (this.IOUtils && this.IOUtils.writeUTF8) {
				try {
					await this.IOUtils.writeUTF8(path, content, { mode: "appendOrCreate" });
					return;
				}
				catch (e) {
					Zotero.debug("[wiki-organizer] appendOrCreate unavailable; using fallback: " + e, 2);
				}
			}
			let existing = "";
			try { existing = await this.readUTF8(path); } catch (e) {}
			content = existing + content;
		}
		if (this.IOUtils && this.IOUtils.writeUTF8) {
			await this.IOUtils.writeUTF8(path, content);
			return;
		}
		await Zotero.File.putContentsAsync(path, content);
	},

	setPrivatePermissions: async function (path) {
		if (this.IOUtils && this.IOUtils.setPermissions) {
			await this.IOUtils.setPermissions(path, 0o600);
			return;
		}
		// Zotero's preference is authoritative if the platform lacks a
		// permissions API; never pretend that the convenience file is secure.
		throw new Error("IOUtils.setPermissions is unavailable; refusing to write an unprotected token file");
	},

	readUTF8: async function (path) {
		if (this.IOUtils && this.IOUtils.readUTF8) {
			return await this.IOUtils.readUTF8(path);
		}
		return await Zotero.File.getContentsAsync(path);
	}
};
