'use strict';
/* Visual Edit + image attachments (founder directive 2026-10-11).

   Point at something in the live preview (mouse or touch) or mark it on a
   screenshot, say what to change, and the change goes through the EXISTING
   modification pipeline (candidate -> checks -> accept/reject -> version ->
   preview). Nothing here edits code itself, guesses an element, or claims an
   image was "understood": image analysis is not enabled, and the UI says so.

   Shares app.js globals (S, T, api, h, t, $, pid, explain, ...). */

Object.assign(T.he, {
  attachImage: 'צירוף תמונה או צילום מסך', attachedImage: 'תמונה מצורפת', removeImage: 'הסרת התמונה',
  imgType: 'אפשר לצרף רק PNG, JPEG או WebP.', imgTooBig: 'התמונה גדולה מדי גם אחרי הקטנה (עד 3MB).',
  imgMax: 'אפשר לצרף עד 6 תמונות להודעה.', imgUploading: 'מעלה תמונות…',
  editTitle: 'עריכה', hideEditor: 'סגירת העריכה', showEditor: 'עריכה', resizeEditor: 'גרירה לשינוי רוחב העריכה',
  pickElement: 'בחירת רכיב לעריכה', picking: 'מצב בחירה: לחצו (או הקישו) על החלק שתרצו לשנות. Esc לביטול.',
  stopPicking: 'סיום בחירה',
  inspectorMissing: 'בחירה ישירה בתצוגה עדיין לא זמינה בשרת התצוגות הזה. אפשר לצרף צילום מסך ולסמן עליו, או לתאר במילים.',
  edPick: '1. מה לשנות?', edPickHint: 'לחצו "בחירת רכיב" ואז על החלק בתצוגה שתרצו לשנות. בטלפון — הקישו עליו.',
  edShot: 'או: צילום מסך עם סימון', edShotAdd: 'צירוף צילום מסך', annotTools: 'כלי סימון', annotCanvas: 'צילום המסך — גררו כדי לסמן',
  toolRect: 'מסגרת', toolDraw: 'ציור', toolClear: 'ניקוי', remove: 'הסרה',
  edWhat: '2. מה לעשות?', edWhatPh: 'לדוגמה: שיהיה ירוק וגדול יותר', edSend: 'ביצוע השינוי',
  selected: 'נבחר', clearSel: 'ביטול', foundAt: 'נמצא בקוד', notFound: 'לא מצאתי את הרכיב בקוד בוודאות. אפשר לתאר במילים מה לשנות — לא אשנה רכיב משוער.',
  ambiguous: 'הרכיב מופיע בכמה מקומות. באיזה מהם מדובר?', noneOfThese: 'אף אחד מאלה — אתאר במילים',
  chooseOne: 'בחרו קודם באיזה מקום מדובר (או "אף אחד מאלה").', needWhat: 'כתבו בקצרה מה לשנות.',
  needVersion: 'אין עדיין גרסה לשנות. בנו את המוצר קודם.', changeRunning: 'כבר רץ שינוי. חכו שיסתיים.',
  edQueued: 'השינוי נשלח. בונים גרסה מועמדת ומריצים את הבדיקות…', edReview: 'הגרסה המועמדת עברה את הבדיקות. לאשר?',
  edAccepted: 'השינוי אושר ונשמר כגרסה חדשה.', edFailed: 'השינוי לא הצליח: ', compare: 'השוואה לפני / אחרי',
  compareOff: 'סגירת ההשוואה', undo: 'ביטול השינוי', undoConfirm: 'לחזור לגרסה שלפני השינוי? תיווצר גרסה חדשה זהה לה.',
  undone: 'חזרנו לגרסה שלפני השינוי.', before: 'לפני', after: 'אחרי', cmpStarting: 'מפעילים תצוגה של הגרסה הקודמת…',
  paneChat: 'שיחה', panePreview: 'תצוגה', paneEdit: 'עריכה', shotNote: 'צילום המסך נשמר בפרויקט ונשלח עם השינוי כהקשר (בלי ניתוח תמונה אוטומטי).',
  k_button: 'כפתור', k_a: 'קישור', k_input: 'שדה', k_textarea: 'שדה טקסט', k_select: 'רשימה', k_img: 'תמונה', k_h: 'כותרת',
  k_p: 'פסקה', k_li: 'פריט ברשימה', k_label: 'תווית', k_nav: 'תפריט', k_form: 'טופס', k_table: 'טבלה', k_any: 'רכיב',
  inPage: p => `בעמוד ${p}`, selectedDesc: 'הרכיב שנבחר', near: x => `ליד "${x}"`, inFile: f => `בקובץ ${f}`,
});
Object.assign(T.en, {
  attachImage: 'Attach an image or screenshot', attachedImage: 'Attached image', removeImage: 'Remove image',
  imgType: 'Only PNG, JPEG or WebP images can be attached.', imgTooBig: 'The image is too large even after resizing (3 MB max).',
  imgMax: 'Up to 6 images per message.', imgUploading: 'Uploading images…',
  editTitle: 'Edit', hideEditor: 'Close editing', showEditor: 'Edit', resizeEditor: 'Drag to resize the editing panel',
  pickElement: 'Pick an element', picking: 'Picking: click (or tap) the part you want to change. Esc to cancel.',
  stopPicking: 'Stop picking',
  inspectorMissing: 'Picking directly in the preview is not available on this preview server yet. Attach a screenshot and mark it, or describe it.',
  edPick: '1. What to change?', edPickHint: 'Press "Pick an element", then click the part of the preview to change. On a phone, tap it.',
  edShot: 'Or: a screenshot with a mark', edShotAdd: 'Attach a screenshot', annotTools: 'Marking tools', annotCanvas: 'Screenshot — drag to mark',
  toolRect: 'Box', toolDraw: 'Draw', toolClear: 'Clear', remove: 'Remove',
  edWhat: '2. What should happen?', edWhatPh: 'For example: make it green and larger', edSend: 'Make the change',
  selected: 'Selected', clearSel: 'Clear', foundAt: 'Found in the code', notFound: 'I could not find this element in the code with certainty. Describe the change in words — I will not change a guessed element.',
  ambiguous: 'This element appears in several places. Which one?', noneOfThese: 'None of these — I will describe it',
  chooseOne: 'First choose which place you mean (or "None of these").', needWhat: 'Write briefly what to change.',
  needVersion: 'There is no version to change yet. Build the product first.', changeRunning: 'A change is already running. Wait for it to finish.',
  edQueued: 'Change sent. Building a candidate version and running the checks…', edReview: 'The candidate passed its checks. Accept it?',
  edAccepted: 'Change accepted and saved as a new version.', edFailed: 'The change did not succeed: ', compare: 'Compare before / after',
  compareOff: 'Close comparison', undo: 'Undo the change', undoConfirm: 'Go back to the version before this change? A new identical version is created.',
  undone: 'Back to the version before the change.', before: 'Before', after: 'After', cmpStarting: 'Starting a preview of the previous version…',
  paneChat: 'Chat', panePreview: 'Preview', paneEdit: 'Edit', shotNote: 'The screenshot is saved in the project and sent with the change as context (no automatic image analysis).',
  k_button: 'Button', k_a: 'Link', k_input: 'Field', k_textarea: 'Text field', k_select: 'List', k_img: 'Image', k_h: 'Heading',
  k_p: 'Paragraph', k_li: 'List item', k_label: 'Label', k_nav: 'Menu', k_form: 'Form', k_table: 'Table', k_any: 'Element',
  inPage: p => `on page ${p}`, selectedDesc: 'The selected element', near: x => `near "${x}"`, inFile: f => `in ${f}`,
});

