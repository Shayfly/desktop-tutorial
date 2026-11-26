"""Law 2 (2026-11-25): every GitHub Actions run cited as evidence is looked up and must be green on its commit.

Real path: the real script (scripts/resolve_evidence_runs.py), the real evidence records and string constants it reads
from the repository (22 run ids on 2026-11-25), the real known-red list (docs/evidence-runs-known-red.json) and the real
workflow file. Only the GitHub answer is replaced: `fetch` answers like GET /repos/{owner}/{repo}/actions/runs/{id}, and
one test goes through the real request code (the drill tool's github_get) with `urlopen` replaced. The default answer is
today's truth as read from GitHub on 2026-11-25: the four listed ids failed, the other 18 succeeded on the cited commit
in the workflow the text names. The guard tests build their own small omni_prod/ tree in a temp dir.
Mutations: tests/negative_controls/evidence_runs.json.

Review 2026-11-25 (three agents): each counter-example they reproduced is a test here -- the vision probe cited as a
plain string, five ways of building a record the guard did not see, a green run of another workflow accepted, the job
summary of CI filled with invented verdicts, a 404 reported as a plain red, and six mutations no test caught.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import textwrap
import urllib.error
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('resolve_evidence_runs', ROOT / 'scripts' / 'resolve_evidence_runs.py')
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)

WORKFLOW = ROOT / '.github' / 'workflows' / 'evidence-runs.yml'
LIST = ROOT / 'docs' / 'evidence-runs-known-red.json'
CITED, UNCITED = R.collect()

# The run ids cited on 2026-11-25, by the kind that alone cites them (a removed source loses its ids).
ONLY_REQUIREMENT = {'37739774562'}                      # runtime_bindings _MODEL.observed: deploy-worker run
ONLY_PROVIDER = {'39378559811'}                         # intelligence/inventory PAID_20261020
ONLY_TEXT = {'43657047045'}                             # vision_models._PROBE, a plain string
SUPPORTING = {'37955419872', '37962090098'}             # a later id in a record's text: green, commit not compared
# Red on GitHub on 2026-11-25 (read with GET /actions/runs/{id}): conclusion failure, all four.
KNOWN_RED = {'37814803770': 'model-probe', '37954236866': 'postdeploy-checks', '39377332673': 'postdeploy-checks',
             '43657047045': 'vision-probe'}


@pytest.fixture(autouse=True)
def _own_job_summary(tmp_path, monkeypatch):
    """Review 2026-11-25: the tests wrote ~20 tables of invented verdicts into the real $GITHUB_STEP_SUMMARY of CI
    (2 MB from the controls step, over GitHub's 1 MiB step limit). Every test here writes to its own temp file."""
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path / 'summary.md'))


def _workflow_of(run_id):
    named = [set(c.workflows) for c in CITED.get(run_id, []) if c.workflows]
    return sorted(set.intersection(*named))[0] if named else 'some-probe'


def green(run_id, head_sha=None, workflow=None):
    commits = [c.commit for c in CITED.get(run_id, []) if c.commit]
    sha = head_sha or ((commits[0] if commits else 'f') + '0' * 40)[:40]
    return {'id': int(run_id), 'status': 'completed', 'conclusion': 'success', 'head_sha': sha,
            'head_branch': 'main', 'path': f'.github/workflows/{workflow or _workflow_of(run_id)}.yml',
            'created_at': '2026-10-10T20:00:00Z', 'event': 'workflow_dispatch'}


def today(run_id):
    """GitHub's answer as read on 2026-11-25."""
    if run_id in KNOWN_RED:
        return dict(green(run_id, workflow=KNOWN_RED[run_id]), conclusion='failure')
    return green(run_id)


def run_main(capsys, answers=None, errors=None, known_red=LIST):
    """main() over every real cited id; `answers` / `errors` override today's answer of chosen ids."""
    answers, errors = answers or {}, errors or {}
    asked = []

    def fetch(run_id):
        asked.append(run_id)
        if run_id in errors:
            raise errors[run_id]
        return answers.get(run_id) or today(run_id)
    rc = R.main(['--repo', 'Shayfly/desktop-tutorial'], fetch=fetch, known_red=known_red)
    out = capsys.readouterr().out
    assert sorted(asked) == sorted(CITED)                 # every cited id was asked, once
    return rc, out


def lines(out, prefix):
    return [line for line in out.splitlines() if line.startswith(prefix)]


def error_for(out, run_id):
    found = [line for line in lines(out, '::error ') if line.startswith(f'::error title=evidence run {run_id}::')]
    assert len(found) == 1, out
    return found[0]


