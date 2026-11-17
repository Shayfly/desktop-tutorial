"""A chain walk reaches the deepest stage however many gates sit on top of it (production 2026-11-17,
bld_a875456f, "148 דלתות": every check passed and the release policy still failed the build -- "consistency gate did
not run (disabled); preview_starts NOT_RUN; behavioural_acceptance NOT_RUN". The walk stopped after 20 wrappers and
answered "not found"; the worker's chain had grown past 20).

The chain here is the worker's own: the real stage executors, with the real gates installed on top by the real
install functions."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from omni_prod import behavior_acceptance as B
from omni_prod import worker_tasks as W
from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
from omni_prod.browser_probe import BrowserFlowExecutor
from omni_prod.consistency_gate import ConsistencyGateExecutor
from omni_prod.dependency_policy import DependencyGateExecutor
from omni_prod.preview_smoke import PreviewReadyExecutor
from omni_prod.quality_gate import QualityAwareExecutor
from omni_prod.verification_group import VerificationGroup
from omni_prod.visual_qa import VisualQAExecutor


class Sandbox:
    def execute(self, *, repository, spec):
        raise AssertionError('not reached')


class Wrapper:
    def __init__(self, inner):
        self._inner = inner


def worker_chain():
    """investor_app's stages (bottom to top), then what the worker installs on every build."""
    threshold = DependencyGateExecutor(ConsistencyGateExecutor(Sandbox()))
    preview = PreviewReadyExecutor(threshold)
    behaviour = BehaviorAcceptanceExecutor(preview)
    browser = BrowserFlowExecutor(behaviour)
    visual = VisualQAExecutor(browser)
    engine = SimpleNamespace(executor=QualityAwareExecutor(
        VerificationGroup(threshold, (preview, behaviour, browser, visual)), minimum_score=80))
    for _ in range(4):                       # the worker's own wrappers: control, recorder, plan admission, logo
        engine.executor = Wrapper(engine.executor)
    env = {k: v for k, v in os.environ.items() if not k.startswith('OMNI_GATE_')}
    with mock.patch.dict(os.environ, env, clear=True):
        from omni_prod.skill_units.gate import install_all
        install_all(engine)
        from omni_prod.runtime_load import install as install_runtime_load
        install_runtime_load(engine)
        from omni_prod.a4 import install as install_asset_plan
        install_asset_plan(engine, prompt='אתר')
        from omni_prod.asset_markers import install as install_asset_marker_gate
        install_asset_marker_gate(engine)
        from omni_prod.g_apple import install as install_apple_gate
        install_apple_gate(engine, prompt='אתר')
    return engine


def depth(executor):
    n = 0
    while executor is not None:
        n, executor = n + 1, getattr(executor, '__dict__', {}).get('_inner')
    return n


class TheDeepestStageIsFound(unittest.TestCase):
    def test_the_workers_chain_is_longer_than_the_old_bound_and_every_evidence_is_read(self):
        engine = worker_chain()
        self.assertGreater(depth(engine.executor), 20)             # the length the old walk could not cross
        self.assertLess(depth(engine.executor), B.MAX_CHAIN)
        for cls in (ConsistencyGateExecutor, PreviewReadyExecutor, BehaviorAcceptanceExecutor):
            self.assertIsInstance(find_in_chain(engine.executor, cls), cls, cls.__name__)
        self.assertIsNotNone(W.consistency_evidence(engine))       # what the release policy reads
        self.assertIsNotNone(W.behavior_evidence(engine))

    def test_a_stage_that_is_not_in_the_chain_is_none(self):
        self.assertIsNone(find_in_chain(Wrapper(Wrapper(Sandbox())), ConsistencyGateExecutor))
        self.assertIsNone(find_in_chain(None, ConsistencyGateExecutor))

    def test_a_chain_past_the_bound_is_an_error_never_not_found(self):
        ex = ConsistencyGateExecutor(Sandbox())
        for _ in range(B.MAX_CHAIN):
            ex = Wrapper(ex)
        with self.assertRaises(B.ChainTooLong) as caught:
            find_in_chain(ex, ConsistencyGateExecutor)
        self.assertIn('ConsistencyGateExecutor', str(caught.exception))
        loop = Wrapper(None)
        loop._inner = loop                                          # a cycle is the same error
        with self.assertRaises(B.ChainTooLong):
            find_in_chain(loop, ConsistencyGateExecutor)

    def test_one_bound_for_every_walk(self):
        from omni_prod.skill_units import gate
        self.assertIs(gate.MAX_CHAIN, B.MAX_CHAIN)
        self.assertGreaterEqual(B.MAX_CHAIN, 64)

    def test_the_gates_report_is_read_through_the_whole_chain(self):
        engine = worker_chain()
        from omni_prod.skill_units.gate import SkillGateExecutor, WORKER_GATES
        found = set()
        ex = engine.executor
        while ex is not None:
            if isinstance(ex, SkillGateExecutor):
                found.add(ex.gate)
            ex = getattr(ex, '__dict__', {}).get('_inner')
        self.assertEqual(found, set(WORKER_GATES))


if __name__ == '__main__':
    unittest.main()
