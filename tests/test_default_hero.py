"""DECISIONS 5 (owner 2026-11-17): a content site with no customer photo gets one generated main image by default;
the approved brief's text-logo line no longer asks for a generated icon."""
from omni_prod.media_pipeline import AssetKind, CreativeDirector, default_hero
from omni_prod.rehearsal import approved_prompt

ANSWERS = {"content_only": "yes", "personal_data": "no", "login": "none"}


def _plan(request):
    return [(r.kind, r.purpose, r.required) for r in CreativeDirector().plan(approved_prompt(request, ANSWERS)).requests]


def test_content_site_without_photo_gets_an_optional_hero():
    plan = _plan('אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה. טלפון 04-8123456.')
    assert (AssetKind.IMAGE, 'hero/brand visual', False) in plan


def test_text_logo_line_of_the_brief_does_not_order_an_icon():
    plan = _plan('אתר לאטליז "בשר השכונה" ברחוב הרצל 12, חיפה.')
    assert not [p for p in plan if p[0] == AssetKind.ICON]


def test_customer_who_asks_for_a_logo_still_gets_an_icon():
    assert [p for p in _plan('אתר לאטליז עם לוגו מעוצב') if p[0] == AssetKind.ICON]


def test_no_pictures_means_no_default_hero():
    assert not default_hero(approved_prompt('אתר לאטליז בלי תמונות בכלל', ANSWERS))


def test_uploaded_photo_means_no_default_hero():
    p = approved_prompt('אתר לאטליז. 148ai-asset://upload/abc.jpg', ANSWERS)
    assert not default_hero(p)


def test_not_a_content_site_means_no_default_hero():
    assert not default_hero('Build a todo app with login')
