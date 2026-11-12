"""Make a repo-control response's action failures fail the cron step."""
import json
import os
from pathlib import Path
import sys


def main(operation):
    failed, actions, reason = True, [], 'Invalid repo-control response'
    try:
        data = json.load(sys.stdin)
        actions = data['actions']
        if (data.get('ok') is not True or data.get('op') != operation
                or not isinstance(actions, list) or not all(isinstance(a, str) for a in actions)
                or data.get('count') != len(actions)):
            raise ValueError('invalid response contract')
        if operation == 'retarget':
            # a PR already contained in main, or GitHub's 422 "no commits between", is a reported no-op, not a failure
            failures = [a for a in actions if not (a.endswith(' -> ok') or ' -> skip ' in a)]
        else:
            failures = [a for a in actions if not (a.endswith(' merge ok') or ' skip ' in a)]
        failed = bool(failures)
        reason = f'{len(failures)} failed of {len(actions)} actions'
    except (ValueError, KeyError, TypeError):
        actions = []
    status = 'FAIL' if failed else 'PASS'
    text = f'### {operation}: {status}\n\n{reason}\n\n'
    text += ''.join(f'- {a}\n' for a in actions)
    token = os.environ.get('SERVICE_TOKEN', '')
    if token:
        text = text.replace(token, '[REDACTED]')
    print(text, end='')
    # Also as a check-run annotation, so the result is readable through the API without downloading the job log.
    line = ('; '.join(actions) if actions else reason).replace('%', '%25').replace('\n', ' ')
    if token:
        line = line.replace(token, '[REDACTED]')
    print(f"::{'error' if failed else 'notice'} title=agent-loop {operation} {status}::{reason}: {line[:900]}")
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with Path(summary).open('a', encoding='utf-8') as output:
            output.write(text + '\n')
    return int(failed)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('retarget', 'sweep'):
        raise SystemExit('usage: check_agent_loop_result.py retarget|sweep')
    raise SystemExit(main(sys.argv[1]))
