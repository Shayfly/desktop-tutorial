"""QUESTIONS-001 / WP1: what each artifact kind needs in order to exist -- and how THIS request changes it.

The declaration says which fields a kind needs, their explicit default and their base impact. Whether a field is
material FOR THIS REQUEST, and in which order the missing ones come, is derived from the request (gaps.Spec):
  implies  the request already implies a value -> not material here: the value is assumed and shown, not asked
  raises   the request makes the field more uncertain or more consequential -> it moves up
  confirm  sensitive fields (privacy, data model, who may enter): an implied value is proposed and confirmed,
           never silently assumed (these are the discovery questions that may not be defaulted)
Values are neutral codes (the discovery option values), so a question in Hebrew or Arabic leaves no English label.
Cue words are listed for Hebrew, Arabic and English; a model interpretation (any language) supplies stated values.
"""
from __future__ import annotations

from dataclasses import dataclass

_BUSINESS = (r'לקוחות|למספרה|לעסק|לחנות|למסעדה|למשרד|לסטודיו|לקליניקה|תיירים|customers|clients|tourists|'
             r'for my (?:shop|bakery|business|salon|restaurant|studio|clinic|barbershop)|'
             r'زبائن|عملاء|لمتجري|لصالون|لمطعمي|لعيادتي|للسياح|سياح')
_TEAM = r'לצוות|לעובדים|פנימי|for (?:my|our) team|internal|staff only|لفريقي|للموظفين|داخلي'
_ABROAD = r'תיירים|תייר|בינלאומי|חו"ל|מחו"ל|tourists|international|abroad|foreign visitors|سياح|دولي|من الخارج'
_LOOK = r'מושך את העין|מיתוג|יוקרתי|מעוצב|eye-?catching|branding|luxury|stylish|جذاب|فاخر|أنيق'
_RECORDS = (r'תור|תורים|הזמנ|הרשמ|טופס|טלפון|מייל|appointment|booking|reservation|register|sign[- ]?up|form|phone|'
            r'e-?mail|موعد|مواعيد|حجز|تسجيل|نموذج|هاتف|بريد')
_SHOWCASE = r'אתר תדמית|תספר (?:קצת )?על|לספר על|דף נחיתה|landing page|brochure|about (?:us|my business)|موقع تعريفي|صفحة هبوط'
_ACCOUNT = r'אזור אישי|החשבון שלי|ייכנסו עם|משתמשים רשומים|my account|user accounts|members|حسابي|حساب شخصي|الأعضاء'


@dataclass(frozen=True)
class Field:
    name: str            # the discovery field name (the interpreter proposes these)
    material: bool       # material for the kind (before the request is read)
    default: str         # explicit; used when not material here, or when the customer delegates
    reason: str          # neutral reason code: what a wrong value changes (phrased per language)
    base: int = 1        # base impact for ordering
    implies: tuple[tuple[str, str], ...] = ()   # (value, cue pattern)
    raises: tuple[tuple[int, str], ...] = ()    # (boost, cue pattern)
    confirm: bool = False


_COMMON = (
    Field('audience', True, 'public', 'who_reads', 3, implies=(('public', _BUSINESS), ('internal', _TEAM))),
    # The conversation's language implies the product's (LANG-001), unless the request says it serves people from abroad.
    Field('languages', True, 'he', 'text_direction', 2, implies=(('__conversation__', ''),), raises=((6, _ABROAD),)),
    Field('style', True, 'clean', 'look_and_feel', 1, raises=((3, _LOOK),)),
    Field('color', False, 'blue', 'brand_colour'),
    Field('font', False, 'heebo', 'typeface'),
    Field('logo', False, 'text', 'header_logo'),
    Field('references', False, 'none', 'inspiration'),
)
_SITE = (
    Field('content_only', True, 'yes', 'saves_records', 4, confirm=True, implies=(('no', _RECORDS), ('yes', _SHOWCASE))),
    Field('login', True, 'none', 'who_can_enter', 1, implies=(('none', ''),), raises=((4, _ACCOUNT),)),
)
_APP = (
    Field('login', True, 'none', 'who_can_enter', 2, raises=((4, _ACCOUNT),)),
    Field('personal_data', True, 'no', 'what_is_stored', 3, confirm=True, raises=((5, _RECORDS),)),
    Field('dates', False, 'future_year', 'date_rules'),
    Field('duplicates', False, 'block', 'duplicate_rules'),
)
# Discovery questions that become relevant only through other answers (e.g. personal data without sign-in).
# Every discovery question that may never be defaulted is also a candidate here, so the detector -- not the old
# questionnaire -- decides when it is asked (a kind that does not declare it still gets it when discovery has it open).
CONDITIONAL = {f.name: f for f in (
    Field('access_scope', True, 'internal_link', 'link_scope', 6, confirm=True),
    Field('personal_data', True, 'no', 'what_is_stored', 3, confirm=True, implies=(('no', _SHOWCASE),),
          raises=((5, _RECORDS),)),
    Field('login', True, 'none', 'who_can_enter', 2, raises=((4, _ACCOUNT),)),
    Field('content_only', True, 'yes', 'saves_records', 4, confirm=True, implies=(('no', _RECORDS), ('yes', _SHOWCASE))),
)}

ARTIFACT_FIELDS: dict[str, tuple[Field, ...]] = {
    'website': _COMMON + _SITE,
    'web_app': _COMMON + _APP,
}


def fields_for(kind: str) -> tuple[Field, ...]:
    """The declaration for a kind; an unsupported kind declares nothing (nothing is built, nothing is asked)."""
    return ARTIFACT_FIELDS.get(kind, ())
