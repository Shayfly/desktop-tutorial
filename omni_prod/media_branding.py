from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from .branding import BrandingEngine
from .media_gateway import GeneratedAsset
from .pricing import PlanCode


class MediaBrandingError(RuntimeError):
    pass


class MediaBrandingEngine:
    """Apply 148AI plan branding to materialized media without faking work.

    Raster images are watermarked locally. MP4 video can be watermarked locally
    when ffmpeg is available. Audio/voice/music/3D keep provenance metadata only;
    adding audible watermarks or mutating 3D geometry would damage user output.
    """

    def __init__(self, branding: BrandingEngine | None = None):
        self.branding = branding or BrandingEngine()

    def apply(
        self,
        asset: GeneratedAsset,
        *,
        plan: str | PlanCode,
        requested_visible: bool | None = None,
    ) -> GeneratedAsset:
        visible = self.branding.resolve_visible(plan=plan, requested_visible=requested_visible)
        meta = dict(asset.metadata or {})
        meta.update({
            'created_with': '148AI',
            'brand_domain': '148ailabs.com',
            'brand_provenance': True,
            'visible_branding': visible,
        })
        data = asset.data
        mime = asset.mime_type.lower()
        if visible and mime in {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}:
            data = self.branding.watermark_image_bytes(data)
            meta['branding_applied'] = 'raster-watermark'
        elif visible and mime == 'video/mp4':
            data = self._watermark_mp4(data)
            meta['branding_applied'] = 'video-watermark'
        elif visible:
            meta['branding_applied'] = 'provenance-only-for-nondestructive-media'
            meta['branding_instruction'] = 'Keep 148AI provenance in export metadata/manifest; do not degrade audio/voice/music/3D content.'
        else:
            meta['branding_applied'] = 'provenance-only'
        return GeneratedAsset(asset.asset_id, asset.mime_type, data, asset.provider, meta)

    def _watermark_mp4(self, payload: bytes) -> bytes:
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise MediaBrandingError('ffmpeg is required for visible MP4 watermarking')
        logo = self.branding.asset_dir / '148ai-logo-256.png'
        if not logo.exists():
            raise MediaBrandingError('148AI logo asset missing')
        with tempfile.TemporaryDirectory(prefix='148ai-media-') as td:
            td = Path(td)
            src = td / 'input.mp4'; dst = td / 'output.mp4'
            src.write_bytes(payload)
            cmd = [
                ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(src), '-i', str(logo),
                '-filter_complex', '[1:v]scale=96:-1[wm];[0:v][wm]overlay=W-w-18:H-h-18:format=auto',
                '-map', '0:a?', '-map', '0:v',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'copy',
                str(dst),
            ]
            # Mapping/filter ordering varies across ffmpeg builds; use a simpler
            # canonical command if the first form is rejected.
            run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if run.returncode != 0:
                cmd = [
                    ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                    '-i', str(src), '-i', str(logo),
                    '-filter_complex', '[1:v]scale=96:-1[wm];[0:v][wm]overlay=W-w-18:H-h-18[outv]',
                    '-map', '[outv]', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac',
                    str(dst),
                ]
                run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if run.returncode != 0 or not dst.exists():
                raise MediaBrandingError('ffmpeg watermark failed: ' + run.stderr.decode('utf-8', 'ignore')[-1000:])
            return dst.read_bytes()
