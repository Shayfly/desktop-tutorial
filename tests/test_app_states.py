"""Warehouse 130, first slice: every data screen of a generated APP has an empty, a loading and an error state, a server
error reaches the customer as a sentence with an action (never a stack trace), the gate runs on app builds only, and the
route decision is recorded with its reason (omni_prod/app_states.py).

Real path: the real check reads whole generated repositories (a server in app.py with its page, as the generator writes
them; the platform's own canonical app fixture, omni_prod/browser_fixtures.py); the gate wraps the real
AutonomousProductEngine's executor; the production worker job `_run_live_build_job` writes the decision and the route's
reason into the build evidence. The generator, repairer and sandbox are fakes (no model, no Docker), the gate and the
engine are not. The content-only request is a production row read read-only (tests/fixtures/
site_content_bld_b0eb47a5.json, the owner's law-firm brief). No production APP repository exists in the repository, so
the app fixtures below are written for this test (said in the report).
Mutations: tests/negative_controls/app_states.json.
"""
from __future__ import annotations

import inspect
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import app_states as A
from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import parse_patch

ROOT = Path(__file__).resolve().parent.parent
CONTENT_ONLY = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
APP = 'אפליקציה לניהול משמרות לעובדים: התחברות, טבלת משמרות, החלפות בין עובדים ואישור מנהל.'

LOADING = '<p data-state="loading">טוען את המשמרות…</p>\n'
EMPTY = ('<div data-state="empty" hidden><p>עוד אין משמרות השבוע.</p>'
         '<button type="button" id="add-first">הוסיפו משמרת ראשונה</button></div>\n')
RETRY = '<button type="button" id="retry">נסו שוב</button>'
ERROR = ('<div data-state="error" role="alert" hidden><p>לא הצלחנו לטעון את המשמרות. בדקו את החיבור ונסו שוב.</p>'
         + RETRY + '</div>\n')
STATUS = "    if (!res.ok) { show('error'); return; }\n"
CATCH = "  } catch (err) {\n    console.error(err);\n    show('error');\n  }\n"

PAGE = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>משמרות</title>\n'
        '<style>[hidden]{display:none}</style></head><body>\n<main><h1>משמרות השבוע</h1>\n'
        + LOADING + EMPTY + ERROR +
        '<ul id="shifts"></ul></main>\n<script>\n'
        "const $ = (s) => document.querySelector(s);\n"
        "function show(state) {\n"
        "  for (const el of document.querySelectorAll('[data-state]')) el.hidden = el.dataset.state !== state;\n"
        "}\n"
        "async function loadShifts() {\n"
        "  show('loading');\n"
        "  try {\n"
        "    const res = await fetch('/api/shifts');\n"
        + STATUS +
        "    const shifts = await res.json();\n"
        "    const list = $('#shifts');\n"
        "    list.replaceChildren();\n"
        "    if (shifts.length === 0) { show('empty'); return; }\n"
        "    for (const s of shifts) { const li = document.createElement('li'); li.textContent = `${s.worker} ${s.day}`; list.append(li); }\n"
        "    show('none');\n"
        + CATCH +
        "}\n"
        "async function addShift(worker, day) {\n"
        "  const res = await fetch('/api/shifts', {method: 'POST', headers: {'Content-Type': 'application/json'},\n"
        "    body: JSON.stringify({worker, day})});\n"
        "  return res.ok;\n"
        "}\n"
        "$('#retry').addEventListener('click', loadShifts);\n"
        "loadShifts();\n"
        '</script></body></html>')

HANDLER = ('        except Exception:\n'
           '            LOG.exception("GET %s failed", self.path)\n'
           '            return self._json(500, {"error": "משהו השתבש אצלנו. נסו שוב בעוד רגע."})\n')

