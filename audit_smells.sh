#!/usr/bin/env bash
# audit_smells.sh — מצפן חשדות. הרץ משורש הריפו.
set -uo pipefail
O=SMELLS.md
: > "$O"
exec 3>&1 1>>"$O"
S(){ printf '\n\n## %s\n\n```\n' "$1"; }
E(){ printf '```\n'; }

S "A1 — כסף: float מול Decimal"
  echo "-- float( --";      grep -rn 'float(' --include='*.py' . | head -80
  echo "-- Decimal( --";    grep -rn 'Decimal(' --include='*.py' . | wc -l
  echo "-- round( --";      grep -rn 'round(' --include='*.py' . | head -60
  echo "-- int( על כסף --"; grep -rnE 'int\((cost|price|amount|usd|total)' --include='*.py' .
E

S "A2 — כסף: עדכון יתרה"
  echo "-- עדכון ארנק/קרדיטים --"
  grep -rnE '(available_credits|reserved_credits|spent_credits|balance|credits)\s*[-+]=' --include='*.py' .
E

S "A3 — מרוץ: check-then-act"
  echo "-- FOR UPDATE --"
  grep -rn 'FOR UPDATE\|for update' --include='*.py' .
  echo "-- SELECT ואז UPDATE באותו קובץ --"
  grep -rln 'SELECT' --include='*.py' omni_prod/ | xargs -r grep -ln 'UPDATE' 2>/dev/null
E

S "A4 — אידמפוטנטיות"
  grep -rniE 'idempot|dedupe|duplicate|claim_' --include='*.py' .
E

S "B1 — כשלים שקטים"
  echo "-- except: --";           grep -rnE 'except\s*:' --include='*.py' .
  echo "-- except Exception --";  grep -rn 'except Exception' --include='*.py' .
  echo "-- pass אחרי except --";  grep -rnA1 'except' --include='*.py' . | grep -n 'pass'
E

S "B2 — לוגים חסרים"
  echo "-- print( בקוד פרודקשן --"
  grep -rn 'print(' --include='*.py' omni_prod/
E

S "B3 — assert בקוד פרודקשן (נמחק עם -O)"
  grep -rnE '^\s+assert ' --include='*.py' omni_prod/
E

S "C1 — ברירת מחדל של משתני סביבה"
  echo "-- getenv בלי default --";     grep -rnE '(getenv|environ\.get)\("[A-Z0-9_]+"\)' --include='*.py' .
  echo "-- default מספרי חשוד --";     grep -rnE '(getenv|environ\.get)\([^,)]*,\s*["'\'']0["'\'']' --include='*.py' .
  echo "-- default 'false'/'no' --";   grep -rniE '(getenv|environ\.get)\([^,)]*,\s*["'\''](false|no|off)["'\'']' --include='*.py' .
  echo "-- if על env (מחרוזת ריקה=false אבל '0'=true) --"
  grep -rnE 'if\s+.*(getenv|environ)' --include='*.py' .
E

S "D1 — אבטחה: השוואת סודות"
  echo "-- == על טוקן/סוד --"
  grep -rnE '(token|secret|key|signature|hmac)\w*\s*==' --include='*.py' .
  echo "-- compare_digest --"
  grep -rn 'compare_digest' --include='*.py' .
E

S "D2 — אבטחה: TLS וקריאות רשת"
  echo "-- verify=False --";  grep -rnE 'verify\s*=\s*False' --include='*.py' .
  echo "-- urlopen/requests --"; grep -rnE 'urlopen|requests\.(get|post|put|delete)' --include='*.py' .
  echo "-- בלי timeout --";   grep -rnE 'urlopen\(' --include='*.py' . | grep -v timeout
E

S "D3 — אבטחה: CORS / עוגיות / CSRF"
  grep -rniE 'allow_origins|allow_credentials|CORS|samesite|httponly|secure=|csrf' --include='*.py' .
E

S "D4 — אבטחה: הרצה והזרקה"
  echo "-- shell=True --";  grep -rnE 'shell\s*=\s*True' --include='*.py' .
  echo "-- subprocess --";  grep -rn 'subprocess\.' --include='*.py' .
  echo "-- eval/exec --";   grep -rnE '\b(eval|exec)\(' --include='*.py' .
  echo "-- pickle --";      grep -rn 'pickle' --include='*.py' .
  echo "-- SQL עם f-string --"; grep -rnE 'execute\(f["'\'']' --include='*.py' .
  echo "-- SQL עם % או .format --"; grep -rnE 'execute\([^,)]*%\s|execute\([^,)]*\.format\(' --include='*.py' .
E

S "D5 — אבטחה: סודות בלוגים"
  grep -rniE '(log|print).*(token|secret|api_key|authorization|password)' --include='*.py' .
E