def known_list():
    return json.loads(LIST.read_text(encoding='utf-8'))


def write_list(tmp_path, doc):
    path = tmp_path / 'known-red.json'
    path.write_text(json.dumps(doc), encoding='utf-8')
    return path


def tree(root, files):
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding='utf-8')
    return root


# ---- the collector -----------------------------------------------------------------------------------------------

def test_the_collector_finds_the_ids_present_today():
    assert len(CITED) == 22, sorted(CITED)
    kinds = {run_id: {c.kind for c in cs} for run_id, cs in CITED.items()}
    assert {r for r, k in kinds.items() if k == {'Requirement'}} == ONLY_REQUIREMENT
    assert {r for r, k in kinds.items() if k == {'ProviderEvidence'}} == ONLY_PROVIDER
    assert {r for r, k in kinds.items() if k == {'Text'}} == ONLY_TEXT
    assert sum(1 for k in kinds.values() if 'Evidence' in k) == 18
    # agent_os/evidence.py: every Evidence there is collected, with its commit
    from omni_prod.agent_os import evidence as E
    for name in ('FREE', 'PAID', 'CRASH', 'BACKUP', 'DEPLOY', 'GATE_REPLAY', 'VERIFY_REPLAY', 'ECONOMICS'):
        ev = getattr(E, name)
        first = R.RUN_ID.findall(ev.ref)[0]
        assert any(c.ref == ev.ref and c.commit == ev.commit and c.primary for c in CITED[first]), name


def test_a_run_named_in_a_plain_string_is_collected():
    # Review 2026-11-25: vision_models._PROBE is the only evidence for four image models and the record walk never saw it
    from omni_prod import vision_models
    [c] = CITED['43657047045']
    assert (c.kind, c.ref, c.where, c.primary, c.commit) == ('Text', vision_models._PROBE, 'omni_prod/vision_models.py:16',
                                                            True, '')
    # a string that is also a record's text is cited once, by the record
    assert [c.kind for c in CITED['37954236866']] == ['Evidence']


def test_docstrings_and_comments_are_not_evidence(tmp_path):
    root = tree(tmp_path, {'omni_prod/x.py': '''\
        """Module docstring: run 1111111111."""
        # a comment: run 2222222222
        A = 'probe run 3333333333 ok'
        def f():
            """Function docstring: run 4444444444."""
            return 'deploy-worker run 5555555555'
        class C:
            """Class docstring: run 6666666666."""
            B = f'inspect run 7777777777 of {A}'
        '''})
    cited, _ = R.collect(sources=(), root=root)
    assert sorted(cited) == ['3333333333', '5555555555', '7777777777']
    assert [c.where for c in cited['5555555555']] == ['omni_prod/x.py:6']


def test_a_run_id_is_ten_or_more_digits():
    # Review 2026-11-25: every id today has 11 digits, so a 10- or 12-digit id could fall out unseen
    assert R.RUN_ID.findall('9 123456789 1234567890 123456789012') == ['1234567890', '123456789012']
    assert R.NAMED_RUN.findall('run 123456789, run 1234567890, Run 123456789012, rerun 1234567890') == [
        '1234567890', '123456789012']


def test_a_ten_and_a_twelve_digit_run_are_collected_from_strings(tmp_path):
    root = tree(tmp_path, {'omni_prod/x.py': "A = 'deploy-worker run 1234567890 and run 123456789012'\n"})
    cited, _ = R.collect(sources=(), root=root)
    assert sorted(cited) == ['1234567890', '123456789012']
    assert [(c.primary, c.workflows) for c in cited['123456789012']] == [(False, ())]   # no such workflow there


def test_the_collector_finds_the_same_ids_every_time():
    # Claude's bug, found before the first commit: the walk marked visited objects by id() without keeping them
    # alive, so a later call reused the id of a freed temporary and skipped inventory.py's records (21, then 19).
    assert [sorted(R.collect()[0]) for _ in range(3)] == [sorted(CITED)] * 3


def test_a_later_id_in_a_record_is_a_supporting_run_without_a_commit():
    assert {r for r, cs in CITED.items() if all(not c.primary for c in cs)} == SUPPORTING
    assert [(c.primary, c.commit) for c in CITED['37955419872']] == [(False, '')]
    assert [(c.primary, c.commit) for c in CITED['37954236866']] == [(True, '2b4bafd')]