SERVER = ('import json\nimport logging\nimport os\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\n\n'
          'LOG = logging.getLogger("shifts")\nSHIFTS = []\nPAGE = """' + PAGE + '"""\n\n\n'
          'class Handler(BaseHTTPRequestHandler):\n'
          '    def log_message(self, *args):\n        pass\n\n'
          '    def _json(self, code, body):\n'
          '        data = json.dumps(body, ensure_ascii=False).encode("utf-8")\n'
          '        self.send_response(code)\n'
          '        self.send_header("Content-Type", "application/json; charset=utf-8")\n'
          '        self.send_header("Content-Length", str(len(data)))\n'
          '        self.end_headers()\n'
          '        self.wfile.write(data)\n\n'
          '    def do_GET(self):\n'
          '        try:\n'
          '            if self.path == "/api/shifts":\n'
          '                return self._json(200, SHIFTS)\n'
          '            data = PAGE.encode("utf-8")\n'
          '            self.send_response(200)\n'
          '            self.send_header("Content-Type", "text/html; charset=utf-8")\n'
          '            self.end_headers()\n'
          '            self.wfile.write(data)\n'
          + HANDLER +
          '\n\nif __name__ == "__main__":\n'
          '    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler).serve_forever()\n')

MANIFEST = json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
                       'health_path': '/'})


def app(server: str = SERVER, **extra) -> dict:
    return {'app.py': server, '.omni/project.json': MANIFEST, **extra}


def changed(old: str, new: str, server: str = SERVER) -> dict:
    if server.count(old) != 1:
        raise AssertionError(f'the fixture does not hold {old!r} exactly once')
    return app(server.replace(old, new))


def codes(result: dict) -> set:
    return {f['code'] for f in result['findings']}


class AGoodAppPasses(unittest.TestCase):
    def test_every_state_is_there_and_the_server_answers_with_a_sentence(self):
        r = A.check(app())
        self.assertEqual((r['status'], r['findings']), ('pass', []))
        self.assertEqual(r['data_screens'], 1)
        [scr] = r['screens']
        self.assertEqual(scr['states'], {'loading': True, 'empty': True, 'error': True})
        self.assertTrue(scr['error_sentence'] and scr['error_action'])
        [read] = scr['reads']                                    # the POST is a write: not a data read
        self.assertEqual((read['route'], read['method'], read['caught'], read['status_checked']),
                         ('/api/shifts', 'GET', True, True))
        self.assertEqual(r['server_files'], ['app.py'])

    def test_the_platforms_own_app_fixture_has_none_of_the_three_states(self):
        from omni_prod.browser_fixtures import fixture_repository
        r = A.check(fixture_repository())
        self.assertEqual(r['status'], 'fail')
        self.assertEqual(codes(r), {'APP_NO_LOADING_STATE', 'APP_NO_EMPTY_STATE', 'APP_NO_ERROR_STATE',
                                    'APP_FETCH_UNHANDLED', 'APP_STATUS_UNCHECKED'})


class EachStateIsRequired(unittest.TestCase):
    def test_a_missing_empty_state_fails(self):
        r = A.check(changed(EMPTY, ''))
        self.assertEqual(codes(r), {'APP_NO_EMPTY_STATE'})
        [f] = r['findings']
        self.assertIn('/api/shifts', f['why'])
        self.assertIn('data-state="empty"', f['fix'])

    def test_a_missing_loading_state_fails(self):
        self.assertEqual(codes(A.check(changed(LOADING, ''))), {'APP_NO_LOADING_STATE'})

    def test_a_missing_error_state_fails(self):
        self.assertEqual(codes(A.check(changed(ERROR, ''))), {'APP_NO_ERROR_STATE'})

    def test_a_css_rule_or_a_query_for_the_state_is_not_the_state(self):
        repo = changed(EMPTY, '<style>[data-state="empty"]{color:gray}</style>\n')
        repo['app.py'] = repo['app.py'].replace("show('none');", "document.querySelector('[data-state=\"empty\"]');")
        self.assertEqual(codes(A.check(repo)), {'APP_NO_EMPTY_STATE'})

    def test_a_state_an_element_is_given_by_script_counts(self):
        repo = changed(EMPTY, '<div id="none"></div>\n')
        repo['app.py'] = repo['app.py'].replace("show('none');", "$('#none').dataset.state = 'empty';")
        self.assertEqual(A.check(repo)['status'], 'pass')


