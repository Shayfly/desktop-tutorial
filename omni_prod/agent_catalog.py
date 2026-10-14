"""148AI Agent OS catalog: every agent role of the founder's spec
(docs/AGENT_OS_SKILLS_RUNTIME_SPEC_HE.md, 2026-10-08) in one place.

A catalog entry DEFINES a role: responsibility, skills it may use, and its
acceptance condition. It claims nothing about whether the role runs. What runs
is declared separately and explicitly in `runtime_bindings.py`, and the status
shown anywhere is computed by `registry_audit.py` from those bindings and their
evidence -- never from this file and never from a prompt existing.

Several roles may be served by the same code (e.g. one generator call writes
frontend and backend); the spec allows that as long as ownership is explicit.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRole:
    key: str
    family: str
    name: str
    responsibility: str
    skills: tuple[str, ...]
    acceptance: str
    registry_key: str | None = None  # older MasterAgentsRegistry entry, if any


def _r(key, family, name, responsibility, skills, acceptance, registry_key=None):
    return AgentRole(key, family, name, responsibility, tuple(skills), acceptance, registry_key)


MANAGEMENT, SOFTWARE, QUALITY, ASSETS, MEDIA, GAMES, AUTOMATION, PLATFORM = (
    'management', 'software', 'quality', 'assets', 'media', 'games', 'automation', 'platform')

CATALOG: tuple[AgentRole, ...] = (
    # 2. Management and planning
    _r('request_interpreter', MANAGEMENT, 'Request Interpreter', 'understand a natural-language request and identify the product type',
       ('requirements extraction', 'target detection', 'constraint detection', 'confidence estimate'),
       'the request becomes an initial spec with assumptions marked', 'agent.product_architect'),
    _r('product_analyst', MANAGEMENT, 'Product Analyst', 'define users, screens and flows',
       ('user stories', 'acceptance criteria', 'edge-case analysis'),
       'every main requirement has a way to be tested', 'agent.product_architect'),
    _r('capability_resolver', MANAGEMENT, 'Capability Resolver', 'check what can be executed now',
       ('dependency closure', 'registry check', 'provider availability'),
       'returns available capabilities and exact gaps', 'agent.capability_planner'),
    _r('solution_architect', MANAGEMENT, 'Solution Architect', 'choose a structure that fits the product and budget',
       ('component design', 'API contracts', 'data schema', 'infrastructure choice'),
       'the design is executable with available capabilities', 'agent.product_architect'),
    _r('project_orchestrator', MANAGEMENT, 'Project Orchestrator', 'run the work graph',
       ('task creation', 'dependencies', 'dispatch', 'resume', 'cancel'),
       'work advances without duplicates and state is persisted', 'agent.chief_orchestrator'),
    _r('cost_controller', MANAGEMENT, 'Cost Controller', 'enforce budget and record cost',
       ('quote', 'reserve', 'meter', 'settle', 'reconcile'),
       'overspend is prevented and the ledger is explainable', 'agent.cost_planner'),
    # 3. Software
    _r('ux_designer', SOFTWARE, 'UX Designer', 'design user flow and screen states',
       ('navigation', 'forms', 'empty/loading/error states', 'accessibility'),
       'the main flow can be completed with no dead end', 'agent.design_director'),
    _r('frontend_developer', SOFTWARE, 'Frontend Developer', 'build a working interface',
       ('components', 'RTL', 'responsiveness', 'state', 'API wiring'),
       'the interface compiles and flows pass in a browser', 'agent.code'),
    _r('backend_developer', SOFTWARE, 'Backend Developer', 'build logic and API',
       ('endpoints', 'input validation', 'services', 'error handling'),
       'API contracts and business behaviour are verified', 'agent.backend'),
    _r('data_engineer', SOFTWARE, 'Data Engineer', 'design and manage data',
       ('schemas', 'migrations', 'indexes', 'integrity', 'restore', 'migration tests', 'compatibility'),
       'data persists, relations hold and migrations are tested', 'agent.backend'),
    _r('identity_access_engineer', SOFTWARE, 'Identity & Access Engineer', 'wire identity and permissions into the product',
       ('signup', 'login', 'sessions', 'authorization', 'tenant isolation'),
       'a user cannot reach data that is not theirs'),
    _r('integration_engineer', SOFTWARE, 'Integration Engineer', 'connect external services',
       ('adapters', 'OAuth/API configuration', 'webhooks', 'retries'),
       'a real authorized call to the provider passes', 'agent.integration'),
    _r('repository_maintainer', SOFTWARE, 'Repository Maintainer', 'keep code and versions whole',
       ('inspect', 'patch', 'dependency checks', 'commit', 'export'),
       'a change stays in scope and the result is reproducible'),
    # 4. Quality, repair, publishing
    _r('qa_verifier', QUALITY, 'QA Verifier', 'check the product against the requirements',
       ('unit/integration/E2E', 'browser tests', 'evidence capture'),
       'acceptance criteria verified with evidence', 'agent.qa'),
    _r('security_reviewer', QUALITY, 'Security Reviewer', 'check access boundaries and secrets',
       ('authorization checks', 'secret detection', 'dependency review'),
       'material failures are reported and block release by policy', 'agent.security'),
    _r('repair_agent', QUALITY, 'Repair Agent', 'reproduce and fix a failure',
       ('reproduce', 'diagnose', 'minimal patch', 'regression verify'),
       'the original failure is fixed with no known regression', 'agent.repair'),
    _r('preview_operator', QUALITY, 'Preview Operator', 'run a preview of the right version',
       ('runtime prepare', 'start', 'readiness', 'preview verify'),
       'the preview shows the right product and version'),
    _r('release_agent', QUALITY, 'Release Agent', 'publish an authorized version',
       ('build', 'deploy', 'smoke', 'release record', 'rollback'),
       'the address is live and the main flow works', 'agent.deployment'),
    _r('operations_agent', QUALITY, 'Operations Agent', 'monitor products and services',
       ('health checks', 'incident triage', 'recovery'),
       'a fault is detected and recorded; recovery stays within permissions'),
    # 5. Assets
    _r('asset_planner', ASSETS, 'Asset Planner', 'define which assets are needed',
       ('asset inventory', 'dimensions', 'formats', 'style specification'),
       'every asset has a use and a specification', 'agent.asset_director'),
    _r('visual_creator', ASSETS, 'Visual Creator', 'create and edit images',
       ('text-to-image', 'image editing', 'background removal', 'variants', 'icons', 'thumbnails', 'textures', 'sprites'),
       'valid files that match the specification', 'agent.asset_director'),
    _r('consistency_director', ASSETS, 'Consistency Director', 'keep characters and visual language consistent',
       ('character bible', 'brand bible', 'reference selection'),
       'consistency is checked between assets; uncertainty is marked', 'agent.design_director'),
    _r('asset_qa', ASSETS, 'Asset QA', 'check asset quality and usability',
       ('resolution', 'alpha', 'format', 'visual inspection'),
       'the asset is usable and its limits are recorded', 'agent.visual_qa'),
    _r('asset_librarian', ASSETS, 'Asset Librarian', 'manage assets and versions',
       ('metadata', 'provenance', 'deduplication', 'storage', 'retrieval'),
       'every asset can be found and is tied to project and source'),
    # 6. Media
    _r('media_producer', MEDIA, 'Media Producer', 'plan a production and its budget',
       ('production brief', 'shot list', 'timing', 'cost planning'), 'a producible plan within budget', 'agent.audio_director'),
    _r('scriptwriter', MEDIA, 'Scriptwriter', 'write the script and structure',
       ('outline', 'dialogue', 'narration', 'scene breakdown'), 'the script fits length, audience and goal'),
    _r('storyboard_director', MEDIA, 'Storyboard Director', 'turn a script into shots',
       ('storyboard', 'references', 'camera/motion specification'), 'every shot has clear generation instructions'),
    _r('video_creator', MEDIA, 'Video Creator', 'create video clips',
       ('text-to-video', 'image-to-video', 'supported editing'), 'clips created and checked for length and content'),
    _r('voice_audio_producer', MEDIA, 'Voice & Audio Producer', 'create or process sound',
       ('TTS', 'STT', 'voice selection', 'music/SFX generation'), 'audio is valid and fits content and usage rights', 'agent.audio_director'),
    _r('timeline_editor', MEDIA, 'Timeline Editor', 'assemble the full product',
       ('composition', 'cuts', 'transitions', 'audio mix', 'captions'), 'the assembled product opens and stays in sync'),
    _r('media_qa', MEDIA, 'Media QA', 'check the production',
       ('continuity', 'captions', 'clipping', 'duration', 'visual/audio review'), 'defects found before delivery'),
    _r('publishing_operator', MEDIA, 'Publishing Operator', 'prepare and publish to authorized channels',
       ('export presets', 'metadata', 'upload', 'scheduling'), 'publishing verified and recorded'),
    # 7. Games
    _r('game_designer', GAMES, 'Game Designer', 'define gameplay and goals',
       ('rules', 'core loop', 'progression', 'win/lose conditions'), 'a defined, testable game', 'agent.game_director'),
    _r('game_architect', GAMES, 'Game Architect', 'choose engine and structure',
       ('engine selection', 'scene model', 'runtime plan'), 'the choice is supported by the runtime', 'agent.game_director'),
    _r('gameplay_developer', GAMES, 'Gameplay Developer', 'implement behaviour',
       ('controls', 'physics', 'interactions', 'scoring'), 'the core loop is playable'),
    _r('level_designer', GAMES, 'Level Designer', 'create levels and content',
       ('layouts', 'encounters', 'difficulty progression'), 'levels load and can be completed', 'agent.world_builder'),
    _r('game_asset_coordinator', GAMES, 'Game Asset Coordinator', 'integrate assets into the game',
       ('sprites/models/audio integration', 'optimization'), 'assets load and fit performance'),
    _r('save_progression_engineer', GAMES, 'Save & Progression Engineer', 'persist progress',
       ('save/load', 'checkpoints', 'migration'), 'save and load restore the right state'),
    _r('playtest_agent', GAMES, 'Playtest Agent', 'test a game for real',
       ('input simulation', 'gameplay checks', 'performance capture'), 'the tested path can be started, played and finished', 'agent.playtester'),
    _r('multiplayer_engineer', GAMES, 'Multiplayer Engineer', 'shared play when infrastructure exists',
       ('synchronization', 'sessions', 'reconnect', 'authority checks'), 'tested with at least two real participants or separate clients'),
    # 8. Automations and customer AI agents
    _r('automation_designer', AUTOMATION, 'Automation Designer', 'define trigger, conditions and actions',
       ('workflow design', 'schemas', 'failure paths'), 'the process has no ambiguous step'),
    _r('connector_operator', AUTOMATION, 'Connector Operator', 'act on external services',
       ('connector invocation', 'webhook verification', 'pagination'), 'the action runs in the right account and scope', 'agent.integration'),
    _r('scheduler_operator', AUTOMATION, 'Scheduler Operator', 'manage scheduling',
       ('schedules', 'timezone handling', 'durable dispatch'), 'the task fires on time in the right time zone'),
    _r('automation_qa', AUTOMATION, 'Automation QA', 'test the process and its failures',
       ('replay', 'duplicate delivery', 'timeout/retry tests'), 'no double action and failures are reproducible'),
    _r('agent_app_builder', AUTOMATION, 'Agent App Builder', 'build an AI agent for a customer',
       ('instructions', 'tools', 'memory', 'guardrails', 'evaluation'), 'the agent does its tasks and avoids forbidden actions'),
    # 9. Extending 148AI itself
    _r('skill_builder', PLATFORM, 'Skill Builder', 'create a candidate skill',
       ('inspect existing code', 'contract generation', 'implementation', 'tests'), 'the candidate runs in a test environment'),
    _r('skill_evaluator', PLATFORM, 'Skill Evaluator', 'verify a new skill',
       ('schema', 'permissions', 'functional and failure tests'), 'an independent report says what passed and what failed'),
    _r('registry_auditor', PLATFORM, 'Registry Auditor', 'keep the registry truthful',
       ('dependency checks', 'stale verification detection', 'implementation matching'), 'nothing is LIVE without implementation and evidence'),
    _r('provider_evaluator', PLATFORM, 'Provider Evaluator', 'test providers and models',
       ('benchmark execution', 'cost/quality measurement'), 'routing decisions rest on recorded measurements'),
    # Master directive 2026-10-09 §8: 12 responsibilities that complete the
    # company. Explicit roles (not merged), so each has its own status; several
    # need deterministic components rather than an LLM.
    _r('discovery_lead', MANAGEMENT, 'Discovery Lead', 'professional discovery conversation, not a generic form',
       ('questions.select', 'preferences.delegate', 'contradiction.detect', 'answers.merge'),
       'clear, vague and delegated conversations each end in a summary the user approves'),
    _r('requirements_traceability_auditor', QUALITY, 'Requirements Traceability Auditor', 'prevent omissions',
       ('brief->task->artifact->test matrix',), 'every approved requirement is covered by a passing check or an explicit blocker'),
    _r('brand_design_director', SOFTWARE, 'Brand & Design Director', 'a professional visual language for each product',
       ('palette.propose', 'typography.select', 'design.tokens', 'references'), 'approved choices are used consistently'),
    _r('accessibility_localization_reviewer', QUALITY, 'Accessibility & Localization Reviewer', 'usability and languages',
       ('keyboard/focus', 'labels', 'RTL/LTR', 'locale.verify'), 'desktop and mobile checks pass'),
    _r('integration_secret_steward', PLATFORM, 'Integration & Secret Steward', 'ownership of commercial connections',
       ('scopes', 'vault refs', 'revoke', 'managed/customer/BYOK'), 'no secret in any product, log or export'),
    _r('reliability_recovery_engineer', PLATFORM, 'Reliability & Recovery Engineer', 'failure without losing work',
       ('checkpoints', 'leases', 'compensation', 'restore'), 'crash recovery is proven'),
    _r('performance_resource_engineer', PLATFORM, 'Performance & Resource Engineer', 'time and resources',
       ('profiling', 'runtime limits', 'resources.cleanup'), 'measured limits hold'),
    _r('release_change_coordinator', PLATFORM, 'Release & Change Coordinator', 'no uncoordinated change',
       ('branch ownership', 'CI/worker gate', 'safe rollout'), 'no worker is replaced in the middle of a build'),
    _r('privacy_ip_steward', QUALITY, 'Privacy & IP Steward', 'provenance, data and policy',
       ('provenance', 'consent', 'retention', 'complaint routing'), 'no invented license'),
    _r('customer_success_handover', MANAGEMENT, 'Customer Success & Handover Agent', 'a delivery the customer understands',
       ('onboarding', 'known limits', 'usage guide'), 'a new person succeeds in using the product'),
    _r('product_economics_analyst', MANAGEMENT, 'Product Economics Analyst', 'business advantage and contribution margin',
       ('per-stage cost', 'scenario analysis', 'gross contribution'), 'assumptions are marked'),
    _r('partner_readiness_reviewer', QUALITY, 'Partner Readiness Reviewer', 'independent review of the product',
       ('acceptance matrix', 'cold demo', 'evidence review'), 'no blocker is hidden'),
)

BY_KEY = {role.key: role for role in CATALOG}
assert len(BY_KEY) == len(CATALOG), 'duplicate agent role key'
