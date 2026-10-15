#!/usr/bin/env bash
# audit_pack.sh — הרץ משורש הריפו
set -uo pipefail
OUT=AUDIT_PACK.md
: > "$OUT"
sec(){ printf '\n\n## %s\n\n```\n' "$1" >> "$OUT"; }
end(){ printf '```\n' >> "$OUT"; }

# Capture section bodies as well as headings; the supplied script omitted this.
{
sec "META"
  echo "commit: $(git rev-parse HEAD)"
  echo "date:   $(date -u +%FT%TZ)"
  echo "branch: $(git rev-parse --abbrev-ref HEAD)"
  echo "files:  $(git ls-files | wc -l)"
end

sec "INVENTORY — כל קובץ py לפי שורות"
  git ls-files '*.py' | xargs wc -l | sort -n
end

sec "PATHS — נתיבים קשיחים"
  grep -rn "/tmp" --include='*.py' .
  echo "---- windows ----"
  grep -rn "C:\\\\" --include='*.py' .
end

sec "ENV VARS — שמות בלבד"
  grep -rhoE '(getenv|environ\.get|environ)\("[A-Z0-9_]+"' --include='*.py' . | sort -u
end

sec "ROUTES"
  grep -rn '@app\.\(get\|post\|put\|patch\|delete\)\|@router\.' --include='*.py' .
end

sec "AUTH"
  grep -rn 'bearer\|Bearer\|middleware\|session\|cookie\|csrf\|CSRF' --include='*.py' .
end

sec "TRANSACTIONS"
  grep -rn 'transaction()\|\.commit()\|\.rollback()' --include='*.py' .
end

sec "IN-MEMORY STATE — מודול-גלובלי"
  grep -rnE '^_v[0-9]+\._|\s_v[0-9]+\._[a-z_]+\s*=' --include='*.py' .
end

sec "BROAD EXCEPTS"
  grep -rn 'except Exception\|except:' --include='*.py' .
end

sec "MARKERS"
  grep -rniE '\b(todo|fixme|hack|xxx|not implemented|placeholder|stub)\b' --include='*.py' .
end

sec "SECRETS"
  grep -rniE 'token|api_key|secret|password|credential' --include='*.py' omni_prod/ | head -200
end

sec "MIGRATIONS"
  ls -1 migrations/ 2>/dev/null || find . -path ./node_modules -prune -o -name '*migration*' -print
end

sec "TESTS"
  git ls-files 'tests/*.py' | xargs wc -l
end

sec "CI"
  find .github -type f 2>/dev/null
  echo "---- ci content ----"
  find .github/workflows -name '*.yml' -o -name '*.yaml' 2>/dev/null | head -5 | xargs -r cat
end

sec "DEPS"
  cat requirements.txt 2>/dev/null
  cat pyproject.toml 2>/dev/null
end
} >> "$OUT" 2>&1

echo "done -> $OUT  ($(wc -l < "$OUT") lines)"