def test_the_workflow_named_before_an_id_is_recorded():
    assert R.named_workflows('postdeploy-checks verify-replay run 1', 40) == ('postdeploy-checks',)   # not 'verify'
    assert R.named_workflows('live probe run 43657047045', 15) == ()
    text = 'deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok'
    assert [c.workflows for c in CITED['37814803770'] if c.ref == text] == [('deploy-worker', 'model-probe')]
    assert [c.workflows for c in CITED['38083162363']] == [('deploy-worker',), ('deploy-worker',)]


def test_live_records_without_a_run_id_are_listed_not_dropped():
    assert len(UNCITED) == 15
    assert 'deploy-worker "janitor started"' in UNCITED


def test_the_unchecked_live_records_are_said_in_the_output(capsys):
    # Review 2026-11-25: with the warning switched off, all tests passed
    rc, out = run_main(capsys)
    [warning] = [w for w in lines(out, '::warning title=evidence runs::')]
    assert warning.startswith('::warning title=evidence runs::15 live evidence records cite no GitHub Actions run id '
                              'and are NOT checked here: ')
    assert 'deploy-worker "janitor started"' in warning


# ---- the guard: a file that builds records is a source -----------------------------------------------------------

def test_every_file_that_builds_evidence_is_a_source():
    assert R.undeclared_sources() == []
    built = dict(R._builders(R.ROOT))
    assert sorted(built) == R.source_files()
    # registry_audit.py imports Evidence for an annotation only: it reads records, it does not build them
    assert 'omni_prod/registry_audit.py' not in built
    for module in R.SOURCES:
        rest = tuple(s for s in R.SOURCES if s != module)
        rel = module.replace('.', '/') + '.py'
        assert R.undeclared_sources(sources=rest) == [f"{rel} builds records ({', '.join(built[rel])})"], module


BASE = {
    'omni_prod/__init__.py': '',
    'omni_prod/runtime_bindings.py': '''\
        from dataclasses import dataclass
        @dataclass(frozen=True)
        class Evidence:
            kind: str
            ref: str = ''
        @dataclass(frozen=True)
        class Requirement:
            names: tuple
            observed: str = ''
        ''',
    'omni_prod/intelligence/__init__.py': '',
    'omni_prod/intelligence/inventory.py': 'class ProviderEvidence:\n    pass\n',
    'omni_prod/agent_os/__init__.py': '',
    'omni_prod/agent_os/evidence.py': '''\
        from ..runtime_bindings import Evidence
        FREE = Evidence('live', 'postdeploy-checks run 11111111111')
        ''',
}
# Review 2026-11-25: only the first form was seen; each of the others built a record unseen.
FORMS = {
    'direct': 'from ..runtime_bindings import Evidence\nX = Evidence("live", "deploy-worker 22222222222")\n',
    'reexport': 'from .evidence import Evidence\nX = Evidence("live", "deploy-worker 22222222222")\n',
    'relative_module': 'from .. import runtime_bindings as rb\nX = rb.Evidence("live", "deploy-worker 22222222222")\n',
    'absolute_module': 'import omni_prod.runtime_bindings\n'
                       'X = omni_prod.runtime_bindings.Evidence("live", "deploy-worker 22222222222")\n',
    'module_alias': 'import omni_prod.intelligence.inventory as inv\nX = inv.ProviderEvidence()\n',
    'alias': 'from ..runtime_bindings import Requirement\nMk = Requirement\nX = Mk(("K",), "deploy-worker 22222222222")\n',
    'replace': 'import dataclasses\nfrom . import evidence as ev\nX = dataclasses.replace(ev.FREE, ref="deploy-worker 22222222222")\n',
    'replace_name': 'from dataclasses import replace\nfrom .evidence import FREE\nX = replace(FREE, ref="deploy-worker 22222222222")\n',
    'star': 'from ..runtime_bindings import *\nX = Evidence("live", "deploy-worker 22222222222")\n',
    'star_reexport': 'from .evidence import *\nX = Evidence("live", "deploy-worker 22222222222")\n',
}
EXPECTED = {'direct': 'Evidence', 'reexport': 'Evidence', 'relative_module': 'Evidence', 'absolute_module': 'Evidence',
            'module_alias': 'ProviderEvidence', 'alias': 'Requirement', 'replace': 'dataclasses.replace',
            'replace_name': 'dataclasses.replace', 'star': 'Evidence', 'star_reexport': 'Evidence'}
