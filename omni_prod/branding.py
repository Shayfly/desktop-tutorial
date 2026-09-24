from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import io
import json
from pathlib import Path

from .pricing import PLAN_CATALOG, PlanCode


BRAND_NAME = '148AI'
BRAND_DOMAIN = '148ailabs.com'
TAGLINE = 'Build Anything.'


@dataclass(frozen=True)
class BrandingPolicy:
    plan: str
    visible_branding_required: bool
    visible_branding_default: bool
    can_remove_visible_branding: bool
    white_label_allowed: bool
    provenance_required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BrandingEngine:
    def __init__(self, *, asset_dir: str | Path | None = None):
        self.asset_dir = Path(asset_dir) if asset_dir else Path(__file__).resolve().parent / 'assets' / 'brand'

    def policy_for(self, plan: str | PlanCode) -> BrandingPolicy:
        code = plan if isinstance(plan, PlanCode) else PlanCode(plan)
        p = PLAN_CATALOG[code]
        required = p.branding in {'required', 'subtle-required'}
        return BrandingPolicy(
            plan=code.value,
            visible_branding_required=required,
            visible_branding_default=required or code == PlanCode.PRO,
            can_remove_visible_branding=p.removable_branding,
            white_label_allowed=p.white_label,
        )

    def resolve_visible(self, *, plan: str | PlanCode, requested_visible: bool | None) -> bool:
        policy = self.policy_for(plan)
        if policy.visible_branding_required:
            if requested_visible is False:
                raise PermissionError('visible 148AI branding cannot be removed on this plan')
            return True
        if requested_visible is None:
            return policy.visible_branding_default
        if not requested_visible and not policy.can_remove_visible_branding:
            raise PermissionError('visible 148AI branding cannot be removed on this plan')
        return bool(requested_visible)

    def decorate_repository(
        self,
        repository: dict[str, str],
        *,
        plan: str | PlanCode,
        project_id: str,
        version_hint: str = '',
        requested_visible: bool | None = None,
        white_label_name: str | None = None,
    ) -> dict[str, str]:
        code = plan if isinstance(plan, PlanCode) else PlanCode(plan)
        policy = self.policy_for(code)
        visible = self.resolve_visible(plan=code, requested_visible=requested_visible)
        if white_label_name and not policy.white_label_allowed:
            raise PermissionError('white-label exports require Business/Enterprise')

        repo = dict(repository)
        signature_source = '\n'.join(f'{k}\0{repo[k]}' for k in sorted(repo)) + f'\0{project_id}\0{version_hint}'
        signature = sha256(signature_source.encode('utf-8')).hexdigest()
        manifest = {
            'brand': BRAND_NAME,
            'domain': BRAND_DOMAIN,
            'tagline': TAGLINE,
            'plan': code.value,
            'visible_branding': visible,
            'white_label_name': white_label_name or '',
            'provenance_signature_sha256': signature,
            'truth': 'Visible branding follows plan policy. Provenance remains even when visible branding is removable.',
        }
        repo['.148ai/brand-manifest.json'] = json.dumps(manifest, indent=2, sort_keys=True)
        repo['.148ai/provenance.json'] = json.dumps({
            'created_with': BRAND_NAME,
            'project_id': project_id,
            'version_hint': version_hint,
            'repository_signature_sha256': signature,
        }, indent=2, sort_keys=True)

        badge_svg = self.badge_svg(white_label_name if white_label_name else BRAND_NAME)
        repo['public/148ai-badge.svg'] = badge_svg
        if visible:
            for path, content in list(repo.items()):
                if path.lower().endswith(('.html', '.htm')) and '</body>' in content.lower():
                    repo[path] = self._inject_html_badge(content)
        return repo

    @staticmethod
    def _inject_html_badge(html: str) -> str:
        if 'data-148ai-brand' in html:
            return html
        badge = (
            '<a data-148ai-brand="1" href="https://148ailabs.com" target="_blank" rel="noopener" '
            'style="position:fixed;right:14px;bottom:14px;z-index:2147483000;background:#07101f;color:#fff;'
            'border:1px solid #1f4ea8;border-radius:999px;padding:7px 10px;font:600 12px/1 system-ui;'
            'text-decoration:none;box-shadow:0 4px 18px #0004">Built with 148AI</a>'
        )
        lower = html.lower()
        idx = lower.rfind('</body>')
        return html[:idx] + badge + html[idx:] if idx >= 0 else html + badge

    @staticmethod
    def badge_svg(label: str = BRAND_NAME) -> str:
        safe = ''.join(ch for ch in label if ch.isalnum() or ch in ' ._-')[:40] or BRAND_NAME
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="164" height="42" viewBox="0 0 164 42" role="img" aria-label="{safe}"><rect width="164" height="42" rx="21" fill="#07101f"/><rect x=".5" y=".5" width="163" height="41" rx="20.5" fill="none" stroke="#1f64ff"/><text x="82" y="26" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="16" font-weight="700" fill="white">{safe}</text></svg>'''

    def watermark_image_bytes(self, image_bytes: bytes, *, opacity: float = 0.58, scale: float = 0.18) -> bytes:
        """Apply the approved 148AI mark to a raster image.

        This is used only when a plan requires/chooses visible media branding.
        Video/audio/3D providers receive equivalent instructions through the
        brand manifest rather than pretending local transcoding occurred.
        """
        from PIL import Image
        if not 0.05 <= opacity <= 1:
            raise ValueError('opacity must be between .05 and 1')
        if not 0.05 <= scale <= 0.5:
            raise ValueError('scale must be between .05 and .5')
        base = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
        mark = Image.open(self.asset_dir / '148ai-logo-256.png').convert('RGBA')
        max_w = max(24, int(base.width * scale))
        mark.thumbnail((max_w, max_w), Image.Resampling.LANCZOS)
        a = mark.getchannel('A').point(lambda p: int(p * opacity))
        mark.putalpha(a)
        margin = max(8, int(min(base.size) * .025))
        pos = (base.width - mark.width - margin, base.height - mark.height - margin)
        base.alpha_composite(mark, pos)
        out = io.BytesIO(); base.save(out, format='PNG')
        return out.getvalue()
