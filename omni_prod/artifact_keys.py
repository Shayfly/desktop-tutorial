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

def build_capability_artifact_key(*, project_id: str, build_id: str, requirement_id: str, filename: str) -> str:
    parts = [_seg(project_id), _seg(build_id), _seg(requirement_id), _seg(filename)]
    return f'projects/{parts[0]}/builds/{parts[1]}/capabilities/{parts[2]}/{parts[3]}'


MEDIA_EXTENSIONS = ('png', 'jpg', 'webp', 'mp4', 'webm', 'mp3', 'wav', 'glb')


def build_media_key(*, account_id: str, project_id: str, sha256: str, ext: str) -> str:
    """S13.2: one key per generated media file, content-addressed and under its owner's account:
    tenants/<account>/projects/<project>/media/<sha256>.<ext>. The account is part of the key, so two accounts that
    generate the same bytes hold two objects and neither can learn the other's exists (no existence oracle)."""
    if not re.fullmatch(r'[0-9a-f]{64}', sha256 or ''):
        raise ValueError('a media key needs the sha256 of the file')
    if ext not in MEDIA_EXTENSIONS:
        raise ValueError(f'a media file of type .{ext} is not stored')
    return f'tenants/{_seg(account_id)}/projects/{_seg(project_id)}/media/{sha256}.{ext}'


def media_key_prefix(account_id: str) -> str:
    return f'tenants/{_seg(account_id)}/'
