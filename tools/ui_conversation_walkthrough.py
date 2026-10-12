"""Real-browser walk-through of the conversation workspace (Wave A).

    OMNI_UI_BASE=http://127.0.0.1:8148 python3 tools/ui_conversation_walkthrough.py <screenshot dir>

Runs against a real server (FastAPI + PostgreSQL with migrations through 036).
Registers a throw-away account, holds a Hebrew and an English conversation,
drags/enlarges/closes the preview, collapses the sidebar, reloads (persistence),
switches projects, and takes desktop (1440x900) and mobile (390x844)
screenshots. The interpreter is the deterministic one: no model is called.
`bypass_csp` only lets the test's own wait functions run; the page itself
keeps its Content-Security-Policy."""
import json, sys, time, uuid
from playwright.sync_api import sync_playwright

import os
BASE = os.getenv('OMNI_UI_BASE', 'http://127.0.0.1:8148')
OUT = sys.argv[1]
email = f'ui-{uuid.uuid4().hex[:6]}@example.com'
log = []

def shot(page, name):
    page.screenshot(path=f'{OUT}/{name}.png', full_page=False)
    log.append(name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='he-IL', bypass_csp=True)
    page = ctx.new_page()
    errors = []
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.goto(BASE)
    page.fill('#email', email); page.fill('#password', 'a-long-password-123')
    page.click('#registerBtn')
    page.wait_for_selector('#workspaceView:not([hidden])')
    page.wait_for_selector('#emptyProjects:not([hidden])')
    shot(page, '01-desktop-first-project-he')
    page.fill('#firstProjectName', 'מספרה של דני'); page.click('#firstProjectForm button[type=submit]')
    page.wait_for_selector('.welcomeChat'); page.wait_for_load_state('networkidle')
    shot(page, '02-desktop-empty-chat-he')
    page.fill('#chatInput', 'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון. בצבע ירוק')
    page.keyboard.press('Enter')
    page.wait_for_selector('.bubble.assistant')
    page.wait_for_selector('.quick .opts button')
    shot(page, '03-desktop-chat-question-he')
    page.click('.quick .opts button:has-text("כן")')
    page.wait_for_function("document.querySelectorAll('.bubble.assistant').length >= 2")
    page.wait_for_selector('.quick .opts button')
    page.click('.quick .opts button:has-text("זה כלי פנימי")')
    page.wait_for_function("document.querySelectorAll('.bubble.assistant').length >= 3")
    time.sleep(1.5)
    shot(page, '04-desktop-plan-ready-he')
    tabs = page.eval_on_selector_all('#ctxTabs button', 'els => els.map(e => e.textContent)')
    page.click('#ctxTabs button:has-text("תוכנית ועלות")')
    time.sleep(0.5)
    shot(page, '05-desktop-plan-tab-he')
    page.click('#ctxTabs button:has-text("תוכנית ועלות")')  # close
    page.fill('#chatInput', 'אפשר להוסיף תשלומים בהמשך?'); page.keyboard.press('Enter')
    page.wait_for_function("document.querySelectorAll('.bubble.assistant').length >= 4")
    page.fill('#chatInput', 'כמה זה יעלה?'); page.keyboard.press('Enter')
    page.wait_for_function("document.querySelectorAll('.bubble.assistant').length >= 5")
    time.sleep(0.5)
    shot(page, '06-desktop-feasibility-cost-he')
    # splitter drag: preview grows
    before = page.eval_on_selector('#stage', 'e => e.getBoundingClientRect().width')
    sp = page.eval_on_selector('#splitter', 'e => { const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }')
    page.mouse.move(*sp); page.mouse.down(); page.mouse.move(sp[0] + 250, sp[1], steps=8); page.mouse.up()
    after = page.eval_on_selector('#stage', 'e => e.getBoundingClientRect().width')
    shot(page, '07-desktop-preview-resized')
    page.click('#expandPreviewBtn'); time.sleep(0.3)
    maxw = page.eval_on_selector('#stage', 'e => e.getBoundingClientRect().width')
    shot(page, '08-desktop-preview-enlarged')
    page.keyboard.press('Escape'); time.sleep(0.2)
    page.click('#closePreviewBtn'); time.sleep(0.2)
    hidden = page.eval_on_selector('#stage', 'e => getComputedStyle(e).display')
    page.click('#togglePreviewBtn'); time.sleep(0.2)
    reopened = page.eval_on_selector('#stage', 'e => getComputedStyle(e).display')
    # 2026-10-11: with three working areas the project list starts as a drawer
    # below 1600 px; open it first, then collapse it again.
    if page.is_visible('#sbOpen'):
        page.click('#sbOpen'); time.sleep(0.3)
    page.click('#sbCollapse'); time.sleep(0.3)
    shot(page, '09-desktop-sidebar-collapsed')
    page.click('#sbOpen'); time.sleep(0.3)
    # persistence: reload -> the same conversation comes back from the server
    page.reload(); page.wait_for_selector('.bubble.assistant')
    n_after_reload = page.eval_on_selector_all('.bubble', 'els => els.length')
    # English
    page.click('#langBtn2'); time.sleep(0.4)
    page.click('#sbNew') if page.query_selector('#sbNew') else page.click('#newProjectTopBtn')
    page.fill('#newProjectName', 'Equipment loans'); page.click('#newProjectCreate')
    page.wait_for_selector('.welcomeChat'); page.wait_for_load_state('networkidle')
    page.fill('#chatInput', 'I need a simple internal tool for my team to track equipment loans, in English, no login, no personal data')
    page.keyboard.press('Enter')
    page.wait_for_selector('.bubble.assistant'); time.sleep(1.2)
    shot(page, '10-desktop-chat-en')
    projects = page.eval_on_selector_all('#sbProjects button .ttl', 'els => els.map(e => e.textContent)')
    page.fill('#sbSearch', 'מספרה'); time.sleep(0.2)
    filtered = page.eval_on_selector_all('#sbProjects button .ttl', 'els => els.map(e => e.textContent)')
    page.fill('#sbSearch', '')
    # switch back to the first project from the sidebar
    page.click('#sbProjects button:has-text("מספרה")'); page.wait_for_selector('.bubble.assistant'); time.sleep(0.6)
    first_project_msgs = page.eval_on_selector_all('.bubble', 'els => els.length')
    page.click('#langBtn2'); time.sleep(0.3)
    # mobile
    m = b.new_context(viewport={'width': 390, 'height': 844}, storage_state=ctx.storage_state(), is_mobile=True, has_touch=True, bypass_csp=True)
    mp = m.new_page(); mp.goto(BASE); mp.wait_for_selector('.bubble.assistant'); time.sleep(0.8)
    mp.screenshot(path=f'{OUT}/11-mobile-chat-he.png'); log.append('11-mobile-chat-he')
    mp.click('#sbOpen'); time.sleep(0.4)
    mp.screenshot(path=f'{OUT}/12-mobile-sidebar-he.png'); log.append('12-mobile-sidebar-he')
    mp.click('#sbScrim', position={'x': 20, 'y': 420}); time.sleep(0.3)
    # 2026-10-11: on phones the bottom tabs (Chat / Preview / Edit) replace the header toggle.
    mp.click('#mobileTabs [data-pane="preview"]' if mp.is_visible('#mobileTabs') else '#togglePreviewBtn'); time.sleep(0.4)
    mp.screenshot(path=f'{OUT}/13-mobile-preview-he.png'); log.append('13-mobile-preview-he')
    hscroll = mp.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    print(json.dumps({'shots': log, 'tabs': tabs, 'stage_width_before': before, 'after_drag': after, 'enlarged': maxw,
                      'closed_display': hidden, 'reopened_display': reopened, 'bubbles_after_reload': n_after_reload,
                      'projects': projects, 'search_filtered': filtered, 'first_project_bubbles_after_switch': first_project_msgs,
                      'mobile_horizontal_scroll': hscroll, 'console_errors': errors[:10]}, ensure_ascii=False, indent=1))
    b.close()
