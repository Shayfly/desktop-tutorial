"""Every failed check the executor chain can produce has exactly one owner on the content route (the CTO's decision 5).

The ids are not typed here: they are READ from the code that produces them -- every unit of every gate the worker
installs (skill_units/gate.WORKER_GATES), every failure-id constant in omni_prod (`*_FAILURE_ID`, `ACCEPTANCE_ID`,
`ACCEPTANCE_PREFIX`, ...), the spec requirement ids the worker's wrappers add, the layer suffixes of the post-build group.
A new gate or a new failure id with no owner in site_content/owners.OWNER fails this test: there is no default bucket.
"""
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod.site_content import owners as O
from omni_prod.skill_units.gate import WORKER_GATES, gate_units

ROOT = Path(__file__).resolve().parent.parent
_CONSTANT = re.compile(r"^(?:[A-Z_]*FAILURE_ID|ACCEPTANCE_ID|ACCEPTANCE_PREFIX|MAIN_ACCEPTANCE_ID|UNSUPPORTED_DEPENDENCY|"
                       r"PLAN_WEAKENED_ID|SUMMARY_FAILURE_ID|UNSPECIFIED_ROUND_FAILURE_ID|REQUIREMENT|"
                       r"FACTS_REQUIREMENT|CONTRACT_REQUIREMENT|RULES_REQUIREMENT)\s*=\s*'([^']+)'", re.M)
# ids written inline where they are raised (not as a constant)
_INLINE = {'uploaded-logo': 'omni_prod/uploaded_assets.py', 'NO_PROGRESS': 'omni_prod/autonomous_core.py',
           'TEST_EDIT_REVERTED': 'omni_prod/autonomous_core.py', 'REPAIR_REGRESSION': 'omni_prod/autonomous_core.py',
           'accept-': 'omni_prod/product_architect.py'}


def group_layers() -> tuple[str, ...]:
    """The layer ids the post-build group gives its stages (verification_group.layer_id), READ from the production
    chain itself (investor_app._verification_executor, with every flag that adds a stage switched on): a crash, an
    empty or a contradictory report of a stage is '<layer>_EXCEPTION' / '_unspecified' / '_contradictory'."""
    from omni_prod import feature_flags, investor_app
    from omni_prod.behavior_acceptance import find_in_chain
    from omni_prod.verification_group import VerificationGroup, layer_id
    env = {'OMNI_SANDBOX_RUNNER_URL': 'http://local-sandbox.invalid', 'OMNI_SANDBOX_SHARED_SECRET': 'l' * 40}
    with mock.patch.dict(os.environ, env), mock.patch.object(feature_flags, 'SITE_AUTH_V2', True):
        chain = investor_app._verification_executor(object())
    group = find_in_chain(chain, VerificationGroup)
    return tuple(layer_id(stage) for stage in group._stages)


def produced_ids() -> dict[str, str]:
    """{acceptance id: where it is produced}"""
    out = {}
    for path in sorted((ROOT / 'omni_prod').rglob('*.py')):
        rel = str(path.relative_to(ROOT))
        if rel.startswith(('omni_prod/intake/', 'omni_prod/site_content/')):
            continue                                   # the intake's ids are conversation ids, not checks
        for m in _CONSTANT.finditer(path.read_text(encoding='utf-8')):
            out.setdefault(m.group(1), rel)
    for g in WORKER_GATES:
        for unit in gate_units(g):
            out[f'gate-{g}-{unit}'] = f'skill_units/{unit}'
    for aid, rel in _INLINE.items():
        source = (ROOT / rel).read_text(encoding='utf-8')
        if aid not in source:
            raise AssertionError(f'{aid!r} is no longer produced in {rel}: update this test')
        out[aid] = rel
    for layer in group_layers():
        out[layer] = 'verification_group (the stage itself)'
        for suffix in O.LAYER_SUFFIXES:
            out[layer + suffix] = 'verification_group / verification_verdict'
    out['window-legal_cookies'] = 'window_catalog (a window id after the prefix)'
    out['accept-site-content'] = 'product_architect._content_only_spec'
    out['gate-SITE_CLAIMS'] = out['gate-SITE_PARITY'] = 'site_content'
    return out


class EveryCheckHasAnOwner(unittest.TestCase):
    maxDiff = None

    def test_every_id_the_chain_can_produce_has_an_owner(self):
        ids = produced_ids()
        self.assertGreaterEqual(len(ids), 60)
        unowned = {}
        for aid, where in sorted(ids.items()):
            try:
                owner = O.owner_of(aid)
            except O.Unowned:
                unowned[aid] = where
                continue
            self.assertIn(owner, O.OWNERS + (O.BY_FINDING,), aid)
        self.assertEqual(unowned, {})

    def test_the_group_names_every_stage_the_chain_appends(self):
        layers = group_layers()
        self.assertEqual(layers, ('PREVIEW', 'BEHAVIOR', 'BROWSER', 'VISUAL', 'AUTHFORM', 'REVIEW'))
        self.assertEqual(O.owner_of('AUTHFORM_EXCEPTION'), 'platform')     # the sign-in check crashed: not the copy

    def test_the_table_names_only_the_four_owners(self):
        self.assertEqual({v for v in O.OWNER.values()} - set(O.OWNERS), {O.BY_FINDING})
        self.assertEqual([k for k, v in O.OWNER.items() if v == O.BY_FINDING], ['REVIEW'])

    def test_an_unknown_id_raises_and_never_falls_into_a_bucket(self):
        for aid in ('gate-NEWGATE-unit', 'SOMETHING_NEW', ''):
            with self.assertRaises(O.Unowned):
                O.owner_of(aid)

    def test_the_copy_gates_are_content_and_the_layout_gates_are_the_platforms(self):
        self.assertEqual({O.owner_of(f'gate-HE-{u}') for u in gate_units('HE')}, {'content'})
        self.assertEqual({O.owner_of(f'gate-G10-{u}') for u in gate_units('G10')}, {'content'})
        for g in ('G3', 'G4', 'G6', 'G11', 'G1', 'BRAND', 'SHARE', 'G5', 'PRO'):
            self.assertEqual({O.owner_of(f'gate-{g}-{u}') for u in gate_units(g)}, {'platform'}, g)
        self.assertEqual(O.owner_of('DESIGN'), 'advisory')
        self.assertEqual(O.owner_of('PREVIEW_EXCEPTION'), 'platform')

    def test_review_findings_the_reviewer_is_advisory_the_truth_gate_is_owned_by_rule(self):
        def owner(msg, source='static', listed=False):
            return O.review_owner(msg, source=source, missing_listed=listed)
        self.assertEqual(owner('QA review (spec): the hero is weak', 'reviewer'), 'advisory')
        self.assertEqual(owner('QA review (skill.copy_quality): facts the customer gave are missing from the page: x'),
                         'platform')
        invented = 'QA review (skill.copy_quality): contact details not in the approved request (invented): +97231'
        self.assertEqual(owner(invented, listed=True), 'customer')
        self.assertEqual(owner(invented, listed=False), 'platform')
        self.assertEqual(owner('QA review (skill.copy_quality): review/rating counts not in the approved request: 50'),
                         'content')
        self.assertEqual(owner('QA review (skill.rtl): the page has no dir'), 'platform')
        with self.assertRaises(O.Unowned):
            owner('QA review (x): y', source='unknown')


if __name__ == '__main__':
    unittest.main()
