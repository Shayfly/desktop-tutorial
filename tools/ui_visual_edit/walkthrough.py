"""Real-browser walkthrough: Conversation UX + attachments + Visual Edit.

Real: FastAPI app, PostgreSQL (migrations through 038), conversation supervisor,
attachments API, locate, modification API (queue + accept + rollback), preview
API with real access tokens, and the real preview router wrapped by the
inspector (TLS). Test-only substitutes, stated in the evidence:
  * object storage = local files (S3/R2 not exercised here);
  * the preview "container" is a local process (no Docker daemon here);
  * the modification CANDIDATE is written by this harness (no model call):
    the worker's model step is not exercised; accept/rollback/preview are real.
"""
import hashlib, json, os, sys, time, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.environ['UX'])
from common import DB, LocalFileStore
from omni_prod.db import DatabasePool
from omni_prod.modification_repository import PostgresModificationRepository
from omni_prod.product_spec import ProductSpec
from omni_prod.spec_repository import PostgresSpecRepository
from omni_prod.workspace import PostgresProjectWorkspace

BASE = 'http://127.0.0.1:8148'
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
FIX = Path(__file__).resolve().parent / 'fixture'
pool = DatabasePool(DB)
ws = PostgresProjectWorkspace(pool, LocalFileStore())
specs = PostgresSpecRepository(pool)
mods = PostgresModificationRepository(pool)
R = {'checks': {}, 'shots': [], 'console_errors': [], 'notes': []}
email = f've-{uuid.uuid4().hex[:6]}@example.com'


def call(pg, method, path, body=None):
    """fetch() from the page itself (same-origin session cookie)."""
    return pg.evaluate("""async ([m, u, b]) => { const r = await fetch(u, { method: m, credentials: 'same-origin',
        headers: b ? { 'Content-Type': 'application/json' } : {}, body: b ? JSON.stringify(b) : undefined });
        const t = await r.text(); let j = null; try { j = JSON.parse(t); } catch (e) {}
        return { status: r.status, json: j, headers: Object.fromEntries(r.headers.entries()) }; }""", [method, path, body])


def wait_js(pg, expr, timeout=20000):
    """page.wait_for_function needs eval (blocked by the app's real CSP); poll instead."""
    end = time.time() + timeout / 1000
    while time.time() < end:
        try:
            if pg.evaluate(f'() => Boolean({expr})'):
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError(expr)


def check(name, ok, detail=''):
    R['checks'][name] = {'ok': bool(ok), 'detail': str(detail)[:400]}
    print(('PASS ' if ok else 'FAIL ') + name, detail if not ok else '', flush=True)


def shot(page, name):
    page.screenshot(path=str(OUT / f'{name}.png')); R['shots'].append(name)


def key_for(owner, project):
    return 'tenant_' + hashlib.sha256((owner + '\0' + project).encode()).hexdigest()[:24]


def fixture_repo():
    return {str(p.relative_to(FIX)): p.read_text() for p in FIX.rglob('*') if p.is_file()}


