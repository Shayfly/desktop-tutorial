"""changed_files_sane.py ANCHOR : every file changed since ANCHOR that is .json parses, and no changed file holds a
conflict marker (^<<<<<<< or ^>>>>>>>; a lone ^======= only beside one of them -- it is a markdown rule otherwise).
The same rule as scripts/commit_resolved.sh, for the `light` CI job. One ::error line per problem; exit 1 on any."""
import json
import re
import subprocess
import sys
from pathlib import Path

_HARD = re.compile(r'^(<<<<<<<|>>>>>>>)( |$)', re.M)
_MID = re.compile(r'^=======$', re.M)


def problems(paths: list[str], root: Path) -> list[str]:
    out = []
    for p in paths:
        f = root / p
        if not f.is_file():
            continue                                    # deleted in this change
        try:
            text = f.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue                                    # binary: no markers, no json
        hard = len(_HARD.findall(text))
        if hard:
            out.append(f'{p}: {hard + len(_MID.findall(text))} conflict marker line(s)')
        if p.endswith('.json'):
            try:
                json.loads(text)
            except ValueError as exc:
                out.append(f'{p}: invalid json ({exc})'[:200])
    return out


def main(argv: list[str]) -> int:
    root = Path(subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                               check=True).stdout.strip())
    changed = subprocess.run(['git', 'diff', '--name-only', argv[0], 'HEAD'], capture_output=True, text=True,
                             check=True, cwd=root).stdout.split()
    found = problems(changed, root)
    for line in found:
        print(f'::error title=changed files::{line}')
    print(f'::notice title=changed files::{len(changed)} changed, {len(found)} problem(s)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
