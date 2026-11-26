"""Every pull request carries the delivery report of the owner's plan (section 17; plan v3 S1.7, 2026-11-25).

The body has one `## <field>` section for each of the 18 fields below, in any order, each exactly once and each with
content. The body is read as GitHub shows it (line endings CRLF or LF):
- Code is read first: a fenced block (``` or ~~~, to its closing fence or the end of the body) and a code span (a run
  of backticks, to the next run of as many in its paragraph) show as written, so a `<!--` or a `## ` line inside code
  is text, never a comment or a section.
- Outside code, HTML comments are removed: a comment that spans a heading hides both, an unclosed `<!--` hides the
  rest of the body, and a comment that begins before a code mark hides it.
- What draws nothing is not content: headings of another level, code fence markers, thematic breaks, an empty list
  item or quote, a link reference definition (`[x]: <>`), a link without text, HTML tags without text (`<br>`,
  `<span></span>`; an image or a video is content), character references to a space or to nothing (`&nbsp;`,
  `&ensp;`, `&#8203;`), white space, and characters that draw nothing (U+200B, U+2060, U+FEFF, U+3164, U+2800 ...).

`## Status` begins with PASS, FAIL or HOLD as a whole word, followed by the end of the line, a space, a colon, a
period or a dash. A mark around the word is closed on both sides (`**PASS**`, `` `HOLD` ``), or right after the stop
that follows the word (`**PASS:** the reason`). "PASS/FAIL", "PASSED" or the template's guidance "PASS, FAIL or HOLD"
do not count.

`## Task ID` names one or more plan task ids (S1.7, S2.3 ...), and the title names at least one of them as a whole id
(S1.75 is not S1.7). A pull request outside the plan writes `none: <the reason>` (a hotfix, an owner's order, a
warehouse item); its title then needs no id.

Accepted without the report, and only these: a pull request opened by a bot in BOTS, and a GitHub revert, which needs
all of: the head branch GitHub's Revert button makes (`revert-<n>-<branch>`), a title that begins `Revert "`, and a
body whose first line is GitHub's `Reverts <owner>/<repo>#<n>`, naming this repository (the event's
repository.full_name; --repository or GITHUB_REPOSITORY without an event) and the same <n>. A title and a body alone
can be typed by anyone: `Revert "nothing"` with `Reverts someone/elsewhere#1` passed without a report until the
review of 2026-11-26. A branch named by hand like GitHub's still passes; nothing here proves that the diff reverts #<n>.

    python3 scripts/check_pr_report.py --event "$GITHUB_EVENT_PATH"   # the workflow: the event GitHub wrote
    python3 scripts/check_pr_report.py --file body.md --title "S1.7 ..."
    PR_TITLE=... PR_BODY=... python3 scripts/check_pr_report.py

Prints one ::error line per problem and exits 1, or one ::notice and exits 0. A body that cannot be read, or that is
null (GitHub sends null for an empty description), is an error, never a pass.
"""
from __future__ import annotations

import argparse
import bisect
import html
import json
import os
import re
import sys
import unicodedata

FIELDS = ('Task ID', 'Requirement', 'Baseline', 'Architecture', 'Implementation', 'Code', 'Diff', 'Dependencies',
          'Security', 'Tests', 'Evidence', 'Cost', 'Performance', 'Deployment', 'Rollback', 'Reviewer', 'Blockers',
          'Status')
STATUSES = ('PASS', 'FAIL', 'HOLD')
BOTS = ('dependabot[bot]',)
TASK_ID = re.compile(r'(?<![\w.])S\d+\.\d+(?![\w]|\.\d)')                 # S1.7; never S1.75, XS1.7 or S1.7.1
_COMMENT = re.compile(r'<!--(?:-?>|.*?-->)', re.S)                     # CommonMark: <!--> and <!---> end at once
_FENCE = re.compile(r'^ {0,3}(`{3,}(?=[^`]*$)|~{3,})')                 # ```x``` opens no fence: it is a code span
_CLOSING = re.compile(r' {0,3}(`{3,}|~{3,})[ \t]*')                    # a closing fence: its marks and nothing else
_COMMENT_LINE = re.compile(r' {0,3}<!--')                              # begins an HTML block: it ends a paragraph
_BACKTICKS = re.compile('`+')
_SECTION = re.compile(r'^ {0,3}##[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$')    # a level-2 heading only
_HEADING = re.compile(r'^ {0,3}#{1,6}(?:[ \t]|$)')
_BREAK = re.compile(r'^ {0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|={3,})$')
_BARE_MARK = re.compile(r'^(?:[-*+>]|\d+[.)])$')                       # a list item or quote with nothing in it
_LINK_DEF = re.compile(r' {0,3}\[(?!\^)(?:[^\]\\\n]|\\.)+\]:[ \t]*(?:<[^<>\n]*>|\S+)'
                       r'(?:[ \t]+(?:"[^"\n]*"|\'[^\'\n]*\'|\([^()\n]*\)))?[ \t]*')   # [x]: <url> "title" shows nothing
