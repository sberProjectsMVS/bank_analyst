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
_RUSSIAN_MONTH = (
    r"(?:январ[ья]|феврал[ья]|марта?|апрел[ья]|ма[йя]|июн[ья]|"
    r"июл[ья]|август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])"
)
_EFFECTIVE_DATE = (
    rf"(?:\d{{1,2}}[./-]\d{{1,2}}(?:[./-]\d{{2,4}})?|"
    rf"\d{{1,2}}\s+{_RUSSIAN_MONTH}(?:\s+\d{{4}})?)"
    rf"(?:\s*(?:г\.?|года))?"
)


def strip_effective_date_emphasis(value: str) -> str:
    """Remove effective-date framing while preserving the dated record metadata."""
    text = value
    text = re.sub(
        rf"(?:обновл[её]нн\w+\s+программа|новые\s+правила|условия)\s+"
        rf"(?:начн\w+\s+действовать|вступ\w+\s+в\s+силу|действуют?)\s+"
        rf"с\s+{_EFFECTIVE_DATE}\s*[.!]?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"(?<!\w)с\s+{_EFFECTIVE_DATE}(?!\w)",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    # When a generic dated heading precedes a numbered list, start with the
    # first concrete change instead of repeating that something changed.
    text = re.sub(
        r"^(?:изменения|обновления)\s+[^.!?]{0,220}?(?=\s+\d+[.)]\s+)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # The date remains in dateSort/dateLabel. A generic first sentence adds no
    # useful information when the following sentence contains the substance.
    text = re.sub(
        r"^(?:изменения|обновления)\s+(?:в|по|условий)\b[^.!?]{0,220}[.!?]+\s*",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^\s*[—–-]\s*", "", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_news_text(value: str) -> str:
    """Remove emoji and typed smileys while preserving meaningful news text."""
    text = value or ""
    text = _KEYCAP_EMOJI_RE.sub(" ", text)
    text = _EMOJI_RE.sub(" ", text)
    text = _ASCII_EMOTICON_RE.sub(" ", text)
    text = _REPEATED_PAREN_SMILE_RE.sub("", text)
    text = strip_effective_date_emphasis(text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .")
