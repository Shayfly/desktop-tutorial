"""Identity of everything 148AI tells its models and checks with, for a fixed set of briefs (Michael 2026-11-10).

Model output is not deterministic, so "byte-identical output" can never be the test. What CAN be frozen is every
input the pipeline gives the models and every check it judges with:
  * the role instructions (architect, generator, repair, evolution, reviewer system prompts incl. skill guidance)
  * the reviewer checklist and the static probes that run
  * the sandbox scripts (behavioural acceptance runner + driver, visual QA, preview smoke)
  * the verification chain (stage classes, in order)
  * for each frozen-run brief: the deterministic contract scope (acceptance floor and waived kinds), the fact canon
`digest()` hashes them; with every flag off it must equal the digest recorded at the baseline commit.
"""
from __future__ import annotations

import hashlib
import json

# The five frozen-run briefs (docs/frozen-run-20261110.md). The cafe and florist texts are the real ones.
ARM_BRIEFS = {
    'restaurant': ('אני רוצה דף נחיתה בעברית לעסק שלי. שם העסק: קפה "בוקר טוב" – בית קפה שכונתי כתובת: רחוב הנביאים 12, '
                   'חיפה טלפון ו-WhatsApp: 050-1234567 שעות פתיחה: א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור. '
                   'שלוש ביקורות של לקוחות: • "הקפה הכי טוב בחיפה" – דנה • "ארוחת בוקר מושלמת, נחזור" – יוסי ומיכל '
                   '• "שירות חם ומחירים הוגנים" – אבי. בלי הרשמה, בלי התחברות ובלי תשלום.'),
    'florist-hard': ('תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים", ברח\' נתיב המזלות 22, ירושלים.\n'
                     'שיהיה יפה, ורוד וירוק, לא משהו כבד.\n'
                     'שיהיה כפתור להתקשר 052-1234567 וכפתור וואטסאפ לאותו מספר, עם הודעה מוכנה "היי, אשמח להזמין זר".\n'
                     "אנחנו פתוחים א'–ה' 8:00–19:00, ו' 8:00–13:00, שבת סגור.\n"
                     'שיהיה קטע עם מה שאומרים עלינו, ורשימה של זרים לחתונה, ליומולדת ולניחומים.\n'
                     'ותכתוב שאפשר גם להזמין משלוח באותו יום.'),
    'florist-new': ('תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים", בירושלים.\nשיהיה יפה, ורוד וירוק, לא משהו כבד.\n'
                    'שיהיה קטע עם מה שאומרים עלינו, ורשימה של זרים לחתונה, ליומולדת ולניחומים.'),
    'negative': 'אפליקציית אייפון נייטיב עם תשלומים בתוך האפליקציה ו-Apple Pay',
    'saas-with-login': 'מערכת לניהול תורים לקוסמטיקאית עם התחברות ללקוחות ולמנהלת, לקוחה קובעת ומבטלת תור.',
}


def components() -> dict:
    from . import autonomous_agents as agents
    from . import behavior_acceptance, preview_smoke, visual_qa
    from .fact_canon import build_canon
    from .product_architect import content_only_approved, no_login_requested
    from .product_evolution import __dict__ as evo
    from .skills_runtime import WEB_SKILLS, checklist_for_review
    from .web_saas_acceptance import WEB_SAAS_REQUIRED_KINDS
    prompts = {name: getattr(agents, name) for name in sorted(dir(agents))
               if name.endswith('_SYSTEM') and isinstance(getattr(agents, name), str)}
    prompts.update({f'evolution.{k}': v for k, v in sorted(evo.items()) if k.endswith('_SYSTEM') and isinstance(v, str)})
    arms = {}
    for arm, text in ARM_BRIEFS.items():
        arms[arm] = {'no_login': no_login_requested(text), 'content_only': content_only_approved(text),
                     'canon': build_canon(text).to_dict()}
    return {
        'prompts': prompts,
        'skills': [{'key': s.key, 'version': s.version, 'roles': list(s.roles), 'guidance': s.guidance,
                    'checklist': list(s.checklist), 'probes': [c.__name__ for c in s.static_checks]} for s in WEB_SKILLS],
        'review_checklist': checklist_for_review(),
        'required_kinds': list(WEB_SAAS_REQUIRED_KINDS),
        'scripts': {'behavior_runner': behavior_acceptance._RUNNER_SOURCE, 'behavior_driver': behavior_acceptance._SCRIPT,
                    'visual_qa': visual_qa.SCRIPT, 'preview_smoke': preview_smoke._SMOKE},
        'arms': arms,
    }


def digest() -> str:
    body = json.dumps(components(), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    print(digest())
