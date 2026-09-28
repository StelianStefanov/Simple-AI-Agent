import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from functions.run_python_file import run_python_file


class ExecutionTests(unittest.TestCase):
    def test_missing_sandbox_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "script.py").write_text("raise RuntimeError('must not execute')")
            with patch("shutil.which", return_value=None):
                self.assertIn("requires Linux", run_python_file(root, "script.py"))

    def test_bad_paths_and_arguments(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "script.py").write_text("print('outside')")
            (Path(root) / "link.py").symlink_to(Path(outside) / "script.py")
            for path in ("../script.py", "link.py", "missing.py", "file.txt"):
                self.assertTrue(run_python_file(root, path).startswith("Error:"))
            self.assertTrue(run_python_file(root, "script.py", "abc").startswith("Error:"))


@unittest.skipUnless(sys.platform == "linux", "Linux execution sandbox")
class SandboxIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "probe.py").write_text("print('sandbox-ready')")
            result = run_python_file(root, "probe.py")
            if "STDOUT:\nsandbox-ready" not in result:
                if os.environ.get("AI_AGENT_REQUIRE_SANDBOX") == "1":
                    raise AssertionError(result)
                raise unittest.SkipTest(f"Sandbox unavailable: {result[:300]}")

    def execute(self, source, args=None):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "script.py").write_text(source)
            return run_python_file(root, "script.py", args)

    def test_host_files_environment_network_and_writes_are_isolated(self):
        with tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / "secret"
            secret.write_text("private")
            source = f'''import os, socket
from pathlib import Path
assert "OPENROUTER_API_KEY" not in os.environ
assert not Path({str(secret)!r}).exists()
assert socket.if_nameindex() == [(1, 'lo')]
try:
    Path('/workspace/changed').write_text('bad')
except OSError:
    pass
else:
    raise AssertionError('workspace was writable')
Path('/tmp/temporary').write_text('allowed')
print('isolated')
'''
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-secret-for-test"}):
                result = self.execute(source)
            self.assertIn("STDOUT:\nisolated", result)

    def test_arguments_unicode_and_stderr(self):
        result = self.execute("import sys; print(sys.argv[1]); print('error detail', file=sys.stderr)", ["hello world"])
        self.assertIn("hello world", result)
        self.assertIn("STDERR:\nerror detail", result)
        self.assertIn("Process exited with code 0", result)

    def test_output_limit(self):
        with patch("config.MAX_TOOL_OUTPUT_BYTES", 1000):
            result = self.execute("while True: print('x' * 1000, flush=True)")
        self.assertIn("output limit exceeded", result)
        self.assertLess(len(result), 1200)

    def test_timeout_even_after_pipes_are_closed(self):
        with patch("config.EXECUTION_TIMEOUT_SECONDS", 0.5):
            result = self.execute("import os, time; os.close(1); os.close(2); time.sleep(60)")
        self.assertIn("timed out", result)

    def test_descendants_are_terminated(self):
        with patch("config.EXECUTION_TIMEOUT_SECONDS", 0.5):
            result = self.execute("import os, time; os.fork(); time.sleep(60)")
        self.assertIn("timed out", result)


if __name__ == "__main__":
    unittest.main()
