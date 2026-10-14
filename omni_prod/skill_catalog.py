"""Master skills catalog (master directive 2026-10-09 §9), executable view.

Every skill named in §9 has an entry: its kind, the code that implements it
(or none -- then it is NOT_IMPLEMENTED, explicitly), its dependencies, the
evidence and the remaining gap. Status is computed by `registry_audit`, never
written here.

Kinds (§6):
  INSTRUCTION  guidance injected into a model prompt (injection is not proof
               the output complied)
  EXECUTABLE   code that performs the action
  VALIDATOR    code that checks an artifact or a running product
  WORKFLOW     an orchestration of other skills

Implementation targets are 'module:Symbol' or 'path:<file>'. Names follow §9;
where existing code serves a skill, it is named instead of re-implemented.
"""
from __future__ import annotations

from dataclasses import dataclass

from .runtime_bindings import Evidence, _FOUNDER_BUILD, _FOUNDER_CHANGE, _LIBRARY, _REHEARSAL, _E2E

INSTRUCTION, EXECUTABLE, VALIDATOR, WORKFLOW = 'INSTRUCTION', 'EXECUTABLE', 'VALIDATOR', 'WORKFLOW'


@dataclass(frozen=True)
class SkillSpec:
    key: str
    area: str
    kind: str
    implementation: tuple[str, ...] = ()
    depends: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    gap: str = ''


_BROWSER_DEPLOY = Evidence('live', 'deploy-worker run 37864475043', 'browser-probe PASS both ways on the host', 'd8a01fa',
                           'worker-host', ('working fixture passes', 'vanishing-message fixture caught'))
_DRAIN = Evidence('live', 'deploy-worker run 37862903906', 'drained 213 s for a running job', '51bb631', 'worker-host',
                  ('deploy waited for the running job',))
_RACE = Evidence('unit', 'tests/test_golden_mod_path_live_postgres.py::test_two_parallel_approvals_of_one_plan_create_one_build',
                 'live Postgres, two parallel approvals -> one build')
_QA_COUNT = Evidence('live', 'build-evidence run 37864934013', 'QA counted all-time $3.31', 'd8a01fa', 'worker-host',
                     ('recorded spend counted once per build',))
_PROBE = Evidence('live', 'model-probe run 37814803770', '3 Gemini models ok; OpenAI/Anthropic: no credit', 'ff6b4f6',
                  'worker-host', ('availability of each catalog model',))
_ZIP = Evidence('live', 'ZIP of v_0bc82ef7b33b4210 opened by the founder 2026-10-08 22:59', '', '3a4d822', 'workspace',
                ('export ZIP of a promoted version',))
_RESTORE = Evidence('unit', 'tests/test_golden_mod_path_live_postgres.py::test_restore_copies_the_spec_so_the_restored_version_can_be_modified')


def _s(key, area, kind, impl=(), depends=(), evidence=(), gap=''):
    return SkillSpec(key, area, kind, tuple(impl), tuple(depends), tuple(evidence), gap)


_NI = 'not implemented'

