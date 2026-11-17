"""DECISIONS 8 (the owner 2026-11-17): the repairer may fix an EXPECTED VALUE in a test the builder wrote in this build;
a test of the customer's phone, price, address or hours is never edited; every edit is counted; the same value fixed
twice escalates. Real loop (AutonomousProductEngine), fake model and sandbox."""
from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import parse_patch
from omni_prod.test_edit_guard import customer_facts, judge

PROMPT = 'אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456. פתוח א׳–ה׳ 07:00–19:00. סטייק 89 ₪.'
TEST = ('import app\n\ndef test_title():\n    assert app.TITLE == "Butcher"\n\n'
        'def test_phone():\n    assert "04-8123456" in app.page()\n')
APP = 'TITLE = "Butcher shop"\ndef page(): return "048123456"\n'
FACTS = customer_facts(PROMPT)


def _engine(repairs, passing):
    class Architect:
        def create_spec(self, prompt): return 'spec'

    class Generator:
        def generate(self, spec):
            return parse_patch({'files': [{'path': 'app.py', 'content': APP}, {'path': 'tests/test_app.py', 'content': TEST}]})

    class Repairer:
        def __init__(self): self.seen = []
        def repair(self, *, spec, repo_summary, failures):
            self.seen.append(failures)
            files = repairs.pop(0) if repairs else [{'path': 'app.py', 'content': APP + f'#{len(self.seen)}'}]
            return parse_patch({'files': files})

    class Executor:
        def __init__(self): self.runs = []
        def execute(self, *, repository, spec):
            self.runs.append(dict(repository))
            if passing(repository):
                return ExecutionReport(True)
            return ExecutionReport(False, (AcceptanceFailure('A1', f'fail {len(self.runs)}'),))

    rep, ex = Repairer(), Executor()
    eng = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=rep, executor=ex,
                                  max_repair_rounds=4)
    return eng, rep, ex


def test_facts_come_from_the_customer_words():
    assert '048123456' in FACTS.phones and '07:00' in FACTS.hours and '89' in FACTS.prices and 'הרצל' in FACTS.streets


def test_expected_value_fix_is_allowed_and_counted():
    fixed = TEST.replace('== "Butcher"', '== "Butcher shop"')
    eng, _, ex = _engine([[{'path': 'tests/test_app.py', 'content': fixed}]],
                         lambda r: '"Butcher shop"' in r['tests/test_app.py'])
    result = eng.build(PROMPT)
    assert result.status == 'ready'
    assert ex.runs[-1]['tests/test_app.py'] == fixed
    ev = eng.test_edits.evidence()
    assert ev['counted'] == 1 and ev['edits'][0]['old'] == ['"Butcher"']


def test_a_test_of_the_customer_phone_is_never_edited():
    bent = TEST.replace('"04-8123456" in', '"048123456" in')
    eng, rep, ex = _engine([[{'path': 'tests/test_app.py', 'content': bent}, {'path': 'app.py', 'content': APP + '#1'}],
                            [{'path': 'app.py', 'content': APP + '#2'}]], lambda r: False)
    eng.build(PROMPT)
    assert all(run['tests/test_app.py'] == TEST for run in ex.runs)
    assert eng.test_edits.refused and 'phone' in eng.test_edits.refused[0]['reason']
    assert any(f.get('acceptance_id') == 'TEST_EDIT_REVERTED' for f in rep.seen[1])


def test_removing_an_assert_is_reverted():
    weaker = TEST.replace('    assert app.TITLE == "Butcher"\n', '')
    eng, _, ex = _engine([[{'path': 'tests/test_app.py', 'content': weaker}, {'path': 'app.py', 'content': APP + '#'}]],
                         lambda r: False)
    eng.build(PROMPT)
    assert all(run['tests/test_app.py'] == TEST for run in ex.runs)


def test_rewriting_an_assert_is_reverted():
    v = judge(TEST, TEST.replace('app.TITLE == "Butcher"', 'app.TITLE != "Butcher"'), FACTS)
    assert not v.allowed and 'rewritten' in v.reason


def test_same_value_fixed_twice_escalates():
    one = TEST.replace('== "Butcher"', '== "Butcher shop"')
    two = TEST.replace('== "Butcher"', '== "The butcher"')
    eng, _, _ = _engine([[{'path': 'tests/test_app.py', 'content': one}],
                         [{'path': 'tests/test_app.py', 'content': two}], [{'path': 'app.py', 'content': 'x'}]],
                        lambda r: False)
    result = eng.build(PROMPT)
    assert result.stop_reason == 'test_value_fixed_twice'
    assert eng.test_edits.evidence()['escalated']


def test_a_test_the_builder_did_not_write_is_reverted():
    from omni_prod.test_edit_guard import TestEditLedger
    ledger = TestEditLedger(frozenset(), FACTS)
    out, notes = ledger.review({'tests/t.py': 'def test():\n    assert a == 1\n'},
                               {'tests/t.py': 'def test():\n    assert a == 2\n'})
    assert out['tests/t.py'].endswith('== 1\n') and notes and not ledger.counted
