from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Iterable

from .agents_registry import MasterAgentsRegistry, build_canonical_agents_registry
from .build_contract import (
    BuildContract,
    BuildContractStatus,
    ClarificationQuestion,
    CostEnvelopeReference,
    InfrastructureRequirement,
    sha256_fingerprint,
)
from .capability_registry import CapabilityRegistry
from .product_spec import AcceptanceCriterion, ProductSpec, Requirement
from .skills_registry import MasterSkillsRegistry, build_canonical_skills_registry
from .infrastructure_registry import MANAGED_WEB_SAAS_V1, SELF_CONTAINED_WEB_V1
from .universal_brain import OmniUniversalBrain

# Self-contained profile floor (decision 2026-10-07 #27, consistent with the
# stdlib-only dependency policy #25): real embedded persistence, verified by
# tests, never presented as managed infrastructure.
_SELF_CONTAINED_DATA = (
    "Business records persist in an embedded SQLite database file (directory from the DATA_DIR "
    "environment variable, otherwise a writable temporary directory) and are read back by later "
    "requests and by a fresh application instance"
)
_SELF_CONTAINED_STACK = ("Python standard library", "SQLite (sqlite3)", "Web UI served by the app")

# Founder principle 2026-10-07: capabilities are demand-driven, not
# product-family defaults. A generated product gets platform-managed
# infrastructure only for what the product itself asks for. This is generated
# *product* infrastructure; 148AI's own artifact storage (R2) is a platform
# requirement and never adds object storage to the product.
_MANAGED_DB_TERMS = ("postgres", "postgresql", "mysql", "mariadb", "sql server", "managed database",
                     "production database", "פוסטגרס", "מסד נתונים מנוהל")
_UPLOAD_TERMS = ("upload", "attachment", "file storage", "store files", "documents storage", "העלאת קבצים",
                 "העלאת", "צרופה", "צרופות", "אחסון קבצים")
_SCHEDULE_TERMS = ("schedule", "reminder", "cron", "recurring", "every day", "every week", "daily digest",
                   "weekly digest", "background job", "follow-up", "follow-ups", "תזכורת", "מתוזמן", "כל יום")
_OUTBOUND_TERMS = ("email", "e-mail", "sms", "webhook", "newsletter", "push notification",
                   "מייל", "אימייל", 'דוא"ל', "דואל")

# Contact details such as "email: contact@example.org" are not an outbound
# sending service. Preserve explicitly requested email notifications, marketing,
# SMS or webhook delivery; never silently remove a capability the planner has
# already marked required.
_OUTBOUND_ACTION_TERMS = ("send", "sending", "notify", "notification", "mailing",
                          "automated email", "outbound", "dispatch", "deliver",
                          "שלח", "לשלוח", "שולח", "שליחה", "שליחת", "התראה",
                          "התראות", "דיוור", "משלוח", "נשלח", "יישלח")


def _requires_outbound_delivery(prompt: str) -> bool:
    low = (prompt or "").casefold()
    if any(term in low for term in ("webhook", "newsletter", "push notification",
                                    "sms", "וובהוק", "ניוזלטר")):
        return True
    # Hebrew newsletter intake: "רוצה לקבל טיפים שבועיים ישירות למייל"
    # is a delivery requirement even though it does not contain "שלח".
    # A static contact address alone must not trigger outbound provisioning.
    if re.search(r"(?:לקבל|קבלת|יישלח|נשלח|subscribe|receive|weekly|שבועי)"
                 r"[^.!?\n]{0,140}(?:למייל|באימייל|אימייל|מייל|email|e-mail)", low):
        return True
    return (any(term in low for term in _OUTBOUND_TERMS)
            and any(action in low for action in _OUTBOUND_ACTION_TERMS))


_NO_LOGIN = re.compile(r"(בלי|ללא)\s+(התחברות|הרשמה|סיסמ|משתמשים)|\b(no|without)\s+(login|sign[- ]?in|user accounts)|"
                       r"sign-in:\s*none", re.I)


