import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publisher


class PublisherSafetyTests(unittest.TestCase):
    def test_prepare_repository_rejects_detached_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir()
            with patch("publisher._git_output", return_value=""), patch(
                "publisher._run_git"
            ) as run_git:
                self.assertFalse(publisher._prepare_repository(repo))
                run_git.assert_not_called()

    def test_prepare_repository_pulls_main_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir()
            with patch("publisher._git_output", return_value="main"), patch(
                "publisher._run_git", return_value=True
            ) as run_git:
                self.assertTrue(publisher._prepare_repository(repo))
                run_git.assert_called_once_with(
                    ["pull", "--rebase", "origin", "main"], repo,
                )

    def test_verify_remote_head_requires_exact_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with patch(
                "publisher._git_output",
                side_effect=["abc123", "abc123\trefs/heads/main"],
            ):
                self.assertTrue(publisher._verify_remote_head(repo))


if __name__ == "__main__":
    unittest.main()
