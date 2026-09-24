from __future__ import annotations

from dataclasses import asdict
from .v26_platform import V26UniversalPlatform
from .repository_patch import FilePatch, apply_patch
from .rights_ip import RightsEngine, RightsEvidence, RightKind, RightsAssessment
from .company_os import OnePersonCompanyOS


class V27UniversalPlatform(V26UniversalPlatform):
    """V26 creator platform plus project-level rights provenance/publish gates."""

    def __init__(self, *, token_secret: str, generated_app_token_secret: str | None = None):
        super().__init__(token_secret=token_secret, generated_app_token_secret=generated_app_token_secret)
        self.rights = RightsEngine()
        self.company_os = OnePersonCompanyOS()
        self._rights_evidence: dict[str, list[RightsEvidence]] = {}
        self._rights_assessment: dict[str, RightsAssessment] = {}
        self._rights_prompt: dict[str, str] = {}
        self._rights_markets: dict[str, tuple[str, ...]] = {}

    def _evidence_for(self, key: str) -> tuple[RightsEvidence, ...]:
        return tuple(self._rights_evidence.get(key, ()))

    def build(self, *, token: str, project_id: str, prompt: str, target_markets: tuple[str, ...] = ('US', 'EU', 'IL')) -> dict:
        account, key = self._key(token=token, project_id=project_id)
        decision = self.brain.decide(prompt, target_markets=target_markets)
        evidence = self._evidence_for(key)
        synthetic_person_media = bool(decision.rights.required_disclosures) or any(
            f.right_kind.value in {'voice', 'persona_likeness'} for f in decision.rights.findings
        )
        assessment = self.rights.assess(
            prompt,
            target_markets=target_markets,
            evidence=evidence,
            synthetic_person_media=synthetic_person_media,
        )
        result = self.engine.build(project_id=key, prompt=prompt)
        current = self.engine.workspace.current(key)
        if current is None:
            raise RuntimeError('build did not create a project version')
        files = {}
        files.update(self.brain.creative.repository_files(decision.creative))
        files.update(self.rights.repository_files(assessment, original_prompt=prompt))
        repo = apply_patch(current.repository(), [FilePatch(path=p, content=c) for p, c in files.items()])
        final_version = self.engine.workspace.commit(project_id=key, repository=repo, message='V27 creative + rights manifest')
        self._rights_assessment[key] = assessment
        self._rights_prompt[key] = prompt
        self._rights_markets[key] = tuple(target_markets)
        return {
            'status': result.status,
            'project_id': project_id,
            'owner_id': account.id,
            'version_id': final_version.id,
            'checksum': final_version.checksum,
            'file_count': len(repo),
            'launch_score': result.launch_score,
            'launch_ready': result.launch_ready and assessment.publish_allowed,
            'brain': decision.to_dict(),
            'creative_assets': {
                'planned': len(decision.creative.requests),
                'materialized': 0,
                'truth': 'planned assets are not claimed as generated until a configured provider returns files',
            },
            'rights': assessment.to_dict(),
        }

    def rights_status(self, *, token: str, project_id: str) -> dict:
        _, key = self._key(token=token, project_id=project_id)
        assessment = self._rights_assessment.get(key)
        if assessment is None:
            return {
                'status': 'NOT_ASSESSED',
                'publish_allowed': False,
                'evidence': [x.to_dict() for x in self._evidence_for(key)],
                'disclaimer': self.rights.disclaimer,
            }
        return assessment.to_dict()

    def _refresh_rights_manifest(self, *, key: str) -> RightsAssessment | None:
        prompt = self._rights_prompt.get(key)
        if not prompt:
            return None
        markets = self._rights_markets.get(key, ('US', 'EU', 'IL'))
        previous = self._rights_assessment.get(key)
        synthetic_person_media = bool(previous and previous.required_disclosures)
        records = self._rights_evidence.get(key, [])
        assessment = self.rights.assess(
            prompt, target_markets=markets, evidence=records,
            synthetic_person_media=synthetic_person_media,
        )
        self._rights_assessment[key] = assessment
        current = self.engine.workspace.current(key)
        if current is not None:
            repo = apply_patch(
                current.repository(),
                [FilePatch(path=p, content=c) for p, c in self.rights.repository_files(assessment, original_prompt=prompt).items()],
            )
            self.engine.workspace.commit(project_id=key, repository=repo, message='V27 rights evidence/review update')
        return assessment

    def add_rights_evidence(
        self,
        *,
        token: str,
        project_id: str,
        right_kind: str,
        subject: str,
        evidence_type: str,
        scope: str,
        source_reference: str = '',
        verified: bool = False,
    ) -> dict:
        _, key = self._key(token=token, project_id=project_id)
        try:
            kind = RightKind(right_kind)
        except ValueError as exc:
            raise ValueError(f'unsupported right_kind: {right_kind}') from exc
        records = self._rights_evidence.setdefault(key, [])
        record = RightsEvidence(
            id=f'evidence-{len(records)+1:03d}',
            right_kind=kind,
            subject=subject.strip(),
            evidence_type=evidence_type.strip(),
            scope=scope.strip(),
            source_reference=source_reference.strip(),
            verified=bool(verified),
        )
        if not record.subject or not record.evidence_type or not record.scope:
            raise ValueError('subject, evidence_type and scope are required')
        records.append(record)

        self._refresh_rights_manifest(key=key)
        return {'record': record.to_dict(), 'rights': self.rights_status(token=token, project_id=project_id)}

    def verify_rights_evidence(self, *, token: str, project_id: str, evidence_id: str) -> dict:
        _, key = self._key(token=token, project_id=project_id)
        records = self._rights_evidence.get(key, [])
        for i, record in enumerate(records):
            if record.id == evidence_id:
                verified = RightsEvidence(
                    id=record.id, right_kind=record.right_kind, subject=record.subject,
                    evidence_type=record.evidence_type, scope=record.scope,
                    source_reference=record.source_reference, verified=True,
                )
                records[i] = verified
                self._refresh_rights_manifest(key=key)
                return {'record': verified.to_dict(), 'rights': self.rights_status(token=token, project_id=project_id)}
        raise KeyError(evidence_id)

    def original_alternative(self, *, token: str, project_id: str, prompt: str | None = None) -> dict:
        _, key = self._key(token=token, project_id=project_id)
        source = prompt or self._rights_prompt.get(key)
        if not source:
            raise ValueError('no source prompt available')
        return self.rights.originalize(source)

    def promote(self, *, token: str, project_id: str, version_id: str | None = None) -> dict:
        account, key = self._key(token=token, project_id=project_id)
        assessment = self._rights_assessment.get(key)
        if assessment is None:
            raise PermissionError('rights assessment required before publish')
        if not assessment.publish_allowed:
            raise PermissionError(f'rights publish gate blocked: {assessment.status.value}')
        snap = self.engine.promote(project_id=key, version_id=version_id)
        return {
            'deployment_id': snap.deployment_id,
            'project_id': project_id,
            'owner_id': account.id,
            'version_id': snap.version_id,
            'repository_checksum': snap.repository_checksum,
            'rights_gate': assessment.status.value,
        }

    def company_operating_system(self) -> dict:
        return {
            'model': 'one-founder / automated departments',
            'departments': self.company_os.departments(),
            'release_council': self.company_os.release_council(),
            'daily_loop': list(self.company_os.daily_loop()),
        }
