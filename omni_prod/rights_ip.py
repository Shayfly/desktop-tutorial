from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
import re
from typing import Iterable


class RightKind(str, Enum):
    COPYRIGHT = 'copyright'
    TRADEMARK = 'trademark'
    PERSONA_LIKENESS = 'persona_likeness'
    VOICE = 'voice'
    PERFORMER = 'performer_rights'
    MUSIC_COMPOSITION = 'music_composition'
    SOUND_RECORDING = 'sound_recording'
    DESIGN = 'design'
    DATA_LICENSE = 'data_license'


class RiskLevel(str, Enum):
    LOW = 'low'
    REVIEW = 'review'
    HIGH = 'high'


class GateStatus(str, Enum):
    CLEAR = 'CLEAR'
    REVIEW = 'REVIEW'
    LEGAL_REVIEW_REQUIRED = 'LEGAL_REVIEW_REQUIRED'


@dataclass(frozen=True)
class RightsEvidence:
    id: str
    right_kind: RightKind
    subject: str
    evidence_type: str
    scope: str
    source_reference: str = ''
    verified: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d['right_kind'] = self.right_kind.value
        return d


@dataclass(frozen=True)
class RightsFinding:
    id: str
    right_kind: RightKind
    subject: str
    reason: str
    risk: RiskLevel
    evidence_required: bool
    safe_path: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d['right_kind'] = self.right_kind.value
        d['risk'] = self.risk.value
        return d


@dataclass(frozen=True)
class JurisdictionProfile:
    code: str
    label: str
    principles: tuple[str, ...]
    source_titles: tuple[str, ...]
    source_urls: tuple[str, ...]
    verified_on: str = '2026-09-22'

    def to_dict(self) -> dict:
        return asdict(self)


JURISDICTIONS: dict[str, JurisdictionProfile] = {
    'US': JurisdictionProfile(
        'US', 'United States',
        (
            'copyright and trademark clearance are separate analyses',
            'trademarks need not be identical to create confusion risk',
            'digital replicas, voice and likeness can implicate rights outside copyright and vary by state',
        ),
        ('USPTO Likelihood of Confusion', 'U.S. Copyright Office AI Report — Digital Replicas'),
        ('https://www.uspto.gov/trademarks/search/likelihood-confusion', 'https://www.copyright.gov/ai/'),
    ),
    'EU': JurisdictionProfile(
        'EU', 'European Union',
        (
            'copyright, trademark, personality and national-law rights may all matter',
            'AI Act Article 50 creates transparency duties for certain AI-generated/manipulated content including deepfakes',
            'member-state rules can add obligations beyond EU-wide rules',
        ),
        ('EU AI Act Regulation (EU) 2024/1689 Article 50',),
        ('https://eur-lex.europa.eu/eli/reg/2024/1689/oj',),
    ),
    'IL': JurisdictionProfile(
        'IL', 'Israel',
        (
            'copyright, trademarks and performers rights are distinct legal layers',
            'performers rights can require agreement for recording/copying/broadcast in circumstances defined by law',
            'privacy/personality analysis can also be relevant to commercial use of a person identity',
        ),
        ('Israel Copyright Act 2007', "Performers' and Broadcasters' Rights Law 5744-1984", 'Protection of Privacy Law 5741-1981'),
        ('https://www.wipo.int/wipolex/en/legislation/details/5016', 'https://www.wipo.int/wipolex/en/legislation/details/15766', 'https://www.wipo.int/wipolex/en/text/347463'),
    ),
}


@dataclass(frozen=True)
class RightsAssessment:
    status: GateStatus
    findings: tuple[RightsFinding, ...]
    target_markets: tuple[str, ...]
    required_disclosures: tuple[str, ...]
    evidence: tuple[RightsEvidence, ...]
    publish_allowed: bool
    original_alternative_recommended: bool
    disclaimer: str

    def to_dict(self) -> dict:
        return {
            'status': self.status.value,
            'findings': [x.to_dict() for x in self.findings],
            'target_markets': list(self.target_markets),
            'jurisdiction_profiles': [JURISDICTIONS[m].to_dict() for m in self.target_markets if m in JURISDICTIONS],
            'required_disclosures': list(self.required_disclosures),
            'evidence': [x.to_dict() for x in self.evidence],
            'publish_allowed': self.publish_allowed,
            'original_alternative_recommended': self.original_alternative_recommended,
            'disclaimer': self.disclaimer,
        }


