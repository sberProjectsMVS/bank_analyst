import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
import publisher


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


class PublisherSafetyTests(unittest.TestCase):
    def test_publication_includes_static_site_marker(self):
        self.assertIn(".nojekyll", publisher._published_git_paths())

    def test_news_workflow_rebuilds_feed_before_public_landing(self):
        calls = []

        with (
            patch.object(
                main,
                "build_premium_changes_only",
                side_effect=lambda: calls.append("feed") or {"changes": 84},
            ),
            patch.object(
                main,
                "build_sber_vs_only",
                side_effect=lambda: calls.append("public") or {"published": True},
            ),
        ):
            result = main.build_news_landings_and_publish()

        self.assertEqual(calls, ["feed", "public"])
        self.assertTrue(result["sber_vs"]["published"])

    def test_public_verification_requires_generated_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "index.html"
            source.write_bytes(b"new landing")
            responses = iter([
                FakeResponse(b"old landing"),
                FakeResponse(b"new landing"),
            ])
            sleeps = []
            urls = []

            def requester(url, **_kwargs):
                urls.append(url)
                return next(responses)

            self.assertTrue(publisher._verify_published_content(
                source,
                requester=requester,
                sleeper=sleeps.append,
                attempts=2,
                delay_seconds=0,
            ))
            self.assertEqual(sleeps, [0])
            self.assertEqual(len(set(urls)), 2)

    def test_public_verification_rejects_stale_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "index.html"
            source.write_bytes(b"new landing")

            self.assertFalse(publisher._verify_published_content(
                source,
                requester=lambda *_args, **_kwargs: FakeResponse(b"old landing"),
                sleeper=lambda _delay: None,
                attempts=2,
                delay_seconds=0,
            ))

    def test_public_verification_stops_at_elapsed_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "index.html"
            source.write_bytes(b"new landing")
            ticks = iter([0.0, 1.0])
            requests = []

            self.assertFalse(publisher._verify_published_content(
                source,
                requester=lambda *_args, **_kwargs: (
                    requests.append(True) or FakeResponse(b"old landing")
                ),
                sleeper=lambda _delay: None,
                attempts=1000,
                deadline_seconds=0.5,
                clock=lambda: next(ticks),
            ))
            self.assertEqual(len(requests), 1)

    def test_public_verification_accepts_matching_build_marker(self):
        marker = b'<meta name="bank-analyst-build" content="build-42">'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "index.html"
            source.write_bytes(b"<head>" + marker + b"</head>" + b"x" * 1000000)

            self.assertTrue(publisher._verify_published_content(
                source,
                requester=lambda *_args, **_kwargs: FakeResponse(marker),
                sleeper=lambda _delay: None,
                attempts=1,
            ))

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
