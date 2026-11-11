#!/usr/bin/env python3
"""Fail-closed, offline gate for trusted Golden E2E collector evidence (stdlib only).

Checks evidence integrity and cross-stage consistency, not the authenticity of
an untrusted producer. Never executes product code or fetches evidence URLs.
See docs/GOLDEN_EVIDENCE_GATE.md for the producer contract and CI invocation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlsplit
import zipfile

SECTIONS = ('input', 'r2', 'preview', 'accounting')
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024


class InvalidEvidence(ValueError):
    pass


def need(condition, label):
    if not condition:
        raise InvalidEvidence(label)


def text(value, label):
    need(isinstance(value, str) and bool(value.strip()), label)
    return value


def integer(value, label, minimum=0):
    need(type(value) is int and value >= minimum, label)
    return value


def money(value):
    # Decimal strings only: reject floats/bools, NaN/infinity, signs and huge exponents.
    need(isinstance(value, str) and re.fullmatch(r'\d{1,12}(?:\.\d{1,18})?', value), 'missing_or_invalid_actual_cost')
    return Decimal(value)


def timestamp(value):
    need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z', value),
         'missing_or_invalid_utc_timestamp')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def json_object(raw):
    need(len(raw) <= MAX_JSON_BYTES, 'json_too_large')
    obj = json.loads(raw, object_pairs_hook=pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(InvalidEvidence('nonfinite_json_number')))
    need(type(obj) is dict, 'expected_json_object')
    return obj


class Bundle:
    def __init__(self, manifest, identity):
        self.root = manifest.parent.resolve()
        self.identity = identity
        need(manifest.is_file() and 0 < manifest.stat().st_size <= MAX_JSON_BYTES, 'missing_empty_or_oversize_manifest')
        self.manifest = json_object(manifest.read_bytes())
        self.bind(self.manifest)
        need(type(self.manifest['schema_version']) is int and self.manifest['schema_version'] == 1, 'schema_version')
        need(type(self.manifest['manual_steps']) is int and self.manifest['manual_steps'] == 0, 'manual_steps_not_zero')

    def bind(self, record):
        need(type(record) is dict, 'expected_receipt_object')
        for key, value in self.identity.items():
            need(record[key] == value, 'identity_mismatch_' + key)
        return record

    def blob(self, ref):
        need(type(ref) is dict, 'expected_file_reference')
        name = text(ref['path'], 'missing_evidence_path')
        relative = PurePosixPath(name)
        need(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name,
             'unsafe_evidence_path')
        path = self.root.joinpath(*relative.parts)
        need(all(not p.is_symlink() for p in (path, *path.parents) if p != self.root.parent),
             'symlink_evidence_rejected')
        need(path.resolve().is_relative_to(self.root), 'evidence_outside_bundle')
        need(path.is_file() and 0 < path.stat().st_size <= MAX_FILE_BYTES, 'missing_empty_or_oversize_file')
        digest = text(ref['sha256'], 'missing_sha256')
        need(re.fullmatch('[a-f0-9]{64}', digest), 'invalid_sha256')
        raw = path.read_bytes()
        need(len(raw) <= MAX_FILE_BYTES and hashlib.sha256(raw).hexdigest() == digest, 'evidence_sha256_mismatch')
        return raw

    def receipt(self, section):
        return self.bind(json_object(self.blob(self.manifest[section])))


def check_input(b, records):
    r = records['input']
    prompt = text(r['prompt'], 'missing_hebrew_prompt')
    need(any('\u05d0' <= c <= '\u05ea' for c in prompt), 'prompt_contains_no_hebrew_letters')
    need(r['channel'] == 'customer_ui', 'input_did_not_use_customer_ui')
    need(timestamp(r['submitted_at']) <= timestamp(r['accepted_at']), 'input_time_order')
    requirements = r['requirements']
    need(type(requirements) is list and requirements, 'missing_requirements')
    ids = []
    for item in requirements:
        ids.append(text(item['id'], 'missing_acceptance_id'))
        text(item['text'], 'missing_requirement_text')
    need(len(set(ids)) == len(ids), 'duplicate_acceptance_id')
    requests = r['provider_request_ids']
    need(type(requests) is list and requests, 'missing_real_provider_request_ids')
    need(all(isinstance(x, str) and x.strip() for x in requests) and len(set(requests)) == len(requests),
         'invalid_or_duplicate_provider_request_id')


def check_r2(b, records):
    r = records['r2']
    need(r['provider'] == 'cloudflare_r2', 'artifact_not_in_r2')
    for key in ('bucket', 'key', 'version_id'):
        text(r[key], 'missing_r2_' + key)
    need(type(r['put_status']) is int and r['put_status'] in (200, 201, 204), 'r2_put_failed')
    need(type(r['get_status']) is int and r['get_status'] == 200, 'r2_readback_failed')
    need(timestamp(records['input']['accepted_at']) <= timestamp(r['written_at']) <= timestamp(r['readback_at']),
         'r2_time_order')
    raw = b.blob(r['artifact'])
    digest = hashlib.sha256(raw).hexdigest()
    need(r['sha256'] == r['readback_sha256'] == digest, 'r2_readback_content_mismatch')
    need(integer(r['bytes_written'], 'invalid_r2_byte_count', 1) == len(raw), 'r2_size_mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files = [f for f in archive.infolist() if not f.is_dir()]
        names = [f.filename for f in files]
        need(2 <= len(files) <= 10000 and len(set(names)) == len(files), 'not_a_unique_multifile_artifact')
        need(sum(f.file_size for f in files) <= MAX_FILE_BYTES, 'expanded_artifact_too_large')
        need(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n
                 for n in names), 'unsafe_archive_member')
        need(archive.testzip() is None, 'corrupt_archive_member')
        need(integer(r['file_count'], 'invalid_file_count', 2) == len(files), 'file_count_mismatch')


def check_preview(b, records):
    r, source = records['preview'], records['r2']
    url = urlsplit(text(r['url'], 'missing_preview_url'))
    need(url.scheme == 'https' and url.hostname and not url.username and not url.password, 'invalid_preview_url')
    need(type(r['http_status']) is int and r['http_status'] == 200, 'preview_http_failed')
    need(r['status'] == 'PASS' and r['browser'] == 'playwright', 'browser_did_not_pass')
    need(r['version_id'] == source['version_id'] and r['artifact_sha256'] == source['readback_sha256'],
         'preview_is_not_the_stored_artifact')
    need(timestamp(source['readback_at']) <= timestamp(r['opened_at']) <= timestamp(r['verified_at']),
         'preview_time_order')
    checks = r['checks']
    need(type(checks) is list and checks, 'missing_browser_acceptance_checks')
    seen = []
    for item in checks:
        seen.append(text(item['acceptance_id'], 'missing_browser_acceptance_id'))
        need(item['passed'] is True, 'browser_acceptance_failed_or_not_boolean')
        text(item['detail'], 'missing_browser_observation')
    required = {item['id'] for item in records['input']['requirements']}
    need(set(seen) == required and len(seen) == len(required), 'browser_acceptance_coverage_mismatch')
    image = b.blob(r['screenshot'])
    need(len(image) > 32 and image.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff')), 'invalid_screenshot_bytes')


def check_accounting(b, records, max_cost, max_ms):
    r = records['accounting']
    need(r['currency'] == 'USD' and r['cost_status'] == 'KNOWN', 'cost_UNKNOWN')
    amount = money(r['actual_cost_usd'])
    ledger = b.bind(json_object(b.blob(r['ledger'])))
    need(ledger['complete'] is True, 'ledger_incomplete_cost_UNKNOWN')
    entries = ledger['entries']
    need(type(entries) is list and entries, 'missing_cost_entries')
    ids, sources, kinds, total = set(), set(), set(), Decimal('0')
    for entry in entries:
        eid = text(entry['id'], 'missing_ledger_entry_id')
        source = text(entry['source_id'], 'missing_cost_source_id')
        need(eid not in ids and source not in sources, 'duplicate_cost_entry')
        ids.add(eid)
        sources.add(source)
        need(entry['basis'] in ('measured', 'reconciled'), 'estimated_cost_is_not_actual')
        need(entry['kind'] in ('model', 'compute', 'storage', 'egress'), 'unknown_cost_kind')
        kinds.add(entry['kind'])
        with localcontext() as ctx:
            ctx.prec = 80
            total += money(entry['actual_cost_usd'])
    need(kinds == {'model', 'compute', 'storage', 'egress'}, 'cost_components_incomplete')
    model_sources = {e['source_id'] for e in entries if e['kind'] == 'model'}
    need(set(records['input']['provider_request_ids']) == model_sources, 'provider_cost_coverage_mismatch')
    need(total == amount, 'ledger_total_mismatch')
    need(amount <= max_cost, 'cost_budget_exceeded')
    need(r['includes_retries'] is True and r['includes_repairs'] is True, 'partial_cost_scope')
    elapsed = integer(r['elapsed_ms'], 'missing_exact_elapsed_ms', 1)
    queue = integer(r['queue_ms'], 'missing_queue_ms')
    start = timestamp(records['input']['submitted_at'])
    accepted = timestamp(records['input']['accepted_at'])
    end = timestamp(records['preview']['verified_at'])
    need(elapsed == (end - start) // timedelta(milliseconds=1), 'elapsed_wallclock_mismatch')
    need(queue == (accepted - start) // timedelta(milliseconds=1), 'queue_time_mismatch')
    mono_start = integer(r['started_monotonic_ns'], 'missing_monotonic_start')
    mono_end = integer(r['finished_monotonic_ns'], 'missing_monotonic_finish')
    need(mono_end >= mono_start and (mono_end - mono_start) // 1000000 == elapsed, 'monotonic_duration_mismatch')
    need(elapsed <= max_ms, 'time_limit_exceeded')
    return str(amount), elapsed


def verify(manifest, *, identity, max_cost, max_ms):
    result = {'status': 'FAIL', 'cost_status': 'UNKNOWN', 'actual_cost_usd': None, 'elapsed_ms': None,
              'checks': {name: {'status': 'FAIL', 'errors': []} for name in SECTIONS}, 'errors': []}
    records = {}
    try:
        need(all(isinstance(v, str) and v.strip() for v in identity.values()), 'invalid_expected_identity')
        need(re.fullmatch('[a-f0-9]{40}', identity['commit']), 'expected_full_commit_sha')
        need(max_cost.is_finite() and max_cost >= 0 and type(max_ms) is int and max_ms > 0, 'invalid_policy_limits')
        bundle = Bundle(Path(manifest), identity)
    except Exception as exc:
        result['errors'].append(str(exc) if isinstance(exc, InvalidEvidence) else type(exc).__name__)
        for check in result['checks'].values():
            check['errors'].append('manifest_unavailable_or_invalid')
        return result
    for name in SECTIONS:
        try:
            records[name] = bundle.receipt(name)
        except Exception as exc:
            result['checks'][name]['errors'].append(str(exc) if isinstance(exc, InvalidEvidence) else type(exc).__name__)
    validators = {'input': check_input, 'r2': check_r2, 'preview': check_preview,
                  'accounting': lambda b, r: check_accounting(b, r, max_cost, max_ms)}
    for name, validator in validators.items():
        check = result['checks'][name]
        if check['errors']:
            continue
        try:
            value = validator(bundle, records)
            if name == 'accounting':
                # Cost cannot be called known for an input/preview identity or scope that failed validation.
                need(all(result['checks'][s]['status'] == 'PASS' for s in SECTIONS[:-1]), 'unverified_build_scope_cost_UNKNOWN')
                result.update(cost_status='KNOWN', actual_cost_usd=value[0], elapsed_ms=value[1])
            check['status'] = 'PASS'
        except Exception as exc:
            check['errors'].append(str(exc) if isinstance(exc, InvalidEvidence) else type(exc).__name__)
    if all(c['status'] == 'PASS' for c in result['checks'].values()):
        result['status'] = 'PASS'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build-id', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--max-cost-usd', required=True)
    parser.add_argument('--max-elapsed-ms', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        cap = money(args.max_cost_usd)
    except InvalidEvidence:
        cap = Decimal('-1')
    report = verify(args.manifest, identity={'run_id': args.run_id, 'build_id': args.build_id, 'commit': args.commit},
                    max_cost=cap, max_ms=args.max_elapsed_ms)
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