# Deterministic baseline only. A model/knowledge service can enrich entity recognition,
# but these rules remain a fail-closed floor for explicit imitation/identity requests.
_EXPLICIT_PATTERNS: tuple[tuple[RightKind, RiskLevel, str, str], ...] = (
    (RightKind.VOICE, RiskLevel.HIGH, r'(?i)\b(?:voice of|in the voice of|sound exactly like|clone (?:the )?voice of)\s+([\w .\'’-]{2,80})', 'A real person voice/identity request needs authorization or an original synthetic voice.'),
    (RightKind.VOICE, RiskLevel.HIGH, r'(?:בקול של|חקה את הקול של|קול זהה ל)\s*([^,.;\n]{2,80})', 'בקשת קול של אדם מזוהה דורשת הרשאה או קול סינתטי מקורי.'),
    (RightKind.PERSONA_LIKENESS, RiskLevel.HIGH, r'(?i)\b(?:face of|likeness of|look exactly like|digital replica of)\s+([\w .\'’-]{2,80})', 'Real-person likeness/digital replica request needs consent/rights review.'),
    (RightKind.PERSONA_LIKENESS, RiskLevel.HIGH, r'(?:פנים של|דמות של|שייראה בדיוק כמו)\s*([^,.;\n]{2,80})', 'שימוש בדמות/פנים של אדם מזוהה דורש בדיקת זכויות והסכמה.'),
    (RightKind.COPYRIGHT, RiskLevel.HIGH, r'(?i)\b(?:copy|recreate|replicate|make an? exact version of)\s+([^,.;\n]{2,100})', 'Exact/substantially copied creative expression needs rights review.'),
    (RightKind.COPYRIGHT, RiskLevel.REVIEW, r'(?i)\b(?:in the style of|like)\s+([^,.;\n]{2,80})', 'Style/reference request should be converted to high-level attributes rather than copied expression or identity.'),
    (RightKind.COPYRIGHT, RiskLevel.REVIEW, r'(?:בסגנון של|כמו)\s*([^,.;\n]{2,80})', 'יש להפוך את ההשראה למאפיינים כלליים וליצור ביטוי מקורי.'),
    (RightKind.TRADEMARK, RiskLevel.HIGH, r'(?i)\b(?:logo of|official logo of|use the brand|branded as)\s+([^,.;\n]{2,80})', 'Third-party brand/logo use needs trademark authorization/clearance.'),
    (RightKind.TRADEMARK, RiskLevel.HIGH, r'(?:לוגו של|המותג של|סמל של)\s*([^,.;\n]{2,80})', 'שימוש בלוגו/סימן של צד שלישי דורש הרשאה/בדיקה.'),
)

# Seed hints improve offline tests and obvious cases. It is intentionally not claimed
# to be exhaustive; live model/entity services should add findings, never remove these.
_PERSON_HINTS = ('messi', 'ronaldo', 'taylor swift', 'drake', 'beyonce', 'ביונסה', 'מסי', 'רונאלדו')
_BRAND_CHARACTER_HINTS = ('mario', 'pokemon', 'pokémon', 'disney', 'marvel', 'nike', 'adidas', 'superman', 'batman', 'מאריו', 'דיסני', 'מארוול')


