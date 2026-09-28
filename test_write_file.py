import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from functions.write_file_content import write_file


class WriteFileTests(unittest.TestCase):
    def test_create_and_replace(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIn("Successfully", write_file(root, "nested/file", "hello"))
            self.assertIn("Successfully", write_file(root, "nested/file", "world"))
            self.assertEqual((Path(root) / "nested/file").read_text(), "world")

    def test_symlinks_and_traversal_cannot_overwrite_outside(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "secret"
            target.write_text("original")
            (Path(root) / "link").symlink_to(target)
            (Path(root) / "dirlink").symlink_to(outside)
            for path in ("link", "dirlink/secret", str(target), "../secret"):
                self.assertTrue(write_file(root, path, "changed").startswith("Error:"))
                self.assertEqual(target.read_text(), "original")

    def test_failed_write_preserves_original_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "file"
            target.write_text("original")
            with patch("os.replace", side_effect=OSError("simulated disk failure")):
                self.assertTrue(write_file(root, "file", "new").startswith("Error:"))
            self.assertEqual(target.read_text(), "original")
            self.assertEqual([p.name for p in Path(root).iterdir()], ["file"])
            for content in (None, "\ud800"):
                self.assertTrue(write_file(root, "file", content).startswith("Error:"))
                self.assertEqual(target.read_text(), "original")
            with patch("config.MAX_WRITE_CHARS", 2):
                self.assertTrue(write_file(root, "file", "large").startswith("Error:"))
                self.assertEqual(target.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
