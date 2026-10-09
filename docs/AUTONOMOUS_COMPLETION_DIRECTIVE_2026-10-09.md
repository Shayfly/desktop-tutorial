כן. עכשיו צריך לתת לו **פקודת־על אחת** שמחברת שלושה דברים יחד:

1. לסגור את כל ה־P0 שכבר נחשפו במערכת האמיתית.
2. לבנות את **Agent OS + Skills OS** המלאים.
3. לבנות במקביל **מערכת בדיקות פנימית שבודקת את 148AI עצמה בזמן שאנחנו מפתחים אותה**, ולא רק את המוצרים של הלקוחות.

והפעם הייתי נותן לו הרשאה מפורשת **להמשיך שלב אחרי שלב בלי לחזור אליך על כל merge/test/fix**, כל עוד הוא שומר rollback ולא עושה פעולה הרסנית בלתי־הפיכה.

תשלח לו את זה בדיוק:

---

# 148AI — AUTONOMOUS COMPLETION DIRECTIVE

## Fix the current real-server blockers, build the complete Agent OS + Skills OS, and build a self-verifying development system

You are authorized to continue autonomously through this program without asking the founder for approval after every step.

The objective is not to stop at another milestone or another registry update.

The objective is to take the current 148AI pre-staging system as far as responsibly possible toward the highest-quality, production-grade implementation supported by the current repository, infrastructure, credentials, providers and budget.

## Founder authorization

You are authorized to:

* create branches
* commit
* merge into the approved pre-staging branch
* run migrations
* deploy pre-staging
* repair failures
* add tests
* refactor where justified
* add agents
* add skills
* add registries
* add runtime infrastructure
* run real-browser tests
* run real-server tests
* run paid AI tests within the approved test budget
* iterate repeatedly until acceptance passes

Do **not** stop to ask for approval between normal engineering steps.

Do **not** stop merely because one test fails.

A failure should normally trigger:

**detect → diagnose → repair → retest → verify → continue**

Only stop and report a hard blocker if continuing is genuinely impossible because of something external such as:

* missing credential that cannot be obtained programmatically
* external provider/account suspension
* irreversible destructive production action with no safe rollback
* legal/commercial ambiguity that cannot be resolved from authoritative terms
* exhausted approved paid test budget
* infrastructure unavailable outside our control

Everything else should be treated as an engineering problem to solve.

---

# 0. NON-NEGOTIABLE RULE — DO NOT BREAK WHAT ALREADY WORKS

Preserve all currently working behavior, including:

* discovery conversation
* server-enforced approval
* no duplicate build on double approval
* durable build jobs
* build cancellation
* live build journal
* page refresh recovery
* persistent generated-app data
* persistence across restart
* persistence across generated versions
* isolated scratch acceptance data
* real browser rehearsal
* preview creation
* project/version integrity
* checksum validation
* real error states
* no fake publish
* no fake demo success
* cost metering
* quote → reserve → execute → meter → settle foundation
* migration history
* existing projects and versions

Before every major phase:

1. run baseline regression suite
2. record results
3. apply change
4. run regression suite again
5. compare
6. repair regressions before continuing

Never knowingly carry a new regression into the next phase.

---

# 1. FIX THE CURRENT REAL-SERVER P0 BLOCKERS FIRST

The latest real-server run exposed real failures.

Close them before declaring the existing build path stable.

## P0.1 — Behavioral Acceptance → Repair Loop

Current problem:

A generated booking application reached READY, browser QA passed, but behavioral acceptance failed because creating an appointment returned HTTP 400.

Behavioral acceptance must become part of the autonomous repair loop.

Required flow:

```text
Build
→ Browser QA
→ Behavioral Acceptance
→ Failure Evidence
→ Root Cause Analysis
→ Repair Plan
→ Minimal Repair
→ Rebuild
→ Behavioral Acceptance
→ repeat until pass / hard blocker / budget limit
```

Acceptance failures must never be treated as informational warnings.

The generated product is not releasable until its critical acceptance flows pass.