class TheErrorIsASentenceWithAnAction(unittest.TestCase):
    def test_an_error_state_without_a_button_fails(self):
        r = A.check(changed(RETRY, ''))
        self.assertEqual(codes(r), {'APP_ERROR_WITHOUT_ACTION'})
        self.assertIn('no button or link', r['findings'][0]['why'])

    def test_an_error_state_without_a_sentence_fails(self):
        r = A.check(changed('<p>לא הצלחנו לטעון את המשמרות. בדקו את החיבור ונסו שוב.</p>', ''))
        self.assertEqual(codes(r), {'APP_ERROR_WITHOUT_ACTION'})
        self.assertIn('no sentence', r['findings'][0]['why'])

    def test_an_error_element_written_by_the_script_counts(self):
        repo = changed(ERROR, '<div id="slot"></div>\n')
        repo['app.py'] = repo['app.py'].replace(
            "show('none');", "show('none');\n    $('#slot').innerHTML = '<div data-state=\"error\" hidden><p>לא הצלחנו "
                             "לטעון. נסו שוב.</p><button type=\"button\">נסו שוב</button></div>';")
        self.assertEqual(A.check(repo)['status'], 'pass')

    def test_the_errors_own_text_shown_to_the_customer_fails(self):
        for shown in ("$('#shifts').textContent = err.message;", "alert(err);", "$('#shifts').innerHTML = `<p>${err}</p>`;",
                      "$('#shifts').textContent = 'שגיאה: ' + String(err);", "$('#shifts').textContent = err.stack;"):
            with self.subTest(shown):
                r = A.check(changed("    console.error(err);\n", f"    console.error(err);\n    {shown}\n"))
                self.assertEqual(codes(r), {'APP_RAW_ERROR_SHOWN'})

    def test_a_variable_named_like_an_error_outside_its_catch_is_not_the_error(self):
        repo = changed("for (const s of shifts) {", "for (const err of shifts) { list.append(err); } for (const s of shifts) {")
        self.assertEqual(A.check(repo)['status'], 'pass')

    def test_a_request_that_is_not_caught_fails(self):
        repo = changed(CATCH, '  } finally {\n    console.log(1);\n  }\n')
        self.assertEqual(codes(A.check(repo)), {'APP_FETCH_UNHANDLED'})

    def test_a_request_caught_by_its_caller_passes(self):
        repo = changed(CATCH, '  } finally {\n    console.log(1);\n  }\n')
        repo['app.py'] = repo['app.py'].replace("\nloadShifts();\n", "\nloadShifts().catch((err) => { console.error(err); show('error'); });\n")
        self.assertEqual(A.check(repo)['status'], 'pass')

    def test_a_response_that_is_not_checked_fails(self):
        r = A.check(changed(STATUS, ''))
        self.assertEqual(codes(r), {'APP_STATUS_UNCHECKED'})
        self.assertIn('response.ok', r['findings'][0]['fix'])


class TheServerNeverSendsAStackTrace(unittest.TestCase):
    def test_the_exceptions_text_to_the_client_fails(self):
        for handler in ('        except Exception as exc:\n            return self._json(500, {"error": str(exc)})\n',
                        '        except Exception as exc:\n            return self._json(500, {"error": f"failed: {exc}"})\n',
                        '        except Exception:\n            return self._json(500, {"error": traceback.format_exc()})\n',
                        '        except BaseException as exc:\n            body = {"error": repr(exc)}\n'
                        '            self._json(500, body)\n',
                        '        except:\n            self.wfile.write(traceback.format_exc().encode())\n'):
            with self.subTest(handler):
                r = A.check(changed(HANDLER, handler))
                self.assertEqual(codes(r), {'APP_TRACEBACK_TO_CLIENT'})
                self.assertTrue(r['findings'][0]['where'].startswith('app.py:'))

    def test_a_flask_or_fastapi_handler_that_returns_the_exception_fails(self):
        flask = ('from flask import Flask, jsonify\napp = Flask(__name__)\n\n@app.errorhandler(Exception)\n'
                 'def failed(e):\n    return jsonify(error=str(e)), 500\n')
        fastapi = ('from fastapi import FastAPI\nfrom fastapi.responses import JSONResponse\napp = FastAPI()\n\n'
                   '@app.exception_handler(Exception)\nasync def failed(request, exc):\n'
                   '    return JSONResponse(status_code=500, content={"detail": exc.args})\n')
        for server in (flask, fastapi):
            with self.subTest(server[:20]):
                self.assertEqual(codes(A.check({'server.py': server})), {'APP_TRACEBACK_TO_CLIENT'})

    def test_a_narrow_handler_a_log_line_or_another_raise_is_not_a_response(self):
        for handler in ('        except ValueError as exc:\n            return self._json(400, {"error": str(exc)})\n',
                        '        except Exception as exc:\n            LOG.exception(exc)\n'
                        '            sys.stderr.write(str(exc))\n'
                        '            if isinstance(exc, KeyError):\n                pass\n'
                        '            return self._json(500, {"error": "לא הצלחנו. נסו שוב."})\n',
                        '        except Exception as exc:\n            raise RuntimeError(f"wrapped: {exc}") from exc\n'):
            with self.subTest(handler):
                self.assertEqual(A.check(changed(HANDLER, handler))['status'], 'pass')

    def test_debug_mode_fails(self):
        for line in ('app.run(debug=True)', 'app.debug = True', "app.config['DEBUG'] = True",
                     'app.config.update(DEBUG=True)', 'import cgitb\ncgitb.enable()'):
            with self.subTest(line):
                r = A.check({'server.py': 'from flask import Flask\napp = Flask(__name__)\n' + line + '\n'})
                self.assertEqual(codes(r), {'APP_DEBUG_ON'})
        self.assertEqual(A.check({'server.py': 'app.run(debug=False)\nDEBUG = True\n'})['findings'], [])

    def test_an_html_error_page_for_a_server_error_fails(self):
        r = A.check(changed(HANDLER, '        except Exception:\n            self.send_error(500)\n'))
        self.assertEqual(codes(r), {'APP_SERVER_ERROR_NOT_JSON'})


