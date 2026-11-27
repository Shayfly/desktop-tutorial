from __future__ import annotations

import logging

import re

from collections import OrderedDict
from collections.abc import Mapping

from .a4 import ITEM_PURPOSE
from .capabilities import CapabilityPlan, CapabilityRequirement
from .capability_registry import CapabilityRegistry
from .intent_terms import ai_agent_intent, has_term
from .media_pipeline import AssetKind, is_default_hero, pictures_declined


# Asset-generation capabilities: activated only when the creative plan requests
# them (decision 2026-10-07 #28).
ASSET_CAPABILITY_KEYS = {
    AssetKind.ICON: "media.image.generate",
    AssetKind.IMAGE: "media.image.generate",
    AssetKind.AUDIO: "media.audio.sfx",
    AssetKind.MUSIC: "media.audio.music",
    AssetKind.VOICE: "media.audio.tts",
    AssetKind.VIDEO: "media.video.generate",
    AssetKind.MODEL3D: "media.3d.mesh.generate",
    AssetKind.TEXTURE: "media.3d.texture",
}


IMAGE_KEY = "media.image.generate"
# Plan notes for an image nothing describes (CapabilityPlan.notes round-trip in the stored contract, so the reason a
# picture is missing stays on the contract). Production 2026-11-23: three owner builds failed after paying for a picture
# drawn from a generic sentence, because only one trigger of an image requirement recorded what it shows.
IMAGE_SUBJECT_UNRESOLVED = "image-subject-unresolved"    # a required image: left out, and the contract asks the customer
IMAGE_NOT_PLANNED = "image-not-planned-no-subject"        # an optional image: left out, never generated
MAX_SUBJECT_CHARS = 300                                   # the alt's own bound (generated_images.alt_text)
IMAGE_ITEMS_UNREAD = "image-items-unread"   # a picture of each item is asked and the brief lists none: the contract asks
# Release review of 550320c (S1): nothing wrote the customer's answer to those two questions where this planner reads,
# so each was asked again on every turn, bounded only by the conversation's cost cap. The supervisor now records the
# answer (discovery.record_picture_answer) and requirements_text writes it into the approved brief as one of these lines,
# which this planner reads. After a question was asked ASK_PICTURE_AT_MOST times without an answer it can read, the
# supervisor records the stated default instead, the plan carries the *_DEFAULTED note and the summary says it.
ASK_PICTURE_AT_MOST = 2
PICTURE_ITEMS_ANSWER = "Picture items (the customer's answer): "
PICTURE_SUBJECT_ANSWER = "Picture subject (the customer's answer): "
PICTURE_ITEMS_DEFAULT = ("Picture items: NOT GIVEN after two questions -- no picture is made per item; the items are shown "
                         "as text.")
PICTURE_SUBJECT_DEFAULT = ("Picture subject: NOT GIVEN after two questions -- the picture nothing describes is left out; "
                           "never drawn from a generic sentence.")
IMAGE_ITEMS_UPLOADED = "image-items-uploaded-photos"      # S3: own photos among the items stand for the first ones
# a photo the approved brief places (discovery.requirements_text's "Uploaded image N ..." line)
_PLACED_UPLOAD = re.compile(r'^Uploaded image (\d{1,2}) attachment: \S+; sha256=[a-f0-9]{64}; '
                            r'src="148ai-asset://upload/\1"; placement: (hero|story|products|gallery);')
ITEM_PHOTO_PLACES = ('products', 'gallery')                  # where the customer's own photo stands for an item
IMAGE_ITEMS_DEFAULTED = "image-items-defaulted-text-only"        # stated in the summary (supervisor) and the contract
IMAGE_SUBJECT_DEFAULTED = "image-subject-defaulted-left-out"     # stated in the summary (supervisor) and the contract
MAX_ANSWER_ITEM_WORDS = 4          # a longer "item" is a sentence ("תעשו מה שנראה לכם"), not an item: not read as one
# words of a sentence addressed to us, never of an item: "תעשו מה שנראה לכם יפה ומתאים" was read as two items
_HANDED_BACK = re.compile(r"(?<![\wא-ת])(?:תעשו|תעשה|תבחרו|תבחר|תחליטו|תחליט|תמליצו|לכם|לך|אתם|אתה|בבקשה|נראה|"
                          r"יודע|יודעת|משנה)(?![\wא-ת])|\b(?:you|your|please|whatever|decide|choose|know)\b|"
                          r"(?<![\w" + "ء-ي" + r"])(?:اختاروا|اختر|قرروا|قرر|أنتم|انتم|لكم|من\s+فضلك|أعرف|اعرف)"
                          r"(?![\w" + "ء-ي" + r"])", re.I)
