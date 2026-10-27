# 148AI Master Agents Registry — Machine Truth Lock

> Generated from `omni_prod.agents_registry`; do not edit by hand.

| Agent | Role | Status | Allowed skills | Agent dependencies |
|---|---|---|---:|---|
| `agent.chief_orchestrator` | Chief Orchestrator | **PARTIAL** | 11 | — |
| `agent.venice` | Venice (understanding -> planning) | **PARTIAL** | 4 | `agent.chief_orchestrator` |
| `agent.plan_verifier` | Plan Verifier | **PARTIAL** | 1 | `agent.venice` |
| `agent.clarification` | Clarification Agent | **NOT_IMPLEMENTED** | 1 | `agent.chief_orchestrator` |
| `agent.capability_planner` | Capability Planner | **PARTIAL** | 1 | `agent.chief_orchestrator` |
| `agent.cost_planner` | Cost Planner | **PARTIAL** | 2 | `agent.chief_orchestrator` |
| `agent.design_director` | Design Director | **NOT_IMPLEMENTED** | 4 | `agent.chief_orchestrator` |
| `agent.code` | Code Agent | **PARTIAL** | 5 | `agent.chief_orchestrator` |
| `agent.backend` | Backend Agent | **PARTIAL** | 5 | `agent.chief_orchestrator` |
| `agent.infrastructure` | Infrastructure Agent | **NOT_IMPLEMENTED** | 5 | `agent.chief_orchestrator` |
| `agent.integration` | Integration Agent | **NOT_IMPLEMENTED** | 12 | `agent.chief_orchestrator` |
| `agent.asset_director` | Asset Director | **NOT_IMPLEMENTED** | 6 | `agent.chief_orchestrator` |
| `agent.three_d` | 3D Agent | **NOT_IMPLEMENTED** | 10 | `agent.chief_orchestrator` |
| `agent.game_director` | Game Director | **NOT_IMPLEMENTED** | 3 | `agent.chief_orchestrator` |
| `agent.world_builder` | World Builder | **NOT_IMPLEMENTED** | 3 | `agent.chief_orchestrator` |
| `agent.mission_designer` | Mission Designer | **NOT_IMPLEMENTED** | 1 | `agent.chief_orchestrator` |
| `agent.animation` | Animation Agent | **NOT_IMPLEMENTED** | 3 | `agent.chief_orchestrator` |
| `agent.audio_director` | Audio Director | **NOT_IMPLEMENTED** | 7 | `agent.chief_orchestrator` |
| `agent.qa` | QA Agent | **PARTIAL** | 2 | `agent.chief_orchestrator` |
| `agent.playtester` | Playtester Agent | **NOT_IMPLEMENTED** | 3 | `agent.chief_orchestrator` |
| `agent.visual_qa` | Visual QA Agent | **NOT_IMPLEMENTED** | 1 | `agent.chief_orchestrator` |
| `agent.performance` | Performance Agent | **NOT_IMPLEMENTED** | 1 | `agent.chief_orchestrator` |
| `agent.security` | Security Agent | **PARTIAL** | 1 | `agent.chief_orchestrator` |
| `agent.compliance` | Compliance Agent | **NOT_IMPLEMENTED** | 1 | `agent.chief_orchestrator` |
| `agent.repair` | Repair Agent | **PARTIAL** | 3 | `agent.chief_orchestrator` |
| `agent.deployment` | Deployment Agent | **NOT_IMPLEMENTED** | 5 | `agent.chief_orchestrator` |
| `agent.cost_auditor` | Cost Auditor | **PARTIAL** | 1 | `agent.chief_orchestrator` |

Agent skill references and dependency cycles are validated in code and CI tests.
