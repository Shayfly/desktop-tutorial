"""Time ranges on a right-to-left page are isolated with <bdi dir="ltr"> (Michael 2026-11-15: "שעות -- תיקון עם bdi").

The butcher page (bld_83529c13, v_8d8ed793) wrote "07:00–19:00" in a dir="rtl" page and the browser showed it as
"19:00–07:00": the Unicode bidi algorithm lays the two LTR numbers and the neutral dash out right-to-left, so the
customer reads the closing hour first -- opening hours that look like night hours. The text was right; the order the
eye sees was not. <bdi dir="ltr"> isolates the range and shows it as written.

Two places use this:
  * page_locale.ensure_rtl wraps the ranges in every .html page of an RTL request (by construction);
  * skills_runtime._time_ranges_isolated judges the SERVED page and blocks an unwrapped range, so a page built inside
    Python or JS (the butcher's was a string in app.py) is repaired by the loop.
Only visible text counts: <script>/<style> content (JSON-LD opening hours) and attribute values are never touched.
"""
from __future__ import annotations

import re

# 07:00–19:00, 7:00-14:00, 07:00 — 19:00 (hyphen, en dash, em dash, minus sign)
# not preceded by a digit, ':' or the 'T' of an ISO timestamp (2026-11-15T10:00-02:00 is a time and its UTC offset)
TIME_RANGE = re.compile(r'(?<![\d:T])\d{1,2}:\d{2}\s*[-–—−]\s*\d{1,2}:\d{2}(?![\d:])')
_HIDDEN = re.compile(r'<(script|style|template)\b[^>]*>.*?</\1\s*>|<!--.*?-->', re.S | re.I)
_OPEN_TAG = re.compile(r'<([a-zA-Z][\w-]*)\b([^>]*)>')


def _masked(html: str) -> str:
    """The page with script/style/template/comment content blanked out, offsets kept."""
    return _HIDDEN.sub(lambda m: ' ' * len(m.group(0)), html)


def _isolated(html: str, start: int) -> bool:
    """The range at `start` is inside <bdi>...</bdi>, or its nearest enclosing element sets dir="ltr"."""
    before = html[:start].lower()
    if before.rfind('<bdi') > before.rfind('</bdi'):
        return True
    tags = list(_OPEN_TAG.finditer(html[:start]))
    if not tags or '</' in html[tags[-1].end():start]:          # the last opened element was closed before the range
        return False
    return re.search(r'\bdir\s*=\s*["\']?ltr', tags[-1].group(2), re.I) is not None


def _in_tag(html: str, start: int) -> bool:
    """`start` is inside a tag (an attribute value), not in text."""
    return html.rfind('<', 0, start) > html.rfind('>', 0, start)


def unwrapped_ranges(html: str) -> list[tuple[int, str]]:
    masked = _masked(html)
    return [(m.start(), m.group(0)) for m in TIME_RANGE.finditer(masked)
            if not _in_tag(masked, m.start()) and not _isolated(masked, m.start())]


def wrap_ranges(html: str) -> str:
    out, last = [], 0
    for start, text in unwrapped_ranges(html):
        out.append(html[last:start])
        out.append(f'<bdi dir="ltr">{text}</bdi>')
        last = start + len(text)
    out.append(html[last:])
    return ''.join(out)
