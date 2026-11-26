"""Every pull request carries the delivery report of the owner's plan (section 17; plan v3 S1.7, 2026-11-25).

The body has one `## <field>` section for each of the 18 fields below, in any order, each with content (HTML comments,
which the template uses for guidance, do not count as content). `## Status` starts with PASS, FAIL or HOLD.
`## Task ID` names one or more plan task ids (S1.7, S2.3 ...), and the pull request's title names at least one of them,
so a PR can be found by its task.

    python3 scripts/check_pr_report.py            # reads PR_TITLE and PR_BODY from the environment (the workflow)
    python3 scripts/check_pr_report.py --file body.md --title "S1.7 ..."

Prints one ::error line per problem and exits 1, or one ::notice and exits 0. A body that cannot be read is an error,
never a pass.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

FIELDS = ('Task ID', 'Requirement', 'Baseline', 'Architecture', 'Implementation', 'Code', 'Diff', 'Dependencies',
          'Security', 'Tests', 'Evidence', 'Cost', 'Performance', 'Deployment', 'Rollback', 'Reviewer', 'Blockers',
          'Status')
STATUSES = ('PASS', 'FAIL', 'HOLD')
TASK_ID = re.compile(r'\bS\d+\.\d+\b')
_HEADING = re.compile(r'^##[ \t]+(.+?)[ \t]*#*[ \t]*$', re.M)
_COMMENT = re.compile(r'<!--.*?-->', re.S)
_STATUS = re.compile(r'[*_`\s]*(' + '|'.join(STATUSES) + r')(?![A-Za-z])')    # "**PASS**:", "`HOLD` (reason)"


def sections(body: str) -> dict[str, str]:
    """{heading: content} for every `## heading` of the body; a heading that appears twice keeps both contents."""
    out: dict[str, str] = {}
    marks = list(_HEADING.finditer(body))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        name = m.group(1).strip()
        out[name] = (out.get(name, '') + '\n' + body[m.end():end]).strip()
    return out


def problems(title: str, body: str) -> list[str]:
    found = {k.casefold(): v for k, v in sections(body).items()}
    out = []
    for field in FIELDS:
        if field.casefold() not in found:
            out.append(f'the section "## {field}" is missing')
        elif not _COMMENT.sub('', found[field.casefold()]).strip():
            out.append(f'the section "## {field}" is empty')
    status = _COMMENT.sub('', found.get('status', '')).strip()
    if status and not _STATUS.match(status):
        out.append(f'"## Status" must start with {", ".join(STATUSES)}, not {status.split()[0]!r}')
    task = _COMMENT.sub('', found.get('task id', ''))
    ids = TASK_ID.findall(task)
    if task.strip() and not ids:
        out.append('"## Task ID" names no plan task id (S<stage>.<task>, for example S1.7)')
    elif ids and not any(i in title for i in ids):
        out.append(f'the title names none of the task ids {", ".join(dict.fromkeys(ids))}')
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--file', help='read the body from this file instead of PR_BODY')
    parser.add_argument('--title', help='the title, instead of PR_TITLE')
    args = parser.parse_args(argv)
    title = args.title if args.title is not None else os.environ.get('PR_TITLE')
    if args.file:
        with open(args.file, encoding='utf-8') as fh:
            body = fh.read()
    else:
        body = os.environ.get('PR_BODY')
    if title is None or body is None:
        print('::error title=PR report::the title or the body could not be read (PR_TITLE / PR_BODY unset)')
        return 1
    found = problems(title, body)
    for p in found:
        print(f'::error title=PR report::{p}')
    if found:
        print(f'::error title=PR report::{len(found)} problem(s); the fields are in .github/pull_request_template.md')
        return 1
    status = {k.casefold(): v for k, v in sections(body).items()}['status']
    print(f'::notice title=PR report::all {len(FIELDS)} fields present; status '
          f'{_STATUS.match(_COMMENT.sub("", status).strip()).group(1)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
