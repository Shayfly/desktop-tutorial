"""G3 acceptance: opt-in, disposable loopback DB, deliberately red on base SHA."""
import json
import os
from pathlib import Path
import uuid

import pytest

from tests.financial_fault_harness import run_case, validate_database


DATABASE_URL = os.environ.get('FINANCIAL_FAULT_DATABASE_URL')


@pytest.mark.skipif(not DATABASE_URL, reason='requires an explicit disposable financial-fault database')
@pytest.mark.parametrize('fail_ledger', [False, True], ids=['durable-ledger', 'failed-ledger'])
def test_crashed_worker_preserves_provider_liability(fail_ledger: bool):
    validate_database(DATABASE_URL)
    output = Path(os.environ.get('FINANCIAL_FAULT_OUTPUT_DIR', 'work/financial-fault-acceptance')) / uuid.uuid4().hex
    output.mkdir(parents=True)
    result = run_case(DATABASE_URL, output, fail_ledger=fail_ledger)
    (output / 'result.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    failures = [name for name, passed in result['checks'].items() if not passed]
    assert not failures, json.dumps({'failed_acceptance': failures, 'result': result}, default=str)
