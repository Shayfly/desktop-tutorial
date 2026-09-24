from __future__ import annotations
from dataclasses import dataclass

SUPPORTED_LOCALES = ('en','he','es','fr','de','it','pt','ar','ru','ja','ko','zh','hi','tr','nl','pl','id','vi','th','uk')
RTL_LOCALES = frozenset({'he','ar'})

@dataclass(frozen=True)
class LocaleConfig:
    default_locale: str='en'
    enabled: tuple[str,...]=('en',)

    def __post_init__(self):
        if self.default_locale not in SUPPORTED_LOCALES:
            raise ValueError('unsupported default locale')
        if not self.enabled or self.default_locale not in self.enabled:
            raise ValueError('default locale must be enabled')
        if any(x not in SUPPORTED_LOCALES for x in self.enabled):
            raise ValueError('unsupported locale')

def direction(locale: str) -> str:
    if locale not in SUPPORTED_LOCALES: raise ValueError('unsupported locale')
    return 'rtl' if locale in RTL_LOCALES else 'ltr'

def html_attrs(locale: str) -> dict[str,str]:
    return {'lang': locale, 'dir': direction(locale)}