Store full evidence:

* action attempted
* HTTP request
* safe/redacted response
* UI state
* backend error
* expected behavior
* actual behavior
* suspected root cause
* repair commit/version
* retest evidence

---

# 2. MAKE ACCEPTANCE REQUIREMENTS-AWARE

Current problem:

Products explicitly approved without authentication are still tested for authentication/roles.

This is architecturally wrong.

Acceptance must be derived from the **approved product specification**, not from a generic universal checklist.

Implement:

```text
Approved Requirements
        ↓
Acceptance Contract Generator
        ↓
Required Tests
```

Examples:

If:

```text
authentication = false
```

then auth/login/role tests must NOT be required.

If:

```text
persistent_data = true
```

then persistence tests ARE mandatory.

If:

```text
mobile_required = true
```

mobile viewport tests ARE mandatory.

If:

```text
payments = false
```

payment acceptance is excluded.

The acceptance suite must understand what was actually promised to the user.

---

# 3. FIX ACTUAL-COST SETTLEMENT

Current failure:

Actual Gemini provider cost was approximately:

```text
$0.1209
```

but the customer reservation settles against a conservative ceiling such as:

```text
$0.50
```

This is unacceptable for final billing economics.

Implement canonical provider usage accounting:

```text
provider response
→ usage evidence
→ input units
→ output units
→ media units if applicable
→ versioned Provider Price Catalog
→ exact provider cost
→ total build actual cost
→ platform markup/margin
→ customer settlement
→ release unused reservation
```

Requirements:

* price catalog version stored with execution
* historical executions remain reproducible after price changes
* unknown provider pricing must not silently become zero
* unknown pricing must block settlement or use explicitly approved conservative policy
* customer must never be charged as though all reserved capacity was consumed
* reservation and actual settlement must be auditable

Add reconciliation tests.

---

# 4. SECURE PREVIEW ACCESS

Current previews are effectively public and may be discovered through certificate transparency/domain enumeration.

Fix this before public launch.

Implement controlled preview access.

Preferred architecture:

* authenticated preview proxy OR signed expiring access token
* project ownership enforcement
* preview session/token expiration
* no direct anonymous access to private generated projects
* secrets never exposed client-side
* access audit
* revocation
* optional share token for deliberate sharing

Clearly distinguish:

```text
PRIVATE
SHARED
PUBLIC
```

preview modes.

Default must be PRIVATE.

Test unauthorized access explicitly.

---

# 5. COMPLETE DURABILITY

Implement and verify:

## Build crash recovery

A build must survive:

* worker restart
* application server restart
* deployment
* process crash

No build may become permanently stranded without janitor/recovery handling.

## Changes/modifications

Bring modification flows to parity with builds:

* cancellation
* journal
* recovery
* status
* cost tracking

## Backup + Restore

Persistence alone is NOT durability.

Implement:

* database backup
* project artifact backup
* version metadata backup
* scheduled retention policy
* restore procedure
* automated restore test

A backup is not VERIFIED until restore succeeds.

---

# 6. NOW BUILD THE COMPLETE AGENT OS

Do not merely create registry entries.

Create executable Agents with runtime contracts.

Every Agent must contain:

```text
agent_key
name
version
category
identity
purpose
unique_responsibility
when_invoked
trigger_conditions
required_inputs
outputs
allowed_skills
forbidden_skills
allowed_tools
forbidden_actions
permissions
provider_policy
budget_policy
memory_policy
state_policy
handoff_policy
retry_policy
timeout_policy
escalation_policy
approval_policy
success_criteria
failure_criteria
verifier
verification_tests
observability_requirements
security_requirements
commercial_constraints
status
implementation_location
last_verified_at
last_verified_commit
```

Statuses:

```text
LIVE
PARTIAL
NOT_CONFIGURED
NOT_IMPLEMENTED
BLOCKED
```

Never mark LIVE because a class exists.

LIVE requires executable evidence.

---

# 7. IMPLEMENT THESE AGENTS

