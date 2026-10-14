from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from omni_prod import investor_app, worker_tasks
from omni_prod.pricing import SubscriptionService, PlanCode, PLAN_CATALOG, CostClass
from omni_prod.stripe_billing import StripeSubscriptionWebhookProcessor

def event(eid, kind, created=100, **fields):
 return {'id':eid,'type':kind,'created':created,'data':{'object':{'id':'cs_audit' if kind.startswith('checkout') else 'sub_audit','subscription':'sub_audit','metadata':{'user_id':'audit-user','plan_code':'basic'},**fields}}}

def test_unpaid_checkout_does_not_grant_entitlements():
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('unpaid','checkout.session.completed',payment_status='unpaid',mode='subscription'))
 assert service.plan_for('audit-user').code == PlanCode.FREE

def test_subscription_update_does_not_restore_spent_credits():
 service=SubscriptionService();processor=StripeSubscriptionWebhookProcessor(service)
 processor.process(event('created','checkout.session.completed',payment_status='paid',mode='subscription'))
 service.consume(user_id='audit-user',decision=service.authorize(user_id='audit-user',cost_class=CostClass.STANDARD,credits=75))
 processor.process(event('updated','customer.subscription.updated',status='active'))
 assert service.snapshot('audit-user')['credits_used']==75

def test_lost_worker_unknown_call_keeps_reservation():
 service=MagicMock()
 gateway=SimpleNamespace(prior_metered={'calls':1,'metered_usd':Decimal('0'),'unknown_calls':1})
 with patch.object(worker_tasks,'spend_snapshot',return_value=(Decimal('0'),0)):
  action,_,actual=worker_tasks.resolve_m5_billing(service,build_id='audit-b',ready=False,gateway=gateway,capability_evidence=None,economics_quote={})
 assert action=='settled'
 service.release.assert_not_called()
 assert actual is None

def test_default_margin_target_is_sixty_percent():
 env={'OMNI_ZERO_COST_MODE':'0','OMNI_ALLOW_EXTERNAL_FALLBACK':'1','OMNI_EXTERNAL_BUDGET_USD':'0.40','OMNI_EXTERNAL_CALLS_PER_BUILD':'3'}
 with patch.dict('os.environ',env,clear=False):
  with pytest.raises(PermissionError):
   investor_app._m5_build_economics_quote(PLAN_CATALOG[PlanCode.BASIC],credits=60)

def test_restarting_processor_cannot_replay_a_cancelled_checkout():
 service=SubscriptionService()
 paid=event('paid','checkout.session.completed',payment_status='paid',mode='subscription')
 StripeSubscriptionWebhookProcessor(service).process(paid)
 StripeSubscriptionWebhookProcessor(service).process(event('cancelled','customer.subscription.deleted',created=200))
 StripeSubscriptionWebhookProcessor(service).process(paid)
 assert service.plan_for('audit-user').code == PlanCode.FREE

def test_old_distinct_paid_event_cannot_undo_a_later_cancellation():
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('cancelled','customer.subscription.deleted',created=200))
 out=StripeSubscriptionWebhookProcessor(service).process(event('paid','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
 assert not out['processed']
 assert service.plan_for('audit-user').code == PlanCode.FREE

def test_equal_timestamp_revocation_wins_independent_of_delivery_order():
 for reverse in (False,True):
  service=SubscriptionService()
  events=[event('paid','checkout.session.completed',payment_status='paid',mode='subscription'),event('cancelled','customer.subscription.deleted')]
  for e in reversed(events) if reverse else events:
   StripeSubscriptionWebhookProcessor(service).process(e)
  assert service.plan_for('audit-user').code == PlanCode.FREE

def test_conflicting_event_id_is_rejected_after_processor_restart():
 from omni_prod.stripe_billing import StripeBillingError
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('paid','checkout.session.completed',payment_status='paid',mode='subscription'))
 with pytest.raises(StripeBillingError):
  StripeSubscriptionWebhookProcessor(service).process(event('paid','customer.subscription.deleted',created=200))

@pytest.mark.parametrize('status',['incomplete','past_due','trialing','unpaid'])
def test_lifecycle_events_without_payment_cannot_grant_a_paid_plan(status):
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('created','customer.subscription.created',status=status))
 assert service.plan_for('audit-user').code == PlanCode.FREE

def test_margin_configuration_cannot_lower_sixty_percent_floor():
 env={'OMNI_ZERO_COST_MODE':'0','OMNI_ALLOW_EXTERNAL_FALLBACK':'1','OMNI_EXTERNAL_BUDGET_USD':'0.40','OMNI_EXTERNAL_CALLS_PER_BUILD':'3','OMNI_MIN_BUILD_VARIABLE_MARGIN':'0.20'}
 with patch.dict('os.environ',env,clear=False):
  with pytest.raises(PermissionError):
   investor_app._m5_build_economics_quote(PLAN_CATALOG[PlanCode.BASIC],credits=60)

def test_cancelling_old_subscription_cannot_revoke_new_paid_subscription():
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('paid1','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
 StripeSubscriptionWebhookProcessor(service).process(event('paid2','checkout.session.completed',created=200,payment_status='paid',mode='subscription',subscription='sub_new'))
 out=StripeSubscriptionWebhookProcessor(service).process(event('old-cancel','customer.subscription.deleted',created=300))
 assert not out['processed']
 assert service.plan_for('audit-user').code == PlanCode.BASIC

@pytest.mark.parametrize('value',['NaN','Infinity','-0.1','1'])
def test_invalid_margin_policy_is_refused(value):
 with patch.dict('os.environ',{'OMNI_MIN_BUILD_VARIABLE_MARGIN':value},clear=False):
  with pytest.raises(PermissionError):
   investor_app._m5_build_economics_quote(PLAN_CATALOG[PlanCode.BASIC],credits=60)

def test_metadata_update_does_not_supersede_a_delayed_paid_upgrade():
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('basic-paid','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
 StripeSubscriptionWebhookProcessor(service).process(event('metadata','customer.subscription.updated',created=300,status='active'))
 paid_upgrade=event('pro-paid','checkout.session.completed',created=200,payment_status='paid',mode='subscription',metadata={'user_id':'audit-user','plan_code':'pro'})
 StripeSubscriptionWebhookProcessor(service).process(paid_upgrade)
 assert service.plan_for('audit-user').code == PlanCode.PRO

def test_early_delivered_new_subscription_cancellation_blocks_its_late_payment():
 service=SubscriptionService()
 StripeSubscriptionWebhookProcessor(service).process(event('basic-paid','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
 StripeSubscriptionWebhookProcessor(service).process(event('new-cancel','customer.subscription.deleted',created=300,id='sub_new'))
 out=StripeSubscriptionWebhookProcessor(service).process(event('new-paid','checkout.session.completed',created=200,payment_status='paid',mode='subscription',subscription='sub_new',metadata={'user_id':'audit-user','plan_code':'pro'}))
 assert not out['processed']
 assert service.plan_for('audit-user').code == PlanCode.BASIC