class WhatIsRead(unittest.TestCase):
    def test_a_script_file_the_page_loads_is_read(self):
        script = PAGE[PAGE.index('<script>') + len('<script>'):PAGE.index('</script>')]
        page = PAGE.replace('<script>' + script + '</script>', '<script src="/static/app.js"></script>')
        repo = {'index.html': page, 'static/app.js': script.replace(STATUS, '')}
        r = A.check(repo)
        self.assertEqual(codes(r), {'APP_STATUS_UNCHECKED'})
        self.assertTrue(r['findings'][0]['where'].startswith('static/app.js:'))

    def test_a_script_that_is_not_a_file_is_said_never_passed(self):
        page = PAGE[:PAGE.index('<script>')] + '<script src="/app.js"></script></body></html>'
        r = A.check({'index.html': page})
        self.assertEqual(r['status'], 'NOT_RUN')
        self.assertIn('/app.js', r['reason'])

    def test_nothing_to_read_is_not_run_and_a_page_without_requests_passes(self):
        self.assertEqual(A.check({'README.md': 'x'})['status'], 'NOT_RUN')
        server_only = A.check({'server.py': 'import json\n'})                 # the screens were never judged
        self.assertEqual(server_only['status'], 'NOT_RUN')
        self.assertIn('screens were not checked', server_only['reason'])
        r = A.check({'index.html': '<html><body><p>שלום</p></body></html>'})
        self.assertEqual((r['status'], r['data_screens']), ('pass', 0))

    def test_static_assets_and_writes_are_not_data_reads(self):
        js = ("fetch('/static/logo.svg').then(r => r.text());\n"
              "fetch('/api/leads', {method: 'POST', body: '{}'}).then(r => r.ok);\n")
        r = A.check({'index.html': f'<html><body><script>{js}</script></body></html>'})
        self.assertEqual((r['status'], r['data_screens']), ('pass', 0))

    def test_strings_templates_comments_and_regexes_do_not_confuse_the_scan(self):
        tricky = ("    const re = /['\"{]/g; // fetch('/not/a/call') {\n"
                  "    /* try { */ const t = `{ ${'}'} fetch('/no') ${ {a: 1}.a } }`;\n")
        r = A.check(changed("    const res = await fetch('/api/shifts');\n",
                            tricky + "    const res = await fetch('/api/shifts');\n"))
        self.assertEqual((r['status'], r['findings']), ('pass', []))
        self.assertEqual([x['route'] for x in r['screens'][0]['reads']], ['/api/shifts'])

    def test_every_walk_is_bounded(self):
        # 2,000 nested functions took 9 seconds when each bracket was matched by walking forward and every definition
        # of the enclosing function's name was taken for a call of it; the bounded scan is linear
        import time
        nested = 'function a(){' * 2000 + 'fetch("/x")' + '}' * 2000
        started = time.monotonic()
        r = A.check({'index.html': '<html><body><script src="/n.js"></script></body></html>', 'n.js': nested})
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(codes(r) & {'APP_FETCH_UNHANDLED'}, {'APP_FETCH_UNHANDLED'})

    def test_an_unknown_code_raises(self):
        with self.assertRaises(ValueError):
            A._finding('APP_SOMETHING', 'x', 'y')


