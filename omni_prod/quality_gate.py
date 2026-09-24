from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import re
from .product_spec import ProductSpec
from .project_manifest import ProjectManifest

_SECRET_RE = re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\'][^"\']{8,}["\']')

@dataclass(frozen=True)
class QualityDimension:
    name: str
    score: int
    weight: int
    notes: tuple[str, ...] = ()

@dataclass(frozen=True)
class QualityAssessment:
    score: int
    passed: bool
    minimum_score: int
    dimensions: tuple[QualityDimension, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            'score': self.score,
            'passed': self.passed,
            'minimum_score': self.minimum_score,
            'dimensions': [asdict(x) for x in self.dimensions],
            'blockers': list(self.blockers),
        }


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def assess_repository(*, spec: ProductSpec, repository: dict[str, str], minimum_score: int = 80) -> QualityAssessment:
    if not 0 <= minimum_score <= 100:
        raise ValueError('minimum_score must be 0..100')
    blockers: list[str] = []
    dimensions: list[QualityDimension] = []

    # Functional traceability.
    try:
        manifest = ProjectManifest.from_repository(repository)
        referenced = {aid for check in manifest.verify for aid in check.acceptance_ids}
        required = {a.id for a in spec.acceptance}
        coverage = 100 if not required else int(100 * len(required & referenced) / len(required))
        notes = [] if coverage == 100 else [f'acceptance traceability {coverage}%']
        dimensions.append(QualityDimension('functional_traceability', coverage, 30, tuple(notes)))
        if coverage < 100:
            blockers.append('not all acceptance criteria are verified')
    except Exception as exc:
        dimensions.append(QualityDimension('functional_traceability', 0, 30, (str(exc),)))
        blockers.append('invalid or missing .omni/project.json')

    paths = set(repository)
    body = '\n'.join(repository.values())

    # Automated tests / maintainability.
    test_files = [p for p in paths if p.startswith('tests/') or p.endswith(('.test.js', '.spec.js', '_test.py'))]
    readme = any(p.lower().startswith('readme') for p in paths)
    config = any(p in paths for p in ('package.json','pyproject.toml','requirements.txt','Cargo.toml','go.mod'))
    maint = 40 + (25 if test_files else 0) + (15 if readme else 0) + (20 if config else 0)
    dimensions.append(QualityDimension('maintainability', _clamp(maint), 15,
        tuple(x for x, ok in [('missing automated tests', bool(test_files)),('missing README', readme),('missing dependency manifest', config)] if not ok)))

    # Security hygiene.
    secret_hits = sum(1 for content in repository.values() if _SECRET_RE.search(content))
    unsafe_eval = bool(re.search(r'\b(eval|exec)\s*\(', body))
    security = 100 - secret_hits * 50 - (30 if unsafe_eval else 0)
    sec_notes = []
    if secret_hits:
        sec_notes.append(f'{secret_hits} possible hard-coded secret(s)')
        blockers.append('possible hard-coded secret')
    if unsafe_eval:
        sec_notes.append('dynamic eval/exec detected')
    dimensions.append(QualityDimension('security_hygiene', _clamp(security), 20, tuple(sec_notes)))

    # Accessibility / responsive UI evidence. Non-UI projects are not punished as hard.
    ui_files = [p for p in paths if p.endswith(('.html','.tsx','.jsx','.vue','.svelte','.css'))]
    if ui_files:
        lower = body.lower()
        accessibility = 40
        accessibility += 20 if ('aria-' in lower or '<label' in lower) else 0
        accessibility += 20 if ('viewport' in lower or '@media' in lower or 'responsive' in lower) else 0
        accessibility += 20 if ('lang=' in lower or 'locale' in lower or 'i18n' in lower) else 0
    else:
        accessibility = 85
    dimensions.append(QualityDimension('ux_accessibility', _clamp(accessibility), 15))

    # Internationalization readiness.
    international = 30
    international += 25 if any('i18n' in p.lower() or 'locale' in p.lower() for p in paths) else 0
    international += 20 if any('rtl' in c.lower() for c in repository.values()) else 0
    international += 25 if any('en' in p.lower() and ('locale' in p.lower() or 'i18n' in p.lower()) for p in paths) else 0
    dimensions.append(QualityDimension('internationalization', _clamp(international), 10))

    # Delivery evidence.
    deploy = 40
    deploy += 20 if any(p.startswith('.github/workflows/') for p in paths) else 0
    deploy += 20 if any(p.lower().startswith('dockerfile') or p.endswith('docker-compose.yml') for p in paths) else 0
    deploy += 20 if '.omni/project.json' in paths else 0
    dimensions.append(QualityDimension('delivery_readiness', _clamp(deploy), 10))

    weighted = sum(d.score * d.weight for d in dimensions)
    total_weight = sum(d.weight for d in dimensions)
    score = int(round(weighted / total_weight)) if total_weight else 0
    passed = score >= minimum_score and not blockers
    return QualityAssessment(score, passed, minimum_score, tuple(dimensions), tuple(blockers))
