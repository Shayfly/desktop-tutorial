"""The game definition the model writes, checked before anything runs (warehouse 134, acceptance 5).

The model never writes engine code. It writes one JSON object; this module either accepts it whole or raises
`InvalidGame` naming every problem. Nothing is repaired, clamped or defaulted: an unknown key, a missing key, a value
out of range or a level that cannot be played is an error (CLAUDE.md section 3: no quiet defaults).
"""
from __future__ import annotations

import re

SCHEMA = '148ai.game/1'
KINDS = ('platformer', 'shooter', 'match', 'runner')
SCHEMA_V2 = '148ai.game/2'      # adds the optional `art` block (S12.3): a version 1 definition still plays, with the flat look
ART_ROLES = ('background', 'player', 'enemy', 'item', 'ground')
ART_MAX_BYTES = 300_000          # one image file; the images of a game stay under ART_TOTAL_MAX_BYTES
ART_TOTAL_MAX_BYTES = 1_200_000
# Art is carried as FILES under assets/ (the platform's own way to carry an image: repository_assets), named by role, and the
# definition only names them. A relative path is a source the rights gate knows (rights_sources.json `build_served`); bytes
# inlined in the page would be "bytes embedded in the file that the platform did not supply" and block (found 2026-11-27).
_ART_PATH = re.compile(r'^assets/148ai-(background|player|enemy|item|ground)\.(png|webp|jpg)$')
LANGS = {'he': 'rtl', 'ar': 'rtl', 'en': 'ltr'}
PALETTE_KEYS = ('bg', 'player', 'enemy', 'item', 'ground', 'text')
TEXT_KEYS = ('start', 'win', 'lose', 'score')
TOP_KEYS = {'schema', 'kind', 'title', 'lang', 'texts', 'palette', 'player', 'time_limit_s', 'levels', 'sound', 'seed'}
PLATFORM_TILES = set('.#oE^PF')
_HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


