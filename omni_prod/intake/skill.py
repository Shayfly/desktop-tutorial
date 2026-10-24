"""M7 intake skill: the discovery questions as the agent's knowledge, not a form (founder 2026-10-24).

The form asked each question in turn. Here every question is a SKILL ENTRY the agent reasons with:
what to listen for in the customer's words, what to assume (and show as "הנחנו") when nothing was said,
and whether the question may be asked at all. A question is asked only when all three hold (rule 7):

  build_blocking   the build cannot be planned correctly without it
  ambiguous        the customer's words do not settle it (decided per conversation by the agent)
  changes_artifact a wrong value changes what is built (code, data model, checks), not only a label

The question texts stay those of `discovery.QUESTIONS` (read, never changed here), so the wording the
customer already knows is kept; this module adds the agent's knowledge around them.
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import discovery as d


@dataclass(frozen=True)
class SkillEntry:
    field: str
    build_blocking: bool
    changes_artifact: bool
    artifact_effect: str             # what a wrong value changes in the product
    assume_he: str                   # how the default is shown ("הנחנו: ...")
    assume_value: object
    propose_he: str = ''             # how the question is phrased as a proposal to correct, not an interrogation

    @property
    def question(self) -> d.Question | None:
        return d.BY_ID.get(self.field)

    def askable(self) -> bool:
        return self.build_blocking and self.changes_artifact


# One entry per discovery question (all of them; content_only is the product-kind question).
ENTRIES: dict[str, SkillEntry] = {e.field: e for e in (
    SkillEntry('audience', False, False, 'who the copy addresses', 'הקהל: הלקוחות של העסק', 'public'),
    SkillEntry('goal', False, True, 'the main action gets the most prominent place',
               'המטרה: מה שתיארת בהודעה הראשונה', '__from_request__'),
    SkillEntry('login', True, True, 'sign-in code, sessions and who may see what',
               'בלי התחברות — מי שיש לו את הקישור נכנס', 'none',
               'הנחתי שאין צורך בהתחברות. אם צריך שכל משתמש ייכנס עם סיסמה — תגיד.'),
    SkillEntry('personal_data', True, True, 'storage of personal details and who may see them',
               'לא נשמרים פרטים אישיים', 'no',
               'הנחתי שנשמרים רק הפרטים של הפעולה עצמה, בלי טלפון או מייל. אם צריך לשמור פרטי קשר — תגיד.'),
    SkillEntry('content_only', True, True, 'whether there is a data model and record APIs (data_create) at all',
               'אתר תוכן: מציג מידע, לא שומר כלום מהמבקרים', 'yes',
               'הבנתי שהאתר מציג מידע ולא שומר כלום מהמבקרים. אם יש טופס שנשמר, הזמנות או רשימה שמתעדכנת — תגיד.'),
    SkillEntry('access_scope', True, True, 'public pages vs a private link',
               'קישור פרטי — רק אתה מקבל אותו', 'internal_link',
               'הנחתי שהקישור פרטי ורק אתה מקבל אותו. אם זה צריך להיות פתוח לציבור — תגיד.'),
    SkillEntry('screens', False, True, 'page structure', 'המסכים: לפי מה שתיארת', '__from_request__'),
    SkillEntry('languages', False, True, 'text direction and labels', 'עברית, מימין לשמאל', 'he'),
    SkillEntry('content', False, False, 'the initial texts', 'התוכן: מה שכתבת, השאר נכתוב ותוכל לתקן', '__from_request__'),
    SkillEntry('dates', False, True, 'date validation rules', 'תאריכים: מהיום ועד שנה קדימה', 'future_year'),
    SkillEntry('duplicates', False, True, 'duplicate handling on the server', 'כפילויות נחסמות עם הסבר', 'block'),
    SkillEntry('style', False, False, 'visual style only', 'סגנון נקי ומודרני', 'clean'),
    SkillEntry('color', False, False, 'colours only', 'צבע ראשי כחול', 'blue'),
    SkillEntry('font', False, False, 'font only', 'גופן Heebo', 'heebo'),
    SkillEntry('logo', False, False, 'the header logo', 'לוגו טקסט עם שם העסק', 'text'),
    SkillEntry('references', False, False, 'inspiration only', 'בלי אתר השראה', 'אין'),
)}


def entry(field: str) -> SkillEntry:
    return ENTRIES[field]


def coverage() -> tuple[set[str], set[str]]:
    """(discovery questions without a skill entry, skill entries without a discovery question): both must be empty."""
    q = {x.field for x in d.QUESTIONS}
    return q - set(ENTRIES), set(ENTRIES) - q
