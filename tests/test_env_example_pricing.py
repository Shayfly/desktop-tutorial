"""2026-10-30: .env.example carried OMNI_PRICE_BASIC_USD=12 / PRO=39 / BUSINESS=99 against 29 / 99 / 299 in
pricing.py -- copied into a deployment, it would silently override the approved prices. Every price and cap
variable pricing.py reads must appear in .env.example with exactly the code default."""
from __future__ import annotations

import re
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def example():
    out = {}
    for line in (ROOT / '.env.example').read_text(encoding='utf-8').splitlines():
        m = re.match(r'^([A-Z0-9_]+)=(.*)$', line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def defaults():
    """{current name: default} for every _env_decimal / _env_decimal_renamed price or cap in pricing.py."""
    src = (ROOT / 'omni_prod' / 'pricing.py').read_text(encoding='utf-8')
    found = {}
    for name, default in re.findall(r"_env_decimal\('((?:OMNI_PRICE|OMNI_PROVIDER_CAP)_[A-Z_]+)',\s*'([0-9.]+)'\)", src):
        found[name] = default
    for name, _legacy, default in re.findall(
            r"_env_decimal_renamed\('((?:OMNI_PRICE|OMNI_PROVIDER_CAP)_[A-Z_]+)',\s*'([A-Z_]+)',\s*'([0-9.]+)'\)", src):
        found[name] = default
    return found


class TheExampleMatchesTheCode(unittest.TestCase):
    def test_every_price_and_cap_is_present_with_the_code_default(self):
        ex, code = example(), defaults()
        self.assertGreaterEqual(len(code), 10, code)                      # the parser still finds them
        for name, default in sorted(code.items()):
            with self.subTest(name=name):
                self.assertIn(name, ex, f'{name} missing from .env.example')
                self.assertEqual(Decimal(ex[name]), Decimal(default))

    def test_no_stale_pre_rename_name_overrides_the_default(self):
        ex = example()
        for legacy in ('OMNI_PRICE_BASIC_USD', 'OMNI_PRICE_BUSINESS_USD', 'OMNI_PRICE_BASIC_ANNUAL_USD',
                       'OMNI_PRICE_BUSINESS_ANNUAL_USD', 'OMNI_PROVIDER_CAP_BASIC_USD', 'OMNI_PROVIDER_CAP_BUSINESS_USD'):
            self.assertNotIn(legacy, ex)

    def test_the_approved_prices(self):
        ex = example()
        self.assertEqual([ex['OMNI_PRICE_AMATEUR_USD'], ex['OMNI_PRICE_PRO_USD'], ex['OMNI_PRICE_STUDIO_USD']],
                         ['29', '99', '299'])


if __name__ == '__main__':
    unittest.main()
