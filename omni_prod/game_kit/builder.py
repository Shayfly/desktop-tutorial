"""The builder `canvas_game_v1` (warehouse 134, plan S12.1): a game built on the SAME engine as every other product.

`AutonomousProductEngine` (omni_prod/autonomous_core.py) takes four agents. For a game they are these:

  GameArchitect   the spec, deterministically from the customer's request: no model call
  GameGenerator   ONE model call writes the game DEFINITION (schema 148ai.game/1; the model never writes engine code), the
                  definition is validated (an invalid one gets exactly one corrective call naming every problem; a second
                  invalid answer fails the build out loud), the art layer attaches images (art.py), and the repository is
                  the page the tested runtime assembles from it (assemble.build_html) plus a static server for the preview
  GameRepairer    the probe's findings go back to the model with the definition it wrote; the answer takes the same road
  GameProbeExecutor  game_probe (probe.py) plays the page in a real Chromium at a computer's and a phone's width. A page that
                  is not byte for byte what the assembler makes from its own definition fails ("the page was edited by
                  hand"). No browser on this machine reads NOT_RUN as a FAILURE: a game that was not played is not ready.

Nothing here is reached unless the output rollout lets `game` through (feature_flags.output_rollout) and the build's family is
`game`: worker_tasks.execute_live_build_job asks `is_game_build` before it chooses the engine.
"""
from __future__ import annotations

import json
import os
import re

from ..autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from ..product_spec import ProductSpec
from ..repository_patch import parse_patch
from . import art as ART
from .assemble import build_html
from .schema import InvalidGame, KINDS, SCHEMA, validate

BUILDER_CANVAS_GAME_V1 = 'canvas_game_v1'
ART_MODES = ('procedural', 'provider')
DEFINITION_FILE, PAGE_FILE, ART_FILE = 'game.json', 'index.html', '.omni/art.json'

_SYSTEM = (
    'You design a small 2D browser game as ONE JSON object. You never write code: a tested engine plays what you describe. '
    'Reply with only JSON of this shape: {"definition": {...}, "art_theme": "one line of English describing the look of the art"}. '
    f'"definition" has EXACTLY these keys, no others: schema ("{SCHEMA}"), kind (one of {list(KINDS)}), title (1-60 characters), '
    'lang ("he", "ar" or "en": the language of the customer\'s request), texts {start, win, lose, score} (each 1-120 characters, '
    'in that language), palette {bg, player, enemy, item, ground, text} (each "#rrggbb"), player {speed 1-10, jump 1-10, lives 1-5}, '
    'time_limit_s (10-300), sound (true or false), seed (a whole number 1-2147483647), levels. '
    'levels by kind: platformer = 1 to 10 of {"rows": [6-13 strings of the SAME width 16-200, using only the tiles . # o E ^ P F]} '
    '(# solid, o coin, E enemy, ^ spike, P the one start tile with ground under it, F the one flag tile; the bottom row has ground); '
    'shooter = exactly 1 of {"waves": [1-20 of {"count": 1-30, "speed": 1-10}]}; '
    'match = exactly 1 of {"cols": 5-8, "rows": 5-8, "colors": 3-6, "moves": 5-50, "target": 30-5000}; '
    'runner = exactly 1 of {"length_s": 10-120 (not longer than time_limit_s), "obstacle_rate": 1-10, "coin_rate": 0-10}. '
    'Choose the kind that fits the request. Make it winnable by a simple player in the time limit. Every value is checked; '
    'a wrong value is refused, never repaired.')


def art_mode(env=None) -> str:
    """OMNI_GAME_ART: 'procedural' (default: deterministic art, no model, no spend) or 'provider' (the image provider asked
    for each image, falling back per image). Any other value raises (CLAUDE.md section 3)."""
    raw = ((os.environ if env is None else env).get('OMNI_GAME_ART') or 'procedural').strip().lower()
    if raw not in ART_MODES:
        raise ValueError(f"OMNI_GAME_ART must be 'procedural' or 'provider', not {raw!r}")
    return raw


