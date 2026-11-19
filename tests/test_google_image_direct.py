import base64
import io
import json
from dataclasses import replace
from unittest import mock

import pytest
from PIL import Image

from omni_prod.capabilities import CapabilityRequirement, CapabilityPlan
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.memory_adapters import MemoryArtifactStore
from omni_prod.providers.image_provider import (build_image_provider, build_image_capability_stage,
                                               build_image_quote_resolver, MemorySubmissionJournal,
                                               AmbiguousSubmission)
from omni_prod.providers.google_image import readiness
from omni_prod.model_policy import ModelPolicyViolation

ENV = {'GEMINI_API_KEY': 'test-secret', 'OMNI_GOOGLE_IMAGE_MODEL': 'gemini-nano-banana-2.1',
       'OMNI_GOOGLE_IMAGE_MAXIMUM_USD': '0.25',
       'OMNI_GOOGLE_IMAGE_PRICE_SOURCE': 'https://aistudio.google.com/docs/pricing',
       'OMNI_GOOGLE_IMAGE_COMMERCIAL_USE': 'true',
       'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}
REQ = CapabilityRequirement('hero', 'media.image.generate', 'hero', True,
                            constraints={'prompt': 'An original blue door'})


class DurableTestJournal(MemorySubmissionJournal):
    # Persistence boundary is the existing journal, tested separately with PG.
    # This double retains records across adapter instances within these tests.
    durable = True


def transport(calls, *, mime='image/png', image_count=1):
    image = io.BytesIO()
    Image.new('RGB', (8, 8), 'blue').save(image, format='PNG')
    payload = {'candidates': [{'content': {'parts': [{'inlineData': {
        'mimeType': mime, 'data': base64.b64encode(image.getvalue()).decode()}}] * image_count}}],
        'usageMetadata': {'promptTokenCount': 10}}
    def send(req, **kwargs):
        calls.append(req)
        assert req.full_url == 'https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent'
        assert req.get_header('X-goog-api-key') == 'test-secret'
        assert 'test-secret' not in req.full_url
        body = json.loads(req.data)
        assert body['generationConfig']['candidateCount'] == 1
        assert body['generationConfig']['imageConfig']['imageSize'] == '1K'
        return io.BytesIO(json.dumps(payload).encode())
    return send


def test_reject_declared_mime_inconsistent_with_the_returned_bytes():
    calls = []
    store = MemoryArtifactStore()
    provider = build_image_provider(ENV, journal=DurableTestJournal(), artifact_store=store,
                                    urlopen=transport(calls, mime='image/jpeg'))
    with pytest.raises(RuntimeError, match='MIME does not match its bytes'):
        provider.submit(REQ, idempotency_key='build:wrong-mime')
    assert len(calls) == 1


def test_reject_more_than_one_image_in_a_single_provider_response():
    calls = []
    provider = build_image_provider(ENV, journal=DurableTestJournal(),
                                    artifact_store=MemoryArtifactStore(),
                                    urlopen=transport(calls, image_count=2))
    with pytest.raises(RuntimeError, match='exactly one image'):
        provider.submit(REQ, idempotency_key='build:extra-image')
    assert len(calls) == 1


def test_collect_checks_checksum_of_image_in_durable_storage():
    store = MemoryArtifactStore()
    provider = build_image_provider(ENV, journal=DurableTestJournal(), artifact_store=store,
                                    urlopen=transport([]))
    handle = provider.submit(REQ, idempotency_key='build:checksum')
    key = f'provider-results/google-image/{handle.provider_task_id}/0.json'
    saved = json.loads(store.get_bytes(key))
    # Simulate a swapped artifact whose bytes still parse and match its MIME type.
    other = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(other, format='PNG')
    saved['data'] = base64.b64encode(other.getvalue()).decode()
    read = store.get_bytes
    with (mock.patch.object(store, 'get_bytes',
                            side_effect=lambda path: json.dumps(saved).encode() if path == key else read(path)),
          pytest.raises(RuntimeError, match='Stored Google image checksum mismatch')):
        provider.collect(handle)


def test_reject_four_images_before_quote_or_provider_contact():
    send = mock.Mock(side_effect=AssertionError('network forbidden'))
    provider = build_image_provider(ENV, journal=DurableTestJournal(),
                                    artifact_store=MemoryArtifactStore(), urlopen=send)
    requirement = replace(REQ, quantity=4)
    with pytest.raises(ValueError, match='1 to 3 images'):
        provider.quote(requirement)
    with pytest.raises(ValueError, match='1 to 3 images'):
        provider.submit(requirement, idempotency_key='build:too-many-images')
    send.assert_not_called()


def test_reject_insecure_image_price_source_in_factory():
    env = {**ENV, 'OMNI_GOOGLE_IMAGE_PRICE_SOURCE': 'http://pricing.example.test/images'}
    assert readiness(env)['status'] == 'BLOCKED'
    assert build_image_provider(env, journal=DurableTestJournal()) is None


def test_factory_quote_and_generation_resume_through_existing_path():
    calls, store, journal = [], MemoryArtifactStore(), DurableTestJournal()
    provider = build_image_provider(ENV, journal=journal, artifact_store=store, urlopen=transport(calls))
    requirement = replace(REQ, quantity=3)
    assert str(provider.quote(requirement).maximum_cost_usd) == '0.75'
    handle = provider.submit(requirement, idempotency_key='build-1:hero')
    assert len(calls) == 3
    restarted = build_image_provider(ENV, journal=journal, artifact_store=store, urlopen=transport(calls))
    assert restarted.submit(requirement, idempotency_key='build-1:hero') == handle
    assert restarted.poll(handle).status == 'SUCCEEDED'
    result = restarted.collect(handle)
    assert len(result.payloads) == 3
    assert result.actual_cost_usd is None
    assert len(calls) == 3
    with pytest.raises(ValueError, match='different request'):
        restarted.submit(replace(REQ, purpose='changed', constraints={'prompt': 'different'}), idempotency_key='build-1:hero')
    with pytest.raises(ValueError, match='handle'):
        restarted.collect(replace(handle, provider_task_id='different'))


def test_uncertain_request_is_not_paid_for_again():
    calls, journal, store = [], DurableTestJournal(), MemoryArtifactStore()
    def timeout(req, **kwargs):
        calls.append(req)
        raise TimeoutError('provider response lost')
    provider = build_image_provider(ENV, journal=journal, artifact_store=store, urlopen=timeout)
    with pytest.raises(TimeoutError):
        provider.submit(REQ, idempotency_key='build:hero')
    restarted = build_image_provider(ENV, journal=journal, artifact_store=store, urlopen=timeout)
    with pytest.raises(AmbiguousSubmission):
        restarted.submit(REQ, idempotency_key='build:hero')
    assert len(calls) == 1


def test_store_failure_after_request_does_not_repeat_paid_work():
    calls, journal, store = [], DurableTestJournal(), MemoryArtifactStore()
    provider = build_image_provider(ENV, journal=journal, artifact_store=store, urlopen=transport(calls))
    with mock.patch.object(store, 'put_bytes', side_effect=RuntimeError('storage unavailable')):
        with pytest.raises(RuntimeError):
            provider.submit(REQ, idempotency_key='build:hero')
    with pytest.raises(AmbiguousSubmission):
        provider.submit(REQ, idempotency_key='build:hero')
    assert len(calls) == 1


def test_closed_switch_and_missing_storage_stop_before_http():
    send = mock.Mock(side_effect=AssertionError('network forbidden'))
    provider = build_image_provider({**ENV, 'OMNI_ZERO_COST_MODE': '1'}, journal=DurableTestJournal(),
                                    artifact_store=MemoryArtifactStore(), urlopen=send)
    with pytest.raises(ModelPolicyViolation):
        provider.submit(REQ, idempotency_key='b1')
    provider = build_image_provider(ENV, journal=DurableTestJournal(), urlopen=send)
    with pytest.raises(RuntimeError, match='durable storage'):
        provider.submit(REQ, idempotency_key='b1')
    send.assert_not_called()


def test_unpriced_or_unknown_model_is_not_configured():
    assert readiness({**ENV, 'OMNI_GOOGLE_IMAGE_MAXIMUM_USD': 'NaN'})['status'] == 'BLOCKED'
    assert readiness({**ENV, 'OMNI_GOOGLE_IMAGE_MODEL': 'invented'})['status'] == 'BLOCKED'
    assert build_image_provider({**ENV, 'OMNI_GOOGLE_IMAGE_MAXIMUM_USD': ''}, journal=DurableTestJournal()) is None


def test_real_capability_executor_verifies_and_stores_the_generated_artifact():
    calls, journal, store, repository = [], DurableTestJournal(), MemoryArtifactStore(), MemoryCapabilityRepository()
    plan = CapabilityPlan((REQ,), ('media.image.generate',))
    # Run the actual normal factory, quote resolver, provider router, capability
    # stage and artifact verifier. Only the upstream HTTP response is substituted.
    quotes = build_image_quote_resolver(ENV)(plan)
    assert REQ.id in quotes
    stage = build_image_capability_stage(env=ENV, repository=repository, artifact_store=store,
                                        journal=journal, worker_id='test-worker', urlopen=transport(calls))
    assert stage.executor is not None
    repository.create_plan(build_id='b1', plan=plan)
    result = stage.executor.execute_plan(build_id='b1', project_id='p1', plan=plan, assignments=quotes, now=100)
    assert result.status == 'VERIFIED'
    assert len(result.artifacts) == 1
    assert store.get_bytes(result.artifacts[0].artifact_key).startswith(b'\x89PNG')
    assert len(calls) == 1


@pytest.mark.parametrize('changed', [
    {'OMNI_GOOGLE_IMAGE_MAXIMUM_USD': '0.30'},
    {'OMNI_GOOGLE_IMAGE_PRICE_SOURCE': 'https://example.com/revised-price'},
    {'OMNI_GOOGLE_IMAGE_MODEL': 'gemini-3-pro-image'},
])
def test_executor_retry_after_lost_response_preserves_paid_attempt(changed):
    journal, store, repository = DurableTestJournal(), MemoryArtifactStore(), MemoryCapabilityRepository()
    plan = CapabilityPlan((REQ,), ('media.image.generate',))
    repository.create_plan(build_id='b1', plan=plan)
    post = mock.Mock(side_effect=TimeoutError('response lost after submit'))

    def execute(env, worker_id, now):
        stage = build_image_capability_stage(env=env, repository=repository, artifact_store=store,
                                            journal=journal, worker_id=worker_id, urlopen=post)
        return stage.executor.execute_plan(build_id='b1', project_id='p1', plan=plan,
                                           assignments=build_image_quote_resolver(env)(plan), now=now)

    with pytest.raises(TimeoutError):
        execute(ENV, 'first', 100)
    with pytest.raises(ValueError, match='execution idempotency key identity conflict'):
        execute({**ENV, **changed}, 'replacement', 10000)
    post.assert_called_once()
    original_quote = build_image_quote_resolver(ENV)(plan)[REQ.id].quote
    assert repository.requirements(build_id='b1')[0]['pricing_version'] == original_quote.pricing_version
    assert repository.usage_for_build(build_id='b1') == []
