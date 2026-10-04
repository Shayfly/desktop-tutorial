"""Token-aware intent term matching for product planning.

Naive substring checks produced false targets ("appointments" -> app ->
Android, "community" -> unity -> 3D game, "delivery" -> live -> realtime).
Latin-script terms here match whole words only (with an optional plural
"s"/"es"); multi-word terms tolerate any whitespace between words.
Hebrew and other non-Latin terms keep substring matching because Hebrew
attaches prefixes (ה, ב, ל, ו, ש) directly to the word.
"""
from __future__ import annotations

from functools import lru_cache
import re

__all__ = ["has_term", "mobile_intent", "ai_agent_intent"]


def _is_latin(term: str) -> bool:
    return all(ord(ch) < 128 for ch in term)


@lru_cache(maxsize=512)
def _pattern(term: str) -> re.Pattern[str]:
    words = [re.escape(w) for w in term.lower().split()]
    body = r"[\s\-]+".join(words)
    return re.compile(rf"(?<![a-z0-9]){body}(?:s|es)?(?![a-z0-9])")


def has_term(text: str, *terms: str) -> bool:
    low = " ".join(str(text).lower().split())
    for term in terms:
        if not term:
            continue
        if _is_latin(term):
            if _pattern(term).search(low):
                return True
        elif term.lower() in low:
            return True
    return False


_WEB_APP = re.compile(r"(?<![a-z0-9])web[\s\-]*apps?(?![a-z0-9])")
_APP_WORD = re.compile(r"(?<![a-z0-9])apps?(?![a-z0-9])")


def mobile_intent(text: str) -> bool:
    """True only for an explicit mobile request.

    * android / ios / iphone / ipad / mobile / Hebrew "אפליקציה" / "אנדרואיד"
    * the standalone word "app"/"apps" unless it is a "web app"
    * "application" alone is not mobile; "mobile/android/ios application" is,
      via the qualifier itself.
    """
    low = " ".join(str(text).lower().split())
    if has_term(low, "android", "ios", "iphone", "ipad", "mobile", "אפליקציה", "אנדרואיד", "מובייל"):
        return True
    without_web_apps = _WEB_APP.sub(" ", low)
    return bool(_APP_WORD.search(without_web_apps))


# Human roles that use the word "agent" ("travel-agent users", "real estate agents").
_HUMAN_AGENT = re.compile(
    r"(?<![a-z0-9])(travel|real[\s\-]+estate|estate|insurance|sales|support|service|booking|ticket(?:ing)?|"
    r"leasing|rental|shipping|customs|border|field|call[\s\-]+center|helpdesk|help[\s\-]+desk)[\s\-]+agents?(?![a-z0-9])")


def ai_agent_intent(text: str) -> bool:
    """AI-agent product intent, not a human job title that contains 'agent'."""
    low = " ".join(str(text).lower().split())
    if has_term(low, "ai agent", "ai assistant", "assistant", "agentic", "autonomous agent", "chatbot",
                "סוכן ai", "עוזר ai"):
        return True
    return has_term(_HUMAN_AGENT.sub(" ", low), "agent")