## Core Product / Software Agents

1. Executive Orchestrator
2. Discovery Agent
3. Requirements Agent
4. Product Planner
5. Architecture Agent
6. UX/UI Design Agent
7. Frontend Agent
8. Backend Agent
9. Database Agent
10. Identity & Authentication Agent
11. Integration Agent
12. Coding Agent
13. Code Review Agent
14. QA Agent
15. Browser Rehearsal Agent
16. Behavioral Acceptance Agent
17. Repair Agent
18. Security Agent
19. Compliance & IP Agent
20. Provider Router Agent
21. Cost & Economics Agent
22. Infrastructure Agent
23. Deployment Agent
24. Release Agent
25. Observability Agent
26. SRE / Reliability Agent
27. Backup & Recovery Agent
28. Migration Agent
29. Performance Agent
30. Accessibility Agent
31. Localization / RTL Agent
32. SEO / Web Quality Agent
33. Analytics Agent
34. Product Evolution Agent
35. Automation Agent

## Media Agents

36. Media Orchestrator
37. Image Agent
38. Video Agent
39. Voice & Speech Agent
40. Audio / Music Agent

## 2D Game Agents

Do not implement open-world/AAA 3D as current core scope.

41. 2D Game Designer Agent
42. 2D Level Designer Agent
43. 2D Game Engineering Agent
44. 2D Game QA Agent

Preferred first runtime:

```text
Phaser + HTML5/Canvas
```

## Support Agents

45. Diagnostic Agent
46. Support Agent

---

# 8. ADD META-AGENTS THAT VERIFY 148AI ITSELF

This is essential.

148AI must not only test generated customer products.

It must also continuously test **its own development system**.

Create these additional system-level Agents.

---

## AGENT 47 — Platform Capability Auditor

### Purpose

Continuously compare:

```text
what 148AI claims it can do
vs
what the repository can actually do
```

### Responsibilities

* scan Master Agents Registry
* scan Master Skills Registry
* inspect implementations
* inspect tests
* inspect last verification evidence
* detect capability drift
* detect stale LIVE statuses
* downgrade capabilities when evidence expires or breaks

It must prevent registry inflation.

---

## AGENT 48 — Regression Guardian

### Purpose

Protect existing functionality while the platform evolves.

### Runs

Before and after every material platform change.

### Maintains

a versioned regression matrix covering:

* discovery
* approval
* build
* modify
* cancel
* resume
* journal
* provider routing
* economics
* persistence
* preview
* browser execution
* release
* recovery

Any new regression blocks progression to the next implementation phase.

---

## AGENT 49 — Golden Path Verifier

### Purpose

Continuously run canonical end-to-end journeys through 148AI itself.

Example Golden Paths:

### Golden Web/SaaS

```text
Prompt
→ Discovery
→ Requirements
→ Quote
→ Approval
→ Plan
→ Build
→ Browser Test
→ Behavioral Test
→ Repair
→ Retest
→ Persistence
→ Version
→ Preview
→ Release Readiness
→ Cost Settlement
```

### Existing Project Modification

```text
Open Existing Project
→ Request Change
→ Analyze Existing Files
→ Minimal Patch
→ Test
→ Browser
→ Verify Existing Behavior
→ Version
```

### Cancellation

### Crash Resume

### Provider Fallback

### Budget Limit

### Backup Restore

### Automation

### Media

### 2D Game

Golden paths must run against real platform components wherever safe.

---

## AGENT 50 — System Test Orchestrator

### Purpose

Own the complete testing strategy of 148AI itself.

It decides which test layers are required after each platform change.

Testing pyramid:

```text
static validation
↓
unit
↓
contract
↓
integration
↓
repository
↓
database
↓
worker/queue
↓
API
↓
browser
↓
behavioral acceptance
↓
real-server
↓
golden E2E
↓
failure injection
↓
recovery
```

It must prevent a developer from saying:

> “unit tests passed, therefore feature is complete.”

---

## AGENT 51 — Failure Injection Agent

