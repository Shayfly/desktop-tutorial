"""Registry Auditor (founder Agent OS spec 2026-10-08, step 1)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import registry_audit as ra
from omni_prod.agent_catalog import BY_KEY, CATALOG
from omni_prod.runtime_bindings import BINDINGS, Binding, Evidence, Requirement


class CatalogAndBindingTests(unittest.TestCase):
    def test_every_spec_family_is_registered(self):
        self.assertEqual({r.family for r in CATALOG},
                         {'management', 'software', 'quality', 'assets', 'media', 'games', 'automation', 'platform'})
        self.assertGreaterEqual(len(CATALOG), 49)

    def test_bindings_point_at_catalog_roles_and_real_code(self):
        for b in BINDINGS:
            self.assertIn(b.role, BY_KEY, b.role)
            for target in b.implementation:
                self.assertTrue(ra._importable(target), target)

    def test_live_evidence_always_has_an_id(self):
        for b in BINDINGS:
            for e in b.evidence:
                self.assertIn(e.kind, ('live', 'unit'))
                self.assertTrue(e.ref.strip(), b.role)


class LifecycleTests(unittest.TestCase):
    role = BY_KEY['qa_verifier']

    def _row(self, binding, env=None, registry=None, lock=None):
        with mock.patch.dict(ra.BY_ROLE, {self.role.key: binding}, clear=False):
            return ra.audit_role(self.role, env or {}, registry, lock if lock is not None else {})

    def test_unbound_role_is_only_defined(self):
        with mock.patch.dict(ra.BY_ROLE, {}, clear=True):
            row = ra.audit_role(self.role, {}, 'PARTIAL')
        self.assertEqual(row.lifecycle, ra.DEFINED)
        self.assertTrue(any('no code on a runtime path' in i for i in row.issues))

    def test_code_without_live_evidence_is_never_verified(self):
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web', (), (Evidence('unit', 't.py'),))
        self.assertEqual(self._row(b).lifecycle, ra.CONNECTED)
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web')
        self.assertEqual(self._row(b).lifecycle, ra.IMPLEMENTED)

    def _fresh_lock(self, commit='abc1234'):
        return {f'{commit}|omni_prod/registry_audit.py': ra._current_digest('omni_prod/registry_audit.py')}

    def test_missing_configuration_blocks_and_names_it(self):
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web', (Requirement(('SOME_KEY',)),),
                    (Evidence('live', 'run 1', commit='abc1234', asserts=('x works',)),), verified_scope=('x works',))
        row = self._row(b, env={})
        self.assertEqual(row.lifecycle, ra.BLOCKED)
        self.assertIn('SOME_KEY: MISSING', row.configuration)
        self.assertEqual(self._row(b, env={'SOME_KEY': 'x'}, lock=self._fresh_lock()).lifecycle, ra.VERIFIED)

    def test_verified_names_its_scope_and_goes_stale_when_code_changes(self):
        """Directive 2026-10-09 §6: VERIFIED is scoped, and a code change
        after the run makes it STALE ("has a run id" is not enough)."""
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web', (),
                    (Evidence('live', 'run 7', commit='abc1234', asserts=('forms submit twice',)),), verified_scope=('forms',))
        fresh = self._row(b, lock=self._fresh_lock())
        self.assertEqual(fresh.lifecycle, ra.VERIFIED)
        self.assertIn('VERIFIED for: forms submit twice', fresh.verification)
        stale = self._row(b, lock={'abc1234|omni_prod/registry_audit.py': 'different'})
        self.assertEqual(stale.lifecycle, ra.STALE)
        self.assertIn('code changed since: omni_prod/registry_audit.py', stale.verification)
        unknown = self._row(b, lock={})
        self.assertEqual(unknown.lifecycle, ra.STALE)
        self.assertIn('freshness unknown', unknown.verification)

    def test_checkout_line_endings_do_not_stale_live_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'module.py'
            source.write_bytes(b'first line\r\nsecond line\r\n')
            binding_files = ('module.py',)
            evidence = Evidence('live', 'run 8', commit='abc1234')
            lock = {'abc1234|module.py': ra._digest(b'first line\nsecond line\n')}
            with mock.patch.object(ra, 'ROOT', Path(root)):
                self.assertEqual(ra.freshness(evidence, binding_files, lock), ('fresh', ()))

    def test_run_id_without_commit_is_never_verified(self):
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web', (), (Evidence('live', 'run 1'),))
        self.assertNotEqual(self._row(b, lock=self._fresh_lock()).lifecycle, ra.VERIFIED)

    def test_broken_implementation_is_flagged_not_trusted(self):
        b = Binding(self.role.key, ('omni_prod.nope:Gone',), 'web', (), (Evidence('live', 'run 1'),))
        row = self._row(b)
        self.assertEqual(row.lifecycle, ra.DEFINED)
        self.assertTrue(any('does not import' in i for i in row.issues))

    def test_registry_live_without_evidence_is_a_mismatch(self):
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web')
        self.assertTrue(any('no fresh live evidence' in i for i in self._row(b, registry='LIVE').issues))


class DirectiveCatalogTests(unittest.TestCase):
    def test_twelve_directive_roles_are_registered(self):
        for key in ('discovery_lead', 'requirements_traceability_auditor', 'brand_design_director',
                    'accessibility_localization_reviewer', 'integration_secret_steward', 'reliability_recovery_engineer',
                    'performance_resource_engineer', 'release_change_coordinator', 'privacy_ip_steward',
                    'customer_success_handover', 'product_economics_analyst', 'partner_readiness_reviewer'):
            self.assertIn(key, BY_KEY)
        self.assertEqual(len(CATALOG), 61)

    def test_every_section_9_skill_has_a_kind_and_an_explicit_status(self):
        from omni_prod.skill_catalog import CATALOG as SKILLS
        rows = ra.catalog_skill_rows()
        self.assertEqual(len(rows), len(SKILLS))
        for key in ('intent.parse', 'approval.bind', 'browser.flow.verify', 'deployment.publish', 'budget.reserve',
                    'video.generate', 'game.playtest', 'registry.audit'):
            self.assertIn(key, {r[0] for r in rows})
        for r in rows:
            self.assertIn(r[2], ('INSTRUCTION', 'EXECUTABLE', 'VALIDATOR', 'WORKFLOW'), r[0])
            self.assertIn(r[3], ra.ORDER, r[0])
        by = {r[0]: r for r in rows}
        self.assertEqual(by['deployment.publish'][3], ra.NOT_IMPLEMENTED)
        self.assertEqual(by['video.generate'][3], ra.NOT_IMPLEMENTED)
        self.assertNotEqual(by['image.generate'][3], ra.VERIFIED)  # Replicate auth is not image generation

    def test_older_registry_has_no_partial_skill_off_the_web_path(self):
        from omni_prod.skills_registry import build_canonical_skills_registry
        partial = [s.key for s in build_canonical_skills_registry().all() if s.status.value == 'PARTIAL']
        self.assertFalse([k for k in partial if k.startswith(('skill.media.', 'skill.integration.', 'skill.target.android',
                                                              'skill.target.ios', 'skill.target.game'))], partial)


class ReportTests(unittest.TestCase):
    def test_committed_status_document_is_current(self):
        path = Path(__file__).resolve().parents[1] / 'docs' / 'AGENT_SKILL_STATUS.md'
        expected = ra.markdown(ra.audit({}), ra.skill_registry_findings()) + '\n'
        self.assertEqual(path.read_text(encoding='utf-8'), expected,
                         'run: python -m omni_prod.registry_audit --write')

    def test_nothing_outside_the_web_path_is_verified(self):
        rows = {r.role.key: r for r in ra.audit({})}
        for key in ('game_designer', 'video_creator', 'automation_designer', 'agent_app_builder', 'release_agent'):
            self.assertEqual(rows[key].lifecycle, ra.DEFINED, key)
        self.assertNotEqual(rows['visual_creator'].lifecycle, ra.VERIFIED)


if __name__ == '__main__':
    unittest.main()
