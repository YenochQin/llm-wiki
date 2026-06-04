import sys
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import _cli_io


class FakeStream:
    def __init__(self, encoding: str) -> None:
        self.encoding = encoding
        self.reconfigure_calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.reconfigure_calls.append(kwargs)
        if "encoding" in kwargs:
            self.encoding = kwargs["encoding"]


class CliIoTests(unittest.TestCase):
    def test_configure_utf8_stdio_reconfigures_non_utf8_streams(self) -> None:
        stdin = FakeStream("cp936")
        stdout = FakeStream("cp936")
        stderr = FakeStream("cp1252")

        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(sys, "stdin", stdin),
            mock.patch.object(sys, "stdout", stdout),
            mock.patch.object(sys, "stderr", stderr),
        ):
            _cli_io.configure_utf8_stdio()
            self.assertEqual(__import__("os").environ["PYTHONUTF8"], "1")
            self.assertEqual(__import__("os").environ["PYTHONIOENCODING"], "utf-8")

        self.assertEqual(stdin.encoding, "utf-8")
        self.assertEqual(stdout.encoding, "utf-8")
        self.assertEqual(stderr.encoding, "utf-8")
        self.assertEqual(stdin.reconfigure_calls, [{"encoding": "utf-8", "errors": "replace"}])
        self.assertEqual(stdout.reconfigure_calls, [{"encoding": "utf-8", "errors": "replace"}])
        self.assertEqual(stderr.reconfigure_calls, [{"encoding": "utf-8", "errors": "replace"}])

    def test_configure_utf8_stdio_leaves_utf8_streams_alone(self) -> None:
        stdout = FakeStream("UTF-8")
        stderr = FakeStream("utf-8")

        with mock.patch.object(sys, "stdout", stdout), mock.patch.object(sys, "stderr", stderr):
            _cli_io.configure_utf8_stdio()

        self.assertEqual(stdout.reconfigure_calls, [])
        self.assertEqual(stderr.reconfigure_calls, [])


if __name__ == "__main__":
    unittest.main()
