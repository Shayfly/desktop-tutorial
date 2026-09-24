from __future__ import annotations

from decimal import Decimal
from .v27_platform import V27UniversalPlatform
from .pricing import SubscriptionService, PlanCode, CostClass, catalog_payload
from .branding import BrandingEngine
from .repository_patch import FilePatch, apply_patch


class V28Platform(V27UniversalPlatform):
    """148AI launch-candidate control plane.

    Adds plan economics, hard provider-spend guardrails and brand/provenance
    policy without weakening the V27 rights or tenant-isolation contracts.
    """
    def __init__(self, *, token_secret: str, generated_app_token_secret: str | None = None, account_service=None, subscription_service=None):
        super().__init__(token_secret=token_secret, generated_app_token_secret=generated_app_token_secret)
        if account_service is not None:
            self.accounts = account_service
        self.subscriptions = subscription_service or SubscriptionService()
        self.branding = BrandingEngine()
        self._project_brand_visible: dict[str, bool | None] = {}
        self._project_white_label: dict[str, str | None] = {}

    def register(self, *, email: str, password: str) -> dict:
        payload = super().register(email=email, password=password)
        self.subscriptions.assign_plan(payload['user']['id'], PlanCode.FREE)
        payload['subscription'] = self.subscriptions.snapshot(payload['user']['id'])
        return payload

    def subscription(self, *, token: str) -> dict:
        account = self.account(token)
        return self.subscriptions.snapshot(account.id)

    def assign_plan_admin(self, *, user_id: str, plan: str) -> dict:
        self.subscriptions.assign_plan(user_id, plan)
        return self.subscriptions.snapshot(user_id)

    def pricing(self) -> dict:
        return catalog_payload()

    def set_project_branding(self, *, token: str, project_id: str, visible: bool | None, white_label_name: str | None = None) -> dict:
        account, key = self._key(token=token, project_id=project_id)
        plan = self.subscriptions.plan_for(account.id)
        resolved = self.branding.resolve_visible(plan=plan.code, requested_visible=visible)
        if white_label_name and not plan.white_label:
            raise PermissionError('white-label branding requires Business/Enterprise')
        self._project_brand_visible[key] = resolved
        self._project_white_label[key] = (white_label_name or '').strip()[:80] or None
        version_id = None
        current = self.engine.workspace.current(key)
        if current is not None:
            repo = self.branding.decorate_repository(
                current.repository(), plan=plan.code, project_id=project_id, version_hint=current.id,
                requested_visible=resolved, white_label_name=self._project_white_label[key],
            )
            version = self.engine.workspace.commit(project_id=key, repository=repo, message='V28 branding policy update')
            version_id = version.id
        return {
            'project_id': project_id,
            'plan': plan.code.value,
            'visible_branding': resolved,
            'white_label_name': self._project_white_label[key],
            'policy': self.branding.policy_for(plan.code).to_dict(),
            'version_id': version_id,
        }

    def build(self, *, token: str, project_id: str, prompt: str, target_markets: tuple[str, ...] = ('US','EU','IL')) -> dict:
        account, key = self._key(token=token, project_id=project_id)
        plan = self.subscriptions.plan_for(account.id)
        # Deterministic/local-template build path has no paid-provider spend and is
        # therefore available even to Free. Live AI/media endpoints are separately metered.
        decision = self.subscriptions.authorize(user_id=account.id, cost_class=CostClass.ZERO, credits=3, category='new_build')
        if not decision.allowed:
            raise PermissionError(decision.reason)
        result = super().build(token=token, project_id=project_id, prompt=prompt, target_markets=target_markets)
        current = self.engine.workspace.current(key)
        if current is None:
            raise RuntimeError('build did not create a version')
        repo = self.branding.decorate_repository(
            current.repository(), plan=plan.code, project_id=project_id, version_hint=current.id,
            requested_visible=self._project_brand_visible.get(key),
            white_label_name=self._project_white_label.get(key),
        )
        final = self.engine.workspace.commit(project_id=key, repository=repo, message='V28 148AI branding + provenance')
        usage = self.subscriptions.consume(user_id=account.id, decision=decision)
        result.update({
            'version_id': final.id, 'checksum': final.checksum, 'file_count': len(repo),
            'brand': {'name':'148AI','domain':'148ailabs.com','tagline':'Build Anything.','policy':self.branding.policy_for(plan.code).to_dict()},
            'subscription': usage,
        })
        return result

    def authorize_live_usage(self, *, token: str, project_id: str, cost_class: str, credits: int, category: str = 'new_build', estimated_cost_usd: str | None = None):
        account, _ = self._key(token=token, project_id=project_id)
        estimate = Decimal(estimated_cost_usd) if estimated_cost_usd is not None else None
        return self.subscriptions.authorize(user_id=account.id, cost_class=cost_class, credits=credits, category=category, estimated_provider_cost_usd=estimate)

    def consume_live_usage(self, *, token: str, project_id: str, decision, actual_cost_usd: str | None = None) -> dict:
        account, _ = self._key(token=token, project_id=project_id)
        actual = Decimal(actual_cost_usd) if actual_cost_usd is not None else None
        return self.subscriptions.consume(user_id=account.id, decision=decision, actual_provider_cost_usd=actual)
