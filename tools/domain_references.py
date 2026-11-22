"""Are the domains' reference sites still alive? (warehouse 127, acceptance 5: a dead reference is flagged and replaced,
never left in the list.)

Every reference in omni_prod/domain_registry.json is fetched once (GET, redirects followed, a short timeout). A reference
is DEAD when it does not answer, answers 4xx/5xx, or answers with a block or empty shell (under 512 bytes of body).
A domain left with fewer than 5 live references is reported by name: its file needs a replacement reference.

    python tools/domain_references.py --out references.json
Exit codes: 0 every reference alive; 1 at least one dead reference (the list says which); 2 nothing could be
checked (the registry cannot be read, or not one reference answered: the runner has no network).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'omni_prod' / 'domain_registry.json'
MIN_LIVE = 5
MIN_BODY = 512
TIMEOUT = 20


def fetch(url: str) -> tuple[int | None, int, str]:
    """(status, body bytes, error). Never raises."""
    req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; reference-check/1.0)'})
    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, len(resp.read(200_000)), ''
    except error.HTTPError as exc:
        return exc.code, 0, f'HTTP {exc.code}'
    except Exception as exc:                        # DNS, TLS, timeout: the reference did not answer
        return None, 0, type(exc).__name__


def verdict(status, size, err) -> str | None:
    """None when alive, else why it is dead."""
    if status is None:
        return f'no answer ({err})'
    if status >= 400:
        return f'HTTP {status}'
    if size < MIN_BODY:
        return f'an empty or blocked page ({size} bytes)'
    return None


def check(registry: dict, fetcher=fetch) -> dict:
    domains = {}
    for slug, d in sorted(registry['domains'].items()):
        refs = []
        for url in d['references']:
            why = verdict(*fetcher(url))
            refs.append({'url': url, 'alive': why is None, 'why': why})
        live = sum(1 for r in refs if r['alive'])
        domains[slug] = {'live': live, 'references': refs, 'needs_replacement': live < MIN_LIVE}
    dead = [(s, r['url'], r['why']) for s, d in domains.items() for r in d['references'] if not r['alive']]
    return {'domains': domains, 'dead': dead,
            'short': sorted(s for s, d in domains.items() if d['needs_replacement'])}


def main(argv=None, fetcher=fetch) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--registry', default=str(REGISTRY))
    a = ap.parse_args(argv)
    try:
        registry = json.loads(Path(a.registry).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print(f'::error title=domain references::cannot read the registry: {type(exc).__name__}')
        return 2
    result = check(registry, fetcher)
    total = sum(len(d['references']) for d in result['domains'].values())
    if total and all(why.startswith('no answer') for _, _, why in result['dead']) and len(result['dead']) == total:
        # not one reference answered: the network is down here, not 207 sites -- nothing was checked
        print(f'::error title=domain references::not one of {total} references answered; the network of this runner '
              'cannot reach them, so nothing was checked')
        return 2
    for slug, url, why in result['dead']:
        print(f'::error title=dead reference ({slug})::{url} -- {why}; replace it in docs/domains/{slug}.md')
    for slug in result['short']:
        print(f'::error title=too few references ({slug})::{result["domains"][slug]["live"]} live; '
              f'at least {MIN_LIVE} are required')
    print(f'::notice title=domain references::{total - len(result["dead"])}/{total} alive across '
          f'{len(result["domains"])} domains; {len(result["short"])} domains below {MIN_LIVE}')
    Path(a.out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return 1 if result['dead'] else 0


if __name__ == '__main__':
    sys.exit(main())
