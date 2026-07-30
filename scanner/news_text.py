"""Normalize user-facing news text without altering stored source evidence."""

from __future__ import annotations

import re


# Keycap emojis include an ordinary digit followed by emoji selectors, so they
# must be removed before the broader Unicode-symbol pass.
_KEYCAP_EMOJI_RE = re.compile(r"[#*0-9]\ufe0f?\u20e3")
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U0001FC00-\U0001FFFF"
    "\U000E0020-\U000E007F"
    "\u2600-\u27BF"
    "\u2B00-\u2BFF"
    "\uFE0E-\uFE0F"
    "\u200D"
    "]"
)
_ASCII_EMOTICON_RE = re.compile(
    r"(?<!\w)(?:"
    r"[:;=8][\-^']?[)(/\\DPpOo]"
    r"|[)(][\-^']?[:;=8]"
    r"|[xX][dD]"
    r"|<3"
    r")(?!\w)"
)
_REPEATED_PAREN_SMILE_RE = re.compile(
    r"(?<=\w)[)(]{2,}(?=\s|$|[.!?,;:])"
)


def clean_news_text(value: str) -> str:
    """Remove emoji and typed smileys while preserving meaningful news text."""
    text = value or ""
    text = _KEYCAP_EMOJI_RE.sub(" ", text)
    text = _EMOJI_RE.sub(" ", text)
    text = _ASCII_EMOTICON_RE.sub(" ", text)
    text = _REPEATED_PAREN_SMILE_RE.sub("", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
