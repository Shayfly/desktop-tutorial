from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class IntegrationDefinition:
    key: str
    category: str
    required_secrets: tuple[str,...]
    optional: tuple[str,...]=()

REGISTRY = {
    x.key: x for x in (
        IntegrationDefinition('stripe','payments',('STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET')),
        IntegrationDefinition('supabase','backend',('SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY'),('SUPABASE_ANON_KEY',)),
        IntegrationDefinition('firebase','backend',('FIREBASE_PROJECT_ID','FIREBASE_CREDENTIALS_JSON')),
        IntegrationDefinition('github','source-control',('GITHUB_TOKEN',)),
        IntegrationDefinition('resend','email',('RESEND_API_KEY',)),
        IntegrationDefinition('sendgrid','email',('SENDGRID_API_KEY',)),
        IntegrationDefinition('google-maps','maps',('GOOGLE_MAPS_API_KEY',)),
        IntegrationDefinition('mapbox','maps',('MAPBOX_TOKEN',)),
        IntegrationDefinition('s3','storage',('S3_ENDPOINT_URL','S3_BUCKET','S3_ACCESS_KEY_ID','S3_SECRET_ACCESS_KEY')),
        IntegrationDefinition('oidc','auth',('OIDC_ISSUER','OIDC_CLIENT_ID','OIDC_CLIENT_SECRET')),
        IntegrationDefinition('cloudflare-r2','storage',('S3_ENDPOINT_URL','S3_BUCKET','S3_ACCESS_KEY_ID','S3_SECRET_ACCESS_KEY')),
        IntegrationDefinition('runpod','gpu',('RUNPOD_API_KEY',)),
        IntegrationDefinition('replicate','media',('REPLICATE_API_TOKEN',)),
        IntegrationDefinition('local-openai-compatible-model','ai',('OMNI_LOCAL_MODEL_BASE_URL','OMNI_LOCAL_MODEL_NAME')),
        IntegrationDefinition('media-gateway','media',('OMNI_MEDIA_BASE_URL',)),
        IntegrationDefinition('apple-developer','mobile-signing',('APPLE_TEAM_ID','APPLE_SIGNING_IDENTITY')),
        IntegrationDefinition('google-play','mobile-signing',('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON',)),
    )
}

@dataclass(frozen=True)
class IntegrationBinding:
    provider: str
    secret_refs: tuple[str,...]

    @classmethod
    def bind(cls, provider: str, secret_refs: dict[str,str]) -> 'IntegrationBinding':
        definition = REGISTRY.get(provider)
        if definition is None: raise KeyError(provider)
        missing = [name for name in definition.required_secrets if not secret_refs.get(name,'').strip()]
        if missing: raise ValueError('missing secret references: '+','.join(missing))
        # Values are references/keys only; raw secret-looking values are rejected.
        refs=[]
        for name in definition.required_secrets:
            ref=secret_refs[name].strip()
            if not (ref.startswith('env:') or ref.startswith('vault:') or ref.startswith('secret:')):
                raise ValueError('integration secrets must be secret references, not raw values')
            refs.append(f'{name}={ref}')
        return cls(provider, tuple(refs))

def catalog() -> list[dict]:
    return [
        {'key': d.key,'category':d.category,'required_secrets':list(d.required_secrets),'optional':list(d.optional)}
        for d in sorted(REGISTRY.values(), key=lambda x:x.key)
    ]