CATALOG: tuple[SkillSpec, ...] = (
    # Discovery
    _s('intent.parse', 'discovery', EXECUTABLE, ('omni_prod.product_architect:ProductArchitect',), (), (_FOUNDER_BUILD, _LIBRARY),
       'one pass, no conversation'),
    _s('domain.classify', 'discovery', EXECUTABLE, ('omni_prod.capability_planner:CapabilityPlanner',), ('intent.parse',), (_FOUNDER_BUILD,),
       'keyword based; "משחק" misread'),
    _s('requirements.extract', 'discovery', EXECUTABLE, ('omni_prod.autonomous_agents:ArchitectAgent',), ('intent.parse',),
       (_FOUNDER_BUILD, _FOUNDER_CHANGE)),
    _s('questions.select', 'discovery', EXECUTABLE, ('omni_prod.discovery:next_group',), ('requirements.extract',), (Evidence('unit', 'tests/test_discovery_and_approval.py'),),
       'deterministic question bank (web/business systems); not yet used by a founder'),
    _s('answers.merge', 'discovery', EXECUTABLE, ('omni_prod.discovery:answer',), ('questions.select',), (Evidence('unit', 'tests/test_discovery_and_approval.py'),)),
    _s('ambiguity.resolve', 'discovery', WORKFLOW, ('omni_prod.discovery:next_group', 'omni_prod.discovery:answer'),
       ('questions.select', 'answers.merge'), (Evidence('unit', 'tests/test_discovery_and_approval.py'),)),
    _s('contradiction.detect', 'discovery', VALIDATOR, ('omni_prod.discovery:contradictions',), ('requirements.extract',), (Evidence('unit', 'tests/test_discovery_and_approval.py'),),
       'one rule (no sign-in + personal data + outside users)'),
    _s('preferences.delegate', 'discovery', EXECUTABLE, ('omni_prod.discovery:answer',), ('questions.select',), (Evidence('unit', 'tests/test_discovery_and_approval.py'),)),
    _s('references.ingest', 'discovery', EXECUTABLE, (), (), (), _NI),
    _s('brief.summarize', 'discovery', EXECUTABLE, ('omni_prod.discovery:summary',), ('answers.merge',), (Evidence('unit', 'tests/test_discovery_and_approval.py'),)),
    _s('acceptance.define', 'discovery', EXECUTABLE, ('omni_prod.autonomous_agents:ArchitectAgent',), ('requirements.extract',),
       (_FOUNDER_BUILD,)),
    # Approval
    _s('brief.revise', 'approval', EXECUTABLE, ('omni_prod.brief_repository:PostgresBriefRepository.save',), ('brief.summarize',),
       (Evidence('unit', 'tests/test_discovery_and_approval.py'),)),
    _s('approval.bind', 'approval', EXECUTABLE, ('omni_prod.brief_repository:PostgresBriefRepository.create_approval',
                                                 'omni_prod.job_repository:PostgresBuildRepository.claim_contract_build'),
       ('brief.revise',), (_RACE, Evidence('unit', 'tests/test_discovery_and_approval.py'))),
    _s('approval.validate', 'approval', VALIDATOR, ('omni_prod.build_contract:BuildContract.verify_fingerprint',), ('approval.bind',),
       (_FOUNDER_BUILD,)),
    _s('approval.invalidate', 'approval', EXECUTABLE, ('omni_prod.brief_repository:PostgresBriefRepository.consume',),
       ('approval.bind',), (Evidence('unit', 'tests/test_discovery_and_approval.py'),)),
    _s('scope.diff', 'approval', EXECUTABLE, (), (), (), _NI),
    _s('change.classify', 'approval', EXECUTABLE, ('omni_prod.autonomous_agents:ChangeClassifierAgent',), (), (_FOUNDER_CHANGE,)),
    # Design
    _s('brand.profile', 'design', EXECUTABLE, (), (), (), _NI),
    _s('palette.propose', 'design', INSTRUCTION, ('omni_prod.skills_runtime:VISUAL_DESIGN',), (), (), 'model chooses; user not asked'),
    _s('typography.select', 'design', INSTRUCTION, ('omni_prod.skills_runtime:VISUAL_DESIGN',), (), (), 'model chooses; user not asked'),
    _s('design.tokens', 'design', VALIDATOR, ('omni_prod.skills_runtime:VISUAL_DESIGN',), ('palette.propose', 'typography.select'), (),
       'CSS heuristic only (not a design approval, §11)'),
    _s('screen.plan', 'design', EXECUTABLE, (), (), (), _NI),
    _s('states.define', 'design', INSTRUCTION, ('omni_prod.skills_runtime:UI_STATES',), (), ()),
    _s('responsive.verify', 'design', VALIDATOR, (), (), (), _NI + ' (static @media check only)'),
    _s('visual.compare', 'design', VALIDATOR, (), (), (), _NI),
    _s('accessibility.check', 'design', VALIDATOR, (), (), (), _NI),
    _s('locale.verify', 'design', INSTRUCTION, ('omni_prod.skills_runtime:TEXT_LOCALE',), (), ()),
    # Planning
    _s('capabilities.resolve', 'planning', EXECUTABLE, ('omni_prod.capability_planner:CapabilityPlanner',), ('requirements.extract',),
       (_FOUNDER_BUILD,)),
    _s('dependencies.close', 'planning', VALIDATOR, ('omni_prod.skills_registry:MasterSkillsRegistry.dependency_closure',),
       ('capabilities.resolve',), (Evidence('unit', 'tests/test_m495_skills_agents_registry.py'),)),
    _s('architecture.plan', 'planning', EXECUTABLE, ('omni_prod.autonomous_agents:ArchitectAgent',), ('capabilities.resolve',),
       (_FOUNDER_BUILD,), 'one fixed stack'),
    _s('api.contract', 'planning', EXECUTABLE, (), (), (), _NI),
    _s('data.schema', 'planning', EXECUTABLE, (), (), (), _NI),
    _s('tasks.graph', 'planning', WORKFLOW, (), (), (), _NI + ' (fixed pipeline)'),
    _s('risk.classify', 'planning', EXECUTABLE, (), (), (), _NI),
    # Code
    _s('repository.inspect', 'code', EXECUTABLE, ('omni_prod.workspace:PostgresProjectWorkspace',), (), (_FOUNDER_CHANGE,)),
    _s('context.select', 'code', EXECUTABLE, (), (), (), _NI + ' (whole repository is sent)'),
    _s('code.generate', 'code', EXECUTABLE, ('omni_prod.autonomous_agents:GeneratorAgent',), ('architecture.plan', 'approval.validate'),
       (_FOUNDER_BUILD, _LIBRARY, _REHEARSAL)),
    _s('code.patch', 'code', EXECUTABLE, ('omni_prod.autonomous_agents:RepairAgent',), ('tests.run',), (_FOUNDER_BUILD,),
       'rewrites the repository, not a minimal patch'),
    _s('frontend.build', 'code', EXECUTABLE, ('omni_prod.autonomous_agents:GeneratorAgent',), ('code.generate',), (_FOUNDER_BUILD,)),
    _s('backend.build', 'code', EXECUTABLE, ('omni_prod.autonomous_agents:GeneratorAgent',), ('code.generate',), (_FOUNDER_BUILD,)),
    _s('dependencies.lock', 'code', VALIDATOR, ('omni_prod.dependency_policy:DependencyGateExecutor',), (), (_FOUNDER_BUILD,),
       'allowlist gate (no install step)'),
    _s('diff.review', 'code', VALIDATOR, ('omni_prod.product_review:ProductReviewExecutor',), ('code.generate',),
       (Evidence('live', 'golden-rehearsal run 37841459920', 'QA review round 1, 0 blocking', 'dbd1232', 'worker-host',
                 ('model review of the code',)),), 'reviews the whole code, not a diff'),
    # Data
    _s('migration.create', 'data', EXECUTABLE, (), (), (), _NI + ' (generated apps)'),
    _s('migration.verify', 'data', VALIDATOR, (), (), (), _NI),
    _s('data.constraints', 'data', INSTRUCTION, ('omni_prod.skills_runtime:DATA_INTEGRITY',), (), (_LIBRARY,),
       'library build: duplicate member answered 409'),
    _s('data.persistence.verify', 'data', VALIDATOR, ('omni_prod.preview_durability:selftest',
                                                      'omni_prod.preview_runtime:DockerPreviewProvider.ensure_data_dir'), (),
       (Evidence('unit', 'tests/test_preview_data_durability.py', 'per-project data dir, scratch copy for acceptance, '
                 'self-test logic'),),
       'previews only (one directory per project on the preview host); no backup, no size quota, '
       'no schema migration of old data'),
    _s('data.backup', 'data', EXECUTABLE, (), (), (), _NI),
    _s('data.restore', 'data', EXECUTABLE, (), (), (), _NI),
    _s('tenant.isolation.verify', 'data', VALIDATOR, (), (), (), _NI + ' (generated apps)'),
    # Identity and connections
    _s('auth.configure', 'identity', EXECUTABLE, (), (), (), _NI + ' (generated apps)'),
    _s('authorization.verify', 'identity', VALIDATOR, (), (), (), _NI),
    _s('secrets.resolve', 'identity', EXECUTABLE, (), (), (), _NI + ' (generated apps)'),
    _s('integration.configure', 'identity', EXECUTABLE, (), (), (), _NI),
    _s('integration.probe', 'identity', VALIDATOR, ('omni_prod.model_probe:probe',), (), (_PROBE,), 'model providers only'),
    _s('webhook.verify', 'identity', VALIDATOR, (), (), (), _NI),
    _s('connection.revoke', 'identity', EXECUTABLE, (), (), (), _NI),
    _s('binding.validate', 'identity', VALIDATOR, (), (), (), _NI),
    # Execution
    _s('sandbox.prepare', 'execution', EXECUTABLE, ('omni_prod.sandbox:build_docker_command',), (), (_FOUNDER_BUILD,)),
    _s('app.start', 'execution', VALIDATOR, ('omni_prod.preview_smoke:PreviewReadyExecutor',), ('sandbox.prepare',), (_FOUNDER_BUILD,)),
    _s('runtime.readiness', 'execution', VALIDATOR, ('omni_prod.preview_runtime:DockerPreviewProvider',), ('app.start',),
       (_FOUNDER_BUILD,)),
    _s('task.checkpoint', 'execution', EXECUTABLE, (), (), (), _NI),
    _s('task.resume', 'execution', EXECUTABLE, (), ('task.checkpoint',), (), _NI),
    _s('task.cancel', 'execution', EXECUTABLE, ('omni_prod.build_control:BuildControl',
                                               'omni_prod.job_repository:PostgresBuildRepository.request_cancel'), (),
       (Evidence('unit', 'tests/test_build_cancel_and_log.py', 'queued cancelled at once; running stops before the next '
                 'model call or test run; foreign tenant refused (live Postgres)'),),
       'builds only (not modifications); stops at a step boundary, not inside a model call'),
    _s('operation.deduplicate', 'execution', EXECUTABLE, ('omni_prod.job_repository:PostgresBuildRepository.claim_contract_build',),
       (), (_RACE,)),
    _s('effects.compensate', 'execution', EXECUTABLE, ('omni_prod.maintenance:run_once',), (), (),
       'janitor releases reservations of lost builds; nothing else'),
    _s('resources.cleanup', 'execution', EXECUTABLE, ('omni_prod.sandbox:sweep_stale_containers', 'omni_prod.maintenance:run_once'),
       (), (Evidence('unit', 'tests/test_sandbox_cleanup.py'),)),
    # Quality
    _s('tests.plan', 'quality', EXECUTABLE, ('omni_prod.autonomous_agents:ArchitectAgent',), ('acceptance.define',), (_FOUNDER_BUILD,)),
    _s('tests.run', 'quality', VALIDATOR, ('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor',), ('sandbox.prepare',),
       (_FOUNDER_BUILD, _REHEARSAL)),
    _s('api.behavior.verify', 'quality', VALIDATOR, ('omni_prod.web_saas_acceptance:WebSaaSAcceptanceRunner',
                                                     'omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor'),
       ('runtime.readiness',),
       (_LIBRARY, Evidence('unit', 'tests/test_behavior_acceptance_in_build.py',
                           'in-build run against a real started app; 400 becomes repairable evidence; '
                           'requirements-aware scope')),
       'in-build gate not yet seen inside a real build'),
    _s('browser.flow.verify', 'quality', VALIDATOR, ('omni_prod.browser_probe:BrowserFlowExecutor',), ('app.start',),
       (_BROWSER_DEPLOY, Evidence('unit', 'tests/test_browser_probe.py')), 'not yet inside a founder build'),
    _s('visual.inspect', 'quality', VALIDATOR, (), ('browser.flow.verify',), (), _NI + ' (no screenshots)'),
    _s('security.negative_test', 'quality', VALIDATOR, ('omni_prod.security_testing:hostile_repository_scan',), (), (_FOUNDER_BUILD,),
       'static scan only'),
    _s('failure.reproduce', 'quality', EXECUTABLE, (), (), (), _NI),
    _s('repair.patch', 'quality', EXECUTABLE, ('omni_prod.autonomous_agents:RepairAgent',), ('tests.run',),
       (Evidence('live', 'golden-rehearsal run 37814985551', '5 repair rounds converged', 'ff6b4f6', 'worker-host',
                 ('failing tests repaired',)),)),
    _s('regression.verify', 'quality', VALIDATOR, ('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor',), ('tests.run',),
       (_FOUNDER_CHANGE,), 'reruns the version\'s own tests'),
    # Delivery
    _s('artifact.commit', 'delivery', EXECUTABLE, ('omni_prod.workspace:PostgresProjectWorkspace',), (), (_FOUNDER_BUILD,)),
    _s('version.restore', 'delivery', EXECUTABLE, ('omni_prod.spec_repository:restore_version_with_spec',), (), (_RESTORE,)),
    _s('preview.verify', 'delivery', VALIDATOR, ('omni_prod.preview_repository:PostgresPreviewRepository',),
       ('runtime.readiness', 'api.behavior.verify'), (_LIBRARY,), 'acceptance recording fixed 2026-10-09'),
    _s('project.export', 'delivery', EXECUTABLE, ('omni_prod.storage:S3ArtifactStore',), ('artifact.commit',), (_ZIP,)),
    _s('release.prepare', 'delivery', WORKFLOW, (), (), (), _NI),
    _s('deployment.publish', 'delivery', EXECUTABLE, (), ('release.prepare',), (), _NI + ' (promote is in memory only)'),
    _s('deployment.verify', 'delivery', VALIDATOR, (), ('deployment.publish',), (), _NI),
    _s('deployment.rollback', 'delivery', EXECUTABLE, (), ('deployment.publish',), (), _NI),
    _s('handover.generate', 'delivery', EXECUTABLE, (), (), (), _NI),
    # Cost
    _s('cost.quote', 'cost', EXECUTABLE, ('path:omni_prod/investor_app.py', 'omni_prod.build_cost_plan:build_economics_quote'), (), (_FOUNDER_BUILD,)),
    _s('budget.reserve', 'cost', EXECUTABLE, ('omni_prod.subscription_store:PostgresSubscriptionService', 'omni_prod.qa_budget:authorize_qa_build'),
       ('cost.quote',), (_FOUNDER_BUILD, _QA_COUNT)),
    _s('usage.record', 'cost', EXECUTABLE, ('omni_prod.routed_gateway:RoutedModelGateway',), (), (_QA_COUNT,),
       'tokens x catalog price, not supplier-confirmed'),
    _s('cost.estimate', 'cost', EXECUTABLE, ('omni_prod.rehearsal:cost_projection',), (), ()),
    _s('cost.reconcile', 'cost', VALIDATOR, (), ('usage.record',), (), _NI + ' (no supplier invoice)'),
    _s('budget.settle', 'cost', EXECUTABLE, ('omni_prod.subscription_store:PostgresSubscriptionService',), ('budget.reserve',),
       (_FOUNDER_BUILD,)),
    _s('margin.calculate', 'cost', EXECUTABLE, (), (), (), _NI),
    _s('budget.guard', 'cost', VALIDATOR, ('omni_prod.routed_gateway:RoutedModelGateway', 'omni_prod.qa_budget:authorize_qa_build'),
       ('budget.reserve',), (_QA_COUNT, Evidence('unit', 'tests/test_qa_budget.py'))),
    # Assets
    _s('assets.plan', 'assets', EXECUTABLE, (), (), (), _NI),
    _s('image.generate', 'assets', EXECUTABLE, ('omni_prod.providers.image_provider:PredictionImageProvider',), (),
       (Evidence('unit', 'tests/test_replicate_image_test.py'),), 'no image generated live; not on the build path'),
    _s('image.edit', 'assets', EXECUTABLE, (), (), (), _NI),
    _s('image.cutout', 'assets', EXECUTABLE, (), (), (), _NI),
    _s('asset.inspect', 'assets', VALIDATOR, (), (), (), _NI),
    _s('consistency.verify', 'assets', VALIDATOR, (), (), (), _NI),
    _s('asset.store', 'assets', EXECUTABLE, (), (), (), _NI),
    _s('provenance.record', 'assets', EXECUTABLE, (), (), (), _NI + ' (provenance.json is written for code builds only)'),
) + tuple(
    _s(key, area, kind, (), (), (), _NI) for area, kind, keys in (
        ('media', EXECUTABLE, ('script.write', 'storyboard.create', 'shots.plan', 'video.generate', 'voice.generate',
                               'speech.transcribe', 'music.generate', 'captions.align', 'timeline.compose', 'media.render',
                               'media.verify', 'media.export')),
        ('games', EXECUTABLE, ('game.rules', 'engine.select', 'scene.build', 'controls.bind', 'physics.configure',
                               'levels.generate', 'save.load', 'game.playtest', 'multiplayer.sync', 'game.performance')),
        ('automation', EXECUTABLE, ('trigger.configure', 'workflow.execute', 'schedule.configure', 'connector.invoke',
                                    'automation.replay', 'agent.configure', 'memory.configure', 'agent.evaluate')),
        ('extension', EXECUTABLE, ('skill.propose', 'skill.implement', 'skill.evaluate', 'verification.refresh',
                                   'readiness.audit')),
    ) for key in keys
) + (
    _s('registry.audit', 'extension', VALIDATOR, ('omni_prod.registry_audit:audit',), (), (Evidence('unit', 'tests/test_registry_audit.py'),)),
    _s('provider.benchmark', 'extension', VALIDATOR, ('omni_prod.model_probe:probe',), (), (_PROBE,), 'availability only, no quality benchmark'),
)

BY_KEY = {s.key: s for s in CATALOG}
assert len(BY_KEY) == len(CATALOG), 'duplicate skill key'
_E2E_USED = _E2E  # kept importable for future entries
