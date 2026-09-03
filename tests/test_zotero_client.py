import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import zotero_client


def _args(**overrides):
    defaults = {
        "url": None,
        "token": None,
        "token_file": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TokenFileTests(unittest.TestCase):
    def test_reads_token_prefix_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wiki-organizer-token.txt"
            path.write_text(
                "token: ABC123\n\nThis file is maintained by...\n",
                encoding="utf-8",
            )
            self.assertEqual(zotero_client._read_token_file(str(path)), "ABC123")

    def test_falls_back_to_first_nonempty_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.txt"
            path.write_text("# comment\nRAWTOKEN\n", encoding="utf-8")
            self.assertEqual(zotero_client._read_token_file(str(path)), "RAWTOKEN")

    def test_missing_file_raises_client_error(self) -> None:
        with self.assertRaises(zotero_client.ClientError):
            zotero_client._read_token_file("/nonexistent/token-file")


class TokenFromPrefsTests(unittest.TestCase):
    @mock.patch.object(zotero_client.platform, "system", return_value="Darwin")
    def test_macos_profile_root(self, _system) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Profiles"
            profile = root / "abc.default"
            profile.mkdir(parents=True)
            (profile / "prefs.js").write_text(
                'user_pref("extensions.zotero.wikiOrganizer.token", "MAC");\n', encoding="utf-8"
            )
            with mock.patch.object(zotero_client.Path, "home", return_value=Path(tmp)):
                # The platform path includes the standard subdirectories.
                app_root = Path(tmp) / "Library" / "Application Support" / "Zotero" / "Profiles"
                app_profile = app_root / "abc.default"
                app_profile.mkdir(parents=True)
                (app_profile / "prefs.js").write_text(
                    'user_pref("extensions.zotero.wikiOrganizer.token", "MAC");\n', encoding="utf-8"
                )
                self.assertEqual(zotero_client._token_from_zotero_prefs(), "MAC")

    def test_reads_token_from_prefs_js(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "abc123.default"
            profile.mkdir()
            (profile / "prefs.js").write_text(
                'user_pref("extensions.zotero.dataDir", "/x");\n'
                'user_pref("extensions.zotero.wikiOrganizer.token", "PREFTOKEN");\n',
                encoding="utf-8",
            )
            self.assertEqual(zotero_client._token_from_zotero_prefs(Path(tmp)), "PREFTOKEN")

    def test_returns_none_when_no_profile_has_the_pref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "abc.default"
            profile.mkdir()
            (profile / "prefs.js").write_text(
                'user_pref("extensions.zotero.dataDir", "/x");\n', encoding="utf-8"
            )
            self.assertIsNone(zotero_client._token_from_zotero_prefs(Path(tmp)))

    def test_returns_none_for_missing_root(self) -> None:
        self.assertIsNone(
            zotero_client._token_from_zotero_prefs(Path("/nonexistent/profile-root"))
        )


class BaseUrlTests(unittest.TestCase):
    def test_default_and_loopback_hosts_are_accepted(self) -> None:
        for host in ("127.0.0.1", "localhost", "::1"):
            url = f"http://[{host}]:23119" if ":" in host else f"http://{host}:23119"
            self.assertEqual(
                zotero_client._resolve_base_url(_args(url=url)), url.rstrip("/")
            )
        self.assertEqual(
            zotero_client._resolve_base_url(_args()),
            zotero_client.DEFAULT_BASE_URL,
        )

    def test_non_loopback_host_is_rejected_by_default(self) -> None:
        with self.assertRaises(zotero_client.ClientError):
            zotero_client._resolve_base_url(_args(url="http://192.168.1.5:23119"))

    def test_non_loopback_host_is_always_rejected(self) -> None:
        with self.assertRaises(zotero_client.ClientError):
            zotero_client._resolve_base_url(_args(url="http://192.168.1.5:23119"))

    def test_invalid_scheme_is_rejected(self) -> None:
        with self.assertRaises(zotero_client.ClientError):
            zotero_client._resolve_base_url(_args(url="ftp://127.0.0.1:23119"))


class ErrorMappingTests(unittest.TestCase):
    def test_status_specific_hints(self) -> None:
        cases = {
            401: "token",
            404: "插件未安装",
            500: "不要自动重试写入",
            503: "尚未完成启动",
        }
        for status, fragment in cases.items():
            with self.subTest(status=status):
                with self.assertRaises(zotero_client.ServerError) as ctx:
                    zotero_client._raise_server_error(status, {})
                self.assertIn(fragment, str(ctx.exception))


class DoiLookupTests(unittest.TestCase):
    def test_normalize_doi_variants(self) -> None:
        self.assertEqual(
            zotero_client.normalize_doi("https://doi.org/10.1103/PhysRevA.109.042811."),
            "10.1103/physreva.109.042811",
        )

    @mock.patch.object(zotero_client.requests, "get")
    def test_exact_doi_scan_does_not_use_fuzzy_match(self, get) -> None:
        response = mock.Mock(status_code=200)
        response.json.return_value = [
            {"data": {"key": "MATCH", "DOI": "10.1103/physreva.109.042811"}},
            {"data": {"key": "OTHER", "DOI": "10.1103/physreva.109.042812"}},
        ]
        get.return_value = response
        matches = zotero_client.find_items_by_doi(
            "10.1103/PhysRevA.109.042811", base_url="http://127.0.0.1:23119"
        )
        self.assertEqual([item["key"] for item in matches], ["MATCH"])

    def test_server_message_is_included(self) -> None:
        with self.assertRaises(zotero_client.ServerError) as ctx:
            zotero_client._raise_server_error(400, {"message": "name must not be empty"})
        self.assertIn("name must not be empty", str(ctx.exception))


class CreateOutputTests(unittest.TestCase):
    def test_json_mode_emits_json_only_after_verification(self) -> None:
        args = argparse.Namespace(
            name="Wiki Documents",
            parent=None,
            parent_key=None,
            token="TOKEN",
            token_file=None,
            url=None,
            json=True,
        )
        created = {
            "name": "Wiki Documents",
            "key": "ABCDEFGH",
            "collectionID": 1,
            "created": True,
        }
        listed = {"collections": [{"key": "ABCDEFGH"}]}
        output = io.StringIO()
        with (
            mock.patch.object(zotero_client, "_load_token", return_value="TOKEN"),
            mock.patch.object(zotero_client, "_resolve_base_url", return_value="http://127.0.0.1:23119"),
            mock.patch.object(
                zotero_client, "_request", side_effect=[(200, created), (200, listed)]
            ),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(zotero_client.cmd_create(args), zotero_client.EXIT_OK)
        self.assertEqual(json.loads(output.getvalue()), created)


class EraseLegacyTests(unittest.TestCase):
    def test_posts_explicit_confirmation_and_keys(self) -> None:
        args = argparse.Namespace(
            keys="TSTCOL01,DIEOX30F",
            confirm="ERASE_LEGACY_COLLECTIONS",
            token="TOKEN",
            token_file=None,
            url=None,
            json=True,
        )
        result = {
            "destructive": True,
            "removed": [{"key": "TSTCOL01", "name": "test", "collectionID": 110}],
            "missing": ["DIEOX30F"],
        }
        output = io.StringIO()
        with (
            mock.patch.object(zotero_client, "_load_token", return_value="TOKEN"),
            mock.patch.object(
                zotero_client, "_resolve_base_url", return_value="http://127.0.0.1:23119"
            ),
            mock.patch.object(zotero_client, "_request", return_value=(200, result)) as request,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(zotero_client.cmd_erase_legacy(args), zotero_client.EXIT_OK)
        request.assert_called_once_with(
            "POST",
            "/wiki-organizer/v1/migration/erase",
            "TOKEN",
            "http://127.0.0.1:23119",
            json_body={
                "confirmation": "ERASE_LEGACY_COLLECTIONS",
                "keys": ["TSTCOL01", "DIEOX30F"],
            },
        )
        self.assertEqual(json.loads(output.getvalue()), result)


if __name__ == "__main__":
    unittest.main()