_APPROVED_BRIEF = re.compile(r"(?m)^--- Approved project brief \(binding; fingerprint [a-f0-9]{16}\) ---$")
_BUSINESS_LINE = "Main action: "
_CONTENT_LINE = "Initial content: "
# the last two items of a list: "קופסאות אחסון ומצתים", "boxes and lighters"
_LAST_AND = re.compile(r"\s+(?:ו-?(?=[א-ת])|and\s+|و\s?(?=[ء-ي]))", re.I)
_NOT_AN_ITEM = {"עוד", "וכו", "וכו׳", "וכו'", "וכדומה", "more", "etc", "etc.", "وغيرها", "إلخ", "الخ"}
_SEGMENTS = re.compile(r"[;|؛]")        # the brief's content segments (and the " | " _record_content joins with)
_ITEM_COMMAS = re.compile(r"[,،]")      # Hebrew/English and Arabic commas
# Labels of an items list besides the item words the picture_per_item reader knows (one_page.ITEMS_HE / ITEMS_EN), in
# Hebrew, English and Arabic (release review S1: "תפריט:", "Menu:", "מוצרי החנות:", "שירותי המספרה:" were missed).
_LABELS_HE_EXTRA = ("תפריט", "תפריטים", "מבחר", "קולקציה", "קולקציות")
_LABELS_EN_EXTRA = r"menu|menus|selection|range|line-?up|list\s+of\s+\w+"
_LABELS_AR = ("منتجات", "خدمات", "أطباق", "اطباق", "أصناف", "اصناف", "فئات", "أقسام", "اقسام", "قائمة", "منيو",
              "وجبات", "مأكولات", "عروض", "باقات")
_AR = "ء-ي"


def _semantic_image_words(semantic_decisions) -> str | None:
    """The customer's own words quoted by the approved semantic decision that requires an image: its evidence, checked
    against the customer's message when it was recorded (semantic_capabilities.validate_decisions)."""
    for decision in semantic_decisions or ():
        if isinstance(decision, Mapping) and decision.get("key") == IMAGE_KEY and decision.get("decision") == "required":
            words = " ".join(str(decision.get("evidence") or "").split())
            if words:
                return words[:MAX_SUBJECT_CHARS]
    return None


def _brief_business_line(full_prompt: str) -> str | None:
    """The approved brief's business line: its "Main action:" line (discovery.requirements_text -- the customer's answer
    to "what is the one thing it must do best", or the first business sentence of their request when they left it to
    148AI). Read only from the LAST server-written brief block, the rule semantic_capabilities.read_approved follows, so
    a customer's text that imitates a brief is never read."""
    text = full_prompt or ""
    markers = list(_APPROVED_BRIEF.finditer(text))
    if not markers:
        return None
    for line in text[markers[-1].end():].splitlines():
        if line.startswith(_BUSINESS_LINE):
            words = " ".join(line[len(_BUSINESS_LINE):].split())
            return words[:MAX_SUBJECT_CHARS] or None
    return None


def _picture_per_item(full_prompt: str) -> bool:
    """Does the customer ask for a picture of EACH item? one_page.beyond reads it in the customer's own words (the
    request and the brief lines that quote them, facts.customer_text): the same reader the content route uses to send
    such a request to the path that writes the site's code (law 9: one reader)."""
    from .site_content.facts import customer_text
    from .site_content.one_page import beyond
    return any(kind == "picture_per_item" for kind, _ in beyond(customer_text(full_prompt)))


def item_pictures_wanted(full_prompt: str) -> bool:
    """A picture of each listed item: when the customer asks for it in their words (_picture_per_item), and -- the
    owner, 2026-11-27 (inbox/005, decision 2) -- by default on a content site whose approved brief lists its items
    (_brief_items: at least two), unless the customer says no pictures (media_pipeline.pictures_declined). Nothing is
    planned for a brief that lists no item: the default never asks a question."""
    if _picture_per_item(full_prompt):
        return True
    from .media_pipeline import _CONTENT_SITE
    return (_CONTENT_SITE in (full_prompt or "") and not pictures_declined(full_prompt) and bool(_brief_items(full_prompt)))