SPEC = ProductSpec.from_dict({'title': 'השאלת ציוד', 'summary': 'מעקב השאלות ציוד לצוות', 'stack': ['python'],
                              'requirements': [{'id': 'R1', 'text': 'רישום השאלה חדשה'}],
                              'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'השאלה נשמרת ומופיעה ברשימה'}]})

with sync_playwright() as p:
    b = p.chromium.launch(args=['--host-resolver-rules=MAP *.prv.148ai.test 127.0.0.1', '--no-proxy-server'])
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, locale='he-IL', ignore_https_errors=True)
    page = ctx.new_page()
    page.on('console', lambda m: R['console_errors'].append(m.text) if m.type == 'error' else None)
    page.goto(BASE)
    page.fill('#email', email); page.fill('#password', 'a-long-password-123'); page.click('#registerBtn')
    page.wait_for_selector('#emptyProjects:not([hidden])')
    page.fill('#firstProjectName', 'השאלת ציוד'); page.click('#firstProjectForm button[type=submit]')
    page.wait_for_selector('.welcomeChat')
    me = call(page, 'GET', '/api/v28/me')['json']
    project = call(page, 'GET', '/api/v28/projects')['json']['projects'][0]['id']
    key = key_for(me['id'], project)
    # Synthetic test account on a paid PLAN (internal credits only; the queued
    # change is never consumed by a worker here, so no model is called).
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute("INSERT INTO creator_subscriptions(user_id,plan_code,cycle,credits_used,provider_spend_usd) "
                         "VALUES(%s,'pro',to_char(now(),'YYYY-MM'),0,0) ON CONFLICT(user_id) DO UPDATE SET plan_code='pro'", (me['id'],))

    # --- 1. conversation: short, material questions; image attached ---------
    page.fill('#chatInput', 'אני רוצה מערכת להשאלת ציוד לצוות שלי, בלי התחברות, נשמור שם של העובד')
    page.keyboard.press('Enter'); page.wait_for_selector('.bubble.assistant')
    first = page.inner_text('.bubble.assistant >> nth=-1')
    check('conversation_reply_short', len(first) < 420, len(first))
    page.fill('#chatInput', 'לא יודע'); page.keyboard.press('Enter')
    wait_js(page, "document.querySelectorAll('.bubble.assistant').length >= 2")
    second = page.inner_text('.bubble.assistant >> nth=-1')
    check('unsure_gets_reason_not_repeat', 'למה אני שואל' in second and second != first, second[:120])
    shot(page, '01-desktop-conversation-he')
    png = OUT / '_sample.png'
    page.screenshot(path=str(png), clip={'x': 0, 'y': 0, 'width': 800, 'height': 500})
    page.set_input_files('#attachInput', str(png))
    page.wait_for_selector('#attachTray figure img')
    shot(page, '02-desktop-image-attached-before-send')
    page.click('#attachTray figure button'); check('attachment_removable', page.locator('#attachTray figure').count() == 0)
    page.set_input_files('#attachInput', str(png)); page.wait_for_selector('#attachTray figure img')
    page.fill('#chatInput', 'ככה נראה הטופס שלנו היום'); page.keyboard.press('Enter')
    page.wait_for_selector('.bubble.customer .thumbs img')
    wait_js(page, "document.querySelector('.bubble.customer .thumbs img').naturalWidth > 0")
    reply = page.inner_text('.bubble.assistant >> nth=-1')
    check('image_in_thread_and_honest_note', 'ניתוח תמונה' in reply, reply[-140:])
    shot(page, '03-desktop-image-in-conversation')
    atts = call(page, 'GET', f'/api/v28/projects/{project}/attachments')['json']['attachments']
    check('attachment_stored_not_analyzed', len(atts) == 1 and atts[0]['analysis']['state'] == 'NOT_ANALYZED', atts)

    # --- 2. a version exists (fixture product) -> real preview through the router
    v1 = ws.commit(project_id=key, repository=fixture_repo(), message='fixture product (UI test)')
    specs.save(version_id=v1.id, project_id=key, spec=SPEC)
    page.reload(); page.wait_for_selector('#previewEmpty button')
    page.click('#previewEmpty button')
    page.wait_for_selector('#previewFrame:not([hidden])', timeout=30000)
    frame = page.frame_locator('#previewFrame')
    frame.locator('#save-btn').wait_for(timeout=30000)
    wait_js(page, "!document.getElementById('edPickBtn').disabled")
    shot(page, '04-desktop-three-panes-preview')
    # layout: chat right, preview centre, editor left (RTL)
    xs = {k: page.eval_on_selector(sel, 'e => e.getBoundingClientRect().x') for k, sel in
          (('chat', '#chatCol'), ('stage', '#stage'), ('editor', '#editor'))}
    check('layout_chat_right_preview_centre_editor_left', xs['chat'] > xs['stage'] > xs['editor'], xs)

    # --- 3. pick an element in the live preview ---------------------------
    page.click('#edPickBtn')
    page.wait_for_selector('#inspectBar:not([hidden])')
    check('inspector_ready', 'מצב בחירה' in page.inner_text('#inspectBar'), page.inner_text('#inspectBar'))
    frame.locator('#save-btn').hover(); time.sleep(0.3)
    shot(page, '05-desktop-picking-hover')
    frame.locator('#save-btn').click()
    page.wait_for_selector('#edSelection .found code')
    found = page.inner_text('#edSelection .found code')
    want = next(i for i, l in enumerate((FIX / 'templates/index.html').read_text().splitlines(), 1) if 'save-btn' in l)
    check('locate_unique_to_source_line', found == f'templates/index.html:{want}', found)
    page.fill('#edInstruction', 'שהכפתור יהיה ירוק ובולט יותר')
    shot(page, '06-desktop-element-selected')
    page.click('#edSend')
    page.wait_for_selector('#edResult:not([hidden])')
    with pool.connection() as conn:
        row = conn.execute("SELECT id, followup, status FROM modification_requests WHERE project_id = %s ORDER BY created_at DESC LIMIT 1",
                           (key,)).fetchone()
    check('targeted_change_entered_existing_pipeline', row and f'templates/index.html (around line {want})' in row[1]
          and row[1].startswith('שהכפתור יהיה ירוק') and row[2] == 'QUEUED', row and row[1][:300])
    shot(page, '07-desktop-change-queued')
    mod_id = row[0]

    # --- 4. ambiguous element: the person is asked, nothing is guessed -----
    page.click('#edPickBtn'); page.wait_for_selector('#inspectBar:not([hidden])')
    frame.locator('button.btn:not(.primary)').click()
    page.wait_for_selector('#edSelection .cands')
    n = page.locator('#edSelection .cands li').count()
    check('ambiguous_lists_candidates_plus_describe', n == 3, n)
    shot(page, '08-desktop-ambiguous-asks')
    res = call(page, 'POST', f'/api/v28/projects/{project}/versions/{v1.id}/modifications', {
        'followup': 'make it red', 'target': {'selection': {'tag': 'button', 'classes': ['btn'], 'text': 'ביטול'}}})
    check('server_refuses_guessed_target_409', res['status'] == 409 and res['json']['detail']['error'] == 'target_ambiguous', res)
    page.click('#edSelection .selChip button')

    # --- 5. candidate ready (harness writes it: no model) -> accept -> compare -> undo
    cand = fixture_repo()
    cand['static/style.css'] += '\n#save-btn{background:#1E7B4A;border-color:#1E7B4A;font-weight:700;padding:.6rem 1.4rem}\n'
    mods.transition_running(mod_id)
    mods.complete(mod_id, project_id=key, status='READY_FOR_REVIEW', classification='change_request',
                  classification_reason='UI test harness candidate (no model call)', billable=False,
                  candidate_repository=cand, candidate_spec=SPEC, evidence_json={'source': 'ui-test-harness'})
    page.wait_for_selector('#edResult button:has-text("אישור השינוי")', timeout=20000)
    shot(page, '09-desktop-review-candidate')
    page.click('#edResult button:has-text("אישור השינוי")')
    page.wait_for_selector('#edResult button:has-text("השוואה")', timeout=20000)
    vers = call(page, 'GET', f'/api/v28/projects/{project}/history')['json']['versions']
    check('accepted_as_new_version', len(vers) == 2, len(vers))
    wait_js(page, "document.getElementById('previewFrame').dataset.access && !document.getElementById('previewFrame').hidden", timeout=30000)
    frame.locator('#save-btn').wait_for(timeout=30000)
    page.click('#edResult button:has-text("השוואה")')
    page.wait_for_selector('#compareFrame:not([hidden])', timeout=40000)
    page.frame_locator('#compareFrame').locator('#save-btn').wait_for(timeout=30000)
    time.sleep(0.8)
    after_bg = frame.locator('#save-btn').evaluate('e => getComputedStyle(e).backgroundColor')
    before_bg = page.frame_locator('#compareFrame').locator('#save-btn').evaluate('e => getComputedStyle(e).backgroundColor')
    check('compare_shows_before_and_after', after_bg != before_bg, f'after={after_bg} before={before_bg}')
    shot(page, '10-desktop-compare-before-after')
    page.once('dialog', lambda d: d.accept())
    page.click('#edResult button:has-text("ביטול השינוי")')
    page.wait_for_selector('#edResult .msg.ok, #edMsg:not(:empty)', timeout=30000)
    R['notes'].append('undo message: ' + page.inner_text('#edMsg'))
    vers = call(page, 'GET', f'/api/v28/projects/{project}/history')['json']['versions']
    newest = sorted(vers, key=lambda v: v['created_at'])[-1]
    restored = ws.get(project_id=key, version_id=newest['id']).repository()
    check('undo_restores_exact_previous_files', restored == fixture_repo() and len(vers) == 3, (len(vers), R['notes'][-1]))
    shot(page, '11-desktop-undone')

    # --- 6. screenshot + marking --------------------------------------------
    page.set_input_files('#edShotInput', str(png))
    page.wait_for_selector('#annot:not([hidden])')
    box = page.eval_on_selector('#annotCanvas', 'e => { const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }')
    page.mouse.move(box[0] + box[2] * .2, box[1] + box[3] * .3); page.mouse.down()
    page.mouse.move(box[0] + box[2] * .6, box[1] + box[3] * .6, steps=6); page.mouse.up()
    page.click('#annot [data-tool="draw"]')
    page.mouse.move(box[0] + box[2] * .7, box[1] + box[3] * .2); page.mouse.down()
    page.mouse.move(box[0] + box[2] * .85, box[1] + box[3] * .35, steps=6); page.mouse.up()
    check('screenshot_note_not_claimed_before_send', 'נשמר בפרויקט ונשלח' not in page.inner_text('#editor'))
    shot(page, '12-desktop-screenshot-marked')
    page.fill('#edInstruction', 'האזור המסומן צפוף מדי — להוסיף רווח')
    page.click('#edSend')
    page.wait_for_selector('#edResult p.hint >> text=צילום המסך נשמר', timeout=20000)
    with pool.connection() as conn:
        f = conn.execute("SELECT followup FROM modification_requests WHERE project_id = %s ORDER BY created_at DESC LIMIT 1",
                         (key,)).fetchone()[0]
    check('marked_screenshot_travels_with_the_change', '[Attached images' in f and 'marked regions (px)' in f
          and 'not analyzed automatically' in f, f[-300:])
    shot(page, '12b-desktop-screenshot-change-sent')

    # --- 7. resize the editor; hide/show --------------------------------------
    w0 = page.eval_on_selector('#editor', 'e => e.getBoundingClientRect().width')
    sp = page.eval_on_selector('#editSplitter', 'e => { const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + 200]; }')
    page.mouse.move(*sp); page.mouse.down(); page.mouse.move(sp[0] + 100, sp[1], steps=6); page.mouse.up()
    w1 = page.eval_on_selector('#editor', 'e => e.getBoundingClientRect().width')
    check('editor_resizable', w1 > w0 + 50, (w0, w1))

    # --- 8. mobile: Chat / Preview / Edit, tap to select ---------------------
    m = b.new_context(viewport={'width': 390, 'height': 844}, locale='he-IL', ignore_https_errors=True,
                      is_mobile=True, has_touch=True, storage_state=ctx.storage_state())
    mp = m.new_page()
    mp.on('console', lambda msg: R['console_errors'].append('mobile: ' + msg.text) if msg.type == 'error' else None)
    mp.goto(BASE); mp.wait_for_selector('#mobileTabs')
    shot(mp, '13-mobile-chat')
    mp.click('#mobileTabs [data-pane="preview"]')
    mp.wait_for_selector('#previewEmpty button, #previewFrame:not([hidden])')
    if mp.locator('#previewEmpty button').count() and mp.locator('#previewEmpty button').is_visible():
        mp.click('#previewEmpty button')
    mp.wait_for_selector('#previewFrame:not([hidden])', timeout=30000)
    mp.frame_locator('#previewFrame').locator('#save-btn').wait_for(timeout=30000)
    shot(mp, '14-mobile-preview')
    mp.click('#mobileTabs [data-pane="edit"]'); wait_js(mp, "!document.getElementById('edPickBtn').disabled")
    shot(mp, '15-mobile-edit')
    mp.click('#edPickBtn')
    mp.wait_for_selector('#inspectBar:not([hidden])')
    check('mobile_pick_switches_to_preview', mp.eval_on_selector('#workspaceView', 'e => e.dataset.pane') == 'preview')
    mp.frame_locator('#previewFrame').locator('h1.title').tap()
    mp.wait_for_selector('#edSelection .selChip')
    check('mobile_tap_selects_and_returns_to_edit', mp.eval_on_selector('#workspaceView', 'e => e.dataset.pane') == 'edit')
    shot(mp, '16-mobile-tapped-selection')
    scroll = mp.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check('mobile_no_horizontal_scroll', scroll <= 0, scroll)

    # --- 9. isolation: another account cannot reach the image ---------------
    other = b.new_context(); op = other.new_page(); op.goto(BASE)
    call(op, 'POST', '/api/v28/auth/register', {'email': f'other-{uuid.uuid4().hex[:6]}@example.com', 'password': 'a-long-password-123'})
    r1 = call(op, 'GET', f'/api/v28/projects/{project}/attachments/{atts[0]["id"]}')
    r2 = call(op, 'DELETE', f'/api/v28/projects/{project}/attachments/{atts[0]["id"]}')
    check('other_account_cannot_read_or_delete_image', r1['status'] in (403, 404) and r2['status'] in (403, 404), (r1['status'], r2['status']))
    r3 = call(page, 'GET', f'/api/v28/projects/{project}/attachments/{atts[0]["id"]}')
    check('owner_reads_image_with_safe_headers', r3['status'] == 200 and r3['headers'].get('x-content-type-options') == 'nosniff'
          and 'sandbox' in r3['headers'].get('content-security-policy', ''), r3['headers'])
    bad = call(page, 'POST', f'/api/v28/projects/{project}/attachments', {'kind': 'image', 'data_base64': 'PHN2Zz48L3N2Zz4='})
    check('svg_refused', bad['status'] == 415, bad['status'])
    b.close()

R['console_errors'] = [e for e in R['console_errors'] if 'favicon' not in e]
R['passed'] = sum(1 for c in R['checks'].values() if c['ok']); R['total'] = len(R['checks'])
R['substitutes'] = ['object storage: local files (S3/R2 not exercised)', 'preview container: local process (no Docker daemon)',
                    'modification candidate written by the harness (no model call); accept/rollback/preview real']
(OUT / 'walkthrough_result.json').write_text(json.dumps(R, ensure_ascii=False, indent=2))
print(json.dumps({k: R[k] for k in ('passed', 'total')}), 'console errors:', R['console_errors'][:5])
