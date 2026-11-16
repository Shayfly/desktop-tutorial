"""The ten slowest files of a fast-suite run (junit xml), one ::error line each -- printed when test_fast.sh fails its
budget, so the failure names what to drop instead of leaving the search to the reader."""
import collections
import sys
import xml.etree.ElementTree as ET


def slowest(path: str, n: int = 10) -> list[tuple[str, float]]:
    per: collections.Counter = collections.Counter()
    for case in ET.parse(path).getroot().iter('testcase'):
        parts = (case.get('classname') or '?').split('.')            # tests.integration.test_x.Class
        cut = next((i for i, p in enumerate(parts) if p.startswith('test_')), len(parts) - 1)
        name = case.get('file') or '/'.join(parts[:cut + 1]) + '.py'
        per[name] += float(case.get('time') or 0)
    return per.most_common(n)


if __name__ == '__main__':
    for name, seconds in slowest(sys.argv[1]):
        print(f'::error title=test_fast slowest::{name} {seconds * 1000:.0f} ms')