def _items_label() -> re.Pattern:
    """An items label, case- and spacing-tolerant: a Hebrew item word in its plural or construct form ("מוצרים",
    "מוצרי החנות", "שירותי המספרה") with up to three prefix letters, "תפריט"; an English plural item word or "menu"; an
    Arabic one with its article, conjunction or possessive ("القائمة", "منتجاتنا")."""
    from .site_content.one_page import ITEMS_HE, _ITEMS_EN_PLURAL     # the item words the picture_per_item reader knows
    he = set(ITEMS_HE) | set(_LABELS_HE_EXTRA) | {w[:-2] + "י" for w in ITEMS_HE if w.endswith("ים")}
    he_rx = (r"(?<![\wא-ת])[ובשלמהכ]{0,3}(?:" + "|".join(sorted(map(re.escape, he), key=len, reverse=True))
             + r")(?![\wא-ת])")
    en_rx = r"\b(?:" + _ITEMS_EN_PLURAL + "|" + _LABELS_EN_EXTRA + r")\b"
    ar_rx = (r"(?<![\w" + _AR + r"])(?:و|ف)?(?:ال)?(?:" + "|".join(sorted(_LABELS_AR, key=len, reverse=True))
             + r")(?:نا|ه|ها|كم)?(?![\w" + _AR + r"])")
    return re.compile(he_rx + "|" + en_rx + "|" + ar_rx, re.I)


def _split_items(listed: str) -> list[str]:
    """The items of one written list: commas separate them and "ו"/"and"/"و" joins the last two. Each item once, its
    whitespace collapsed, never a filler word ("וכו", "etc")."""
    parts = [" ".join(p.split()) for p in _ITEM_COMMAS.split(listed)]
    last = list(_LAST_AND.finditer(parts[-1]))
    if last:                                          # "a ו-b": the last element holds the last two items
        parts[-1:] = [parts[-1][:last[-1].start()], parts[-1][last[-1].end():]]
    items = []
    for part in parts:
        item = part.strip(" .")
        if item.lower().startswith("and "):
            item = item[4:].strip()
        if item and item.lower() not in _NOT_AN_ITEM and item not in items:
            items.append(item[:MAX_SUBJECT_CHARS])
    return items


def _approved_lines(full_prompt: str) -> list[str]:
    """The lines of the LAST server-written brief block ([] without one): a customer's text that imitates a brief is
    never read (the rule semantic_capabilities.read_approved follows)."""
    text = full_prompt or ""
    markers = list(_APPROVED_BRIEF.finditer(text))
    return text[markers[-1].end():].splitlines() if markers else []


# Review of 49d61d3 (B1): an unrelated reply was recorded as the picture answer -- "תשנו את הצבע לכחול" and "no idea"
# became items, "הטלפון שלנו 03-5559999" and "גם כתובת: הרצל 5, חיפה" too, and "Also add an opening hours section" became
# what the picture shows. A reply is the answer only when it reads as one (read_picture_answer); when in doubt it is not
# recorded and the question is asked once more, within ASK_PICTURE_AT_MOST.
# "I don't know / skip / you decide" (he, en, ar): the stated default, at once -- never an answer.
_DECLINE = re.compile(
    r"(?<![\wא-ת])(?:לא\s+(?:יודע|יודעת|יודעים|בטוח|בטוחה|משנה|צריך|חשוב)|אין\s+לי\s+(?:מושג|רעיון)|אין\s+מושג|"
    r"תחליטו|תחליט|תבחרו|תבחר|דלגו|תדלגו|דלג|מה\s+ש(?:נראה|תרצו|בא|מתאים)|בלי\s+תמונ\S*|"
    r"תעשו\s+מה)(?![\wא-ת])"
    r"|\b(?:no\s+idea|not\s+sure|i\s+don'?t\s+know|don'?t\s+know|dunno|idk|skip(?:\s+it)?|whatever|you\s+decide|"
    r"up\s+to\s+you|your\s+call|you\s+choose|no\s+pictures?)\b"
    r"|(?<![\wء-ي])(?:لا\s+أعرف|لا\s+اعرف|لست\s+متأكد\S*|تخط[ىي]|تجاوز|قرروا|اختاروا|لا\s+يهم|بدون\s+صور\S*)"
    r"(?![\wء-ي])", re.I)
