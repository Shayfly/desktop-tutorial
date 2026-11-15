"""The closed catalogue: 32 categories (appendix A's 30 + butcher + interior design, by the owner's decision of
2026-11-15 20:12) and the adjacency between them (appendix B).

Michael 2026-11-15: "הנספחים הם הרשימה הסגורה, ואסור להמציא קטגוריה או סמיכות מחוץ להם". So this module is data, not
judgement: a category or a link outside the appendices raises. Where appendix B names something appendix A does not,
the line is NOT guessed into existence -- it is listed in UNRESOLVED and left out, to be decided by the owner.

Reserve categories (appendix C) are not collected for and cannot be a starting category; two of them are reachable
ONLY as the cross-vertical neighbours appendix B marks (pet shops, interior design).
"""
from __future__ import annotations

# ---- appendix A: the 30 categories, in the document's own order and grouping ----------------------------------
CATEGORIES: dict[str, str] = {
    # אירוח ומזון
    'restaurants': 'מסעדות', 'cafes': 'בתי קפה', 'bakeries': 'מאפיות', 'delis': 'מעדניות וגורמה',
    'butcher': 'אטליז',                       # the owner, 2026-11-15 20:12: added (sections 8 and B name it)
    'alcohol': 'אלכוהול ויין', 'catering': 'קייטרינג ואירועים',
    # נופש
    'cabins': 'צימרים',
    # יופי
    'hair_salons': 'מספרות', 'nails': 'ציפורניים', 'cosmetics': 'קוסמטיקה', 'aesthetics': 'אסתטיקה',
    # בריאות
    'dental': 'שיניים', 'clinics_physio': 'קליניקות ופיזיותרפיה', 'vets': 'וטרינרים',
    # שירותים
    'lawyers': 'עורכי דין', 'accountants': 'רואי חשבון', 'renovation': 'שיפוצים', 'electrical': 'חשמל',
    'plumbing': 'אינסטלציה',
    # שירותי בית
    'hvac': 'מיזוג', 'locksmiths': 'מנעולנות', 'moving': 'הובלות',
    # כושר
    'gyms': 'חדרי כושר', 'personal_training': 'אימון אישי',
    # מדיה
    'photographers': 'צלמים', 'design_branding': 'עיצוב ומיתוג', 'digital_marketing': 'שיווק דיגיטלי',
    # מסחר
    'fashion': 'אופנה', 'jewelry': 'תכשיטים',
    # נדל"ן
    'realty': 'תיווך',
    # promoted from the reserve by the owner, 2026-11-15 20:12 (three verticals already link to it)
    'furniture_interior': 'ריהוט ועיצוב פנים',
}

# ---- appendix C: the reserve. Not collected for; only these two are reachable, as marked cross-vertical links --
RESERVE: dict[str, str] = {
    'garages': 'מוסכים', 'cleaning': 'ניקיון', 'gardening': 'גינון',
    'appliances': 'מוצרי חשמל', 'hotels': 'מלונות', 'online_courses': 'קורסים דיגיטליים',
    'medical_devices': 'מכשור רפואי', 'insurance': 'ביטוח', 'pet_shops': 'חנויות חיות',
}

LEGACY: dict[str, str] = {}   # was {'butcher'}: the owner made it a category (2026-11-15 20:12)

# ---- appendix B: the links, as consecutive pairs of each chain the document writes --------------------------
# (a, b, cross_vertical). Undirected: the fallback reads them both ways.
LINKS: tuple[tuple[str, str, bool], ...] = (
    ('restaurants', 'cafes', False),
    ('cafes', 'catering', False),
    ('bakeries', 'delis', False),
    ('butcher', 'delis', False),                  # the owner, 2026-11-15 20:12
    ('butcher', 'catering', False),               # the owner, 2026-11-15 20:12
    ('alcohol', 'restaurants', False),
    ('cabins', 'restaurants', False),             # "צימרים ↔ מסעדות מקומיות"
    ('hair_salons', 'cosmetics', False),
    ('cosmetics', 'aesthetics', False),
    ('aesthetics', 'nails', False),
    ('dental', 'clinics_physio', False),
    ('vets', 'pet_shops', True),                  # marked cross_vertical in appendix B
    ('renovation', 'electrical', False),
    ('electrical', 'plumbing', False),
    ('plumbing', 'hvac', False),
    ('locksmiths', 'renovation', False),
    ('moving', 'renovation', False),
    ('gyms', 'personal_training', False),
    ('personal_training', 'clinics_physio', False),
    ('photographers', 'design_branding', False),
    ('design_branding', 'digital_marketing', False),
    ('fashion', 'jewelry', False),
    ('fashion', 'furniture_interior', True),      # the owner, 2026-11-15 20:24: interior design -> fashion,
    ('jewelry', 'furniture_interior', True),      # jewelry and realty (cross_vertical, as appendix B marks it)
    ('realty', 'renovation', False),
    ('realty', 'furniture_interior', True),       # the owner, 2026-11-15 20:24 (replaces renovation -> interior design)
)

# Lines of appendix B this module does NOT turn into links, each with the reason. Never guessed into existence.
UNRESOLVED: tuple[tuple[str, str], ...] = (
    ('קליניקות ↔ פיזיותרפיה',
     'שתי הקטגוריות הן אחת בנספח א׳ ("קליניקות ופיזיותרפיה"). The owner, 2026-11-15: the line is removed, '
     'not a category added to justify it'),
)


class CatalogError(ValueError):
    pass


def _known(slug: str) -> bool:
    return slug in CATEGORIES or slug in RESERVE or slug in LEGACY


def check(slug: str) -> str:
    """The slug, or a loud failure. Nothing outside the appendices is a category."""
    if not _known(slug):
        raise CatalogError(f'{slug!r} is not in the catalogue (appendix A, appendix C or the legacy vertical)')
    return slug


def collectable(slug: str) -> bool:
    """A category the platform collects references for: appendix A only (the reserve is not collected for)."""
    return slug in CATEGORIES


def neighbours(slug: str) -> list[tuple[str, bool]]:
    """(neighbour, cross_vertical) in rank order: the order appendix B writes them."""
    check(slug)
    out = []
    for a, b, cross in LINKS:
        other = b if a == slug else a if b == slug else None
        if other is not None and other not in {n for n, _ in out}:
            out.append((other, cross))
    return out


def _validate() -> None:
    for a, b, _ in LINKS:
        for slug in (a, b):
            if not _known(slug):
                raise CatalogError(f'appendix B names {slug!r}, which is in no appendix')
        if a == b:
            raise CatalogError(f'a category is never adjacent to itself: {a!r}')
    for a, b, cross in LINKS:
        for slug in (a, b):
            if slug in RESERVE and not cross:
                raise CatalogError(f'{slug!r} is a reserve category: it is reachable only as a cross_vertical link')
    if len(CATEGORIES) != 32:   # appendix A's 30 + butcher + interior design (the owner, 2026-11-15 20:12)
        raise CatalogError(f'the catalogue has 32 categories, not {len(CATEGORIES)}')


_validate()


def rows_for_store() -> list[tuple[str, list[tuple[str, bool]]]]:
    """What a store's category_adjacency should hold: one row per (category, neighbour) in rank order."""
    return [(slug, neighbours(slug)) for slug in CATEGORIES if neighbours(slug)]
