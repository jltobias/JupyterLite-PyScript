"""Focused guards for build cleanup and URL-prefix validation; no build runs."""
from pathlib import Path
import unittest
from unittest.mock import patch

import build


class BuildGuards(unittest.TestCase):
    def test_in_repo_symlink_or_junction_target_is_not_deleted(self):
        lexical = build.ROOT / "tmp/generated-link"
        # Simulate both symlinks and Windows junctions without elevated rights.
        with patch.object(Path, "resolve", return_value=build.ROOT / "content"), patch.object(build.shutil, "rmtree") as remove:
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                build.clean_generated(lexical)
            remove.assert_not_called()

    def test_invalid_prefixes_fail_before_cleanup(self):
        for prefix in ["//other-host", "/repo?query=1", "/repo#fragment", "/repo\\child",
                       "/repo name", "/repo\tname", "repo", "https://example.com", "/../repo"]:
            with self.subTest(prefix=prefix), patch.object(build, "clean_generated") as clean:
                with self.assertRaises(ValueError):
                    build.build(prefix)
                clean.assert_not_called()

    def test_root_and_repository_prefixes(self):
        for prefix, expected in [("", ""), ("/", ""), ("/JupyterLite-PyScript/", "/JupyterLite-PyScript"), ("/nested/repo", "/nested/repo")]:
            self.assertEqual(build.validate_base_url(prefix), expected)


if __name__ == "__main__":
    unittest.main()