_DECLINE_ALONE = re.compile(r"^\s*(?:no|none|nothing|nope|לא|אין|כלום|لا|لا\s+شيء)\s*[.!]*\s*$", re.I)
# A change to the request, not an answer: an imperative edit verb (he / en / ar).
_CHANGE = re.compile(
    r"(?<![\wא-ת])ו?(?:תשנ[וה]|שנו|תוסיפ[וי]|תוסיף|הוסיפו|תוריד[וי]|תוריד|הורידו|תחליפ[וי]|החליפו|תמחק[וי]|מחקו|תעביר[וי]|"
    r"העבירו|אפשר\s+(?:להוסיף|לשנות|להוריד|להחליף)|גם\s+(?:כתובת|טלפון|שעות|מייל))(?![\wא-ת])"
    r"|\b(?:change|add|remove|delete|replace|move|can\s+you|could\s+you|please|also)\b"
    r"|(?<![\wء-ي])(?:غيروا|غيّروا|أضيفوا|اضيفوا|احذفوا|انقلوا|استبدلوا)(?![\wء-ي])", re.I)
_LONG_NUMBER = re.compile(r"\d[\d\s\-]{4,}\d")             # a phone or another number, never an item or a picture


def read_picture_answer(text: str, qid: str) -> tuple[str, object]:
    """How the customer's reply to a picture question of the contract reads (one reader for the supervisor, which
    records it, and the planner, which reads what was recorded):
      ('answer', value)  -- the items (a tuple) for image_items, the sentence for image_subject;
      ('decline', None)  -- "I don't know / skip / you decide" (he, en, ar): the stated default, now;
      ('unread', reason) -- not an answer: a question, a change to the request, a phone / address / labelled field, an
                            item that is not a short noun phrase. Never recorded; the question is asked again."""
    if qid not in ('image_items', 'image_subject'):
        raise ValueError(f'not a picture question: {qid!r}')
    text = " ".join((text or "").split())
    if not re.search(r"[^\W\d_]", text):
        return 'unread', 'no words'
    if text.endswith(("?", "؟")):
        return 'unread', 'a question'
    if _DECLINE_ALONE.match(text) or (_DECLINE.search(text) and len(text.split()) <= 12):
        return 'decline', None
    if _CHANGE.search(text):
        return 'unread', 'a change to the request'
    from .fact_canon import fact_spans
    if _LONG_NUMBER.search(text) or fact_spans(text):
        return 'unread', 'a phone, an address or another fact'
    label, colon, listed = text.partition(":")
    if qid == 'image_subject':
        if colon and not re.search(r"תמונה|picture|image|photo|صورة", label, re.I):
            return 'unread', 'a labelled field'
        return ('answer', text) if len(text) <= MAX_SUBJECT_CHARS else ('unread', 'too long for one sentence')
    if colon:
        if not _items_label().search(label):
            return 'unread', 'a labelled field that is not an items list'
        text = listed
    items = _split_items(text) if text.strip() else []
    if not items:
        return 'unread', 'no items'
    if any(len(item.split()) > MAX_ANSWER_ITEM_WORDS or ":" in item for item in items):
        return 'unread', 'an item that is not a short noun phrase'
    if _HANDED_BACK.search(text):
        return 'unread', 'a sentence addressed to us'
    return 'answer', tuple(items)


def answer_items(answer: str) -> tuple[str, ...]:
    """The items of the customer's answer to the items question, when it reads as one (read_picture_answer), else ()."""
    kind, value = read_picture_answer(answer, 'image_items')
    return value if kind == 'answer' else ()


def _brief_items(full_prompt: str) -> tuple[str, ...]:
    """The items the approved brief names, read only from its LAST server-written block: the customer's recorded answer
    to the items question (PICTURE_ITEMS_ANSWER) first; else the list after an items label (_items_label: "קטגוריות:",
    "תפריט:", "Menu:", "القائمة:") in its "Initial content:" line (discovery.requirements_text: the customer's content,
    in their words), the first such list of at least two. () when there is neither."""
    lines = _approved_lines(full_prompt)
    for line in lines:
        if line.startswith(PICTURE_ITEMS_ANSWER):
            items = answer_items(line[len(PICTURE_ITEMS_ANSWER):])
            if items:
                return items
    label_words = _items_label()
    for line in lines:
        if not line.startswith(_CONTENT_LINE):
            continue
        for segment in _SEGMENTS.split(line[len(_CONTENT_LINE):]):
            label, colon, listed = segment.partition(":")
            if not colon or not label_words.search(" ".join(label.split())):
                continue
            items = _split_items(listed)
            if len(items) >= 2:                           # one phrase after a label is a sentence, not a list
                return tuple(items)
    return ()


