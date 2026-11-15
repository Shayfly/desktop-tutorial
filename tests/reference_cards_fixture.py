"""Reference cards for the store tests: valid per docs/spec/reference_card.schema.json (#369), made here."""
import copy

_ALPHA = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'


def card_id(n: int) -> str:
    s, x = '', n
    for _ in range(26):
        s, x = _ALPHA[x % 32] + s, x // 32
    return 'ref_' + s


def card(n: int, *, total=9, status='approved', decided_by='michael', captured_at='2026-11-15T10:00:00Z',
         reason_code=None, vertical='butcher') -> dict:
    cid = card_id(n)
    scores = {'hierarchy': 2, 'air': 2, 'typography': 2, 'mobile_390': 2, 'originality': 2}
    for k in list(scores)[:10 - total]:
        scores[k] = 1
    reason = {k: {'anchor_id': f'anc_{k}_{v}_ab12', 'observation': 'מרווח נדיב'} for k, v in scores.items()}
    return copy.deepcopy({
        'schema_version': '0.1', 'card_id': cid, 'vertical': vertical,
        'source': {'url': f'https://example{n}.co.il/', 'captured_at': captured_at, 'author': None,
                   'captures': [{'viewport_width': w, 'full_page': True, 'sha256': f'{n % 10}' * 64,
                                 'path': f'references/{vertical}/{cid}/{w}.png'} for w in (390, 1440)]},
        'verify': {'http_status': 200, 'load_ms_390': 1800, 'direction': 'rtl', 'site_builder': None,
                   'carousel': False, 'first_screen_popup': False, 'placeholder_text': False, 'nav_depth': 2},
        'skeleton': {'section_order': ['nav', 'hero', 'products', 'hours', 'contact', 'footer'],
                     'hero': {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 2, 'cta_count': 1},
                     'rhythm': {'section_gap_px': [96, 128], 'inner_gap_px': [16, 24]},
                     'type_scale_px': [64, 30, 22, 18], 'columns': 12, 'traits': ['single_cta', 'hours_as_table']},
        'judge': {'panel': [{'model': 'judge-a', 'scores': scores}, {'model': 'judge-b', 'scores': scores}],
                  'scores': scores, 'total': total, 'reasons': reason},
        'decision': {'status': status, 'reason_code': reason_code, 'decided_by': decided_by,
                     'decided_at': '2026-11-15T11:00:00Z'},
    })
