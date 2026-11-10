"""Probe manifest (Michael 2026-11-10, conditions 1, 2, 5 before the frozen run).

Every probe the build is judged by, with two declared properties -- declared here, never inferred from code:
  reads_source  None, or the reason the SERVED page cannot show what this probe checks (it reads source files)
  critical      True when a quarantine of this probe must never release silently (Hebrew page served LTR,
                a fabricated tel/WhatsApp, a missing alt). A critical probe in quarantine withdraws release_ready.

tests/test_frozen_run_conditions_20261110.py fails when a static check is missing here, when a check reads source
without a declaration, when the declaration here and the @reads_source decorator disagree, or when the critical set
is empty. Six probes read source: the five code checks in skills_runtime and the secret scan in the quality gate.
"""
from __future__ import annotations

PROBES: dict[str, dict] = {
    # ---- markup probes: judge the SERVED page (preview smoke) ----
    '_rtl_for_hebrew': {'skill': 'skill.text_locale', 'reads_source': None, 'critical': True},
    '_invented_contact': {'skill': 'skill.copy_quality', 'reads_source': None, 'critical': True},   # tel, wa.me, street
    '_images_without_alt': {'skill': 'skill.accessibility', 'reads_source': None, 'critical': True},
    '_unlabelled_inputs': {'skill': 'skill.accessibility', 'reads_source': None, 'critical': False},
    '_placeholder_copy': {'skill': 'skill.copy_quality', 'reads_source': None, 'critical': False},
    '_styled_page': {'skill': 'skill.visual_design', 'reads_source': None, 'critical': False},
    # ---- code probes: the defect exists only in source ----
    '_no_browser_dialogs': {'skill': 'skill.form_validation', 'critical': False,
                            'reads_source': 'alert()/confirm()/prompt() are JavaScript calls: they exist only in code'},
    '_unguarded_int_conversion': {'skill': 'skill.data_integrity', 'critical': False,
                                  'reads_source': 'int() of request input is server code'},
    '_escape_once': {'skill': 'skill.text_locale', 'critical': False,
                     'reads_source': 'html.escape() before an INSERT is server code'},
    '_innerhtml_interpolation': {'skill': 'skill.text_locale', 'critical': False,
                                 'reads_source': 'innerHTML with interpolation is a script-level XSS pattern'},
    '_sql_string_formatting': {'skill': 'skill.security_basics', 'critical': False,
                               'reads_source': 'SQL built with f-strings/format is server code'},
    '_auth_source_rules': {'skill': 'skill.site_auth', 'critical': True, 'flag': 'site_auth_v2',
                           'reads_source': 'password hashing and credentials in logs/URLs are server code'},
    # ---- outside skills_runtime ----
    'quality_gate.secret_scan': {'skill': 'quality_gate', 'critical': False,
                                 'reads_source': 'a hard-coded key is in source files, never in the served page'},
}

# JSON-LD schema: there is no JSON-LD probe yet. It is NOT added before the frozen run (a new gate would change the
# baseline being measured); when it is added it is declared critical here in the same PR.
NOT_YET_PROBED = ('json_ld_schema',)


def critical_probes() -> frozenset[str]:
    return frozenset(name for name, p in PROBES.items() if p['critical'])


def is_critical(probe: str | None) -> bool:
    return bool(probe) and PROBES.get(probe, {}).get('critical', False)