_EMPTY_LINK = re.compile(r'(?<!!)\[\]\([^()\n]*\)')                    # [](url) shows nothing; ![](x) is an image
_TAG = re.compile(r'</?([A-Za-z][A-Za-z0-9-]*)(?:\s[^<>]*)?/?>')
_DRAWN = frozenset({'img', 'picture', 'video', 'audio', 'svg', 'iframe', 'object', 'embed', 'canvas', 'input',
                    'textarea', 'select', 'button', 'meter', 'progress'})      # tags that show something without text
_REFERENCE = re.compile(r'&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});')
_FILLERS = frozenset('\u115f\u1160\u3164\uffa0\u2800\U0001d159')     # draw nothing, take a place
_NO_WIDTH = frozenset('\u034f' + ''.join(map(chr, range(0xfe00, 0xfe10))) + ''.join(map(chr, range(0xe0100, 0xe01f0))))
_STATUS = re.compile(r'(?P<mark>\*\*|__|\*|_|`)?(?P<word>' + '|'.join(STATUSES) + r')(?:(?(mark)(?P=mark))'
                     r'(?=$|[ \t:.\-–—])'
                     r'|(?(mark)[:.\-–—](?P=mark)(?=$|[ \t])|(?!)))')    # **PASS:** reason: closed after the stop
_NONE = re.compile(r'none\b(?P<reason>.*)', re.I | re.S)
_REVERT_TITLE = re.compile(r'Revert "')
_REVERT_BRANCH = re.compile(r'revert-(?P<number>[1-9]\d*)-.+')          # the branch GitHub's Revert button makes
_REVERT_BODY = re.compile(r'Reverts (?P<repository>[\w.-]+/[\w.-]+)#(?P<number>[1-9]\d*)[ \t]*')


def _closes(opener: str, line: str) -> bool:
    """Whether `line` closes the fenced block `opener` opened: the same mark, at least as long, nothing after it."""
    mark = _CLOSING.fullmatch(line)
    return bool(mark) and mark.group(1)[0] == opener[0] and len(mark.group(1)) >= len(opener)


def _escaped(text: str, pos: int) -> bool:
    """Whether the character at `pos` follows an odd number of backslashes (\\` and \\< are text on GitHub)."""
    k = pos
    while k > 0 and text[k - 1] == '\\':
        k -= 1
    return (pos - k) % 2 == 1


def _breaks(line: str) -> bool:
    """Whether `line` ends the paragraph before it: a blank line, a fence, a heading or a line that begins a comment."""
    return not line.strip() or bool(_FENCE.match(line) or _HEADING.match(line) or _COMMENT_LINE.match(line))


def _scan(body: str) -> list[tuple[str, str]]:
    """The body as GitHub shows it, line by line: (line, kind), kind 'text', 'code' (inside a fenced block) or 'fence'
    (a fence's own marker line). Code is read first, as GitHub reads it: a fenced block runs to its closing fence or
    the end of the body; a code span runs from a run of backticks to the next run exactly as long in its paragraph (it
    never crosses a blank line, a fence, a heading or a line that begins a comment, and never leaves a heading line).
    Outside code each HTML comment is removed, and one that is never closed hides the rest of the body."""
    text = body.replace('\r\n', '\n').replace('\r', '\n')
    n = len(text)
    starts = [0] + [m.end() for m in re.finditer('\n', text)]        # where each line begins
    ends = [s - 1 for s in starts[1:]] + [n]
    limit = ends[:]                                                  # how far a code span begun on that line may run
    for i in range(len(starts) - 2, -1, -1):
        if not (_HEADING.match(text[starts[i]:ends[i]]) or _breaks(text[starts[i + 1]:ends[i + 1]])):
            limit[i] = limit[i + 1]
    runs: dict[int, list[int]] = {}                                  # the backtick runs of each length, in order
    for m in _BACKTICKS.finditer(text):
        runs.setdefault(m.end() - m.start(), []).append(m.start())
    out: list[tuple[str, str]] = []
    buf: list[str] = []
    pos, at_start = 0, True
    while True:
        if at_start:                                    # a fence opens only where a line begins
            end = text.find('\n', pos)
            end = n if end < 0 else end
            mark = _FENCE.match(text[pos:end])
            if mark:
                out.append((text[pos:end], 'fence'))
                opener, pos = mark.group(1), end + 1
                while pos <= n:                         # its lines, to the closing fence or the end of the body
                    end = text.find('\n', pos)
                    end = n if end < 0 else end
                    line, pos = text[pos:end], end + 1
                    if _closes(opener, line):
                        out.append((line, 'fence'))
                        break
                    out.append((line, 'code'))
                if pos > n:
                    return out
                continue
            at_start = False
        if pos >= n:
            out.append((''.join(buf), 'text'))
            return out
        ch = text[pos]
        if ch == '\n':
            out.append((''.join(buf), 'text'))
            buf, pos, at_start = [], pos + 1, True
        elif ch == '`' and not _escaped(text, pos):
            run = _BACKTICKS.match(text, pos).end() - pos   # from here: an escaped first backtick is text
            same = runs.get(run, [])
            k = bisect.bisect_left(same, pos + run)
            close = same[k] + run if k < len(same) else None
            if close is not None and close > limit[bisect.bisect_right(starts, pos) - 1]:
                close = None                            # no closing run in this paragraph: the backticks are text
            for j, part in enumerate(text[pos:close or pos + run].split('\n')):   # a span may run over lines
                if j:
                    out.append((''.join(buf), 'text'))
                    buf = []
                buf.append(part)
            pos = close or pos + run
        elif text.startswith('<!--', pos) and not _escaped(text, pos):
            comment = _COMMENT.match(text, pos)
            pos = comment.end() if comment else n       # an unclosed comment hides the rest of the body, as on GitHub
        else:
            buf.append(ch)
            pos += 1


