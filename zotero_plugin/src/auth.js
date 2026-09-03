/* Token authentication for the Wiki Organizer local endpoints.
 *
 * The token is generated on first startup and stored in the
 * extensions.zotero.wikiOrganizer.token preference (the authoritative copy).
 * A convenience copy is written to <dataDir>/wiki-organizer-token.txt so the
 * Python client can pick it up. The token never appears in the audit log or
 * in ordinary debug output.
 */

var WikiOrgAuth = {
	TOKEN_PREF: "extensions.zotero.wikiOrganizer.token",

	_token: null,

	init: function () {
		let token = "";
		try {
			token = String(Zotero.Prefs.get(this.TOKEN_PREF, true) || "");
		}
		catch (e) {
			Zotero.debug("[wiki-organizer] could not read token preference: " + e, 2);
		}
		if (!token) {
			token = this.randomToken(40);
			Zotero.Prefs.set(this.TOKEN_PREF, token, true);
			Zotero.debug("[wiki-organizer] generated new API token");
		}
		this._token = token;
		return token;
	},

	randomToken: function (length) {
		let alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
		if (typeof crypto === "undefined" || !crypto.getRandomValues) {
			return Zotero.Utilities.randomString(length);
		}
		let result = "";
		let bytes = new Uint8Array(32);
		while (result.length < length) {
			crypto.getRandomValues(bytes);
			for (let byte of bytes) {
				if (byte < 248) result += alphabet[byte % alphabet.length];
				if (result.length === length) break;
			}
		}
		return result;
	},

	getToken: function () {
		return this._token;
	},

	extractToken: function (requestData) {
		// Zotero wraps request headers in a case-insensitive proxy.
		let auth = String((requestData.headers || {})["authorization"] || "").trim();
		let match = /^Bearer\s+(.+)$/i.exec(auth);
		if (match) {
			return match[1].trim();
		}
		return null;
	},

	// Length-independent comparison so a caller cannot shortcut on length;
	// localhost-only in practice, but this costs nothing.
	tokensEqual: function (a, b) {
		a = String(a || "");
		b = String(b || "");
		let diff = a.length ^ b.length;
		let n = Math.max(a.length, b.length);
		for (let i = 0; i < n; i++) {
			diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
		}
		return diff === 0;
	},

	authorize: function (requestData) {
		if (!this._token) {
			return false;
		}
		let provided = this.extractToken(requestData);
		return !!provided && this.tokensEqual(provided, this._token);
	},

	writeTokenFile: async function () {
		if (!this._token) {
			return;
		}
		// Errors propagate to the caller (plugin startup task) so failures
		// become visible in the health endpoint instead of being swallowed.
		let path = WikiOrgFs.join(
			WikiOrgFs.dataDirPath(),
			"wiki-organizer-token.txt"
		);
		let content =
			"token: " + this._token + "\n" +
			"\n" +
			"This file is maintained by the Zotero Wiki Organizer plugin.\n" +
			"The authoritative value lives in the Zotero preference\n" +
			"extensions.zotero.wikiOrganizer.token (see about:config).\n" +
			"\n" +
			"Usage from the llm-wiki repository:\n" +
			"  export ZOTERO_WIKI_ORGANIZER_TOKEN=" + this._token + "\n" +
			"  uv run python -X utf8 tools/zotero_client.py health\n" +
			"\n" +
			"Do not commit this token to git.\n" +
			"请勿将 token 提交到 git。\n";
		// Establish restrictive permissions before placing the secret on disk.
		// If the process dies during the update, the convenience mirror may be
		// empty, but it will not leave a newly-created world-readable token.
		let tmpPath = path + ".tmp-" + Date.now();
		await WikiOrgFs.writeUTF8(tmpPath, content);
		await WikiOrgFs.setPrivatePermissions(tmpPath);
		if (WikiOrgFs.IOUtils && WikiOrgFs.IOUtils.move) {
			await WikiOrgFs.IOUtils.move(tmpPath, path, { noOverwrite: false });
		}
		else {
			// Older builds lack atomic move; retain the protected-file fallback.
			await WikiOrgFs.writeUTF8(path, "");
			await WikiOrgFs.setPrivatePermissions(path);
			await WikiOrgFs.writeUTF8(path, content);
		}
	}
};
