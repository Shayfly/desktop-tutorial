"""A validated game definition -> one self-contained HTML page (warehouse 134).

The page is the tested runtime (runtime.js, byte for byte) plus the definition as JSON. No network, no external
file: it opens from a file, a preview or a deployment the same way, on the phone and on the computer.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .schema import direction, validate

RUNTIME = (Path(__file__).with_name('runtime.js')).read_text(encoding='utf-8')

_CSS = """
*{box-sizing:border-box}html,body{margin:0;height:100%;overflow:hidden;background:#000;touch-action:none;
-webkit-user-select:none;user-select:none;font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif}
#game{display:block;width:100vw;height:100vh}
#screen{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;
background:rgba(0,0,0,.55);color:#fff;text-align:center;padding:24px}
#screen[hidden]{display:none}
#screen-title{margin:0;font-size:clamp(28px,6vw,56px);line-height:1.1}
#screen-text{margin:0;font-size:clamp(17px,2.6vw,24px);max-width:36ch;opacity:.92}
#screen-btn{font:inherit;font-size:22px;font-weight:700;min-width:180px;min-height:56px;border:0;border-radius:14px;
padding:0 28px;background:#fff;color:#111;cursor:pointer}
#screen-btn:focus-visible{outline:4px solid #ffd54a;outline-offset:3px}
#touch{position:fixed;inset:auto 0 0 0;display:flex;justify-content:space-between;align-items:flex-end;gap:10px;
padding:14px max(14px,env(safe-area-inset-right)) max(14px,env(safe-area-inset-bottom)) max(14px,env(safe-area-inset-left));
pointer-events:none;direction:ltr}
#touch[hidden]{display:none}
.tb{pointer-events:auto;width:68px;height:68px;border-radius:50%;border:2px solid rgba(255,255,255,.55);
background:rgba(0,0,0,.35);color:#fff;font-size:28px;line-height:1;touch-action:none}
.tb:active{background:rgba(255,255,255,.3)}
.tb-jump,.tb-fire{margin-inline-start:auto;width:84px;height:84px}
#rotate{position:fixed;top:max(10px,env(safe-area-inset-top));inset-inline:12px;padding:10px 14px;border-radius:12px;
background:rgba(0,0,0,.6);color:#fff;font-size:16px;text-align:center;pointer-events:none}
#rotate[hidden]{display:none}
"""


def build_html(defn: dict) -> str:
    validate(defn)
    page_def = dict(defn, dir=direction(defn))
    data = json.dumps(page_def, ensure_ascii=False).replace('</', '<\\/')
    title = html.escape(defn['title'])
    return (
        '<!doctype html>\n'
        f'<html lang="{defn["lang"]}" dir="{page_def["dir"]}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover">\n'
        f'<meta name="theme-color" content="{defn["palette"]["bg"]}">\n'
        f'<title>{title}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n'
        f'<canvas id="game" role="img" aria-label="{title}"></canvas>\n'
        '<div id="screen" role="dialog" aria-live="polite"><h1 id="screen-title"></h1><p id="screen-text"></p>'
        '<button id="screen-btn" type="button"></button></div>\n'
        '<div id="touch" hidden></div>\n'
        '<div id="rotate" role="status" hidden></div>\n'
        f'<script id="game-def" type="application/json">{data}</script>\n'
        f'<script>{RUNTIME}</script>\n</body>\n</html>\n'
    )
