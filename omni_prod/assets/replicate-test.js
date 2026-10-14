'use strict';
const path = '/api/v28/providers/replicate/image-test';
const el = id => document.getElementById(id);
let busy = false, submitted = false, timer;
async function api(method = 'GET') {
  const response = await fetch(path, {method, credentials:'same-origin',
    headers: method === 'POST' ? {'Content-Type':'application/json'} : {},
    body: method === 'POST' ? JSON.stringify({confirmed:true}) : undefined});
  const data = await response.json();
  if (!response.ok) throw new Error(response.status === 401 ? 'צריך להיכנס לחשבון 148AI דרך הקישור למעלה ואז לחזור לכאן.' : data.detail || 'הבדיקה אינה זמינה כרגע.');
  return data;
}
function render(data) {
  submitted = data.status !== 'NOT_STARTED';
  el('start').disabled = busy || submitted || !el('confirm').checked;
  const messages = {NOT_STARTED:'מוכן לבדיקה. עדיין לא נוצרה תמונה בתשלום.',
    SUBMITTED:'הבקשה נשלחה. ממתינים לתמונה…', QUEUED:'התמונה ממתינה בתור…',
    RUNNING:'Replicate יוצר את התמונה…', FAILED:'יצירת התמונה נכשלה. לא נשלח ניסיון נוסף.',
    CANCELLED:'יצירת התמונה בוטלה.', UNKNOWN_SUBMISSION:'מצב השליחה אינו ידוע. ניסיון נוסף נחסם כדי למנוע חיוב כפול.',
    SUCCEEDED:'התמונה נוצרה, נבדקה ונשמרה בהצלחה. מחיר המודל לתמונה: $0.003.'};
  el('message').textContent = messages[data.status] || data.status;
  if (data.generation_verified) {
    el('image').src = data.image_url; el('image').hidden = false;
    el('download').href = data.image_url; el('download').hidden = false;
  }
  clearTimeout(timer);
  if (['SUBMITTED','QUEUED','RUNNING'].includes(data.status)) timer = setTimeout(refresh, 3500);
}
async function refresh() {
  try { render(await api()); } catch(error) { el('message').textContent = error.message; }
}
el('confirm').addEventListener('change', () => { el('start').disabled = busy || submitted || !el('confirm').checked; });
el('refresh').addEventListener('click', refresh);
el('start').addEventListener('click', async () => {
  if (busy || submitted || !el('confirm').checked) return;
  busy = true; el('start').disabled = true;
  try { render(await api('POST')); }
  catch(error) { submitted = true; el('message').textContent = error.message; }
  finally { busy = false; }
});
refresh();
