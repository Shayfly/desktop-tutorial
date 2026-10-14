#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omni_prod.secret_scan import scan_tree
from omni_prod.release_manifest import verify_release_manifest
from omni_prod.pricing import PLAN_CATALOG, PlanCode

checks = {}

def run(name, argv):
    p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    checks[name] = {
        'ok': p.returncode == 0,
        'returncode': p.returncode,
        'stdout': p.stdout[-7000:],
        'stderr': p.stderr[-7000:],
    }
    return p.returncode == 0

def check(name, ok, detail=''):
    checks[name] = {'ok': bool(ok), 'detail': detail}
    return bool(ok)

ok = True
ok &= run('compileall', [sys.executable, '-m', 'compileall', '-q', 'omni_prod', 'tests'])
ok &= run('pytest', [sys.executable, '-m', 'pytest', '-q'])
ok &= run('v10_parity', [sys.executable, '-m', 'pytest', '-q', 'tests/test_v25_unified_v10_parity.py'])
ok &= run('v26_product', [sys.executable, '-m', 'pytest', '-q', 'tests/test_v26_universal_pro.py'])
ok &= run('v27_rights_company_os', [sys.executable, '-m', 'pytest', '-q', 'tests/test_v27_rights_company_os.py'])
ok &= run('v28_brand_pricing_launch', [sys.executable, '-m', 'pytest', '-q', 'tests/test_v28_148ai_launch.py'])
ok &= run('javascript', ['node', '--check', 'omni_prod/assets/app.js'])

bench_path = ROOT / 'BENCHMARK_V28_OFFLINE.json'
bench = json.loads(bench_path.read_text()) if bench_path.exists() else {}
ok &= check('benchmark_v28_200', bench.get('cases') == 200 and bench.get('passed') == 200 and bench.get('failed') == 0,
            json.dumps(bench, sort_keys=True))

http_path = ROOT / 'LIVE_HTTP_V28.json'
http = json.loads(http_path.read_text()) if http_path.exists() else {}
http_ok = (
    http.get('product') == '148AI' and
    http.get('status_code') == 200 and
    http.get('pricing_status') == 200 and
    http.get('default_plan') == 'free' and
    http.get('safe_build_status') == 200 and
    http.get('safe_rights') == 'CLEAR' and
    http.get('safe_promote_status') == 200 and
    http.get('brand_manifest_in_export') is True and
    http.get('provenance_in_export') is True and
    http.get('risky_rights') == 'LEGAL_REVIEW_REQUIRED' and
    http.get('risky_promote_status') == 409 and
    http.get('free_third_project_status') == 402 and
    http.get('free_live_build_status') == 402 and
    http.get('integration_payload_contains_secret_values') is False and
    http.get('creator_without_billing_admin_key_status') == 403
)
ok &= check('production_http_v28', http_ok, json.dumps(http, sort_keys=True))

load_path = ROOT / 'LOAD_SMOKE_V28.json'
load = json.loads(load_path.read_text()) if load_path.exists() else {}
ok &= check('local_load_smoke', load.get('requests') == 200 and load.get('ok') == 200 and load.get('errors') == 0,
            json.dumps(load, sort_keys=True))

margin_detail = {}
for code, floor in [(PlanCode.BASIC, 0.70), (PlanCode.PRO, 0.70), (PlanCode.BUSINESS, 0.70)]:
    plan = PLAN_CATALOG[code]
    margin = plan.variable_margin_floor()
    margin_detail[code.value] = None if margin is None else float(margin)
    ok &= check(f'{code.value}_variable_margin_floor', margin is not None and float(margin) >= floor,
                f'margin_floor={margin}; excludes fixed infrastructure/support/tax/payment processing')

brand_dir = ROOT / 'omni_prod' / 'assets' / 'brand'
required_brand = [
    '148ai-logo-master.png','148ai-logo-512.png','148ai-logo-128.png',
    '148ai-watermark-256.png','148ai-app-icon-512.png','148ai-favicon.ico'
]
ok &= check('brand_pack_assets', all((brand_dir / n).exists() for n in required_brand), ','.join(required_brand))
ok &= check('creator_postgres_migrations',
            (ROOT/'infra/postgres/011_creator_accounts.sql').exists() and (ROOT/'infra/postgres/012_creator_subscriptions.sql').exists())

findings = scan_tree(ROOT)
ok &= check('secret_scan', not findings, f'{len(findings)} findings')
manifest_ok, errors = verify_release_manifest(ROOT)
ok &= check('release_manifest', manifest_ok, '; '.join(errors[:30]))

checks['external_live_gates'] = {
    'ok': True,
    'detail': {
        'creator_postgres_live': 'NOT_RUN_HERE',
        'redis_live': 'NOT_RUN_HERE',
        's3_r2_live': 'NOT_RUN_HERE',
        'open_weight_gpu_model': 'NOT_CONNECTED',
        'remote_docker_sandbox': 'NOT_CONNECTED',
        'image_audio_music_video_3d_models': 'NOT_CONNECTED',
        'stripe_checkout_webhooks': 'NOT_CONNECTED',
        'resend_live_email': 'NOT_CONNECTED',
        'signed_android_aab': 'NOT_RUN_HERE',
        'signed_ios_ipa': 'NOT_RUN_HERE',
        'public_domain_dns_tls': 'DOMAIN_NOT_CONFIRMED_PURCHASED',
        '148AI_trademark_clearance': 'NOT_COMPLETED',
        'full_human_translation_qa_all_20_locales': 'NOT_COMPLETED',
    }
}

payload = {'ok': bool(ok), 'release': '148AI V28 Launch Candidate Reviewer', 'checks': checks}
print(json.dumps(payload, indent=2))
raise SystemExit(0 if ok else 1)
