"""Behavior tests use only the public CLI, from the repository root."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "patch_context_check.py"


class CliTests(unittest.TestCase):
    def test_machine_readable_json_reports(self):
        for patch, expected in [("--- a\n+++ b\n@@ -1 +1 @@\n alpha\n", "CLEAN"),
                                ("--- a\n+++ b\n@@ -1 +1 @@\n-beta\n+x\n", "MISMATCH"),
                                ("malformed", "INVALID")]:
            with self.subTest(expected=expected):
                result = self.invoke(patch.encode())
                self.assertEqual(json.loads(result.stdout)["code"], expected)

    def invoke(self, patch, base=b"alpha\nbeta\ngamma\n"):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / "secret-patch", Path(directory) / "secret-base"]
            for path, data in zip(paths, [patch, base]):
                path.write_bytes(data)
            before = [(p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).digest()) for p in paths]
            result = subprocess.run([sys.executable, "-B", SCRIPT, *map(str, paths)],
                                    cwd=ROOT, capture_output=True, text=True)
            after = [(p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).digest()) for p in paths]
            self.assertEqual(before, after)
            self.assertEqual(result.stderr, "")
            self.assertNotIn("secret", result.stdout)
            return result

    def check(self, patch, expected, base=b"alpha\nbeta\ngamma\n", code=None):
        result = self.invoke(patch.encode() if isinstance(patch, str) else patch, base)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if code:
            self.assertIn(code, result.stdout)
        return result.stdout

    def test_exact_replacement(self):
        out = self.check("--- private/path\n+++ https://secret.invalid/name\n@@ -1,3 +1,3 @@ label\n alpha\n-beta\n+delta\n gamma\n", 0, code="CLEAN")
        self.assertNotIn("alpha", out)
        self.assertNotIn("private", out)
        self.assertNotIn("delta", out)

    def test_no_fuzzy_search(self):
        self.check("--- a\n+++ b\n@@ -1 +1 @@\n-beta\n+z\n", 1, code="MISMATCH")

    def test_context_mismatch(self):
        self.check("--- a\n+++ b\n@@ -2 +2 @@\n gamma\n", 1)

    def test_insert_start_empty_range(self):
        self.check("--- a\n+++ b\n@@ -0,0 +1 @@\n+z\n", 0)

    def test_insert_middle(self):
        self.check("--- a\n+++ b\n@@ -2,0 +3 @@\n+z\n", 0)

    def test_insert_end(self):
        self.check("--- a\n+++ b\n@@ -3,0 +4 @@\n+z\n", 0)

    def test_empty_base_insertion(self):
        self.check("--- a\n+++ b\n@@ -0,0 +1 @@\n+z\n", 0, b"")

    def test_delete_first(self):
        self.check("--- a\n+++ b\n@@ -1 +0,0 @@\n-alpha\n", 0)

    def test_delete_middle(self):
        self.check("--- a\n+++ b\n@@ -2 +1,0 @@\n-beta\n", 0)

    def test_multiple_hunks_delta(self):
        self.check("--- a\n+++ b\n@@ -1 +1,2 @@\n alpha\n+x\n@@ -3 +4 @@\n-gamma\n+z\n", 0)

    def test_crlf_and_final_newline_normalized(self):
        self.check(b"--- a\r\n+++ b\r\n@@ -1 +1 @@\r\n alpha", 0, b"alpha")

    def test_empty_line_context(self):
        self.check("--- a\n+++ b\n@@ -1 +1 @@\n \n", 0, b"\n")

    def test_malformed_cases(self):
        cases = [
            "", "--- a\n+++ b\n", "+++ b\n--- a\n@@ -1 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@ -0 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@ -1 +0 @@\n alpha\n",
            "--- a\n+++ b\n@@ -1,0 +0,0 @@\n",
            "--- a\n+++ b\n@@ -1,2 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@ -1 +1 @@\n alpha\n extra\n",
            "--- a\n+++ b\n@@ -2 +2 @@\n beta\n@@ -1 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@ -1,2 +1,2 @@\n alpha\n beta\n@@ -2 +2 @@\n beta\n",
            "--- a\n+++ b\n@@ -1 +2 @@\n alpha\n",
            "--- a\n+++ b\n@@ -1 +1,2 @@\n alpha\n+x\n@@ -3 +3 @@\n gamma\n",
            "--- a\n+++ b\n@@ -999999999999999999999999999999 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@ -4,0 +5 @@\n+x\n",
            "--- a\n+++ b\n@@ -1,0 +2 @@\n+x\n@@ -1,0 +3 @@\n+y\n",
        ]
        for patch in cases:
            with self.subTest(patch=patch):
                self.check(patch, 2)

    def test_unsupported_cases(self):
        cases = [
            "diff --git a/a b/a\n--- a\n+++ b\n@@ -1 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@ -1 +1 @@\n alpha\n--- c\n+++ d\n@@ -1 +1 @@\n alpha\n",
            "--- a\n+++ b\n@@@ -1 -1 +1 @@@\n alpha\n",
            "--- a\n+++ b\n@@ -1 +1 @@\n alpha\n\\ No newline at end of file\n",
            "--- a\n+++ b\nindex abc..def 100644\n",
            "GIT binary patch\n", "rename from a\nrename to b\n",
        ]
        for patch in cases:
            with self.subTest(patch=patch):
                self.check(patch, 2)

    def test_encoding_and_line_ending_rejection(self):
        for patch, base in [(b"\xef\xbb\xbf--- a\n+++ b\n", b"a"),
                            (b"\xff", b"a"), (b"--- a\n+++ b\n", b"\xff"),
                            (b"--- a\r+++ b\r", b"a")]:
            with self.subTest(patch=patch):
                self.check(patch, 2, base)

    def test_byte_caps(self):
        self.check(b"x" * (2 * 1024 * 1024 + 1), 2)
        self.check("--- a\n+++ b\n@@ -1 +1 @@\n alpha\n", 2, b"x" * (2 * 1024 * 1024 + 1))

    def test_line_caps(self):
        self.check("--- a\n+++ b\n@@ -1 +1 @@\n alpha\n", 2, b"a\n" * 20001)
        self.check(b"x\n" * 20001, 2)

    def test_hunk_cap(self):
        patch = "--- a\n+++ b\n" + "".join(f"@@ -{i} +{i} @@\n a\n" for i in range(1, 1002))
        self.check(patch, 2, b"a\n" * 1001)

    def test_inclusive_resource_boundaries(self):
        self.check("--- a\n+++ b\n@@ -1 +1 @@\n a\n", 0,
                   b"a\n" + b"x" * (2 * 1024 * 1024 - 2))
        self.check("--- a\n+++ b\n@@ -1 +1 @@\n a\n", 0, b"a\n" * 20000)
        patch = "--- a\n+++ b\n" + "".join(f"@@ -{i} +{i} @@\n a\n" for i in range(1, 1001))
        self.check(patch, 0, b"a\n" * 1000)

    def test_opaque_header_text_never_opens_paths(self):
        self.check("--- //secret/missing\n+++ C:\\secret\\missing\n@@ -1 +1 @@\n alpha\n", 0)

    def test_path_rejections_and_neutral_errors(self):
        paths = ["https://secret.invalid/a", "//secret/share", "\\\\secret\\share", "a/b\\secret",
                 "\\\\?\\C:\\secret", "NUL", "COM1.txt", "C:secret", "secret:stream", "."]
        for path in paths:
            with self.subTest(path=path):
                result = subprocess.run([sys.executable, "-B", SCRIPT, path, path], cwd=ROOT,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, "")
                self.assertNotIn("secret", result.stdout)

    def test_console_device_names_rejected_lexically(self):
        import patch_context_check as tool
        for name in ["CONIN$", "CONOUT$", "CLOCK$", "dir/CONIN$.txt"]:
            with self.subTest(name=name):
                with self.assertRaises(tool.Invalid):
                    tool.local_path(name)

    def test_symlink_rejected_if_available(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            link = Path(directory) / "link"
            source.write_bytes(b"alpha\n")
            try:
                link.symlink_to(source)
            except OSError:
                self.skipTest("symlink creation unavailable")
            result = subprocess.run([sys.executable, "-B", SCRIPT, str(link), str(source)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, "")

    def test_cli_help_and_usage(self):
        for args, expected in [([], 2), (["--help"], 0), (["-h"], 0), (["--secret"], 2)]:
            result = subprocess.run([sys.executable, "-B", SCRIPT, *args], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, expected)
            self.assertEqual(result.stderr, "")
            self.assertNotIn("--secret", result.stdout)

    def test_real_closed_stdout_including_help(self):
        for args, expected in [(["--help"], 0), ([], 2),
                               (["fixtures/clean.patch", "fixtures/base.txt"], 0)]:
            process = subprocess.Popen([sys.executable, "-B", SCRIPT, *args], cwd=ROOT,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.stdout.close()
            stderr = process.stderr.read()
            result = process.wait(timeout=10)
            process.stderr.close()
            self.assertEqual(result, expected)
            self.assertNotEqual(result, 120)
            self.assertEqual(stderr, b"")


if __name__ == "__main__":
    unittest.main()
