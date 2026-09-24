from __future__ import annotations
import re

_SEG=re.compile(r'^[A-Za-z0-9._-]{1,120}$')

def _seg(value: str) -> str:
    if not _SEG.fullmatch(value or '') or value in {'.','..'}:
        raise ValueError('unsafe artifact key segment')
    return value

def build_artifact_key(*, project_id: str, version_id: str, build_id: str, filename: str='app.zip') -> str:
    parts=[_seg(project_id),_seg(version_id),_seg(build_id),_seg(filename)]
    return f'projects/{parts[0]}/versions/{parts[1]}/builds/{parts[2]}/{parts[3]}'
