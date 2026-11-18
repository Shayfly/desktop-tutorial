"""Exercise the runtime boundaries without a provider key, DB or paid call."""
import io
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from omni_prod.discovery import start
from omni_prod.intake.interpreter import contextual_user
from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelGatewayError, OpenAICompatibleGateway
from omni_prod.product_spec import ProductSpec
from omni_prod.providers.venice import NoAllowedModel
from omni_prod.providers.venice_gateway import VeniceIntakeGateway
from omni_prod.routed_gateway import RoutedModelGateway
from omni_prod.spec_review import SpecificationReview
from tests.test_architect_spec_shape import GOOD
from tests.test_venice_allowed_models import item

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'infra/worker-host/model-catalog.json').read_text())
PRIVATE = [r for r in CATALOG if r['provider'] == 'venice']
KEY = {'VENICE_API_KEY1': 'synthetic'}


def test_context_remembers_earlier_turns_and_preserves_valid_json(monkeypatch):
    monkeypatch.setenv('OMNI_INTAKE_AGENT', '1')
    dialogue = [{'role': 'customer', 'content': 'Use a green heading'},
                {'role': 'assistant', 'content': 'Recorded.'}] * 7
    user = contextual_user('Continue', start('Equipment loans for our team'), dialogue)
    context = json.loads(user.split('\n', 1)[1].split('\nCurrent customer message:')[0])
    assert context['recent_messages'] == dialogue
    assert not context['earlier_turns_omitted']


@pytest.mark.parametrize('row', PRIVATE, ids=lambda r: r['model'])
def test_private_worker_routes_are_staged_and_role_scoped(row):
    model, = parse_model_catalog(json.dumps([row]), KEY)
    assert not model.endpoint
    active = {**row, 'enabled': True, 'quality': 85}
    model, = parse_model_catalog(json.dumps([active]), KEY)
    gw = RoutedModelGateway(ranked=(model,))
    assert gw.ranked_routes({}, row['allowed_tasks'][0])
    assert not gw.ranked_routes({}, 'general')


@pytest.mark.parametrize('privacy,price,allowed', [('private', '1.00', True), ('private', '1.01', False),
                                                   ('anonymized', '0.01', False)])
def test_private_gateway_rechecks_price_and_privacy_before_disclosing_content(privacy, price, allowed):
    row = next(r for r in PRIVATE if r['model'] == 'grok-build-0-1')
    model, = parse_model_catalog(json.dumps([{**row, 'enabled': True, 'quality': 85}]), KEY)
    methods = []

    def transport(req, timeout):
        methods.append(req.get_method())
        if req.get_method() == 'GET':
            assert req.data is None
            data = {'data': [item(row['model'], privacy, price, '2')]}
        else:
            data = {'choices': [{'message': {'content': '{"ok":true}'}}]}
        return io.BytesIO(json.dumps(data).encode())

    gw = OpenAICompatibleGateway(model.endpoint, urlopen=transport)
    if allowed:
        assert gw.complete_json(system='s', user='customer input') == {'ok': True}
        assert methods == ['GET', 'POST']
    else:
        with pytest.raises(ModelGatewayError):
            gw.complete_json(system='s', user='customer input')
        assert methods == ['GET']


def test_sonnet_first_without_lowering_a_reservation_ceiling():
    models = [item('claude-haiku-5-5', 'anonymized', '0.1', '0.5'),
              item('claude-sonnet-5-5', 'anonymized', '2', '10')]
    transport = Mock(return_value=(200, {'data': models}))
    args = dict(env=KEY, transport=transport, allowed=tuple(x['id'] for x in models))
    gw = VeniceIntakeGateway(Decimal('1'), ceiling=(Decimal('2'), Decimal('10')), **args)
    assert [m.id for m in gw.client.models()] == ['claude-sonnet-5-5']
    gw = VeniceIntakeGateway(Decimal('1'), ceiling=(Decimal('1'), Decimal('4')), **args)
    with pytest.raises(NoAllowedModel):
        gw.complete_json(system='s', user='u', max_tokens=20, call_id='test')
    assert all(c.args[0] == 'GET' for c in transport.call_args_list)


def test_reviewer_cannot_call_an_author_even_through_another_route():
    row = next(r for r in PRIVATE if 'spec_review' in r['allowed_tasks'])
    model, = parse_model_catalog(json.dumps([{**row, 'enabled': True, 'quality': 85}]), KEY)
    gw = RoutedModelGateway(ranked=(model,), gateway_factory=Mock(side_effect=AssertionError('no call')))
    gw.model_ids_by_task['architecture'] = {row['model']}
    gw.models_by_task['architecture'] = {'other-account'}
    with pytest.raises(ModelGatewayError, match='no independent'):
        gw.complete_json(task='spec_review', system='s', user='u')


@pytest.mark.parametrize('accepted,ids,findings,ok', [(True, ['R1'], [], True), (True, [], [], False),
    (True, ['R1','R1'], [], False), (False, ['R1'], [], False), (True, ['R1'], ['unsupported fact'], False)])
def test_spec_review_requires_full_coverage_and_a_clean_verdict(accepted, ids, findings, ok):
    gw = Mock(model_ids_by_task={'spec_review': {'reviewer'}})
    gw.complete_json.return_value = {'accepted': accepted, 'reviewed_ids': ids, 'findings': findings}
    check = SpecificationReview(gw, 'A team dashboard', [])
    spec = ProductSpec.from_dict(GOOD)
    if ok:
        check.check(spec)
        assert check.evidence['model_ids'] == ['reviewer']
        assert len(check.evidence['spec_sha256']) == 64
    else:
        with pytest.raises(ValueError):
            check.check(spec)
        assert check.evidence is None