def clean(body: str) -> str:
    """The body as GitHub shows it: LF line endings, code as written, no HTML comment outside code."""
    return '\n'.join(line for line, _kind in _scan(body))


def sections(body: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """[(heading, rows), ...] for every `## heading` outside code, in order, with the (line, kind) rows under it; a
    repeated heading is kept twice (problems() reports it)."""
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for line, kind in _scan(body):
        heading = _SECTION.match(line) if kind == 'text' else None
        if heading:
            out.append((heading.group(1).strip(), []))
        elif out:
            out[-1][1].append((line, kind))
    return out


def _shown(text: str) -> str:
    """The text as it shows: a character that draws nothing and takes no place is dropped (control and format
    characters such as U+200B, U+200C, U+2060, U+FEFF; variation selectors; U+034F); one that draws nothing but
    takes a place (white space, U+3164 and the other fillers, U+2800) becomes a space."""
    out = []
    for ch in text:
        kind = unicodedata.category(ch)
        if ch.isspace() or kind in ('Zs', 'Zl', 'Zp') or ch in _FILLERS:
            out.append(' ')
        elif kind not in ('Cc', 'Cf') and ch not in _NO_WIDTH:
            out.append(ch)
    return ''.join(out)


def _visible(line: str) -> str:
    """A line outside code as it shows: no link without text, no HTML tag (one that draws something without text, an
    image or a video, leaves a mark), character references decoded (one without its ';' is text), _shown."""
    line = _EMPTY_LINK.sub('', line)
    line = _TAG.sub(lambda tag: '\u25a1' if tag.group(1).lower() in _DRAWN else '', line)
    line = _REFERENCE.sub(lambda ref: html.unescape(ref.group(0)), line)
    return _shown(line).strip()


def content_lines(rows: list[tuple[str, str]]) -> list[str]:
    """The lines of a section that show something, as they show. Inside a fenced block a line shows as written (only
    white space and characters that draw nothing are nothing). Outside one, a heading, a thematic break, an empty list
    item or quote and a link reference definition show nothing, and neither does a fence's own marker line."""
    out = []
    for line, kind in rows:
        if kind == 'fence' or (kind == 'text' and _LINK_DEF.fullmatch(line)):
            continue
        shown = _shown(line).strip() if kind == 'code' else _visible(line)
        if shown and not (kind == 'text' and (_HEADING.match(shown) or _BREAK.match(shown) or _BARE_MARK.match(shown))):
            out.append(shown)
    return out


def accepted_without_report(title: str, body: str | None, author: str | None, head_ref: str | None = None,
                            repository: str | None = None) -> str | None:
    """The reason a pull request needs no report, or None. A revert needs everything GitHub's Revert button makes:
    the branch revert-<n>-..., the title `Revert "...` and the body `Reverts <this repository>#<n>`."""
    if author in BOTS:
        return f'opened by {author}'
    branch = _REVERT_BRANCH.fullmatch(head_ref or '')
    if body is None or not _REVERT_TITLE.match(title) or branch is None:
        return None
    first = next((l for l in clean(body).split('\n') if l.strip()), '').strip()
    reverts = _REVERT_BODY.fullmatch(first)
    if reverts is None or reverts.group('number') != branch.group('number'):
        return None
    if not repository or reverts.group('repository').casefold() != repository.casefold():
        return None
    return f'a GitHub revert ({first}, branch {head_ref})'


def problems(title: str, body: str) -> list[str]:
    found = sections(body)
    by_name: dict[str, list[list[tuple[str, str]]]] = {}
    for name, rows in found:
        by_name.setdefault(name.casefold(), []).append(rows)
    out = []
    for field in FIELDS:
        texts = by_name.get(field.casefold())
        if not texts:
            out.append(f'the section "## {field}" is missing')
        elif len(texts) > 1:
            out.append(f'the section "## {field}" appears {len(texts)} times; write it once')
        elif not content_lines(texts[0]):
            out.append(f'the section "## {field}" is empty')
    status = content_lines((by_name.get('status') or [[]])[0])
    if status and len(by_name['status']) == 1 and not _STATUS.match(status[0]):
        out.append(f'"## Status" must begin with {", ".join(STATUSES[:-1])} or {STATUSES[-1]} as a whole word, not '
                   f'{status[0][:40]!r}')
    task = content_lines((by_name.get('task id') or [[]])[0])
    if task and len(by_name['task id']) == 1:
        none = _NONE.match(task[0])
        if none:
            if not (none.group('reason').strip(' \t:-–—,.;') or task[1:]):
                out.append('"## Task ID" says none without the reason: write "none: <why there is no plan task>"')
        else:
            ids = list(dict.fromkeys(TASK_ID.findall('\n'.join(task))))
            if not ids:
                out.append('"## Task ID" names no plan task id (S<stage>.<task>, for example S1.7), and does not '
                           'say "none: <reason>"')
            elif not set(ids) & set(TASK_ID.findall(title)):
                out.append(f'the title names none of the task ids {", ".join(ids)}')
    return out


def status_word(body: str) -> str:
    rows = [r for n, r in sections(body) if n.casefold() == 'status']
    return _STATUS.match(content_lines(rows[0])[0]).group('word')


def _read(args) -> tuple[str | None, str | None, str | None, str | None, str | None, str]:
    """(title, body, author, head branch, repository, where they came from). The body is None when it could not be
    read or is null."""
    if args.event:
        with open(args.event, encoding='utf-8') as fh:
            event = json.load(fh)
        pr = event.get('pull_request')
        if not isinstance(pr, dict):
            return None, None, None, None, None, f'{args.event} holds no pull_request'
        return (pr.get('title'), pr.get('body'), (pr.get('user') or {}).get('login'), (pr.get('head') or {}).get('ref'),
                (event.get('repository') or {}).get('full_name'), 'the event')
    title = args.title if args.title is not None else os.environ.get('PR_TITLE')
    if args.file:
        with open(args.file, encoding='utf-8') as fh:
            body = fh.read()
    else:
        body = os.environ.get('PR_BODY')
    return (title, body, args.author or os.environ.get('PR_AUTHOR'), args.head_ref or os.environ.get('PR_HEAD_REF'),
            args.repository or os.environ.get('GITHUB_REPOSITORY'), 'PR_TITLE / PR_BODY')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--event', help='a GitHub pull_request event file (the workflow passes $GITHUB_EVENT_PATH)')
    parser.add_argument('--file', help='read the body from this file instead of PR_BODY')
    parser.add_argument('--title', help='the title, instead of PR_TITLE')
    parser.add_argument('--author', help="the author's login, instead of PR_AUTHOR")
    parser.add_argument('--head-ref', help='the head branch, instead of PR_HEAD_REF')
    parser.add_argument('--repository', help='owner/repo, instead of GITHUB_REPOSITORY')
    args = parser.parse_args(argv)
    title, body, author, head_ref, repository, source = _read(args)
    if title is None:
        print(f'::error title=PR report::the title could not be read ({source})')
        return 1
    reason = accepted_without_report(title, body, author, head_ref, repository)
    if reason:
        print(f'::notice title=PR report::no delivery report needed: {reason}')
        return 0
    if body is None and source != 'the event':
        print(f'::error title=PR report::the body could not be read ({source} unset)')
        return 1
    if body is None or not body.strip():
        print(f'::error title=PR report::the body is {"null" if body is None else "empty"} ({source}): GitHub sends '
              'null for a pull request without a description. Fill .github/pull_request_template.md')
        return 1
    found = problems(title, body)
    for p in found:
        print(f'::error title=PR report::{p}')
    if found:
        print(f'::error title=PR report::{len(found)} problem(s); the fields are in .github/pull_request_template.md')
        return 1
    print(f'::notice title=PR report::all {len(FIELDS)} fields present; status {status_word(body)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
