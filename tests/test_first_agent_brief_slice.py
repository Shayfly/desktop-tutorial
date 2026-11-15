"""First agent, slice 3 (Michael 2026-11-15, option A with five conditions):
1. Brief gains `structure` additively (field, to_dict, from_dict).
2. Existing briefs keep their fingerprints: the four production briefs committed as fixtures (butcher rev 8 and 4,
   the served butcher page's brief, the cafe) recompute to their stored fingerprint. (All 225 production briefs were
   recomputed on 2026-11-15 against this branch: 225/225 equal to the stored fingerprint -- PR description.)
3. The structure is in the fingerprint an approval binds.
4. A write touches only `structure` and `fields.references` -- anything else raises and nothing is saved.
Reversible: write() returns `undo`; revert() writes it back as one more revision (an in-memory repository with the
real BriefRepository compare-and-set contract here; the Postgres repository in test_first_agent_brief_slice_pg.py)."""
import json
import unittest
from dataclasses import replace
from pathlib import Path

from omni_prod.brief_repository import BriefRow, StaleBrief
from omni_prod.discovery import Brief
from omni_prod.first_agent import brief_slice as BS
from omni_prod.first_agent.structure import build_card
from omni_prod.fact_canon import build_canon

FIX = Path(__file__).resolve().parent / 'fixtures'


def production_briefs():
    out = []
    b = json.loads((FIX / 'butcher_prj_fV8kB7FwuNimGw.json').read_text())
    out += [(b['brief'], b['fingerprint']), (b['revision_4']['brief'], b['revision_4']['fingerprint'])]
    c = json.loads((FIX / 'cafe_prj_tEyyuyyWNZRpiw.json').read_text())
    out.append((c['brief'], c['fingerprint']))
    s = json.loads((FIX / 'butcher_served_page_2026_11_14.json').read_text())
    out.append((s['brief'], s['brief_fingerprint']))
    return out


class MemoryBriefs:
    """The BriefRepository contract: immutable revisions, compare-and-set on expected_revision."""
    def __init__(self, brief):
        self.rows = [BriefRow('brf_1', 'prj', 1, brief, True, brief.fingerprint())]

    def latest(self, project_id):
        return self.rows[-1]

    def save(self, *, project_id, account_id, brief, expected_revision, request_key=None):
        if self.rows[-1].revision != expected_revision:
            raise StaleBrief('changed')
        row = BriefRow(f'brf_{expected_revision + 1}', project_id, expected_revision + 1, brief, True, brief.fingerprint())
        self.rows.append(row)
        return row


BUTCHER = Brief.from_dict(production_briefs()[0][0])
CARD = build_card(BUTCHER.prompt, canon=build_canon(BUTCHER.prompt), vertical='butcher')


class ExistingBriefsDoNotMove(unittest.TestCase):
    def test_every_committed_production_brief_keeps_its_fingerprint(self):
        for data, stored in production_briefs():
            brief = Brief.from_dict(data)
            self.assertEqual(brief.fingerprint(), stored)
            self.assertNotIn('structure', brief.to_dict())          # absent, not empty: the hashed dict is unchanged

    def test_a_round_trip_keeps_the_structure(self):
        b = replace(BUTCHER, structure=[CARD])
        self.assertEqual(Brief.from_dict(b.to_dict()).structure, [CARD])


class TheApprovalBindsTheStructure(unittest.TestCase):
    def test_a_different_structure_is_a_different_fingerprint(self):
        a = BS.with_slice(BUTCHER, structure=[CARD])
        moved = dict(CARD, rows=list(reversed(CARD['rows'])))
        b = BS.with_slice(BUTCHER, structure=[moved])
        self.assertNotEqual(a.fingerprint(), BUTCHER.fingerprint())
        self.assertNotEqual(a.fingerprint(), b.fingerprint())


class OnlyTheSlice(unittest.TestCase):
    def test_structure_and_references_are_written(self):
        out = BS.with_slice(BUTCHER, structure=[CARD], references='https://example.com/butcher')
        self.assertEqual(out.structure, [CARD])
        self.assertEqual(out.fields['references']['value'], 'https://example.com/butcher')

    def test_anything_else_raises(self):
        for other in (replace(BUTCHER, prompt=BUTCHER.prompt + ' ועוד'),
                      replace(BUTCHER, fields={**BUTCHER.fields, 'color': {'value': 'red'}}),
                      replace(BUTCHER, skipped=['logo'])):
            with self.assertRaises(BS.SliceViolation):
                BS.slice_only(BUTCHER, other)


class Reversible(unittest.TestCase):
    def test_write_then_revert_restores_the_previous_values_as_a_new_revision(self):
        repo = MemoryBriefs(BUTCHER)
        before = BS.current_slice(BUTCHER)
        w = BS.write(repo, project_id='prj', account_id='usr', structure=[CARD], references='קישור לאטליז אהוב')
        self.assertEqual(w['row'].revision, 2)
        self.assertEqual(w['undo'], {'revision': 1, **before})
        r = BS.revert(repo, project_id='prj', account_id='usr', undo=w['undo'])
        self.assertEqual(r['row'].revision, 3)                               # one more revision, nothing deleted
        self.assertEqual(BS.current_slice(repo.latest('prj').brief), before)
        self.assertEqual(repo.latest('prj').brief.fingerprint(), BUTCHER.fingerprint())   # back to the same brief
        self.assertEqual([row.revision for row in repo.rows], [1, 2, 3])

    def test_a_concurrent_write_is_refused_not_overwritten(self):
        repo = MemoryBriefs(BUTCHER)
        stale = repo.latest('prj')
        BS.write(repo, project_id='prj', account_id='usr', references='a')
        repo.latest = lambda project_id: stale                               # this writer read revision 1
        with self.assertRaises(StaleBrief):
            BS.write(repo, project_id='prj', account_id='usr', references='b')


if __name__ == '__main__':
    unittest.main()