# Files that read records, or have a class of the same name of their own, do not build one.
NOT_BUILDERS = {
    'annotation': 'from ..runtime_bindings import Evidence\ndef f(e: Evidence) -> Evidence:\n    return e\n'
                  'x: Evidence = None\n',
    'isinstance': 'from ..runtime_bindings import Evidence\ndef f(e):\n    return isinstance(e, (Evidence,))\n',
    'own_class': 'class Evidence:\n    pass\nX = Evidence()\n',
    'replace_elsewhere': 'import dataclasses\nfrom ..intake import thing\nX = dataclasses.replace(thing.Y, a=1)\n',
}


@pytest.mark.parametrize('form', sorted(FORMS))
def test_each_way_of_building_a_record_is_seen(tmp_path, form):
    root = tree(tmp_path, {**BASE, f'omni_prod/agent_os/{form}.py': FORMS[form]})
    assert R.undeclared_sources(root=root, sources=('omni_prod.runtime_bindings', 'omni_prod.agent_os.evidence')) == [
        f'omni_prod/agent_os/{form}.py builds records ({EXPECTED[form]})']


def test_reading_a_record_or_a_class_of_the_same_name_is_not_building(tmp_path):
    root = tree(tmp_path, {**BASE, 'omni_prod/intake/__init__.py': '', 'omni_prod/intake/thing.py': 'Y = 1\n',
                           **{f'omni_prod/agent_os/{k}.py': v for k, v in NOT_BUILDERS.items()}})
    assert R.undeclared_sources(root=root, sources=('omni_prod.runtime_bindings', 'omni_prod.agent_os.evidence')) == []


def test_an_undeclared_evidence_file_stops_the_check(capsys, monkeypatch):
    monkeypatch.setattr(R, 'undeclared_sources', lambda: ['omni_prod/new_place.py builds records (Evidence)'])
    rc = R.main(['--repo', 'o/r'], fetch=lambda run_id: pytest.fail('nothing may be verified with a source missing'))
    out = capsys.readouterr().out
    assert rc == 2
    assert out.startswith('::error title=evidence runs::omni_prod/new_place.py builds records (Evidence), but it is '
                          'not in SOURCES')


def test_nothing_collected_is_never_a_pass(capsys, monkeypatch):
    monkeypatch.setattr(R, 'collect', lambda: ({}, []))
    rc = R.main(['--repo', 'o/r'], fetch=lambda run_id: pytest.fail('there is nothing to ask'))
    assert rc == 2
    assert '::error title=evidence runs::no run id was collected' in capsys.readouterr().out


# ---- the verdict -------------------------------------------------------------------------------------------------

def test_today_every_unlisted_run_is_green_and_the_listed_ones_are_shown_red(capsys):
    rc, out = run_main(capsys)
    assert rc == 0, out
    assert lines(out, '::error') == []
    assert len(lines(out, '::notice title=evidence run ')) == 18
    assert out.splitlines()[0] == ('::notice title=evidence runs::18 of 22 cited run ids resolved green; KNOWN RED '
                                   '(capabilities marked verified on a failed run): 37814803770, 37954236866, '
                                   '39377332673, 43657047045')


@pytest.mark.parametrize('conclusion', ['failure', 'cancelled', 'skipped', None])
def test_a_run_that_is_not_green_fails(capsys, conclusion):
    rc, out = run_main(capsys, answers={'38083312245': dict(green('38083312245'), conclusion=conclusion)})
    assert rc == 1
    assert f'RED: conclusion {conclusion}' in error_for(out, '38083312245')
    assert len(lines(out, '::error')) == 1
    assert '17 of 22 cited run ids resolved green; KNOWN RED' in out and '; not green: 38083312245' in out


def test_a_run_in_progress_fails(capsys):
    running = dict(green('39307232830'), status='in_progress', conclusion=None)
    rc, out = run_main(capsys, answers={'39307232830': running})
    assert rc == 1
    assert 'not completed (status in_progress)' in error_for(out, '39307232830')
    # a re-run in progress may still carry the old conclusion: not completed is enough to fail
    rc, out = run_main(capsys, answers={'39307232830': dict(running, conclusion='success')})
    assert rc == 1
    assert 'RED: not completed (status in_progress) |' in error_for(out, '39307232830')


def test_a_run_github_no_longer_has_is_expired_and_fails(capsys):
    # Review 2026-11-25: runs are deleted after the retention period; a 404 is its own verdict, still a failure
    gone = urllib.error.HTTPError('https://api.github.com/x', 404, 'Not Found', {}, None)
    rc, out = run_main(capsys, errors={'37962179844': gone})
    assert rc == 1
    assert error_for(out, '37962179844').startswith(
        '::error title=evidence run 37962179844::EXPIRED: evidence expired: GitHub no longer has run 37962179844 '
        '(HTTP 404); run again and cite the new run | cited by: ')
    assert '; expired: 37962179844' in out.splitlines()[0] and 'not green' not in out.splitlines()[0]