### Purpose

Intentionally test bad conditions.

Inject controlled failures such as:

* provider timeout
* malformed provider response
* provider 429
* provider 500
* DB unavailable
* worker killed
* queue interruption
* deployment during build
* browser JS exception
* invalid migration
* network interruption
* insufficient credits
* exhausted budget
* invalid OAuth
* expired preview token
* corrupted artifact reference

Verify graceful handling and recovery.

Never run destructive chaos tests against real customer production data.

---

## AGENT 52 — Quality Gate Agent

### Purpose

Final platform-level gate.

A milestone cannot be considered VERIFIED unless this agent can prove:

* tests passed
* critical regressions absent
* security gate passed
* behavioral acceptance passed
* cost accounting valid
* recovery validated
* registry statuses truthful

---

# 9. BUILD THE COMPLETE SKILLS OS

Agents decide and coordinate.

Skills execute bounded capabilities.

Do not create giant generic skills such as:

```text
build_everything()
```

Skills must be composable and independently testable.

Implement/register the complete Skills taxonomy below.

---

## Discovery / Requirements

```text
intent_classification
requirement_extraction
ambiguity_detection
smart_question_generation
safe_default_selection
confidence_scoring
persona_definition
target_user_definition
product_goal_definition
functional_requirement_generation
nonfunctional_requirement_generation
acceptance_criteria_generation
acceptance_contract_generation
scope_detection
feature_prioritization
risk_identification
constraint_extraction
dependency_analysis
```

## Planning

```text
build_plan_generation
milestone_generation
task_decomposition
task_dependency_generation
critical_path_detection
effort_estimation
cost_estimation
capability_closure
agent_assignment
parallelization_planning
risk_adjusted_planning
```

## Architecture

```text
stack_selection
frontend_architecture
backend_architecture
database_architecture
auth_architecture
integration_architecture
storage_architecture
queue_architecture
cache_architecture
deployment_architecture
multi_tenant_architecture
api_contract_design
data_model_design
event_model_design
scalability_design
failure_mode_design
```

## UX/UI

```text
information_architecture
user_flow_design
wireframe_generation
responsive_layout
design_system_generation
design_token_generation
component_selection
form_design
navigation_design
empty_state_design
error_state_design
loading_state_design
mobile_layout
dashboard_design
accessibility_design
rtl_design
```

## Frontend

```text
page_generation
component_generation
form_generation
client_validation
state_management
api_binding
auth_ui
responsive_implementation
rtl_implementation
loading_ui
error_ui
navigation_implementation
table_generation
dashboard_generation
file_upload_ui
frontend_error_boundary
browser_storage
frontend_test_generation
```

## Backend

```text
api_endpoint_generation
request_validation
business_logic_generation
service_layer_generation
repository_layer_generation
authorization_enforcement
background_job_generation
webhook_receiver
webhook_sender
rate_limit_enforcement
server_error_handling
idempotency
transaction_handling
pagination
filtering
search_backend
file_upload_backend
```

## Database

```text
schema_generation
migration_generation
migration_validation
index_design
query_generation
query_optimization
transaction_design
data_integrity_validation
foreign_key_design
seed_data_generation
persistence_verification
data_isolation
scratch_database_generation
data_upgrade
data_rollback
backup_generation
restore_validation
```

## Authentication

```text
signup
login
logout
session_management
google_oauth
apple_oauth
email_verification
password_reset
role_management
permission_management
account_deletion
account_export
mfa_readiness
auth_security_validation
```

## Integration

```text
api_connector_generation
oauth_connector
api_key_connector
webhook_connector
integration_health_check
credential_validation
rate_limit_handling
integration_retry
integration_timeout
provider_fallback
payload_mapping
external_error_normalization
```

## Coding

```text
file_create
file_modify
safe_refactor
dependency_add
dependency_remove
import_fix
type_fix
lint_fix
config_update
environment_config
code_cleanup
dead_code_detection
duplicate_code_detection
repository_diff_generation
repository_patch_application
```

