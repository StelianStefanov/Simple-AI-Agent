import tempfile
import unittest
from pathlib import Path

from config import MAX_CHARS
from functions.get_file_content import get_file_content


class ReadFileTests(unittest.TestCase):
    def test_contents_and_truncation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "text.txt"
            path.write_text("x" * (MAX_CHARS + 1))
            result = get_file_content(root, "text.txt")
            self.assertTrue(result.startswith("x" * MAX_CHARS))
            self.assertIn("truncated", result)
            path.write_text("x" * MAX_CHARS)
            self.assertEqual(get_file_content(root, "text.txt"), "x" * MAX_CHARS)

    def test_unsafe_paths_and_file_types(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "secret").write_text("private")
            (Path(root) / "link").symlink_to(Path(outside) / "secret")
            (Path(root) / "directory_link").symlink_to(outside)
            (Path(root) / "binary").write_bytes(b"\xff\xfe")
            for path in ("../secret", str(Path(outside) / "secret"), "link", "directory_link/secret", "binary", "missing", "."):
                with self.subTest(path=path):
                    self.assertTrue(get_file_content(root, path).startswith("Error:"))


if __name__ == "__main__":
    unittest.main()