def test_a_run_on_another_commit_fails(capsys):
    rc, out = run_main(capsys, answers={'37962179844': green('37962179844', head_sha='a' * 40)})
    assert rc == 1
    assert 'head_sha aaaaaaaaaaaa does not start with the cited commit 039574f' in error_for(out, '37962179844')


def test_the_cited_commit_is_a_prefix_not_a_substring(capsys):
    # Review 2026-11-25: 'commit in head' survived every test
    rc, out = run_main(capsys, answers={'37962179844': green('37962179844', head_sha='f039574f' + '0' * 32)})
    assert rc == 1
    assert 'head_sha f039574f0000 does not start with the cited commit 039574f' in error_for(out, '37962179844')


def test_an_answer_without_head_sha_fails_the_commit_check(capsys):
    # Review 2026-11-25: skipping the comparison when head_sha is missing survived every test
    rc, out = run_main(capsys, answers={'37962179844': dict(green('37962179844'), head_sha=None)})
    assert rc == 1
    assert 'head_sha none does not start with the cited commit 039574f' in error_for(out, '37962179844')


def test_every_citing_record_is_checked_against_its_commit(capsys):
    # 38083162363 is cited by DEPLOY (Evidence) and DEPLOY_NOTICE (ProviderEvidence), both @67a0765
    rc, out = run_main(capsys, answers={'38083162363': green('38083162363', head_sha='b' * 40)})
    assert rc == 1
    assert error_for(out, '38083162363').count('does not start with the cited commit 67a0765') == 2


def test_the_run_must_be_of_the_workflow_the_text_names(capsys):
    # Review 2026-11-25: the green ci-fast run of the same push, from a fork's pull request, resolved GREEN for
    # 'deploy-worker run 38083162363'
    other = dict(green('38083162363', workflow='ci-fast'), head_branch='fork-pr-branch', event='pull_request')
    rc, out = run_main(capsys, answers={'38083162363': other})
    assert rc == 1
    assert error_for(out, '38083162363').count('workflow ci-fast is not the deploy-worker the text names') == 2
    # a supporting run is held to the workflow too, and an answer without a path is not a pass
    rc, out = run_main(capsys, answers={'37955419872': dict(green('37955419872'), path=None)})
    assert rc == 1
    assert 'workflow none is not the postdeploy-checks the text names' in error_for(out, '37955419872')


def test_a_text_that_names_no_workflow_is_not_held_to_one():
    assert [c.workflows for c in CITED['43657047045']] == [()]          # 'live probe run 43657047045 ...'
    answer = dict(green('43657047045', workflow='any-workflow'))
    assert R.judge('43657047045', CITED['43657047045'], lambda run_id: answer)[:2] == ('green', [])


def test_a_supporting_run_must_be_green_but_its_commit_is_not_compared(capsys):
    rc, out = run_main(capsys, answers={'37955419872': green('37955419872', head_sha='54620a4' + '0' * 33)})
    assert rc == 0, out
    rc, out = run_main(capsys, answers={'37955419872': dict(green('37955419872'), conclusion='failure')})
    assert rc == 1
    assert 'supporting run' in error_for(out, '37955419872')


@pytest.mark.parametrize('error', [
    urllib.error.URLError('connection refused'),
    urllib.error.HTTPError('https://api.github.com/x', 500, 'Server Error', {}, None),
    urllib.error.HTTPError('https://api.github.com/x', 403, 'rate limit exceeded', {}, None),
    TimeoutError('timed out'),
    json.JSONDecodeError('Expecting value', '<html>', 0),
], ids=['network', 'http500', 'http403', 'timeout', 'not-json'])
def test_an_api_error_is_unverified_never_a_pass(capsys, error):
    rc, out = run_main(capsys, errors={'38083647077': error})
    assert rc == 2
    assert error_for(out, '38083647077').startswith('::error title=evidence run 38083647077::UNVERIFIED: API error')
    assert 'unverified: 38083647077' in out


def test_an_answer_for_another_run_is_unverified(capsys):
    rc, out = run_main(capsys, answers={'38083647077': green('38083312245')})
    assert rc == 2
    assert 'the answer is not run 38083647077' in error_for(out, '38083647077')