## QA

```text
unit_test_generation
unit_test_execution
contract_test
integration_test_generation
integration_test_execution
e2e_test_generation
e2e_execution
regression_test
negative_test
edge_case_test
api_test
auth_test
permission_test
persistence_test
migration_test
rollback_test
cost_test
provider_failure_test
restart_test
resume_test
cancellation_test
behavioral_acceptance_test
requirement_traceability_test
```

## Browser

```text
browser_launch
page_load_test
click_test
form_test
navigation_test
mobile_view_test
desktop_view_test
responsive_test
javascript_error_detection
network_error_detection
browser_persistence_test
reload_test
browser_acceptance_test
```

## Repair

```text
failure_classification
root_cause_analysis
repair_plan_generation
minimal_patch_generation
repair_execution
repair_verification
regression_after_repair
retry_decision
escalation_decision
```

## Security

```text
secret_detection
secret_exposure_check
dependency_vulnerability_scan
xss_check
csrf_check
sql_injection_check
ssrf_check
auth_bypass_check
permission_escalation_check
insecure_storage_check
unsafe_endpoint_check
security_header_check
preview_access_check
security_release_gate
```

## Compliance

```text
commercial_provider_validation
model_license_validation
commercial_output_validation
embedded_saas_validation
copyright_risk_detection
license_requirement_detection
user_consent_logging
ip_warning_generation
commercial_use_policy_check
provider_terms_check
content_takedown_support
```

## Provider Routing

```text
capability_provider_match
provider_health_check
provider_cost_compare
provider_quality_compare
provider_latency_compare
commercial_permission_check
privacy_policy_check
provider_selection
provider_fallback_selection
provider_retry
model_selection
```

## Economics

```text
build_quote
credit_reservation
agent_budget_assignment
provider_budget_assignment
usage_metering
provider_price_lookup
actual_cost_calculation
credit_settlement
unused_reservation_release
margin_calculation
cost_anomaly_detection
budget_guard
budget_escalation
reconciliation
```

## Infrastructure

```text
worker_health_check
queue_health_check
storage_health_check
database_health_check
environment_validation
runtime_validation
resource_allocation
queue_job_submit
job_resume
job_cancel
job_timeout
stale_job_recovery
```

## Deployment

```text
preview_prepare
preview_deploy
preview_health_check
preview_access_protect
preview_token_issue
preview_token_revoke
production_prepare
production_deploy
deployment_status_check
environment_binding
deployment_rollback
deployment_verification
```

## Release

```text
version_create
artifact_commit
release_evidence_generation
release_candidate_validation
release_gate
release_publish
rollback_point_create
release_rollback
```

## Observability

```text
execution_trace
agent_trace
skill_trace
provider_trace
cost_trace
failure_trace
latency_measurement
health_metric
structured_logging
incident_creation
```

## Backup / Recovery

```text
database_backup
artifact_backup
project_backup
backup_validation
restore_database
restore_project
restore_artifact
restore_verification
disaster_recovery_test
```

## Performance

```text
frontend_performance_test
backend_performance_test
database_performance_test
bundle_analysis
slow_query_detection
latency_analysis
memory_analysis
concurrency_test
load_test
```

## Accessibility

```text
keyboard_navigation_test
semantic_html_test
label_test
contrast_test
touch_target_test
screen_reader_structure_test
focus_order_test
```

## Localization

```text
translation
hebrew_localization
rtl_layout
ltr_layout
locale_date
locale_currency
locale_number
translation_validation
missing_translation_detection
```

## SEO

```text
metadata_generation
title_generation
description_generation
canonical_generation
sitemap_generation
robots_generation
opengraph_generation
structured_data_generation
seo_validation
```

## Analytics

```text
event_schema_generation
event_tracking
funnel_definition
usage_metric
conversion_metric
error_metric
feature_usage_metric
```

## Media — Image

```text
text_to_image
image_to_image
image_edit
background_remove
image_upscale
image_variation
character_consistency
brand_consistency
thumbnail_generation
image_quality_check
```

