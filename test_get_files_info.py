import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from functions.get_files_info import get_files_info


class ListFilesTests(unittest.TestCase):
    def test_listing_and_broken_link(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "ok").write_text("hello")
            (Path(root) / "broken").symlink_to("nonexistent")
            result = get_files_info(root)
            self.assertIn("'ok': file_size=5", result)
            self.assertIn("is_symlink=True", result)
            self.assertFalse(result.startswith("Error:"))

    def test_bounds_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            (Path(root) / "link").symlink_to(outside)
            (Path(root) / "a").touch()
            (Path(root) / "b").touch()
            for path in ("..", outside, "link"):
                self.assertTrue(get_files_info(root, path).startswith("Error:"))
            with patch("config.MAX_DIRECTORY_ENTRIES", 1):
                self.assertIn("truncated", get_files_info(root))


if __name__ == "__main__":
    unittest.main()