def test_the_summary_comes_first_and_names_every_failure(capsys):
    gone = urllib.error.HTTPError('https://api.github.com/x', 404, 'Not Found', {}, None)
    rc, out = run_main(capsys, answers={'37820429767': dict(green('37820429767'), conclusion='failure')},
                       errors={'38083647077': urllib.error.URLError('down'), '37862903906': gone})
    assert rc == 2
    assert out.splitlines()[0] == (
        '::notice title=evidence runs::15 of 22 cited run ids resolved green; KNOWN RED (capabilities marked verified '
        'on a failed run): 37814803770, 37954236866, 39377332673, 43657047045; not green: 37820429767; expired: '
        '37862903906; unverified: 38083647077')


def test_every_failing_id_has_its_own_error_line(capsys):
    # Review 2026-11-25: annotating only the first failing id survived every test; the first real run had three
    failing = ['37820429767', '38083312245', '39307232830']
    rc, out = run_main(capsys, answers={r: dict(green(r), conclusion='failure') for r in failing})
    assert rc == 1
    assert [line.split('::')[1] for line in lines(out, '::error ')] == [f'error title=evidence run {r}' for r in failing]


# ---- the known-red list ------------------------------------------------------------------------------------------

def test_the_list_holds_exactly_the_runs_red_today_and_says_what_each_backs():
    entries = known_list()['known_red']
    assert {e['run_id']: e['workflow'] for e in entries} == {r: f'{w}.yml' for r, w in KNOWN_RED.items()}
    for e in entries:
        assert e['backs'] and e['why_red'].startswith('Run completed with conclusion failure (read 2026-11-25)'), e
        assert e['cited_in'] == R.cited_in(e['run_id']) and e['cited_in'], e
    assert R.entry_problems(entries, CITED) == []
    assert 'capability marked verified on a run that failed' in known_list()['_what']


def test_each_listed_red_run_is_a_warning_that_says_what_it_is(capsys):
    rc, out = run_main(capsys)
    assert rc == 0
    [head] = lines(out, '::warning title=evidence runs: known red::')
    assert head.startswith('::warning title=evidence runs: known red::4 capabilities are marked verified on a run that '
                           'did not succeed: 37814803770, 37954236866, 39377332673, 43657047045. They are listed in '
                           'docs/evidence-runs-known-red.json, not fixed;')
    each = lines(out, '::warning title=known red evidence run ')
    assert [w.split('::')[1] for w in each] == [f'warning title=known red evidence run {r}' for r in sorted(KNOWN_RED)]
    for w, e in zip(each, sorted(known_list()['known_red'], key=lambda e: e['run_id'])):
        body = w.split('::', 2)[2]
        assert body.startswith(f"CAPABILITY MARKED VERIFIED ON A FAILED RUN: {' '.join(e['backs'].split())[:60]}")
        assert '| RED: conclusion failure |' in body and f"| listed {e['listed_on']}: " in body


def test_a_listed_run_that_turned_green_fails_so_the_list_only_shrinks(capsys):
    ok = dict(today('37954236866'), conclusion='success')
    rc, out = run_main(capsys, answers={'37954236866': ok})
    assert rc == 1
    assert error_for(out, '37954236866').startswith(
        '::error title=evidence run 37954236866::LISTED AS KNOWN RED BUT GREEN NOW: success on 2b4bafd00000 '
        '(postdeploy-checks.yml on main, 2026-10-10); remove it from docs/evidence-runs-known-red.json')
    assert '; listed as known red but green now: 37954236866' in out.splitlines()[0]
    assert '37954236866' not in out.splitlines()[0].split('KNOWN RED')[1].split(';')[0]


def test_a_listed_run_that_expired_is_still_shown_not_passed(capsys):
    gone = urllib.error.HTTPError('https://api.github.com/x', 404, 'Not Found', {}, None)
    rc, out = run_main(capsys, errors={'43657047045': gone})
    assert rc == 0
    [w] = lines(out, '::warning title=known red evidence run 43657047045::')
    assert '| EXPIRED: evidence expired: GitHub no longer has run 43657047045' in w


def test_a_listed_run_github_could_not_be_asked_about_is_not_a_pass(capsys):
    rc, out = run_main(capsys, errors={'43657047045': urllib.error.URLError('down')})
    assert rc == 2
    assert error_for(out, '43657047045').startswith('::error title=evidence run 43657047045::UNVERIFIED: API error')
    assert lines(out, '::warning title=known red evidence run 43657047045') == []


