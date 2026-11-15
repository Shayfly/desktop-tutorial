"""Price v0 for the proposal card (Michael 2026-11-15).

25 NIS per section, +39 NIS when the product includes generated media, never below 99 or above 399. The price is
ALWAYS shown and always marked "הערכה" (estimate): it does not block (the editor blocks only on completeness and
feasibility). Real ranges come after enough successful builds; until then this is v0.
"""
from __future__ import annotations

VERSION = 'v0'
PER_SECTION_ILS = 25
MEDIA_ILS = 39
FLOOR_ILS = 99
CEILING_ILS = 399
LABEL_HE, LABEL_EN = 'הערכה', 'estimate'


def estimate(*, sections: int, media: bool) -> dict:
    if not isinstance(sections, int) or isinstance(sections, bool) or sections < 0:
        raise ValueError(f'sections must be a non-negative integer, not {sections!r}')
    raw = PER_SECTION_ILS * sections + (MEDIA_ILS if media else 0)
    amount = min(max(raw, FLOOR_ILS), CEILING_ILS)
    basis = f'{sections} × {PER_SECTION_ILS}₪' + (f' + {MEDIA_ILS}₪ מדיה' if media else '')
    clamp = 'floor' if raw < FLOOR_ILS else 'ceiling' if raw > CEILING_ILS else None
    return {'amount_ils': amount, 'raw_ils': raw, 'basis': basis, 'clamped': clamp, 'estimate': True,
            'label_he': LABEL_HE, 'label_en': LABEL_EN, 'version': VERSION, 'blocks': False}
