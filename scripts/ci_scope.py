"""Skip expensive CI only for an explicitly documentation-only diff."""
from pathlib import PurePosixPath
import os
import subprocess
import sys


def needs_heavy(files):
    if not files:
        return True
    for name in files:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            return True
        # Workflow metadata, executable examples and unknown files fail closed.
        documentation = path.suffix == '.md' and (
            len(path.parts) == 1 or path.parts[0] == 'docs'
        )
        if not documentation:
            return True
    return False


def gate_passes(scope_result, heavy, test_result):
    return scope_result == 'success' and (
        (heavy == 'true' and test_result == 'success')
        or (heavy == 'false' and test_result == 'skipped')
    )


def main():
    if sys.argv[1:] == ['--verify-gate']:
        passed = gate_passes(
            os.environ.get('SCOPE_RESULT'), os.environ.get('HEAVY'),
            os.environ.get('TEST_RESULT'),
        )
        print(f'Heavy-check gate passed={passed}')
        raise SystemExit(0 if passed else 1)
    base = os.environ.get('CI_BASE_SHA', '')
    head = os.environ.get('CI_HEAD_SHA', 'HEAD')
    heavy = True
    if base and base != '0' * 40 and os.environ.get('CI_EVENT') != 'workflow_dispatch':
        try:
            # No rename detection: code renamed into docs must include both paths.
            result = subprocess.run(
                ['git', 'diff', '--no-renames', '--name-only', '-z', base, head, '--'],
                check=True, capture_output=True,
            )
            files = result.stdout.decode('utf-8', errors='strict').rstrip('\0').split('\0')
            heavy = needs_heavy(files)
        except (OSError, subprocess.CalledProcessError, UnicodeError):
            print('::warning::Changed-file detection unavailable; running heavy checks')
    output = f'heavy={str(heavy).lower()}\n'
    print(output, end='')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as handle:
        handle.write(output)


if __name__ == '__main__':
    main()
