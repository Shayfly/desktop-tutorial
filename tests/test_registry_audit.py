"""Registry Auditor (founder Agent OS spec 2026-10-08, step 1)."""
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

    def _row(self, binding, env=None, registry=None):
        with mock.patch.dict(ra.BY_ROLE, {self.role.key: binding}, clear=False):
            return ra.audit_role(self.role, env or {}, registry)

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

    def test_missing_configuration_blocks_and_names_it(self):
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web', (Requirement(('SOME_KEY',)),),
                    (Evidence('live', 'run 1'),))
        row = self._row(b, env={})
        self.assertEqual(row.lifecycle, ra.BLOCKED)
        self.assertIn('SOME_KEY: MISSING', row.configuration)
        self.assertEqual(self._row(b, env={'SOME_KEY': 'x'}).lifecycle, ra.VERIFIED)

    def test_broken_implementation_is_flagged_not_trusted(self):
        b = Binding(self.role.key, ('omni_prod.nope:Gone',), 'web', (), (Evidence('live', 'run 1'),))
        row = self._row(b)
        self.assertEqual(row.lifecycle, ra.DEFINED)
        self.assertTrue(any('does not import' in i for i in row.issues))

    def test_registry_live_without_evidence_is_a_mismatch(self):
        b = Binding(self.role.key, ('omni_prod.registry_audit:audit',), 'web')
        self.assertTrue(any('no live evidence' in i for i in self._row(b, registry='LIVE').issues))


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