def no_login_requested(prompt: str) -> bool:
    return bool(_NO_LOGIN.search(prompt or ''))


# A WhatsApp *link* (wa.me / "קישור לוואטסאפ" / "whatsapp button") is a plain hyperlink, not a messaging
# integration: nothing is sent by the product. Stripped before integration inference only.
_WA_LINK = re.compile(
    r"(wa\.me\S*|api\.whatsapp\.com\S*|"
    r"(קישור|לינק|כפתור|link|button)\s+(ישיר\s+)?(ל|של\s+)?(וואטסאפ|ווטסאפ|whatsapp)|"
    r"(וואטסאפ|ווטסאפ|whatsapp)\s+(link|button|קישור|לינק|כפתור))", re.I)


def strip_whatsapp_links(text: str) -> str:
    return _WA_LINK.sub(" ", text or "")


_CONTENT_ONLY_PROMPT = ("Product kind: CONTENT-ONLY website", "Sign-in: NONE", "Do not store personal or contact details of people.")


def content_only_approved(prompt: str) -> bool:
    """True only when the *approved brief block* (not the free text) records a content-only website with no
    sign-in and no personal data. Free-text keywords never qualify."""
    flat = " ".join((prompt or "").split())
    marker = "--- Approved project brief"
    if marker not in flat:
        return False
    block = flat.split(marker, 1)[1]
    return all(t in block for t in _CONTENT_ONLY_PROMPT)


def _infer_infrastructure(prompt: str, integrations, *, no_login: bool | None = None) -> tuple[InfrastructureRequirement, ...]:
    """Infrastructure the product needs, in the canonical managed-profile order.

    Persistence and sessions are always needed (every contract has data and the
    platform-auth floor); they are embedded (SELF_CONTAINED) unless a managed
    database is required, in which case both are platform-managed. Object
    storage, scheduled work and outbound delivery appear only on demand."""
    low = prompt.casefold()
    wants = lambda terms: any(t in low for t in terms)  # noqa: E731
    integration_keys = set(integrations or ())
    managed_db = wants(_MANAGED_DB_TERMS)
    needed = {
        "database": True,
        # Directive 2026-10-09 §17 "no-login fidelity": sessions are not added
        # when the request (or the approved brief) says there is no sign-in.
        "auth_session": not (no_login_requested(prompt) if no_login is None else no_login),
        "object_storage": wants(_UPLOAD_TERMS) or "storage" in integration_keys,
        "scheduled_http": wants(_SCHEDULE_TERMS),
        "outbound": _requires_outbound_delivery(prompt) or bool({"email", "webhook"} & integration_keys),
    }
    embedded = {r.kind: r for r in SELF_CONTAINED_WEB_V1.requirements}
    out = []
    for managed in MANAGED_WEB_SAAS_V1.requirements:
        if not needed[managed.kind]:
            continue
        if managed.kind in embedded and not managed_db:
            out.append(embedded[managed.kind])
        else:
            out.append(managed)
    return tuple(out)


