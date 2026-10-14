import unittest
from decimal import Decimal

from omni_prod.error_taxonomy import classify_error, ErrorClass
from omni_prod.retry import RetryPolicy, retry_delay
from omni_prod.build_budget import BuildBudget, BudgetState, assert_within_budget
from omni_prod.repair_loop import decide_after_failure
from omni_prod.canary import CanaryPolicy, CanaryObservation, evaluate_canary
from omni_prod.orchestrator import BuildOrchestrator, OrchestrationState

class ErrorTaxonomyTests(unittest.TestCase):
    def test_syntax_error_is_repairable(self):
        c=classify_error('SyntaxError: invalid syntax')
        self.assertEqual(c.category,ErrorClass.USER_CODE)
        self.assertTrue(c.repairable)

    def test_timeout_is_retryable(self):
        c=classify_error('provider timeout')
        self.assertTrue(c.retryable)

class RetryTests(unittest.TestCase):
    def test_exponential_backoff_capped(self):
        p=RetryPolicy(max_attempts=5,base_delay_seconds=2,max_delay_seconds=5)
        self.assertEqual(retry_delay(p,1),2)
        self.assertEqual(retry_delay(p,3),5)

class BudgetTests(unittest.TestCase):
    def test_over_budget_raises(self):
        b=BuildBudget(Decimal('1.00'),60,2)
        s=BudgetState(ai_cost=Decimal('1.01'))
        with self.assertRaises(RuntimeError): assert_within_budget(b,s)

class RepairTests(unittest.TestCase):
    def test_user_code_failure_requests_repair(self):
        b=BuildBudget(Decimal('10'),120,2)
        s=BudgetState()
        d=decide_after_failure(error_message='TypeError: bad value',budget=b,state=s)
        self.assertEqual(d.action,'repair')

class CanaryTests(unittest.TestCase):
    def test_bad_canary_rolls_back(self):
        p=CanaryPolicy(error_rate_threshold=.02,min_requests=100)
        o=CanaryObservation(requests=100,errors=5)
        self.assertEqual(evaluate_canary(p,o,5),'rollback')

    def test_good_canary_advances(self):
        p=CanaryPolicy(error_rate_threshold=.02,min_requests=100)
        o=CanaryObservation(requests=1000,errors=5)
        self.assertEqual(evaluate_canary(p,o,5),'advance')

class OrchestratorTests(unittest.TestCase):
    def test_retry_then_fail_at_retry_limit(self):
        o=BuildOrchestrator(build_budget=BuildBudget(Decimal('5'),120,2),retry_policy=RetryPolicy(max_attempts=2))
        s=OrchestrationState()
        self.assertEqual(o.failure_action(s,'timeout'), 'retry')
        self.assertEqual(o.failure_action(s,'timeout'), 'fail')

    def test_repair_increments_budget_state(self):
        o=BuildOrchestrator(build_budget=BuildBudget(Decimal('5'),120,2),retry_policy=RetryPolicy())
        s=OrchestrationState()
        self.assertEqual(o.failure_action(s,'SyntaxError'), 'repair')
        self.assertEqual(s.budget.repair_rounds,1)

if __name__=='__main__': unittest.main()
