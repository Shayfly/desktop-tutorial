"""Server-only Replicate configuration and non-billable authentication check."""
import json
from urllib import request, error

DEFAULT_MODEL = 'black-forest-labs/flux-schnell'


def image_environment(env):
    """Use the saved token without overriding an explicitly configured provider.

    The default model's published price is $3 per thousand output images:
    https://replicate.com/pricing (checked 2026-10-06).
    Custom models require their own price and licence configuration.
    """
    values = dict(env)
    if not str(values.get('REPLICATE_API_TOKEN', '')).strip():
        return values
    base = str(values.get('OMNI_IMAGE_PROVIDER_BASE_URL', '')).strip().rstrip('/')
    if base and base != 'https://api.replicate.com/v1':
        return values
    model = str(values.get('OMNI_IMAGE_PROVIDER_MODEL', '')).strip() or DEFAULT_MODEL
    defaults = {
        'OMNI_IMAGE_PROVIDER_NAME': 'replicate',
        'OMNI_IMAGE_PROVIDER_BASE_URL': 'https://api.replicate.com/v1',
        'OMNI_IMAGE_PROVIDER_API_KEY_REF': 'env:REPLICATE_API_TOKEN',
        'OMNI_IMAGE_PROVIDER_MODEL': model,
        'OMNI_IMAGE_PROVIDER_SUBMIT_PATH': '/models/' + model + '/predictions',
        'OMNI_IMAGE_PROVIDER_OUTPUT_HOSTS': 'replicate.delivery',
    }
    if model == DEFAULT_MODEL and not str(values.get('OMNI_IMAGE_PROVIDER_VERSION', '')).strip():
        defaults.update({
            'OMNI_IMAGE_PROVIDER_ESTIMATED_USD_PER_IMAGE': '0.003',
            'OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE': '0.003',
            'OMNI_IMAGE_PROVIDER_PRICE_SOURCE': 'https://replicate.com/pricing#2026-10-06',
            'OMNI_IMAGE_PROVIDER_COMMERCIAL_USE': 'true',
            'OMNI_IMAGE_PROVIDER_LICENSE': 'Apache-2.0 (FLUX.1 schnell)',
        })
    if str(values.get('OMNI_IMAGE_PROVIDER_VERSION', '')).strip():
        defaults['OMNI_IMAGE_PROVIDER_SUBMIT_PATH'] = '/predictions'
    for name, value in defaults.items():
        if not str(values.get(name, '')).strip():
            values[name] = value
    return values


def check_replicate_connection(env, *, urlopen=None):
    """GET /account verifies the token without creating predictions or costs.

    Discard account data and upstream error text; never expose credentials.
    No persistent LIVE or generation claim follows from this check.
    """
    result = {'provider': 'replicate', 'connection_verified': False,
              'generation_verified': False, 'billable_generation_started': False}
    token = str(env.get('REPLICATE_API_TOKEN', '')).strip()
    if not token:
        return {**result, 'status': 'NOT_CONFIGURED', 'reason': 'REPLICATE_API_TOKEN is missing'}
    req = request.Request('https://api.replicate.com/v1/account',
                          headers={'Authorization': 'Bearer ' + token}, method='GET')
    try:
        with (urlopen or request.urlopen)(req, timeout=10) as response:
            body = json.loads(response.read(65537))
        if not isinstance(body, dict) or not body.get('username'):
            return {**result, 'status': 'BLOCKED', 'reason': 'Invalid account response'}
    except error.HTTPError as exc:
        return {**result, 'status': 'BLOCKED', 'http_status': exc.code,
                'reason': 'Replicate rejected the connection check'}
    except Exception:
        return {**result, 'status': 'BLOCKED', 'reason': 'Replicate connection check failed'}
    return {**result, 'status': 'PARTIAL', 'connection_verified': True,
            'reason': 'Token accepted; image generation has not been live verified'}