## Media — Video

```text
video_brief
script_generation
storyboard_generation
shot_list_generation
text_to_video
image_to_video
video_to_video
scene_generation
scene_continuity
lip_sync
caption_generation
video_composition
video_render
video_quality_check
```

## Voice

```text
text_to_speech
speech_to_text
voice_selection
voice_clone_where_licensed
voice_localization
speech_quality_check
```

## Audio / Music

```text
music_generation
sound_effect_generation
audio_mix
audio_normalization
music_license_check
```

## Automation

```text
trigger_definition
schedule_definition
webhook_trigger
action_definition
workflow_branch
workflow_condition
workflow_retry
workflow_state
workflow_audit
workflow_test
```

## 2D Games

```text
game_concept
game_loop_design
genre_rules
player_movement
player_input
collision
physics_2d
enemy_ai_2d
npc_2d
health_system
damage_system
score_system
inventory
item_system
upgrade_system
shop_system
quest_system
dialogue_system
level_system
checkpoint_system
save_system
load_system
progression_system
difficulty_system
boss_system
spawn_system
camera_2d
animation_2d
sprite_management
tileset_management
audio_game
hud
pause_menu
game_over
restart
leaderboard
touch_controls
keyboard_controls
gameplay_test
level_completion_test
save_load_test
```

---

# 10. EVERY SKILL MUST KNOW EXACTLY WHAT IT IS

Every Skill record must contain:

```text
skill_key
name
version
category

purpose
unique_responsibility

when_used
when_not_used
trigger_conditions

required_inputs
optional_inputs
outputs

preconditions
postconditions

dependencies

primary_agent
secondary_agent
verifier_agent

supported_targets

providers
cheap_provider
standard_provider
premium_provider
fallback_provider

estimated_cost_model

permissions
security_constraints
commercial_constraints
data_policy

implementation_location

verification_method
quality_metrics
success_criteria
failure_modes

retry_policy
fallback_policy

status
last_verified_at
last_verified_commit
```

A Skill with only a name and description is NOT considered implemented.

---

# 11. DEPENDENCY CLOSURE

Before any build, modification, automation, media generation or 2D game generation:

resolve all required capabilities.

Example:

```text
"Build a Hebrew appointment SaaS"
```

must resolve dependencies such as:

```text
frontend
backend
database
forms
persistence
rtl
browser QA
behavioral acceptance
preview
cost accounting
...
```

The system must produce:

```text
AVAILABLE
PARTIAL
MISSING
BLOCKED
```

for every required capability.

It must never guess that a feature exists simply because an Agent name exists.

---

# 12. DURABLE AGENT EXECUTION

Implement/finish:

```text
AgentRuntime
TaskGraph
AgentHandoff
CapabilityResolver
PermissionEngine
BudgetEngine
AgentMemory
AgentEvidenceStore
VerificationEngine
```

Task states:

```text
PENDING
READY
RUNNING
WAITING
BLOCKED
VERIFYING
REPAIRING
SUCCEEDED
FAILED
CANCEL_REQUESTED
CANCELLED
```

Task state must survive process/server/worker restart.

---

# 13. SEPARATION OF DUTIES

Critical work cannot self-approve.

Examples:

```text
Coding Agent
→ Code Review Agent
→ QA Agent
```

```text
Deployment Agent
→ Release Agent
```

```text
Migration Agent
→ QA + Backup/Recovery verification
```

```text
Provider Router
→ Compliance commercial check
```

```text
2D Game Engineering
→ 2D Game QA
```

---

# 14. BUILD A SELF-TESTING PLATFORM

This is a major architectural requirement.

Every meaningful change to 148AI itself should automatically answer:

> Did this change improve the platform without breaking anything that already worked?

Implement a versioned:

```text
PLATFORM_CAPABILITY_MATRIX
PLATFORM_REGRESSION_MATRIX
GOLDEN_E2E_MATRIX
FAILURE_INJECTION_MATRIX
```