def test_the_listed_workflow_must_be_the_runs(capsys):
    rc, out = run_main(capsys, answers={'43657047045': dict(today('43657047045'), path='.github/workflows/model-probe.yml')})
    assert rc == 1
    [e] = lines(out, '::error title=evidence runs: known-red list::')
    assert ('docs/evidence-runs-known-red.json: entry 3 (43657047045): workflow says vision-probe.yml, GitHub says '
            'model-probe.yml') in e


def _changed(tmp_path, change):
    doc = known_list()
    change(doc['known_red'])
    return write_list(tmp_path, doc)


@pytest.mark.parametrize('reviewer', ['claude', 'pending', '', 'CLAUDE'])
def test_an_entry_without_a_reviewer_other_than_the_author_fails(capsys, tmp_path, reviewer):
    path = _changed(tmp_path, lambda es: es[0].update(reviewer=reviewer))
    rc, out = run_main(capsys, known_red=path)
    assert rc == 1
    [e] = lines(out, '::error title=evidence runs: known-red list::')
    assert 'entry 0 (37814803770): no reviewer other than the author' in e
    path = _changed(tmp_path, lambda es: es[1].update(author='shai'))
    rc, out = run_main(capsys, known_red=path)
    assert rc == 1 and 'entry 1 (37954236866): no reviewer other than the author (shai)' in out


def test_an_entry_no_longer_cited_fails(capsys, tmp_path):
    path = _changed(tmp_path, lambda es: es.append(dict(es[0], run_id='1234567890')))
    rc, out = run_main(capsys, known_red=path)
    assert rc == 1
    [e] = lines(out, '::error title=evidence runs: known-red list::')
    assert 'entry 4 (1234567890): no longer cited by any evidence; remove it (the list only shrinks)' in e


def test_cited_in_must_be_where_the_code_cites_the_run(capsys, tmp_path):
    path = _changed(tmp_path, lambda es: es[3].update(cited_in=['omni_prod/routed_gateway.py']))
    rc, out = run_main(capsys, known_red=path)
    assert rc == 1
    assert ("entry 3 (43657047045): cited_in says ['omni_prod/routed_gateway.py'], the code cites it in "
            "['omni_prod/vision_models.py']") in out


@pytest.mark.parametrize('change, said', [
    (lambda es: es[2].pop('why_red'), 'entry 2 (39377332673): missing why_red'),
    (lambda es: es[2].update(allowed=True), 'entry 2 (39377332673): unknown allowed'),
    (lambda es: es[2].update(backs=' '), 'entry 2 (39377332673): empty backs'),
    (lambda es: es[2].update(run_id='latest'), 'entry 2 (latest): run_id is not a run id'),
    (lambda es: es.append(dict(es[2])), 'entry 4 (39377332673): listed twice'),
], ids=['missing', 'unknown', 'empty', 'not-an-id', 'twice'])
def test_an_entry_that_is_not_complete_fails(capsys, tmp_path, change, said):
    rc, out = run_main(capsys, known_red=_changed(tmp_path, change))
    assert rc == 1
    assert said in out


@pytest.mark.parametrize('content', [None, '{', '{"known_red": {}}', '{"known_red": ["37814803770"]}', '[]'],
                         ids=['missing', 'not-json', 'not-a-list', 'not-entries', 'not-an-object'])
def test_a_list_that_cannot_be_read_is_never_a_pass(capsys, tmp_path, content):
    path = tmp_path / 'known-red.json'
    if content is not None:
        path.write_text(content, encoding='utf-8')
    rc = R.main(['--repo', 'o/r'], fetch=lambda run_id: pytest.fail('nothing may be verified without the list'),
                known_red=path)
    assert rc == 2
    assert f'::error title=evidence runs::the known-red list {path} cannot be read' in capsys.readouterr().out


def test_an_empty_list_makes_every_red_run_an_error(capsys, tmp_path):
    rc, out = run_main(capsys, known_red=write_list(tmp_path, {'known_red': []}))
    assert rc == 1
    assert [line.split('::')[1] for line in lines(out, '::error ')] == [
        f'error title=evidence run {r}' for r in sorted(KNOWN_RED)]
    assert lines(out, '::warning title=known red') == []


# ---- the job summary ---------------------------------------------------------------------------------------------

def test_no_test_writes_the_real_job_summary(tmp_path):
    assert os.environ['GITHUB_STEP_SUMMARY'] == str(tmp_path / 'summary.md')


