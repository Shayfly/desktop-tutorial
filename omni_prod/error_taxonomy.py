from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ErrorClass(str, Enum):
    TRANSIENT = 'transient'
    USER_CODE = 'user_code'
    PROVIDER = 'provider'
    POLICY = 'policy'
    INFRASTRUCTURE = 'infrastructure'
    UNKNOWN = 'unknown'

@dataclass(frozen=True)
class ClassifiedError:
    category: ErrorClass
    retryable: bool
    repairable: bool

_RETRYABLE_MARKERS = ('timeout', 'temporarily unavailable', 'connection reset', 'rate limit', '429', '503')
_USER_CODE_MARKERS = ('syntaxerror', 'typeerror', 'referenceerror', 'modulenotfounderror', 'assertionerror')
_POLICY_MARKERS = ('policy violation', 'forbidden capability', 'network disabled', 'budget exceeded')

def classify_error(message: str) -> ClassifiedError:
    text=(message or '').lower()
    if any(x in text for x in _POLICY_MARKERS):
        return ClassifiedError(ErrorClass.POLICY, False, False)
    if any(x in text for x in _RETRYABLE_MARKERS):
        return ClassifiedError(ErrorClass.TRANSIENT, True, False)
    if any(x in text for x in _USER_CODE_MARKERS):
        return ClassifiedError(ErrorClass.USER_CODE, False, True)
    if 'provider' in text or 'model' in text:
        return ClassifiedError(ErrorClass.PROVIDER, True, False)
    if 'docker' in text or 'disk' in text or 'worker' in text:
        return ClassifiedError(ErrorClass.INFRASTRUCTURE, True, False)
    return ClassifiedError(ErrorClass.UNKNOWN, False, True)