For every major capability record:

```text
capability
expected behavior
test layer
test location
last result
last verified commit
last verified environment
evidence
```

---

# 15. CONTINUOUS SELF-VERIFICATION LOOP

After every implementation batch:

```text
Implement
→ Static Checks
→ Unit
→ Contract
→ Integration
→ Database
→ Worker/Queue
→ API
→ Browser
→ Behavioral Acceptance
→ Golden E2E
→ Failure Injection where relevant
→ Regression Comparison
→ Repair
→ Repeat
```

Do not continue to the next major batch with a new critical regression.

---

# 16. REAL GOLDEN SCENARIOS

Run actual end-to-end scenarios.

At minimum:

### Golden 1 — New SaaS

Hebrew-first business SaaS with:

* discovery
* no unnecessary questions
* persistent DB
* responsive dashboard
* forms
* preview
* restart persistence
* version persistence

### Golden 2 — SaaS with Authentication

Google/email auth where configured.

### Golden 3 — Existing Project Modification

Modify existing project without damaging unrelated behavior.

### Golden 4 — Cancellation

Queued and active build.

### Golden 5 — Crash Recovery

Kill/restart worker and recover execution.

### Golden 6 — Provider Failure

Primary AI provider fails and approved fallback continues.

### Golden 7 — Budget Guard

Attempted cost exceeds budget and execution handles correctly.

### Golden 8 — Backup / Restore

Backup real synthetic project → remove test copy → restore → verify checksums/functionality.

### Golden 9 — Automation

Generate and test a basic workflow.

### Golden 10 — Media

Generate approved media through commercial-safe provider.

### Golden 11 — 2D Game

Generate a small real Phaser game and play it in browser.

Must test:

* controls
* collision
* scoring
* completion
* restart
* mobile input
* browser errors

---

# 17. MAXIMUM QUALITY LOOP

Do not stop after the first successful E2E.

After Golden scenarios pass:

1. inspect weaknesses
2. identify repeated failure classes
3. harden implementation
4. improve tests
5. reduce unnecessary provider calls
6. reduce cost
7. improve latency
8. improve repair precision
9. improve UI error communication
10. rerun Golden suite

Continue until additional iterations produce diminishing material benefit or encounter a hard external blocker/budget boundary.

---

# 18. TEST BUDGET

Use the existing approved test budget carefully.

Prefer:

* deterministic local tests
* synthetic real-server tests
* free provider checks
* minimal paid E2E runs

For paid model execution:

* use hard per-run ceilings
* record exact provider usage
* record exact cost
* avoid duplicate expensive runs when unchanged evidence already exists

Do not exceed the remaining approved test budget.

---

# 19. COMMERCIAL PROVIDER SAFETY

Provider/model approval must be evaluated at:

```text
provider
model
endpoint
plan
```

States:

```text
COMMERCIAL_APPROVED
CONDITIONAL
DEV_ONLY
BLOCKED
```

Paying customer traffic may use only:

```text
COMMERCIAL_APPROVED
```

or explicitly satisfied `CONDITIONAL` cases.

Never route commercial customer work to DEV_ONLY/BLOCKED.

---

# 20. DO NOT BUILD HEAVY 3D NOW

Current product scope:

* Web/SaaS
* applications
* agents
* automation
* media
* 2D games

3D assets may remain experimental/future capability.

Do not spend current core engineering effort on:

* GTA-like
* open world
* MMORPG 3D
* AAA game creation
* massive procedural 3D worlds

---

# 21. MIGRATION STRATEGY

Do not replace working production paths in one shot.

Use:

```text
audit
→ adapter
→ shadow/feature-flag
→ verify
→ switch
→ remove obsolete path only after evidence
```

No giant rewrite.

Reuse existing modules whenever technically sound.

---

# 22. COMPLETION POLICY

Do NOT stop after saying:

* “agents created”
* “registry updated”
* “tests green”
* “browser loads”
* “build ready”

Those are intermediate states.

A capability becomes verified only when the entire promised outcome works.

