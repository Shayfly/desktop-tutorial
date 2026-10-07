"""M5 Task 6: canonical generated-app infrastructure profiles.

Profile and kind keys are vendor-neutral by rule: a concrete provider (a
database host, an object store, a scheduler) is chosen by a provisioner
adapter and recorded on the binding, never baked into a canonical key.
"""
from __future__ import annotations

from typing import Iterable

from .build_contract import InfrastructureRequirement
from .infrastructure_contracts import InfrastructureKind, InfrastructureProfile

# Vendor/product names that must never appear in a canonical profile or kind
# key. This is a guard against accidental coupling, not an endorsement list.
_VENDOR_TOKENS = (
    "aws", "amazon", "s3", "gcp", "google", "azure", "vercel", "netlify", "supabase", "neon",
    "planetscale", "firebase", "cloudflare", "r2", "e2b", "fly", "render", "heroku", "railway",
    "stripe", "resend", "sendgrid", "mailgun", "postmark", "twilio", "openai", "anthropic",
    "upstash", "inngest", "clerk", "auth0", "mongodb", "redis",
)

MANAGED_WEB_SAAS_V1 = InfrastructureProfile(
    key="managed_web_saas_v1",
    version=1,
    description=(
        "Platform-managed infrastructure for a generated Web/SaaS product: Postgres-compatible "
        "database, application auth/session secret, S3-compatible object storage, scheduled HTTP "
        "work and outbound webhook/email delivery. Each environment (preview, production) gets "
        "its own isolated resources and secrets."
    ),
    requirements=(
        InfrastructureRequirement("database", "durable relational application data"),
        InfrastructureRequirement("auth_session", "application-scoped durable authentication and sessions"),
        InfrastructureRequirement("object_storage", "durable file/object uploads and generated assets"),
        InfrastructureRequirement("scheduled_http", "background or scheduled application work"),
        InfrastructureRequirement("outbound", "email/webhook outbound delivery"),
    ),
    # Sessions and scheduled jobs persist state in the application database.
    kind_dependencies={
        InfrastructureKind.AUTH_SESSION: (InfrastructureKind.DATABASE,),
        InfrastructureKind.SCHEDULED_HTTP: (InfrastructureKind.DATABASE,),
    },
)

# Profile of a contract whose infrastructure is entirely embedded (Golden E2E
# #1, founder decisions 2026-10-07 #27 and "capabilities are demand-driven").
# Self-contained is not fake: the generated app embeds a standard-library SQLite database and
# in-app sessions in its own runtime. Nothing is provisioned, so nothing here
# is ever LIVE; these kinds count as verified only when the app's own tests
# and the behavioral preview acceptance pass. Object storage, scheduled work
# and outbound delivery are out of this profile's scope and stay NOT_VERIFIED.
SELF_CONTAINED_WEB_V1 = InfrastructureProfile(
    key="self_contained_web_v1",
    version=1,
    description=(
        "Self-contained generated web app: embedded SQLite application data and in-app "
        "authentication/sessions inside the app runtime. No platform-provisioned resources. "
        "Object storage, scheduled work and outbound delivery are out of scope (NOT_VERIFIED)."
    ),
    requirements=(
        InfrastructureRequirement("database", "embedded SQLite application data inside the generated app",
                                  connection_mode="SELF_CONTAINED"),
        InfrastructureRequirement("auth_session", "in-app authentication and sessions stored in the embedded database",
                                  connection_mode="SELF_CONTAINED"),
    ),
    kind_dependencies={InfrastructureKind.AUTH_SESSION: (InfrastructureKind.DATABASE,)},
)
# Every generated-app infrastructure kind the platform knows. A kind absent
# from a contract is NOT_REQUIRED for that build (demand-driven).
INFRASTRUCTURE_KINDS: tuple[str, ...] = tuple(r.kind for r in MANAGED_WEB_SAAS_V1.requirements)

_WEB_TARGETS = frozenset({"web", "saas"})


class InfrastructureProfileRegistry:
    def __init__(self, profiles: Iterable[InfrastructureProfile] | None = None) -> None:
        source = tuple(profiles) if profiles is not None else (MANAGED_WEB_SAAS_V1, SELF_CONTAINED_WEB_V1)
        self._profiles: dict[str, InfrastructureProfile] = {}
        for profile in source:
            self.validate_canonical_key(profile.key)
            for requirement in profile.requirements:
                self.validate_canonical_key(requirement.kind)
            if profile.key in self._profiles:
                raise ValueError(f"duplicate infrastructure profile: {profile.key}")
            self._profiles[profile.key] = profile

    @staticmethod
    def validate_canonical_key(key: str) -> None:
        tokens = set(str(key).lower().replace("-", "_").split("_"))
        leaked = sorted(tokens.intersection(_VENDOR_TOKENS))
        if leaked:
            raise ValueError(f"canonical infrastructure key {key!r} must not contain provider names: {leaked}")

    def get(self, key: str) -> InfrastructureProfile:
        try:
            return self._profiles[key]
        except KeyError as exc:
            raise KeyError(f"unknown infrastructure profile: {key}") from exc

    def all(self) -> tuple[InfrastructureProfile, ...]:
        return tuple(self._profiles[k] for k in sorted(self._profiles))


DEFAULT_INFRASTRUCTURE_PROFILES = InfrastructureProfileRegistry()


def is_self_contained(requirement) -> bool:
    return getattr(requirement, "connection_mode", "PLATFORM_MANAGED") == "SELF_CONTAINED"


def profile_for_contract(contract, registry: InfrastructureProfileRegistry | None = None) -> InfrastructureProfile:
    """Resolve the profile that must satisfy a BuildContract's infrastructure.

    ``BuildContract.product_family`` already names the profile for Web/SaaS
    contracts (M5 Task 4). Every infrastructure kind in the contract must be
    covered by that profile; anything else is a planning error, not something
    to silently drop.
    """
    registry = registry or DEFAULT_INFRASTRUCTURE_PROFILES
    family = str(getattr(contract, "product_family", "") or "")
    target = str(getattr(contract, "target", "") or "")
    try:
        profile = registry.get(family)
    except KeyError:
        if target in _WEB_TARGETS:
            profile = registry.get(MANAGED_WEB_SAAS_V1.key)
        else:
            raise ValueError(f"no infrastructure profile for product family {family!r} / target {target!r}")
    profile_kinds = {r.kind for r in profile.requirements}
    for requirement in getattr(contract, "infrastructure", ()):
        if requirement.kind not in profile_kinds:
            raise ValueError(
                f"contract infrastructure kind {requirement.kind!r} is not provided by profile {profile.key}")
    return profile