class ProductArchitect:
    """Compile product intent into the immutable M5 Web/SaaS Build Contract.

    Deterministic policy owns the minimum capability/security/infrastructure
    floor. A model-backed ArchitectAgent may enrich the product spec but cannot
    remove that floor.
    """

    def __init__(
        self,
        *,
        brain: OmniUniversalBrain | None = None,
        architect_agent=None,
        capability_registry: CapabilityRegistry | None = None,
        skills_registry: MasterSkillsRegistry | None = None,
        agents_registry: MasterAgentsRegistry | None = None,
    ) -> None:
        self.capabilities = capability_registry or CapabilityRegistry()
        self.skills = skills_registry or build_canonical_skills_registry(self.capabilities)
        self.agents = agents_registry or build_canonical_agents_registry(self.skills)
        self.brain = brain or OmniUniversalBrain()
        self.architect_agent = architect_agent

    def compile(
        self,
        prompt: str,
        *,
        project_id: str,
        contract_version: int,
        pricing_catalog_version: str = "runtime-provider-price-catalog",
        created_at: str | None = None,
    ) -> BuildContract:
        clean = " ".join(prompt.split()).strip()
        if not clean:
            raise ValueError("prompt cannot be empty")
        if not project_id.strip():
            raise ValueError("project_id cannot be empty")
        if contract_version < 1:
            raise ValueError("contract_version must be >= 1")

        # Capabilities, infrastructure, roles and data needs are detected from
        # the user's own request (plus the sign-in decision), never from the
        # brief text 148AI wrote; the full text still binds the spec and code.
        from .discovery import detection_text
        intent = detection_text(clean) or clean
        from .semantic_capabilities import read_approved
        semantic_decisions = read_approved(clean)
        decision = self.brain.decide(intent, semantic_decisions=semantic_decisions)
        capability_plan = decision.capabilities
        capability_fingerprint = sha256_fingerprint(capability_plan.to_dict())
        # Demand-driven infrastructure, bound into the immutable contract.
        no_login_early = no_login_requested(clean)
        infrastructure = _infer_infrastructure(
            intent, self._infer_integrations(intent, capability_plan), no_login=no_login_early)
        embedded_db = any(r.kind == "database" and r.connection_mode == "SELF_CONTAINED" for r in infrastructure)
        profile = (SELF_CONTAINED_WEB_V1 if all(r.connection_mode == "SELF_CONTAINED" for r in infrastructure)
                   else MANAGED_WEB_SAAS_V1)
        content_only = no_login_early and content_only_approved(clean)
        floor_spec = self._floor_spec(clean, decision, self_contained=embedded_db,
                                      content_only=content_only, no_login=no_login_early)

        model_spec = None
        if self.architect_agent is not None:
            floor_context = {
                "product_spec_floor": floor_spec.to_dict(),
                "capability_plan": capability_plan.to_dict(),
                "capability_plan_fingerprint": capability_fingerprint,
                "principles": list(decision.principles),
                "rights": decision.rights.to_dict(),
                "rule": "Model output may enrich but must not remove deterministic minimums.",
            }
            try:
                model_spec = self.architect_agent.create_spec(clean, deterministic_floor=floor_context)
            except TypeError:
                # Compatibility for third-party/reviewer ArchitectAgent shims using
                # the legacy create_spec(prompt) contract. The deterministic floor
                # is still merged below and remains authoritative.
                model_spec = self.architect_agent.create_spec(clean)
        product_spec = self._merge_specs(floor_spec, model_spec)
        # Fingerprint the spec exactly as it will be read back from storage
        # (founder build 2026-10-08: an 80-char title cut after a space was
        # stripped on load, the fingerprint no longer matched, HTTP 500).
        product_spec = ProductSpec.from_dict(product_spec.to_dict())

        roles, role_defaults = self._infer_roles(intent)
        no_login = no_login_requested(clean)
        if no_login:
            # "No sign-in" is honoured: one kind of user, no roles or sessions.
            roles, role_defaults = ("user",), ["no_login_single_user"]
        data_requirements = self._infer_data_requirements(intent, decision.plan.modules)
        integrations = self._infer_integrations(intent, capability_plan)
        questions = self._material_questions(intent, data_requirements)
        status = BuildContractStatus.NEEDS_CLARIFICATION if questions else BuildContractStatus.READY
        static_default = ["static_content_site"] if content_only else []
        defaults = tuple(role_defaults + static_default + [profile.key, "vercel_release_target"])
        security = tuple(s for s in (
            "tenant_isolation",
            "least_privilege_rbac",
            "secret_references_only",
            "secure_session_lifecycle",
            "input_validation",
            "audit_evidence",
            "no_cross_tenant_resource_access",
        ) if not (no_login and s in ("least_privilege_rbac", "secure_session_lifecycle")))
        cost = CostEnvelopeReference(pricing_catalog_version=pricing_catalog_version)

        required_skills = self._required_skills(capability_plan)
        required_agents = self._required_agents(required_skills)

        timestamp = created_at or datetime.now(timezone.utc).isoformat()
        provisional = {
            "project_id": project_id,
            "contract_version": contract_version,
            "status": status.value,
            "prompt": clean,
            "product_family": profile.key,
            "target": "web",
            "release_target": "vercel",
            "product_spec": product_spec.to_dict(),
            "user_roles": list(roles),
            "data_requirements": list(data_requirements),
            "required_integrations": list(integrations),
            "infrastructure": [item.to_dict() for item in infrastructure],
            "capability_plan": capability_plan.to_dict(),
            "capability_plan_fingerprint": capability_fingerprint,
            "acceptance": [a.__dict__ for a in product_spec.acceptance],
            "security": list(security),
            "cost_envelope": cost.to_dict(),
            "unresolved_questions": [q.to_dict() for q in questions],
            "defaults_applied": list(defaults),
            "required_skill_keys": list(required_skills),
            "required_agent_keys": list(required_agents),
            "skills_registry_version": self.skills.version,
            "agents_registry_version": self.agents.version,
        }
        contract_fingerprint = sha256_fingerprint(provisional)
        contract_id = "bc_" + sha256(
            f"{project_id}:{contract_version}:{contract_fingerprint}".encode("utf-8")
        ).hexdigest()[:24]
        return BuildContract(
            id=contract_id,
            project_id=project_id,
            contract_version=contract_version,
            status=status,
            prompt=clean,
            product_family=profile.key,
            target="web",
            release_target="vercel",
            product_spec=product_spec,
            user_roles=roles,
            data_requirements=data_requirements,
            required_integrations=integrations,
            infrastructure=infrastructure,
            capability_plan=capability_plan,
            capability_plan_fingerprint=capability_fingerprint,
            acceptance=product_spec.acceptance,
            security=security,
            cost_envelope=cost,
            unresolved_questions=questions,
            defaults_applied=defaults,
            required_skill_keys=required_skills,
            required_agent_keys=required_agents,
            skills_registry_version=self.skills.version,
            agents_registry_version=self.agents.version,
            created_at=timestamp,
            contract_fingerprint=contract_fingerprint,
        )

    @staticmethod
    def _floor_spec(prompt: str, decision, *, self_contained: bool = False,
                    content_only: bool = False, no_login: bool = False) -> ProductSpec:
        title = decision.plan.title or prompt[:80]
        if content_only:
            return ProductArchitect._content_only_spec(prompt, title)
        requirements: list[Requirement] = [
            Requirement("platform-auth", "Users authenticate through durable application sessions", "security"),
            Requirement("platform-rbac", "At least two application roles are enforced server-side", "security"),
            Requirement("platform-data", _SELF_CONTAINED_DATA if self_contained
                        else "Business records persist in durable relational storage", "data"),
            Requirement("platform-responsive", "Primary workflows are usable on mobile and desktop web", "quality"),
            Requirement("platform-api", "Backend exposes a versionable API/health surface", "functional"),
            Requirement("platform-observability", "Runtime errors and health are observable without secret leakage", "quality"),
            Requirement("platform-deploy", "Verified immutable release can be deployed separately from preview", "deployment"),
            Requirement("platform-secrets", "Secrets are injected by reference and never embedded in generated source", "security"),
        ]
        if no_login:
            # An approved no-sign-in landing page must not acquire visitor auth
            # or multi-role requirements from the platform's default template.
            requirements = [r for r in requirements if r.id not in ('platform-auth', 'platform-rbac')]
        existing = {r.id for r in requirements}
        for module in decision.plan.modules:
            rid = "module-" + re.sub(r"[^a-z0-9]+", "-", module.lower()).strip("-")
            if rid and rid not in existing:
                requirements.append(Requirement(rid, f"Support the {module} business workflow", "functional"))
                existing.add(rid)
        acceptance = tuple(
            AcceptanceCriterion(
                id="accept-" + req.id,
                requirement_id=req.id,
                text=f"Automated acceptance proves: {req.text}",
            )
            for req in requirements
        )
        if self_contained:
            return ProductSpec(
                title=title,
                summary=f"Self-contained Web app contract for: {prompt}",
                stack=_SELF_CONTAINED_STACK,
                requirements=tuple(requirements),
                acceptance=acceptance,
            )
        return ProductSpec(
            title=title,
            summary=f"M5 managed Web/SaaS contract for: {prompt}",
            stack=("Python", "FastAPI", "PostgreSQL-compatible", "Web UI"),
            requirements=tuple(requirements),
            acceptance=acceptance,
        )

    @staticmethod
    def _content_only_spec(prompt: str, title: str) -> ProductSpec:
        """Floor for an approved CONTENT-ONLY website: no sign-in, roles, database or record API to prove; the page
        must show the approved content and work on mobile and desktop. Nothing here lets a build skip real checks."""
        requirements = [
            Requirement("site-content", "CONTENT-ONLY website: GET / serves the complete approved content, prices, links and "
                        "logo text exactly as given; no sign-in, no stored visitor data, no record forms and no record API", "functional"),
            Requirement("platform-responsive", "The page is usable on mobile and desktop web (viewport meta and responsive CSS)", "quality"),
            Requirement("platform-api", "The server answers HTTP 200 on its health path; no /api/* record endpoint is required", "functional"),
            Requirement("platform-observability", "Runtime errors and health are observable without secret leakage", "quality"),
            Requirement("platform-deploy", "Verified immutable release can be deployed separately from preview", "deployment"),
            Requirement("platform-secrets", "Secrets are injected by reference and never embedded in generated source", "security"),
        ]
        acceptance = tuple(AcceptanceCriterion(id="accept-" + r.id, requirement_id=r.id,
                                               text=f"Automated acceptance proves: {r.text}") for r in requirements)
        return ProductSpec(title=title, summary=f"Content-only Web site contract for: {prompt}",
                           stack=_SELF_CONTAINED_STACK, requirements=tuple(requirements), acceptance=acceptance)

    @staticmethod
    def _merge_specs(floor: ProductSpec, model: ProductSpec | None) -> ProductSpec:
        if model is None:
            return floor
        requirements = list(floor.requirements)
        req_ids = {r.id for r in requirements}
        for req in model.requirements:
            if req.id not in req_ids:
                requirements.append(req)
                req_ids.add(req.id)
        acceptance = list(floor.acceptance)
        acc_ids = {a.id for a in acceptance}
        for criterion in model.acceptance:
            if criterion.requirement_id in req_ids and criterion.id not in acc_ids:
                acceptance.append(criterion)
                acc_ids.add(criterion.id)
        stack = tuple(dict.fromkeys((*floor.stack, *model.stack)))
        return ProductSpec(
            title=model.title or floor.title,
            summary=model.summary or floor.summary,
            stack=stack,
            requirements=tuple(requirements),
            acceptance=tuple(acceptance),
        )

    @staticmethod
    def _infer_roles(prompt: str) -> tuple[tuple[str, ...], list[str]]:
        low = prompt.casefold()
        role_terms = (
            ("admin", ("admin", "administrator", "מנהל מערכת")),
            ("travel_agent", ("travel agent", "travel-agent", "סוכן נסיעות")),
            ("manager", ("manager", "מנהל")),
            ("agent", (" agent", "סוכן")),
            ("customer", ("customer", "client", "לקוח")),
            ("driver", ("driver", "נהג")),
            ("member", ("member", "team member", "עובד", "צוות")),
        )
        roles: list[str] = []
        for role, terms in role_terms:
            if any(term in low for term in terms):
                roles.append(role)
        defaults: list[str] = []
        if "admin" not in roles:
            roles.insert(0, "admin")
            defaults.append("default_admin_role")
        non_admin = [r for r in roles if r != "admin"]
        if not non_admin:
            roles.append("member")
            defaults.append("default_member_role")
        return tuple(dict.fromkeys(roles)), defaults

    @staticmethod
    def _infer_data_requirements(prompt: str, modules: Iterable[str]) -> tuple[str, ...]:
        low = prompt.casefold()
        result = list(modules)
        vocabulary = (
            ("customers", ("customer", "customers", "client", "clients", "לקוח", "לקוחות")),
            ("bookings", ("booking", "bookings", "reservation", "reservations", "הזמנה", "הזמנות")),
            ("leads", ("lead", "leads", "ליד", "לידים")),
            ("orders", ("order", "orders", "הזמנות מוצר")),
            ("products", ("product", "products", "מוצרים")),
            ("inventory", ("inventory", "stock", "מלאי")),
            ("drivers", ("driver", "drivers", "נהג", "נהגים")),
            ("rides", ("ride", "rides", "trip", "trips", "נסיעה", "נסיעות")),
            ("messages", ("message", "messages", "chat", "הודעות")),
            ("invoices", ("invoice", "invoices", "חשבונית", "חשבוניות")),
        )
        for name, terms in vocabulary:
            if any(term in low for term in terms):
                result.append(name)
        return tuple(dict.fromkeys(result))

    @staticmethod
    def _infer_integrations(prompt: str, capability_plan) -> tuple[str, ...]:
        low = strip_whatsapp_links(prompt).casefold()
        result: list[str] = []
        canonical_capability_integrations = {
            "integration.payment": "payments",
            "integration.messaging": "messaging",
            "integration.maps": "maps",
            "integration.email": "email",
            "integration.webhook": "webhook",
            "integration.oauth": "oauth",
            "integration.analytics": "analytics",
            "integration.storage": "storage",
            "integration.database": "database",
            "integration.source_control": "source_control",
        }
        for req in capability_plan.requirements:
            mapped = canonical_capability_integrations.get(req.key)
            if mapped:
                result.append(mapped)
        direct = (
            ("email", ("email", "e-mail", "מייל", "דוא")) if _requires_outbound_delivery(prompt) else ("email", ()),
            ("webhook", ("webhook", "web hook")),
            ("payments", ("payment", "payments", "checkout", "תשלום")),
            ("maps", ("map", "maps", "gps", "מפה")),
            ("messaging", ("message", "messaging", "whatsapp", "chat", "הודעות")),
        )
        for key, terms in direct:
            if any(term in low for term in terms):
                result.append(key)
        return tuple(dict.fromkeys(result))

    @staticmethod
    def _material_questions(prompt: str, data_requirements: tuple[str, ...]) -> tuple[ClarificationQuestion, ...]:
        low = prompt.casefold().strip()
        generic = {
            "build me an app", "build an app", "make me an app", "create an app",
            "תבנה לי אפליקציה", "תיצור לי אפליקציה", "בנה לי אפליקציה",
        }
        generic_data = set(data_requirements).issubset({"users", "items", "activity"})
        if low in generic or (len(low.split()) <= 5 and generic_data):
            return (
                ClarificationQuestion(
                    id="clarify-primary-workflow",
                    question="What is the primary business workflow and who will use it?",
                    reason="The answer materially changes the data model and acceptance contract.",
                    material=True,
                ),
            )
        return ()

    def _required_skills(self, capability_plan) -> tuple[str, ...]:
        keys = [
            "skill.internal.requirements.clarify",
            "skill.internal.capability.plan",
            "skill.internal.cost.plan",
            "skill.internal.infrastructure.plan",
        ]
        for requirement in capability_plan.requirements:
            if requirement.required:
                keys.extend(skill.key for skill in self.skills.skills_for_capability(requirement.key))
        return tuple(dict.fromkeys(keys))

    def _required_agents(self, required_skills: tuple[str, ...]) -> tuple[str, ...]:
        required = set(required_skills)
        keys = ["agent.chief_orchestrator", "agent.product_architect", "agent.capability_planner", "agent.cost_planner"]
        for agent in self.agents.all():
            if required.intersection(agent.allowed_skills):
                keys.append(agent.key)
        return tuple(dict.fromkeys(keys))