def item_pictures(full_prompt: str) -> dict:
    """{'own', 'covered', 'generated'}: of the items the approved brief lists (_brief_items), the first `own` -- the
    number of the customer's photos its server-written block places in products or gallery (ITEM_PHOTO_PLACES) --
    are covered by those photos, and a picture is generated for each of the rest. A photo placed as the hero or in the
    story covers no item. Read only from the LAST brief block, never from a marker the customer typed."""
    lines = _approved_lines(full_prompt)
    own = len({m.group(1) for m in (_PLACED_UPLOAD.match(line) for line in lines)
               if m and m.group(2) in ITEM_PHOTO_PLACES})
    listed = _brief_items(full_prompt)
    return {'own': own, 'covered': listed[:own], 'generated': listed[own:]}


def _brief_says(full_prompt: str, line: str) -> bool:
    """Does the approved brief's last block carry this exact line (a recorded default)?"""
    return line in _approved_lines(full_prompt)


def _brief_subject_answer(full_prompt: str) -> str | None:
    """The customer's recorded answer to the picture question (PICTURE_SUBJECT_ANSWER), from the last brief block."""
    for line in _approved_lines(full_prompt):
        if line.startswith(PICTURE_SUBJECT_ANSWER):
            kind, words = read_picture_answer(line[len(PICTURE_SUBJECT_ANSWER):], 'image_subject')
            return words if kind == 'answer' else None
    return None


def asset_capability_status(plan) -> dict[str, str]:
    """Build-level status per asset capability: REQUIRED, OPTIONAL or
    NOT_REQUIRED. NOT_REQUIRED is neither a failure nor a pass; it means the
    product did not ask for that asset and no provider is called for it."""
    in_plan = {r.key: r.required for r in getattr(plan, "requirements", ())}
    out = {}
    for key in sorted(set(ASSET_CAPABILITY_KEYS.values())):
        if key not in in_plan:
            out[key] = "NOT_REQUIRED"
        else:
            out[key] = "REQUIRED" if in_plan[key] else "OPTIONAL"
    return out