const VE = (() => {
  const MAX_IMAGES = 6, MAX_BYTES = 3 * 1024 * 1024, MAX_SIDE = 2000;
  const TYPES = ['image/png', 'image/jpeg', 'image/webp'];
  const st = { pending: [], inspecting: false, ready: false, origin: null, selection: null, located: null, chosen: null,
               describe: false, shot: null, tool: 'rect', pane: 'chat', compare: false, lastStatus: null, timer: null };
  const ws = () => $('workspaceView');
  const mobile = () => matchMedia('(max-width:900px)').matches;

  /* ---------- images (chat + screenshot) ---------- */
  function loadImage(blob) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(blob); const img = new Image();
      img.onload = () => resolve({ img, url }); img.onerror = () => { URL.revokeObjectURL(url); reject(new Error(t('imgType'))); };
      img.src = url;
    });
  }
  function toBlob(canvas, type, q) { return new Promise(r => canvas.toBlob(r, type, q)); }
  // Photos are always re-encoded: that drops camera metadata (location) and
  // keeps uploads small; small PNG screenshots are kept as they are.
  async function prepare(file) {
    if (!TYPES.includes(file.type)) throw new Error(t('imgType'));
    const { img, url } = await loadImage(file);
    let w = img.naturalWidth, h0 = img.naturalHeight;
    const keep = file.type === 'image/png' && file.size <= 2.5 * 1024 * 1024 && Math.max(w, h0) <= 2400;
    if (keep) return { blob: file, url, w, h: h0, img };
    const scale = Math.min(1, MAX_SIDE / Math.max(w, h0));
    const c = document.createElement('canvas'); c.width = Math.round(w * scale); c.height = Math.round(h0 * scale);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    let blob = await toBlob(c, 'image/jpeg', 0.85);
    if (blob && blob.size > MAX_BYTES) blob = await toBlob(c, 'image/jpeg', 0.6);
    if (!blob || blob.size > MAX_BYTES) { URL.revokeObjectURL(url); throw new Error(t('imgTooBig')); }
    URL.revokeObjectURL(url);
    const small = await loadImage(blob);
    return { blob, url: small.url, w: c.width, h: c.height, img: small.img };
  }
  function b64(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader(); r.onload = () => resolve(String(r.result).split(',', 2)[1]); r.onerror = reject; r.readAsDataURL(blob);
    });
  }
  async function upload(blob, kind, annotation) {
    return api(`/api/v28/projects/${pid()}/attachments`, { method: 'POST', body: { kind, data_base64: await b64(blob), annotation: annotation || null } });
  }
  async function addFiles(files) {
    $('composerMsg').textContent = '';
    for (const f of files) {
      if (st.pending.length >= MAX_IMAGES) { $('composerMsg').textContent = t('imgMax'); break; }
      try { st.pending.push(await prepare(f)); } catch (e) { $('composerMsg').textContent = e.message; }
    }
    renderTray();
  }
  function renderTray() {
    const tray = $('attachTray'); tray.hidden = !st.pending.length;
    tray.replaceChildren(...st.pending.map((p, i) => h('figure', {},
      h('img', { src: p.url, alt: t('attachedImage') }),
      h('button', { type: 'button', 'aria-label': t('removeImage'), title: t('removeImage'), onclick: () => {
        URL.revokeObjectURL(p.url); st.pending.splice(i, 1); renderTray(); } }, '✕'),
      h('figcaption', {}, `${Math.max(1, Math.round(p.blob.size / 1024))}KB`))));
  }
  async function uploadPending() {
    $('composerMsg').textContent = t('imgUploading');
    const ids = [];
    for (const p of st.pending) {
      // Retain successful uploads across a failed send/partial upload retry.
      if(p.uploadedProject !== S.projectId){p.uploadedId=null;p.uploadedProject=S.projectId;}
      if(!p.uploadedId)p.uploadedId=(await upload(p.blob,'image')).id;
      ids.push(p.uploadedId);
    }
    $('composerMsg').textContent = '';
    return ids;
  }
  function clearPending() { st.pending.forEach(p => URL.revokeObjectURL(p.url)); st.pending = []; renderTray(); }

  /* ---------- preview inspector (postMessage, origin-checked both ways) ---------- */
  function previewOrigin() {
    try { return S.preview && S.preview.preview_url ? new URL(S.preview.preview_url).origin : null; } catch { return null; }
  }
  function hello() {
    const f = $('previewFrame'); st.origin = previewOrigin();
    if (!st.origin || !f.contentWindow) return;
    try { f.contentWindow.postMessage({ type: '148ai:hello' }, st.origin); } catch { /* frame not ready */ }
  }
  function onMessage(ev) {
    const f = $('previewFrame');
    if (!st.origin || ev.origin !== st.origin || ev.source !== f.contentWindow) return;
    const d = ev.data || {};
    if (d.type === '148ai:ready') { st.ready = true; render(); }
    if (d.type === '148ai:selection' && d.selection) { setInspect(false); onSelection(d.selection); }
    if (d.type === '148ai:cancel') setInspect(false);
  }
  function setInspect(on, retried) {
    const f = $('previewFrame');
    if (on && !st.ready && !retried) {   // the inspector answers "hello" once its script has loaded
      hello(); setTimeout(() => setInspect(true, true), 900); return;
    }
    st.inspecting = Boolean(on) && st.ready;
    if (st.origin && f.contentWindow) try { f.contentWindow.postMessage({ type: '148ai:inspect', enabled: st.inspecting }, st.origin); } catch { /* */ }
    const bar = $('inspectBar');
    if (on && !st.ready) {
      bar.hidden = false; bar.className = 'inspectBar warn'; bar.replaceChildren(h('span', {}, t('inspectorMissing')));
    } else if (st.inspecting) {
      bar.hidden = false; bar.className = 'inspectBar';
      bar.replaceChildren(h('span', {}, t('picking')), h('button', { type: 'button', class: 'ghost', onclick: () => setInspect(false) }, t('stopPicking')));
      if (mobile()) setPane('preview');
    } else bar.hidden = true;
    render();
  }
  const KIND = { button: 'k_button', a: 'k_a', input: 'k_input', textarea: 'k_textarea', select: 'k_select', img: 'k_img',
    h1: 'k_h', h2: 'k_h', h3: 'k_h', h4: 'k_h', h5: 'k_h', h6: 'k_h', p: 'k_p', li: 'k_li', label: 'k_label', nav: 'k_nav', form: 'k_form', table: 'k_table' };
  const friendly = s => {
    const name = s.text || (s.attrs && (s.attrs['aria-label'] || s.attrs.placeholder || s.attrs.alt || s.attrs.name)) || '';
    return `${t(KIND[s.tag] || 'k_any')}${name ? ` "${name.slice(0, 60)}"` : ''}`;
  };
  async function onSelection(sel) {
    st.selection = sel; st.located = null; st.chosen = null; st.describe = false; $('edMsg').textContent = '';
    if (mobile()) setPane('edit');
    render();
    const vid = currentVersionId(); if (!vid) return;
    try {
      st.located = await api(`/api/v28/projects/${pid()}/versions/${encodeURIComponent(vid)}/visual-edit/locate`, { method: 'POST', body: { selection: sel } });
    } catch (e) { st.located = { status: 'ERROR', error: explain(e), candidates: [] }; }
    render();
    $('edInstruction').focus();
  }

  /* ---------- screenshot + marking (rectangles / free drawing) ---------- */
  const canvas = () => $('annotCanvas');
  function drawShot() {
    const sh = st.shot; const c = canvas(); if (!sh) return;
    c.width = sh.w; c.height = sh.h;
    const g = c.getContext('2d'); g.drawImage(sh.img, 0, 0, sh.w, sh.h);
    const lw = Math.max(3, Math.round(sh.w / 300));
    g.lineWidth = lw; g.strokeStyle = '#E5484D'; g.lineJoin = g.lineCap = 'round';
    for (const r of sh.regions) g.strokeRect(r.x, r.y, r.w, r.h);
    for (const p of sh.paths) { g.beginPath(); p.forEach((pt, i) => i ? g.lineTo(pt.x, pt.y) : g.moveTo(pt.x, pt.y)); g.stroke(); }
  }
  function toImage(ev) {
    const c = canvas(); const r = c.getBoundingClientRect();
    return { x: Math.max(0, Math.min(st.shot.w, (ev.clientX - r.left) * st.shot.w / r.width)),
             y: Math.max(0, Math.min(st.shot.h, (ev.clientY - r.top) * st.shot.h / r.height)) };
  }
  function wireCanvas() {
    const c = canvas(); let start = null, path = null;
    c.addEventListener('pointerdown', ev => {
      if (!st.shot) return; c.setPointerCapture(ev.pointerId); const p = toImage(ev);
      if (st.tool === 'rect') start = p; else { path = [p]; st.shot.paths.push(path); }
    });
    c.addEventListener('pointermove', ev => {
      if (!st.shot) return; const p = toImage(ev);
      if (path) { path.push(p); drawShot(); }
      else if (start) { drawShot(); const g = c.getContext('2d'); g.setLineDash([8, 6]); g.strokeRect(start.x, start.y, p.x - start.x, p.y - start.y); g.setLineDash([]); }
    });
    c.addEventListener('pointerup', ev => {
      if (!st.shot) return; const p = toImage(ev);
      if (start) {
        const r = { x: Math.round(Math.min(start.x, p.x)), y: Math.round(Math.min(start.y, p.y)),
                    w: Math.round(Math.abs(p.x - start.x)), h: Math.round(Math.abs(p.y - start.y)) };
        if (r.w >= 4 && r.h >= 4 && st.shot.regions.length < 20) st.shot.regions.push(r);
      }
      start = null; path = null; drawShot(); render();
    });
  }
  async function setShot(file) {
    $('edMsg').textContent = '';
    try { const p = await prepare(file); st.shot = { ...p, regions: [], paths: [] }; }
    catch (e) { $('edMsg').textContent = e.message; return; }
    $('annot').hidden = false; drawShot(); render();
  }
  async function shotBlob() {
    drawShot();   // the uploaded picture is what the person sees: image + marks
    return toBlob(canvas(), 'image/png');
  }

  /* ---------- send the change through the existing modification pipeline ---------- */
  async function send() {
    const msg = $('edMsg'); msg.className = 'msg'; msg.textContent = '';
    const text = $('edInstruction').value.trim();
    if (text.length < 3) { msg.textContent = t('needWhat'); return; }
    if (!currentVersionId()) { msg.textContent = t('needVersion'); return; }
    if (modActive()) { msg.textContent = t('changeRunning'); return; }
    const loc = st.located;
    if (st.selection && loc && loc.status === 'AMBIGUOUS' && !st.chosen && !st.describe) { msg.textContent = t('chooseOne'); return; }
    const extra = {};
    let instruction = text;
    if (st.selection && loc && (loc.status === 'UNIQUE' || st.chosen) && !st.describe)
      extra.target = { selection: st.selection, candidate: st.chosen };
    else if (st.selection)   // not located with certainty: describe it, never target a guess
      instruction += `\n(${t('selectedDesc')}: ${friendly(st.selection)}${st.selection.page ? ', ' + t('inPage')(st.selection.page) : ''})`;
    $('edSend').disabled = true;
    try {
      if (st.shot) {
        let blob = await shotBlob();
        if (blob && blob.size > MAX_BYTES) blob = await toBlob(canvas(), 'image/jpeg', 0.85);
        const a = await upload(blob, 'screenshot', { regions: st.shot.regions, strokes: st.shot.paths.length, note: text.slice(0, 500) });
        extra.attachment_ids = [a.id];
      }
      $('followup').value = instruction;
      const sent = await sendModification(extra);
      if (sent && extra.attachment_ids) {   // the marked screenshot went with THIS change
        st.shotSentFor = sent.modification_id; if (st.shot) URL.revokeObjectURL(st.shot.url); st.shot = null; $('annot').hidden = true;
      }
      st.lastStatus = null; watch();
    } catch (e) {
      if (e.status === 409 && e.detail && e.detail.locate) { st.located = { ...e.detail.locate, selection: st.selection }; msg.textContent = t('chooseOne'); }
      else msg.textContent = explain(e);
    } finally { $('edSend').disabled = false; render(); }
  }
  function watch() {
    clearInterval(st.timer);
    st.timer = setInterval(() => { const s = S.mod && S.mod.status; if (s !== st.lastStatus) { st.lastStatus = s; renderResult(); } }, 700);
  }

  /* ---------- before / after + undo (existing previews and rollback) ---------- */
  async function previewFor(versionId) {
    const d = await api(`/api/v28/projects/${pid()}/versions/${encodeURIComponent(versionId)}/previews`, { method: 'POST' });
    const id = d.preview_id || d.id;
    for (let i = 0; i < 90; i++) {
      const p = await api(`/api/v28/projects/${pid()}/previews/${encodeURIComponent(id)}`);
      if (p.status === 'RUNNING') {
        const a = await api(`/api/v28/projects/${pid()}/previews/${encodeURIComponent(id)}/access`, { method: 'POST' });
        return a.url;
      }
      if (['FAILED', 'NOT_PREVIEWABLE', 'EXPIRED', 'STOPPED'].includes(p.status)) throw new Error(p.error_message || p.status);
      await new Promise(r => setTimeout(r, 2000));
    }
    throw new Error('timeout');
  }
  async function toggleCompare() {
    st.compare = !st.compare;
    const stage = $('stage'); stage.classList.toggle('comparing', st.compare);
    $('cmpPane').hidden = !st.compare; $('cmpAfterLabel').hidden = !st.compare;
    if (mobile() && st.compare) setPane('preview');
    renderResult();
    if (!st.compare || !S.lastChange) return;
    const wait = $('cmpWait'); wait.hidden = false; wait.textContent = t('cmpStarting'); $('compareFrame').hidden = true;
    try { const url = await previewFor(S.lastChange.before); $('compareFrame').src = url; $('compareFrame').hidden = false; wait.hidden = true; }
    catch (e) { wait.textContent = explain(e); }
  }
  async function undo() {
    if (!S.lastChange || !window.confirm(t('undoConfirm'))) return;
    const before = S.lastChange.before;
    try {   // the existing rollback: re-commits the exact stored files of `before` as a new version
      await api(`/api/v28/projects/${pid()}/rollback`, { method: 'POST', body: { target_version_id: before, message: 'undo visual edit' } });
    } catch (e) { $('edMsg').className = 'msg'; $('edMsg').textContent = explain(e); return; }
    await loadVersions();
    if (st.compare) await toggleCompare();
    S.lastChange = null;
    if (currentVersionId()) startPreview(currentVersionId());
    $('edResult').hidden = false; $('edResult').replaceChildren(h('p', { class: 'msg ok' }, t('undone')));
  }

  /* ---------- layout: panes, editor width, mobile tabs ---------- */
  function setPane(p) {
    st.pane = p; ws().dataset.pane = p;
    document.querySelectorAll('#mobileTabs button[data-pane]').forEach(b => b.setAttribute('aria-pressed', b.dataset.pane === p ? 'true' : 'false'));
  }
  function setEditWidth(px) {
    const v = Math.max(240, Math.min(480, px));
    document.documentElement.style.setProperty('--edit-w', `${v}px`);
    try { localStorage.setItem('148ai_edit_w', String(v)); } catch { /* convenience only */ }
  }

  /* ---------- rendering ---------- */
  function renderSelection() {
    const box = $('edSelection'); const s = st.selection;
    if (!s) { box.replaceChildren(); return; }
    const kids = [h('div', { class: 'selChip' }, h('span', {}, `${t('selected')}: `), h('b', { dir: 'auto' }, friendly(s)),
      h('button', { type: 'button', class: 'ghost', onclick: () => { st.selection = null; st.located = null; st.chosen = null; render(); } }, t('clearSel')))];
    const loc = st.located;
    if (loc && loc.status === 'UNIQUE') {
      const c = loc.candidates[0];
      kids.push(h('p', { class: 'found' }, `${t('foundAt')}: `, h('code', {}, `${c.file}:${c.line}`)));
    } else if (loc && loc.status === 'AMBIGUOUS') {
      kids.push(h('p', { class: 'hint' }, t('ambiguous')), h('ul', { class: 'cands' },
        ...loc.candidates.map(c => h('li', {}, h('label', {},
          h('input', { type: 'radio', name: 'cand', checked: st.chosen && st.chosen.file === c.file && st.chosen.line === c.line,
            onchange: () => { st.chosen = { file: c.file, line: c.line }; st.describe = false; } }),
          h('span', {}, h('b', {}, c.context ? t('near')(c.context) : t('inFile')(c.page)),
            h('small', { class: 'hint' }, ' · ', t('inFile')(c.page)),
            h('details', { class: 'tech' }, h('summary', {}, t('techDetails')), h('code', { dir: 'ltr' }, `${c.file}:${c.line}`), h('pre', {}, c.snippet)))))),
        h('li', {}, h('label', {}, h('input', { type: 'radio', name: 'cand', checked: st.describe, onchange: () => { st.describe = true; st.chosen = null; } }),
          h('span', {}, t('noneOfThese'))))));
    } else if (loc && (loc.status === 'NOT_FOUND' || loc.status === 'ERROR')) {
      kids.push(h('p', { class: 'hint' }, loc.error || t('notFound')));
    }
    box.replaceChildren(...kids);
  }
  function renderResult() {
    const box = $('edResult'); const m = S.mod;
    const kids = [];
    if (m && m.id && ['QUEUED', 'RUNNING'].includes(m.status)) kids.push(h('p', { class: 'hint' }, t('edQueued')));
    else if (m && m.status === 'READY_FOR_REVIEW') kids.push(h('p', {}, t('edReview')), h('div', { class: 'edResultRow' },
      h('button', { type: 'button', onclick: () => decideMod(true) }, t('accept')),
      h('button', { type: 'button', class: 'secondary', onclick: () => decideMod(false) }, t('reject'))));
    else if (m && ['FAILED', 'ERROR', 'CLARIFICATION_REQUIRED', 'NEEDS_CLARIFICATION', 'CONFLICT'].includes(m.status))
      kids.push(h('p', { class: 'msg' }, t('edFailed') + (m.error_message || m.classification_reason || m.status)));
    if (S.lastChange) {
      if (m && m.status === 'ACCEPTED') kids.push(h('p', { class: 'msg ok' }, t('edAccepted')));
      kids.push(h('div', { class: 'edResultRow' },
        h('button', { type: 'button', class: 'secondary', 'aria-pressed': st.compare ? 'true' : 'false', onclick: toggleCompare }, st.compare ? t('compareOff') : t('compare')),
        h('button', { type: 'button', class: 'ghost danger', onclick: undo }, t('undo'))));
    }
    if (m && m.id && st.shotSentFor === m.id) kids.push(h('p', { class: 'hint' }, t('shotNote')));
    box.hidden = !kids.length; box.replaceChildren(...kids);
  }
  function render() {
    if (!$('editor')) return;
    const running = S.preview && S.preview.status === 'RUNNING';
    const canPick = Boolean(running && currentVersionId());
    for (const b of [$('edPickBtn'), $('inspectToggle')]) {
      b.disabled = !canPick; b.setAttribute('aria-pressed', st.inspecting ? 'true' : 'false');
      b.textContent = st.inspecting ? t('stopPicking') : t('pickElement');
    }
    $('edSend').disabled = !currentVersionId();
    renderSelection(); renderResult();
    const eb = $('editorToggle');
    if (eb) eb.setAttribute('aria-expanded', ws().classList.contains('editor-hidden') ? 'false' : 'true');
  }
  function onPreview() {
    const running = S.preview && S.preview.status === 'RUNNING';
    if (!running) { st.ready = false; st.inspecting = false; $('inspectBar').hidden = true; }
    render();
  }
  function onChangeAccepted() { st.lastStatus = null; watch(); renderResult(); }
  function reset() {
    clearPending(); clearInterval(st.timer);
    Object.assign(st, { inspecting: false, ready: false, selection: null, located: null, chosen: null, describe: false, shot: null, compare: false });
    if ($('annot')) { $('annot').hidden = true; $('stage').classList.remove('comparing'); $('cmpPane').hidden = true; $('cmpAfterLabel').hidden = true;
      $('inspectBar').hidden = true; $('edInstruction').value = ''; $('edMsg').textContent = ''; }
  }

  function wire() {
    window.addEventListener('message', onMessage);
    $('previewFrame').addEventListener('load', () => { st.ready = false; st.inspecting = false; hello(); setTimeout(hello, 600); render(); });
    $('attachBtn').addEventListener('click', () => $('attachInput').click());
    $('attachInput').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    // Paste or drop a screenshot straight into the conversation.
    $('chatInput').addEventListener('paste', e => {
      const files = [...(e.clipboardData && e.clipboardData.files || [])].filter(f => f.type.startsWith('image/'));
      if (files.length) { e.preventDefault(); addFiles(files); }
    });
    $('chatCol').addEventListener('dragover', e => { if ([...e.dataTransfer.types].includes('Files')) e.preventDefault(); });
    $('chatCol').addEventListener('drop', e => { const f = [...e.dataTransfer.files]; if (f.length) { e.preventDefault(); addFiles(f); } });
    for (const b of [$('edPickBtn'), $('inspectToggle')]) b.addEventListener('click', () => setInspect(!st.inspecting));
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && st.inspecting) setInspect(false); });
    $('edShotBtn').addEventListener('click', () => $('edShotInput').click());
    $('edShotInput').addEventListener('change', e => { if (e.target.files[0]) setShot(e.target.files[0]); e.target.value = ''; });
    document.querySelectorAll('#annot [data-tool]').forEach(b => b.addEventListener('click', () => {
      st.tool = b.dataset.tool; document.querySelectorAll('#annot [data-tool]').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    }));
    $('annotClear').addEventListener('click', () => { if (st.shot) { st.shot.regions = []; st.shot.paths = []; drawShot(); } });
    $('annotRemove').addEventListener('click', () => { if (st.shot) URL.revokeObjectURL(st.shot.url); st.shot = null; $('annot').hidden = true; render(); });
    wireCanvas();
    $('edSend').addEventListener('click', send);
    // Editor show/hide (desktop) and a button for it next to "Preview".
    const toggle = h('button', { class: 'ghost', id: 'editorToggle', type: 'button', 'aria-controls': 'editor', 'data-i18n': 'showEditor' }, t('showEditor'));
    $('togglePreviewBtn').after(toggle);
    toggle.addEventListener('click', () => {
      if (mobile()) { setPane('edit'); return; }
      ws().classList.toggle('editor-hidden');
      try { localStorage.setItem('148ai_editor', ws().classList.contains('editor-hidden') ? 'hidden' : 'shown'); } catch { /* */ }
      render();
    });
    $('editorClose').addEventListener('click', () => { ws().classList.add('editor-hidden'); try { localStorage.setItem('148ai_editor', 'hidden'); } catch { /* */ } render(); });
    try {
      if (localStorage.getItem('148ai_editor') === 'hidden') ws().classList.add('editor-hidden');
      const w = Number(localStorage.getItem('148ai_edit_w')); if (w) setEditWidth(w);
      // Three working areas need the room: the project list starts as a drawer
      // on screens narrower than 1600 px unless the person opened it before.
      if (window.innerWidth < 1600 && !localStorage.getItem('148ai_sb') && !localStorage.getItem('148ai_sb_open')) ws().classList.add('sb-collapsed');
    } catch { /* defaults */ }
    syncSidebar();
    $('sbOpen').addEventListener('click', () => { try { localStorage.setItem('148ai_sb_open', '1'); } catch { /* */ } });
    // Mobile: Chat / Preview / Edit.
    document.querySelectorAll('#mobileTabs button[data-pane]').forEach(b => b.addEventListener('click', () => setPane(b.dataset.pane)));
    $('togglePreviewBtn').addEventListener('click', () => { if (mobile()) setPane(st.pane === 'preview' ? 'chat' : 'preview'); });
    $('closePreviewBtn').addEventListener('click', () => { if (mobile()) setPane('chat'); });
    setPane('chat');
    // The editor separator: drag (pointer) or arrow keys.
    const sp = $('editSplitter'); const rtl = () => document.documentElement.dir === 'rtl';
    sp.addEventListener('pointerdown', e => {
      sp.setPointerCapture(e.pointerId); sp.classList.add('drag');
      const frames = [$('previewFrame'), $('compareFrame')]; frames.forEach(f => { f.style.pointerEvents = 'none'; });
      const move = ev => { const r = ws().getBoundingClientRect(); setEditWidth(rtl() ? ev.clientX - r.left : r.right - ev.clientX); };
      const up = () => { sp.classList.remove('drag'); frames.forEach(f => { f.style.pointerEvents = ''; }); sp.removeEventListener('pointermove', move); sp.removeEventListener('pointerup', up); };
      sp.addEventListener('pointermove', move); sp.addEventListener('pointerup', up);
    });
    sp.addEventListener('keydown', e => {
      const cur = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--edit-w')) || 300;
      const grow = (e.key === 'ArrowLeft') !== rtl() ? 1 : -1;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); setEditWidth(cur + 16 * grow); }
    });
    render();
  }
  document.addEventListener('DOMContentLoaded', wire);
  return { onPreview, onChangeAccepted, reset, render, pendingCount: () => st.pending.length, uploadPending, clearPending,
           _state: st, _locate: onSelection, setPane };
})();
window.VE = VE;
