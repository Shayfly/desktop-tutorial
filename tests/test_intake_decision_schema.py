"""IntakeDecision v1 (docs/design/intake-decision-schema.md, signed by Michael 2026-11-11 with F1-F6, G1, G2)."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from omni_prod.intake import decision as D

ROOT = Path(__file__).resolve().parents[1]
RAW = 'תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים". שיהיה כפתור להתקשר וכפתור וואטסאפ.'
A1 = D.new_artifact_id(now_ms=1_762_860_000_000, randomness=bytes(range(10)))
A2 = D.new_artifact_id(now_ms=1_762_860_000_001, randomness=bytes(range(10, 20)))

BTN = dict(conf='stated', src='customer', via='button')
TXT = dict(conf='stated', src='customer', via='text')


def complete_site(**over) -> D.IntakeDecision:
    art = D.ArtifactIntent(
        id=A1, kind=D.Field('site', **BTN), purpose=D.Field('דף לחנות פרחים', **TXT),
        audience=D.Field('לקוחות', **TXT), must_include=D.Field(['שעות', 'זרים'], **TXT),
        persistence=D.Field('none', **BTN), requires_auth=D.Field(False, **BTN), personal_data=D.Field('no', **BTN))
    dec = D.IntakeDecision(raw_brief=RAW, raw_brief_sha256=D.sha256(RAW), artifacts=(art,),
                           shared=D.Shared(tone=D.Field('חם', **TXT), brand_name=D.Field('שושנת העמקים', **TXT)))
    return replace(dec, **over)


def codes(violations):
    return sorted({(v.code, v.where) for v in violations})


class Ids(unittest.TestCase):
    def test_art_ulid_crockford_26_sortable(self):
        self.assertTrue(D.is_artifact_id(A1))
        self.assertEqual(len(A1), 30)
        self.assertLess(A1, A2)                                  # time-ordered
        self.assertNotEqual(D.new_artifact_id(), D.new_artifact_id())
        for bad in ('art_' + 'I' * 26, 'art_' + '0' * 25, 'xyz_' + A1[4:], 'art_8' + A1[5:]):
            self.assertFalse(D.is_artifact_id(bad), bad)


class Validation(unittest.TestCase):
    def test_a_complete_decision_is_valid(self):
        self.assertEqual(D.validate(complete_site(), revision_raw_brief=RAW), [])

    # ---- G2: stated only by a button; never a button for a fact ----
    def test_a_decision_stated_from_free_text_is_rejected(self):
        dec = complete_site()
        art = replace(dec.artifacts[0], persistence=D.Field('none', **TXT))      # "דף סטטי" typed, not pressed
        v = D.validate(replace(dec, artifacts=(art,)))
        self.assertIn(('SCHEMA', f'{A1}.persistence'), codes(v))
        self.assertTrue(all(x.stop for x in v))

    def test_a_decision_stated_by_extraction_or_the_model_is_rejected(self):
        dec = complete_site()
        for via in ('extract', None):
            with self.subTest(via=via):
                art = replace(dec.artifacts[0], kind=D.Field('site', conf='stated', src='customer', via=via))
                self.assertIn(('SCHEMA', f'{A1}.kind'), codes(D.validate(replace(dec, artifacts=(art,)))))

    def test_a_fact_set_by_a_button_is_rejected(self):
        dec = complete_site()
        art = replace(dec.artifacts[0], purpose=D.Field('דף', **BTN))
        self.assertIn(('SCHEMA', f'{A1}.purpose'), codes(D.validate(replace(dec, artifacts=(art,)))))

    def test_inferred_never_from_the_customer(self):
        dec = complete_site()
        art = replace(dec.artifacts[0], kind=D.Field('site', conf='inferred', src='customer', via='text'))
        self.assertIn(('SCHEMA', f'{A1}.kind'), codes(D.validate(replace(dec, artifacts=(art,)))))

    # ---- F5: the library exception is an explicit allow-list ----
    def test_library_fixed_persistence_only_for_song_and_video(self):
        song = D.ArtifactIntent(id=A2, kind=D.Field('song', **BTN), purpose=D.Field('שיר רקע', **TXT),
                                persistence=D.Field('none', conf='stated', src='library', via='extract'),
                                song=D.SongIntent())
        dec = complete_site()
        self.assertEqual([x for x in D.validate(replace(dec, artifacts=dec.artifacts + (song,))) if x.stop], [])
        site = replace(dec.artifacts[0], persistence=D.Field('none', conf='stated', src='library', via='extract'))
        self.assertIn(('SCHEMA', f'{A1}.persistence'), codes(D.validate(replace(dec, artifacts=(site,)))))
        auth = replace(song, requires_auth=D.Field(False, conf='stated', src='library', via='extract'))
        self.assertIn(('SCHEMA', f'{A2}.requires_auth'), codes(D.validate(replace(dec, artifacts=(dec.artifacts[0], auth)))))

    # ---- F2 / V1: rawBrief ----
    def test_a_decision_attached_to_another_revision_is_rejected(self):
        self.assertIn(('SCHEMA', 'raw_brief'), codes(D.validate(complete_site(), revision_raw_brief=RAW + ' עם הרשמה')))

    def test_raw_brief_is_immutable_and_its_hash_is_checked(self):
        prev = complete_site()
        changed = replace(prev, raw_brief=RAW + '!', raw_brief_sha256=D.sha256(RAW + '!'))
        self.assertIn(('SCHEMA', 'raw_brief'), codes(D.validate(changed, previous=prev)))
        self.assertIn(('SCHEMA', 'raw_brief'), codes(D.validate(replace(prev, raw_brief=RAW + '!'))))

    # ---- V5 / V6 / V9 ----
    def test_structure(self):
        dec = complete_site()
        self.assertIn(('SCHEMA', 'artifacts'), codes(D.validate(replace(dec, artifacts=()))))
        self.assertIn(('SCHEMA', 'artifacts'), codes(D.validate(replace(dec, artifacts=dec.artifacts * 2))))
        stray = replace(dec.artifacts[0], game=D.GameIntent())
        self.assertIn(('SCHEMA', f'{A1}.game'), codes(D.validate(replace(dec, artifacts=(stray,)))))

    def test_game_genre_is_closed_seven(self):
        self.assertEqual(len(D.GAME_GENRES), 7)
        game = D.ArtifactIntent(id=A1, kind=D.Field('game', **BTN),
                                game=D.GameIntent(genre=D.Field('racing', **BTN)))
        dec = complete_site()
        self.assertIn(('SCHEMA', f'{A1}.game.genre'), codes(D.validate(replace(dec, artifacts=(game,)))))

    def test_agent_skills_are_checked_against_the_registry(self):
        agent = D.ArtifactIntent(id=A1, kind=D.Field('agent', **BTN),
                                 agent=D.AgentIntent(skills=D.Field(['skill.copy_quality', 'skill.nope'], **TXT)))
        dec = replace(complete_site(), artifacts=(agent,))
        self.assertIn(('SCHEMA', f'{A1}.agent.skills'), codes(D.validate(dec, skill_ids={'skill.copy_quality'})))

    # ---- F6: 2 = report, 3 = stop ----
    def test_asked_twice_is_reported_three_times_stops(self):
        dec = complete_site()
        two = D.validate(replace(dec, gaps=(D.Gap(f'{A1}.persistence', 'build', 'customer', asked_count=2),)))
        self.assertEqual([(x.code, x.stop) for x in two], [('GapAskedTwice', False)])
        three = D.validate(replace(dec, gaps=(D.Gap(f'{A1}.persistence', 'build', 'customer', asked_count=3),)))
        self.assertEqual([(x.code, x.stop) for x in three], [('GapStuck', True)])

    def test_a_gap_on_a_field_that_does_not_exist(self):
        dec = replace(complete_site(), gaps=(D.Gap('art_nope.kind', 'build', 'customer'),))
        self.assertIn(('SCHEMA', 'art_nope.kind'), codes(D.validate(dec)))


class GapDerivation(unittest.TestCase):
    """G1: a known missing set gives EXACTLY the expected gaps; a complete decision gives zero."""

    def test_complete_gives_zero(self):
        self.assertEqual(D.derive_gaps(complete_site()), ())
        self.assertTrue(D.handoff_ready(complete_site()))

    def test_known_missing_set_gives_exactly_these_gaps(self):
        dec = complete_site()
        art = replace(dec.artifacts[0], kind=D.Field('site', conf='inferred', src='rawBrief', via='extract'),
                      persistence=D.MISSING, purpose=D.MISSING)
        dec = replace(dec, artifacts=(art,), shared=replace(dec.shared, tone=D.MISSING))
        got = {(g.field, g.blocks, g.trigger) for g in D.derive_gaps(dec)}
        self.assertEqual(got, {(f'{A1}.kind', 'build', 'missing'),          # inferred is not confirmed (§12)
                               (f'{A1}.persistence', 'build', 'missing'),
                               (f'{A1}.purpose', 'approval', 'missing'),
                               ('shared.tone', 'nothing', 'missing')})
        self.assertFalse(D.handoff_ready(replace(dec, gaps=D.derive_gaps(dec))))

    def test_stale_and_asked_counts_are_kept(self):
        dec = replace(complete_site(), gaps=(D.Gap(f'{A1}.persistence', 'build', 'customer', asked_count=1),))
        gaps = D.derive_gaps(dec, stale=frozenset({f'{A1}.persistence'}))
        self.assertEqual([(g.field, g.trigger, g.asked_count) for g in gaps], [(f'{A1}.persistence', 'stale', 1)])

    def test_a_song_asks_neither_sign_in_nor_personal_data(self):
        song = D.ArtifactIntent(id=A2, kind=D.Field('song', **BTN), purpose=D.Field('שיר', **TXT),
                                persistence=D.Field('none', conf='stated', src='library', via='extract'),
                                song=D.SongIntent())
        dec = replace(complete_site(), artifacts=(song,))
        self.assertEqual(D.derive_gaps(dec), ())

    def test_identity_store_is_project_level_and_derived(self):
        dec = complete_site()
        self.assertEqual(dec.identity_store, 'none')
        a = replace(dec.artifacts[0], requires_auth=D.Field(True, **BTN))
        b = replace(a, id=A2)
        self.assertEqual(replace(dec, artifacts=(a, b)).identity_store, 'project')   # two need it: ONE store


class GeneratedSchema(unittest.TestCase):
    def test_committed_schema_is_generated_no_drift(self):
        committed = json.loads((ROOT / D.SCHEMA_PATH).read_text(encoding='utf-8'))
        self.assertEqual(committed, D.json_schema(), 'run: python -m omni_prod.intake.decision --write')

    def test_a_valid_decision_round_trips_through_the_schema(self):
        import jsonschema
        data = D.to_dict(complete_site())
        jsonschema.validate(data, D.json_schema())
        self.assertEqual(D.from_dict(json.loads(json.dumps(data))), complete_site())

    def test_the_schema_refuses_shape_errors(self):
        import jsonschema
        data = D.to_dict(complete_site())
        data['artifacts'][0]['kind']['conf'] = 'sure'
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(data, D.json_schema())


if __name__ == '__main__':
    unittest.main()