---

# 23. FINAL DEFINITION OF DONE

This program can be considered complete only when:

* current P0 real-server failures are resolved
* Behavioral Acceptance feeds Repair
* requirement-aware acceptance works
* actual-cost settlement works
* private preview access works
* crash recovery works
* backup + restore works
* build + modification parity exists
* AgentRuntime is real
* TaskGraph is durable
* agent handoffs are structured
* permissions are enforced
* budgets are enforced
* provider commercial rules are enforced
* registries are runtime truth
* Skills are executable
* independent verification exists
* Platform Capability Auditor works
* Regression Guardian works
* Golden Path Verifier works
* System Test Orchestrator works
* Failure Injection Agent works
* Quality Gate works
* Golden E2E scenarios pass
* no critical regression remains
* no fake production path remains

---

# 24. FINAL REPORT

When you have pushed the system as far as possible, give the founder one consolidated report.

Include:

```text
starting_commit
final_commit
pre_staging_commit
rollback_commit

migrations_added

agents_total
agents_live
agents_partial
agents_not_configured
agents_not_implemented
agents_blocked

skills_total
skills_live
skills_partial
skills_not_configured
skills_not_implemented
skills_blocked

capabilities_verified

tests_total
tests_passed
tests_failed
tests_skipped

golden_e2e_results
browser_results
behavioral_results
failure_injection_results
backup_restore_result
crash_recovery_result
provider_fallback_result

actual_paid_test_cost
remaining_test_budget

regressions_found
regressions_repaired
remaining_regressions

security_findings
commercial_provider_findings

known_limitations
external_blockers

exact remaining work before:
PRE_STAGING_READY
PRIVATE_BETA_READY
PUBLIC_BETA_READY
PRODUCTION_READY
```

Update all sources of truth:

```text
STATUS.md
MASTER_AGENTS_REGISTRY
MASTER_SKILLS_REGISTRY
PLATFORM_CAPABILITY_MATRIX
PLATFORM_REGRESSION_MATRIX
GOLDEN_E2E_MATRIX
```

---

# FINAL COMMAND

You have authorization to continue.

Do not ask for routine approval.

Do not stop at the next error.

Do not optimize for impressive status reports.

Do not mark incomplete work as LIVE.

Use the repository and real evidence as truth.

Preserve what works.

Fix what fails.

Verify every major result.

Repair and repeat.

Continue autonomously until the platform reaches the maximum verified quality achievable with the current infrastructure, credentials and approved budget, or until you hit a genuine external hard blocker.

---

### מה הוספתי לו עכשיו מעבר למה שכבר נתנו

הוספתי **6 שכבות קריטיות** שלא הייתי רוצה שחסרות במערכת שלנו:

* **Behavioral Acceptance Agent** — בודק שהמוצר לא רק נפתח, אלא באמת עושה מה שהלקוח ביקש.
* **Platform Capability Auditor** — בודק שהמערכת לא טוענת שיש לה יכולות שאין לה.
* **Regression Guardian** — מוודא שכל שינוי שאנחנו עושים ב־148AI לא שובר משהו ישן.
* **Golden Path Verifier** — בונה מוצרים אמיתיים שוב ושוב כדי לבדוק את כל 148AI מקצה לקצה.
* **Failure Injection Agent** — בכוונה מכבה ספק, worker, DB וכו' ובודק אם המערכת יודעת להתאושש.
* **Quality Gate Agent** — האחרון בשרשרת; לא מאפשר לסמן milestone כמאומת בלי ראיות.

כלומר אנחנו עוברים ממערכת ש**בודקת את המוצר שהיא מייצרת**, למערכת שגם **בודקת את עצמה בזמן שאנחנו בונים ומשנים אותה**.

זה בדיוק מה שחסר בפרויקט בגודל הזה. אם קלאוד יבצע את המפרט הזה באמת ולא רק יוסיף שמות ל־Registry, תהיה לנו שכבת הנדסה הרבה יותר רצינית.