class InvalidGame(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__('invalid game definition: ' + '; '.join(problems))


def _int(problems, where, v, lo, hi):
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        problems.append(f'{where} must be a whole number from {lo} to {hi}, got {v!r}')


def _text(problems, where, v, hi):
    if not isinstance(v, str) or not v.strip() or len(v) > hi:
        problems.append(f'{where} must be text of 1 to {hi} characters')


def _keys(problems, where, obj, want: set[str]):
    if not isinstance(obj, dict):
        problems.append(f'{where} must be an object')
        return False
    for k in sorted(set(obj) - want):
        problems.append(f'{where} has an unknown key {k!r}')
    for k in sorted(want - set(obj)):
        problems.append(f'{where} is missing {k!r}')
    return True


def _platformer_level(problems, where, lv):
    if not _keys(problems, where, lv, {'rows'}):
        return
    rows = lv['rows']
    if not isinstance(rows, list) or not 6 <= len(rows) <= 13 or not all(isinstance(r, str) for r in rows):
        problems.append(f'{where}.rows must be 6 to 13 lines of text')
        return
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        problems.append(f'{where}.rows have different widths {sorted(widths)}')
        return
    width = widths.pop()
    if not 16 <= width <= 200:
        problems.append(f'{where}.rows must be 16 to 200 tiles wide, got {width}')
    bad = sorted({ch for r in rows for ch in r} - PLATFORM_TILES)
    if bad:
        problems.append(f'{where}.rows use unknown tiles {bad}; allowed: {"".join(sorted(PLATFORM_TILES))}')
    flat = ''.join(rows)
    for tile, name in (('P', 'start'), ('F', 'flag')):
        if flat.count(tile) != 1:
            problems.append(f'{where} needs exactly one {name} tile {tile!r}, found {flat.count(tile)}')
    if 'P' in flat and flat.count('P') == 1:
        r = next(i for i, row in enumerate(rows) if 'P' in row)
        c = rows[r].index('P')
        if not any(rows[k][c] == '#' for k in range(r + 1, len(rows))):
            problems.append(f'{where}: no ground under the start tile')
    if '#' not in rows[-1]:
        problems.append(f'{where}: the bottom row has no ground')


def _waves(problems, where, lv):
    if not _keys(problems, where, lv, {'waves'}):
        return
    waves = lv['waves']
    if not isinstance(waves, list) or not 1 <= len(waves) <= 20:
        problems.append(f'{where}.waves must be a list of 1 to 20 waves')
        return
    for i, wv in enumerate(waves):
        if _keys(problems, f'{where}.waves[{i}]', wv, {'count', 'speed'}):
            _int(problems, f'{where}.waves[{i}].count', wv['count'], 1, 30)
            _int(problems, f'{where}.waves[{i}].speed', wv['speed'], 1, 10)


def _match_level(problems, where, lv):
    if not _keys(problems, where, lv, {'cols', 'rows', 'colors', 'target', 'moves'}):
        return
    _int(problems, f'{where}.cols', lv['cols'], 5, 8)
    _int(problems, f'{where}.rows', lv['rows'], 5, 8)
    _int(problems, f'{where}.colors', lv['colors'], 3, 6)
    _int(problems, f'{where}.moves', lv['moves'], 5, 50)
    _int(problems, f'{where}.target', lv['target'], 30, 5000)


def _runner_level(problems, where, lv):
    if not _keys(problems, where, lv, {'length_s', 'obstacle_rate', 'coin_rate'}):
        return
    _int(problems, f'{where}.length_s', lv['length_s'], 10, 120)
    _int(problems, f'{where}.obstacle_rate', lv['obstacle_rate'], 1, 10)
    _int(problems, f'{where}.coin_rate', lv['coin_rate'], 0, 10)


_LEVEL = {'platformer': (_platformer_level, 1, 10), 'shooter': (_waves, 1, 1),
          'match': (_match_level, 1, 1), 'runner': (_runner_level, 1, 1)}


def _art(problems, art):
    """The art block of a version 2 definition: the path of one image file per role, named after its role."""
    if not isinstance(art, dict) or not art:
        problems.append('art must be an object with at least one image')
        return
    for k in sorted(set(art) - set(ART_ROLES)):
        problems.append(f'art has an unknown role {k!r}; allowed: {list(ART_ROLES)}')
    for role in ART_ROLES:
        if role in art:
            m = _ART_PATH.match(art[role]) if isinstance(art[role], str) else None
            if not m or m.group(1) != role:
                problems.append(f'art.{role} must be the path assets/148ai-{role}.png (or .webp, .jpg), got {art[role]!r}')


def validate(defn: object) -> dict:
    """Return the definition unchanged when it is playable; raise InvalidGame listing every problem otherwise."""
    problems: list[str] = []
    if isinstance(defn, dict) and defn.get('schema') == SCHEMA_V2:
        # Version 2 = version 1 + the optional `art` block. The whole version 1 check runs on the rest, unchanged; a
        # version 1 file that carries `art` is refused by it below as an unknown key, never quietly accepted.
        validate({**{k: v for k, v in defn.items() if k != 'art'}, 'schema': SCHEMA})
        if 'art' in defn:
            _art(problems, defn['art'])
            if problems:
                raise InvalidGame(problems)
        return defn
    if not _keys(problems, 'game', defn, TOP_KEYS):
        raise InvalidGame(problems)
    if problems:
        raise InvalidGame(problems)
    if defn['schema'] != SCHEMA:
        problems.append(f'schema must be {SCHEMA!r}')
    kind = defn['kind']
    if kind not in KINDS:
        problems.append(f'kind must be one of {list(KINDS)}, got {kind!r}')
    _text(problems, 'title', defn['title'], 60)
    if defn['lang'] not in LANGS:
        problems.append(f'lang must be one of {sorted(LANGS)}, got {defn["lang"]!r}')
    if _keys(problems, 'texts', defn['texts'], set(TEXT_KEYS)):
        for k in TEXT_KEYS:
            if k in defn['texts']:
                _text(problems, f'texts.{k}', defn['texts'][k], 120)
    if _keys(problems, 'palette', defn['palette'], set(PALETTE_KEYS)):
        for k in PALETTE_KEYS:
            if k in defn['palette'] and not (isinstance(defn['palette'][k], str) and _HEX.match(defn['palette'][k])):
                problems.append(f'palette.{k} must be a colour like #1a2b3c')
    if _keys(problems, 'player', defn['player'], {'speed', 'jump', 'lives'}):
        _int(problems, 'player.speed', defn['player'].get('speed'), 1, 10)
        _int(problems, 'player.jump', defn['player'].get('jump'), 1, 10)
        _int(problems, 'player.lives', defn['player'].get('lives'), 1, 5)
    _int(problems, 'time_limit_s', defn['time_limit_s'], 10, 300)
    _int(problems, 'seed', defn['seed'], 1, 2 ** 31 - 1)
    if not isinstance(defn['sound'], bool):
        problems.append('sound must be true or false')
    if kind in _LEVEL:
        check, lo, hi = _LEVEL[kind]
        levels = defn['levels']
        if not isinstance(levels, list) or not lo <= len(levels) <= hi:
            problems.append(f'levels must be a list of {lo} to {hi} for {kind}')
        else:
            for i, lv in enumerate(levels):
                check(problems, f'levels[{i}]', lv)
        if kind == 'runner' and not problems and defn['levels'][0]['length_s'] > defn['time_limit_s']:
            problems.append('levels[0].length_s is longer than time_limit_s: the run can never be finished')
    if problems:
        raise InvalidGame(problems)
    return defn


def direction(defn: dict) -> str:
    return LANGS[defn['lang']]
