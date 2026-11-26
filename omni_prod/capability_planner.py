from __future__ import annotations

import logging

import re

from collections import OrderedDict
from collections.abc import Mapping

from .a4 import ITEM_PURPOSE
from .capabilities import CapabilityPlan, CapabilityRequirement
from .capability_registry import CapabilityRegistry
from .intent_terms import ai_agent_intent, has_term
from .media_pipeline import AssetKind, is_default_hero


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
_APPROVED_BRIEF = re.compile(r"(?m)^--- Approved project brief \(binding; fingerprint [a-f0-9]{16}\) ---$")
_BUSINESS_LINE = "Main action: "
_CONTENT_LINE = "Initial content: "
# the last two items of a list: "קופסאות אחסון ומצתים", "boxes and lighters"
_LAST_AND = re.compile(r"\s+(?:ו-?(?=[א-ת])|and\s+)", re.I)
_NOT_AN_ITEM = {"עוד", "וכו", "וכו׳", "וכו'", "וכדומה", "more", "etc", "etc."}


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


def _brief_items(full_prompt: str) -> tuple[str, ...]:
    """The items the approved brief names: the list after an items label ("קטגוריות:", "מוצרים:", "dishes:") in its
    "Initial content:" line (discovery.requirements_text: the customer's content, in their words), the first such list
    of at least two. Commas separate the items and "ו"/"and" joins the last two. Read only from the LAST server-written
    brief block. () when that line has no labelled list."""
    from .site_content.one_page import ITEMS_HE, _ITEMS_EN_PLURAL     # the item words the picture_per_item reader knows
    label_words = re.compile(r"(?<![\wא-ת])[ובשלמהכ]{0,3}(?:" + "|".join(sorted(ITEMS_HE, key=len, reverse=True))
                             + r")(?![\wא-ת])|\b" + _ITEMS_EN_PLURAL + r"\b", re.I)
    text = full_prompt or ""
    markers = list(_APPROVED_BRIEF.finditer(text))
    lines = text[markers[-1].end():].splitlines() if markers else ()
    for line in lines:
        if not line.startswith(_CONTENT_LINE):
            continue
        for segment in line[len(_CONTENT_LINE):].split(";"):
            label, colon, listed = segment.partition(":")
            if not colon or not label_words.search(label):
                continue
            parts = [" ".join(p.split()) for p in listed.split(",")]
            last = list(_LAST_AND.finditer(parts[-1]))
            if last:                                      # "a ו-b": the last element holds the last two items
                parts[-1:] = [parts[-1][:last[-1].start()], parts[-1][last[-1].end():]]
            items = []
            for part in parts:
                item = part.strip(" .")
                if item.lower().startswith("and "):
                    item = item[4:].strip()
                if item and item.lower() not in _NOT_AN_ITEM and item not in items:
                    items.append(item[:MAX_SUBJECT_CHARS])
            if len(items) >= 2:                           # one phrase after a label is a sentence, not a list
                return tuple(items)
    return ()


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
                image_notes = (IMAGE_SUBJECT_UNRESOLVED if image_required else IMAGE_NOT_PLANNED,)
                logging.getLogger(__name__).warning("%s purpose=%s: nothing the customer said describes the picture",
                                                    image_notes[0], image_purpose)
        # A picture of EACH item the customer named (the owner, 2026-11-26: no image cap): one requirement per item,
        # its own words its subject (_image_requirements). Asked in the customer's words (_picture_per_item); the items
        # are the list the approved brief's "Initial content:" line labels (_brief_items). Asked with no list to read:
        # the contract asks for the list. Never when the approved decisions exclude images.
        item_subjects = ()
        text = full_prompt if full_prompt is not None else prompt
        if semantic.get(IMAGE_KEY) != "not_required" and _picture_per_item(text):
            item_subjects = _brief_items(text)
            if item_subjects:
                requested.setdefault(IMAGE_KEY, (ITEM_PURPOSE, True))
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
        customer's own words quoted by the approved semantic decision that requires it; else, for the default hero of a
        content site (DECISIONS 5), the approved brief's business line. None when none of them exists."""
        from .generated_images import describe
        clause = describe(prompt, purpose)
        if clause:
            return clause
        quoted = _semantic_image_words(semantic_decisions)
        if quoted:
            return quoted
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
