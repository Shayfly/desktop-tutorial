from __future__ import annotations

from dataclasses import asdict, dataclass
import os


TRUE_VALUES = {'1', 'true', 'yes', 'on'}


def _env_true(name: str) -> bool:
    return os.getenv(name, '').strip().lower() in TRUE_VALUES


@dataclass(frozen=True)
class BrandReadiness:
    brand_name: str
    working_domain: str
    founder_approved_identity: bool
    logo_pack_present: bool
    trademark_clearance_complete: bool
    trademark_filing_complete: bool
    domain_owned: bool
    dns_tls_configured: bool
    public_brand_ready: bool
    blockers: tuple[str, ...]
    note: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d['blockers'] = list(self.blockers)
        return d


def brand_readiness(*, logo_pack_present: bool = True) -> BrandReadiness:
    """Fail-closed brand/legal readiness contract.

    Founder approval of a visual identity is intentionally not treated as legal
    trademark clearance or ownership of a domain. Those require external acts.
    """
    trademark_clearance = _env_true('OMNI_BRAND_TRADEMARK_CLEARED')
    trademark_filing = _env_true('OMNI_BRAND_TRADEMARK_FILED')
    domain_owned = _env_true('OMNI_BRAND_DOMAIN_OWNED')
    dns_tls = _env_true('OMNI_BRAND_DNS_TLS_READY')
    founder_approved = True
    blockers: list[str] = []
    if not trademark_clearance:
        blockers.append('formal 148AI trademark clearance not completed')
    if not domain_owned:
        blockers.append('148ailabs.com ownership not confirmed')
    if not dns_tls:
        blockers.append('production DNS/TLS not confirmed')
    if not logo_pack_present:
        blockers.append('148AI brand pack missing')
    return BrandReadiness(
        brand_name='148AI', working_domain='148ailabs.com',
        founder_approved_identity=founder_approved, logo_pack_present=logo_pack_present,
        trademark_clearance_complete=trademark_clearance,
        trademark_filing_complete=trademark_filing,
        domain_owned=domain_owned, dns_tls_configured=dns_tls,
        public_brand_ready=not blockers,
        blockers=tuple(blockers),
        note='Visual identity is founder-approved. Legal clearance, filing, domain ownership and DNS/TLS are external launch gates and are never inferred.',
    )