class _Arch:
    def __init__(self, spec=None):
        self.spec = spec

    def create_spec(self, prompt):
        return self.spec or SimpleNamespace(acceptance=(SimpleNamespace(id='A1', text='the app'),), requirements=())


class _Files:
    def __init__(self, files):
        self.files, self.failures = files, []

    def generate(self, spec):
        return parse_patch({'files': [{'path': k, 'content': v} for k, v in self.files.items()]})

    def repair(self, *, spec, repo_summary, failures):
        self.failures.append(failures)
        return parse_patch({'files': [{'path': k, 'content': v} for k, v in self.files.items()]})


class _Sandbox:
    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'sandbox ok', tests_executed=3)


def engine(first: dict, repaired: dict, *, prompt: str = APP, mode: str | None = 'block', rounds: int = 2):
    rep = _Files(repaired)
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files(first), repairer=rep, executor=_Sandbox(),
                                max_repair_rounds=rounds)
    env = {'OMNI_GATE_APP_STATES': mode} if mode else {}
    with mock.patch.dict(os.environ, env):
        if not mode:
            os.environ.pop('OMNI_GATE_APP_STATES', None)
        installed = A.install(e, prompt=prompt)
    return e, rep, installed


class TheGateInTheEngine(unittest.TestCase):
    def test_in_block_a_missing_state_fails_the_round_and_the_repair_fixes_it(self):
        e, rep, installed = engine(changed(EMPTY, ''), app())
        self.assertEqual(installed, 'block')
        result = e.build(APP)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))
        first = {f['acceptance_id']: f['message'] for f in rep.failures[0]}
        self.assertEqual([k for k in first if k.startswith(A.ACCEPTANCE_PREFIX)], ['gate-APP_STATES-APP_NO_EMPTY_STATE'])
        self.assertIn('data-state="empty"', first['gate-APP_STATES-APP_NO_EMPTY_STATE'])
        self.assertEqual(A.report(e)['last']['status'], 'pass')               # the repaired app

    def test_in_block_a_stack_trace_to_the_client_fails_the_round(self):
        broken = changed(HANDLER, '        except Exception as exc:\n            return self._json(500, {"error": str(exc)})\n')
        e, rep, _ = engine(broken, app())
        self.assertEqual(e.build(APP).status, 'ready')
        message = {f['acceptance_id']: f['message'] for f in rep.failures[0]}['gate-APP_STATES-APP_TRACEBACK_TO_CLIENT']
        self.assertIn('logging.exception', message)

    def test_an_app_that_keeps_failing_fails_the_build(self):
        e, _, _ = engine(changed(LOADING, ''), changed(LOADING, ''), rounds=1)
        self.assertEqual(e.build(APP).status, 'failed')

    def test_it_warns_by_default_and_the_evidence_keeps_the_findings(self):
        from omni_prod.skill_units import gate as G
        self.assertIn(A.GATE, G.CALIBRATING)
        e, rep, installed = engine(changed(LOADING, ''), app(), mode=None)
        self.assertEqual(installed, 'warn')
        result = e.build(APP)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        ev = A.report(e)
        self.assertEqual((ev['applies'], ev['why'], ev['mode']), (True, 'not_content_only', 'warn'))
        self.assertEqual((ev['last']['status'], codes(ev['last'])), ('fail', {'APP_NO_LOADING_STATE'}))
        json.dumps(ev)                                                         # the evidence is JSON

    def test_off_is_said_and_an_unknown_mode_raises(self):
        e, _, installed = engine(app(), app(), mode='off')
        self.assertEqual((installed, A.report(e)['mode'], A.report(e)['last']), ('off', 'off', None))
        with self.assertRaises(ValueError), mock.patch.dict(os.environ, {'OMNI_GATE_APP_STATES': 'maybe'}):
            A.install(SimpleNamespace(executor=_Sandbox()), prompt=APP)

    def test_never_on_a_content_only_site(self):
        prompt = CONTENT_ONLY['prompt']
        e, _, installed = engine(changed(EMPTY, ''), app(), prompt=prompt)
        self.assertEqual(installed, 'not_applicable')
        self.assertIsInstance(e.executor, _Sandbox)                            # the chain is untouched
        self.assertEqual(e.build(prompt).status, 'ready')
        ev = A.report(e)
        self.assertEqual((ev['applies'], ev['why'], ev['mode'], ev['last']), (False, 'content_only_site', None, None))
        self.assertEqual(A.applies(APP), (True, 'not_content_only'))

    def test_the_rule_reaches_the_generator_of_an_app_and_never_of_a_content_site(self):
        from omni_prod.product_spec import ProductSpec
        spec = ProductSpec.from_dict({'title': 'משמרות', 'summary': 'ניהול משמרות', 'stack': ['python'],
                                      'requirements': [{'id': 'R1', 'text': 'טבלת משמרות'}],
                                      'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'רואים משמרות'}]})
        for prompt, carried in ((APP, True), (CONTENT_ONLY['prompt'], False)):
            with self.subTest(carried=carried):
                e = SimpleNamespace(executor=_Sandbox(), architect=_Arch(spec))
                A.install(e, prompt=prompt)
                self.assertIs(A.carry_rule(e), carried)
                ids = [r.id for r in e.architect.create_spec(prompt).requirements]
                self.assertEqual(A.REQUIREMENT in ids, carried)
                self.assertIs(A.report(e)['rule_carried'], carried)
        twice = A.with_rule(A.with_rule(spec))
        self.assertEqual([r.id for r in twice.requirements].count(A.REQUIREMENT), 1)


class TheWorkerRecordsTheDecision(unittest.TestCase):
    """The production worker job: an app request stays off the site engine, the route's reason is in the evidence, and
    the app gate's decision with its reason too."""

    def harness(self, **kw):
        from tests.test_m3_preview_logic import BuildHarness
        h = BuildHarness(**kw)
        h.jobs.request['prompt'] = APP
        return h

    def deployed(self):
        env = {'OMNI_SITE_LIBRARY': 'on'}                                     # as the worker is deployed (DECISIONS)
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop('OMNI_GATE_APP_STATES', None)

    def test_an_app_build_records_the_route_reason_and_the_app_gate(self):
        self.deployed()
        h = self.harness()
        self.assertEqual(h.run(), 'ready')
        ev = h.final['evidence_json']
        self.assertEqual((ev['site_route']['route'], ev['site_route']['reason']), ('legacy', 'not_content_only'))
        self.assertEqual((ev['app_states']['applies'], ev['app_states']['why'], ev['app_states']['mode']),
                         (True, 'not_content_only', 'warn'))
        self.assertIs(ev['app_states']['rule_carried'], True)
        self.assertNotIn('ContentSpecArchitect', type(h.engine.core.architect).__name__)   # the site engine never came in

    def test_the_route_reason_is_recorded_when_the_build_raises(self):
        self.deployed()
        h = self.harness(engine_exc=RuntimeError('boom'))
        with self.assertRaises(RuntimeError):
            h.run()
        self.assertEqual(h.final['evidence_json']['site_route']['reason'], 'not_content_only')

    def test_the_worker_and_the_rehearsal_install_it_before_the_build(self):
        from omni_prod import rehearsal, worker_tasks
        src = inspect.getsource(worker_tasks._run_live_build_job)
        self.assertLess(src.index('install_app_states(engine, prompt=prompt)'), src.index('engine.build(build_prompt)'))
        self.assertLess(src.index('carry_app_states_rule(engine)'), src.index('engine.build(build_prompt)'))
        self.assertIn("evidence['app_states'] = app_states_report(engine)", inspect.getsource(worker_tasks))
        rsrc = inspect.getsource(rehearsal.run)
        self.assertLess(rsrc.index('install_app_states(engine, prompt=prompt)'), rsrc.index('result = engine.build(prompt)'))
        self.assertIn("report['app_states'] = app_states_report(engine)", rsrc)


if __name__ == '__main__':
    unittest.main()
