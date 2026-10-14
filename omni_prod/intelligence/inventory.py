"""Canonical provider/model inventory (Wave A §3). The single typed source for
PROVIDER_MATRIX.json; the generated file is never edited by hand.

Each entry states facts about one model id and the evidence for its credential,
connection and verification states. Evidence is a real, openable record (a
GitHub Actions run id, a deployment id); the validator in `matrix.py` rejects
any state stronger than its evidence. Nothing here is a secret: only the NAMES
of environment variables appear.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import states as S


@dataclass(frozen=True)
class ProviderEvidence:
    ref: str            # openable record
    at: str             # UTC time of the observation
    commit: str         # deployed code that ran ('' when not applicable)
    observed: str       # exactly what it showed


# --- observations (names/status only) ---------------------------------------
DEPLOY_NOTICE = ProviderEvidence(
    'deploy-worker run 38083162363 (annotation "model catalog")', '2026-10-10T20:17Z', '67a0765',
    'all six catalog routes CONFIGURED on the worker; OPENAI_API_KEY and ANTHROPIC_API_KEY added from GitHub secrets')
PROBE = ProviderEvidence(
    'model-probe run 37814803770 (annotations)', '2026-10-08T17:12Z', 'ff6b4f6',
    'gemini-3.8-flash, gemini-3.5-flash-lite, gemini-3.1-flash-lite answered OK; gpt-6-luna and gpt-6.1-sol '
    'HTTP 429 "no credits remaining"; claude-sonnet-5-5 HTTP 400 "credit balance is too low"')
LEDGER = ProviderEvidence(
    'postdeploy-checks economics run 38083624196 (annotation "economics by model")', '2026-10-10T20:24Z', '67a0765',
    'attempt ledger: gemini-3.8-flash 36 ok / 88 calls; gemini-3.1-flash-lite 115 ok / 117; gemini-3.5-flash-lite '
    '2 ok / 2; gpt-6-luna 0 ok / 18; gpt-6.1-sol 0 ok / 10; claude-sonnet-5-5 0 ok / 10')
# The same annotation as structured data: successful calls per provider model
# id in the attempt ledger. Execution evidence counts only where this is > 0.
LEDGER_OK_CALLS = {'gemini-3.8-flash': 36, 'gemini-3.1-flash-lite': 115, 'gemini-3.5-flash-lite': 2,
                   'gpt-6-luna': 0, 'gpt-6.1-sol': 0, 'claude-sonnet-5-5': 0}
GOLDEN = ProviderEvidence(
    'postdeploy-checks run 37961193099', '2026-10-09T16:43Z', '039574f',
    'paid golden build READY: discovery -> approval -> model-built product -> preview')
REPLICATE_ACCOUNT = ProviderEvidence(
    'Vercel Preview deployment p40n0qijl, GET /api/v28/providers/replicate/check', '2026-10-06', '',
    'authenticated account check connection_verified=true; no prediction was ever submitted')
VERCEL_ENV_NAMES = ProviderEvidence(
    'Vercel project 148aiv28 environment variable names (read 2026-10-11, values not read)', '2026-10-11', '',
    'REPLICATE_API_TOKEN present (Preview, sensitive); no LLM provider key on Vercel')

LANG_HE_EN = ('he', 'en')


@dataclass(frozen=True)
class ModelEntry:
    provider_key: str
    model_key: str                  # 148AI route name (catalog `name`) or candidate key
    provider_model_id: str          # exactly what the API takes
    id_source: str                  # where the id was verified
    model_family: str
    provider_type: str              # llm | image | video | audio | music | embedding | 3d
    capability_types: tuple[str, ...]
    intended_task_types: tuple[str, ...]
    execution_adapter: str
    adapter_implementation_path: str
    supported_modalities: tuple[str, ...]
    supported_languages: tuple[str, ...]
    context_window: int | None
    maximum_output_tokens: int | None
    supports_tool_calls: bool
    supports_structured_output: bool
    supports_streaming: bool
    supports_reasoning: bool
    supports_vision: bool
    supports_function_calling: bool
    credential_reference_names: tuple[str, ...]
    credential_scope: str           # where the key lives: worker | vercel-preview | none
    credential_state: str
    connection_state: str
    verification_state: str
    evidence: tuple[ProviderEvidence, ...]
    commercial_usage_constraints: str
    security_constraints: str
    known_limitations: str
    fallback_eligibility: str       # primary | escalation | review-only | none
    in_catalog: bool = False        # present in infra/worker-host/model-catalog.json
    health_note: str = ''           # last observed provider answer that blocks it

    @property
    def last_verified_at(self) -> str | None:
        return max((e.at for e in self.evidence), default=None)


_GEM_COMMERCIAL = 'Gemini API paid tier: outputs usable commercially; paid-tier prompts not used to improve products'
_NO_SECRETS = 'secret references only; customer screenshots never sent to third-party AI; prompts carry no secrets'


def _llm(provider, key, model_id, family, *, quality_tasks, key_env, cred, conn, ver, ev, limits, fallback, ctx,
         max_out, reasoning=True, vision=True, in_catalog=True, health_note='', commercial=_GEM_COMMERCIAL,
         id_source='', adapter='routed_gateway (OpenAI-compatible chat)', adapter_path='omni_prod/routed_gateway.py, omni_prod/model_gateway.py',
         scope='worker'):
    return ModelEntry(
        provider_key=provider, model_key=key, provider_model_id=model_id,
        id_source=id_source or ('model-probe 37814803770 served_model' if conn == S.CONNECTION_TESTED else 'provider docs'),
        model_family=family, provider_type='llm', capability_types=('text.generate', 'json.structured'),
        intended_task_types=quality_tasks, execution_adapter=adapter, adapter_implementation_path=adapter_path,
        supported_modalities=('text', 'image') if vision else ('text',), supported_languages=LANG_HE_EN,
        context_window=ctx, maximum_output_tokens=max_out, supports_tool_calls=False,
        supports_structured_output=True, supports_streaming=False, supports_reasoning=reasoning,
        supports_vision=vision, supports_function_calling=False, credential_reference_names=(key_env,) if key_env else (),
        credential_scope=scope, credential_state=cred, connection_state=conn, verification_state=ver, evidence=ev,
        commercial_usage_constraints=commercial, security_constraints=_NO_SECRETS, known_limitations=limits,
        fallback_eligibility=fallback, in_catalog=in_catalog, health_note=health_note)


# Tool/function calling and streaming are capabilities of the provider APIs,
# but the 148AI adapter does not use them: reported as what 148AI can use.
INVENTORY: tuple[ModelEntry, ...] = (
    # ------------------------------------------------------------ Gemini (worker)
    _llm('gemini', 'gemini-3-8-flash', 'gemini-3.8-flash', 'Gemini Flash',
         quality_tasks=('architecture', 'codegen', 'repair', 'modification', 'review'), key_env='GEMINI_API_KEY',
         cred=S.CREDENTIAL_PRESENT, conn=S.CONNECTION_TESTED, ver=S.REAL_EXECUTION_VERIFIED,
         ev=(DEPLOY_NOTICE, PROBE, LEDGER, GOLDEN), ctx=1_000_000, max_out=65_536,
         limits='41% call success in the ledger (timeouts, truncated JSON before reasoning_effort=low); price doubles 2027-01-01',
         fallback='primary'),
    _llm('gemini', 'gemini-3-1-flash-lite', 'gemini-3.1-flash-lite', 'Gemini Flash-Lite',
         quality_tasks=('general', 'classification', 'conversation', 'intake_extraction'), key_env='GEMINI_API_KEY',
         cred=S.CREDENTIAL_PRESENT, conn=S.CONNECTION_TESTED, ver=S.REAL_EXECUTION_VERIFIED,
         ev=(DEPLOY_NOTICE, PROBE, LEDGER), ctx=1_000_000, max_out=8192,
         limits='retires 2027-05-07 (successor gemini-3.5-flash-lite); below the 85 floor for code',
         fallback='escalation'),
    _llm('gemini', 'gemini-3-5-flash-lite', 'gemini-3.5-flash-lite', 'Gemini Flash-Lite',
         quality_tasks=('general', 'classification', 'conversation', 'intake_extraction'), key_env='GEMINI_API_KEY',
         cred=S.CREDENTIAL_PRESENT, conn=S.CONNECTION_TESTED, ver=S.REAL_EXECUTION_VERIFIED,
         ev=(DEPLOY_NOTICE, PROBE, LEDGER), ctx=1_000_000, max_out=8192,
         limits='only 2 real calls in the ledger: too few to measure quality; Hebrew intake quality unmeasured',
         fallback='escalation'),
    # ------------------------------------------------------------ OpenAI (worker)
    _llm('openai', 'openai-gpt-6-luna', 'gpt-6-luna', 'GPT Luna',
         quality_tasks=('general', 'conversation', 'intake_extraction'), key_env='OPENAI_API_KEY',
         cred=S.CREDENTIAL_PRESENT, conn=S.CONNECTION_TESTED, ver=S.UNVERIFIED, ev=(DEPLOY_NOTICE, PROBE, LEDGER),
         ctx=None, max_out=16384, limits='no successful call: account has no credit',
         fallback='escalation', health_note='HTTP 429 no credits remaining (2026-10-08); 0 ok / 18 in the ledger',
         commercial='OpenAI API terms: customer owns outputs; API data not used for training by default',
         adapter='routed_gateway (OpenAI reasoning dialect)'),
    _llm('openai', 'openai-gpt-6-1-sol', 'gpt-6.1-sol', 'GPT Sol',
         quality_tasks=('architecture', 'codegen', 'repair', 'review', 'security_review'), key_env='OPENAI_API_KEY',
         cred=S.CREDENTIAL_PRESENT, conn=S.CONNECTION_TESTED, ver=S.UNVERIFIED, ev=(DEPLOY_NOTICE, PROBE, LEDGER),
         ctx=None, max_out=16384, limits='no successful call: account has no credit', fallback='review-only',
         health_note='HTTP 429 no credits remaining (2026-10-08); 0 ok / 10 in the ledger',
         commercial='OpenAI API terms: customer owns outputs; API data not used for training by default',
         adapter='routed_gateway (OpenAI reasoning dialect)'),
    # --------------------------------------------------------- Anthropic (worker)
    _llm('anthropic', 'anthropic-claude-sonnet-5-5', 'claude-sonnet-5-5', 'Claude Sonnet',
         quality_tasks=('architecture', 'codegen', 'repair', 'review', 'security_review'), key_env='ANTHROPIC_API_KEY',
         cred=S.CREDENTIAL_PRESENT, conn=S.CONNECTION_TESTED, ver=S.UNVERIFIED, ev=(DEPLOY_NOTICE, PROBE, LEDGER),
         ctx=None, max_out=16384, limits='no successful call: prepaid balance too low', fallback='review-only',
         health_note='HTTP 400 credit balance too low (2026-10-08); 0 ok / 10 in the ledger',
         commercial='Anthropic commercial terms: customer owns outputs; no training on API data by default',
         adapter='routed_gateway (Anthropic Messages API)', id_source='Anthropic published model string'),
    # ------------------------------------------------- candidates (not in catalog)
    _llm('gemini', 'gemini-2-5-flash-lite', 'gemini-2.5-flash-lite', 'Gemini Flash-Lite',
         quality_tasks=('conversation', 'intake_extraction'), key_env='GEMINI_API_KEY', cred=S.CREDENTIAL_PRESENT,
         conn=S.NOT_CONNECTED, ver=S.UNVERIFIED, ev=(DEPLOY_NOTICE,), ctx=1_000_000, max_out=8192, in_catalog=False,
         limits='Google limits 2.5 access to projects that used it before: availability for this project unknown until probed',
         fallback='none', id_source='Gemini deprecations page (2026-10-11)'),
    _llm('anthropic', 'anthropic-claude-haiku-5-5', 'claude-haiku-5-5', 'Claude Haiku',
         quality_tasks=('conversation', 'intake_extraction'), key_env='ANTHROPIC_API_KEY', cred=S.CREDENTIAL_PRESENT,
         conn=S.NOT_CONNECTED, ver=S.UNVERIFIED, ev=(DEPLOY_NOTICE,), ctx=None, max_out=None, in_catalog=False,
         limits='not in the catalog; same account as Sonnet (balance too low)', fallback='none',
         commercial='Anthropic commercial terms', adapter='routed_gateway (Anthropic Messages API)',
         id_source='Anthropic published model string'),
    _llm('gemini', 'gemini-3-1-pro-preview', 'gemini-3.1-pro-preview', 'Gemini Pro',
         quality_tasks=('architecture', 'security_review'), key_env='GEMINI_API_KEY', cred=S.CREDENTIAL_PRESENT,
         conn=S.NOT_CONNECTED, ver=S.UNVERIFIED, ev=(DEPLOY_NOTICE,), ctx=None, max_out=None, in_catalog=False,
         limits='preview model; no free tier', fallback='none', id_source='Gemini pricing page (2026-10-11)'),
    # ------------------------------------------------------------------- media
    ModelEntry('replicate', 'replicate-flux-schnell', 'black-forest-labs/flux-schnell', 'Replicate official model',
               'FLUX', 'image', ('media.image.generate',), ('image_asset',), 'image_provider (Replicate predictions)',
               'omni_prod/providers/image_provider.py, omni_prod/providers/replicate_connection.py',
               ('text', 'image'), LANG_HE_EN, None, None, False, False, False, False, False, False,
               ('REPLICATE_API_TOKEN',), 'vercel-preview', S.CREDENTIAL_PRESENT, S.CONNECTION_TESTED, S.UNVERIFIED,
               (VERCEL_ENV_NAMES, REPLICATE_ACCOUNT), 'per-model licence: FLUX Schnell is Apache-2.0 (check per model)',
               _NO_SECRETS, 'no image ever generated; the worker has no OMNI_IMAGE_PROVIDER_* configuration',
               'none'),
    ModelEntry('gemini', 'gemini-3-1-flash-lite-image', 'gemini-3.1-flash-lite-image', 'Gemini pricing page (2026-10-11)',
               'Nano Banana', 'image', ('media.image.generate',), ('image_asset',), 'none (adapter not written)', '',
               ('text', 'image'), LANG_HE_EN, None, None, False, False, False, False, True, False,
               ('GEMINI_API_KEY',), 'worker', S.CREDENTIAL_PRESENT, S.NOT_CONNECTED, S.UNVERIFIED, (DEPLOY_NOTICE,),
               _GEM_COMMERCIAL, _NO_SECRETS, 'no adapter; no free tier', 'none'),
    ModelEntry('gemini', 'gemini-omni-1-1-flash', 'gemini-omni-1.1-flash', 'Gemini deprecations page (2026-10-11)',
               'Gemini Omni', 'video', ('media.video.generate',), ('video_asset',), 'none (adapter not written)', '',
               ('text', 'image', 'video'), LANG_HE_EN, None, None, False, False, False, False, True, False,
               ('GEMINI_API_KEY',), 'worker', S.CREDENTIAL_PRESENT, S.NOT_CONNECTED, S.UNVERIFIED, (DEPLOY_NOTICE,),
               _GEM_COMMERCIAL, _NO_SECRETS, 'no adapter; long-running jobs need polling + artifact storage', 'none'),
    ModelEntry('gemini', 'gemini-3-8-flash-lite-tts', 'gemini-3.8-flash-lite-tts', 'Gemini deprecations page (2026-10-11)',
               'Gemini TTS', 'audio', ('media.speech.generate',), ('voice_asset',), 'none (adapter not written)', '',
               ('text', 'audio'), LANG_HE_EN, None, None, False, False, False, False, False, False,
               ('GEMINI_API_KEY',), 'worker', S.CREDENTIAL_PRESENT, S.NOT_CONNECTED, S.UNVERIFIED, (DEPLOY_NOTICE,),
               _GEM_COMMERCIAL, _NO_SECRETS, 'no adapter; Hebrew voice quality unmeasured', 'none'),
    ModelEntry('gemini', 'lyria-3-5', 'lyria-3.5', 'Gemini pricing page (2026-10-11)', 'Lyria', 'music',
               ('media.music.generate',), ('music_asset',), 'none (adapter not written)', '', ('text', 'audio'),
               LANG_HE_EN, None, None, False, False, False, False, False, False, ('GEMINI_API_KEY',), 'worker',
               S.CREDENTIAL_PRESENT, S.NOT_CONNECTED, S.UNVERIFIED, (DEPLOY_NOTICE,),
               'commercial music licence terms NOT yet reviewed: blocked until founder review', _NO_SECRETS,
               'no adapter; licence unreviewed', 'none'),
)

# Code paths that can route model calls but are not part of the governed
# catalog. Reported in the matrix so they are visible; none may take customer work.
LEGACY_ROUTES = (
    {'route': 'OMNI_LOCAL_MODEL_URL (local primary)', 'path': 'omni_prod/model_runtime_config.py',
     'state': 'NOT_CONNECTED', 'note': 'DEV_ONLY; docker-compose.production.yml (legacy) still requires it; unset on the worker'},
    {'route': 'OMNI_EXTERNAL_MODELS_JSON (legacy fallback list)', 'path': 'omni_prod/model_runtime_config.py',
     'state': 'NOT_CONNECTED', 'note': 'carries raw api_key inside JSON; superseded by the catalog; deprecated'},
    {'route': 'providers/llm_provider.LLMCapabilityProvider', 'path': 'omni_prod/providers/llm_provider.py',
     'state': 'NOT_CONNECTED', 'note': 'no production caller'},
    {'route': 'providers/http_media_provider', 'path': 'omni_prod/providers/http_media_provider.py',
     'state': 'NOT_CONNECTED', 'note': 'no production caller'},
    {'route': 'media_gateway.HTTPMediaGateway (OMNI_MEDIA_BASE_URL)', 'path': 'omni_prod/media_gateway.py',
     'state': 'NOT_CONNECTED', 'note': 'used only by media_branding; no endpoint configured'},
)

# Capability needs with no provider at all.
GAPS = (
    {'capability': '3d.generate', 'state': 'NOT_CONNECTED',
     'note': 'no 3D model in the Google/OpenAI catalogs read 2026-10-11; Replicate models vary by licence: founder decision'},
    {'capability': 'media.sfx.generate', 'state': 'NOT_CONNECTED', 'note': 'no provider selected'},
    {'capability': 'review.independent_provider', 'state': 'BLOCKED',
     'note': 'needs a second provider with credit (OpenAI or Anthropic); same-model review is not independent'},
)