class CapabilityPlanner:
    """Compile deterministic product intent into a capability DAG.

    Model output may enrich constraints later, but this layer owns the minimum
    requirements that may never be silently removed.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self.registry = registry or CapabilityRegistry()

    def plan(self, *, prompt: str, unified_plan, creative_plan, semantic_decisions=(),
             full_prompt: str | None = None) -> CapabilityPlan:
        # `full_prompt`: the prompt WITH its approved brief (the default hero's subject is the brief's business line);
        # `prompt` stays the customer's own words, which every detector here reads.
        low = " ".join(prompt.lower().split())
        requested: OrderedDict[str, tuple[str, bool]] = OrderedDict()

        def add(key: str, purpose: str, required: bool = True) -> None:
            if not self.registry.contains(key):
                raise ValueError(f"planner requested unknown capability: {key}")
            if key in requested:
                old_purpose, old_required = requested[key]
                requested[key] = (old_purpose, old_required or required)
            else:
                requested[key] = (purpose, required)

        # Every real product build gets the same minimum software lifecycle.
        for key in (
            "software.plan",
            "software.architecture",
            "software.code.generate",
            "software.dependencies.install",
            "software.build",
            "software.test",
            "software.repair",
            "software.preview",
            "software.export",
        ):
            add(key, "minimum real-product build lifecycle")

        explicit_2d = any(term in low for term in ("2d game", "2-d game", "משחק 2d", "משחק דו ממד"))
        for target in unified_plan.targets:
            if target == "web":
                add("target.web", "web product target")
            elif target == "android":
                add("target.android.source", "Android source target")
                if self._has_any(low, "publish", "release", "signed", "play store", "aab", "פרסום", "חתום"):
                    add("target.android.build", "Android release/build target")
            elif target == "ios":
                add("target.ios.source", "iOS source target")
                if self._has_any(low, "publish", "release", "signed", "app store", "ipa", "פרסום", "חתום"):
                    add("target.ios.build", "iOS release/build target")
            elif target == "game3d" and not explicit_2d:
                add("target.game.3d", "3D game target")

        if explicit_2d:
            add("target.game.2d", "2D game target")
        if "saas" in low:
            add("target.saas", "SaaS product target")
        if self._has_any(low, "backend", "api", "rest api", "graphql", "שרת", "ממשק api"):
            add("target.backend", "backend/API target")
        if self._has_any(low, "database", "postgres", "mysql", "sqlite", "db", "מסד נתונים"):
            add("target.database", "database target")
        if self._has_any(low, "desktop", "windows app", "mac app", "electron", "תוכנת מחשב"):
            add("target.desktop.source", "desktop product target")
        if ai_agent_intent(low):
            add("target.agent", "AI agent product target")
            add("ai.agent.tools", "agent tool execution")
            if self._has_any(low, "memory", "persistent context", "long-term memory", "זיכרון"):
                add("ai.agent.memory", "agent persistent memory")
            add("ai.agent.eval", "agent evaluation", required=False)
        if self._has_any(low, "automation", "workflow", "zapier", "אוטומציה", "תהליך אוטומטי"):
            add("target.automation", "automation product target")

        asset_map = ASSET_CAPABILITY_KEYS
        for asset in creative_plan.requests:
            capability_key = asset_map.get(asset.kind)
            if capability_key:
                add(capability_key, asset.purpose, asset.required)
        default_hero = any(is_default_hero(asset) for asset in creative_plan.requests)

        if self._has_any(low, "speech to text", "stt", "transcrib", "microphone", "listens", "listen to", "תמלול", "מיקרופון", "מאזין"):
            add("media.audio.stt", "speech input/transcription")
        if self._has_any(low, "realtime voice", "real-time voice", "live voice", "voice chat", "שיחה קולית", "קול בזמן אמת"):
            add("media.audio.realtime_voice", "real-time bidirectional voice")

        if self._has_any(low, "multiplayer", "multi-player", "online multiplayer", "רב משתתפים", "מרובה משתתפים"):
            add("game.multiplayer", "multiplayer gameplay")
        if self._has_any(low, "matchmaking", "match making", "lobby", "שידוך שחקנים", "לובי"):
            add("game.matchmaking", "player matchmaking")

        unified_capability_map = {
            "maps": "integration.maps",
            "payments": "integration.payment",
            "messaging": "integration.messaging",
        }
        for capability in unified_plan.capabilities:
            mapped = unified_capability_map.get(capability)
            if mapped:
                add(mapped, f"integration required by {capability}")

        if self._has_any(low, "github", "gitlab", "source control", "git repo"):
            add("integration.source_control", "source control integration")
        if self._has_any(low, "oauth", "google login", "google sign-in", "apple login", "sign in with apple"):
            add("integration.oauth", "OAuth identity integration")
        if self._has_any(low, "analytics", "telemetry", "product analytics"):
            add("integration.analytics", "analytics integration")

        if self._has_any(low, "publish", "deploy", "go live", "production url", "פרסם", "העלה לאוויר"):
            add("software.deploy.web", "requested production web deployment")
            add("publish.web", "requested public web publishing")

        # Only the confirmed, evidence-validated semantic decisions bound into
        # the approved Brief may amend ambiguous keyword interpretations.
        # This acts BEFORE DAG dependency closure and keeps the same registries.
        from .semantic_capabilities import overrides
        semantic = overrides(semantic_decisions, prompt=prompt)
        for key, outcome in semantic.items():
            if not self.registry.contains(key):
                continue
            if outcome == "not_required":
                requested.pop(key, None)
            elif outcome == "required":
                add(key, "approved semantic customer intent")
        # An agent requirement cannot survive removing its whole target.
        if semantic.get("target.agent") == "not_required":
            for key in ("ai.agent.tools", "ai.agent.eval", "ai.agent.memory"):
                if semantic.get(key) != "required":
                    requested.pop(key, None)

        # Every image says what it shows (the owner, 2026-11-26), from the trigger that made it (_image_subject). An
        # image nothing describes is never generated from a generic sentence: an optional one is not planned, a
        # required one becomes the contract's question (product_architect), and validate_plan refuses any image
        # requirement without a subject.
        image_subject, image_notes = None, ()
        if IMAGE_KEY in requested:
            image_purpose, image_required = requested[IMAGE_KEY]
            image_subject = self._image_subject(image_purpose, prompt, semantic_decisions, default_hero=default_hero,
                                                full_prompt=full_prompt)
            if image_subject is None:
                requested.pop(IMAGE_KEY)
                defaulted = image_required and _brief_says(full_prompt or "", PICTURE_SUBJECT_DEFAULT)
                image_notes = ((IMAGE_SUBJECT_DEFAULTED if defaulted else IMAGE_SUBJECT_UNRESOLVED) if image_required
                               else IMAGE_NOT_PLANNED,)
                logging.getLogger(__name__).warning("%s purpose=%s: nothing the customer said describes the picture",
                                                    image_notes[0], image_purpose)
        # A picture of EACH item the customer named (the owner, 2026-11-26: no image cap): one requirement per item,
        # its own words its subject (_image_requirements). Asked in the customer's words (_picture_per_item); the items
        # are the list the approved brief's "Initial content:" line labels (_brief_items). Asked with no list to read:
        # the contract asks for the list. Never when the approved decisions exclude images.
        item_subjects = ()
        text = full_prompt if full_prompt is not None else prompt
        if semantic.get(IMAGE_KEY) != "not_required" and item_pictures_wanted(text):
            # S3 (release review of 550320c): the customer's own photos are the items' pictures -- founder decision
            # #28 (media_pipeline), the check a4.pictures and media_pipeline.default_hero already make. Said in the
            # contract's notes, never a silent drop.
            # Review SF1 (49d61d3): only the photos the approved brief places among the items (products, gallery)
            # count, read from its server-written block; they stand for the first items as listed, the summary says
            # which, and a picture is generated for each item after them (item_pictures).
            split = item_pictures(text)
            item_subjects = split['generated']
            if split['own']:
                image_notes += (IMAGE_ITEMS_UPLOADED,)
                logging.getLogger(__name__).info("%s: %d own photo(s) among the items; generated for %d item(s)",
                                                 IMAGE_ITEMS_UPLOADED, split['own'], len(item_subjects))
            if item_subjects:
                requested.setdefault(IMAGE_KEY, (ITEM_PURPOSE, True))
            elif split['own'] or split['covered']:
                pass                                        # the customer's own photos stand for the items
            elif _brief_says(text, PICTURE_ITEMS_DEFAULT):
                image_notes += (IMAGE_ITEMS_DEFAULTED,)      # asked twice, no list: the stated default, not a question
                logging.getLogger(__name__).warning("%s: no item list after %d questions; items shown as text",
                                                    IMAGE_ITEMS_DEFAULTED, ASK_PICTURE_AT_MOST)
            else:
                image_notes += (IMAGE_ITEMS_UNREAD,)
                logging.getLogger(__name__).warning("%s: a picture of each item is asked and the brief lists none",
                                                    IMAGE_ITEMS_UNREAD)

        # Requiredness propagates backwards through definition dependencies so an
        # optional child never makes a dependency mandatory unless another required
        # request needs it.
        required_by_key = {key: required for key, (_, required) in requested.items()}
        changed = True
        while changed:
            changed = False
            for key, required in tuple(required_by_key.items()):
                for dependency in self.registry.get(key).dependency_keys:
                    previous = required_by_key.get(dependency, False)
                    next_value = previous or required
                    if dependency not in required_by_key or next_value != previous:
                        required_by_key[dependency] = next_value
                        changed = True

        ordered_keys = self.registry.dependency_closure(tuple(requested))
        id_by_key = {key: self._requirement_id(key) for key in ordered_keys}
        requirements = []
        for key in ordered_keys:
            definition = self.registry.get(key)
            purpose, explicit_required = requested.get(
                key, (f"dependency required by capability DAG for {key}", False)
            )
            if key == IMAGE_KEY:
                requirements.extend(self._image_requirements(
                    id_by_key[key], purpose, required_by_key.get(key, explicit_required), prompt,
                    subject=image_subject, items=item_subjects))
                continue
            requirements.append(
                CapabilityRequirement(
                    id=id_by_key[key],
                    key=key,
                    purpose=purpose,
                    required=required_by_key.get(key, explicit_required),
                    quantity=self._picture_count(key, purpose, prompt)["count"],
                    constraints=self._image_constraints(key, purpose, prompt),
                    dependency_ids=tuple(id_by_key[dep] for dep in definition.dependency_keys),
                )
            )

        target_keys = tuple(key for key in ordered_keys if key.startswith("target."))
        result = CapabilityPlan(
            requirements=tuple(requirements),
            target_keys=target_keys,
            notes=("deterministic-minimum-requirements",) + (("approved-semantic-evidence",) if semantic else ())
            + image_notes,
        )
        self.registry.validate_plan(result)
        return result

    @staticmethod
    def _has_any(text: str, *terms: str) -> bool:
        # Token-aware: "api" must not match "rapid", "db" must not match "feedback".
        return has_term(text, *terms)

    @staticmethod
    def _picture_count(key: str, purpose: str, prompt: str) -> dict:
        """How many pictures the image requirement generates: A4 decides (a4.pictures; the owner, 2026-11-17). An
        icon is always one, and so is every capability that is not an image."""
        if key != "media.image.generate":
            return {"asked": 1, "uploaded": 0, "count": 1}
        from .a4 import pictures
        from .generated_images import _kind
        if _kind(purpose) == "icon":
            return {"asked": 1, "uploaded": 0, "count": 1}
        return pictures(prompt)

    @staticmethod
    def _image_subject(purpose: str, prompt: str, semantic_decisions, *, default_hero: bool,
                       full_prompt: str | None) -> str | None:
        """What the picture shows, from the trigger that made the requirement, the first found in this order (the
        owner, 2026-11-26): the customer's own clause that names the picture (generated_images.describe); else the
        customer's own words quoted by the approved semantic decision that requires it; else the customer's recorded
        answer to the picture question (release review S1); else, for the default hero of a content site (DECISIONS
        5), the approved brief's business line. None when none of them exists."""
        from .generated_images import describe
        clause = describe(prompt, purpose)
        if clause:
            return clause
        quoted = _semantic_image_words(semantic_decisions)
        if quoted:
            return quoted
        answered = _brief_subject_answer(full_prompt if full_prompt is not None else prompt)
        if answered:                      # the customer's answer to the picture question (recorded by the supervisor)
            return answered
        if default_hero:
            return _brief_business_line(full_prompt if full_prompt is not None else prompt)
        return None

    @staticmethod
    def _image_constraints(key: str, purpose: str, prompt: str, subject: str | None = None) -> dict:
        """#324 (Michael 2026-11-13): a generated image is made FROM THE BRIEF -- the same clause of the approved
        request that becomes its alt (generated_images.describe), and an aspect ratio for its purpose. Before, only
        the purpose reached the provider and FLUX drew a generic "hero/brand visual" whatever the request said."""
        if key != "media.image.generate":
            return {}
        from .generated_images import aspect_ratio, describe, stated_style
        constraints = {"aspect_ratio": aspect_ratio(purpose)}
        # `subject`: what plan() settled (_image_subject); a direct call without one reads the customer's clause
        subject = subject or describe(prompt, purpose)
        if subject:
            constraints["subject"] = subject
        # the plan's style direction (the brief's "Design:" line): the image matches the page it is made for
        design = re.search(r"Design: style ([^;\n]+)", prompt or "")
        if design:
            constraints["style"] = design.group(1).strip()
        colours = re.search(r"requested colour description '([^'\n]+)'", prompt or "")
        if colours:
            constraints["colours"] = colours.group(1).strip()
        # without the plan's line, the customer's own style and colour words (production 2026-11-13)
        said_style, said_colours = stated_style(prompt)
        if said_style and "style" not in constraints:
            constraints["style"] = said_style
        if said_colours and "colours" not in constraints:
            constraints["colours"] = said_colours
        return constraints

    def _image_requirements(self, rid: str, purpose: str, required: bool, prompt: str, *, subject: str | None,
                            items: tuple[str, ...]) -> list[CapabilityRequirement]:
        """One requirement per generated picture (the owner, 2026-11-26: "אין דבר כזה תקרת תמונות"): A4's count of
        the main picture, each made from the subject plan() settled; then one per item the approved brief names when
        the customer asked for a picture of each, that item's own words its subject. Every picture is generated,
        checked and placed on its own, so neither a fixed number nor a provider's batch size (num_outputs) bounds how
        many a build has; the build's cost ceiling does. Each loop is bounded by its own list: A4's count, the items."""
        out = []
        count = self._picture_count(IMAGE_KEY, purpose, prompt)["count"] if subject else 0
        for n in range(1, count + 1):
            out.append(CapabilityRequirement(
                id=rid if n == 1 else f"{rid}-{n}", key=IMAGE_KEY, purpose=purpose, required=required, quantity=1,
                constraints=self._image_constraints(IMAGE_KEY, purpose, prompt, subject=subject)))
        for n, item in enumerate(items, start=1):
            out.append(CapabilityRequirement(
                id=f"{rid}-item-{n}", key=IMAGE_KEY, purpose=ITEM_PURPOSE, required=True, quantity=1,
                constraints=self._image_constraints(IMAGE_KEY, ITEM_PURPOSE, prompt, subject=item)))
        return out

    @staticmethod
    def _requirement_id(key: str) -> str:
        return "cap-" + key.replace(".", "-")
