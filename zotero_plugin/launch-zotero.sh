#!/bin/sh
# Desktop launcher for Zotero.  The stock SOURCE desktop entry expands an
# empty `%U` to a bare `-url`, which Zotero 10 rejects with
# NS_ERROR_ILLEGAL_VALUE.  Add `-url` only when a URL was actually supplied.
set -eu

if [ "$#" -eq 0 ]; then
	 exec /usr/bin/zotero
fi

exec /usr/bin/zotero -url "$@"
