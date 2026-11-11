"""Every UI string key that ui/live-runner.js asks for must exist in the launch copy.

A missing key is not a cosmetic issue: the runner shows it to a customer in their
own language (Hebrew first), so each key must exist for every launch locale.
"""

import re
from pathlib import Path

import pytest

from omni_prod.ui_translations import UI_COPY, UI_LANGUAGES

RUNNER = Path(__file__).resolve().parents[1] / "ui" / "live-runner.js"
KEY_CALL = re.compile(r"\bt\('([A-Za-z0-9_.]+)'\)")


def _runner_keys():
    return sorted(set(KEY_CALL.findall(RUNNER.read_text(encoding="utf-8"))))


def test_runner_asks_for_at_least_one_key():
    # Guards against the regex silently matching nothing and the contract passing empty.
    assert _runner_keys(), "no t('…') calls found in ui/live-runner.js"


def test_every_launch_locale_has_copy():
    assert set(UI_COPY) == set(UI_LANGUAGES)


@pytest.mark.parametrize("locale", sorted(UI_LANGUAGES))
def test_runner_keys_exist_in_locale(locale):
    missing = [key for key in _runner_keys() if key not in UI_COPY[locale]]
    assert not missing, f"{locale}: missing {missing}"