def test_the_job_summary_shows_the_known_red_section_and_every_run(capsys, tmp_path):
    rc, _ = run_main(capsys, answers={'37820429767': dict(green('37820429767'), conclusion='failure')})
    assert rc == 1
    text = (tmp_path / 'summary.md').read_text(encoding='utf-8').splitlines()
    k = text.index('### Known red: capabilities marked verified on a failed run')
    every = text.index('### Every cited run')
    known_rows = [line for line in text[k:every] if line.startswith('| [')]
    assert [row.split(']')[0][3:] for row in known_rows] == sorted(KNOWN_RED)
    assert all('| RED: conclusion failure |' in row for row in known_rows)
    rows = [line for line in text[every:] if line.startswith('| [')]
    assert len(rows) == 22
    verdict = {row.split(']')[0][3:]: row.split(' | ')[1] for row in rows}
    assert verdict == {r: 'KNOWN RED' if r in KNOWN_RED else 'RED' if r == '37820429767' else 'GREEN' for r in CITED}


# ---- the real entry point and the real request ------------------------------------------------------------------

def test_without_a_token_nothing_is_verified_and_the_exit_is_2(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ('GITHUB_TOKEN', 'GITHUB_REPOSITORY')}
    p = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'resolve_evidence_runs.py'), '--repo', 'o/r'],
                       env=env, capture_output=True, text=True, timeout=60)
    assert p.returncode == 2, p.stdout + p.stderr
    assert p.stdout.strip() == ('::error title=evidence runs::GITHUB_TOKEN and --repo (or GITHUB_REPOSITORY) are needed; '
                                '22 cited run ids were not verified')
    assert not (tmp_path / 'summary.md').exists()


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_the_real_request_carries_the_token_in_the_header_only(capsys, monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'tok-never-printed')
    sent = []

    def urlopen(req, timeout):
        sent.append(req)
        run_id = req.full_url.rsplit('/', 1)[1]
        return Answer(json.dumps(today(run_id)).encode())
    rc = R.main(['--repo', 'Shayfly/desktop-tutorial'], urlopen=urlopen)
    out = capsys.readouterr().out
    assert rc == 0, out
    assert sorted(r.full_url for r in sent) == sorted(
        f'https://api.github.com/repos/Shayfly/desktop-tutorial/actions/runs/{i}' for i in CITED)
    assert {r.get_header('Authorization') for r in sent} == {'Bearer tok-never-printed'}
    assert 'tok-never-printed' not in out
    assert R.github_get.__code__.co_filename == str(ROOT / 'tools' / 'drill_runs_from_github.py')


# ---- the workflow ------------------------------------------------------------------------------------------------

def _workflow():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    return doc, doc.get('on') or doc.get(True)


def test_the_workflow_runs_when_a_citing_file_changes_daily_and_by_hand():
    _, on = _workflow()
    assert set(on) == {'pull_request', 'schedule', 'workflow_dispatch'}
    citing = {f for run_id in CITED for f in R.cited_in(run_id)}
    assert 'omni_prod/vision_models.py' in citing
    assert on['pull_request']['paths'] == sorted(
        set(R.source_files()) | citing
        | {'docs/evidence-runs-known-red.json', 'scripts/resolve_evidence_runs.py', '.github/workflows/evidence-runs.yml'})
    assert set(on['pull_request']) == {'paths'}
    [cron] = on['schedule']
    assert len(cron['cron'].split()) == 5 and cron['cron'].split()[2:] == ['*', '*', '*']   # daily


def test_the_workflow_reads_only_and_passes_the_token_through_env():
    doc, _ = _workflow()
    assert doc['permissions'] == {'actions': 'read', 'contents': 'read'}
    [job] = doc['jobs'].values()
    assert 'permissions' not in job
    [step] = [s for s in job['steps'] if 'resolve_evidence_runs.py' in str(s.get('run', ''))]
    assert step['env'] == {'GITHUB_TOKEN': '${{ github.token }}'}
    for s in job['steps']:
        for field in ('run', 'with'):
            assert 'token' not in str(s.get(field, '')).lower().replace('persist-credentials', ''), s
    checkout = next(s for s in job['steps'] if str(s.get('uses', '')).startswith('actions/checkout@'))
    assert checkout['with']['persist-credentials'] is False


def test_nothing_lets_a_failure_through():
    doc, _ = _workflow()
    [job] = doc['jobs'].values()
    assert 'continue-on-error' not in job and 'if' not in job
    for s in job['steps']:
        assert 'continue-on-error' not in s and 'if' not in s, s
    [step] = [s for s in job['steps'] if 'resolve_evidence_runs.py' in str(s.get('run', ''))]
    assert step['run'] == 'python scripts/resolve_evidence_runs.py --repo "$GITHUB_REPOSITORY"'   # its exit decides
    assert 'shell' not in step
