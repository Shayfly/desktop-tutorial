# 148AI Capability Matrix — Machine Truth Lock

> Generated from canonical code. Do not edit by hand.
> Source presence, an enum, a plan, or an API key alone is never evidence that a capability is LIVE.

| Capability | Family | Status | Provider-backed | Dependencies |
|---|---|---|---:|---|
| `software.plan` | `software` | **PARTIAL** | yes | — |
| `software.architecture` | `software` | **PARTIAL** | yes | `software.plan` |
| `software.code.generate` | `software` | **PARTIAL** | yes | `software.architecture` |
| `software.code.modify` | `software` | **PARTIAL** | yes | — |
| `software.dependencies.install` | `software` | **PARTIAL** | no | `software.code.generate` |
| `software.build` | `software` | **PARTIAL** | no | `software.dependencies.install` |
| `software.test` | `software` | **PARTIAL** | no | `software.build` |
| `software.repair` | `software` | **PARTIAL** | yes | `software.test` |
| `software.preview` | `software` | **PARTIAL** | no | `software.build` |
| `software.export` | `software` | **PARTIAL** | no | `software.test` |
| `software.deploy.web` | `software` | **PARTIAL** | no | `software.export` |
| `target.web` | `target` | **PARTIAL** | no | — |
| `target.saas` | `target` | **PARTIAL** | no | — |
| `target.backend` | `target` | **PARTIAL** | no | — |
| `target.database` | `target` | **PARTIAL** | no | — |
| `target.android.source` | `target` | **PARTIAL** | no | — |
| `target.android.build` | `target` | **PARTIAL** | no | — |
| `target.ios.source` | `target` | **PARTIAL** | no | — |
| `target.ios.build` | `target` | **PARTIAL** | no | — |
| `target.desktop.source` | `target` | **NOT_IMPLEMENTED** | no | — |
| `target.agent` | `target` | **NOT_IMPLEMENTED** | no | — |
| `target.automation` | `target` | **NOT_IMPLEMENTED** | no | — |
| `target.game.2d` | `target` | **PARTIAL** | no | — |
| `target.game.3d` | `target` | **PARTIAL** | no | — |
| `media.image.generate` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.image.edit` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.image.remove_background` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.image.upscale` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.vector.generate` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.texture.generate` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.sprite.generate` | `media.2d` | **NOT_CONFIGURED** | yes | — |
| `media.3d.mesh.generate` | `media.3d` | **NOT_CONFIGURED** | yes | — |
| `media.3d.texture` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate` |
| `media.3d.multiview` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate` |
| `media.3d.retopology` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate` |
| `media.3d.optimize` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate` |
| `media.3d.rig` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate` |
| `media.3d.animate` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.rig` |
| `media.3d.retarget` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.rig` |
| `media.3d.export` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate` |
| `media.3d.scene.compose` | `media.3d` | **NOT_CONFIGURED** | yes | `media.3d.mesh.generate`, `media.3d.texture` |
| `media.audio.sfx` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.audio.music` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.audio.tts` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.audio.stt` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.audio.realtime_voice` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.audio.dubbing` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.audio.cleanup` | `media.audio` | **NOT_CONFIGURED** | yes | — |
| `media.video.generate` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.video.edit` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.video.lipsync` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.video.captions` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.video.upscale` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.film.storyboard` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.film.shot_plan` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `media.film.render` | `media.video` | **NOT_CONFIGURED** | yes | — |
| `ai.embedding` | `ai` | **NOT_CONFIGURED** | yes | — |
| `ai.rag.ingest` | `ai` | **NOT_CONFIGURED** | yes | — |
| `ai.rag.retrieve` | `ai` | **NOT_CONFIGURED** | yes | `ai.rag.ingest` |
| `ai.agent.tools` | `ai` | **NOT_CONFIGURED** | yes | — |
| `ai.agent.memory` | `ai` | **NOT_CONFIGURED** | yes | — |
| `ai.agent.eval` | `ai` | **NOT_CONFIGURED** | yes | — |
| `integration.payment` | `integration` | **PARTIAL** | no | — |
| `integration.email` | `integration` | **PARTIAL** | no | — |
| `integration.sms` | `integration` | **PARTIAL** | no | — |
| `integration.messaging` | `integration` | **PARTIAL** | no | — |
| `integration.maps` | `integration` | **PARTIAL** | no | — |
| `integration.storage` | `integration` | **PARTIAL** | no | — |
| `integration.database` | `integration` | **PARTIAL** | no | — |
| `integration.source_control` | `integration` | **PARTIAL** | no | — |
| `integration.oauth` | `integration` | **PARTIAL** | no | — |
| `integration.analytics` | `integration` | **PARTIAL** | no | — |
| `integration.webhook` | `integration` | **PARTIAL** | no | — |
| `publish.web` | `publish` | **PARTIAL** | no | — |
| `publish.android` | `publish` | **NOT_CONFIGURED** | no | — |
| `publish.ios` | `publish` | **NOT_CONFIGURED** | no | — |
| `publish.asset` | `publish` | **NOT_CONFIGURED** | no | — |
| `ecosystem.discover` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.creator_profile` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.like` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.comment` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.follow` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.remix` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.marketplace` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `ecosystem.revenue_share` | `ecosystem` | **NOT_IMPLEMENTED** | no | — |
| `game.multiplayer` | `game` | **NOT_IMPLEMENTED** | no | — |
| `game.matchmaking` | `game` | **NOT_IMPLEMENTED** | no | `game.multiplayer` |

## Status semantics

- `LIVE`: verified against the intended production path with current evidence.
- `PARTIAL`: meaningful implementation exists but the full production contract is not yet verified.
- `NOT_CONFIGURED`: implementation/contract may exist, but required provider/runtime configuration is absent.
- `NOT_IMPLEMENTED`: canonical product scope exists but execution is not implemented.
- `BLOCKED`: an explicit dependency, policy, budget, or external gate prevents execution.