S "E1 — עמידות: מצב בזיכרון"
  echo "-- מודול-גלובלי שנכתב --"
  grep -rnE '^_?[a-z][a-z0-9_]* *(: *[A-Za-z\[\], ]+)?= *(\{\}|\[\]|dict\(\)|set\(\)|list\(\)|defaultdict\()|^_v[0-9]+[a-z0-9_]* *=' --include='*.py' .
  echo "-- dict/list גלובלי ברמת מודול --"
  grep -rnE '^[A-Z_]+ *= *(\{\}|\[\])' --include='*.py' omni_prod/
E

S "E2 — עמידות: cache ומצב מיושן"
  echo "-- lru_cache --";       grep -rn 'lru_cache' --include='*.py' .
  echo "-- functools.cache --"; grep -rn 'functools.cache' --include='*.py' .
  echo "-- global --";          grep -rnE '^\s+global ' --include='*.py' .
E

S "E3 — עמידות: חסימה בתוך async"
  echo "-- time.sleep --";      grep -rn 'time.sleep' --include='*.py' .
  echo "-- async def --";       grep -rn 'async def' --include='*.py' . | wc -l
  echo "-- קריאה סינכרונית בתוך async --"
  grep -rnE 'requests\.|urlopen' --include='*.py' omni_prod/
E

S "E4 — עמידות: זמן"
  echo "-- utcnow (naive) --";  grep -rn 'utcnow()' --include='*.py' .
  echo "-- now() --";           grep -rn 'datetime.now()' --include='*.py' .
  echo "-- time.time() כ-ID --"; grep -rnE 'time\.time\(\)' --include='*.py' .
E

S "E5 — עמידות: כתיבה לדיסק בסביבת serverless"
  grep -rnE 'open\(|Path\(|mkdir|makedirs|shutil\.' --include='*.py' omni_prod/ | head -120
E

S "F1 — תורים ו-workers"
  echo "-- enqueue --";        grep -rnB4 'enqueue' --include='*.py' .
  echo "-- lease/heartbeat --"; grep -rniE 'lease|heartbeat|visibility_timeout|renew' --include='*.py' .
  echo "-- retries --";        grep -rniE 'max_retries|retry_count|dead_letter|dlq' --include='*.py' .
E

S "F2 — LLM / סוכנים"
  echo "-- json.loads בלי הגנה --"; grep -rn 'json.loads' --include='*.py' .
  echo "-- finish_reason --";       grep -rn 'finish_reason' --include='*.py' .
  echo "-- שמות מודלים קשיחים --"
  grep -rnE '["'\''][a-z0-9.-]*(gpt|claude|gemini|deepseek|qwen|glm|llama)[a-z0-9.-]*["'\'']' --include='*.py' .
  echo "-- ספירת טוקנים לפי len --"; grep -rnE 'len\(.*\)\s*//?\s*[0-9]' --include='*.py' .
  echo "-- max_tokens --";          grep -rn 'max_tokens\|max_output' --include='*.py' .
E

S "F3 — תבניות פרומפט"
  grep -rnE 'f"""|f"|\.format\(|\+ *["'\'']' --include='*.py' omni_prod/ | grep -iE 'prompt|system|message' | head -80
E

S "G1 — מספרים קסומים"
  grep -rnE '== *[0-9]{2,}|< *[0-9]{2,}|> *[0-9]{2,}' --include='*.py' omni_prod/ | head -120
E

S "G2 — קבועים כפולים"
  echo "-- קרדיטים --";  grep -rnE '[A-Z_]*CREDITS?[A-Z_]* *=' --include='*.py' .
  echo "-- מחירים --";   grep -rnE '[A-Z_]*(PRICE|USD|BUDGET|CAP)[A-Z_]* *=' --include='*.py' .
E

S "H1 — באגים קלאסיים"
  echo "-- ארגומנט ברירת מחדל משתנה --"
  grep -rnE 'def [a-z_]+\(.*=(\[\]|\{\})' --include='*.py' .
  echo "-- is מול == --"
  grep -rnE '\bis\s+["'\'' 0-9]' --include='*.py' .
  echo "-- dict.get ואז חשבון --"
  grep -rnE '\.get\([^,)]+\)\s*[-+*]' --include='*.py' .
E

S "H2 — סכמה ומיגרציות"
  echo "-- מיגרציות --"; ls -1 migrations/ 2>/dev/null | tail -30
  echo "-- timestamp --"; grep -rniE 'timestamp' --include='*.sql' . 2>/dev/null | head -40
  echo "-- ON DELETE --"; grep -rniE 'references .*on delete' --include='*.sql' . 2>/dev/null | head -40
  echo "-- CHECK --";     grep -rniE 'check *\(' --include='*.sql' . 2>/dev/null | head -40
E

echo "done -> $O  ($(wc -l < "$O") lines)" >&3
