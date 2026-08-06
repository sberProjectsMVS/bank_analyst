# -*- coding: utf-8 -*-
"""Project-level settings for generated site publication."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

# Sibling Git repository used by GitHub Pages.
SITE_REPOSITORY = BASE_DIR / "../bank_cite"

# Current generated landing file. Change this if the generator output is renamed.
GENERATED_HTML = "sber_vs_banks.html"

# Structured comparison data consumed by the Sber VS landing.
COMPARISON_JSON = "comparison_data.json"

# GitHub Pages entrypoint in the publication repository.
PUBLISHED_HTML = "index.html"
PUBLISH_BRANCH = "main"
PUBLISHED_URL = "https://sberprojectsmvs.github.io/bank_cite/"

# Publish the generated HTML as a plain static file.  This avoids an unnecessary
# Jekyll build between a successful push and the GitHub Pages deployment.
PUBLISH_EXTRA_ASSETS: tuple[tuple[Path, Path], ...] = (
    (OUTPUT_DIR / ".nojekyll", Path(".nojekyll")),
)