def _files(definition: dict, images: dict, report: ART.ArtReport) -> dict[str, str]:
    from ..repository_assets import envelope
    html = build_html(definition)
    server = ('import http.server, os\n\n\nclass H(http.server.SimpleHTTPRequestHandler):\n'
              '    def log_message(self, *a):\n        pass\n\n\n'
              'os.chdir(os.path.dirname(os.path.abspath(__file__)))\n'
              "http.server.ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8000'))), H).serve_forever()\n")
    manifest = {'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'], 'port': 8000,
                'health_path': '/', 'build': [],
                'verify': [{'name': 'the game page is served', 'argv': ['python', '-c', 'import json; json.load(open("game.json"))'],
                            'acceptance_ids': ['A1', 'A2']}]}
    carried = {path: envelope(data, mime) for path, (data, mime) in images.items()}     # an image is a file, as every image is
    return {**carried, PAGE_FILE: html, DEFINITION_FILE: json.dumps(definition, ensure_ascii=False, indent=1) + '\n', 'app.py': server,
            '.omni/project.json': json.dumps(manifest, indent=1) + '\n',
            ART_FILE: json.dumps(report.to_dict(), indent=1) + '\n'}


class GameState:
    """What the generator and the repairer share across rounds of one build."""
    def __init__(self, *, build_id: str, art_source=None):
        self.build_id, self.art_source = build_id, art_source
        self.request = ''
        self.definition: dict | None = None          # the model's version 1 definition
        self.theme = ''
        self.art_report: ART.ArtReport | None = None
        self.model_calls = 0


def _parse(data) -> tuple[dict, str]:
    if not isinstance(data, dict) or not isinstance(data.get('definition'), dict):
        raise InvalidGame(['the answer must be {"definition": {...}, "art_theme": "..."}'])
    return data['definition'], str(data.get('art_theme') or '')[:200]


def _definition_from_model(gateway, state: GameState, user: dict) -> tuple[dict, str]:
    """One call; an invalid answer gets ONE corrective call that names every problem; a second invalid answer raises."""
    state.model_calls += 1
    data = gateway.complete_json(system=_SYSTEM, user=json.dumps(user, ensure_ascii=False), max_tokens=8000)
    try:
        defn, theme = _parse(data)
        return validate(defn), theme
    except InvalidGame as first:
        state.model_calls += 1
        fix = dict(user, invalid_definition=data, problems=first.problems[:40],
                   instruction='Return the corrected JSON with exactly the required shape; fix every listed problem.')
        data = gateway.complete_json(system=_SYSTEM, user=json.dumps(fix, ensure_ascii=False), max_tokens=8000)
        try:
            defn, theme = _parse(data)
            return validate(defn), theme
        except InvalidGame as second:
            raise ValueError(f'the model returned an invalid game definition twice: {second} (first: {first})') from second


def _patch(state: GameState, defn: dict, theme: str):
    full, images, report = ART.attach(defn, source=state.art_source, theme=theme)
    state.definition, state.theme, state.art_report = defn, theme, report
    return parse_patch({'files': [{'path': p, 'content': c} for p, c in _files(full, images, report).items()]})


class GameArchitect:
    def __init__(self, state: GameState):
        self.state = state

    def create_spec(self, prompt: str, **_ignored) -> ProductSpec:
        if not prompt.strip():
            raise ValueError('prompt cannot be empty')
        self.state.request = prompt.strip()
        title = ' '.join(prompt.split())[:60]
        return ProductSpec.from_dict({
            'title': title, 'summary': prompt.strip()[:1500], 'stack': ['html', 'canvas', 'javascript'],
            'requirements': [
                {'id': 'R1', 'text': 'A 2D game the customer plays in the browser: ' + prompt.strip()[:400], 'kind': 'functional'},
                {'id': 'R2', 'text': 'It is playable on a phone with on-screen buttons and on a computer with the keyboard', 'kind': 'quality'}],
            'acceptance': [
                {'id': 'A1', 'requirement_id': 'R1', 'text': 'game_probe plays it: it starts, answers input, scores and ends with its end screen'},
                {'id': 'A2', 'requirement_id': 'R2', 'text': 'at phone width every control is on screen and at least 44 px'}]})


class GameGenerator:
    def __init__(self, gateway, state: GameState):
        self.gateway, self.state = gateway, state

    def generate(self, spec: ProductSpec) -> tuple:
        defn, theme = _definition_from_model(self.gateway, self.state, {'customer_request': self.state.request or spec.summary})
        return _patch(self.state, defn, theme)


