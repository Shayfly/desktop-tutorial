"""Real image bytes made with Pillow, for tests whose pictures go through the image-weight conversion (2026-11-26).

Every photo and generated image the page carries is decoded and converted now (omni_prod/web_rendition.py): nothing is
carried byte for byte. A test picture must therefore be a real image. A few bytes that only START like a JPEG or a PNG
were enough while a light picture was carried untouched; they are refused by name now ("the image could not be read
as an image"). Every function returns different bytes for a different `seed`, so two pictures have two digests."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw


def picture(seed: int = 1, size=(160, 120), mode: str = 'RGB') -> Image.Image:
    """A small picture with a gradient, an edge and a colour of its own (seed)."""
    w, h = size
    tone = (37 * seed % 200 + 30, 91 * seed % 200 + 30, 53 * seed % 200 + 30)
    img = Image.linear_gradient('L').resize((w, h)).convert('RGB')
    img = Image.blend(img, Image.new('RGB', (w, h), tone), 0.6)
    d = ImageDraw.Draw(img)
    d.rectangle((w // 5, h // 4, w // 5 + max(1, w // 3), h // 4 + max(1, h // 3)), fill=tone[::-1])
    d.line((0, h - 1, w - 1, 0), fill=(250, 250, 250), width=max(1, w // 40))
    if mode == 'RGBA':
        img = img.convert('RGBA')
        img.putalpha(Image.linear_gradient('L').rotate(90).resize((w, h)))
    return img


def jpeg(seed: int = 1, size=(160, 120), quality: int = 90, **save) -> bytes:
    out = io.BytesIO()
    picture(seed, size).save(out, 'JPEG', quality=quality, **save)
    return out.getvalue()


def png(seed: int = 1, size=(64, 36), alpha: bool = False) -> bytes:
    out = io.BytesIO()
    picture(seed, size, 'RGBA' if alpha else 'RGB').save(out, 'PNG')
    return out.getvalue()


def webp(seed: int = 1, size=(64, 36)) -> bytes:
    out = io.BytesIO()
    picture(seed, size).save(out, 'WEBP', quality=90)
    return out.getvalue()
