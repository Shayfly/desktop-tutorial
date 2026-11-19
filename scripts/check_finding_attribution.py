"""Verify that a declared finding reporter did not co-author its fix."""
import argparse
import subprocess


def identity(value):
    name = ' '.join(value.split('<', 1)[0].casefold().split())
    return {'claude code': 'claude', 'openai codex': 'codex'}.get(name, name)


def conflicts(message):
    result = subprocess.run(['git', 'interpret-trailers', '--parse'], input=message,
                            capture_output=True, text=True, check=True)
    reporters, authors = set(), set()
    for trailer in result.stdout.splitlines():
        key, _, value = trailer.partition(':')
        name = identity(value)
        if name and key.casefold() == 'found-by':
            reporters.add(name)
        if name and key.casefold() == 'co-authored-by':
            authors.add(name)
    return reporters & authors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('head')
    args = parser.parse_args()
    commits = subprocess.check_output(['git', 'rev-list', args.head, f'^{args.base}', '--'],
                                      text=True).splitlines()
    failed = []
    for sha in commits:
        message = subprocess.check_output(['git', 'show', '-s', '--format=%B', sha], text=True)
        if conflicts(message):
            failed.append(sha)
            print(f'::error title=Finding attribution::{sha} names the same agent as reporter and co-author.')
    print(f'Checked {len(commits)} commits; {len(failed)} attribution conflicts.')
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