class GameRepairer:
    def __init__(self, gateway, state: GameState):
        self.gateway, self.state = gateway, state

    def repair(self, *, spec: ProductSpec, repo_summary: dict, failures: list[dict]) -> tuple:
        if self.state.definition is None:
            raise ValueError('nothing to repair: no game was generated in this build')
        findings = [{'id': f.get('acceptance_id'), 'message': str(f.get('message', ''))[:600]} for f in failures[:12]]
        defn, theme = _definition_from_model(self.gateway, self.state, {
            'customer_request': self.state.request, 'current_definition': self.state.definition, 'probe_findings': findings,
            'instruction': 'The game was played by a probe and failed as listed. Return the whole corrected definition.'})
        return _patch(self.state, defn, theme or self.state.theme)


_A2_KINDS = {'no_touch_controls'}
# The platform's own transforms add to the page (a share meta, the brand part); what must be exactly the engine's is the
# definition the page plays and the tested runtime that plays it.
_CORE = re.compile(r'<script id="game-def" type="application/json">.*?</script>\n<script>.*?</script>', re.S)


def _core(page: str) -> str | None:
    m = _CORE.search(page)
    return m.group(0) if m else None


class GameProbeExecutor:
    """game_probe as the engine's verification step. `probe` is probe.probe_html (injectable only for a test that must
    not start a browser; production never passes one)."""

    def __init__(self, probe=None):
        self._probe = probe

    def execute(self, *, repository: dict, spec: ProductSpec) -> ExecutionReport:
        def failed(aid, message, evidence=''):
            return ExecutionReport(False, (AcceptanceFailure(aid, message, evidence[:2000]),), message, 0)
        try:
            defn = json.loads(repository[DEFINITION_FILE])
            validate(defn)
            page = build_html(defn)
        except (KeyError, ValueError) as exc:        # json errors and InvalidGame are ValueErrors
            return failed('A1', f'the game definition is missing or invalid: {exc}'[:900])
        if _core(repository.get(PAGE_FILE) or '') != _core(page):
            return failed('A1', 'index.html does not carry the definition and the runtime that game.json assembles: the page was edited by hand')
        from ..repository_assets import AssetCarryError, decode
        try:
            images = {path: decode(path, repository[path]) for path in (defn.get('art') or {}).values()}
        except KeyError as exc:
            return failed('A1', f'the game names an image that is not in the repository: {exc}')
        except AssetCarryError as exc:
            return failed('A1', f'a game image is not what it says: {exc}')
        probe = self._probe
        if probe is None:
            try:
                from .probe import probe_html as probe
                import playwright  # noqa: F401
            except ImportError:
                return failed('A1', 'NOT_RUN: this machine has no browser to play the game in; a game that was not played is not ready')
        try:
            result = probe(page, defn, files=images)
        except Exception as exc:       # noqa: BLE001 -- a probe that could not run is a failed probe, never a pass
            return failed('A1', f'NOT_RUN: the game could not be played ({type(exc).__name__}): {str(exc)[:300]}')
        if result['ok']:
            return ExecutionReport(True, (), json.dumps({'game_probe': result['measures']}, ensure_ascii=False)[:3000], 1)
        failures = tuple(AcceptanceFailure('A2' if f['kind'] in _A2_KINDS else 'A1', f"{f['kind']} ({f['where']}): {f['message']}")
                         for f in result['findings'])
        return ExecutionReport(False, failures, json.dumps(result['findings'], ensure_ascii=False)[:3000], 1)


def game_engine(gateway, *, build_id: str, executor_wrapper=None, art_source=None, max_repair_rounds: int = 3,
                probe=None) -> AutonomousProductEngine:
    """The engine of a game build. `gateway` is the build's own routed gateway (the build's budget and ledger apply)."""
    from ..attempt_ledger import TaskTaggedGateway
    state = GameState(build_id=build_id, art_source=art_source)
    executor = GameProbeExecutor(probe)
    engine = AutonomousProductEngine(
        architect=GameArchitect(state), generator=GameGenerator(TaskTaggedGateway(gateway, 'codegen'), state),
        repairer=GameRepairer(TaskTaggedGateway(gateway, 'repair'), state),
        executor=executor_wrapper(executor) if executor_wrapper else executor,
        max_repair_rounds=max_repair_rounds, repair_ceiling=max(3, max_repair_rounds))
    engine.no_progress_retries = 1
    engine.game_state = state
    return engine


def is_game_build(request: dict) -> bool:
    """True when a build request's approved contract says the product is a game (the worker's engine choice)."""
    return ((request or {}).get('build_contract') or {}).get('product_family') == 'game'