class RightsEngine:
    """Rights/IP risk triage and evidence gate.

    This is not a substitute for counsel or an official clearance search. It is
    deliberately conservative: it records provenance, asks for evidence, offers
    an original alternative, and prevents a high-risk publish claim when explicit
    third-party identity/IP use is unresolved.
    """

    disclaimer = (
        'Automated rights triage is not legal advice and cannot establish ownership, '
        'fair use, public-domain status, trademark clearance, consent, or jurisdiction-specific legality. '
        'High-risk or ambiguous commercial uses require verified rights evidence or qualified legal review.'
    )

    def detect(self, prompt: str) -> tuple[RightsFinding, ...]:
        clean = ' '.join(prompt.split())
        findings: list[RightsFinding] = []
        seen: set[tuple[str, str]] = set()

        def add(kind: RightKind, subject: str, reason: str, risk: RiskLevel, safe_path: str) -> None:
            subject = subject.strip(' \t\n\r\"\'')[:100] or 'unspecified third-party reference'
            key = (kind.value, subject.lower())
            if key in seen:
                return
            seen.add(key)
            findings.append(RightsFinding(
                f'right-{len(findings)+1:03d}', kind, subject, reason, risk,
                risk in {RiskLevel.HIGH, RiskLevel.REVIEW}, safe_path,
            ))

        for kind, risk, pattern, safe in _EXPLICIT_PATTERNS:
            for match in re.finditer(pattern, clean):
                add(kind, match.group(1), safe, risk, safe)

        low = clean.lower()
        for name in _PERSON_HINTS:
            if name in low:
                # Person names alone are not automatically infringement, but product/voice/game
                # commercialization around the identity warrants review.
                if any(x in low for x in ('game', 'character', 'avatar', 'face', 'likeness', 'משחק', 'דמות', 'פנים')):
                    add(RightKind.PERSONA_LIKENESS, name, 'Named real person detected in a character/likeness context.', RiskLevel.HIGH,
                        'Use a fictional/original person or attach verified consent/license for the intended scope.')
        for name in _BRAND_CHARACTER_HINTS:
            if name in low:
                add(RightKind.COPYRIGHT, name, 'Recognizable third-party character/brand reference detected.', RiskLevel.HIGH,
                    'Extract only generic mechanics/attributes and create original names, characters, art, music and branding.')
                add(RightKind.TRADEMARK, name, 'Recognizable third-party brand/character name may create trademark/source confusion risk.', RiskLevel.REVIEW,
                    'Use an original product/character name and perform trademark clearance before public commercial launch.')

        # Music requests can carry multiple independent rights layers.
        if any(x in low for x in ('existing song', 'original recording', 'master recording', 'lyrics from', 'melody from', 'שיר קיים', 'הקלטה המקורית', 'מילים של')):
            add(RightKind.MUSIC_COMPOSITION, 'referenced song/composition', 'Music can involve composition/lyrics rights distinct from the recording.', RiskLevel.HIGH,
                'Create an original composition or provide verified composition/lyrics rights.')
            add(RightKind.SOUND_RECORDING, 'referenced sound recording', 'A master recording can carry separate rights from the composition.', RiskLevel.HIGH,
                'Use an original recording or provide verified master-use rights.')

        return tuple(findings)

    @staticmethod
    def _evidence_matches(finding: RightsFinding, evidence: RightsEvidence) -> bool:
        if not evidence.verified or evidence.right_kind != finding.right_kind:
            return False
        fs = finding.subject.lower().strip()
        es = evidence.subject.lower().strip()
        return es in {'*', 'all', 'all authorized assets'} or fs == es or (len(es) >= 4 and es in fs) or (len(fs) >= 4 and fs in es)

    def assess(
        self,
        prompt: str,
        *,
        target_markets: Iterable[str] = ('US', 'EU', 'IL'),
        evidence: Iterable[RightsEvidence] = (),
        synthetic_person_media: bool = False,
    ) -> RightsAssessment:
        markets = tuple(dict.fromkeys(m.upper() for m in target_markets if m)) or ('US', 'EU', 'IL')
        evidence_tuple = tuple(evidence)
        findings = self.detect(prompt)
        unresolved = [f for f in findings if f.evidence_required and not any(self._evidence_matches(f, e) for e in evidence_tuple)]
        high = [f for f in unresolved if f.risk == RiskLevel.HIGH]
        review = [f for f in unresolved if f.risk == RiskLevel.REVIEW]
        if high:
            status = GateStatus.LEGAL_REVIEW_REQUIRED
        elif review:
            status = GateStatus.REVIEW
        else:
            status = GateStatus.CLEAR

        disclosures: list[str] = []
        if 'EU' in markets and synthetic_person_media:
            disclosures.append('EU: disclose qualifying AI-generated/manipulated deepfake content in an appropriate clear manner (Article 50 analysis required).')
        if synthetic_person_media:
            disclosures.append('Preserve provenance that image/audio/video was AI-generated or manipulated and record consent/authorization where a real person is implicated.')

        return RightsAssessment(
            status=status,
            findings=findings,
            target_markets=markets,
            required_disclosures=tuple(disclosures),
            evidence=evidence_tuple,
            publish_allowed=status == GateStatus.CLEAR,
            original_alternative_recommended=bool(unresolved),
            disclaimer=self.disclaimer,
        )

    def originalize(self, prompt: str) -> dict:
        """Return a non-evasive original-design brief.

        The goal is not to make a small percentage change. It removes explicit
        third-party identifiers and preserves only generic product mechanics or
        creative attributes that can be independently re-designed.
        """
        findings = self.detect(prompt)
        redacted = ' '.join(prompt.split())
        for f in sorted(findings, key=lambda x: len(x.subject), reverse=True):
            redacted = re.sub(re.escape(f.subject), '[ORIGINAL_ELEMENT]', redacted, flags=re.IGNORECASE)
        return {
            'source_prompt': prompt,
            'original_brief': redacted,
            'rules': [
                'Do not preserve third-party names, logos, character designs, face/voice identity, lyrics, melody, recordings, uniforms or distinctive trade dress.',
                'Keep only generic mechanics, functional requirements, genre and high-level mood/attributes.',
                'Generate new names, visual language, characters, audio, story, UI, worldbuilding and branding from scratch.',
                'Run the resulting names/marks/assets through rights review before commercial publication.',
            ],
            'removed_subjects': [f.subject for f in findings],
            'truth_note': 'Originalization reduces copying risk; it is not a legal safe-harbor and does not replace clearance.',
        }

    def repository_files(self, assessment: RightsAssessment, *, original_prompt: str) -> dict[str, str]:
        manifest = assessment.to_dict()
        manifest['original_prompt'] = original_prompt
        return {
            'rights/rights-manifest.json': json.dumps(manifest, ensure_ascii=False, indent=2),
            'rights/README.md': (
                '# Omni Rights & IP Manifest\n'
                'This is an automated risk/provenance gate, not a legal opinion. '
                'Do not publish unresolved high-risk third-party identity/IP uses.\n'
            ),
            'rights/jurisdictions.json': json.dumps({k: v.to_dict() for k, v in JURISDICTIONS.items()}, ensure_ascii=False, indent=2),
        }
