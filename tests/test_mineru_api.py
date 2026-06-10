import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import _mineru


class MineruApiTests(unittest.TestCase):
    def test_data_id_is_api_safe_and_stable_for_unicode_pdf_names(self) -> None:
        pdf = Path("Gaigalas 等 - 2026 - Second-order rayleigh–schrödinger perturbation theory.pdf")

        data_id = _mineru._safe_data_id(pdf)

        self.assertRegex(data_id, r"^[A-Za-z0-9_.-]{1,128}$")
        self.assertIn("Gaigalas", data_id)
        self.assertIn("2026", data_id)

    def test_api_submit_uses_safe_data_id_and_persists_batch_state(self) -> None:
        class FakeResponse:
            def __init__(self, payload=None):
                self.payload = payload or {}

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class FakeRequests:
            posted_json = None

            @staticmethod
            def post(url, headers, json, timeout):
                FakeRequests.posted_json = json
                return FakeResponse(
                    {
                        "code": 0,
                        "data": {
                            "batch_id": "batch-123",
                            "file_urls": ["https://upload.example/pdf"],
                        },
                    }
                )

            @staticmethod
            def put(url, data, timeout):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            pdf = Path(tmp) / "Gaigalas 等 - 2026 - Second-order rayleigh–schrödinger perturbation theory.pdf"
            pdf.write_bytes(b"%PDF-1.7\n")

            with (
                mock.patch.object(_mineru, "_config", side_effect=lambda name, default="": "token" if name == "MINERU_API_TOKEN" else default),
                mock.patch.object(_mineru, "_poll_batch_until_done", side_effect=RuntimeError("stop after submit")),
                self.assertRaisesRegex(RuntimeError, "stop after submit"),
            ):
                _mineru._extract_via_api_with_requests(FakeRequests, pdf, cache_dir, "en")

            data_id = FakeRequests.posted_json["files"][0]["data_id"]
            self.assertRegex(data_id, r"^[A-Za-z0-9_.-]{1,128}$")
            self.assertNotIn(" ", data_id)
            self.assertNotIn("等", data_id)

            state = json.loads((cache_dir / "api-task.json").read_text(encoding="utf-8"))
            self.assertEqual(state["batch_id"], "batch-123")
            self.assertEqual(state["data_id"], data_id)

    def test_api_reuses_cached_batch_state_before_submitting_again(self) -> None:
        class FakeRequests:
            post_called = False
            put_called = False

            @staticmethod
            def post(*args, **kwargs):
                FakeRequests.post_called = True
                raise AssertionError("must not submit a new task")

            @staticmethod
            def put(*args, **kwargs):
                FakeRequests.put_called = True
                raise AssertionError("must not upload again")

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.7\n")
            (cache_dir / "api-task.json").write_text(
                json.dumps(
                    {
                        "batch_id": "batch-old",
                        "data_id": "paper",
                        "api_base": "https://mineru.net/api/v4",
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(_mineru, "_config", side_effect=lambda name, default="": "token" if name == "MINERU_API_TOKEN" else default),
                mock.patch.object(_mineru, "_poll_batch_until_done", return_value="https://download.example/result.zip") as poll,
                mock.patch.object(_mineru, "_download_and_extract_zip") as download,
            ):
                _mineru._extract_via_api_with_requests(FakeRequests, pdf, cache_dir, "en")

            poll.assert_called_once()
            self.assertEqual(poll.call_args.args[3], "batch-old")
            self.assertEqual(poll.call_args.args[4], "paper")
            download.assert_called_once()
            self.assertFalse(FakeRequests.post_called)
            self.assertFalse(FakeRequests.put_called)

    def test_api_ignores_cached_batch_for_different_model_version(self) -> None:
        class FakeResponse:
            def __init__(self, payload=None):
                self.payload = payload or {}

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class FakeRequests:
            posted_json = None

            @staticmethod
            def post(url, headers, json, timeout):
                FakeRequests.posted_json = json
                return FakeResponse(
                    {
                        "code": 0,
                        "data": {
                            "batch_id": "batch-new",
                            "file_urls": ["https://upload.example/pdf"],
                        },
                    }
                )

            @staticmethod
            def put(url, data, timeout):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.7\n")
            (cache_dir / "api-task.json").write_text(
                json.dumps(
                    {
                        "batch_id": "batch-old",
                        "data_id": "paper",
                        "api_base": "https://mineru.net/api/v4",
                        "model_version": "vlm",
                        "language": "en",
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(_mineru, "_config", side_effect=lambda name, default="": "token" if name == "MINERU_API_TOKEN" else default),
                mock.patch.object(_mineru, "_poll_batch_until_done", side_effect=RuntimeError("stop after submit")),
                self.assertRaisesRegex(RuntimeError, "stop after submit"),
            ):
                _mineru._extract_via_api_with_requests(FakeRequests, pdf, cache_dir, "en")

            self.assertEqual(FakeRequests.posted_json["model_version"], "pipeline")
            state = json.loads((cache_dir / "api-task.json").read_text(encoding="utf-8"))
            self.assertEqual(state["batch_id"], "batch-new")
            self.assertEqual(state["model_version"], "pipeline")

    def test_poll_tolerates_transient_read_timeout(self) -> None:
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {
                                "data_id": "paper",
                                "state": "done",
                                "full_zip_url": "https://download.example/result.zip",
                            }
                        ]
                    },
                }

        class FakeTimeout(Exception):
            pass

        class FakeExceptions:
            Timeout = FakeTimeout
            ReadTimeout = FakeTimeout

        class FakeRequests:
            exceptions = FakeExceptions
            calls = 0
            timeouts: list[int] = []

            @staticmethod
            def get(url, headers, timeout):
                FakeRequests.calls += 1
                FakeRequests.timeouts.append(timeout)
                if FakeRequests.calls == 1:
                    raise FakeTimeout("read timed out")
                return FakeResponse()

        with mock.patch.object(_mineru.time, "sleep"):
            url = _mineru._poll_batch_until_done(
                FakeRequests,
                "https://mineru.net/api/v4",
                {"Authorization": "Bearer token"},
                "batch-123",
                "paper",
            )

        self.assertEqual(url, "https://download.example/result.zip")
        self.assertEqual(FakeRequests.calls, 2)
        self.assertEqual(FakeRequests.timeouts, [_mineru.POLL_READ_TIMEOUT_SEC, _mineru.POLL_READ_TIMEOUT_SEC])

    def test_normalize_library_layout_accepts_v2_content_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            (cache_dir / "full.md").write_text("# parsed\n", encoding="utf-8")
            (cache_dir / "task_content_list_v2.json").write_text('[{"type": "text"}]\n', encoding="utf-8")

            _mineru._normalize_library_layout(cache_dir, "paper")

            self.assertEqual((cache_dir / "paper.md").read_text(encoding="utf-8"), "# parsed\n")
            self.assertEqual((cache_dir / "paper.json").read_text(encoding="utf-8"), '[{"type": "text"}]\n')
            self.assertFalse((cache_dir / "task_content_list_v2.json").exists())

    def test_existing_outputs_ignores_api_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            md_path = cache_dir / "paper.md"
            json_path = cache_dir / "paper.json"
            md_path.write_text("# parsed\n", encoding="utf-8")
            json_path.write_text("[]\n", encoding="utf-8")
            (cache_dir / "api-task.json").write_text('{"batch_id": "batch-123"}\n', encoding="utf-8")

            self.assertEqual(_mineru._existing_outputs(cache_dir), (md_path, json_path))

    def test_normalize_library_layout_prefers_v1_over_bare_v2_content_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            (cache_dir / "full.md").write_text("# parsed\n", encoding="utf-8")
            (cache_dir / "task_content_list.json").write_text('[{"type": "v1"}]\n', encoding="utf-8")
            (cache_dir / "content_list_v2.json").write_text('[{"type": "v2"}]\n', encoding="utf-8")

            _mineru._normalize_library_layout(cache_dir, "paper")

            self.assertEqual((cache_dir / "paper.json").read_text(encoding="utf-8"), '[{"type": "v1"}]\n')

    def test_normalize_library_layout_rejects_multiple_v2_content_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            (cache_dir / "full.md").write_text("# parsed\n", encoding="utf-8")
            (cache_dir / "content_list_v2.json").write_text('[{"type": "v2-a"}]\n', encoding="utf-8")
            (cache_dir / "task_content_list_v2.json").write_text('[{"type": "v2-b"}]\n', encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "ambiguous content list JSON"):
                _mineru._normalize_library_layout(cache_dir, "paper")

    def test_poll_matches_original_file_name_when_data_id_is_sanitized(self) -> None:
        original_file_name = "Gaigalas 等 - 2026 - Second-order rayleigh–schrödinger perturbation theory.pdf"
        safe_data_id = _mineru._safe_data_id(Path(original_file_name))

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "code": 0,
                    "data": {
                        "extract_result": [
                            {
                                "data_id": "other-paper",
                                "file_name": "other.pdf",
                                "state": "done",
                                "full_zip_url": "https://download.example/wrong.zip",
                            },
                            {
                                "file_name": original_file_name,
                                "state": "done",
                                "full_zip_url": "https://download.example/correct.zip",
                            },
                        ]
                    },
                }

        class FakeRequests:
            @staticmethod
            def get(url, headers, timeout):
                return FakeResponse()

        url = _mineru._poll_batch_until_done(
            FakeRequests,
            "https://mineru.net/api/v4",
            {"Authorization": "Bearer token"},
            "batch-123",
            safe_data_id,
            file_name=original_file_name,
        )

        self.assertEqual(url, "https://download.example/correct.zip")


if __name__ == "__main__":
    unittest.main()
