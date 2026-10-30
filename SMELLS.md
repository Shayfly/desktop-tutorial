

## A1 — כסף: float מול Decimal

```
-- float( --
./omni_prod/active_jobs.py:174:        wait, poll = float(arg('--wait-minutes', 0.0)), float(arg('--poll-seconds', 30.0))
./omni_prod/attachments.py:139:            x, y, w, h = (int(round(float(r[k]))) for k in ('x', 'y', 'w', 'h'))
./omni_prod/capability_repository.py:231:        expires = float(row.get("lease_expires_at") or 0)
./omni_prod/capability_repository.py:321:                lease_expires_at=(None if row.get("lease_expires_at") is None else float(row["lease_expires_at"])),
./omni_prod/capability_repository.py:535:            lease_expires_at=(None if expires is None else float(expires)),
./omni_prod/config.py:15:def _float(name: str, default: float) -> float:
./omni_prod/config.py:17:    return float(raw) if raw else default
./omni_prod/config.py:69:            db_pool_timeout_seconds=_float("OMNI_DB_POOL_TIMEOUT_SECONDS", 10.0),
./omni_prod/config.py:71:            redis_socket_timeout_seconds=_float("OMNI_REDIS_SOCKET_TIMEOUT_SECONDS", 5.0),
./omni_prod/config.py:72:            redis_connect_timeout_seconds=_float("OMNI_REDIS_CONNECT_TIMEOUT_SECONDS", 5.0),
./omni_prod/economics_report.py:199:               'seconds': float(r[5]) if r[5] is not None else None, 'repairs': r[6], 'settled': r[7],
./omni_prod/intake/contract.py:123:            if float(c.cost_constraints['max_usd']) < 0:
./omni_prod/intake/lanes.py:46:            float(bench.get('accuracy') or 0) >= 0.95 and bench.get('sensitive_false_negatives') == 0):
./omni_prod/intake/worker_route.py:48:        self.wait = float(os.getenv('OMNI_INTAKE_WAIT_SECONDS', '8')) if wait_seconds is None else wait_seconds
./omni_prod/intelligence/health.py:182:            wait = timedelta(seconds=float(hint)) if hint else RATE_COOLDOWN * min(failures, 8)
./omni_prod/model_catalog.py:131:            timeout = float(item.get('timeout_seconds', 120))
./omni_prod/model_gateway.py:56:        return max(0.0, float(value)) if value is not None else None
./omni_prod/model_runtime_config.py:34:            timeout_seconds=float(os.getenv('OMNI_LOCAL_MODEL_TIMEOUT', '120')),
./omni_prod/model_runtime_config.py:59:                    timeout_seconds=float(item.get('timeout_seconds', 120)),
./omni_prod/planning/router.py:36:                                   else 0, float((m.get('price_in_force') or {}).get('output_per_million') or 1e9)))
./omni_prod/product_analytics.py:35:        median_repair_rounds=float(median([m.repair_rounds for m in metrics])),
./omni_prod/providers/image_provider.py:418:                self.sleep(min(float(wait), self.max_rate_limit_wait_seconds))
./omni_prod/provider_router.py:190:            return float(value or 0)
./omni_prod/redis_circuit_breaker.py:37:        opened_at = float(get("opened_at", 0) or 0)
./omni_prod/redis_circuit_breaker.py:38:        blocked_until = float(get("blocked_until", 0) or 0)
./omni_prod/redis_circuit_breaker.py:77:        recovery = self.policy.recovery_seconds if recovery_seconds is None else float(recovery_seconds)
./omni_prod/verification_contract.py:174:    return float(v)
./omni_prod/visual_edit.py:52:        rect = {k: round(float(rect.get(k, 0)), 1) for k in ('x', 'y', 'w', 'h')}
./omni_prod/web_saas_acceptance.py:202:        self.timeout_seconds = float(timeout_seconds)
./omni_prod/web_saas_acceptance.py:247:                        timeout_seconds=float(step.get('timeout_seconds', self.timeout_seconds)),
./omni_prod/worker_tasks.py:1524:        probe_timeout=float(os.getenv('OMNI_PREVIEW_HEALTH_TIMEOUT_SECONDS', '30')),
./scripts/run_v28_release_gate.py:73:    margin_detail[code.value] = None if margin is None else float(margin)
./scripts/run_v28_release_gate.py:74:    ok &= check(f'{code.value}_variable_margin_floor', margin is not None and float(margin) >= floor,
./tests/m4d2b_worker_process.py:68:    burst_timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
./tests/test_deployment_verification.py:158:            'nan timestamp': {'finished_at': float('nan')},
./tests/test_deployment_verification.py:159:            'inf timestamp': {'finished_at': float('inf')},
-- Decimal( --
679
-- round( --
./omni_prod/attachments.py:139:            x, y, w, h = (int(round(float(r[k]))) for k in ('x', 'y', 'w', 'h'))
./omni_prod/benchmark_suite.py:94:        return {'cases':total,'ready':ready,'success_rate':round(ready/total,4) if total else 0,
./omni_prod/economics_report.py:34:    k = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
./omni_prod/economics_report.py:85:        'success_rate': (round(len(ready) / len([r for r in measured if r['status'] in ('ready', 'failed')]), 3)
./omni_prod/economics_report.py:90:        'cost_per_build_avg_usd': str(round(statistics.mean(all_costs), 6)) if all_costs else None,
./omni_prod/economics_report.py:93:        'cost_per_successful_build_usd': (str(round(sum((r['metered'] for r in measured), Decimal('0')) / len(ready), 6))
./omni_prod/economics_report.py:96:        'repair_share_of_spend': (str(round(total_repair / total_metered, 3)) if total_metered else None),
./omni_prod/economics_report.py:101:                       'success_rate': round(v['ok'] / v['calls'], 3) if v['calls'] else None}
./omni_prod/economics_report.py:122:    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]
./omni_prod/economics_report.py:158:            'builds': n, 'verified_successes': k, 'success_rate': round(k / n, 3) if n else None,
./omni_prod/economics_report.py:161:            'cost_per_verified_success_usd': str(round(g['cost'] / k, 6)) if k else None,
./omni_prod/economics_report.py:171:                                      'call_success_rate': round(v['ok'] / v['calls'], 3) if v['calls'] else None}
./omni_prod/gate_replay.py:135:                             'seconds': round(time.monotonic() - t0), 'policy': policy['decision'],
./omni_prod/human_evaluation.py:16:    return {'responses':len(items),'satisfaction_rate':round(sum(x.satisfied for x in items)/len(items),4),'avg_score':round(sum(x.score for x in items)/len(items),2)}
./omni_prod/intake/benchmark.py:40:            'field_recall': round(tp / max(tp + fn, 1), 3), 'wrong_values': wrong, 'hallucinations': halluc,
./omni_prod/intake/benchmark.py:41:            'family_accuracy': round(fam_ok / max(n, 1), 3), 'delegate_accuracy': round(deleg_ok / max(n, 1), 3),
./omni_prod/model_probe.py:44:        row['seconds'] = round(time.monotonic() - started, 1)
./omni_prod/product_analytics.py:28:    idx=min(len(durations)-1, max(0, int(round((len(durations)-1)*0.95))))
./omni_prod/product_analytics.py:32:        success_rate=round(len(ready)/len(metrics),4),
./omni_prod/product_analytics.py:36:        avg_cost_per_ready_usd=round(sum(m.cost_usd for m in ready)/len(ready),6) if ready else 0,
./omni_prod/product_analytics.py:37:        avg_quality_score=round(sum(m.quality_score for m in metrics)/len(metrics),2),
./omni_prod/quality_gate.py:115:    score = int(round(weighted / total_weight)) if total_weight else 0
./omni_prod/rehearsal.py:63:    report.update(model_calls=calls, authorized_spend_usd=str(spent), seconds=round(time.monotonic() - started))
./omni_prod/release_policy.py:218:                  f'{unresolved} unresolved blocking finding(s) after {len(reviews)} review round(s)'))
./omni_prod/visual_edit.py:52:        rect = {k: round(float(rect.get(k, 0)), 1) for k in ('x', 'y', 'w', 'h')}
./omni_prod/visual_qa.py:76:    if (r.right > vw + 2 || r.left < -2) add('offscreen_control', el, 'x ' + Math.round(r.left) + '..' + Math.round(r.right));
./omni_prod/visual_qa.py:78:      add('small_touch', el, Math.round(r.width) + 'x' + Math.round(r.height));
./omni_prod/visual_qa.py:93:    if (w > 4 && h > 4) add('overlap', a, 'overlaps ' + b.tagName.toLowerCase() + ' by ' + Math.round(w) + 'x' + Math.round(h));
./omni_prod/worker_tasks.py:534:            f'build did not pass sandbox verification after {getattr(result, "repair_rounds", "?")} repair round(s)'
./scripts/run_http_load.py:16:payload={'url':URL,'requests':REQUESTS,'concurrency':CONCURRENCY,'ok':ok,'errors':REQUESTS-ok,'success_rate':round(ok/REQUESTS,4) if REQUESTS else 0,'p95_ms':p95,'rps':round(REQUESTS/elapsed,2) if elapsed else 0}
./scripts/run_v25_offline_benchmark.py:33:payload={'engine':'V25 Unified Core deterministic/offline baseline','cases':len(rows),'passed':passed,'failed':len(rows)-passed,'success_rate':round(passed/len(rows),4) if rows else 0,'p95_duration_ms':p95,'wall_ms':int((time.monotonic()-started)*1000),'by_category':by,'results':rows,'truth_note':'This benchmark exercises deterministic V25 planning/repository/runtime contracts without a live GPU model or Docker execution.'}
./scripts/run_v28_offline_benchmark.py:28:payload={'engine':'148AI V28 deterministic/offline commercial-shell benchmark','cases':len(rows),'passed':passed,'failed':len(rows)-passed,'success_rate':round(passed/len(rows),4),'p95_ms':p95,'wall_ms':int((time.monotonic()-started)*1000),'results':rows,'truth_note':'This verifies deterministic V28 build/rights/branding/quality/security contracts. It does not claim a live GPU model, live media provider or live Docker sandbox.'}
./tests/test_economics_report.py:28:        self.assertEqual(self.r['success_rate'], round(2 / 3, 3))
./tests/test_modifier_engine.py:131:    def test_missing_requirement_applies_after_one_repair_round(self):
-- int( על כסף --
```


## A2 — כסף: עדכון יתרה

```
-- עדכון ארנק/קרדיטים --
./omni_prod/billing.py:76:        self.balance -= decision.credits
./omni_prod/billing.py:82:        self.balance += amount; self.entries.append((reason, amount)); return self.balance
```


## A3 — מרוץ: check-then-act

```
-- FOR UPDATE --
./omni_prod/agent_os/runtime.py:84:                    'SELECT id FROM agent_runs WHERE subject_kind = %s AND subject_id = %s AND finished_at IS NULL FOR UPDATE',
./omni_prod/agent_os/runtime.py:128:                                   'FOR UPDATE', (task_id,)).fetchone()
./omni_prod/agent_os/runtime.py:160:                row = conn.execute('SELECT state, budget_usd, cost_usd, run_id FROM agent_tasks WHERE id = %s FOR UPDATE',
./omni_prod/attempt_ledger.py:279:                    cur.execute('SELECT status FROM build_jobs WHERE id=%s FOR UPDATE', (build_id,))
./omni_prod/attempt_ledger.py:283:                    cur.execute('SELECT status FROM credit_reservations WHERE build_id=%s FOR UPDATE', (build_id,))
./omni_prod/brief_repository.py:137:                    " budget_fingerprint, status, expires_at, used_by_build_id FROM build_approvals WHERE id = %s FOR UPDATE",
./omni_prod/build_contract_repository.py:77:                        # FOR UPDATE on aggregate rows, and the project lock serializes
./omni_prod/build_contract_repository.py:80:                            "SELECT id FROM creator_projects WHERE id=%s FOR UPDATE",
./omni_prod/build_control.py:149:                row = conn.execute("SELECT status FROM modification_requests WHERE id = %s AND project_id = %s FOR UPDATE",
./omni_prod/capability_repository.py:565:                        WHERE idempotency_key=%s FOR UPDATE
./omni_prod/capability_repository.py:625:                           WHERE idempotency_key=%s FOR UPDATE""",
./omni_prod/capability_repository.py:749:                           WHERE idempotency_key=%s FOR UPDATE""",
./omni_prod/idempotency.py:40:                    FOR UPDATE
./omni_prod/identity_lifecycle.py:360:                        "SELECT id,user_id FROM creator_identity_tokens WHERE token_hash=%s AND purpose=%s AND consumed_at IS NULL AND expires_at>%s FOR UPDATE",
./omni_prod/infrastructure_provisioner.py:136:                        "SELECT tenant_id FROM generated_app_bindings WHERE idempotency_key=%s FOR UPDATE",
./omni_prod/intake/budget.py:28:No aggregate is read FOR UPDATE; no lock is held during the provider call.
./omni_prod/intake/budget.py:248:            cur.execute('SELECT scope FROM intake_budget_scopes WHERE scope = %s FOR UPDATE', (scope,))
./omni_prod/intake/budget.py:421:                cur.execute('SELECT state FROM intake_reservations WHERE id = %s FOR UPDATE', (reservation_id,))
./omni_prod/intake/budget.py:507:                                'FOR UPDATE OF o SKIP LOCKED', (RESERVED, int(older_than_seconds)))
./omni_prod/job_repository.py:191:            FOR UPDATE OF idem
./omni_prod/job_repository.py:302:        with FOR UPDATE SKIP LOCKED so concurrent relays never double-claim a
./omni_prod/job_repository.py:319:                            FOR UPDATE SKIP LOCKED
./omni_prod/job_repository.py:339:                    cur.execute("SELECT status, phase FROM build_jobs WHERE id = %s FOR UPDATE", (build_id,))
./omni_prod/job_repository.py:378:                    cur.execute("SELECT status FROM build_jobs WHERE id = %s AND project_id = %s FOR UPDATE",
./omni_prod/maintenance.py:160:                                           'AND heartbeat_at < now() - make_interval(mins => %s) FOR UPDATE',
./omni_prod/modification_repository.py:136:        (one row per transaction, FOR UPDATE SKIP LOCKED, duplicate delivery
./omni_prod/modification_repository.py:151:                            FOR UPDATE SKIP LOCKED
./omni_prod/modification_repository.py:386:                            "WHERE id = %s AND project_id = %s FOR UPDATE",
./omni_prod/modification_repository.py:454:                        "SELECT status FROM modification_requests WHERE id=%s AND project_id=%s FOR UPDATE",
./omni_prod/outbox.py:62:            "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT %s"
./omni_prod/preview_repository.py:108:                        FOR UPDATE
./omni_prod/preview_repository.py:199:        lock = ' FOR UPDATE' if for_update else ''
./omni_prod/providers/image_provider.py:228:                            "FROM media_provider_submissions WHERE idempotency_key=%s FOR UPDATE",
./omni_prod/subscription_store.py:38:                                'WHERE account_id=%s FOR UPDATE', (event.user_id,))
./omni_prod/subscription_store.py:83:        suffix = ' FOR UPDATE' if for_update else ''
./omni_prod/subscription_store.py:200:                + ' FROM credit_reservations WHERE build_id=%s FOR UPDATE',
./omni_prod/subscription_store.py:242:        # Load user sub strictly for update
./omni_prod/subscription_store.py:243:        cur.execute('SELECT plan_code,cycle,credits_used,provider_spend_usd FROM creator_subscriptions WHERE user_id=%s FOR UPDATE', (user_id,))
./omni_prod/subscription_store.py:316:                    cur.execute("SELECT account_id, status, estimated_provider_cost_usd, funding_source FROM credit_reservations WHERE build_id=%s FOR UPDATE", (build_id,))
./omni_prod/subscription_store.py:352:                        cur.execute("SELECT plan_code, provider_spend_usd FROM creator_subscriptions WHERE user_id=%s FOR UPDATE", (user_id,))
./omni_prod/subscription_store.py:406:                    cur.execute("SELECT account_id, status, credits_reserved, estimated_provider_cost_usd, funding_source FROM credit_reservations WHERE build_id=%s FOR UPDATE", (build_id,))
./tests/test_intake_budget_pg.py:293:                        conn.execute('SELECT 1 FROM intake_budget_scopes WHERE scope = %s FOR UPDATE', (first,))
./tests/test_intake_budget_pg.py:295:                        conn.execute('SELECT 1 FROM intake_budget_scopes WHERE scope = %s FOR UPDATE', (second,))
./tests/test_intake_budget_pg.py:311:                if 'FOR UPDATE' in sql and 'intake_budget_scopes' in sql:
./tests/test_m3_preview_logic.py:783:        self.assertIn('FOR UPDATE', cur.executed[0][0])
./tests/test_m3_preview_logic.py:1061:        self.assertTrue(all('FOR UPDATE SKIP LOCKED' in s and 'enqueued_at IS NULL' in s for s in selects))
./tests/test_m4d2_live_postgres.py:466:      1. SELECT source_version_id, status FROM modification_requests ... FOR UPDATE
./tests/test_m4_acceptance.py:259:        full relay contract (FOR UPDATE SKIP LOCKED, one row per
./tests/test_m5_build_economics.py:106:        self.assertIn('FOR UPDATE', cur.calls[0][0])
./tests/test_m5_build_economics.py:211:        self.assertIn('FOR UPDATE OF idem', cur.calls[1][0])
./tests/test_m5_managed_web_saas_profile.py:422:        self.assertIn("FOR UPDATE", calls[0][0])
./tests/test_m5_web_saas_acceptance.py:289:        self.assertIn('FOR UPDATE', cur.executed[0][0])
./tests/test_modification_repository.py:257:        self.assertTrue(all('FOR UPDATE SKIP LOCKED' in s and 'enqueued_at IS NULL' in s for s in selects))
-- SELECT ואז UPDATE באותו קובץ --
omni_prod/agent_os/runtime.py
omni_prod/attachments.py
omni_prod/attempt_ledger.py
omni_prod/brief_repository.py
omni_prod/build_contract_repository.py
omni_prod/build_control.py
omni_prod/capability_repository.py
omni_prod/deployments.py
omni_prod/entitlements.py
omni_prod/idempotency.py
omni_prod/identity_lifecycle.py
omni_prod/infrastructure_provisioner.py
omni_prod/intake/budget.py
omni_prod/intelligence/health.py
omni_prod/job_repository.py
omni_prod/maintenance.py
omni_prod/modification_repository.py
omni_prod/outbox.py
omni_prod/postdeploy_checks.py
omni_prod/preview_access.py
omni_prod/preview_repository.py
omni_prod/project_lifecycle.py
omni_prod/providers/image_provider.py
omni_prod/subscription_store.py
```


## A4 — אידמפוטנטיות

```
./omni_prod/agents_registry.py:54:                raise ValueError(f"duplicate agent key: {definition.key}")
./omni_prod/agent_catalog.py:52:       'work advances without duplicates and state is persisted', 'agent.chief_orchestrator'),
./omni_prod/agent_catalog.py:155:       ('replay', 'duplicate delivery', 'timeout/retry tests'), 'no double action and failures are reproducible'),
./omni_prod/agent_catalog.py:198:assert len(BY_KEY) == len(CATALOG), 'duplicate agent role key'
./omni_prod/agent_os/truth_matrix.py:46:    PlatformCapability('contract_bound_approval', ('omni_prod.job_repository:PostgresBuildRepository.claim_contract_build',),
./omni_prod/attempt_ledger.py:258:    """Insert records idempotently (attempt_id primary key). Returns rows offered."""
./omni_prod/autonomous_agents.py:87:    'The plan is run against the real app inside the build and every failing step is sent back for repair, so its test data must be valid under the product\'s own rules (dates from today within the allowed window, phone numbers in local format, unique values where duplicates are refused) and expect_text_contains must quote text the page really shows. Never write a fixed calendar date in a step: use ${today}, ${date_plus_N} or ${date_minus_N} (N days from the day the plan runs), which the platform fills in. '
./omni_prod/benchmark_suite.py:30:    'automation': 'workflow automation system with triggers, actions, retries, idempotency, secrets and run history',
./omni_prod/benchmark_suite.py:41:    ('04','advanced','Add resilient background jobs, retries, idempotency and failure recovery.'),
./omni_prod/build_contract_repository.py:113:            if "unique" in text or "duplicate" in text:
./omni_prod/build_control.py:41:        # Writes the attempt ledger so far (idempotent). Called at every model
./omni_prod/build_state.py:32:# duplicated worker after a terminal state, or a step backwards, is ignored.
./omni_prod/capability_executor.py:87:    def _idempotency_key(build_id: str, requirement: CapabilityRequirement, assignment: CapabilityExecutionAssignment) -> str:
./omni_prod/capability_executor.py:242:        idempotency_key = self._idempotency_key(build_id, requirement, assignment)
./omni_prod/capability_executor.py:244:            attempt_id="att_" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:24],
./omni_prod/capability_executor.py:249:            idempotency_key=idempotency_key,
./omni_prod/capability_executor.py:257:        if not self.repository.claim_execution_attempt(
./omni_prod/capability_executor.py:258:            idempotency_key,
./omni_prod/capability_executor.py:265:        attempt = self.repository.execution_attempt(idempotency_key)
./omni_prod/capability_executor.py:268:            # The external submit MUST receive the same durable idempotency key
./omni_prod/capability_executor.py:270:            # handle write is therefore recoverable without duplicate spend for
./omni_prod/capability_executor.py:271:            # providers truthfully marked durable-idempotent.
./omni_prod/capability_executor.py:273:                if not getattr(provider, "durable_idempotency", False):
./omni_prod/capability_executor.py:274:                    raise CapabilityExecutionError("paid provider lacks durable idempotency")
./omni_prod/capability_executor.py:277:            handle = provider.submit(requirement, idempotency_key=idempotency_key)
./omni_prod/capability_executor.py:278:            if handle.idempotency_key != idempotency_key or handle.provider != assignment.provider:
./omni_prod/capability_executor.py:281:                idempotency_key,
./omni_prod/capability_executor.py:290:                idempotency_key=idempotency_key,
./omni_prod/capability_executor.py:293:        current_status = self.repository.execution_attempt(idempotency_key)["status"]
./omni_prod/capability_executor.py:301:                    idempotency_key,
./omni_prod/capability_executor.py:310:            current_status = self.repository.execution_attempt(idempotency_key)["status"]
./omni_prod/capability_executor.py:312:                idempotency_key,
./omni_prod/capability_executor.py:379:            idempotency_key=idempotency_key, worker_id=self.worker_id,
./omni_prod/capability_registry.py:180:                raise ValueError(f"duplicate capability key: {definition.key}")
./omni_prod/capability_registry.py:228:                raise ValueError(f"duplicate capability requirement id: {requirement.id}")
./omni_prod/capability_repository.py:46:    idempotency_key: str
./omni_prod/capability_repository.py:88:    crash/retry/idempotency behavior can be proven without a live Postgres
./omni_prod/capability_repository.py:183:                raise ValueError("usage event idempotency conflict")
./omni_prod/capability_repository.py:196:        provider: str, pricing_version: str, idempotency_key: str,
./omni_prod/capability_repository.py:198:        existing = self._attempts.get(idempotency_key)
./omni_prod/capability_repository.py:203:                raise ValueError("execution idempotency key identity conflict")
./omni_prod/capability_repository.py:213:            "idempotency_key": idempotency_key,
./omni_prod/capability_repository.py:219:        self._attempts[idempotency_key] = row
./omni_prod/capability_repository.py:222:    def claim_execution_attempt(self, idempotency_key: str, *, worker_id: str, now: float, lease_seconds: int) -> bool:
./omni_prod/capability_repository.py:225:        row = self._attempts.get(idempotency_key)
./omni_prod/capability_repository.py:238:    def record_provider_handle(self, idempotency_key: str, *, provider_task_id: str, worker_id: str | None = None) -> bool:
./omni_prod/capability_repository.py:239:        row = self._attempts.get(idempotency_key)
./omni_prod/capability_repository.py:252:    def execution_attempt(self, idempotency_key: str) -> dict[str, Any]:
./omni_prod/capability_repository.py:253:        row = self._attempts.get(idempotency_key)
./omni_prod/capability_repository.py:258:    def transition_execution_attempt(self, idempotency_key: str, *, expected: str, target: str, worker_id: str | None = None) -> bool:
./omni_prod/capability_repository.py:259:        row = self._attempts.get(idempotency_key)
./omni_prod/capability_repository.py:270:        self, *, idempotency_key: str, worker_id: str, build_id: str,
./omni_prod/capability_repository.py:274:        attempt = self._attempts.get(idempotency_key)
./omni_prod/capability_repository.py:298:            raise ValueError("usage event idempotency conflict")
./omni_prod/capability_repository.py:319:                idempotency_key=row["idempotency_key"], provider_task_id=row["provider_task_id"],
./omni_prod/capability_repository.py:355:        """Idempotent for the same plan (a retried job); a different plan for
./omni_prod/capability_repository.py:533:            pricing_version=row[4], idempotency_key=row[5], provider_task_id=row[6],
./omni_prod/capability_repository.py:545:            "idempotency_key": attempt.idempotency_key,
./omni_prod/capability_repository.py:554:        pricing_version: str, idempotency_key: str,
./omni_prod/capability_repository.py:562:                               idempotency_key, provider_task_id, status, lease_owner,
./omni_prod/capability_repository.py:565:                        WHERE idempotency_key=%s FOR UPDATE
./omni_prod/capability_repository.py:567:                        (idempotency_key,),
./omni_prod/capability_repository.py:575:                            raise ValueError("execution idempotency key identity conflict")
./omni_prod/capability_repository.py:581:                            idempotency_key, status, lease_owner, lease_expires_at
./omni_prod/capability_repository.py:584:                        (attempt_id, build_id, requirement_id, provider, pricing_version, idempotency_key, "SUBMITTING"),
./omni_prod/capability_repository.py:589:                        "pricing_version": pricing_version, "idempotency_key": idempotency_key,
./omni_prod/capability_repository.py:594:    def claim_execution_attempt(
./omni_prod/capability_repository.py:595:        self, idempotency_key: str, *, worker_id: str, now: float, lease_seconds: int
./omni_prod/capability_repository.py:608:                        WHERE idempotency_key=%s
./omni_prod/capability_repository.py:612:                        (worker_id, expires, idempotency_key, worker_id, now_dt),
./omni_prod/capability_repository.py:617:        self, idempotency_key: str, *, provider_task_id: str, worker_id: str
./omni_prod/capability_repository.py:625:                           WHERE idempotency_key=%s FOR UPDATE""",
./omni_prod/capability_repository.py:626:                        (idempotency_key,),
./omni_prod/capability_repository.py:641:                        WHERE idempotency_key=%s AND lease_owner=%s
./omni_prod/capability_repository.py:643:                        (provider_task_id, idempotency_key, worker_id),
./omni_prod/capability_repository.py:647:    def execution_attempt(self, idempotency_key: str) -> dict[str, Any]:
./omni_prod/capability_repository.py:653:                           idempotency_key, provider_task_id, status, lease_owner,
./omni_prod/capability_repository.py:655:                    FROM provider_execution_attempts WHERE idempotency_key=%s
./omni_prod/capability_repository.py:657:                    (idempotency_key,),
./omni_prod/capability_repository.py:665:        self, idempotency_key: str, *, expected: str, target: str, worker_id: str
./omni_prod/capability_repository.py:675:                        WHERE idempotency_key=%s AND status=%s AND lease_owner=%s
./omni_prod/capability_repository.py:677:                        (target, idempotency_key, expected, worker_id),
./omni_prod/capability_repository.py:683:        idempotency_key: str, lease_owner: str, now: float,
./omni_prod/capability_repository.py:689:            provider=provider, pricing_version=pricing_version, idempotency_key=idempotency_key,
./omni_prod/capability_repository.py:691:        if not self.claim_execution_attempt(
./omni_prod/capability_repository.py:692:            idempotency_key, worker_id=lease_owner, now=now, lease_seconds=lease_seconds
./omni_prod/capability_repository.py:694:            existing = self.execution_attempt(idempotency_key)
./omni_prod/capability_repository.py:697:        current = self.execution_attempt(idempotency_key)
./omni_prod/capability_repository.py:701:            pricing_version=current["pricing_version"], idempotency_key=current["idempotency_key"],
./omni_prod/capability_repository.py:711:                cur.execute("SELECT idempotency_key FROM provider_execution_attempts WHERE id=%s", (attempt_id,))
./omni_prod/capability_repository.py:721:                cur.execute("SELECT idempotency_key FROM provider_execution_attempts WHERE id=%s", (attempt_id,))
./omni_prod/capability_repository.py:731:        self, *, idempotency_key: str, worker_id: str, build_id: str,
./omni_prod/capability_repository.py:749:                           WHERE idempotency_key=%s FOR UPDATE""",
./omni_prod/capability_repository.py:750:                        (idempotency_key,),
./omni_prod/capability_repository.py:802:                        WHERE idempotency_key=%s AND lease_owner=%s
./omni_prod/capability_repository.py:805:                        (idempotency_key, worker_id),
./omni_prod/company_loss.py:15:idempotent per (source, idempotency_key), so a retried settlement never
./omni_prod/company_loss.py:38:def record_overrun(cur, *, source: str, idempotency_key: str, quoted_usd, actual_usd, cause: str,
./omni_prod/company_loss.py:44:    none (actual <= quoted). Idempotent per (source, idempotency_key).
./omni_prod/company_loss.py:52:    if not source or not idempotency_key:
./omni_prod/company_loss.py:53:        raise ValueError('source and idempotency_key are required')
./omni_prod/company_loss.py:61:        'INSERT INTO company_loss_events (source, idempotency_key, build_id, reservation_id, account_id, '
./omni_prod/company_loss.py:64:        'ON CONFLICT (source, idempotency_key) DO NOTHING',
./omni_prod/company_loss.py:65:        (source, idempotency_key, build_id, reservation_id, account_id, project_id, lane, provider, model,
./omni_prod/conversation/store.py:8:Writes are idempotent per request_key (a retried send never duplicates).
./omni_prod/conversation/supervisor.py:192:           'screens': 'מסכים', 'languages': 'שפה', 'content': 'תוכן התחלתי', 'dates': 'תאריכים', 'duplicates': 'כפילויות',
./omni_prod/conversation/supervisor.py:196:           'duplicates': 'duplicates', 'style': 'style', 'color': 'colour', 'font': 'font', 'logo': 'logo',
./omni_prod/cors_policy.py:8:    if len(origins)!=len(set(origins)): raise ValueError('duplicate CORS origin')
./omni_prod/db.py:78:    duplicate side effects. Retry belongs at idempotent command/job boundaries.
./omni_prod/dependency_inventory.py:28:        if d.name in seen: raise ValueError(f'duplicate dependency: {d.name}')
./omni_prod/discovery.py:139:    Question('duplicates', 'duplicates', 'rules', 'מה לעשות כשמנסים להוסיף משהו שכבר קיים?', 'What if something already exists?',
./omni_prod/discovery.py:266:# defaults below (a list screen with an add form, date ranges, duplicate blocking, an empty start) are right
./omni_prod/discovery.py:274:    'duplicates': 'allow',
./omni_prod/discovery.py:489:    if v.get('duplicates') == 'block':
./omni_prod/discovery.py:490:        lines.append('Duplicates: block them on the server (also under two simultaneous requests) and explain why.')
./omni_prod/entitlements.py:42:    """Idempotent: an existing active grant is returned unchanged."""
./omni_prod/idempotency.py:10:        raise ValueError("invalid idempotency key")
./omni_prod/idempotency.py:22:class PostgresIdempotencyRepository:
./omni_prod/idempotency.py:38:                    FROM idempotency_keys
./omni_prod/idempotency.py:39:                    WHERE account_id = %s AND idempotency_key = %s
./omni_prod/idempotency.py:47:                        raise ValueError("idempotency key reused with different payload")
./omni_prod/idempotency.py:51:                    INSERT INTO idempotency_keys(
./omni_prod/idempotency.py:52:                        account_id, idempotency_key, request_fingerprint
./omni_prod/idempotency.py:65:                    UPDATE idempotency_keys
./omni_prod/idempotency.py:67:                    WHERE account_id = %s AND idempotency_key = %s
./omni_prod/idempotency.py:72:                    raise KeyError("idempotency claim not found")
./omni_prod/identity_lifecycle.py:259:            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
./omni_prod/infrastructure_contracts.py:45:    "provisioning_idempotency_key",
./omni_prod/infrastructure_contracts.py:160:def provisioning_idempotency_key(*, profile_key: str, project_id: str, environment, kind) -> str:
./omni_prod/infrastructure_contracts.py:219:    idempotency_key: str
./omni_prod/infrastructure_contracts.py:233:                     "idempotency_key", "provisioner"):
./omni_prod/infrastructure_contracts.py:267:            "idempotency_key": self.idempotency_key, "provisioner": self.provisioner,
./omni_prod/infrastructure_contracts.py:279:            resource_name=str(data["resource_name"]), idempotency_key=str(data["idempotency_key"]),
./omni_prod/infrastructure_contracts.py:401:    """Adapter boundary. Implementations must be idempotent per idempotency_key."""
./omni_prod/infrastructure_contracts.py:411:                  environment, idempotency_key: str) -> InfrastructureBinding: ...
./omni_prod/infrastructure_provisioner.py:7:* Idempotent: a LIVE binding with the same idempotency key is reused, never
./omni_prod/infrastructure_provisioner.py:9:  the *same* key, so a later configuration change heals without duplicates.
./omni_prod/infrastructure_provisioner.py:30:    provisioning_idempotency_key,
./omni_prod/infrastructure_provisioner.py:51:    def get_by_idempotency_key(self, idempotency_key: str) -> InfrastructureBinding | None:
./omni_prod/infrastructure_provisioner.py:52:        return self._by_key.get(idempotency_key)
./omni_prod/infrastructure_provisioner.py:61:        existing = self._by_key.get(binding.idempotency_key)
./omni_prod/infrastructure_provisioner.py:64:        self._by_key[binding.idempotency_key] = binding
./omni_prod/infrastructure_provisioner.py:79:    _COLUMNS = ("binding_id, idempotency_key, profile_key, tenant_id, project_id, environment, kind, status, "
./omni_prod/infrastructure_provisioner.py:88:        (binding_id, idempotency_key, profile_key, tenant_id, project_id, environment, kind, status,
./omni_prod/infrastructure_provisioner.py:104:            "binding_id": binding_id, "idempotency_key": idempotency_key, "profile_key": profile_key,
./omni_prod/infrastructure_provisioner.py:112:    def get_by_idempotency_key(self, idempotency_key: str) -> InfrastructureBinding | None:
./omni_prod/infrastructure_provisioner.py:115:                cur.execute(f"SELECT {self._COLUMNS} FROM generated_app_bindings WHERE idempotency_key=%s",
./omni_prod/infrastructure_provisioner.py:116:                            (idempotency_key,))
./omni_prod/infrastructure_provisioner.py:136:                        "SELECT tenant_id FROM generated_app_bindings WHERE idempotency_key=%s FOR UPDATE",
./omni_prod/infrastructure_provisioner.py:137:                        (binding.idempotency_key,),
./omni_prod/infrastructure_provisioner.py:143:                        "INSERT INTO generated_app_bindings(binding_id, idempotency_key, profile_key, tenant_id, "
./omni_prod/infrastructure_provisioner.py:147:                        "ON CONFLICT (idempotency_key) DO UPDATE SET status=EXCLUDED.status, "
./omni_prod/infrastructure_provisioner.py:152:                        (record["binding_id"], record["idempotency_key"], record["profile_key"],
./omni_prod/infrastructure_provisioner.py:198:    def provision(self, requirement, *, tenant_id, project_id, environment, idempotency_key) -> InfrastructureBinding:
./omni_prod/infrastructure_provisioner.py:201:            binding_id="ib_" + idempotency_key[:24], profile_key=self.profile_key, tenant_id=tenant_id,
./omni_prod/infrastructure_provisioner.py:204:            idempotency_key=idempotency_key, provisioner=self.name, status_reason=self.reason,
./omni_prod/infrastructure_provisioner.py:271:            key = provisioning_idempotency_key(profile_key=profile_key, project_id=project_id, environment=env, kind=kind)
./omni_prod/infrastructure_provisioner.py:272:            existing = self.repository.get_by_idempotency_key(key)
./omni_prod/infrastructure_provisioner.py:285:        key = provisioning_idempotency_key(
./omni_prod/infrastructure_provisioner.py:287:        existing = self.repository.get_by_idempotency_key(key)
./omni_prod/infrastructure_provisioner.py:296:                        environment=environment, idempotency_key=key)
./omni_prod/infrastructure_provisioner.py:300:                environment=environment, idempotency_key=key)
./omni_prod/infrastructure_provisioner.py:301:        if (binding.idempotency_key != key or binding.project_id != project_id
./omni_prod/infrastructure_registry.py:85:                raise ValueError(f"duplicate infrastructure profile: {profile.key}")
./omni_prod/intake/budget.py:14:                   reservation + scopes + outbox row + event. Idempotent per key.
./omni_prod/intake/budget.py:71:class IdempotencyConflict(BudgetError):
./omni_prod/intake/budget.py:171:    idempotency_key: str
./omni_prod/intake/budget.py:181:    claim_token: str | None = None
./omni_prod/intake/budget.py:191:        d.pop('claim_token')
./omni_prod/intake/budget.py:195:_COLS = ('id, idempotency_key, account_id, project_id, lane, campaign_id, quoted_usd, state, cost_state, actual_usd, '
./omni_prod/intake/budget.py:196:         'failure_reason, claim_token, provider, model, result, quote')
./omni_prod/intake/budget.py:270:    def reserve(self, *, idempotency_key: str, account_id: str, project_id: str, quote_: Quote, caps: Caps,
./omni_prod/intake/budget.py:274:        if not idempotency_key or len(idempotency_key) > 300:
./omni_prod/intake/budget.py:275:            raise ValueError('idempotency key required')
./omni_prod/intake/budget.py:285:                cur.execute(f'SELECT {_COLS} FROM intake_reservations WHERE idempotency_key = %s', (idempotency_key,))
./omni_prod/intake/budget.py:291:                        raise IdempotencyConflict('idempotency key already used for another request')
./omni_prod/intake/budget.py:292:                    return existing                         # duplicate request: the original reservation
./omni_prod/intake/budget.py:303:                    'INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, campaign_id, '
./omni_prod/intake/budget.py:305:                    (rid, idempotency_key, account_id, project_id, lane, campaign_id, amount,
./omni_prod/intake/budget.py:313:        return Reservation(rid, idempotency_key, account_id, project_id, lane, campaign_id, amount, RESERVED, quote=q)
./omni_prod/intake/budget.py:325:                    f"UPDATE intake_reservations SET state = 'CLAIMED', claim_token = %s, claimed_by = %s, "
./omni_prod/intake/budget.py:345:                            "WHERE id = %s AND state = 'CLAIMED' AND claim_token = %s AND lease_expires_at > now() "
./omni_prod/intake/budget.py:346:                            "RETURNING id", (lease_seconds, reservation.id, reservation.claim_token))
./omni_prod/intake/budget.py:391:                    f'updated_at = now() WHERE id = %s AND state = %s AND claim_token = %s RETURNING {_COLS}',
./omni_prod/intake/budget.py:394:                     reservation.id, EXECUTING, reservation.claim_token))
./omni_prod/intake/budget.py:400:                            cur, source='intake_reservation', idempotency_key=reservation.id,
./omni_prod/intake/budget.py:411:            return current                                     # duplicate settlement of the same outcome
./omni_prod/intake/budget.py:482:                    cur, source='intake_reservation', idempotency_key=reservation_id,
./omni_prod/intake/budget.py:499:        never double-claim a row; a duplicate Redis job is harmless (claim)."""
./omni_prod/intake/contract.py:101:        p.append('duplicate requirement ids')
./omni_prod/intake/contract.py:171:    if v.get('duplicates') == 'block':
./omni_prod/intake/contract.py:172:        nfr.append(Requirement('N4', 'Duplicates are blocked on the server with an explanation', 'data',
./omni_prod/intake/contract.py:173:                               origin('duplicates'), confidence('duplicates')))
./omni_prod/intake/contract.py:209:        data_requirements={'personal_data': personal, 'dates': v.get('dates'), 'duplicates': v.get('duplicates'),
./omni_prod/intake/interpreter.py:116:    (r'(למנוע כפילויות|בלי כפילויות|לא לאפשר כפילויות|no duplicates|prevent (double|duplicate)|לא (יהיו )?שתי הזמנות)', 'duplicates', 'block', HIGH),
./omni_prod/intake/interpreter.py:262:            dropped.append(f'{fld}: duplicate proposal ignored')
./omni_prod/intake/reservation_worker.py:6:* A duplicate Redis delivery finds the reservation already claimed: no-op.
./omni_prod/intake/worker_route.py:66:            r = self.svc.reserve(idempotency_key=self._key(message), account_id=self.account_id,
./omni_prod/intelligence/matrix.py:154:        problems.append('duplicate model_key in the inventory')
./omni_prod/investor_app.py:65:from .idempotency import request_fingerprint, validate_key
./omni_prod/investor_app.py:239:def _m5_build_idempotency_fingerprints(*, account_id, internal_project_id, public_project_id,
./omni_prod/investor_app.py:300:class _DuplicateApproval(Exception):
./omni_prod/investor_app.py:471:    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)
./omni_prod/investor_app.py:2232:        caller_idempotency_key = validate_key(req.idempotency_key) if req.idempotency_key else None
./omni_prod/investor_app.py:2234:        raise HTTPException(422, detail={'error': 'invalid_idempotency_key'}) from exc
./omni_prod/investor_app.py:2298:        if caller_idempotency_key:
./omni_prod/investor_app.py:2301:            request_fp, quote_fp, quote_fp_version = _m5_build_idempotency_fingerprints(
./omni_prod/investor_app.py:2317:                        if caller_idempotency_key:
./omni_prod/investor_app.py:2319:                                claimed, replay = jobs.claim_build_request_idempotency(
./omni_prod/investor_app.py:2321:                                    idempotency_key=caller_idempotency_key, request_fingerprint=request_fp,
./omni_prod/investor_app.py:2327:                                    'error': 'idempotency_conflict',
./omni_prod/investor_app.py:2328:                                    'message': 'This idempotency key was already used for a different build request or quote.',
./omni_prod/investor_app.py:2332:                                raise _DuplicateApproval()
./omni_prod/investor_app.py:2333:                        existing = jobs.claim_contract_build(cur, internal_project_id=key,
./omni_prod/investor_app.py:2338:                            raise _DuplicateApproval()
./omni_prod/investor_app.py:2397:        except _DuplicateApproval:
./omni_prod/investor_app.py:2399:                "status": existing[1], "build_id": existing[0], "duplicate": True,
./omni_prod/investor_app.py:2490:        # Idempotent: a no-op unless the reservation is still RESERVED.
./omni_prod/job_repository.py:132:    def claim_contract_build(self, cur, *, internal_project_id: str, build_contract_id: str):
./omni_prod/job_repository.py:156:    def claim_build_request_idempotency(self, cur, *, account_id: str, internal_project_id: str,
./omni_prod/job_repository.py:157:                                       idempotency_key: str, request_fingerprint: str,
./omni_prod/job_repository.py:166:        from .idempotency import validate_key
./omni_prod/job_repository.py:167:        validate_key(idempotency_key)
./omni_prod/job_repository.py:170:            INSERT INTO build_request_idempotency(
./omni_prod/job_repository.py:171:                account_id, internal_project_id, idempotency_key,
./omni_prod/job_repository.py:174:            ON CONFLICT (account_id, internal_project_id, idempotency_key) DO NOTHING
./omni_prod/job_repository.py:176:            (account_id, internal_project_id, idempotency_key,
./omni_prod/job_repository.py:186:            FROM build_request_idempotency AS idem
./omni_prod/job_repository.py:190:              AND idem.idempotency_key = %s
./omni_prod/job_repository.py:193:            (account_id, internal_project_id, idempotency_key),
./omni_prod/job_repository.py:197:            raise RuntimeError('idempotency key conflict did not resolve to a durable build')
./omni_prod/job_repository.py:200:            raise ValueError('idempotency key reused with different request or quote')
./omni_prod/job_repository.py:304:        of enqueueing alone. Duplicate delivery (enqueue succeeded, commit
./omni_prod/maintenance.py:21:   conditional, so a duplicate delivery is a no-op.
./omni_prod/media_gateway.py:32:    def generate(self,request:AssetRequest,*,idempotency_key:str|None=None)->GeneratedAsset:
./omni_prod/media_gateway.py:34:        if idempotency_key: payload_body['idempotency_key']=idempotency_key
./omni_prod/memory_adapters.py:8:        if build_id in self.jobs: raise KeyError('duplicate build')
./omni_prod/migrations.py:40:        raise ValueError("duplicate migration version")
./omni_prod/model_catalog.py:106:            raise ModelCatalogError(f'{name}: duplicate name')
./omni_prod/model_gateway.py:146:        self.last_idempotency_key = None
./omni_prod/model_gateway.py:149:                 max_tokens: int = 4096, idempotency_key: str | None = None) -> str:
./omni_prod/model_gateway.py:160:        if idempotency_key and str(idempotency_key).strip():
./omni_prod/model_gateway.py:161:            headers['Idempotency-Key'] = str(idempotency_key).strip()[:255]
./omni_prod/model_gateway.py:192:        self.last_idempotency_key = headers.get('Idempotency-Key')
./omni_prod/model_gateway.py:295:def idempotency_key_for(*, build_id: str, task: str, attempt: int = 0, call_index: int = 0) -> str:
./omni_prod/model_gateway.py:299:    dedupe); distinct per attempt and call index, so two *different* calls
./omni_prod/modification_repository.py:136:        (one row per transaction, FOR UPDATE SKIP LOCKED, duplicate delivery
./omni_prod/modification_repository.py:195:        """QUEUED -> RUNNING, conditional so a duplicate outbox/queue
./omni_prod/modification_repository.py:196:        delivery is a no-op (acceptance test T: idempotent retry)."""
./omni_prod/modification_repository.py:215:        conditional on RUNNING so a duplicate delivery after completion is a
./omni_prod/outbox.py:14:    dedupe_key: str
./omni_prod/outbox.py:17:def deterministic_dedupe_key(*, topic: str, aggregate_id: str, payload: dict) -> str:
./omni_prod/outbox.py:36:        dedupe_key=deterministic_dedupe_key(
./omni_prod/outbox.py:46:            "(id,topic,aggregate_id,payload,dedupe_key,created_at) "
./omni_prod/outbox.py:48:            "ON CONFLICT (dedupe_key) DO NOTHING"
./omni_prod/outbox.py:52:            json.dumps(event.payload), event.dedupe_key, event.created_at
./omni_prod/outbox.py:55:    def claim_batch(self, cur, *, limit: int = 100) -> list[tuple]:
./omni_prod/outbox.py:59:            "SELECT id,topic,aggregate_id,payload,dedupe_key "
./omni_prod/planning/graph.py:100:            out.append('duplicate task ids')
./omni_prod/postdeploy_checks.py:277:                         'idempotency_key': uuid.uuid4().hex}, token)
./omni_prod/preview_repository.py:95:        for this project. Idempotent: an already-terminal preview is returned
./omni_prod/preview_runtime.py:513:                return  # already gone: stopping is idempotent
./omni_prod/pricing.py:192:                return {'processed': False, 'duplicate': True}
./omni_prod/product_spec.py:51:            raise ValueError('duplicate requirement id')
./omni_prod/product_spec.py:64:            raise ValueError('duplicate acceptance id')
./omni_prod/project_lifecycle.py:170:            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
./omni_prod/project_lifecycle.py:203:        # COALESCE preserves the first tombstone timestamp/retention window so retry is idempotent.
./omni_prod/providers/http_media_provider.py:37:        durable_idempotency: bool,
./omni_prod/providers/http_media_provider.py:41:        if paid_external and not durable_idempotency:
./omni_prod/providers/http_media_provider.py:42:            raise ValueError("paid external providers require durable idempotency support")
./omni_prod/providers/http_media_provider.py:53:        self.durable_idempotency = durable_idempotency
./omni_prod/providers/http_media_provider.py:85:    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle:
./omni_prod/providers/http_media_provider.py:88:        task_id = "sync_" + sha256(f"{self.name}\0{idempotency_key}".encode()).hexdigest()[:24]
./omni_prod/providers/http_media_provider.py:89:        asset = self.gateway.generate(self._asset_request(requirement), idempotency_key=idempotency_key)
./omni_prod/providers/http_media_provider.py:95:            provenance={"provider": asset.provider, "idempotency_key": idempotency_key},
./omni_prod/providers/http_media_provider.py:100:            evidence={"adapter": "HTTPMediaCapabilityProvider", "durable_idempotency": self.durable_idempotency},
./omni_prod/providers/http_media_provider.py:103:        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)
./omni_prod/providers/http_media_provider.py:112:            raise RuntimeError("provider result is not available in this adapter process; idempotent resubmit is required") from exc
./omni_prod/providers/image_provider.py:22:  provider task id right after. Resubmitting the same idempotency key returns
./omni_prod/providers/image_provider.py:24:  either resubmits with a provider-honoured idempotency header (only when the
./omni_prod/providers/image_provider.py:95:    idempotency_header: str = ""
./omni_prod/providers/image_provider.py:119:            idempotency_header=_clean(env, "OMNI_IMAGE_PROVIDER_IDEMPOTENCY_HEADER"),
./omni_prod/providers/image_provider.py:157:    idempotency_key: str
./omni_prod/providers/image_provider.py:176:    def begin(self, idempotency_key: str, *, provider: str) -> SubmissionRecord:
./omni_prod/providers/image_provider.py:177:        row = self._rows.get(idempotency_key)
./omni_prod/providers/image_provider.py:179:            self._rows[idempotency_key] = {"provider": provider, "state": "INTENT", "provider_task_id": None}
./omni_prod/providers/image_provider.py:180:            return SubmissionRecord(idempotency_key, provider, "INTENT", None, False)
./omni_prod/providers/image_provider.py:182:            raise RuntimeError("idempotency key already used by another provider")
./omni_prod/providers/image_provider.py:183:        return SubmissionRecord(idempotency_key, row["provider"], row["state"], row["provider_task_id"], True)
./omni_prod/providers/image_provider.py:185:    def record_task(self, idempotency_key: str, provider_task_id: str) -> None:
./omni_prod/providers/image_provider.py:186:        row = self._rows[idempotency_key]
./omni_prod/providers/image_provider.py:191:    def clear(self, idempotency_key: str) -> None:
./omni_prod/providers/image_provider.py:192:        row = self._rows.get(idempotency_key)
./omni_prod/providers/image_provider.py:194:            del self._rows[idempotency_key]
./omni_prod/providers/image_provider.py:208:                cur.execute('SELECT idempotency_key, provider, state, provider_task_id FROM media_provider_submissions WHERE idempotency_key=%s', (key,))
./omni_prod/providers/image_provider.py:212:    def begin(self, idempotency_key: str, *, provider: str) -> SubmissionRecord:
./omni_prod/providers/image_provider.py:217:                        "INSERT INTO media_provider_submissions(idempotency_key, provider, state) "
./omni_prod/providers/image_provider.py:218:                        "VALUES(%s,%s,'INTENT') ON CONFLICT (idempotency_key) DO NOTHING "
./omni_prod/providers/image_provider.py:219:                        "RETURNING idempotency_key, provider, state, provider_task_id",
./omni_prod/providers/image_provider.py:220:                        (idempotency_key, provider),
./omni_prod/providers/image_provider.py:227:                            "SELECT idempotency_key, provider, state, provider_task_id "
./omni_prod/providers/image_provider.py:228:                            "FROM media_provider_submissions WHERE idempotency_key=%s FOR UPDATE",
./omni_prod/providers/image_provider.py:229:                            (idempotency_key,),
./omni_prod/providers/image_provider.py:235:            raise RuntimeError("idempotency key already used by another provider")
./omni_prod/providers/image_provider.py:238:    def record_task(self, idempotency_key: str, provider_task_id: str) -> None:
./omni_prod/providers/image_provider.py:244:                        "WHERE idempotency_key=%s AND (provider_task_id IS NULL OR provider_task_id=%s)",
./omni_prod/providers/image_provider.py:245:                        (provider_task_id, idempotency_key, provider_task_id),
./omni_prod/providers/image_provider.py:250:    def clear(self, idempotency_key: str) -> None:
./omni_prod/providers/image_provider.py:256:                        "WHERE idempotency_key=%s AND state='INTENT' AND provider_task_id IS NULL",
./omni_prod/providers/image_provider.py:257:                        (idempotency_key,),
./omni_prod/providers/image_provider.py:318:        self.durable_idempotency = True
./omni_prod/providers/image_provider.py:351:    def _headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
./omni_prod/providers/image_provider.py:357:        if idempotency_key and self.config.idempotency_header:
./omni_prod/providers/image_provider.py:358:            headers[self.config.idempotency_header] = idempotency_key
./omni_prod/providers/image_provider.py:361:    def _json(self, method: str, url: str, *, body: dict | None = None, idempotency_key: str | None = None) -> dict:
./omni_prod/providers/image_provider.py:362:        req = request.Request(url, method=method, headers=self._headers(idempotency_key=idempotency_key),
./omni_prod/providers/image_provider.py:367:    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle:
./omni_prod/providers/image_provider.py:370:        record = self.journal.begin(idempotency_key, provider=self.name)
./omni_prod/providers/image_provider.py:372:            return ProviderTaskHandle(self.name, record.provider_task_id, requirement.id, idempotency_key)
./omni_prod/providers/image_provider.py:373:        if record.preexisting and not self.config.idempotency_header:
./omni_prod/providers/image_provider.py:375:                f"{self.name}: a previous submit for {idempotency_key} may have reached the provider and the "
./omni_prod/providers/image_provider.py:376:                "provider has no declared idempotency header; manual reconciliation required")
./omni_prod/providers/image_provider.py:390:                                    idempotency_key=idempotency_key)
./omni_prod/providers/image_provider.py:393:                self.journal.clear(idempotency_key)  # rejected before creation: safe to retry later
./omni_prod/providers/image_provider.py:397:                self.journal.clear(idempotency_key)  # definite rejection: nothing was created
./omni_prod/providers/image_provider.py:403:        self.journal.record_task(idempotency_key, task_id)
./omni_prod/providers/image_provider.py:406:        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)
./omni_prod/providers/image_provider.py:471:                    "provider_task_id": handle.provider_task_id, "idempotency_key": handle.idempotency_key,
./omni_prod/providers/llm_provider.py:29:        self.durable_idempotency = False
./omni_prod/providers/llm_provider.py:47:    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle:
./omni_prod/providers/llm_provider.py:50:        task_id = "sync_" + sha256(f"{self.name}\0{idempotency_key}".encode()).hexdigest()[:24]
./omni_prod/providers/llm_provider.py:61:            provenance={"provider": self.name, "idempotency_key": idempotency_key,
./omni_prod/providers/llm_provider.py:69:        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)
./omni_prod/providers/llm_provider.py:78:            raise RuntimeError("provider result unavailable; idempotent resubmit is required") from exc
./omni_prod/providers/managed_web_saas.py:435:    def _binding(self, requirement, *, tenant_id, project_id, environment, idempotency_key, status,
./omni_prod/providers/managed_web_saas.py:439:            binding_id="ib_" + idempotency_key[:24], profile_key=self.profile_key, tenant_id=tenant_id,
./omni_prod/providers/managed_web_saas.py:442:            idempotency_key=idempotency_key, provisioner=self.name,
./omni_prod/providers/managed_web_saas.py:477:    def provision(self, requirement, *, tenant_id, project_id, environment, idempotency_key) -> InfrastructureBinding:
./omni_prod/providers/managed_web_saas.py:480:        common = dict(tenant_id=tenant_id, project_id=project_id, environment=env, idempotency_key=idempotency_key)
./omni_prod/providers/managed_web_saas.py:505:    def _provision_database(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./omni_prod/providers/managed_web_saas.py:506:        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
./omni_prod/providers/managed_web_saas.py:539:    def _provision_auth_session(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./omni_prod/providers/managed_web_saas.py:540:        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
./omni_prod/providers/managed_web_saas.py:548:    def _provision_object_storage(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./omni_prod/providers/managed_web_saas.py:551:        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
./omni_prod/providers/managed_web_saas.py:604:    def _provision_scheduled_http(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./omni_prod/providers/managed_web_saas.py:605:        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
./omni_prod/providers/managed_web_saas.py:634:    def _provision_outbound(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./omni_prod/providers/managed_web_saas.py:635:        common = dict(tenant_id=tenant_id, project_id=project_id, environment=environment, idempotency_key=idempotency_key)
./omni_prod/providers/qstash_scheduler.py:153:    def verify(self, *, signature: str, body: bytes, destination: str, claim_once):
./omni_prod/providers/qstash_scheduler.py:156:        claim_once(jti, expiry) must return True exactly once across processes.
./omni_prod/providers/qstash_scheduler.py:157:        A rejected duplicate raises a safe error; consumers may return 200 for
./omni_prod/providers/qstash_scheduler.py:161:            if not callable(claim_once) or not isinstance(body, bytes) or len(body) > 1048576:
./omni_prod/providers/qstash_scheduler.py:194:            claimed = claim_once(jti, exp)
./omni_prod/providers/qstash_scheduler.py:198:            raise QStashError("duplicate QStash delivery")
./omni_prod/providers/replicate_image_test.py:90:        handle = self.provider.submit(requirement, idempotency_key=self.key(account_id))
./omni_prod/providers/replicate_image_test.py:118:        handle = ProviderTaskHandle(record.provider, record.provider_task_id, 'replicate-test', record.idempotency_key)
./omni_prod/provider_contracts.py:62:    idempotency_key: str
./omni_prod/provider_contracts.py:69:            "idempotency_key",
./omni_prod/provider_contracts.py:79:            "idempotency_key": self.idempotency_key,
./omni_prod/provider_contracts.py:88:            idempotency_key=str(payload["idempotency_key"]),
./omni_prod/provider_contracts.py:174:    durable_idempotency: bool
./omni_prod/provider_contracts.py:187:        idempotency_key: str,
./omni_prod/provider_pricing.py:64:                raise ValueError(f"duplicate provider price entry: {key}")
./omni_prod/provider_registry.py:12:    Registration is deterministic and rejects duplicate provider names so routing
./omni_prod/provider_registry.py:27:            raise ValueError(f"duplicate provider: {name}")
./omni_prod/provider_usage.py:13:* The ledger de-duplicates by provider request identity so re-recording the
./omni_prod/provider_usage.py:164:    """Per-build, de-duplicated collection of provider-reported usage."""
./omni_prod/recovery_simulation.py:37:        "event_dedupe": event.dedupe_key,
./omni_prod/release_policy.py:252:    035). Idempotent per (build, artifact digest, policy version, check).
./omni_prod/repair_contracts.py:161:            raise ValueError('duplicate changed path')
./omni_prod/repair_contracts.py:163:            raise ValueError('duplicate acceptance id')
./omni_prod/repository_patch.py:33:            raise PatchValidationError(f'duplicate patch path: {path}')
./omni_prod/requirement_ledger.py:48:                raise ValueError(f"duplicate requirement id: {record.requirement_id}")
./omni_prod/runtime_bindings.py:176:            ('path:.github/workflows/deploy-worker.yml', 'omni_prod.job_repository:PostgresBuildRepository.claim_contract_build'),
./omni_prod/secret_scan.py:84:    # de-duplicate same line/kind
./omni_prod/semantic_capabilities.py:52:            rejected.append("duplicate or oversized semantic decision")
./omni_prod/skills_registry.py:51:                raise ValueError(f"duplicate skill key: {definition.key}")
./omni_prod/skills_registry.py:195:        return base + ("secret_safety", "idempotency")
./omni_prod/skills_runtime.py:214:        'Data integrity: enforce business rules on the server (e.g. no two bookings in the same slot, no duplicate names '
./omni_prod/skill_catalog.py:83:                                                 'omni_prod.job_repository:PostgresBuildRepository.claim_contract_build'),
./omni_prod/skill_catalog.py:132:       'library build: duplicate member answered 409'),
./omni_prod/skill_catalog.py:163:    _s('operation.deduplicate', 'execution', EXECUTABLE, ('omni_prod.job_repository:PostgresBuildRepository.claim_contract_build',),
./omni_prod/skill_catalog.py:243:assert len(BY_KEY) == len(CATALOG), 'duplicate skill key'
./omni_prod/spec_repository.py:28:        """Idempotent: ON CONFLICT DO NOTHING, matching
./omni_prod/stripe_billing.py:120:    Entitlement mutations and idempotency belong to the subscription service:
./omni_prod/subscription_store.py:47:                        return {'processed': False, 'duplicate': True}
./omni_prod/subscription_store.py:342:                                cur, source='build_reservation', idempotency_key=build_id,
./omni_prod/subscription_store.py:372:                                cur, source='build_reservation', idempotency_key=build_id,
./omni_prod/verification_contract.py:101:    duplicates = sorted({n for n in names if names.count(n) > 1})
./omni_prod/verification_contract.py:102:    if duplicates:
./omni_prod/verification_contract.py:103:        return BLOCKED, 'duplicate check names: ' + ', '.join(duplicates)
./omni_prod/web_security.py:11:                       allow_headers=['Authorization','Content-Type','Idempotency-Key'],
./omni_prod/worker.py:40:    # Plain stdout in RQ's own log format; logging.basicConfig would duplicate
./omni_prod/worker_tasks.py:577:        return None  # duplicate delivery / already handled: idempotent no-op
./omni_prod/worker_tasks.py:1051:# (transition_running, conditional on QUEUED -> duplicate-delivery safe),
./omni_prod/worker_tasks.py:1101:        return None  # duplicate delivery / already handled: idempotent no-op
./omni_prod/worker_tasks.py:1537:        # duplicate) cleanup job -- only the API's stop transition licenses it.
./omni_prod/worker_tasks.py:1547:        provider.stop(info['container_id'])  # idempotent; raises on real docker failure
./omni_prod/__init__.py:1:__all__ = ['config', 'db', 'queueing', 'storage', 'sandbox', 'health', 'models', 'build_state', 'job_repository', 'deployments', 'usage', 'provenance', 'api_routes', 'idempotency', 'limits', 'model_router', 'rollback', 'worker_health', 'artifact_keys', 'build_budget', 'canary', 'error_taxonomy', 'orchestrator', 'repair_loop', 'retry', 'memory_adapters', 'secret_redaction', 'acceptance_pipeline', 'migrations', 'audit', 'secret_scan', 'canary_controller', 'release_manifest', 'release_gate', 'staging_simulation', 'preflight', 'migration_runner', 'artifact_integrity', 'dependency_inventory', 'sbom', 'cors_policy', 'web_security', 'attestation', 'circuit_breaker', 'outbox', 'worker_lease', 'dead_letter', 'recovery_simulation', 'request_id', 'metrics', 'slo', 'backup_manifest', 'structured_event', 'observability', 'recovery_drill', 'production_adapters', 'redis_circuit_breaker', 'model_gateway', 'model_policy', 'product_spec', 'repository_patch', 'change_policy', 'autonomous_agents', 'autonomous_core', 'modifier_engine', 'model_runtime_config', 'project_manifest', 'sandbox_executor']
./tests/integration/test_m495_provider_adapter.py:126:            durable_idempotency=True,
./tests/integration/test_m495_provider_adapter.py:156:        self.assertTrue(request["idempotency_key"].startswith("cap_"))
./tests/integration/test_m5_build_economics_postgres.py:23:                "to_regclass('public.build_request_idempotency')"
./tests/integration/test_m5_build_economics_postgres.py:30:            return 'build request idempotency migration 040 not applied'
./tests/integration/test_m5_build_economics_postgres.py:68:                    "DELETE FROM build_request_idempotency WHERE account_id=%s", (self.user_id,)
./tests/integration/test_m5_build_economics_postgres.py:133:                            created, replay=repository.claim_build_request_idempotency(
./tests/integration/test_m5_build_economics_postgres.py:135:                                idempotency_key='concurrent-build-key-1',
./tests/integration/test_m5_build_economics_postgres.py:158:                                    VALUES (%s, %s, %s, 'integration idempotency test')
./tests/integration/test_m5_build_economics_postgres.py:173:        self.assertTrue(all(not thread.is_alive() for thread in threads), 'idempotency race timed out')
./tests/integration/test_m5_build_economics_postgres.py:182:                "SELECT count(*) FROM build_request_idempotency "
./tests/integration/test_m5_build_economics_postgres.py:183:                "WHERE account_id=%s AND idempotency_key=%s",
./tests/integration/test_m5_build_economics_postgres.py:200:                        created, replay=repository.claim_build_request_idempotency(
./tests/integration/test_m5_build_economics_postgres.py:202:                            idempotency_key=key, request_fingerprint=fingerprints[0],
./tests/integration/test_m5_build_economics_postgres.py:232:                "SELECT count(*) FROM build_request_idempotency "
./tests/integration/test_m5_build_economics_postgres.py:233:                "WHERE account_id=%s AND idempotency_key=%s",
./tests/integration/test_m5_managed_web_saas_live.py:62:    def test_provision_verify_idempotent_revoke_against_real_infrastructure(self):
./tests/integration/test_m5_managed_web_saas_live.py:114:                    "INSERT INTO generated_app_bindings(binding_id,idempotency_key,profile_key,tenant_id,project_id,"
./tests/integration/test_m5_managed_web_saas_live.py:119:                "INSERT INTO generated_app_bindings(binding_id,idempotency_key,profile_key,tenant_id,project_id,"
./tests/integration/test_profit_billing_events_pg.py:79:            migration = Path(__file__).resolve().parents[2] / 'infra/postgres/039_billing_event_idempotency.sql'
./tests/integration/test_profit_billing_events_pg.py:81:            conn.execute(migration.read_text(encoding='utf-8'))  # additive/idempotent
./tests/integration/test_profit_billing_events_pg.py:92:def test_duplicate_and_usage_survive_service_restart(pool):
./tests/integration/test_profit_billing_events_pg.py:98:    assert second.apply_billing_entitlement(payment())['duplicate']
./tests/integration/test_profit_billing_events_pg.py:109:    assert sum(r.get('duplicate', False) for r in results) == 7
./tests/test_build_cancel_and_log.py:166:        self.assertEqual(self.jobs.request_cancel(b, self.project, requested_by='u1'), 'cancelled')  # idempotent
./tests/test_build_state_machine.py:2:forward-only while RUNNING, and no way to skip a gate by retry, duplicate
./tests/test_build_state_machine.py:55:    def test_duplicate_delivery_claims_once(self):
./tests/test_build_state_machine.py:65:        # a retry/duplicate worker that still thinks it is RUNNING cannot write READY
./tests/test_company_loss.py:25:        cur, source='intake_reservation', idempotency_key='r1',
./tests/test_company_loss.py:33:        cur, source='intake_reservation', idempotency_key='r1',
./tests/test_company_loss.py:40:        cur, source='intake_reservation', idempotency_key='r1',
./tests/test_company_loss.py:46:    assert 'ON CONFLICT (source, idempotency_key) DO NOTHING' in sql
./tests/test_company_loss.py:54:        company_loss.record_overrun(cur, source='s', idempotency_key='k',
./tests/test_conversation_os.py:442:    def test_memory_survives_restart_and_retries_are_idempotent(self):
./tests/test_conversation_os.py:451:        self.assertEqual(len(store.messages_for(self.project)), before)          # same request_key: no duplicate
./tests/test_deployment_verification.py:273:    def test_duplicate_check_names(self):
./tests/test_deployment_verification.py:278:        self.assertIn('duplicate', why)
./tests/test_entitlements.py:42:    def test_grant_is_idempotent(self):
./tests/test_golden_mod_path_live_postgres.py:239:                        existing = jobs.claim_contract_build(cur, internal_project_id=self.project, build_contract_id=contract)
./tests/test_golden_mod_path_live_postgres.py:241:                            results.append(('duplicate', existing[0]))
./tests/test_golden_mod_path_live_postgres.py:258:        self.assertEqual(kinds, ['created', 'duplicate'], results)
./tests/test_golden_mod_path_live_postgres.py:260:        self.assertEqual(next(b for k, b in results if k == 'duplicate'), created)
./tests/test_golden_mod_path_live_postgres.py:266:                self.assertIsNone(jobs.claim_contract_build(cur, internal_project_id=self.project, build_contract_id=contract))
./tests/test_intake_budget_pg.py:2:for duplicate delivery). Each class creates a throw-away database, applies the
./tests/test_intake_budget_pg.py:75:        return self.svc.reserve(idempotency_key=key or uuid.uuid4().hex, account_id=account, project_id=project,
./tests/test_intake_budget_pg.py:270:    def test_idempotency_50_concurrent_duplicates(self):
./tests/test_intake_budget_pg.py:275:        self.assertEqual(self.sql('SELECT count(*) FROM intake_reservations WHERE idempotency_key = %s', (key,))[0][0], 1)
./tests/test_intake_budget_pg.py:276:        with self.assertRaises(B.IdempotencyConflict):
./tests/test_intake_budget_pg.py:349:        s2 = self.svc.settle(r, cost_state=B.CONFIRMED, actual_usd=Decimal('0.002'))   # duplicate: same outcome
./tests/test_intake_budget_pg.py:355:        other.claim_token = 'forged'
./tests/test_intake_budget_pg.py:392:        self.assertEqual(self.svc.reconcile(), {'unknown': [], 'released': []})   # idempotent
./tests/test_intake_budget_pg.py:409:                r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='outcomes',
./tests/test_intake_budget_pg.py:429:        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='over', quote_=real_quote(),
./tests/test_intake_budget_pg.py:447:    def test_stale_reserved_is_released_and_late_claim_refused(self):
./tests/test_intake_budget_pg.py:478:    def test_concurrent_duplicate_deliveries_invoke_provider_once(self):
./tests/test_intake_budget_pg.py:479:        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='dupq', quote_=real_quote(),
./tests/test_intake_budget_pg.py:487:    def test_real_redis_rq_duplicate_jobs(self):
./tests/test_intake_budget_pg.py:500:        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='rq', quote_=real_quote(),
./tests/test_intake_budget_pg.py:588:    def test_upgrade_preserves_data_and_is_idempotent(self):
./tests/test_intake_budget_pg.py:613:                self.assertEqual(apply_migrations(conn, upto37).applied_versions, ())      # idempotent
./tests/test_intake_requirements_preservation.py:115:        self.assertEqual(t2.reply.count('התחברות:'), 2)                          # once per side (short name), not duplicated
./tests/test_intake_worker_route.py:37:        return B.Reservation('irs_1', kw['idempotency_key'], kw['account_id'], kw['project_id'], kw['lane'], None,
./tests/test_intake_worker_route.py:78:        self.assertTrue(svc.reserved[0]['idempotency_key'].startswith('intake:acct:p:rk:'))
./tests/test_intake_worker_route.py:99:                    B.IdempotencyConflict('x'), RuntimeError('relation "intake_reservations" does not exist')):
./tests/test_m3_preview_logic.py:331:    def test_stop_is_idempotent_for_missing_container(self):
./tests/test_m3_preview_logic.py:787:    def test_request_stop_terminal_is_idempotent(self):
./tests/test_m3_preview_logic.py:1043:    def test_duplicate_delivery_is_noop(self):
./tests/test_m495_capability_executor.py:59:    durable_idempotency = True
./tests/test_m495_capability_executor.py:77:    def submit(self, req, *, idempotency_key):
./tests/test_m495_capability_executor.py:78:        self.submit_calls.append((req.id, idempotency_key))
./tests/test_m495_capability_executor.py:79:        return ProviderTaskHandle(self.name, f"task-{req.id}", req.id, idempotency_key)
./tests/test_m495_capability_executor.py:153:    def test_restart_resumes_persisted_provider_task_without_duplicate_submit(self):
./tests/test_m495_capability_executor.py:190:        self.assertEqual(len(repo.usage_for_build(build_id="b1")), 1, "usage event must remain idempotent")
./tests/test_m495_capability_registry.py:76:    def test_duplicate_definition_keys_are_rejected(self):
./tests/test_m495_capability_registry.py:77:        duplicate = CapabilityDefinition("x", "test", "one")
./tests/test_m495_capability_registry.py:78:        with self.assertRaisesRegex(ValueError, "duplicate capability key"):
./tests/test_m495_capability_registry.py:79:            CapabilityRegistry((duplicate, duplicate))
./tests/test_m495_capability_repository.py:73:    def test_create_plan_is_idempotent_for_identical_plan_and_rejects_drift(self):
./tests/test_m495_capability_repository.py:100:    def test_usage_event_is_idempotent_by_event_key(self):
./tests/test_m495_capability_repository.py:121:            provider="p", pricing_version="v1", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:125:            provider="p", pricing_version="v1", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:129:        self.assertEqual(second["idempotency_key"], "idem-1")
./tests/test_m495_capability_repository.py:134:            provider="p", pricing_version="v1", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:136:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w1", now=100, lease_seconds=30))
./tests/test_m495_capability_repository.py:137:        self.assertFalse(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=120, lease_seconds=30))
./tests/test_m495_capability_repository.py:138:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=131, lease_seconds=30))
./tests/test_m495_capability_repository.py:143:            provider="p", pricing_version="v1", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:156:            provider="p", pricing_version="v1", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:160:        self.assertFalse(self.repo.claim_execution_attempt("idem-1", worker_id="w", now=1000, lease_seconds=30))
./tests/test_m495_capability_repository.py:165:            provider="p", pricing_version="v1", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:167:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w1", now=100, lease_seconds=10))
./tests/test_m495_capability_repository.py:168:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=111, lease_seconds=10))
./tests/test_m495_capability_repository.py:177:    def test_migration_has_durable_attempt_and_usage_idempotency_columns(self):
./tests/test_m495_capability_repository.py:184:        self.assertIn("idempotency_key text not null unique", normalized)
./tests/test_m495_capability_repository.py:201:            pricing_version="price-2026-10", idempotency_key="idem-1",
./tests/test_m495_capability_repository.py:242:        self.assertIn("idempotency_key=%s", lowered)
./tests/test_m495_capability_verification.py:51:    def test_random_bytes_cannot_claim_to_be_glb(self):
./tests/test_m495_golden_acceptance.py:50:    durable_idempotency = True
./tests/test_m495_golden_acceptance.py:74:    def submit(self, requirement, *, idempotency_key):
./tests/test_m495_golden_acceptance.py:76:        task_id = 'golden-' + hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]
./tests/test_m495_golden_acceptance.py:78:        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)
./tests/test_m495_provider_adapters_credentials.py:80:    def generate(self, request, *, idempotency_key=None):
./tests/test_m495_provider_adapters_credentials.py:81:        self.calls.append((request, idempotency_key))
./tests/test_m495_provider_adapters_credentials.py:97:    def test_media_adapter_passes_idempotency_and_returns_raw_payload_for_storage_layer(self):
./tests/test_m495_provider_adapters_credentials.py:104:            durable_idempotency=True,
./tests/test_m495_provider_adapters_credentials.py:107:        handle = provider.submit(req, idempotency_key='idem-77')
./tests/test_m495_provider_adapters_credentials.py:121:            quote_factory=media_quote, durable_idempotency=True,
./tests/test_m495_provider_adapters_credentials.py:125:            provider.submit(req, idempotency_key='x')
./tests/test_m495_provider_adapters_credentials.py:128:    def test_paid_media_adapter_must_explicitly_support_durable_idempotency(self):
./tests/test_m495_provider_adapters_credentials.py:129:        with self.assertRaisesRegex(ValueError, 'durable idempotency'):
./tests/test_m495_provider_adapters_credentials.py:133:                durable_idempotency=False, paid_external=True,
./tests/test_m495_provider_adapters_credentials.py:136:    def test_paid_synchronous_media_adapter_cannot_claim_crash_resumable_execution(self):
./tests/test_m495_provider_adapters_credentials.py:141:                durable_idempotency=True, paid_external=True,
./tests/test_m495_provider_adapters_credentials.py:158:        handle = provider.submit(req, idempotency_key='idem')
./tests/test_m495_provider_contracts.py:34:            idempotency_key="build-1:cap-media-3d-mesh-generate:meshy:v1",
./tests/test_m495_provider_contracts.py:41:        with self.assertRaisesRegex(ValueError, "idempotency_key"):
./tests/test_m495_provider_contracts.py:90:            def submit(self, requirement, *, idempotency_key): return ProviderTaskHandle("fake", "t1", requirement.id, idempotency_key)
./tests/test_m495_provider_contracts.py:96:        handle = provider.submit(req, idempotency_key="idem")
./tests/test_m495_provider_pricing_economics.py:55:    def test_duplicate_provider_capability_operation_is_rejected(self):
./tests/test_m495_provider_pricing_economics.py:61:        with self.assertRaisesRegex(ValueError, 'duplicate'):
./tests/test_m495_provider_router.py:24:    def submit(self, requirement, *, idempotency_key): raise NotImplementedError
./tests/test_m495_provider_router.py:82:    def test_duplicate_provider_name_fails(self):
./tests/test_m495_provider_router.py:85:        with self.assertRaisesRegex(ValueError, "duplicate provider"):
./tests/test_m495_skills_agents_registry.py:36:        with self.assertRaisesRegex(ValueError, "duplicate skill key"):
./tests/test_m4d1_atomic_accept.py:24:  - retry after process crash                         -> IdempotentRetryTests
./tests/test_m4d1_atomic_accept.py:25:  - duplicate accept delivery                         -> IdempotentRetryTests
./tests/test_m4d1_atomic_accept.py:346:# Retry after crash / duplicate delivery -- idempotent via the status gate
./tests/test_m4d1_atomic_accept.py:349:class IdempotentRetryTests(unittest.TestCase):
./tests/test_m4d1_atomic_accept.py:376:    def test_duplicate_delivery_while_still_ready_for_review_is_serialized_not_doubled(self):
./tests/test_m4d1_atomic_accept.py:377:        """A duplicate delivery that arrives WHILE the first is still
./tests/test_m4d1_atomic_accept.py:474:        # duplicates (a dict can't hold duplicates, but this also confirms
./tests/test_m4d2b_parity_and_worker.py:339:    def test_duplicate_delivery_of_the_same_modification_does_not_reexecute_or_duplicate_state(self):
./tests/test_m4d2b_parity_and_worker.py:341:        duplicate promotion/candidate state. Drives the real ambiguous
./tests/test_m4d2b_parity_and_worker.py:345:        duplicate delivery is two distinct queue messages that both name
./tests/test_m4d2b_parity_and_worker.py:357:            json={'followup': 'duplicate delivery check -- M4D2B_CLASSIFY:ambiguous please clarify'})
./tests/test_m4d2b_parity_and_worker.py:377:                          'a duplicate delivery must never re-run the job body or overwrite the terminal result')
./tests/test_m4d2b_parity_and_worker.py:380:        self.assertEqual(current.id, version_id, 'duplicate delivery must never promote/duplicate a version')
./tests/test_m4d2_live_fastapi_redis.py:264:                               headers=h, json={'followup': 'idempotency check'})
./tests/test_m4d2_live_fastapi_redis.py:280:        duplicate = self.client.post(f'/api/v28/projects/{project_id}/modifications/{mid}/accept', headers=h,
./tests/test_m4d2_live_fastapi_redis.py:282:        self.assertEqual(duplicate.status_code, 422, duplicate.text)
./tests/test_m4d2_live_fastapi_redis.py:283:        self.assertEqual(duplicate.json()['reason'], 'invalid_status')
./tests/test_m4d2_live_fastapi_redis.py:286:        self.assertEqual(len(history), 2, 'a duplicate HTTP accept request must never double-promote')
./tests/test_m4d2_live_postgres.py:553:    def test_duplicate_accept_delivery_after_success_is_not_double_promoted(self):
./tests/test_m4d2_live_postgres.py:560:        self.assertEqual(len(history), 2, 'a duplicate accept delivery must never create a second promotion')
./tests/test_m4_acceptance.py:527:# T -- modification retry is idempotent
./tests/test_m4_acceptance.py:531:    def test_T_duplicate_delivery_of_queued_and_of_a_completion_are_both_noops(self):
./tests/test_m4_worker.py:296:    def test_duplicate_delivery_is_a_noop(self):
./tests/test_m5_build_economics.py:58:    def test_unknown_revenue_cannot_claim_margin_pass(self):
./tests/test_m5_build_economics.py:187:    def test_claim_build_request_idempotency_inserts_once(self):
./tests/test_m5_build_economics.py:189:        created, replay = PostgresBuildRepository(None).claim_build_request_idempotency(
./tests/test_m5_build_economics.py:190:            cur, account_id='u1', internal_project_id='p1', idempotency_key='retry-key-0001',
./tests/test_m5_build_economics.py:196:        self.assertIn('ON CONFLICT (account_id, internal_project_id, idempotency_key) DO NOTHING',
./tests/test_m5_build_economics.py:202:    def test_claim_build_request_idempotency_replays_same_quote(self):
./tests/test_m5_build_economics.py:204:        created, replay = PostgresBuildRepository(None).claim_build_request_idempotency(
./tests/test_m5_build_economics.py:205:            cur, account_id='u1', internal_project_id='p1', idempotency_key='retry-key-0001',
./tests/test_m5_build_economics.py:213:    def test_caller_key_claim_is_scoped_to_account_and_project(self):
./tests/test_m5_build_economics.py:217:            created, replay = repository.claim_build_request_idempotency(
./tests/test_m5_build_economics.py:218:                cur, account_id='u1', internal_project_id=project, idempotency_key='shared-key-0001',
./tests/test_m5_build_economics.py:224:        self.assertIn('(account_id, internal_project_id, idempotency_key)', cur.calls[0][0])
./tests/test_m5_build_economics.py:228:    def test_claim_build_request_idempotency_rejects_request_quote_or_version_changes(self):
./tests/test_m5_build_economics.py:242:                    PostgresBuildRepository(None).claim_build_request_idempotency(
./tests/test_m5_build_economics.py:243:                        cur, account_id='u1', internal_project_id='p1', idempotency_key='retry-key-0001',
./tests/test_m5_build_economics.py:257:        request_fp, quote_fp, quote_version = investor_app._m5_build_idempotency_fingerprints(**args)
./tests/test_m5_build_economics.py:259:        changed_request_fp, changed_quote_fp, _ = investor_app._m5_build_idempotency_fingerprints(**changed)
./tests/test_m5_build_economics.py:260:        changed_version_fp = investor_app._m5_build_idempotency_fingerprints(
./tests/test_m5_build_economics.py:263:        changed_category_fp = investor_app._m5_build_idempotency_fingerprints(
./tests/test_m5_build_economics.py:392:             idempotency_result=(True, None), idempotency_key='caller-retry-key-1'):
./tests/test_m5_build_economics.py:409:        if isinstance(idempotency_result, BaseException):
./tests/test_m5_build_economics.py:410:            jobs.claim_build_request_idempotency.side_effect = idempotency_result
./tests/test_m5_build_economics.py:412:            jobs.claim_build_request_idempotency.return_value = idempotency_result
./tests/test_m5_build_economics.py:413:        jobs.claim_contract_build.return_value = existing_build
./tests/test_m5_build_economics.py:436:                                               idempotency_key=idempotency_key)
./tests/test_m5_build_economics.py:451:        claim = jobs.claim_build_request_idempotency.call_args.kwargs
./tests/test_m5_build_economics.py:452:        self.assertEqual(claim['idempotency_key'], 'caller-retry-key-1')
./tests/test_m5_build_economics.py:477:        self.assertEqual((body['build_id'], body['status'], body['duplicate']), ('bld_first', 'running', True))
./tests/test_m5_build_economics.py:478:        jobs.claim_build_request_idempotency.assert_called_once()
./tests/test_m5_build_economics.py:485:            idempotency_result=(False, ('bld_replay', 'ready')),
./tests/test_m5_build_economics.py:489:        self.assertEqual((body['build_id'], body['status'], body['duplicate']),
./tests/test_m5_build_economics.py:491:        jobs.claim_contract_build.assert_not_called()
./tests/test_m5_build_economics.py:499:                    idempotency_result=(False, ('bld_crashed', status)),
./tests/test_m5_build_economics.py:503:                self.assertEqual((body['build_id'], body['status'], body['duplicate']),
./tests/test_m5_build_economics.py:511:            idempotency_result=ValueError('idempotency key reused with different request or quote'),
./tests/test_m5_build_economics.py:514:        self.assertEqual(exc.detail['error'], 'idempotency_conflict')
./tests/test_m5_build_economics.py:519:        response, reserve, enqueue, jobs, exc = self._run(idempotency_key=None)
./tests/test_m5_build_economics.py:522:        jobs.claim_build_request_idempotency.assert_not_called()
./tests/test_m5_build_economics.py:523:        jobs.claim_contract_build.assert_called_once()
./tests/test_m5_build_economics.py:528:        _, reserve, enqueue, jobs, exc = self._run(idempotency_key='not a valid key')
./tests/test_m5_build_economics.py:530:        self.assertEqual(exc.detail['error'], 'invalid_idempotency_key')
./tests/test_m5_build_economics.py:531:        jobs.claim_build_request_idempotency.assert_not_called()
./tests/test_m5_economics_reconciliation.py:27:    provisioning_idempotency_key)
./tests/test_m5_economics_reconciliation.py:130:            key = provisioning_idempotency_key(profile_key="managed_web_saas_v1", project_id="prj_econ",
./tests/test_m5_economics_reconciliation.py:136:                idempotency_key=key, provisioner="p", secret_references={"x": "vault:secret/data/x"}))
./tests/test_m5_generated_app_storage_isolation.py:82:                                 environment=environment, idempotency_key=f"k_{project_id}_{environment}".ljust(64, "x"))
./tests/test_m5_generated_app_storage_isolation.py:137:                                 idempotency_key="k" * 64)
./tests/test_m5_generated_app_storage_isolation.py:159:                                 idempotency_key="k" * 64)
./tests/test_m5_infrastructure_contracts.py:22:    provisioning_idempotency_key,
./tests/test_m5_infrastructure_contracts.py:69:    def provision(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./tests/test_m5_infrastructure_contracts.py:71:        self.calls.append((kind, project_id, environment, idempotency_key))
./tests/test_m5_infrastructure_contracts.py:77:            binding_id="ib_" + idempotency_key[:20], profile_key=self.profile_key,
./tests/test_m5_infrastructure_contracts.py:79:            status=self._status, resource_name=name, idempotency_key=idempotency_key,
./tests/test_m5_infrastructure_contracts.py:145:            resource_name="ga_x_preview_database", idempotency_key="k" * 64,
./tests/test_m5_infrastructure_contracts.py:183:class NamingAndIdempotencyTests(unittest.TestCase):
./tests/test_m5_infrastructure_contracts.py:195:    def test_idempotency_key_binds_profile_project_environment_kind(self):
./tests/test_m5_infrastructure_contracts.py:197:        k1 = provisioning_idempotency_key(**base)
./tests/test_m5_infrastructure_contracts.py:198:        self.assertEqual(k1, provisioning_idempotency_key(**base))
./tests/test_m5_infrastructure_contracts.py:202:            self.assertNotEqual(k1, provisioning_idempotency_key(**changed))
./tests/test_m5_infrastructure_contracts.py:249:                                 idempotency_key=provisioning_idempotency_key(
./tests/test_m5_infrastructure_contracts.py:269:    def test_provisioning_is_idempotent(self):
./tests/test_m5_infrastructure_contracts.py:301:            self.assertNotEqual(preview[kind].idempotency_key, prod[kind].idempotency_key)
./tests/test_m5_llm_usage_evidence.py:134:    def test_retry_or_rerecord_does_not_duplicate_rows(self):
./tests/test_m5_llm_usage_evidence.py:204:        handle = provider.submit(req, idempotency_key="idem_1")
./tests/test_m5_llm_usage_evidence.py:214:        result2 = provider2.collect(provider2.submit(req, idempotency_key="idem_2"))
./tests/test_m5_managed_web_saas_profile.py:3:All backends here are in-test doubles. They let us prove naming, idempotency,
./tests/test_m5_managed_web_saas_profile.py:189:    def test_idempotent_second_ensure_does_not_reprovision(self):
./tests/test_m5_managed_web_saas_profile.py:252:            environment="production", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:282:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:289:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:295:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:301:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:307:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:311:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:315:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:321:                                 environment="preview", idempotency_key="k" * 64)
./tests/test_m5_managed_web_saas_profile.py:388:        self.assertIn("unique (idempotency_key)", sql)
./tests/test_m5_managed_web_saas_profile.py:394:    def test_repository_upsert_is_idempotency_keyed_and_tenant_guarded(self):
./tests/test_m5_managed_web_saas_profile.py:418:            status=BindingStatus.LIVE, resource_name="ga_x", idempotency_key="k" * 64, provisioner="p",
./tests/test_m5_managed_web_saas_profile.py:429:        self.assertIn("ON CONFLICT (idempotency_key) DO UPDATE", insert[0][0])
./tests/test_m5_media_provider_adapters.py:58:    def __init__(self, *, image=None, honor_idempotency=False, fail=False, rate_limit_once=False):
./tests/test_m5_media_provider_adapters.py:60:        self.honor_idempotency = honor_idempotency
./tests/test_m5_media_provider_adapters.py:68:        self.idempotency_headers: list[str | None] = []
./tests/test_m5_media_provider_adapters.py:77:            key = req.headers.get("Idempotency-key")
./tests/test_m5_media_provider_adapters.py:78:            self.idempotency_headers.append(key)
./tests/test_m5_media_provider_adapters.py:79:            if self.honor_idempotency and key in self.by_key:
./tests/test_m5_media_provider_adapters.py:161:        self.assertTrue(provider.durable_idempotency)
./tests/test_m5_media_provider_adapters.py:180:        handle = provider.submit(REQ, idempotency_key="cap_abc")
./tests/test_m5_media_provider_adapters.py:214:        handle = provider.submit(REQ, idempotency_key="cap_cost")
./tests/test_m5_media_provider_adapters.py:222:        handle = provider.submit(REQ, idempotency_key="cap_bad")
./tests/test_m5_media_provider_adapters.py:230:        handle = provider.submit(REQ, idempotency_key="cap_fail")
./tests/test_m5_media_provider_adapters.py:238:        handle = provider.submit(REQ, idempotency_key="cap_cancel")
./tests/test_m5_media_provider_adapters.py:243:class IdempotencyAndResumeTests(unittest.TestCase):
./tests/test_m5_media_provider_adapters.py:247:        first = _provider(api, journal=journal).submit(REQ, idempotency_key="cap_same")
./tests/test_m5_media_provider_adapters.py:248:        second = _provider(api, journal=journal).submit(REQ, idempotency_key="cap_same")
./tests/test_m5_media_provider_adapters.py:255:        handle = _provider(api, journal=journal).submit(REQ, idempotency_key="cap_resume")
./tests/test_m5_media_provider_adapters.py:261:    def test_ambiguous_crash_window_fails_closed_without_idempotency_support(self):
./tests/test_m5_media_provider_adapters.py:266:            _provider(api, journal=journal).submit(REQ, idempotency_key="cap_window")
./tests/test_m5_media_provider_adapters.py:267:        self.assertEqual(api.created, [])  # never a blind duplicate paid submit
./tests/test_m5_media_provider_adapters.py:269:    def test_ambiguous_window_resubmits_when_provider_honors_idempotency(self):
./tests/test_m5_media_provider_adapters.py:270:        api = FakePredictionAPI(honor_idempotency=True)
./tests/test_m5_media_provider_adapters.py:272:        env = dict(ENV, OMNI_IMAGE_PROVIDER_IDEMPOTENCY_HEADER="Idempotency-Key")
./tests/test_m5_media_provider_adapters.py:275:        handle = _provider(api, env=env, journal=journal).submit(REQ, idempotency_key="cap_window2")
./tests/test_m5_media_provider_adapters.py:278:        self.assertEqual(api.idempotency_headers, ["cap_window2"])
./tests/test_m5_media_provider_adapters.py:284:            provider.submit(REQ, idempotency_key="cap_429")
./tests/test_m5_media_provider_adapters.py:288:        handle = provider.submit(REQ, idempotency_key="cap_429")
./tests/test_m5_media_provider_adapters.py:294:        handle = provider.submit(REQ, idempotency_key="cap_sleep")
./tests/test_m5_media_provider_adapters.py:355:        self.assertIn("idempotency_key text primary key", sql)
./tests/test_m5_media_provider_adapters.py:379:        self.assertTrue(any("ON CONFLICT (idempotency_key) DO NOTHING" in c for c in calls))
./tests/test_m5_migration_numbering.py:16:    def test_no_duplicate_versions(self):
./tests/test_m5_migration_numbering.py:17:        migrations = discover_migrations(ROOT / "infra/postgres")  # raises on duplicates
./tests/test_m5_project_lifecycle.py:35:    def test_delete_is_tombstone_idempotent_and_history_row_remains(self):
./tests/test_m5_project_lifecycle.py:37:        second = self.service.delete_project(owner_id=self.owner, project_id=self.project.id, reason="duplicate_request")
./tests/test_m5_project_lifecycle.py:72:        duplicate = ProjectRecord(
./tests/test_m5_project_lifecycle.py:80:            self.repo.create(duplicate)
./tests/test_m5_ssrf_guard.py:148:        handle = provider.submit(REQ, idempotency_key="cap_ssrf")
./tests/test_maintenance_live_postgres.py:73:        self.assertFalse(maintenance.reap_build(self.jobs, self.subs, bid, 45))  # idempotent
./tests/test_model_catalog_routing.py:83:    def test_duplicate_names_rejected(self):
./tests/test_model_gateway_idempotency.py:5:                                     idempotency_key_for)
./tests/test_model_gateway_idempotency.py:33:    key = idempotency_key_for(build_id='b', task='codegen', attempt=2)
./tests/test_model_gateway_idempotency.py:34:    gw.complete(system='s', user='u', idempotency_key=key)
./tests/test_model_gateway_idempotency.py:35:    assert seen.get('idempotency-key') == key
./tests/test_model_gateway_idempotency.py:36:    assert gw.last_idempotency_key == key
./tests/test_model_gateway_idempotency.py:42:    assert 'idempotency-key' not in seen
./tests/test_model_gateway_idempotency.py:43:    assert gw.last_idempotency_key is None
./tests/test_model_gateway_idempotency.py:46:    a = idempotency_key_for(build_id='b', task='t', attempt=1)
./tests/test_model_gateway_idempotency.py:47:    assert a == idempotency_key_for(build_id='b', task='t', attempt=1)
./tests/test_model_gateway_idempotency.py:48:    assert a != idempotency_key_for(build_id='b', task='t', attempt=2)
./tests/test_modification_repository.py:6:round-tripping), the outbox relay's one-row-per-transaction/duplicate-safe
./tests/test_modification_repository.py:20:duplicate that coverage without adding anything).
./tests/test_modification_repository.py:309:    def test_transition_running_is_a_noop_on_duplicate_delivery(self):
./tests/test_modification_repository.py:360:    def test_duplicate_completion_is_a_noop_and_never_double_writes_the_candidate(self):
./tests/test_plan_driven_execution.py:370:        self.assertEqual(merge_approved_criteria(spec, APPROVED), spec)          # idempotent
./tests/test_provider_quota_and_dialects.py:333:        self.assertEqual([r.outcome for r in gw.recorder.records], ['ok'])   # completed in place, not duplicated
./tests/test_qstash_scheduler.py:100:    def test_404_get_and_cancel_are_idempotent(self):
./tests/test_qstash_scheduler.py:153:                                                destination=TARGET, claim_once=lambda jti, exp: True)
./tests/test_qstash_scheduler.py:160:                          claim_once=lambda jti, exp: self.fail("invalid signature must not claim"))
./tests/test_qstash_scheduler.py:173:                                       claim_once=lambda *args:self.fail("must not claim"))
./tests/test_qstash_scheduler.py:182:        kwargs = dict(signature=signed(), body=b'{"probe":true}', destination=TARGET, claim_once=claim)
./tests/test_qstash_scheduler.py:184:        with self.assertRaisesRegex(QStashError, "duplicate"):
./tests/test_qstash_scheduler.py:188:        kwargs["claim_once"] = unavailable
./tests/test_qstash_scheduler.py:196:                self.receiver().verify(signature=signature, body=b"", destination=TARGET, claim_once=None)
./tests/test_qstash_scheduler.py:226:            binding = p.provision(req, tenant_id="u", project_id="p", environment="preview", idempotency_key="k"*64)
./tests/test_r2_generated_credentials.py:125:        binding = p.provision(req, tenant_id="u", project_id="prj_r2", environment="preview", idempotency_key="k" * 64)
./tests/test_release_policy.py:190:    """Migration 035: immutable, idempotent stage rows bound to the artifact digest."""
./tests/test_release_policy.py:214:            persist(self.pool, report, tenant_key='tenant-x')            # duplicate delivery: no new rows
./tests/test_replicate_connection.py:45:    first = provider.submit(req, idempotency_key='build-icon')
./tests/test_replicate_connection.py:46:    second = provider.submit(req, idempotency_key='build-icon')
./tests/test_spec_repository.py:64:    def test_save_writes_jsonb_and_is_idempotent_on_conflict(self):
./tests/test_v13_core.py:5:from omni_prod.idempotency import request_fingerprint, validate_key
./tests/test_v13_core.py:11:class IdempotencyTests(unittest.TestCase):
./tests/test_v19_reliability.py:6:from omni_prod.outbox import deterministic_dedupe_key, new_event
./tests/test_v19_reliability.py:31:    def test_dedupe_is_deterministic(self):
./tests/test_v19_reliability.py:32:        a = deterministic_dedupe_key(
./tests/test_v19_reliability.py:35:        b = deterministic_dedupe_key(
./tests/test_v19_reliability.py:40:    def test_new_event_unique_id_same_dedupe(self):
./tests/test_v19_reliability.py:44:        self.assertEqual(a.dedupe_key, b.dedupe_key)
./tests/test_v26_universal_pro.py:24:    def test_duplicate_email_and_bad_password(self):
./tests/test_v28_148ai_launch.py:196:    def test_stripe_signature_and_idempotent_plan_assignment(self):
./tests/test_v28_148ai_launch.py:209:        self.assertTrue(second['duplicate']); self.assertFalse(second['processed'])
./tests/test_worker_deploy_recovery.py:330:        for f in ('014_real_running_preview.sql', '037_intake_budget_reservations.sql'):      # idempotent; rolled back too
./tests/test_worker_deploy_recovery.py:381:                    conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, quoted_usd, quote, state, claim_token, lease_expires_at) "
./tests/test_worker_deploy_recovery.py:388:                conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, quoted_usd, quote, state) "
./tests/test_worker_repository_parity.py:92:    def test_inserts_every_requirement_idempotently(self):
```


## B1 — כשלים שקטים

```
-- except: --
-- except Exception --
./omni_prod/active_jobs.py:39:    except Exception as exc:                                    # a failed query is missing information, never "quiet"
./omni_prod/active_jobs.py:43:        except Exception:
./omni_prod/active_jobs.py:107:    except Exception as exc:
./omni_prod/active_jobs.py:145:    except Exception as exc:
./omni_prod/active_jobs.py:183:        except Exception as exc:                        # anything unexpected is also "cannot verify"
./omni_prod/agent_os/recorder.py:44:        except Exception as exc:  # recording must never fail the build
./omni_prod/agent_os/recorder.py:312:        except Exception:
./omni_prod/agent_os/recorder.py:487:        except Exception:
./omni_prod/attachments.py:219:        except Exception:
./omni_prod/attachments.py:222:            except Exception:
./omni_prod/attempt_ledger.py:187:        except Exception as exc:
./omni_prod/auth.py:48:    except Exception as exc: raise AuthError('invalid token') from exc
./omni_prod/autonomous_core.py:83:        except Exception:  # a snapshot must never change the build
./omni_prod/backup.py:157:        except Exception as exc:
./omni_prod/backup.py:216:    except Exception as exc:
./omni_prod/behavior_acceptance.py:62:    except Exception:
./omni_prod/behavior_acceptance.py:74:except Exception:
./omni_prod/behavior_acceptance.py:160:        except Exception as exc:
./omni_prod/benchmark_suite.py:79:            except Exception as exc:
./omni_prod/browser_probe.py:50:    except Exception:
./omni_prod/browser_probe.py:184:        except Exception as exc:
./omni_prod/build_contract_repository.py:111:        except Exception as exc:
./omni_prod/build_control.py:50:        except Exception:
./omni_prod/build_control.py:60:        except Exception:  # pragma: no cover - logging must never fail a build
./omni_prod/build_control.py:69:        except Exception:
./omni_prod/build_outbox_relay.py:56:            except Exception as exc:  # keep looping; report honestly
./omni_prod/conversation/memory.py:32:    except Exception as exc:  # a missing table on an older database: say so, never fail the page
./omni_prod/conversation/supervisor.py:467:        except Exception:
./omni_prod/conversation/supervisor.py:475:        except Exception:
./omni_prod/db.py:68:            except Exception as exc:
./omni_prod/db.py:100:    except Exception:
./omni_prod/demo_project.py:122:        except Exception as exc:
./omni_prod/demo_project.py:130:        except Exception as exc:
./omni_prod/evidence_export.py:102:        except Exception:
./omni_prod/evidence_export.py:142:    except Exception:  # pragma: no cover - stdin use on an older image
./omni_prod/evidence_export.py:243:            except Exception as exc:
./omni_prod/gate_replay.py:67:        except Exception as exc:
./omni_prod/gate_replay.py:139:        except Exception as exc:
./omni_prod/gate_replay.py:200:    except Exception as exc:
./omni_prod/identity_lifecycle.py:258:        except Exception as exc:
./omni_prod/intake/interpreter.py:326:        except Exception as exc:  # provider down / budget: the conversation continues deterministically
./omni_prod/intake/mode.py:111:    except Exception as exc:  # spend unknown -> never risk an uncapped call
./omni_prod/intake/reservation_worker.py:106:    except Exception as exc:
./omni_prod/intake/reservation_worker.py:116:    except Exception as exc:
./omni_prod/intake/reservation_worker.py:176:            except Exception as exc:
./omni_prod/intake/worker_route.py:75:        except Exception as exc:   # BudgetError, ValueError, schema/DB errors: fail closed, no paid call
./omni_prod/intake/worker_route.py:82:            except Exception as exc:    # queue down: nothing was sent, so give the money back now
./omni_prod/intelligence/health.py:144:        except Exception:
./omni_prod/intelligence/health.py:190:        except Exception:
./omni_prod/intelligence/health.py:200:        except Exception:
./omni_prod/investor_app.py:774:    except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:1000]) from exc
./omni_prod/investor_app.py:781:        except Exception as exc:
./omni_prod/investor_app.py:900:    except Exception as exc: raise HTTPException(503,str(exc)[:1000]) from exc
./omni_prod/investor_app.py:952:    except Exception:
./omni_prod/investor_app.py:1048:    except Exception:
./omni_prod/investor_app.py:1229:    except Exception as exc: raise HTTPException(503,str(exc)[:1000]) from exc
./omni_prod/investor_app.py:1275:    except Exception:
./omni_prod/investor_app.py:1404:    except Exception as exc:
./omni_prod/investor_app.py:1412:    except Exception as exc:
./omni_prod/investor_app.py:1614:        except Exception:
./omni_prod/investor_app.py:1727:    except Exception as exc:
./omni_prod/investor_app.py:1911:        except Exception:
./omni_prod/investor_app.py:2409:        except Exception:
./omni_prod/investor_app.py:2582:    except Exception as exc:
./omni_prod/investor_app.py:2668:        except Exception as exc:
./omni_prod/investor_app.py:2763:    except Exception:
./omni_prod/investor_app.py:3103:    except Exception:
./omni_prod/investor_app.py:3112:    except Exception:
./omni_prod/investor_app.py:3122:    except Exception:
./omni_prod/investor_app.py:3182:    except Exception:
./omni_prod/investor_app.py:3197:    except Exception as exc:
./omni_prod/investor_app.py:3272:    except Exception as exc:
./omni_prod/investor_app.py:3335:    except Exception:
./omni_prod/maintenance.py:208:    except Exception as exc:
./omni_prod/maintenance.py:214:            except Exception as exc:
./omni_prod/maintenance.py:216:    except Exception as exc:
./omni_prod/maintenance.py:222:            except Exception as exc:
./omni_prod/maintenance.py:224:    except Exception as exc:
./omni_prod/maintenance.py:229:        except Exception as exc:
./omni_prod/maintenance.py:235:        except Exception as exc:
./omni_prod/maintenance.py:281:            except Exception:
./omni_prod/media_gateway.py:41:        except Exception as exc: raise MediaGatewayError(f'{self.endpoint.name} media generation failed: {exc}') from exc
./omni_prod/media_gateway.py:44:        except Exception as exc: raise MediaGatewayError('invalid media provider response') from exc
./omni_prod/migration_runner.py:76:                except Exception as exc:
./omni_prod/model_gateway.py:38:    except Exception:
./omni_prod/model_probe.py:42:        except Exception as exc:
./omni_prod/postdeploy_checks.py:135:        except Exception:
./omni_prod/postdeploy_checks.py:324:    except Exception as exc:  # the check outcome is already printed; storage is best effort
./omni_prod/postdeploy_checks.py:367:        except Exception as exc:
./omni_prod/postdeploy_checks.py:640:    except Exception as exc:
./omni_prod/preview_access.py:152:            except Exception:
./omni_prod/preview_durability.py:64:        except Exception:
./omni_prod/preview_durability.py:106:    except Exception as exc:
./omni_prod/preview_durability.py:112:            except Exception:
./omni_prod/preview_inspector.py:195:            except Exception:
./omni_prod/preview_router.py:93:        except Exception:
./omni_prod/preview_router.py:147:                except Exception:
./omni_prod/preview_runtime.py:342:        except Exception as exc:  # connection refused/reset/timeouts while booting
./omni_prod/preview_runtime.py:471:        except Exception:
./omni_prod/preview_runtime.py:491:        except Exception:
./omni_prod/preview_smoke.py:51:    except Exception:
./omni_prod/preview_smoke.py:70:            except Exception:
./omni_prod/preview_smoke.py:81:    except Exception as e:
./omni_prod/preview_smoke.py:87:except Exception:
./omni_prod/preview_smoke.py:125:        except Exception as exc:  # sandbox unavailable: the build cannot be verified
./omni_prod/product_review.py:71:        except Exception as exc:  # outage: say so, never invent a review
./omni_prod/project_lifecycle.py:169:        except Exception as exc:
./omni_prod/providers/image_provider.py:81:    except Exception:
./omni_prod/providers/managed_web_saas.py:244:    except Exception:
./omni_prod/providers/managed_web_saas.py:270:    except Exception as exc:  # status codes from HTTPError, otherwise unreachable
./omni_prod/providers/managed_web_saas.py:386:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:394:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:450:        except Exception:
./omni_prod/providers/managed_web_saas.py:459:        except Exception:
./omni_prod/providers/managed_web_saas.py:495:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:684:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:699:                except Exception as exc:
./omni_prod/providers/qstash_scheduler.py:82:        except Exception:
./omni_prod/providers/qstash_scheduler.py:190:        except Exception:
./omni_prod/providers/qstash_scheduler.py:195:        except Exception:
./omni_prod/providers/replicate_connection.py:71:    except Exception:
./omni_prod/providers/replicate_connection.py:96:    except Exception:
./omni_prod/providers/replicate_image_test.py:74:        except Exception as exc:
./omni_prod/providers/replicate_image_test.py:110:            except Exception as exc:
./omni_prod/quality_gate.py:55:    except Exception as exc:
./omni_prod/queueing.py:78:    except Exception:
./omni_prod/registry_audit.py:74:    except Exception:
./omni_prod/registry_audit.py:247:    except Exception:
./omni_prod/registry_audit.py:257:    except Exception as exc:
./omni_prod/rehearsal.py:36:    except Exception as exc:
./omni_prod/rehearsal.py:40:    except Exception as exc:
./omni_prod/release_gate.py:25:    except Exception as exc:
./omni_prod/routed_gateway.py:191:            except Exception as exc:
./omni_prod/routed_gateway.py:204:        except Exception as exc:
./omni_prod/routed_gateway.py:421:                except Exception as exc:
./omni_prod/routed_gateway.py:440:                                except Exception as fitted_exc:
./omni_prod/sandbox.py:142:    except Exception:
./omni_prod/sandbox_service.py:64:    except Exception as exc: raise HTTPException(400,'invalid request') from exc
./omni_prod/secrets_manager.py:40:        except Exception as exc: raise SecretResolutionError('vault resolution failed') from exc
./omni_prod/secrets_manager.py:101:        except Exception as exc:
./omni_prod/secrets_manager.py:207:        except Exception:
./omni_prod/security_testing.py:39:    except Exception as exc:
./omni_prod/storage.py:65:        except Exception:
./omni_prod/storage.py:180:        except Exception:
./omni_prod/stripe_billing.py:78:        except Exception as exc:
./omni_prod/stripe_billing.py:99:    except Exception as exc:
./omni_prod/stripe_billing.py:110:    except Exception as exc:
./omni_prod/stripe_billing.py:159:                except Exception as exc:
./omni_prod/visual_qa.py:57:    except Exception:
./omni_prod/visual_qa.py:213:            except Exception as exc:
./omni_prod/visual_qa.py:229:                except Exception as exc:  # evidence storage must not change the outcome
./omni_prod/web_saas_acceptance.py:254:                except Exception as exc:
./omni_prod/web_saas_acceptance.py:262:                    except Exception:
./omni_prod/worker_tasks.py:213:    except Exception:
./omni_prod/worker_tasks.py:236:    except Exception:
./omni_prod/worker_tasks.py:266:    except Exception:  # evidence must never fail a build
./omni_prod/worker_tasks.py:302:    except Exception:
./omni_prod/worker_tasks.py:433:    except Exception:
./omni_prod/worker_tasks.py:582:        except Exception:
./omni_prod/worker_tasks.py:861:    except Exception as exc:
./omni_prod/worker_tasks.py:956:            except Exception:
./omni_prod/worker_tasks.py:965:    except Exception:
./omni_prod/worker_tasks.py:985:        except Exception:
./omni_prod/worker_tasks.py:991:    except Exception as exc:
./omni_prod/worker_tasks.py:1168:    except Exception as exc:
./omni_prod/worker_tasks.py:1261:    except Exception as exc:
./omni_prod/worker_tasks.py:1265:    except Exception as exc:
./omni_prod/worker_tasks.py:1270:        except Exception as exc:
./omni_prod/worker_tasks.py:1301:    except Exception as exc:
./omni_prod/worker_tasks.py:1327:            except Exception as exc:
./omni_prod/worker_tasks.py:1378:                except Exception as exc:
./omni_prod/worker_tasks.py:1388:                    except Exception as exc:
./omni_prod/worker_tasks.py:1393:                    except Exception:
./omni_prod/worker_tasks.py:1398:                        except Exception as exc:
./omni_prod/worker_tasks.py:1422:                        except Exception:
./omni_prod/worker_tasks.py:1426:    except Exception as exc:
./omni_prod/worker_tasks.py:1476:    except Exception:
./omni_prod/workspace.py:191:        except Exception:
./scripts/run_http_load.py:11:    except Exception as exc: return 0,int((time.perf_counter()-t)*1000),str(exc)[:200]
./scripts/run_v25_offline_benchmark.py:25:    except Exception as exc:
./scripts/run_v28_http_acceptance.py:26:        except Exception: payload=raw.decode('utf-8','ignore')
./scripts/run_v28_http_acceptance.py:44:        except Exception: pass
./scripts/run_v28_offline_benchmark.py:25:    except Exception as exc:
./tests/integration/test_m5_build_economics_postgres.py:31:    except Exception as exc:
./tests/integration/test_m5_build_economics_postgres.py:98:            except Exception as exc:
./tests/integration/test_m5_build_economics_postgres.py:164:            except Exception as exc:
./tests/m4d2b_local_model_server.py:129:        except Exception as exc:  # pragma: no cover - defensive, surfaces as a real HTTP 500
./tests/test_agent_os.py:153:    except Exception as exc:
./tests/test_behavior_acceptance_in_build.py:21:    except Exception:
./tests/test_build_cancel_and_log.py:130:    except Exception as exc:
./tests/test_conversation_os.py:408:    except Exception as exc:
./tests/test_crash_recovery_and_change_parity.py:21:    except Exception as exc:
./tests/test_discovery_and_approval.py:92:    except Exception as exc:
./tests/test_golden_mod_path_live_postgres.py:30:    except Exception as exc:
./tests/test_golden_mod_path_live_postgres.py:230:            except Exception as exc:  # surfaced in the assertion message
./tests/test_intake_budget_pg.py:48:        except Exception as exc:
./tests/test_intake_budget_pg.py:102:            except Exception as exc:            # collected and asserted by the caller
./tests/test_intake_budget_pg.py:296:            except Exception as exc:
./tests/test_janitor_redispatch.py:50:    except Exception as exc:
./tests/test_legacy_paths_guard.py:9:except Exception:  # pragma: no cover - fastapi absent in some local environments
./tests/test_m49_clean_room.py:74:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m49_clean_room.py:78:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m49_lifecycle.py:50:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m49_sandbox_security.py:78:except Exception as e:
./tests/test_m49_sandbox_security.py:87:except Exception as e:
./tests/test_m49_sandbox_security.py:94:except Exception as e:
./tests/test_m49_sandbox_security.py:102:except Exception as e:
./tests/test_m49_sandbox_security.py:108:except Exception as e:
./tests/test_m4d1_atomic_accept.py:588:            except Exception:
./tests/test_m4d2b_parity_and_worker.py:67:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2b_parity_and_worker.py:71:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2_live_fastapi_redis.py:58:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2_live_fastapi_redis.py:62:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2_live_postgres.py:70:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_maintenance_live_postgres.py:20:    except Exception as exc:
./tests/test_plan_driven_execution.py:248:            except Exception:
./tests/test_preview_access.py:21:    except Exception as exc:
./tests/test_quality_repairable.py:70:        except Exception as exc:  # patch object shape differs
./tests/test_real_docker_drain_recovery.py:66:    except Exception:
./tests/test_visual_edit.py:100:    except Exception as exc:
./tools/ui_visual_edit/preview_host.py:52:                except Exception:
./tools/ui_visual_edit/walkthrough.py:50:        except Exception:
-- pass אחרי except --
8:./omni_prod/active_jobs.py-44-            pass
65:./omni_prod/attachments.py-223-                pass
153:./omni_prod/build_outbox_relay.py-57-                print(f'build_outbox_relay: pass failed: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
356:./omni_prod/intelligence/health.py-191-            pass
359:./omni_prod/intelligence/health.py-201-            pass
438:./omni_prod/investor_app.py-901-    return {'mode':'v26-live-autonomous','status':result.status,'release_ready':result.status=='ready' and quality.passed and security.passed,
730:./omni_prod/investor_app.py-1844-                pass
1054:./omni_prod/model_gateway.py-48-        pass
1103:./omni_prod/postdeploy_checks.py-136-            pass
1121:./omni_prod/preview_access.py-153-                pass
1130:./omni_prod/preview_durability.py-113-                pass
1139:./omni_prod/preview_router.py-94-            pass
1175:./omni_prod/preview_smoke.py-71-                pass
1285:./omni_prod/providers/replicate_connection.py-97-        pass
1291:./omni_prod/providers/replicate_image_test.py-109-                pass  # In-memory test store: no saved result yet.
1372:./omni_prod/routed_gateway.py-297-                pass
1393:./omni_prod/sandbox.py-143-        pass
1563:./omni_prod/worker_tasks.py-303-        pass
1685:./scripts/run_v28_http_acceptance.py:44:        except Exception: pass
1853:./tests/test_intake_budget_pg.py-99-                pass
1936:./tests/test_m49_sandbox_security.py-181-        pass
1939:./tests/test_m49_sandbox_security.py-186-        pass
1945:./tests/test_m4d1_atomic_accept.py-174-            pass
2120:./tests/test_plan_driven_execution.py-249-                pass
2240:./tools/ui_visual_edit/walkthrough.py-51-            pass
```


## B2 — לוגים חסרים

```
-- print( בקוד פרודקשן --
omni_prod/active_jobs.py:176:        print('::error title=active-jobs::bad arguments; NOT draining')
omni_prod/active_jobs.py:186:        print(json.dumps(_brief(snap), ensure_ascii=False))
omni_prod/active_jobs.py:189:            print('::notice title=active-jobs::verified quiet; draining is safe'
omni_prod/active_jobs.py:194:                print(f"::error title=active-jobs::NOT draining: the state could not be verified: {snap['errors']}")
omni_prod/active_jobs.py:196:            print(f"::error title=active-jobs::NOT draining: running work remains after {wait:g} min: {snap['blocking'][:10]}")
omni_prod/agent_os/audit.py:180:    print(json.dumps(result['summary']))
omni_prod/agent_os/audit.py:182:        print('INFLATION', p)
omni_prod/agent_os/departments.py:212:        print('\n'.join(probs))
omni_prod/agent_os/departments.py:218:    print(json.dumps(m['summary']))
omni_prod/agent_os/meta.py:218:            print(f'::error title=regression guardian::{p}')
omni_prod/agent_os/meta.py:219:        print(f'::notice title=regression guardian::{len(problems)} problem(s)')
omni_prod/agent_os/meta.py:222:        print(json.dumps(required_layers(argv[1:])))
omni_prod/agent_os/meta.py:229:        print(f"::notice title=quality gate::{json.dumps(verdict)}")
omni_prod/agent_os/meta.py:231:    print('usage: python -m omni_prod.agent_os.meta regression JUNIT | layers FILES... | gate [JUNIT]')
omni_prod/autonomous_core.py:58:        original_fingerprint = self._fingerprint(repo)
omni_prod/autonomous_core.py:70:    def _fingerprint(repo: dict[str, str]) -> str:
omni_prod/autonomous_core.py:140:        seen = {self._fingerprint(repo)}
omni_prod/autonomous_core.py:173:            fingerprint = self._fingerprint(candidate)
omni_prod/backup.py:217:        print(f'::error title=backup {cmd}::{type(exc).__name__}: {str(exc)[:400]}')
omni_prod/backup.py:220:    print(f"::{'notice' if ok else 'error'} title=backup {cmd}::" + json.dumps(out, default=str)[:3500])
omni_prod/behavior_acceptance.py:77:print("BEHAVIOR-ACCEPTANCE " + json.dumps(report, ensure_ascii=False))
omni_prod/billing.py:38:    def fingerprint(self):
omni_prod/brief_repository.py:96:                             brief.fingerprint(), request_key))
omni_prod/brief_repository.py:104:        return BriefRow(bid, project_id, expected_revision + 1, brief, complete(brief), brief.fingerprint())
omni_prod/browser_probe.py:140:print("OMNI_BROWSER_PROBE " + json.dumps(out, ensure_ascii=False))
omni_prod/build_contract.py:17:def sha256_fingerprint(data: Mapping[str, Any] | dict[str, Any]) -> str:
omni_prod/build_contract.py:174:        expected_plan = sha256_fingerprint(self.capability_plan.to_dict())
omni_prod/build_contract.py:186:    def verify_fingerprint(self) -> bool:
omni_prod/build_contract.py:187:        return self.contract_fingerprint == sha256_fingerprint(self._fingerprint_payload())
omni_prod/build_contract.py:276:        if not contract.verify_fingerprint():
omni_prod/build_contract_repository.py:27:        if not contract.verify_fingerprint():
omni_prod/build_contract_repository.py:69:        if not contract.verify_fingerprint():
omni_prod/build_outbox_relay.py:46:        print('OMNI_DATABASE_URL and OMNI_REDIS_URL are required', file=sys.stderr)
omni_prod/build_outbox_relay.py:55:                print(f'build_outbox_relay: dispatched {len(sent)} build(s)', flush=True)
omni_prod/build_outbox_relay.py:57:                print(f'build_outbox_relay: pass failed: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
omni_prod/conversation/supervisor.py:397:        if row is None or new_brief.fingerprint() != row.fingerprint:
omni_prod/design_system.py:29:def anti_template_fingerprint(tokens: DesignTokens) -> str:
omni_prod/discovery.py:241:    def fingerprint(self) -> str:
omni_prod/discovery.py:464:    lines = ['', BRIEF_MARKER + ' (binding; fingerprint ' + brief.fingerprint()[:16] + ') ---']
omni_prod/economics_report.py:203:    print('ECONOMICS ' + json.dumps(compute(builds, attempts), default=str))
omni_prod/entitlements.py:95:        print('OMNI_DATABASE_URL is not set', file=sys.stderr)
omni_prod/entitlements.py:109:        print(f'refused: {exc}', file=sys.stderr)
omni_prod/entitlements.py:111:    print(result)
omni_prod/evidence_export.py:254:        print('usage: python -m omni_prod.evidence_export bld_<hex> [--out file.json]', file=sys.stderr)
omni_prod/evidence_export.py:263:        print(text)
omni_prod/failure_replay.py:109:        print('usage: python -m omni_prod.failure_replay export.json [--files-dir DIR]', file=sys.stderr)
omni_prod/failure_replay.py:113:    print(json.dumps(out, ensure_ascii=False, indent=2))
omni_prod/gate_replay.py:208:        print('VERIFY_REPLAY ' + json.dumps(verify_versions(int(sys.argv[2])), ensure_ascii=False, default=str))
omni_prod/gate_replay.py:216:    print('GATE_REPLAY ' + json.dumps(result, ensure_ascii=False, default=str))
omni_prod/idempotency.py:13:def request_fingerprint(payload: dict) -> str:
omni_prod/intake/benchmark.py:52:            print('refused: a model benchmark makes paid calls; set OMNI_INTAKE_BENCH_BUDGET_USD after founder approval')
omni_prod/intake/benchmark.py:58:    print(json.dumps(score(interp, cases), ensure_ascii=False, indent=1))
omni_prod/intake/contract.py:80:    def fingerprint(self) -> str:
omni_prod/intake/contract.py:218:        complexity=complexity, brief_fingerprint=brief.fingerprint(),
omni_prod/intake/reservation_worker.py:158:        print('OMNI_DATABASE_URL (and OMNI_REDIS_URL for relay) required', file=sys.stderr)
omni_prod/intake/reservation_worker.py:175:                print(f'intake {args.cmd}: {out}', flush=True)
omni_prod/intake/reservation_worker.py:177:                print(f'intake {args.cmd} failed: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
omni_prod/intelligence/health.py:230:        print(json.dumps([h.to_dict() for h in book.store.all()], indent=1))
omni_prod/intelligence/health.py:232:        print(json.dumps(book.reset(args.route, by=args.by).to_dict()))
omni_prod/intelligence/matrix.py:259:            print('\n'.join(problems))
omni_prod/intelligence/matrix.py:263:        print(json.dumps(m['summary']))
omni_prod/intelligence/matrix.py:269:            print(p)
omni_prod/intelligence/matrix.py:271:    print(js)
omni_prod/investor_app.py:244:    quote_fingerprint = request_fingerprint({
omni_prod/investor_app.py:255:    build_request_fingerprint = request_fingerprint({
omni_prod/investor_app.py:329:    if not contract.verify_fingerprint():
omni_prod/investor_app.py:647:        'design_fingerprint':anti_template_fingerprint(tokens),'agent_team':plan_team(target='web').to_dict(),
omni_prod/investor_app.py:2102:def _budget_fingerprint(contract, quote, funding: str) -> str:
omni_prod/investor_app.py:2161:            budget_fingerprint=_budget_fingerprint(contract, quote, 'internal_qa' if internal_qa else 'customer_plan'))
omni_prod/investor_app.py:2345:                                    budget_fingerprint=_budget_fingerprint(
omni_prod/isolation_check.py:118:        print(json.dumps({'identities': ids, 'notes': notes}, indent=2))
omni_prod/isolation_check.py:121:        print('usage: python -m omni_prod.isolation_check --env-file a.env --env-file b.env [--label x --label y] | --show --env-file a.env',
omni_prod/isolation_check.py:126:    print(json.dumps(out, indent=2, ensure_ascii=False))
omni_prod/maintenance.py:48:    print(time.strftime('%H:%M:%S ') + msg, flush=True)
omni_prod/migrate.py:47:        print(str(exc), file=sys.stderr)
omni_prod/migrate.py:51:        print('OMNI_DATABASE_URL is not set', file=sys.stderr)
omni_prod/migrate.py:59:        print(f"database: host={ident['db_host']} fingerprint={ident['db_fingerprint']}")
omni_prod/migrate.py:63:            print(f'::warning title=migrate::database is AHEAD of this code at versions {ahead} (accepted explicitly); nothing was changed or hidden')
omni_prod/migrate.py:64:        print('pending migrations:', [m.version for m in pending] or 'none')
omni_prod/migrate.py:68:        print('applied migrations:', list(run.applied_versions))
omni_prod/model_probe.py:58:    print('MODEL-PROBE ' + json.dumps(rows, ensure_ascii=False))
omni_prod/model_probe.py:61:        print(f"::notice title={r['name']}::{body}".replace('\n', ' '))
omni_prod/planning/architect.py:182:            'requirements_fingerprint': contract.fingerprint(), 'product_family': fam, 'complexity': contract.complexity,
omni_prod/planning/architect.py:211:            'graph_fingerprint': graph.fingerprint(),
omni_prod/planning/graph.py:221:    def fingerprint(self) -> str:
omni_prod/postdeploy_checks.py:83:        print(f'::error title=postdeploy {check}::{body}', flush=True)
omni_prod/postdeploy_checks.py:325:        print(f'::warning title=postdeploy::results not stored: {type(exc).__name__}', flush=True)
omni_prod/postdeploy_checks.py:647:    print(f'::notice title=postdeploy {stage} summary::' + lines[:3800].replace('%', '%25').replace('\n', '%0A'), flush=True)
omni_prod/postdeploy_checks.py:648:    print('POSTDEPLOY ' + json.dumps({'stage': stage, 'passed': len(RESULTS) - len(failed), 'failed': failed},
omni_prod/preview_durability.py:124:    print(f"::{level} title=preview-data::{result['status']} {json.dumps(result, ensure_ascii=False)}")
omni_prod/preview_inspector.py:242:    print(f'preview router (inspector {"on" if os.getenv("OMNI_PREVIEW_INSPECTOR") == "1" else "off"}) on '
omni_prod/preview_router.py:118:            print(f'{self.command} {self.headers.get("Host", "-")} {self.path.split("?", 1)[0]} -> {args[1] if len(args) > 1 else ""}',
omni_prod/preview_router.py:217:    print(f'preview router on 127.0.0.1:{port} for *.{suffix} (host {runtime_host})', flush=True)
omni_prod/preview_smoke.py:89:print("PREVIEW-SMOKE " + verdict)
omni_prod/preview_smoke.py:90:print(out.decode("utf-8", "replace")[-1500:])
omni_prod/product_architect.py:210:        capability_fingerprint = sha256_fingerprint(capability_plan.to_dict())
omni_prod/product_architect.py:302:        contract_fingerprint = sha256_fingerprint(provisional)
omni_prod/providers/replicate_image_test.py:21:    def fingerprint(value):
omni_prod/providers/replicate_image_test.py:27:    loaded = {'access_key': fingerprint(creds.access_key),
omni_prod/providers/replicate_image_test.py:28:              'secret_key': fingerprint(creds.secret_key)}
omni_prod/providers/replicate_image_test.py:29:    configured = {'access_key': fingerprint(env.get('OMNI_S3_ACCESS_KEY', '').strip()),
omni_prod/providers/replicate_image_test.py:30:                  'secret_key': fingerprint(env.get('OMNI_S3_SECRET_KEY', '').strip())}
omni_prod/registry_audit.py:370:        print(f'wrote {path}')
omni_prod/registry_audit.py:372:        print(text)
omni_prod/rehearsal.py:129:        print('usage: python -m omni_prod.rehearsal "<prompt>"', file=sys.stderr)
omni_prod/rehearsal.py:132:    print('REHEARSAL ' + json.dumps(report, ensure_ascii=False))
omni_prod/rehearsal.py:134:        print(line)
omni_prod/repair_contracts.py:57:def repository_fingerprint(repository: dict[str, str]) -> str:
omni_prod/requirement_ledger.py:187:        print("requirement-ledger: OK")
omni_prod/schema_manifest.py:14:def db_fingerprint(host, dbname) -> str:
omni_prod/schema_manifest.py:25:    return {'db_host': host, 'db_fingerprint': db_fingerprint(host, dbname)}
omni_prod/truth_lock.py:329:        print(str(exc))
omni_prod/universal_brain.py:23:    def capability_plan_fingerprint(self) -> str:
omni_prod/visual_qa.py:150:    print("OMNI_VISUAL_SHOT " + shot)
omni_prod/visual_qa.py:151:print("OMNI_VISUAL_QA " + json.dumps(out, ensure_ascii=False))
omni_prod/worker.py:42:    print(time.strftime("%H:%M:%S") + " " + message, flush=True)
omni_prod/worker_tasks.py:599:        if not build_contract.verify_fingerprint():
```


## B3 — assert בקוד פרודקשן (נמחק עם -O)

```
omni_prod/provider_pricing.py:102:            assert entry.estimated_unit_cost_usd is not None
omni_prod/provider_pricing.py:103:            assert entry.maximum_unit_cost_usd is not None
omni_prod/recovery_simulation.py:17:    assert breaker.allow(0)
omni_prod/recovery_simulation.py:19:    assert breaker.allow(1)
omni_prod/recovery_simulation.py:21:    assert breaker.state == CircuitState.OPEN
omni_prod/recovery_simulation.py:22:    assert not breaker.allow(5)
omni_prod/recovery_simulation.py:23:    assert breaker.allow(12)
omni_prod/recovery_simulation.py:25:    assert breaker.state == CircuitState.CLOSED
omni_prod/recovery_simulation.py:28:    assert not can_claim(lease, now=5, owner="w2")
omni_prod/recovery_simulation.py:29:    assert can_claim(lease, now=11, owner="w2")
omni_prod/recovery_simulation.py:34:    assert dead.dead_letter
```


## C1 — ברירת מחדל של משתני סביבה

```
-- getenv בלי default --
./omni_prod/brand_native_clients.py:9:        'app/build.gradle.kts':f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{ val ks=System.getenv("ONE48AI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks); storePassword=System.getenv("ONE48AI_ANDROID_STORE_PASSWORD"); keyAlias=System.getenv("ONE48AI_ANDROID_KEY_ALIAS"); keyPassword=System.getenv("ONE48AI_ANDROID_KEY_PASSWORD") }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
./omni_prod/native_source.py:68:        'app/build.gradle.kts': f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{\n   val ks=System.getenv("OMNI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks)\n   storePassword=System.getenv("OMNI_ANDROID_STORE_PASSWORD")\n   keyAlias=System.getenv("OMNI_ANDROID_KEY_ALIAS")\n   keyPassword=System.getenv("OMNI_ANDROID_KEY_PASSWORD")\n }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
./omni_prod/preview_inspector.py:242:    print(f'preview router (inspector {"on" if os.getenv("OMNI_PREVIEW_INSPECTOR") == "1" else "off"}) on '
./tests/integration/test_live_stack.py:4:RUN = os.getenv("OMNI_RUN_LIVE_INTEGRATION") == "1"
./tests/integration/test_m5_live_llm_usage.py:45:        if os.environ.get("M5_LIVE_LLM_EXPECT_COST") == "1":
./tests/integration/test_m5_live_media_provider.py:17:    if os.environ.get("M5_LIVE_IMAGE") != "1":
./tests/integration/test_m5_managed_web_saas_live.py:30:    if os.environ.get("M5_GENAPP_LIVE") != "1":
./tests/integration/test_m5_managed_web_saas_live.py:47:    if not os.environ.get("M5_DATABASE_URL"):
./tests/integration/test_qstash_scheduler_live.py:9:if os.environ.get("M5_QSTASH_LIVE") != "1":
./tests/integration/test_qstash_scheduler_live.py:11:elif not os.environ.get("QSTASH_URL") or not os.environ.get("QSTASH_TOKEN"):
./tests/integration/test_qstash_scheduler_live.py:21:    @unittest.skipUnless(os.environ.get("QSTASH_TEST_DESTINATION"),
./tests/integration/test_r2_generated_storage_live.py:18:    if os.environ.get("M5_R2_LIVE") != "1":
./tests/integration/test_r2_generated_storage_live.py:39:        self.assertNotEqual(cfg.s3_bucket, os.environ.get("OMNI_S3_BUCKET"))
./tests/integration/test_r2_generated_storage_live.py:40:        self.assertTrue(access != os.environ.get("OMNI_S3_ACCESS_KEY"), "generated-app access must differ from control plane")
-- default מספרי חשוד --
./omni_prod/investor_app.py:206:    infra_est = Decimal(os.getenv('OMNI_BUILD_INFRA_ESTIMATED_USD', '0'))
./omni_prod/investor_app.py:208:    retry_reserve = Decimal(os.getenv('OMNI_BUILD_RETRY_RESERVE_USD', '0'))
./omni_prod/model_runtime_config.py:38:        allow = os.getenv('OMNI_ALLOW_EXTERNAL_FALLBACK', '0') == '1'
./omni_prod/model_runtime_config.py:39:        budget = Decimal(os.getenv('OMNI_EXTERNAL_BUDGET_USD', '0'))
./omni_prod/model_runtime_config.py:40:        calls = int(os.getenv('OMNI_EXTERNAL_CALLS_PER_BUILD', '0'))
-- default 'false'/'no' --
-- if על env (מחרוזת ריקה=false אבל '0'=true) --
./omni_prod/brand_native_clients.py:9:        'app/build.gradle.kts':f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{ val ks=System.getenv("ONE48AI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks); storePassword=System.getenv("ONE48AI_ANDROID_STORE_PASSWORD"); keyAlias=System.getenv("ONE48AI_ANDROID_KEY_ALIAS"); keyPassword=System.getenv("ONE48AI_ANDROID_KEY_PASSWORD") }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
./omni_prod/deployments.py:18:    if not _ENV.fullmatch(environment):
./omni_prod/infrastructure_contracts.py:135:        return (environment if isinstance(environment, InfrastructureEnvironment)
./omni_prod/infrastructure_contracts.py:463:        elif binding.environment != env:
./omni_prod/infrastructure_provisioner.py:68:        env = InfrastructureEnvironment(environment) if not isinstance(environment, InfrastructureEnvironment) else environment
./omni_prod/infrastructure_provisioner.py:70:            (b for b in self._by_key.values() if b.project_id == project_id and b.environment == env),
./omni_prod/infrastructure_provisioner.py:163:        env = environment.value if isinstance(environment, InfrastructureEnvironment) else str(environment)
./omni_prod/infrastructure_provisioner.py:266:        env = InfrastructureEnvironment(environment) if not isinstance(environment, InfrastructureEnvironment) else environment
./omni_prod/infrastructure_provisioner.py:308:        env = InfrastructureEnvironment(environment) if not isinstance(environment, InfrastructureEnvironment) else environment
./omni_prod/intake/benchmark.py:51:        if not os.getenv('OMNI_INTAKE_BENCH_BUDGET_USD'):
./omni_prod/intake/interpreter.py:344:    if os.getenv('OMNI_INTAKE_MODEL') == '1' and gateway is not None:
./omni_prod/intake/mode.py:66:    if os.getenv('OMNI_INTAKE_MODEL') != '1':
./omni_prod/intake/mode.py:78:    if os.getenv('OMNI_INTAKE_VIA_WORKER') == '1':
./omni_prod/intake/reservation_worker.py:136:    if os.getenv('OMNI_INTAKE_MODEL') != '1':
./omni_prod/integration_center.py:48:        missing = tuple(name for name in required if not os.getenv(name, '').strip())
./omni_prod/investor_app.py:98:    if os.getenv('OMNI_ENV','development')=='production' and request.url.path.startswith('/api/') and not any(request.url.path==p or (p.endswith('/') and request.url.path.startswith(p)) for p in _PUBLIC_PREFIXES):
./omni_prod/investor_app.py:118:    if os.getenv('OMNI_ENV','development').strip().lower() in ('staging','production'):
./omni_prod/investor_app.py:137:    if os.getenv('OMNI_ENV','development')=='production':
./omni_prod/investor_app.py:144:    if os.getenv('OMNI_ENV','development')=='production':
./omni_prod/investor_app.py:342:    if os.getenv('OMNI_CREATOR_PERSISTENCE','memory').strip().lower()!='postgres' or _v28_pool is None:
./omni_prod/investor_app.py:389:    if os.getenv('OMNI_CREATOR_PERSISTENCE','memory').strip().lower()!='postgres' or _v28_pool is None:
./omni_prod/investor_app.py:729:    if os.getenv('OMNI_ENABLE_LIVE_BUILD')!='1': raise RuntimeError('OMNI_ENABLE_LIVE_BUILD=1 is required')
./omni_prod/investor_app.py:778:    if os.getenv('OMNI_ENABLE_SPECIALIST_REVIEW','1')=='1' and result.status=='ready':
./omni_prod/investor_app.py:1923:    if os.getenv('OMNI_INTAKE_MODEL') == '1' and os.getenv('OMNI_INTAKE_VIA_WORKER') == '1' \
./omni_prod/investor_app.py:2060:    if os.getenv('OMNI_FEASIBILITY_GATE', 'enforce') == 'enforce' and not plan.get('executable'):
./omni_prod/investor_app.py:3064:    if os.getenv('VERCEL_ENV') != 'preview':
./omni_prod/memory_adapters.py:30:            if p.project_id==project_id and p.environment==environment:
./omni_prod/native_source.py:68:        'app/build.gradle.kts': f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{\n   val ks=System.getenv("OMNI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks)\n   storePassword=System.getenv("OMNI_ANDROID_STORE_PASSWORD")\n   keyAlias=System.getenv("OMNI_ANDROID_KEY_ALIAS")\n   keyPassword=System.getenv("OMNI_ANDROID_KEY_PASSWORD")\n }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
./omni_prod/preview_inspector.py:239:    access = PreviewAccess(repo.pool) if os.getenv('OMNI_PREVIEW_ACCESS_CONTROL', '1') != '0' else None
./omni_prod/preview_inspector.py:242:    print(f'preview router (inspector {"on" if os.getenv("OMNI_PREVIEW_INSPECTOR") == "1" else "off"}) on '
./omni_prod/preview_router.py:214:    access = PreviewAccess(repo.pool) if os.getenv('OMNI_PREVIEW_ACCESS_CONTROL', '1') != '0' else None
./omni_prod/preview_runtime.py:421:        self.data_root = (data_root if data_root is not None else os.getenv('OMNI_PREVIEW_DATA_ROOT', '')).strip() or None
./omni_prod/production_adapters.py:25:    if settings.environment != "production":
./omni_prod/providers/managed_web_saas.py:478:        env = environment if isinstance(environment, InfrastructureEnvironment) else InfrastructureEnvironment(environment)
./omni_prod/providers/managed_web_saas.py:564:        sibling_env = (InfrastructureEnvironment.PRODUCTION if environment == InfrastructureEnvironment.PREVIEW
./omni_prod/qa_budget.py:76:        if environment == 'production' or env.get('VERCEL_ENV', '').strip().lower() == 'production':
./omni_prod/qa_budget.py:78:        if environment != QA_ENVIRONMENT:
./omni_prod/readiness.py:13:def _any_env(*names): return next((os.getenv(n) for n in names if os.getenv(n)), None)
./omni_prod/release_policy.py:233:    if os.getenv('OMNI_ENV', '').strip().lower() in ('staging', 'production'):
./omni_prod/worker_tasks.py:940:    if os.getenv('OMNI_AGENT_RECORDER', '1') != '0':
./scripts/run_live_benchmark.py:15:if os.getenv('OMNI_ENABLE_LIVE_BUILD') != '1':
./scripts/run_live_sandbox_hostile.py:7:if os.getenv('OMNI_RUN_LIVE_SANDBOX')!='1': raise SystemExit('Set OMNI_RUN_LIVE_SANDBOX=1 only on an isolated Docker-capable test host.')
./tests/integration/test_m5_live_llm_usage.py:16:_MISSING = [name for name in _REQUIRED if not os.environ.get(name)]
./tests/integration/test_m5_live_llm_usage.py:45:        if os.environ.get("M5_LIVE_LLM_EXPECT_COST") == "1":
./tests/integration/test_m5_live_media_provider.py:17:    if os.environ.get("M5_LIVE_IMAGE") != "1":
./tests/integration/test_m5_managed_web_saas_live.py:30:    if os.environ.get("M5_GENAPP_LIVE") != "1":
./tests/integration/test_m5_managed_web_saas_live.py:32:    missing = [name for name in REQUIRED if not os.environ.get(name)]
./tests/integration/test_m5_managed_web_saas_live.py:34:    if not os.environ.get(token_env):
./tests/integration/test_m5_managed_web_saas_live.py:47:    if not os.environ.get("M5_DATABASE_URL"):
./tests/integration/test_qstash_scheduler_live.py:9:if os.environ.get("M5_QSTASH_LIVE") != "1":
./tests/integration/test_qstash_scheduler_live.py:11:elif not os.environ.get("QSTASH_URL") or not os.environ.get("QSTASH_TOKEN"):
./tests/integration/test_r2_generated_storage_live.py:18:    if os.environ.get("M5_R2_LIVE") != "1":
./tests/integration/test_r2_generated_storage_live.py:21:        if not os.environ.get(name):
./tests/integration/test_r2_generated_storage_live.py:25:        if not ref.startswith("env:") or not os.environ.get(ref[4:]):
./tests/test_m4_acceptance.py:663:        if os.environ.get('OMNI_M4_ACCEPTANCE_W_NESTED') == '1':
./tools/deployment_verify.py:373:    if meta['environment'] == 'production' and not allow_production_writes:
```


## D1 — אבטחה: השוואת סודות

```
-- == על טוקן/סוד --
./omni_prod/agents_registry.py:277:            ("dependency_agents", bool(agent.dependency_agents) or agent.key == "agent.chief_orchestrator"),
./omni_prod/capability_worker.py:117:                target_keys=tuple(k for k in plan.target_keys if any(r.key == k for r in assigned_requirements)),
./omni_prod/preview_inspector.py:96:  function onKey(ev) { if (enabled && ev.key === 'Escape') { post({ type: '148ai:cancel' }); } }
./omni_prod/providers/image_provider.py:574:                capability = next(c for c in candidate_provider.capabilities() if c.capability_key == requirement.key)
./omni_prod/providers/managed_web_saas.py:151:        if self.secret_store_provider == "infisical":
./omni_prod/providers/managed_web_saas.py:158:        return bool(self.secret_store_provider == "vault" and self.secret_store_url
./omni_prod/providers/managed_web_saas.py:163:        if self.secret_store_provider == "infisical":
./omni_prod/providers/managed_web_saas.py:234:                if key and key == _clean(control_env, "RESEND_API_KEY"):
./omni_prod/providers/managed_web_saas.py:640:            if key and key == _clean(self.control_plane_env, "RESEND_API_KEY"):
./omni_prod/providers/managed_web_saas.py:733:    if config.secret_store_provider == "infisical":
./omni_prod/sandbox_executor.py:34:    if not argv or argv[0] in ('true', ':') or any(token == 'echo' for token in argv):
./omni_prod/skills_registry.py:121:            if key == "software.deploy.web"
./omni_prod/skills_registry.py:179:    if capability_key.startswith("publish.") or capability_key == "software.deploy.web":
./omni_prod/web_saas_acceptance.py:362:    if key == 'today':
./tests/test_agent_os.py:64:        base = next(s for s in SKILLS if s.skill_key == 'preview_access_protect')
./tests/test_intelligence_plane.py:172:        luna = next(e for e in INVENTORY if e.model_key == 'openai-gpt-6-luna')
./tests/test_intelligence_plane.py:174:        haiku = next(e for e in INVENTORY if e.model_key == 'anthropic-claude-haiku-5-5')
./tests/test_intelligence_plane.py:179:            inv = tuple(bad if e.model_key == bad.model_key else e for e in INVENTORY)
./tests/test_m5_economics_reconciliation.py:65:        self.image_req = next(r for r in self.contract.capability_plan.requirements if r.key == "media.image.generate")
./tests/test_m5_generated_app_storage_isolation.py:38:        assert operator_access_key == "genapp-access" and role_arn.startswith("arn:")
./tests/test_m5_managed_web_saas_profile.py:110:        assert operator_access_key == "genapp-access" and operator_secret_key == "genapp-secret"
./tests/test_model_gateway_idempotency.py:36:    assert gw.last_idempotency_key == key
./tests/test_replicate_connection.py:16:    assert config.api_key_ref == 'env:REPLICATE_API_TOKEN'
./tests/test_replicate_connection.py:27:    assert config.api_key_ref == ''
./tests/test_replicate_image_test.py:107:            assert key == self.key
./tests/test_visual_edit.py:285:                return token == 'owner'
-- compare_digest --
./omni_prod/account_tenant.py:63:            if not hmac.compare_digest(acct.password_hash,_hash_password(password,salt)): raise PermissionError('invalid credentials')
./omni_prod/auth.py:41:        if not hmac.compare_digest(sig,expected): raise AuthError('invalid signature')
./omni_prod/identity_lifecycle.py:452:        if not hmac.compare_digest(account.password_hash, _hash_password(password, salt)):
./omni_prod/identity_lifecycle.py:471:        if not hmac.compare_digest(session.token_hash, _token_hash(token)):
./omni_prod/investor_app.py:1159:    if not expected or not provided or not hmac.compare_digest(expected,provided):
./omni_prod/investor_app.py:1484:    if not expected or not provided or not hmac.compare_digest(expected, provided):
./omni_prod/providers/qstash_scheduler.py:172:            if not any(hmac.compare_digest(hmac.new(key, data, hashlib.sha256).digest(), expected)
./omni_prod/providers/qstash_scheduler.py:185:            if not isinstance(claims.get("body"), str) or not hmac.compare_digest(claims["body"].rstrip("="), digest):
./omni_prod/sandbox_service.py:62:    if not hmac.compare_digest(supplied,sign_body(secret,body)): raise HTTPException(401,'invalid signature')
./omni_prod/stripe_billing.py:106:    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
./omni_prod/unified_engine.py:229:        if user is None or not hmac.compare_digest(user.password_hash, _pbkdf2(credential, user.salt)):
```


## D2 — אבטחה: TLS וקריאות רשת

```
-- verify=False --
./omni_prod/evidence_export.py:241:                out['generated_files'] = files_section(store.get_bytes(key, verify=False), files_dir)
./omni_prod/workspace.py:190:            self.storage.get_bytes(artifact_key, verify=False)
./omni_prod/workspace.py:227:            zip_bytes = self.storage.get_bytes(artifact_key, verify=False)
./tests/test_m4d1_atomic_accept.py:587:                self.storage.get_bytes(artifact_key, verify=False)
./tests/test_m4d1_atomic_accept.py:623:            def get_bytes(self, key, verify=False):
./tests/test_workspace_version_conflict.py:106:    def get_bytes(self, key, verify=False):
-- urlopen/requests --
./omni_prod/behavior_acceptance.py:59:        urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=2); ok = True; break
./omni_prod/browser_probe.py:49:        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
./omni_prod/media_gateway.py:40:            with urllib.request.urlopen(req,timeout=self.endpoint.timeout_seconds) as r: body=json.loads(r.read().decode())
./omni_prod/model_gateway.py:137:    def __init__(self, endpoint: ModelEndpoint, *, urlopen: Callable[..., Any] | None = None):
./omni_prod/model_gateway.py:139:        self._urlopen = urlopen or request.urlopen
./omni_prod/model_gateway.py:194:            with self._urlopen(req, timeout=self.endpoint.timeout_seconds) as resp:
./omni_prod/postdeploy_checks.py:111:        with urlrequest.urlopen(req, timeout=timeout) as resp:
./omni_prod/postdeploy_checks.py:451:        with urlrequest.urlopen(req, timeout=60) as resp:
./omni_prod/preview_durability.py:54:    with urlrequest.urlopen(req, timeout=timeout) as resp:
./omni_prod/preview_runtime.py:352:        with urlrequest.urlopen(req, timeout=timeout) as resp:
./omni_prod/preview_smoke.py:45:        with urllib.request.urlopen("http://127.0.0.1:%%d%%s" %% (port, path), timeout=2) as r:
./omni_prod/preview_smoke.py:57:        with urllib.request.urlopen("http://127.0.0.1:%%d/" %% port, timeout=3) as r:
./omni_prod/preview_smoke.py:68:                with urllib.request.urlopen("http://127.0.0.1:%%d/%%s" %% (port, ref.lstrip("./")), timeout=3) as a:
./omni_prod/providers/image_provider.py:298:                 urlopen=None, sleep: Callable[[float], None] | None = None, poll_interval_seconds: float = 2.0,
./omni_prod/providers/image_provider.py:307:        self.urlopen = urlopen or request.urlopen
./omni_prod/providers/image_provider.py:364:        with self.urlopen(req, timeout=self.config.timeout_seconds) as resp:
./omni_prod/providers/image_provider.py:510:def build_image_provider(env: Mapping[str, str] | None = None, *, journal, urlopen=None, fetcher=None):
./omni_prod/providers/image_provider.py:528:    return PredictionImageProvider(config=config, resolve_reference=resolve, journal=journal, urlopen=urlopen,
./omni_prod/providers/image_provider.py:533:                                 worker_id: str, urlopen=None, fetcher=None):
./omni_prod/providers/image_provider.py:539:    provider = build_image_provider(env, journal=journal, urlopen=urlopen, fetcher=fetcher)
./omni_prod/providers/managed_web_saas.py:264:def _probe_url(url: str, *, token: str, timeout: float = 5.0, urlopen=None) -> int:
./omni_prod/providers/managed_web_saas.py:265:    opener = urlopen or request.urlopen
./omni_prod/providers/replicate_connection.py:47:def check_replicate_connection(env, *, urlopen=None):
./omni_prod/providers/replicate_connection.py:63:        with (urlopen or request.urlopen)(req, timeout=10) as response:
./omni_prod/providers/replicate_image_test.py:51:    def __init__(self, *, env, journal, store, urlopen=None, fetcher=None):
./omni_prod/providers/replicate_image_test.py:55:            journal=journal, urlopen=urlopen, fetcher=fetcher)
./omni_prod/remote_sandbox.py:37:    def __init__(self, config: RemoteSandboxConfig, *, urlopen=None):
./omni_prod/remote_sandbox.py:38:        self.config=config; self._urlopen=urlopen or request.urlopen
./omni_prod/remote_sandbox.py:49:            with self._urlopen(req,timeout=self.config.timeout_seconds) as resp:
./omni_prod/safe_fetch.py:123:    urlopen: Callable | None = None  # injected transport for tests; validation still applies
./omni_prod/safe_fetch.py:159:        opener = self.urlopen or self._opener().open
./omni_prod/secrets_manager.py:29:    def __init__(self,config:VaultHttpConfig,*,urlopen=None): self.config=config; self.urlopen=urlopen or request.urlopen
./omni_prod/secrets_manager.py:38:            with self.urlopen(req,timeout=self.config.timeout_seconds) as r: payload=json.loads(r.read().decode())
./omni_prod/secrets_manager.py:71:                 timeout_seconds: float = 5, urlopen=None):
./omni_prod/secrets_manager.py:77:        self.urlopen = urlopen or request.urlopen
./omni_prod/secrets_manager.py:99:            with self.urlopen(req, timeout=self.timeout_seconds) as resp:
./omni_prod/secrets_manager.py:161:                 urlopen=None, clock=None):
./omni_prod/secrets_manager.py:175:        self.urlopen = urlopen or request.build_opener(_NoInfisicalRedirect()).open
./omni_prod/secrets_manager.py:198:            with self.urlopen(req, timeout=self.timeout_seconds) as response:
./omni_prod/stripe_billing.py:45:        self.opener = opener or urllib.request.urlopen
./omni_prod/visual_qa.py:56:        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
./scripts/run_http_load.py:9:        with urllib.request.urlopen(URL,timeout=10) as r: r.read(); status=r.status
./scripts/run_v28_http_acceptance.py:20:        with urllib.request.urlopen(r,timeout=15) as resp:
./tests/integration/test_live_preview_runtime.py:105:            body = urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=5).read().decode()
./tests/test_failure_injection.py:92:        ex._urlopen = MagicMock(side_effect=error.URLError('connection reset'))
./tests/test_infisical_secret_store.py:86:            urlopen=api, **kwargs)
./tests/test_m5_llm_usage_evidence.py:59:    return OpenAICompatibleGateway(endpoint, urlopen=lambda req, timeout: _Resp(payload, headers))
./tests/test_m5_llm_usage_evidence.py:171:            return OpenAICompatibleGateway(endpoint, urlopen=_fail)
./tests/test_m5_llm_usage_evidence.py:172:        return OpenAICompatibleGateway(endpoint, urlopen=lambda req, timeout: seq.pop(0))
./tests/test_m5_llm_usage_evidence.py:253:            return OpenAICompatibleGateway(endpoint, urlopen=boom)
./tests/test_m5_managed_web_saas_profile.py:359:        def urlopen(req, timeout):
./tests/test_m5_managed_web_saas_profile.py:370:                                           urlopen=urlopen)
./tests/test_m5_managed_web_saas_profile.py:379:        writer = VaultHttpSecretWriter(base_url="https://vault.example", token_env="X", urlopen=lambda *a, **k: None)
./tests/test_m5_media_provider_adapters.py:136:    return SafeFetcher(resolver=public_resolver, urlopen=api)
./tests/test_m5_media_provider_adapters.py:146:        journal=journal or MemorySubmissionJournal(), urlopen=api,
./tests/test_m5_media_provider_adapters.py:405:                                             journal=MemorySubmissionJournal(), worker_id="w1", urlopen=api,
./tests/test_m5_media_provider_adapters.py:430:                                             journal=MemorySubmissionJournal(), worker_id="w1", urlopen=api)
./tests/test_m5_ssrf_guard.py:88:        fetcher = SafeFetcher(resolver=PUBLIC, urlopen=lambda req, timeout: _Resp(url="https://10.0.0.5/x.png"))
./tests/test_m5_ssrf_guard.py:95:        fetcher = SafeFetcher(resolver=PUBLIC, urlopen=lambda req, timeout: _Resp(headers={"Content-Type": "text/html"}))
./tests/test_m5_ssrf_guard.py:100:        big_header = SafeFetcher(resolver=PUBLIC, max_bytes=10, urlopen=lambda req, timeout: _Resp(
./tests/test_m5_ssrf_guard.py:104:        big_body = SafeFetcher(resolver=PUBLIC, max_bytes=4, urlopen=lambda req, timeout: _Resp())
./tests/test_m5_ssrf_guard.py:109:        fetcher = SafeFetcher(resolver=PUBLIC, urlopen=lambda req, timeout: _Resp())
./tests/test_manifest_shape.py:27:    def urlopen(req, timeout):
./tests/test_manifest_shape.py:30:    return RemoteSandboxRepositoryExecutor(RemoteSandboxConfig("http://sandbox:8010", "s" * 64), urlopen=urlopen)
./tests/test_model_catalog_routing.py:187:        OpenAICompatibleGateway(ep, urlopen=opener).complete(system="s", user="u")
./tests/test_model_gateway_idempotency.py:25:    def urlopen(req, timeout=None):
./tests/test_model_gateway_idempotency.py:28:    return OpenAICompatibleGateway(_endpoint(), urlopen=urlopen)
./tests/test_model_json_parsing.py:26:    gw._urlopen = lambda req, timeout=None: _Resp({'choices': [{'message': {'content': content}, 'finish_reason': finish}]})
./tests/test_model_transient_retry.py:111:        def urlopen(req, timeout):
./tests/test_model_transient_retry.py:115:        return OpenAICompatibleGateway(endpoint, urlopen=urlopen)
./tests/test_provider_quota_and_dialects.py:180:        def urlopen(req, timeout):
./tests/test_provider_quota_and_dialects.py:186:        gw = OpenAICompatibleGateway(ep, urlopen=urlopen)
./tests/test_provider_quota_and_dialects.py:228:        def urlopen(req, timeout):
./tests/test_provider_quota_and_dialects.py:232:            OpenAICompatibleGateway(ep, urlopen=urlopen).complete(system='s', user='u')
./tests/test_replicate_connection.py:41:        journal=MemorySubmissionJournal(), urlopen=transport)
./tests/test_replicate_connection.py:62:    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'test-only-token'}, urlopen=transport)
./tests/test_replicate_connection.py:73:    assert check_replicate_connection({}, urlopen=transport)['status'] == 'NOT_CONFIGURED'
./tests/test_replicate_connection.py:80:    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'test-only-token'}, urlopen=transport)
./tests/test_replicate_connection.py:123:    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'secret-test-token'}, urlopen=transport)
./tests/test_replicate_connection.py:134:    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'test-only-token'}, urlopen=transport)
./tests/test_replicate_image_test.py:13:        journal=journal or MemorySubmissionJournal(), store=store, urlopen=transport)
./tests/test_replicate_image_test.py:40:            urlopen=forbidden).start('account-one', confirmed=True)
./tests/test_replicate_image_test.py:91:        store=store, urlopen=transport, fetcher=Fetcher())
./tests/test_v24_native_remote.py:41:        cfg=RemoteSandboxConfig('https://runner','x'*32); ex=RemoteSandboxRepositoryExecutor(cfg,urlopen=fake)
./tests/test_v24_native_remote.py:49:        cfg=RemoteSandboxConfig('https://runner','x'*32); ex=RemoteSandboxRepositoryExecutor(cfg,urlopen=fake)
./tools/ui_visual_edit/preview_host.py:51:                    urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=1); break
-- בלי timeout --
```


## D3 — אבטחה: CORS / עוגיות / CSRF

```
./omni_prod/agent_os/skills.py:173:    'csrf_check': (('omni_prod.browser_session:extract_session_token',), (U('tests/test_v24_auth.py'),), 'platform API only'),
./omni_prod/browser_session.py:1:"""Browser session transport: HttpOnly cookie for the web workspace, Bearer for API clients.
./omni_prod/browser_session.py:6:* login/register set ``148ai_session`` as HttpOnly, SameSite=Strict, path=/,
./omni_prod/browser_session.py:15:  SameSite=Strict this blocks cross-site request forgery.
./omni_prod/browser_session.py:78:    return {"key": COOKIE_NAME, "httponly": True, "secure": _secure(production, env), "samesite": "strict", "path": "/"}
./omni_prod/browser_session.py:84:        return {"status": "BLOCKED", "transport": "HTTPONLY_COOKIE",
./omni_prod/browser_session.py:85:                "reason": "session cookie is not Secure (OMNI_SESSION_COOKIE_SECURE=0); acceptable only for local http development"}
./omni_prod/browser_session.py:86:    return {"status": "PARTIAL", "transport": "HTTPONLY_COOKIE",
./omni_prod/browser_session.py:87:            "reason": ("HttpOnly + Secure + SameSite=Strict cookie with same-origin check on writes; "
./omni_prod/cors_policy.py:7:    if '*' in origins: raise ValueError('wildcard CORS origin is forbidden')
./omni_prod/cors_policy.py:8:    if len(origins)!=len(set(origins)): raise ValueError('duplicate CORS origin')
./omni_prod/cors_policy.py:16:            raise ValueError('localhost CORS origin forbidden in production')
./omni_prod/investor_app.py:798:    # Bearer header (API clients) or the HttpOnly browser session cookie, with a
./omni_prod/investor_app.py:799:    # same-origin requirement for cookie-authenticated writes (CSRF guard).
./omni_prod/investor_app.py:811:    response.delete_cookie(settings['key'], path=settings['path'], secure=settings['secure'],
./omni_prod/investor_app.py:812:                           httponly=True, samesite=settings['samesite'])
./omni_prod/investor_app.py:2621:    preview (the router exchanges it for an HttpOnly cookie)."""
./omni_prod/modification_diff.py:26:    'admin', '.env', 'cors', 'session', 'credential', 'webhook',
./omni_prod/preview_access.py:13:The router accepts a token as `?__148ai_access=` (sets an HttpOnly cookie and
./omni_prod/preview_router.py:161:                    # Exchange the link token for an HttpOnly cookie and drop it from the address bar.
./omni_prod/preview_router.py:165:                                                   'HttpOnly; Secure; SameSite=None; Partitioned')
./omni_prod/web_security.py:2:from fastapi.middleware.cors import CORSMiddleware
./omni_prod/web_security.py:4:from .cors_policy import parse_and_validate_origins
./omni_prod/web_security.py:9:    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,
./omni_prod/__init__.py:1:__all__ = ['config', 'db', 'queueing', 'storage', 'sandbox', 'health', 'models', 'build_state', 'job_repository', 'deployments', 'usage', 'provenance', 'api_routes', 'idempotency', 'limits', 'model_router', 'rollback', 'worker_health', 'artifact_keys', 'build_budget', 'canary', 'error_taxonomy', 'orchestrator', 'repair_loop', 'retry', 'memory_adapters', 'secret_redaction', 'acceptance_pipeline', 'migrations', 'audit', 'secret_scan', 'canary_controller', 'release_manifest', 'release_gate', 'staging_simulation', 'preflight', 'migration_runner', 'artifact_integrity', 'dependency_inventory', 'sbom', 'cors_policy', 'web_security', 'attestation', 'circuit_breaker', 'outbox', 'worker_lease', 'dead_letter', 'recovery_simulation', 'request_id', 'metrics', 'slo', 'backup_manifest', 'structured_event', 'observability', 'recovery_drill', 'production_adapters', 'redis_circuit_breaker', 'model_gateway', 'model_policy', 'product_spec', 'repository_patch', 'change_policy', 'autonomous_agents', 'autonomous_core', 'modifier_engine', 'model_runtime_config', 'project_manifest', 'sandbox_executor']
./tests/test_m5_browser_session.py:1:"""M5 remediation: browser sessions use an HttpOnly cookie; Bearer stays for API clients."""
./tests/test_m5_browser_session.py:52:    def test_production_cookie_is_httponly_secure_strict(self):
./tests/test_m5_browser_session.py:54:        self.assertEqual((s["httponly"], s["secure"], s["samesite"], s["path"]), (True, True, "strict", "/"))
./tests/test_preview_access.py:96:        self.assertIn('HttpOnly', headers['Set-Cookie'])
./tests/test_v18_supplychain_security.py:3:from omni_prod.cors_policy import parse_and_validate_origins
./tests/test_v18_supplychain_security.py:18:class CORSPolicyTests(unittest.TestCase):
```


## D4 — אבטחה: הרצה והזרקה

```
-- shell=True --
-- subprocess --
./infra/staging/verify_neon_bootstrap.py:22:    result = subprocess.run(
./infra/staging/verify_neon_bootstrap.py:40:retry = subprocess.run(
./omni_prod/behavior_acceptance.py:55:p = subprocess.Popen(c["start"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
./omni_prod/browser_probe.py:42:srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
./omni_prod/media_branding.py:81:            run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
./omni_prod/media_branding.py:90:                run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
./omni_prod/preview_runtime.py:414:                 runner: Callable[..., subprocess.CompletedProcess] | None = None,
./omni_prod/preview_runtime.py:439:        runner = self._runner or subprocess.run
./omni_prod/preview_runtime.py:442:    def _run(self, argv: list[str], timeout: int) -> subprocess.CompletedProcess:
./omni_prod/preview_runtime.py:443:        runner = self._runner or subprocess.run
./omni_prod/preview_smoke.py:38:p = subprocess.Popen(c["start"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
./omni_prod/registry_audit.py:125:        r = subprocess.run(['git', 'show', f'{commit}:{rel}'], cwd=ROOT, capture_output=True)
./omni_prod/sandbox.py:123:def sweep_stale_containers(max_age_seconds: int, *, runner=subprocess.run, now: datetime | None = None,
./omni_prod/sandbox.py:165:        proc = subprocess.run(
./omni_prod/sandbox.py:173:    except subprocess.TimeoutExpired as exc:
./omni_prod/sandbox.py:177:        subprocess.run(["docker", "rm", "-f", name], text=True, capture_output=True, timeout=30, check=False, env=_docker_env())
./omni_prod/visual_qa.py:52:srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
./scripts/run_international_gate.py:17:    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
./scripts/run_quality_gate.py:17:    p = subprocess.run(argv, cwd=root, text=True, capture_output=True)
./scripts/run_v25_release_gate.py:12:    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
./scripts/run_v26_release_gate.py:11:    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
./scripts/run_v27_release_gate.py:11:    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
./scripts/run_v28_http_acceptance.py:37:p=subprocess.Popen([sys.executable,'-m','uvicorn','omni_prod.investor_app:app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
./scripts/run_v28_http_acceptance.py:91:    except subprocess.TimeoutExpired:p.kill()
./scripts/run_v28_release_gate.py:16:    p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
./tests/financial_fault_harness.py:194:                child = subprocess.Popen([sys.executable, '-m', 'tests.financial_fault_harness', '--worker',
./tests/integration/test_live_preview_runtime.py:73:    return subprocess.run(['docker', 'inspect', cid], capture_output=True).returncode == 0
./tests/integration/test_live_preview_runtime.py:108:            info = json.loads(subprocess.run(['docker', 'inspect', cid], capture_output=True, text=True, check=True).stdout)[0]
./tests/integration/test_live_preview_runtime.py:124:                return subprocess.run(['docker', 'exec', cid, 'python', '-c', code], capture_output=True, text=True)
./tests/test_behavior_acceptance_in_build.py:83:            p = subprocess.run(list(argv), cwd=root, capture_output=True, text=True, timeout=90)
./tests/test_browser_probe.py:95:            r = subprocess.run([sys.executable, '-c', PROBE], cwd=d, capture_output=True, text=True, timeout=120,
./tests/test_evidence_export.py:219:        r = subprocess.run([sys.executable, '-', 'not-a-build-id'], input=src.read_text(), capture_output=True, text=True, timeout=30)
./tests/test_m3_preview_logic.py:12:What is faked, and why: `subprocess.run` (no Docker registry in this sandbox),
./tests/test_m3_preview_logic.py:227:    """Stands in for subprocess.run: records argv, returns queued results."""
./tests/test_m3_preview_logic.py:236:        return subprocess.CompletedProcess(argv, rc, out, err)
./tests/test_m49_clean_room.py:82:    out = subprocess.run(['docker', 'inspect', '--format={{.Id}}', 'omni-sandbox:latest'],
./tests/test_m49_clean_room.py:126:def _run_separate_worker_process(timeout: float = 90.0) -> subprocess.CompletedProcess:
./tests/test_m49_clean_room.py:133:    proc = subprocess.run(
./tests/test_m49_sandbox_security.py:220:    out = subprocess.run(['docker', 'inspect', '--format={{.Id}}', 'omni-sandbox:latest'],
./tests/test_m4d2b_parity_and_worker.py:115:def _run_separate_worker_process(timeout: float = 60.0) -> subprocess.CompletedProcess:
./tests/test_m4d2b_parity_and_worker.py:122:    proc = subprocess.run(
./tests/test_m4_acceptance.py:667:        proc = subprocess.run(
./tests/test_migration_rollback_tolerance.py:114:        r = subprocess.run([sys.executable, '-m', 'omni_prod.migrate', '--check'], env=env, cwd=ROOT, capture_output=True, text=True)
./tests/test_migration_rollback_tolerance.py:118:        r = subprocess.run([sys.executable, '-m', 'omni_prod.migrate'], env=env, cwd=ROOT, capture_output=True, text=True)
./tests/test_migration_rollback_tolerance.py:123:            r = subprocess.run([sys.executable, '-m', 'omni_prod.migrate', *extra], env=env, cwd=ROOT, capture_output=True, text=True)
./tests/test_migration_rollback_tolerance.py:125:        r = subprocess.run([sys.executable, '-m', 'omni_prod.migrate', '--accept-newer', 'all'], env=env, cwd=ROOT, capture_output=True, text=True)
./tests/test_preview_data_durability.py:50:                return subprocess.CompletedProcess(argv, 0, 'cid123\n', '')
./tests/test_preview_data_durability.py:52:                return subprocess.CompletedProcess(argv, 0, '127.0.0.1:49999\n', '')
./tests/test_preview_data_durability.py:53:            return subprocess.CompletedProcess(argv, 0, '', '')
./tests/test_preview_smoke.py:56:            p = subprocess.run(list(argv), cwd=d, capture_output=True, text=True, timeout=60)
./tests/test_preview_smoke.py:125:        r = subprocess.run([sys.executable, '-c', _SMOKE], cwd=d, capture_output=True, text=True, timeout=60)
./tests/test_real_docker_drain_recovery.py:65:        return subprocess.run(['docker', 'info'], capture_output=True, timeout=20).returncode == 0
./tests/test_real_docker_drain_recovery.py:71:    return subprocess.run(list(cmd), env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout)
./tests/test_sandbox_cleanup.py:58:                raise subprocess.TimeoutExpired(argv, kw.get('timeout'), output=b'partial', stderr=b'')
./tests/test_visual_qa.py:96:            proc = subprocess.run([sys.executable, '-c', SCRIPT, viewport], cwd=d, capture_output=True, text=True,
./tests/test_worker_deploy_recovery.py:71:    return (subprocess.run(['bash', str(HOST / script)], env=env, capture_output=True, text=True, timeout=60),
./tests/test_worker_deploy_recovery.py:110:        rr = subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True, timeout=60)
./tests/test_worker_deploy_recovery.py:126:        self.assertEqual(subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True).returncode, 0)
./tests/test_worker_deploy_recovery.py:130:        rr = subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True)
./tests/test_worker_deploy_recovery.py:139:    return subprocess.run(['bash', str(HOST / 'recover.sh')], env=env, capture_output=True, text=True, timeout=60)
./tests/test_worker_deploy_recovery.py:431:        r = subprocess.run(py, env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
./tests/test_worker_deploy_recovery.py:435:        r = subprocess.run(py, env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
./tests/test_worker_deploy_recovery.py:437:        r = subprocess.run(py + ['--wait-minutes', 'abc'], env=env, capture_output=True, text=True, cwd=ROOT, timeout=60)
./tools/ui_visual_edit/preview_host.py:44:            proc = subprocess.Popen([sys.executable, 'app.py'], cwd=d, env={**os.environ, 'PORT': str(port)},
./tools/ui_visual_edit/preview_host.py:45:                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
-- eval/exec --
./omni_prod/behavior_acceptance.py:49:exec(compile(cfg["runner"], "web_saas_acceptance.py", "exec"), mod.__dict__)
-- pickle --
-- SQL עם f-string --
./omni_prod/attachments.py:229:            r = conn.execute(f'SELECT {_COLS} FROM conversation_attachments WHERE id = %s AND project_id = %s '
./omni_prod/attachments.py:243:            rows = conn.execute(f'SELECT {_COLS} FROM conversation_attachments WHERE project_id = %s AND account_id = %s '
./omni_prod/backup.py:67:        out[table] = conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
./omni_prod/conversation/store.py:118:                    r = conn.execute(f'SELECT {self._MSG} FROM intake_messages WHERE project_id = %s AND request_key = %s AND role = %s',
./omni_prod/conversation/store.py:124:            rows = conn.execute(f'SELECT {self._MSG} FROM intake_messages WHERE project_id = %s ORDER BY id DESC LIMIT %s',
./omni_prod/conversation/store.py:132:            r = conn.execute(f"SELECT {self._MSG} FROM intake_messages WHERE project_id = %s AND request_key = %s AND role = 'assistant'",
./omni_prod/infrastructure_provisioner.py:115:                cur.execute(f"SELECT {self._COLUMNS} FROM generated_app_bindings WHERE idempotency_key=%s",
./omni_prod/infrastructure_provisioner.py:123:                cur.execute(f"SELECT {self._COLUMNS} FROM generated_app_bindings WHERE binding_id=%s", (binding_id,))
./omni_prod/intake/budget.py:263:            cur.execute(f'SELECT {_COLS} FROM intake_reservations WHERE id = %s'
./omni_prod/intake/budget.py:285:                cur.execute(f'SELECT {_COLS} FROM intake_reservations WHERE idempotency_key = %s', (idempotency_key,))
./omni_prod/intake/budget.py:470:                cur.execute(f"UPDATE intake_reservations SET state = 'SETTLED', cost_state = %s, actual_usd = %s, "
./omni_prod/intelligence/health.py:112:            row = conn.execute(f'SELECT {", ".join(self.COLS)} FROM provider_health WHERE route = %s', (route,)).fetchone()
./omni_prod/intelligence/health.py:129:            rows = conn.execute(f'SELECT {", ".join(self.COLS)} FROM provider_health ORDER BY route').fetchall()
./omni_prod/maintenance.py:158:                    current = conn.execute(f'SELECT cancel_requested_at IS NOT NULL, recovery_attempts FROM {table} '
./tests/test_conversation_os.py:522:        admin.execute(f'CREATE DATABASE {name}')
./tests/test_conversation_os.py:534:            admin.execute(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')
./tests/test_intake_budget_pg.py:54:        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
./tests/test_intake_budget_pg.py:64:        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
./tests/test_intake_budget_pg.py:599:        admin.execute(f'CREATE DATABASE {name}')
./tests/test_intake_budget_pg.py:623:            admin.execute(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')
./tests/test_migration_rollback_tolerance.py:63:        self.admin.execute(f'CREATE DATABASE {self.name}')
./tests/test_migration_rollback_tolerance.py:73:        self.admin.execute(f'DROP DATABASE IF EXISTS {self.name} WITH (FORCE)')
./tests/test_real_docker_drain_recovery.py:162:        self.admin.execute(f'CREATE DATABASE {self.db}')
./tests/test_real_docker_drain_recovery.py:178:        self.admin.execute(f'DROP DATABASE IF EXISTS {self.db} WITH (FORCE)')
-- SQL עם % או .format --
```


## D5 — אבטחה: סודות בלוגים

```
./omni_prod/account_tenant.py:56:    def login(self,*,email:str,password:str)->tuple[Account,str]:
./omni_prod/agent_catalog.py:70:       ('signup', 'login', 'sessions', 'authorization', 'tenant isolation'),
./omni_prod/agent_os/agents.py:206:        forbidden_actions=('approve its own output', 'spend outside the reservation', 'read or print secrets',
./omni_prod/attempt_ledger.py:44:    """usage x catalog price. Unknown when the provider did not report tokens."""
./omni_prod/backup.py:4:deployed worker image, with the real environment. Never prints secrets.
./omni_prod/creator_accounts.py:32:    def login(self, *, email: str, password: str) -> tuple[Account, str]:
./omni_prod/creator_accounts.py:33:        return self.identity.login(email=email, password=password)
./omni_prod/design_system.py:29:def anti_template_fingerprint(tokens: DesignTokens) -> str:
./omni_prod/economics_report.py:9:  * metered = provider tokens x versioned catalog price (incl. thinking tokens
./omni_prod/evidence_export.py:10:It opens a READ ONLY transaction, writes nothing, calls no model and prints no secret (known secret shapes are
./omni_prod/identity_lifecycle.py:447:    def login(self, *, email: str, password: str) -> tuple[Account, str]:
./omni_prod/identity_lifecycle.py:479:    def logout(self, token: str) -> None:
./omni_prod/intake/interpreter.py:92:    (r'\b(no|without|don\'?t need( a)?)\s+(login|sign ?in|accounts?|passwords?|users)\b', 'login', 'none', HIGH),
./omni_prod/intelligence/inventory.py:28:    'all six catalog routes CONFIGURED on the worker; OPENAI_API_KEY and ANTHROPIC_API_KEY added from GitHub secrets')
./omni_prod/intelligence/matrix.py:184:            problems.append(f'{c["name"]}: credential reference differs from the catalog api_key_env')
./omni_prod/investor_app.py:647:        'design_fingerprint':anti_template_fingerprint(tokens),'agent_team':plan_team(target='web').to_dict(),
./omni_prod/investor_app.py:821:    try: return _v26.login(email=req.email,password=req.password)
./omni_prod/investor_app.py:908:    return {'release':'V26 Universal Pro','creator_security':['signup/login','PBKDF2 password hashing','signed session tokens','owner-scoped project IDs','cross-user denial'],
./omni_prod/investor_app.py:930:    try: role,issued=_v26.engine.runtime(deployment_id).login(email=req.email,credential=req.password)
./omni_prod/investor_app.py:1025:    try: role,issued=_unified.runtime(deployment_id).login(email=req.email,credential=req.password)
./omni_prod/investor_app.py:1088:    try: return _v27.login(email=req.email,password=req.password)
./omni_prod/investor_app.py:1253:    try: role,issued=_v27.engine.runtime(deployment_id).login(email=req.email,credential=req.password)
./omni_prod/investor_app.py:1353:        payload = _v28.login(email=req.email, password=req.password)
./omni_prod/investor_app.py:3304:        role, issued = _v28.engine.runtime(deployment_id).login(email=req.email, credential=req.password)
./omni_prod/isolation_check.py:1:"""Effective Preview vs Production isolation check (DB, queues, storage) -- read-only, prints NO secrets.
./omni_prod/isolation_check.py:7:for the worker host: its .env). The tool never connects to anything, never writes, and prints only non-secret identity
./omni_prod/isolation_check.py:9:fingerprints = SHARED; different = ISOLATED; a missing value on either side = UNKNOWN. Secrets are only compared for
./omni_prod/model_catalog.py:109:            raise ModelCatalogError(f'{name}: put the key in an environment variable and use api_key_env')
./omni_prod/model_catalog.py:112:            raise ModelCatalogError(f'{name}: api_key_env must be an UPPER_CASE variable name')
./omni_prod/model_catalog.py:160:        out.append(CatalogModel(option=option, endpoint=endpoint, max_output_tokens=max_out,
./omni_prod/model_probe.py:7:a fraction of a cent per model. Prints names, outcomes, token counts and the
./omni_prod/modification_diff.py:25:    'auth', 'login', 'password', 'secret', 'token', 'permission', 'security',
./omni_prod/postdeploy_checks.py:13:entitlement) and synthetic data only. Never prints secrets. Stages:
./omni_prod/postdeploy_checks.py:510:    s, log = api('GET', f'/api/v28/projects/{project}/builds/{b}/events?after=0', None, token)
./omni_prod/postdeploy_checks.py:553:    s, log = api('GET', f'/api/v28/projects/{project}/builds/{b}/events?after=0', None, token)
./omni_prod/providers/managed_web_saas.py:290:                cur.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
./omni_prod/providers/managed_web_saas.py:293:                cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
./omni_prod/providers/managed_web_saas.py:700:                    LOG.warning("could not delete generated secret for %s: %s", binding.resource_name, type(exc).__name__)
./omni_prod/providers/replicate_image_test.py:28:              'secret_key': fingerprint(creds.secret_key)}
./omni_prod/providers/replicate_image_test.py:30:                  'secret_key': fingerprint(env.get('OMNI_S3_SECRET_KEY', '').strip())}
./omni_prod/rights_ip.py:149:    (RightKind.TRADEMARK, RiskLevel.HIGH, r'(?i)\b(?:logo of|official logo of|use the brand|branded as)\s+([^,.;\n]{2,80})', 'Third-party brand/logo use needs trademark authorization/clearance.'),
./omni_prod/unified_engine.py:164:            'observability/logging.md': '# Logging\nStructured logs with request IDs and secret redaction.\n',
./omni_prod/v26_platform.py:19:    def login(self,*,email:str,password:str)->dict:
./omni_prod/v26_platform.py:20:        account,issued=self.accounts.login(email=email,password=password)
./tests/integration/test_v28_creator_persistence.py:16:        b=PostgresAccountService(token_secret=self.secret,pool=self.pool); logged,_=b.login(email=email,password='StrongPass123!')
./tests/test_attempt_ledger.py:71:    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {"KEY_ONE": "secret-a", "KEY_TWO": "secret-b"}),
./tests/test_deployment_verification.py:595:    def test_redirect_after_login_does_not_forward_the_bearer_token(self):
./tests/test_evidence_export.py:150:            z.writestr('app.py', 'print("hi")\nDB_PASSWORD="supersecretvalue123"\n')
./tests/test_intake_budget_pg.py:152:        cat = parse_model_catalog(raw, {'GEMINI_API_KEY': 'test-only-not-a-key'})
./tests/test_intelligence_plane.py:108:        models = parse_model_catalog(raw, {'GEMINI_API_KEY': 'k', 'OPENAI_API_KEY': 'k', 'ANTHROPIC_API_KEY': 'k'},
./tests/test_j1_j2_existing_engine_integration.py:66:    def test_log_secrets_redacted_before_truncation(self):
./tests/test_m5_identity_lifecycle.py:76:        logged, _ = self.identity.login(email=account.email, password="NewStrongPass123!")
./tests/test_m5_web_saas_acceptance.py:62:             'path': '/api/login', 'json': {'email': 'owner@example.test', 'password': 'secret'},
./tests/test_m5_web_saas_acceptance.py:210:    def logs(self, cid, tail=50): return 'fatal preview crash\nsecret=REDACTED'
./tests/test_model_transient_retry.py:60:    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {"GEMINI_API_KEY": "k"}),
./tests/test_provider_quota_and_dialects.py:25:    return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k', external=True),
./tests/test_provider_quota_and_dialects.py:240:        models = parse_model_catalog(raw, {'GEMINI_API_KEY': 'g', 'ANTHROPIC_API_KEY': 'a'})
./tests/test_provider_quota_and_dialects.py:246:        sol = parse_model_catalog(raw, {'OPENAI_API_KEY': 'o'})
./tests/test_provider_quota_and_dialects.py:257:            parse_model_catalog(json.dumps([{**base, 'extra_body': {'max_tokens': 1}}]), {})
./tests/test_skills_runtime_and_review.py:160:            return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k', external=True),
./tests/test_task_quality_routing.py:15:    return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k', external=True),
./tests/test_v24_international.py:95:    def test_design_varies(self): self.assertNotEqual(anti_template_fingerprint(derive_tokens('alpha')),anti_template_fingerprint(derive_tokens('beta')))
./tests/test_v26_universal_pro.py:28:        with self.assertRaises(PermissionError): s.login(email='a@example.com',password='wrong-password')
```


## E1 — עמידות: מצב בזיכרון

```
-- מודול-גלובלי שנכתב --
./infra/staging/verify_neon_bootstrap.py:13:expected = {}
./infra/staging/verify_neon_bootstrap.py:28:actual = {}
./omni_prod/investor_app.py:149:_v26=V26UniversalPlatform(token_secret=_control_plane_secret(),generated_app_token_secret=_generated_runtime_secret())
./omni_prod/investor_app.py:150:_v27=V27UniversalPlatform(token_secret=_control_plane_secret(),generated_app_token_secret=_generated_runtime_secret())
./omni_prod/investor_app.py:151:_v28_pool=None
./omni_prod/investor_app.py:183:_v28=_build_v28_platform()
./scripts/run_hostile_static_suite.py:10:cases=[]
./scripts/run_international_gate.py:14:checks={}
./scripts/run_live_sandbox_hostile.py:8:checks=[]
./scripts/run_quality_gate.py:14:checks = {}
./scripts/run_v25_offline_benchmark.py:14:rows=[]
./scripts/run_v25_offline_benchmark.py:30:by={}
./scripts/run_v25_release_gate.py:10:checks={}
./scripts/run_v26_release_gate.py:9:checks={}
./scripts/run_v27_release_gate.py:9:checks={}
./scripts/run_v28_offline_benchmark.py:15:rows=[]; started=time.monotonic()
./scripts/run_v28_release_gate.py:13:checks = {}
./scripts/run_v28_release_gate.py:69:margin_detail = {}
./tests/test_m49_sandbox_security.py:65:results = []
./tests/test_m49_sandbox_security.py:158:children = []
./tests/test_m49_sandbox_security.py:200:chunks = []
./tools/ui_conversation_walkthrough.py:19:log = []
./tools/ui_visual_edit/preview_host.py:24:procs = []
-- dict/list גלובלי ברמת מודול --
omni_prod/browser_fixtures.py:13:ITEMS = []
```


## E2 — עמידות: cache ומצב מיושן

```
-- lru_cache --
./omni_prod/intent_terms.py:12:from functools import lru_cache
./omni_prod/intent_terms.py:22:@lru_cache(maxsize=512)
./omni_prod/planning/registry_view.py:12:from functools import lru_cache
./omni_prod/planning/registry_view.py:27:@lru_cache(maxsize=1)
-- functools.cache --
-- global --
./omni_prod/investor_app.py:163:    global _v28_pool
./tests/test_attempt_ledger.py:35:    global _ENV_PATCH
```


## E3 — עמידות: חסימה בתוך async

```
-- time.sleep --
./omni_prod/active_jobs.py:198:        time.sleep(poll)
./omni_prod/behavior_acceptance.py:63:        time.sleep(0.4)
./omni_prod/browser_probe.py:51:        time.sleep(0.5)
./omni_prod/build_outbox_relay.py:62:            time.sleep(args.loop)
./omni_prod/db.py:71:                time.sleep(base_delay_seconds * (2 ** (attempt - 1)))
./omni_prod/intake/reservation_worker.py:182:            time.sleep(args.loop)
./omni_prod/intake/worker_route.py:42:                 wait_seconds: float | None = None, sleep=time.sleep, clock=time.monotonic,
./omni_prod/maintenance.py:299:        time.sleep(INTERVAL_SECONDS)
./omni_prod/postdeploy_checks.py:137:        time.sleep(0.5)
./omni_prod/postdeploy_checks.py:199:        time.sleep(every)
./omni_prod/postdeploy_checks.py:435:        time.sleep(6)  # router caches mode/token decisions for a few seconds
./omni_prod/preview_durability.py:67:            time.sleep(0.5)
./omni_prod/preview_runtime.py:323:                       sleep: Callable[[float], None] = time.sleep,
./omni_prod/preview_smoke.py:52:        time.sleep(0.5)
./omni_prod/providers/image_provider.py:314:        self.sleep = sleep or time.sleep
./omni_prod/routed_gateway.py:67:        sleep: Callable[[float], None] = time.sleep,
./omni_prod/visual_qa.py:58:        time.sleep(0.5)
./omni_prod/worker.py:59:                           sleep=time.sleep) -> int:
./omni_prod/worker_tasks.py:1278:                        http_get=None, sleep=time.sleep, clock=time.monotonic,
./scripts/run_v28_http_acceptance.py:45:        time.sleep(.15)
./tests/financial_fault_harness.py:52:        time.sleep(0.05)
./tests/test_deployment_verification.py:349:                    time.sleep(1.5)
./tests/test_golden_mod_path_live_postgres.py:250:                        time.sleep(0.3)  # widen the race window
./tests/test_intake_budget_pg.py:81:        time.sleep(0.6)
./tests/test_intake_budget_pg.py:127:            time.sleep(self.sleep)
./tests/test_intake_budget_pg.py:385:        time.sleep(1.3)
./tests/test_m49_sandbox_security.py:168:            time.sleep(5)
./tests/test_m4d2_live_postgres.py:366:        time.sleep(0.5)  # give the thread time to actually reach pg_advisory_xact_lock and block
./tests/test_m4d2_live_postgres.py:741:            time.sleep(0.05)
./tests/test_real_docker_drain_recovery.py:210:            time.sleep(1)
./tests/test_real_docker_drain_recovery.py:344:        time.sleep(4)
./tools/ui_conversation_walkthrough.py:50:    time.sleep(1.5)
./tools/ui_conversation_walkthrough.py:54:    time.sleep(0.5)
./tools/ui_conversation_walkthrough.py:61:    time.sleep(0.5)
./tools/ui_conversation_walkthrough.py:69:    page.click('#expandPreviewBtn'); time.sleep(0.3)
./tools/ui_conversation_walkthrough.py:72:    page.keyboard.press('Escape'); time.sleep(0.2)
./tools/ui_conversation_walkthrough.py:73:    page.click('#closePreviewBtn'); time.sleep(0.2)
./tools/ui_conversation_walkthrough.py:75:    page.click('#togglePreviewBtn'); time.sleep(0.2)
./tools/ui_conversation_walkthrough.py:80:        page.click('#sbOpen'); time.sleep(0.3)
./tools/ui_conversation_walkthrough.py:81:    page.click('#sbCollapse'); time.sleep(0.3)
./tools/ui_conversation_walkthrough.py:83:    page.click('#sbOpen'); time.sleep(0.3)
./tools/ui_conversation_walkthrough.py:88:    page.click('#langBtn2'); time.sleep(0.4)
./tools/ui_conversation_walkthrough.py:94:    page.wait_for_selector('.bubble.assistant'); time.sleep(1.2)
./tools/ui_conversation_walkthrough.py:97:    page.fill('#sbSearch', 'מספרה'); time.sleep(0.2)
./tools/ui_conversation_walkthrough.py:101:    page.click('#sbProjects button:has-text("מספרה")'); page.wait_for_selector('.bubble.assistant'); time.sleep(0.6)
./tools/ui_conversation_walkthrough.py:103:    page.click('#langBtn2'); time.sleep(0.3)
./tools/ui_conversation_walkthrough.py:106:    mp = m.new_page(); mp.goto(BASE); mp.wait_for_selector('.bubble.assistant'); time.sleep(0.8)
./tools/ui_conversation_walkthrough.py:108:    mp.click('#sbOpen'); time.sleep(0.4)
./tools/ui_conversation_walkthrough.py:110:    mp.click('#sbScrim', position={'x': 20, 'y': 420}); time.sleep(0.3)
./tools/ui_conversation_walkthrough.py:112:    mp.click('#mobileTabs [data-pane="preview"]' if mp.is_visible('#mobileTabs') else '#togglePreviewBtn'); time.sleep(0.4)
./tools/ui_visual_edit/preview_host.py:53:                    time.sleep(0.1)
./tools/ui_visual_edit/preview_host.py:56:        time.sleep(0.5)
./tools/ui_visual_edit/walkthrough.py:52:        time.sleep(0.2)
./tools/ui_visual_edit/walkthrough.py:142:    frame.locator('#save-btn').hover(); time.sleep(0.3)
./tools/ui_visual_edit/walkthrough.py:191:    time.sleep(0.8)
-- async def --
10
-- קריאה סינכרונית בתוך async --
omni_prod/active_jobs.py:15:  * modification_requests.status = 'RUNNING'
omni_prod/behavior_acceptance.py:59:        urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=2); ok = True; break
omni_prod/browser_probe.py:49:        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
omni_prod/investor_app.py:2286:        # explicitly instead so build_requests.rights_evidence actually writes.
omni_prod/investor_app.py:2691:# time (modification_requests.target_markets_json/rights_evidence_json,
omni_prod/media_gateway.py:40:            with urllib.request.urlopen(req,timeout=self.endpoint.timeout_seconds) as r: body=json.loads(r.read().decode())
omni_prod/model_gateway.py:137:    def __init__(self, endpoint: ModelEndpoint, *, urlopen: Callable[..., Any] | None = None):
omni_prod/model_gateway.py:139:        self._urlopen = urlopen or request.urlopen
omni_prod/model_gateway.py:194:            with self._urlopen(req, timeout=self.endpoint.timeout_seconds) as resp:
omni_prod/postdeploy_checks.py:111:        with urlrequest.urlopen(req, timeout=timeout) as resp:
omni_prod/postdeploy_checks.py:451:        with urlrequest.urlopen(req, timeout=60) as resp:
omni_prod/preview_durability.py:54:    with urlrequest.urlopen(req, timeout=timeout) as resp:
omni_prod/preview_runtime.py:352:        with urlrequest.urlopen(req, timeout=timeout) as resp:
omni_prod/preview_smoke.py:45:        with urllib.request.urlopen("http://127.0.0.1:%%d%%s" %% (port, path), timeout=2) as r:
omni_prod/preview_smoke.py:57:        with urllib.request.urlopen("http://127.0.0.1:%%d/" %% port, timeout=3) as r:
omni_prod/preview_smoke.py:68:                with urllib.request.urlopen("http://127.0.0.1:%%d/%%s" %% (port, ref.lstrip("./")), timeout=3) as a:
omni_prod/providers/image_provider.py:298:                 urlopen=None, sleep: Callable[[float], None] | None = None, poll_interval_seconds: float = 2.0,
omni_prod/providers/image_provider.py:307:        self.urlopen = urlopen or request.urlopen
omni_prod/providers/image_provider.py:364:        with self.urlopen(req, timeout=self.config.timeout_seconds) as resp:
omni_prod/providers/image_provider.py:510:def build_image_provider(env: Mapping[str, str] | None = None, *, journal, urlopen=None, fetcher=None):
omni_prod/providers/image_provider.py:528:    return PredictionImageProvider(config=config, resolve_reference=resolve, journal=journal, urlopen=urlopen,
omni_prod/providers/image_provider.py:533:                                 worker_id: str, urlopen=None, fetcher=None):
omni_prod/providers/image_provider.py:539:    provider = build_image_provider(env, journal=journal, urlopen=urlopen, fetcher=fetcher)
omni_prod/providers/managed_web_saas.py:264:def _probe_url(url: str, *, token: str, timeout: float = 5.0, urlopen=None) -> int:
omni_prod/providers/managed_web_saas.py:265:    opener = urlopen or request.urlopen
omni_prod/providers/replicate_connection.py:47:def check_replicate_connection(env, *, urlopen=None):
omni_prod/providers/replicate_connection.py:63:        with (urlopen or request.urlopen)(req, timeout=10) as response:
omni_prod/providers/replicate_image_test.py:51:    def __init__(self, *, env, journal, store, urlopen=None, fetcher=None):
omni_prod/providers/replicate_image_test.py:55:            journal=journal, urlopen=urlopen, fetcher=fetcher)
omni_prod/remote_sandbox.py:37:    def __init__(self, config: RemoteSandboxConfig, *, urlopen=None):
omni_prod/remote_sandbox.py:38:        self.config=config; self._urlopen=urlopen or request.urlopen
omni_prod/remote_sandbox.py:49:            with self._urlopen(req,timeout=self.config.timeout_seconds) as resp:
omni_prod/rights_ip.py:140:# but these rules remain a fail-closed floor for explicit imitation/identity requests.
omni_prod/safe_fetch.py:123:    urlopen: Callable | None = None  # injected transport for tests; validation still applies
omni_prod/safe_fetch.py:159:        opener = self.urlopen or self._opener().open
omni_prod/secrets_manager.py:29:    def __init__(self,config:VaultHttpConfig,*,urlopen=None): self.config=config; self.urlopen=urlopen or request.urlopen
omni_prod/secrets_manager.py:38:            with self.urlopen(req,timeout=self.config.timeout_seconds) as r: payload=json.loads(r.read().decode())
omni_prod/secrets_manager.py:71:                 timeout_seconds: float = 5, urlopen=None):
omni_prod/secrets_manager.py:77:        self.urlopen = urlopen or request.urlopen
omni_prod/secrets_manager.py:99:            with self.urlopen(req, timeout=self.timeout_seconds) as resp:
omni_prod/secrets_manager.py:161:                 urlopen=None, clock=None):
omni_prod/secrets_manager.py:175:        self.urlopen = urlopen or request.build_opener(_NoInfisicalRedirect()).open
omni_prod/secrets_manager.py:198:            with self.urlopen(req, timeout=self.timeout_seconds) as response:
omni_prod/stripe_billing.py:45:        self.opener = opener or urllib.request.urlopen
omni_prod/visual_qa.py:56:        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
```


## E4 — עמידות: זמן

```
-- utcnow (naive) --
-- now() --
-- time.time() כ-ID --
./omni_prod/auth.py:26:    ts=int(time.time() if now is None else now)
./omni_prod/auth.py:44:        exp=int(data['exp']); ts=int(time.time() if now is None else now)
./omni_prod/behavior_acceptance.py:56:ok, deadline = False, time.time() + 20
./omni_prod/behavior_acceptance.py:57:while time.time() < deadline and p.poll() is None:
./omni_prod/conversation/store.py:55:               'request_key': request_key, 'created_at': time.time(), 'cost_state': cost_state,
./omni_prod/conversation/store.py:73:        since = (time.time() if now is None else now) - 86400
./omni_prod/preview_access.py:139:        minute = int(time.time() // 60)
./omni_prod/preview_smoke.py:39:deadline, verdict = time.time() + %(seconds)d, "no answer within %(seconds)ds"
./omni_prod/preview_smoke.py:40:while time.time() < deadline:
./omni_prod/provider_router.py:142:            reference = time.time() if now is None else now
./omni_prod/provider_router.py:195:        reference = time.time() if now is None else now
./omni_prod/provider_router.py:216:        reference = time.time() if now is None else now
./omni_prod/rate_limit.py:27:        now=int(time.time()); window=now//self.window_seconds; rk=f'{self.prefix}:{window}:{key}'
./omni_prod/redis_circuit_breaker.py:42:        now = time.time() if now is None else now
./omni_prod/redis_circuit_breaker.py:76:        now = time.time() if now is None else now
./omni_prod/redis_circuit_breaker.py:89:        now = time.time() if now is None else now
./omni_prod/stripe_billing.py:101:    current = int(time.time()) if now is None else int(now)
./omni_prod/verification_contract.py:153:        self.finished_at = time.time()
./omni_prod/verification_contract.py:203:    clock = time.time() if now is None else now
./omni_prod/worker_tasks.py:636:                now=time.time(),
./scripts/run_v28_http_acceptance.py:39:    deadline=time.time()+15
./scripts/run_v28_http_acceptance.py:40:    while time.time()<deadline:
./tests/financial_fault_harness.py:128:                             ('req_' + uuid.uuid4().hex, build_id, str(PROVIDER_COST), time.time()))
./tests/test_deployment_verification.py:90:        self.assertFalse(promote(ok, now=time.time() + 2 * vc.DEFAULT_TTL_SECONDS)[0])  # expired
./tests/test_deployment_verification.py:150:        now = time.time()
./tests/test_deployment_verification.py:246:        now = time.time()
./tests/test_v28_148ai_launch.py:200:        now=int(time.time())
./tests/test_v28_148ai_launch.py:246:        event={'id':'evt_'+uuid.uuid4().hex,'created':int(time.time()),'type':'checkout.session.completed','data':{'object':{'id':'cs_test_paid','subscription':'sub_test_paid','payment_status':'paid','mode':'subscription','client_reference_id':uid,'metadata':{'user_id':uid,'plan_code':'pro'}}}}
./tests/test_v28_148ai_launch.py:247:        body=json.dumps(event,separators=(',',':')).encode(); ts=int(time.time()); secret='verified-webhook-secret'
./tools/ui_visual_edit/walkthrough.py:45:    end = time.time() + timeout / 1000
./tools/ui_visual_edit/walkthrough.py:46:    while time.time() < end:
```


## E5 — עמידות: כתיבה לדיסק בסביבת serverless

```
omni_prod/agent_os/audit.py:35:ROOT = Path(__file__).resolve().parents[2]
omni_prod/agent_os/departments.py:22:ROOT = Path(__file__).resolve().parents[2]
omni_prod/agent_os/meta.py:24:ROOT = Path(__file__).resolve().parents[2]
omni_prod/agent_os/recorder.py:72:    def _open(self, agent: str, skills=(), cost: Decimal | None = None) -> None:
omni_prod/agent_os/recorder.py:85:        self._open(agent, skills)
omni_prod/agent_os/recorder.py:89:        self._open('qa_agent', ('unit_test_execution',))
omni_prod/agent_os/recorder.py:351:    def _open(self, stage):
omni_prod/agent_os/recorder.py:380:            self._open(stage)
omni_prod/agent_os/recorder.py:426:        tid = self._open('unit_tests')
omni_prod/agent_os/skills.py:19:TAXONOMY: dict[str, list[str]] = json.loads((Path(__file__).with_name('skills_taxonomy.json')).read_text(encoding='utf-8'))
omni_prod/agent_os/truth_matrix.py:23:ROOT = Path(__file__).resolve().parents[2]
omni_prod/attestation.py:7:    with open(path,'rb') as f:
omni_prod/attestation.py:19:    Path(path).write_text(json.dumps(a,indent=2,sort_keys=True),encoding='utf-8')
omni_prod/backup.py:78:            with open(path, 'rb') as f:
omni_prod/backup.py:92:    with open(os.path.join(bk, 'manifest.json'), 'w') as f:
omni_prod/backup.py:107:        with open(path, 'rb') as f:
omni_prod/backup.py:117:    os.makedirs(os.path.join(bk, 'restore'), exist_ok=True)
omni_prod/backup.py:121:        with open(os.path.join(bk, 'restore', name), 'wb') as f:
omni_prod/backup.py:130:    with open(os.path.join(bk, 'restore', 'manifest.json')) as f:
omni_prod/backup.py:170:    with tarfile.open(path, 'r:gz') as tar:
omni_prod/backup_manifest.py:8:    with open(path, "rb") as f:
omni_prod/backup_manifest.py:14:    base = Path(root)
omni_prod/backup_manifest.py:27:    base = Path(root)
omni_prod/backup_manifest.py:36:    base = Path(root)
omni_prod/behavior_acceptance.py:33:_RUNNER_SOURCE = (Path(__file__).with_name('web_saas_acceptance.py')).read_text(encoding='utf-8')
omni_prod/behavior_acceptance.py:46:cfg = json.load(open(".omni/_behavior_run.json"))
omni_prod/behavior_acceptance.py:50:c = json.load(open(".omni/project.json"))
omni_prod/behavior_acceptance.py:55:p = subprocess.Popen(c["start"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
omni_prod/behavior_acceptance.py:59:        urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=2); ok = True; break
omni_prod/benchmark_suite.py:100:        Path(path).write_text(json.dumps(payload, indent=2), encoding='utf-8')
omni_prod/branding.py:32:        self.asset_dir = Path(asset_dir) if asset_dir else Path(__file__).resolve().parent / 'assets' / 'brand'
omni_prod/branding.py:134:        base = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
omni_prod/branding.py:135:        mark = Image.open(self.asset_dir / '148ai-logo-256.png').convert('RGBA')
omni_prod/browser_probe.py:39:c = json.load(open(".omni/project.json"))
omni_prod/browser_probe.py:42:srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
omni_prod/browser_probe.py:49:        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
omni_prod/capability_executor.py:117:        with path.open("rb") as source:
omni_prod/capability_executor.py:141:            source_path = Path(payload.file_path)
omni_prod/db.py:23:    def open(self) -> "DatabasePool":
omni_prod/db.py:47:            self.open()
omni_prod/demo_project.py:75:            {'name': 'html exists', 'argv': ['python', '-c', "from pathlib import Path; assert Path('index.html').exists()"], 'acceptance_ids': ['A1']},
omni_prod/demo_project.py:76:            {'name': 'request preserved', 'argv': ['python', '-c', "import json; assert json.load(open('request.json', encoding='utf-8'))['prompt']"], 'acceptance_ids': ['A2']},
omni_prod/demo_project.py:77:            {'name': 'manifest present', 'argv': ['python', '-c', "from pathlib import Path; assert Path('.omni/project.json').exists()"], 'acceptance_ids': ['A3']},
omni_prod/demo_project.py:98:        'tests/smoke_test.py': "from pathlib import Path\nassert Path('index.html').exists()\nassert 'aria-live' in Path('index.html').read_text()\n",
omni_prod/evidence_export.py:116:        os.makedirs(root, exist_ok=True)
omni_prod/evidence_export.py:118:            if PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts:
omni_prod/evidence_export.py:123:            os.makedirs(os.path.dirname(dst), exist_ok=True)
omni_prod/evidence_export.py:124:            with open(dst, 'wb') as fh:
omni_prod/evidence_export.py:260:        with open(argv[argv.index('--out') + 1], 'w', encoding='utf-8') as fh:
omni_prod/failure_replay.py:45:                txt = open(p, encoding='utf-8', errors='replace').read()
omni_prod/failure_replay.py:111:    exp = json.load(open(paths[0], encoding='utf-8'))
omni_prod/game_pipeline.py:19:        exe=shutil.which('godot4') or shutil.which('godot')
omni_prod/game_pipeline.py:22:        exe=shutil.which('unity-editor') or shutil.which('Unity')
omni_prod/game_pipeline.py:25:        exe=shutil.which('UnrealEditor') or shutil.which('UnrealEditor-Cmd')
omni_prod/gate_replay.py:161:        with open(path, 'wb') as f:
omni_prod/intake/benchmark.py:21:FIXTURES = Path(__file__).resolve().parents[2] / 'tests' / 'fixtures' / 'intake' / 'cases.json'
omni_prod/intake/budget.py:93:        path = Path(__file__).resolve().parents[2] / 'infra' / 'worker-host' / 'model-catalog.json'
omni_prod/intake/lanes.py:29:QUALIFICATION_FILE = Path(__file__).resolve().parents[2] / 'docs' / 'evidence' / 'intake' / 'low_risk_lane_qualification.json'
omni_prod/intake/lanes.py:33:    path = Path(os.getenv('OMNI_INTAKE_LOW_RISK_QUALIFICATION', '') or QUALIFICATION_FILE)
omni_prod/intelligence/matrix.py:30:ROOT = Path(__file__).resolve().parents[2]
omni_prod/international_readiness.py:36:        CapabilityGate('production_runtime',True,bool(shutil.which('docker')),'Postgres/Redis/S3/queue/autoscaling contracts exist; live stack depends on Docker/services'),
omni_prod/investor_app.py:679:        if not shutil.which('docker'): raise RuntimeError('docker or OMNI_SANDBOX_RUNNER_URL is required for live generated-code execution')
omni_prod/investor_app.py:1059:_ASSET_DIR=Path(__file__).resolve().parent/'assets'
omni_prod/investor_app.py:3345:_BRAND_DIR = Path(__file__).resolve().parent / 'assets' / 'brand'
omni_prod/isolation_check.py:117:        ids, notes = identities(parse_env(open(files[0], encoding='utf-8').read()))
omni_prod/isolation_check.py:125:    out = compare(*(parse_env(open(f, encoding='utf-8').read()) for f in files), labels=tuple(labels))
omni_prod/media_branding.py:61:        ffmpeg = shutil.which('ffmpeg')
omni_prod/media_branding.py:68:            td = Path(td)
omni_prod/media_gateway.py:40:            with urllib.request.urlopen(req,timeout=self.endpoint.timeout_seconds) as r: body=json.loads(r.read().decode())
omni_prod/migrate.py:26:MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / 'infra' / 'postgres'
omni_prod/migrations.py:21:    root = Path(directory)
omni_prod/mobile_pipeline.py:21:        return MobileBuildPlan('android',f,cmd,('ANDROID_KEYSTORE','ANDROID_KEYSTORE_PASSWORD','ANDROID_KEY_ALIAS','ANDROID_KEY_PASSWORD'),'aab', bool(shutil.which('java')))
omni_prod/mobile_pipeline.py:24:        return MobileBuildPlan('ios',f,cmd,('APPLE_TEAM_ID','APP_STORE_CONNECT_KEY_ID','APP_STORE_CONNECT_ISSUER_ID','APP_STORE_CONNECT_PRIVATE_KEY'),'ipa', bool(shutil.which('xcodebuild')))
omni_prod/model_gateway.py:194:            with self._urlopen(req, timeout=self.endpoint.timeout_seconds) as resp:
omni_prod/planning/registry_view.py:15:ROOT = Path(__file__).resolve().parents[2]
omni_prod/postdeploy_checks.py:52:DATA = pathlib.Path(os.environ.get("DATA_DIR", "/tmp")) / "count.txt"
omni_prod/postdeploy_checks.py:89:        with open(STATE_PATH) as f:
omni_prod/postdeploy_checks.py:96:    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
omni_prod/postdeploy_checks.py:97:    with open(STATE_PATH, 'w') as f:
omni_prod/postdeploy_checks.py:111:        with urlrequest.urlopen(req, timeout=timeout) as resp:
omni_prod/postdeploy_checks.py:338:    expected = max(int(p.name.split('_', 1)[0]) for p in __import__('pathlib').Path(__file__).resolve().parents[1]
omni_prod/postdeploy_checks.py:339:                   .joinpath('infra', 'postgres').glob('*.sql')) if __import__('pathlib').Path(__file__).resolve()\
omni_prod/postdeploy_checks.py:451:        with urlrequest.urlopen(req, timeout=60) as resp:
omni_prod/preflight.py:31:    return shutil.which(name) is not None
omni_prod/preview_durability.py:27:DATA = pathlib.Path(os.environ.get("DATA_DIR", "/tmp")) / "count.txt"
omni_prod/preview_durability.py:54:    with urlrequest.urlopen(req, timeout=timeout) as resp:
omni_prod/preview_durability.py:115:            shutil.rmtree(project_data_dir(provider.data_root, pid), ignore_errors=True)
omni_prod/preview_inspector.py:47:  function cssPath(el) {
omni_prod/preview_inspector.py:66:             attrs: attrs, text: text, path: cssPath(el), html: htmlCopy, page: location.pathname,
omni_prod/preview_runtime.py:352:        with urlrequest.urlopen(req, timeout=timeout) as resp:
omni_prod/preview_runtime.py:362:        path.parent.mkdir(parents=True, exist_ok=True)
omni_prod/preview_runtime.py:385:    p = Path(path).resolve()
omni_prod/preview_runtime.py:386:    tmp = Path(tempfile.gettempdir()).resolve()
omni_prod/preview_runtime.py:409:    return str(Path(root) / f'p-{digest}')
omni_prod/preview_runtime.py:429:        os.makedirs(path, mode=0o700, exist_ok=True)
omni_prod/preview_runtime.py:457:        root = Path(tempfile.mkdtemp(prefix=f'{PREVIEW_WORKDIR_PREFIX}{preview_id}-'))
omni_prod/preview_runtime.py:472:            shutil.rmtree(root, ignore_errors=True)
omni_prod/preview_runtime.py:493:            shutil.rmtree(root, ignore_errors=True)
omni_prod/preview_runtime.py:525:        shutil.rmtree(path, ignore_errors=True)
omni_prod/preview_runtime.py:526:        return not Path(path).exists()
omni_prod/preview_smoke.py:35:c = json.load(open(".omni/project.json"))
omni_prod/preview_smoke.py:38:p = subprocess.Popen(c["start"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
omni_prod/preview_smoke.py:45:        with urllib.request.urlopen("http://127.0.0.1:%%d%%s" %% (port, path), timeout=2) as r:
omni_prod/preview_smoke.py:57:        with urllib.request.urlopen("http://127.0.0.1:%%d/" %% port, timeout=3) as r:
omni_prod/preview_smoke.py:68:                with urllib.request.urlopen("http://127.0.0.1:%%d/%%s" %% (port, ref.lstrip("./")), timeout=3) as a:
omni_prod/provenance.py:17:    with open(path, "rb") as f:
omni_prod/provenance.py:24:    p = Path(path)
omni_prod/provenance.py:39:    out = Path(destination)
omni_prod/provenance.py:40:    out.parent.mkdir(parents=True, exist_ok=True)
omni_prod/providers/image_provider.py:364:        with self.urlopen(req, timeout=self.config.timeout_seconds) as resp:
omni_prod/providers/qstash_scheduler.py:66:            with self._open(req, timeout=10) as resp:
omni_prod/readiness.py:23:        ReadinessGate('python',bool(shutil.which('python')),True,'Python runtime available'),
omni_prod/readiness.py:24:        ReadinessGate('docker',bool(shutil.which('docker')),True,'Required for isolated generated-code execution'),
omni_prod/readiness.py:31:        ReadinessGate('android_toolchain',bool(shutil.which('java')),False,'JDK available for Android builds'),
omni_prod/readiness.py:32:        ReadinessGate('ios_toolchain',bool(shutil.which('xcodebuild')),False,'Xcode required for signed iOS builds'),
omni_prod/recovery_drill.py:8:        root = Path(td)
omni_prod/recovery_drill.py:10:        (root / "artifacts").mkdir()
omni_prod/redis_circuit_breaker.py:70:    def force_open(
omni_prod/registry_audit.py:44:ROOT = Path(__file__).resolve().parent.parent
omni_prod/release_gate.py:15:    base = Path(root)
```


## F1 — תורים ו-workers

```
-- enqueue --
./omni_prod/active_jobs.py-52-    mods = _rows(conn, "SELECT id, status FROM modification_requests WHERE status IN ('QUEUED', 'RUNNING')",
./omni_prod/active_jobs.py-53-                 errors, 'modification_requests')
./omni_prod/active_jobs.py-54-    intake = _rows(conn, "SELECT id, state FROM intake_reservations WHERE state IN ('RESERVED', 'CLAIMED', 'EXECUTING')",
./omni_prod/active_jobs.py-55-                   errors, 'intake_reservations')
./omni_prod/active_jobs.py:56:    pending = _rows(conn, 'SELECT reservation_id FROM intake_outbox WHERE enqueued_at IS NULL', errors, 'intake_outbox')
--
./omni_prod/active_jobs.py-87-        if host:
./omni_prod/active_jobs.py-88-            from .queueing import preview_host_queue
./omni_prod/active_jobs.py-89-            names.append(preview_host_queue(host))
./omni_prod/active_jobs.py-90-        names += [q.name for q in Queue.all(connection=redis)]
./omni_prod/active_jobs.py:91:        # A host-scoped queue is not in rq's queue set until something was enqueued on it, and this process may not
--
./omni_prod/agent_os/skills.py-203-    'worker_health_check': (('omni_prod.postdeploy_checks:stage_free',), (FREE, DEPLOY), ''),
./omni_prod/agent_os/skills.py-204-    'queue_health_check': (('path:.github/workflows/deploy-worker.yml',), (DEPLOY,), ''),
./omni_prod/agent_os/skills.py-205-    'storage_health_check': (('path:.github/workflows/deploy-worker.yml',), (DEPLOY,), ''),
./omni_prod/agent_os/skills.py-206-    'database_health_check': (('omni_prod.postdeploy_checks:stage_free',), (FREE,), ''),
./omni_prod/agent_os/skills.py:207:    'queue_job_submit': (('omni_prod.queueing:enqueue_build',), (PAID, FREE), ''),
--
./omni_prod/build_cost_plan.py-15-  capabilities without an assignment are not priced (and will not run).
./omni_prod/build_cost_plan.py-16-* An unknown required quote is never invented: ``CostQuoteUnknown`` blocks the
./omni_prod/build_cost_plan.py-17-  build before any reservation. It subclasses PermissionError so existing API
./omni_prod/build_cost_plan.py-18-  handlers map it to 402 like other authorization failures.
./omni_prod/build_cost_plan.py:19:* The full total is reserved once, durably, before anything is enqueued.
--
./omni_prod/build_cost_plan.py-29-from .provider_contracts import ProviderQuote
./omni_prod/build_cost_plan.py-30-from .provider_pricing import BuildEconomicsQuote, aggregate_build_quote
./omni_prod/build_cost_plan.py-31-
./omni_prod/build_cost_plan.py-32-__all__ = ["BuildCostInputs", "CostQuoteUnknown", "build_economics_quote", "collect_build_cost_inputs",
./omni_prod/build_cost_plan.py:33:           "reserve_and_enqueue"]
--
./omni_prod/build_cost_plan.py-156-    }
./omni_prod/build_cost_plan.py-157-    return quote, components
./omni_prod/build_cost_plan.py-158-
./omni_prod/build_cost_plan.py-159-
./omni_prod/build_cost_plan.py:160:def reserve_and_enqueue(*, quote: BuildEconomicsQuote, reserve: Callable[[Decimal], Any], enqueue: Callable[[], Any]):
./omni_prod/build_cost_plan.py:161:    """Reserve the whole conservative total; enqueue only after it succeeded."""
./omni_prod/build_cost_plan.py-162-    decision = reserve(quote.total_authorized_variable_usd)
./omni_prod/build_cost_plan.py-163-    if not getattr(decision, "allowed", False):
./omni_prod/build_cost_plan.py-164-        raise PermissionError(getattr(decision, "reason", "reservation denied"))
./omni_prod/build_cost_plan.py:165:    enqueue()
--
./omni_prod/build_outbox_relay.py-1-from __future__ import annotations
./omni_prod/build_outbox_relay.py-2-
./omni_prod/build_outbox_relay.py:3:"""Relay for build_outbox rows whose Redis enqueue never happened.
--
./omni_prod/build_outbox_relay.py-20-
./omni_prod/build_outbox_relay.py-21-BUILD_JOB_PATH = "omni_prod.worker_tasks.execute_live_build_job"
./omni_prod/build_outbox_relay.py-22-
./omni_prod/build_outbox_relay.py-23-
./omni_prod/build_outbox_relay.py:24:def relay_once(pool, redis_url: str, *, older_than_seconds: int = 30, limit: int = 100, enqueue=None) -> list[str]:
./omni_prod/build_outbox_relay.py-25-    from .job_repository import PostgresBuildRepository
./omni_prod/build_outbox_relay.py:26:    if enqueue is None:
./omni_prod/build_outbox_relay.py:27:        from .queueing import enqueue_build
./omni_prod/build_outbox_relay.py-28-
./omni_prod/build_outbox_relay.py:29:        def enqueue(build_id: str) -> None:
./omni_prod/build_outbox_relay.py:30:            enqueue_build(redis_url, BUILD_JOB_PATH, build_id, job_id=build_id)
./omni_prod/build_outbox_relay.py-31-
./omni_prod/build_outbox_relay.py-32-    return PostgresBuildRepository(pool).dispatch_pending_outbox(
./omni_prod/build_outbox_relay.py:33:        enqueue, older_than_seconds=older_than_seconds, limit=limit)
--
./omni_prod/conversation/supervisor.py-215-
./omni_prod/conversation/supervisor.py-216-class ConversationSupervisor:
./omni_prod/conversation/supervisor.py-217-    def __init__(self, *, briefs, store, gateway=None, architect: ChiefArchitect | None = None, credits: int | None = None,
./omni_prod/conversation/supervisor.py-218-                 budget_usd: Decimal = Decimal('0.50'), context=None, worker_interpreter=None,
./omni_prod/conversation/supervisor.py:219:                 reservations=None, enqueue=None):
--
./omni_prod/conversation/supervisor.py-225-        self.budget_usd = budget_usd
./omni_prod/conversation/supervisor.py-226-        self.context = context or (lambda project_id: {})   # durable build/version state (read-only)
./omni_prod/conversation/supervisor.py-227-        self.worker_interpreter = worker_interpreter           # injected in tests
./omni_prod/conversation/supervisor.py-228-        self.reservations = reservations                       # intake.budget.ReservationService (migration 037)
./omni_prod/conversation/supervisor.py:229:        self.enqueue = enqueue                                 # RQ enqueue of a reservation id
--
./omni_prod/conversation/supervisor.py-238-                return (self.reservations.counted(f'project:{account_id}:{project_id}'),
./omni_prod/conversation/supervisor.py-239-                        self.reservations.counted(B.DAILY_SCOPE))
./omni_prod/conversation/supervisor.py-240-            return self.store.conversation_cost(project_id), self.store.daily_cost()
./omni_prod/conversation/supervisor.py-241-        worker_route_available = self.worker_interpreter is not None or (
./omni_prod/conversation/supervisor.py:242:            self.reservations is not None and self.enqueue is not None)
--
./omni_prod/conversation/supervisor.py-254-        if self.worker_interpreter is not None:
./omni_prod/conversation/supervisor.py-255-            if hasattr(self.worker_interpreter, 'task'):
./omni_prod/conversation/supervisor.py-256-                self.worker_interpreter.task = task
./omni_prod/conversation/supervisor.py-257-            return self.worker_interpreter
./omni_prod/conversation/supervisor.py:258:        if self.reservations is None or self.enqueue is None or not account_id:
./omni_prod/conversation/supervisor.py-259-            return DeterministicInterpreter()
./omni_prod/conversation/supervisor.py-260-        from ..intake.worker_route import ReservedWorkerInterpreter
./omni_prod/conversation/supervisor.py:261:        return ReservedWorkerInterpreter(self.reservations, self.enqueue, account_id=account_id,
--
./omni_prod/creator_plan.py-2-
./omni_prod/creator_plan.py-3-Compiles (and durably saves) the next Build Contract revision for a prompt,
./omni_prod/creator_plan.py-4-then reports what 148AI understood, which capabilities and infrastructure the
./omni_prod/creator_plan.py-5-product needs, the conservative cost authorization and every named blocker.
./omni_prod/creator_plan.py:6:Nothing here reserves credits, calls a model provider or enqueues work: the
--
./omni_prod/intake/budget.py-486-                    evidence={'evidence': evidence[:1000], 'resolved_by': resolved_by[:120]})
./omni_prod/intake/budget.py-487-        return _res(row)
./omni_prod/intake/budget.py-488-
./omni_prod/intake/budget.py-489-    # -- outbox ------------------------------------------------------------------
./omni_prod/intake/budget.py:490:    def mark_enqueued(self, reservation_id: str) -> None:
./omni_prod/intake/budget.py-491-        with self.pool.connection() as conn:
./omni_prod/intake/budget.py-492-            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:493:                cur.execute('UPDATE intake_outbox SET enqueued_at = now(), deliveries = deliveries + 1 '
./omni_prod/intake/budget.py:494:                            'WHERE reservation_id = %s AND enqueued_at IS NULL', (reservation_id,))
./omni_prod/intake/budget.py-495-
./omni_prod/intake/budget.py:496:    def relay_once(self, enqueue, *, older_than_seconds: int = 5, limit: int = 100) -> list[str]:
./omni_prod/intake/budget.py:497:        """Deliver outbox rows whose immediate enqueue never happened (crash,
--
./omni_prod/intake/budget.py-501-        for _ in range(max(0, int(limit))):
./omni_prod/intake/budget.py-502-            with self.pool.connection() as conn:
./omni_prod/intake/budget.py-503-                with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py-504-                    cur.execute('SELECT o.reservation_id FROM intake_outbox o JOIN intake_reservations r '
./omni_prod/intake/budget.py:505:                                'ON r.id = o.reservation_id WHERE o.enqueued_at IS NULL AND r.state = %s '
--
./omni_prod/intake/budget.py-507-                                'FOR UPDATE OF o SKIP LOCKED', (RESERVED, int(older_than_seconds)))
./omni_prod/intake/budget.py-508-                    row = cur.fetchone()
./omni_prod/intake/budget.py-509-                    if not row:
./omni_prod/intake/budget.py-510-                        return sent
./omni_prod/intake/budget.py:511:                    enqueue(row[0])                     # raises -> rolls back, stays pending
./omni_prod/intake/budget.py:512:                    cur.execute('UPDATE intake_outbox SET enqueued_at = now(), deliveries = deliveries + 1 '
--
./omni_prod/intake/reservation_worker.py-160-    from ..db import DatabasePool
./omni_prod/intake/reservation_worker.py-161-    pool = DatabasePool(db)
./omni_prod/intake/reservation_worker.py-162-    svc = B.ReservationService(pool)
./omni_prod/intake/reservation_worker.py-163-
./omni_prod/intake/reservation_worker.py:164:    def enqueue(rid):
./omni_prod/intake/reservation_worker.py:165:        from ..queueing import enqueue_build
./omni_prod/intake/reservation_worker.py:166:        enqueue_build(redis_url, RQ_JOB, rid, job_id=rid, queue_name=INTAKE_QUEUE, timeout=120)
--
./omni_prod/intake/reservation_worker.py-168-        while True:
./omni_prod/intake/reservation_worker.py-169-            try:
./omni_prod/intake/reservation_worker.py-170-                out = {}
./omni_prod/intake/reservation_worker.py-171-                if args.cmd in ('relay', 'maintain'):
./omni_prod/intake/reservation_worker.py:172:                    out['relayed'] = svc.relay_once(enqueue)
--
./omni_prod/intake/worker_route.py-4-    API (Vercel)                                  worker host (intake-worker)
./omni_prod/intake/worker_route.py-5-    ReservedWorkerInterpreter.interpret()
./omni_prod/intake/worker_route.py-6-      QUOTE   worst case of the bounded call
./omni_prod/intake/worker_route.py-7-      RESERVE reservation + outbox row (1 txn)  ->  RQ 'omni-intake', job id = reservation id
./omni_prod/intake/worker_route.py:8:      enqueue (fast path; relay is the backstop)    reservation_worker.execute_reservation():
--
./omni_prod/intake/worker_route.py-36-
./omni_prod/intake/worker_route.py-37-class ReservedWorkerInterpreter:
./omni_prod/intake/worker_route.py-38-    name = 'model-via-worker'
./omni_prod/intake/worker_route.py-39-
./omni_prod/intake/worker_route.py:40:    def __init__(self, service: B.ReservationService, enqueue, *, account_id: str, project_id: str,
./omni_prod/intake/worker_route.py-41-                 request_key: str | None, caps: B.Caps, lane: str = B.PRODUCTION, campaign_id: str | None = None,
./omni_prod/intake/worker_route.py-42-                 wait_seconds: float | None = None, sleep=time.sleep, clock=time.monotonic,
./omni_prod/intake/worker_route.py-43-                 task: str = 'conversation'):
./omni_prod/intake/worker_route.py:44:        self.svc, self.enqueue = service, enqueue
--
./omni_prod/intake/worker_route.py-76-            base.dropped.append(f'model not used: {type(exc).__name__}')
./omni_prod/intake/worker_route.py-77-            return base
./omni_prod/intake/worker_route.py-78-        if r.state == B.RESERVED:
./omni_prod/intake/worker_route.py-79-            try:
./omni_prod/intake/worker_route.py:80:                self.enqueue(r.id)
./omni_prod/intake/worker_route.py:81:                self.svc.mark_enqueued(r.id)
./omni_prod/intake/worker_route.py-82-            except Exception as exc:    # queue down: nothing was sent, so give the money back now
./omni_prod/intake/worker_route.py:83:                self.svc.release(r.id, reason=f'enqueue failed: {type(exc).__name__}')
--
./omni_prod/intake/worker_route.py-112-        return merge(base, model, interpreter=f'model:{current.model or "?"}+deterministic', cost_usd=current.actual_usd,
./omni_prod/intake/worker_route.py-113-                     cost_state=current.cost_state, reservation_id=r.id)
./omni_prod/intake/worker_route.py-114-
./omni_prod/intake/worker_route.py-115-
./omni_prod/intake/worker_route.py:116:def rq_enqueue(redis_url: str):
./omni_prod/intake/worker_route.py:117:    from ..queueing import enqueue_build
./omni_prod/intake/worker_route.py-118-
./omni_prod/intake/worker_route.py:119:    def enqueue(reservation_id: str):
./omni_prod/intake/worker_route.py:120:        enqueue_build(redis_url, JOB, reservation_id, job_id=reservation_id, queue_name=INTAKE_QUEUE, timeout=120)
./omni_prod/intake/worker_route.py:121:    return enqueue
--
./omni_prod/investor_app.py-56-from .customer_views import strip_internal_economics, unpriced_capabilities
./omni_prod/investor_app.py-57-from .creator_accounts import PostgresAccountService
./omni_prod/investor_app.py-58-from .subscription_store import PostgresSubscriptionService
./omni_prod/investor_app.py-59-from .db import DatabasePool
./omni_prod/investor_app.py:60:from .queueing import PREVIEW_QUEUE, enqueue_build, preview_host_queue
--
./omni_prod/investor_app.py-307-
./omni_prod/investor_app.py-308-    Existing contract IDs are authoritative: the mutable request prompt is not
./omni_prod/investor_app.py-309-    allowed to replace their intent. New intent creates a new append-only
./omni_prod/investor_app.py-310-    revision. A non-READY contract is durable evidence but cannot reserve or
./omni_prod/investor_app.py:311:    enqueue paid work.
--
./omni_prod/investor_app.py-1709-#
./omni_prod/investor_app.py-1710-# The worker (omni_prod/worker_tasks.py::execute_live_build_job) runs the
./omni_prod/investor_app.py-1711-# same verification + quality + security + rights gates as v28_live_build and
./omni_prod/investor_app.py-1712-# is the only build path in async mode (see _async_build_mode()). If Redis is
./omni_prod/investor_app.py:1713:# unavailable at enqueue time the build is still durably accepted; the
--
./omni_prod/investor_app.py-1917-def _supervisor(key: str):
./omni_prod/investor_app.py-1918-    """Paid intake runs only through durable reservations on the worker (Issue #12):
./omni_prod/investor_app.py-1919-    no model gateway is built on the API host."""
./omni_prod/investor_app.py-1920-    from .conversation.supervisor import ConversationSupervisor
./omni_prod/investor_app.py:1921:    reservations = enqueue = None
./omni_prod/investor_app.py-1922-    redis_url = os.getenv('OMNI_REDIS_URL', '').strip()
./omni_prod/investor_app.py-1923-    if os.getenv('OMNI_INTAKE_MODEL') == '1' and os.getenv('OMNI_INTAKE_VIA_WORKER') == '1' \
./omni_prod/investor_app.py-1924-            and _v28_pool is not None and redis_url:
./omni_prod/investor_app.py-1925-        from .intake.budget import ReservationService
./omni_prod/investor_app.py:1926:        from .intake.worker_route import rq_enqueue
./omni_prod/investor_app.py:1927:        reservations, enqueue = ReservationService(_v28_pool), rq_enqueue(redis_url)
./omni_prod/investor_app.py-1928-    return ConversationSupervisor(briefs=_brief_repo(), store=_conversation_store(), gateway=None,
./omni_prod/investor_app.py-1929-                                  credits=_M5_BUILD_CREDITS, context=_project_context(key),
./omni_prod/investor_app.py-1930-                                  budget_usd=Decimal(os.getenv('OMNI_EXTERNAL_BUDGET_USD', '0.50') or '0.50'),
./omni_prod/investor_app.py:1931:                                  reservations=reservations, enqueue=enqueue)
--
./omni_prod/investor_app.py-2273-            raise HTTPException(402, detail={'error': 'plan_cannot_authorize_build',
./omni_prod/investor_app.py-2274-                                             'message': 'This build is not available on your current plan.'}) from exc
./omni_prod/investor_app.py-2275-        # M5 remediation: one durable reservation of the FULL conservative total
./omni_prod/investor_app.py-2276-        # (LLM + required capabilities + generated-app infra + platform infra +
./omni_prod/investor_app.py:2277:        # retry) before anything is enqueued. No later separate reservation.
--
./omni_prod/investor_app.py-2402-            })
./omni_prod/investor_app.py-2403-
./omni_prod/investor_app.py-2404-        redis_url = os.getenv('OMNI_REDIS_URL', 'redis://127.0.0.1:6379/0')
./omni_prod/investor_app.py-2405-        try:
./omni_prod/investor_app.py:2406:            enqueue_build(redis_url, "omni_prod.worker_tasks.execute_live_build_job", build_id, job_id=build_id)
./omni_prod/investor_app.py:2407:            jobs.mark_outbox_enqueued(build_id)
./omni_prod/investor_app.py:2408:            dispatch = "enqueued"
./omni_prod/investor_app.py-2409-        except Exception:
./omni_prod/investor_app.py-2410-            # The build, its reservation and its outbox row are already
./omni_prod/investor_app.py-2411-            # committed. Failing the request here would tell the client the
./omni_prod/investor_app.py-2412-            # build was rejected when it was in fact accepted; the outbox
./omni_prod/investor_app.py:2413:            # relay re-dispatches rows with enqueued_at IS NULL.
--
./omni_prod/investor_app.py-2511-#
./omni_prod/investor_app.py-2512-# M3 Revision 2: real running preview (separate lifecycle from the build sandbox).
./omni_prod/investor_app.py-2513-#
./omni_prod/investor_app.py-2514-# The API never talks to a Docker daemon: it validates, records durable state
./omni_prod/investor_app.py:2515:# and enqueues. Containers are started, probed and removed by workers, which
--
./omni_prod/investor_app.py-2576-    preview_repo.create(preview_id, key, version_id, ttl_seconds=_PREVIEW_TTL_SECONDS)
./omni_prod/investor_app.py-2577-
./omni_prod/investor_app.py-2578-    redis_url = os.getenv('OMNI_REDIS_URL', 'redis://127.0.0.1:6379/0')
./omni_prod/investor_app.py-2579-    try:
./omni_prod/investor_app.py:2580:        enqueue_build(redis_url, "omni_prod.worker_tasks.execute_preview_launch",
--
./omni_prod/investor_app.py-2660-        try:
./omni_prod/investor_app.py-2661-            # Container + workdir live on the launching worker's host; with
./omni_prod/investor_app.py-2662-            # no host recorded yet the launch task itself tears down (it sees
./omni_prod/investor_app.py-2663-            # STOPPED on its next conditional write).
./omni_prod/investor_app.py:2664:            enqueue_build(redis_url, "omni_prod.worker_tasks.stop_preview_task", preview_id,
./omni_prod/investor_app.py-2665-                          job_id=f'stop-{preview_id}-{uuid.uuid4().hex[:8]}',
./omni_prod/investor_app.py-2666-                          **({'queue_name': preview_host_queue(host)} if host else {}))
./omni_prod/investor_app.py:2667:            cleanup = 'enqueued'
./omni_prod/investor_app.py-2668-        except Exception as exc:
./omni_prod/investor_app.py-2669-            # STOPPED is durable; cleanup is retried by repeating DELETE.
./omni_prod/investor_app.py-2670-            raise HTTPException(503, 'preview marked STOPPED but cleanup could not be dispatched; retry DELETE') from exc
./omni_prod/investor_app.py-2671-
./omni_prod/investor_app.py:2672:    return JSONResponse(status_code=202 if cleanup == 'enqueued' else 200,
--
./omni_prod/investor_app.py-2681-# "never load latest spec when modifying an older version" -- checked here,
./omni_prod/investor_app.py-2682-# not guessed), reserves credits (M4G) and durably records the request
./omni_prod/investor_app.py-2683-# (create() + create_outbox() in the same transaction as the reservation,
./omni_prod/investor_app.py-2684-# the same transactional-outbox shape job_repository.py established for
./omni_prod/investor_app.py:2685:# builds) before enqueueing. worker_tasks.execute_modification_job does the
--
./omni_prod/investor_app.py-2756-                mods.create_outbox(cur, modification_id=modification_id)
./omni_prod/investor_app.py-2757-
./omni_prod/investor_app.py-2758-    redis_url = os.getenv('OMNI_REDIS_URL', 'redis://127.0.0.1:6379/0')
./omni_prod/investor_app.py-2759-    try:
./omni_prod/investor_app.py:2760:        enqueue_build(redis_url, "omni_prod.worker_tasks.execute_modification_job", modification_id, job_id=modification_id)
./omni_prod/investor_app.py:2761:        mods.mark_outbox_enqueued(modification_id)
./omni_prod/investor_app.py:2762:        dispatch = "enqueued"
./omni_prod/investor_app.py-2763-    except Exception:
./omni_prod/investor_app.py-2764-        # Durably accepted already (request + reservation + outbox row are
./omni_prod/investor_app.py-2765-        # committed); the outbox relay re-dispatches rows with
./omni_prod/investor_app.py:2766:        # enqueued_at IS NULL, same as the build path above.
--
./omni_prod/isolation_check.py-93-            rows[res] = {'verdict': 'ISOLATED', labels[0]: ia[res], labels[1]: ib[res]}
./omni_prod/isolation_check.py-94-    # queues live in Redis: sharing Redis means sharing queues unless the queue names differ per environment
./omni_prod/isolation_check.py-95-    rows['queues'] = {'verdict': rows['redis']['verdict'],
./omni_prod/isolation_check.py-96-                      'why': ('queues are RQ keys inside Redis: same Redis = same omni-builds / omni-previews / omni-intake queues, so a '
./omni_prod/isolation_check.py:97:                              'Preview deployment can enqueue work a Production worker executes' if rows['redis']['verdict'] == 'SHARED'
--
./omni_prod/job_repository.py-284-
./omni_prod/job_repository.py-285-    def create_outbox(self, cur, *, build_id: str) -> None:
./omni_prod/job_repository.py-286-        cur.execute("INSERT INTO build_outbox(build_id) VALUES (%s)", (build_id,))
./omni_prod/job_repository.py-287-
./omni_prod/job_repository.py:288:    def mark_outbox_enqueued(self, build_id: str) -> None:
./omni_prod/job_repository.py-289-        with self.pool.connection() as conn:
./omni_prod/job_repository.py-290-            with conn.transaction():
./omni_prod/job_repository.py-291-                with conn.cursor() as cur:
./omni_prod/job_repository.py:292:                    cur.execute("UPDATE build_outbox SET enqueued_at = now() WHERE build_id = %s", (build_id,))
./omni_prod/job_repository.py-293-
./omni_prod/job_repository.py:294:    def dispatch_pending_outbox(self, enqueue, *, older_than_seconds: int = 30, limit: int = 100) -> list[str]:
./omni_prod/job_repository.py-295-        """Transactional-outbox relay (M1 blocker resolution).
./omni_prod/job_repository.py-296-
./omni_prod/job_repository.py-297-        The API commits reservation + request + job + outbox row atomically,
./omni_prod/job_repository.py:298:        *then* enqueues to Redis. If Redis is down at that moment the build is
--
./omni_prod/job_repository.py-300-        nothing ever retried it: the credits stayed RESERVED and the job sat
./omni_prod/job_repository.py-301-        at QUEUED forever. This re-dispatches such rows, one per transaction,
./omni_prod/job_repository.py-302-        with FOR UPDATE SKIP LOCKED so concurrent relays never double-claim a
./omni_prod/job_repository.py-303-        row. `older_than_seconds` leaves rows the API is still in the middle
./omni_prod/job_repository.py:304:        of enqueueing alone. Duplicate delivery (enqueue succeeded, commit
--
./omni_prod/job_repository.py-311-                    with conn.cursor() as cur:
./omni_prod/job_repository.py-312-                        cur.execute(
./omni_prod/job_repository.py-313-                            """
./omni_prod/job_repository.py-314-                            SELECT build_id FROM build_outbox
./omni_prod/job_repository.py:315:                            WHERE enqueued_at IS NULL
--
./omni_prod/job_repository.py-323-                        row = cur.fetchone()
./omni_prod/job_repository.py-324-                        if not row:
./omni_prod/job_repository.py-325-                            return dispatched
./omni_prod/job_repository.py-326-                        build_id = row[0]
./omni_prod/job_repository.py:327:                        enqueue(build_id)  # raises -> transaction rolls back, row stays pending
./omni_prod/job_repository.py:328:                        cur.execute("UPDATE build_outbox SET enqueued_at = now() WHERE build_id = %s", (build_id,))
--
./omni_prod/maintenance.py-97-_REDISPATCHED: dict[str, int] = {}
./omni_prod/maintenance.py-98-MAX_REDISPATCH = 3
./omni_prod/maintenance.py-99-
./omni_prod/maintenance.py-100-
./omni_prod/maintenance.py:101:def redispatch_lost(pool, *, queued_ids, enqueue, minutes: int = LOST_QUEUED_MINUTES,
./omni_prod/maintenance.py-102-                    attempts: dict | None = None) -> list[str]:
./omni_prod/maintenance.py:103:    """Re-enqueue QUEUED work whose id is no longer waiting in the queue.
./omni_prod/maintenance.py-104-    `queued_ids()` returns the ids currently in the build queue (and being
./omni_prod/maintenance.py:105:    worked on); `enqueue(func, id)` dispatches with job_id=id. Each id is sent
--
./omni_prod/maintenance.py-109-    sent = []
./omni_prod/maintenance.py-110-    for func, item in queued_too_long(pool, minutes):
./omni_prod/maintenance.py-111-        if item in waiting or attempts.get(item, 0) >= MAX_REDISPATCH:
./omni_prod/maintenance.py-112-            continue  # still in line behind another job, or given up on
./omni_prod/maintenance.py:113:        enqueue(func, item)
--
./omni_prod/maintenance.py-138-                     "AND heartbeat_at < now() - make_interval(mins => %s)"),
./omni_prod/maintenance.py-139-}
./omni_prod/maintenance.py-140-
./omni_prod/maintenance.py-141-
./omni_prod/maintenance.py:142:def recover_lost_running(pool, *, subscriptions, enqueue, busy_ids=lambda: (), minutes: int = LOST_RUNNING_MINUTES,
--
./omni_prod/maintenance.py-187-            if not done:
./omni_prod/maintenance.py-188-                continue
./omni_prod/maintenance.py-189-            out[bucket].append(item)
./omni_prod/maintenance.py-190-            if bucket == 'recovered':
./omni_prod/maintenance.py:191:                enqueue(BUILD_JOB if kind == 'build' else MODIFICATION_JOB, item)
--
./omni_prod/maintenance.py-200-    return conn.execute(_END['modification'], (status, code, message, item)).rowcount == 1
./omni_prod/maintenance.py-201-
./omni_prod/maintenance.py-202-
./omni_prod/maintenance.py-203-def run_once(*, pool, preview_repo, jobs, subscriptions, stop_preview, runtime_host: str,
./omni_prod/maintenance.py:204:             queued_ids=None, enqueue=None, busy_ids=None) -> dict:
--
./omni_prod/maintenance.py-222-            except Exception as exc:
./omni_prod/maintenance.py-223-                out['errors'].append(f'reap {bid}: {type(exc).__name__}: {exc}')
./omni_prod/maintenance.py-224-    except Exception as exc:
./omni_prod/maintenance.py-225-        out['errors'].append(f'stale_builds: {type(exc).__name__}: {exc}')
./omni_prod/maintenance.py:226:    if queued_ids is not None and enqueue is not None:
./omni_prod/maintenance.py-227-        try:
./omni_prod/maintenance.py:228:            out['redispatched'] = redispatch_lost(pool, queued_ids=queued_ids, enqueue=enqueue)
./omni_prod/maintenance.py-229-        except Exception as exc:
./omni_prod/maintenance.py-230-            out['errors'].append(f'redispatch: {type(exc).__name__}: {exc}')
./omni_prod/maintenance.py-231-        try:
./omni_prod/maintenance.py:232:            rec = recover_lost_running(pool, subscriptions=subscriptions, enqueue=enqueue,
--
./omni_prod/maintenance.py-239-
./omni_prod/maintenance.py-240-def recover_now(minutes: int) -> dict:
./omni_prod/maintenance.py-241-    """One recovery pass with a custom staleness limit (crash-recovery test)."""
./omni_prod/maintenance.py-242-    from .investor_app import _v28, _v28_pool
./omni_prod/maintenance.py:243:    from .queueing import BUILD_QUEUE, enqueue_build, queue, redis_connection
--
./omni_prod/maintenance.py-247-    def busy():
./omni_prod/maintenance.py-248-        return [w.get_current_job_id() for w in Worker.all(connection=redis_connection(redis_url))
./omni_prod/maintenance.py-249-                if w.get_current_job_id()]
./omni_prod/maintenance.py-250-    return recover_lost_running(_v28_pool, subscriptions=_v28.subscriptions,
./omni_prod/maintenance.py:251:                                enqueue=lambda f, i: enqueue_build(redis_url, f, i, job_id=i),
--
./omni_prod/maintenance.py-259-    from .worker_tasks import preview_runtime_host, stop_preview_task
./omni_prod/maintenance.py-260-    if _v28_pool is None:
./omni_prod/maintenance.py-261-        raise RuntimeError('maintenance requires OMNI_CREATOR_PERSISTENCE=postgres')
./omni_prod/maintenance.py-262-    host = preview_runtime_host()
./omni_prod/maintenance.py:263:    from .queueing import BUILD_QUEUE, enqueue_build, queue
--
./omni_prod/maintenance.py-267-        from rq.registry import StartedJobRegistry
./omni_prod/maintenance.py-268-        q = queue(redis_url, BUILD_QUEUE)
./omni_prod/maintenance.py-269-        return list(q.job_ids) + list(StartedJobRegistry(queue=q).get_job_ids())
./omni_prod/maintenance.py-270-
./omni_prod/maintenance.py:271:    def enqueue(func, item):
./omni_prod/maintenance.py:272:        enqueue_build(redis_url, func, item, job_id=item)
--
./omni_prod/maintenance.py-286-
./omni_prod/maintenance.py-287-    deps = dict(pool=_v28_pool, preview_repo=PostgresPreviewRepository(_v28_pool),
./omni_prod/maintenance.py-288-                jobs=PostgresBuildRepository(_v28_pool), subscriptions=_v28.subscriptions,
./omni_prod/maintenance.py-289-                stop_preview=stop_preview_task, runtime_host=host,
./omni_prod/maintenance.py:290:                queued_ids=queued_ids if redis_url else None, enqueue=enqueue if redis_url else None,
--
./omni_prod/modification_engine.py-7-from .modifier_engine import repo_summary, run_free_repair
./omni_prod/modification_engine.py-8-from .modification_diff import ModificationDiff, diff_modification
./omni_prod/modification_engine.py-9-
./omni_prod/modification_engine.py-10-# M4C/D/E: this module is the pure, testable core of M4 -- it never touches
./omni_prod/modification_engine.py:11:# durable storage, never enqueues anything, and never mutates the accepted
--
./omni_prod/modification_repository.py-88-
./omni_prod/modification_repository.py-89-class PostgresModificationRepository:
./omni_prod/modification_repository.py-90-    """M4A: durable `ModificationRequest` lifecycle, plus M4D's accept/
./omni_prod/modification_repository.py-91-    reject/rollback. Structure mirrors job_repository.PostgresBuildRepository
./omni_prod/modification_repository.py:92:    exactly -- create()/create_outbox()/mark_outbox_enqueued()/
--
./omni_prod/modification_repository.py-121-
./omni_prod/modification_repository.py-122-    def create_outbox(self, cur, *, modification_id: str) -> None:
./omni_prod/modification_repository.py-123-        cur.execute("INSERT INTO modification_outbox(modification_id) VALUES (%s)", (modification_id,))
./omni_prod/modification_repository.py-124-
./omni_prod/modification_repository.py:125:    def mark_outbox_enqueued(self, modification_id: str) -> None:
./omni_prod/modification_repository.py-126-        with self.pool.connection() as conn:
./omni_prod/modification_repository.py-127-            with conn.transaction():
./omni_prod/modification_repository.py-128-                with conn.cursor() as cur:
./omni_prod/modification_repository.py-129-                    cur.execute(
./omni_prod/modification_repository.py:130:                        "UPDATE modification_outbox SET enqueued_at = now() WHERE modification_id = %s",
./omni_prod/modification_repository.py-131-                        (modification_id,),
./omni_prod/modification_repository.py-132-                    )
./omni_prod/modification_repository.py-133-
./omni_prod/modification_repository.py:134:    def dispatch_pending_outbox(self, enqueue, *, older_than_seconds: int = 30, limit: int = 100) -> list[str]:
--
./omni_prod/modification_repository.py-143-                    with conn.cursor() as cur:
./omni_prod/modification_repository.py-144-                        cur.execute(
./omni_prod/modification_repository.py-145-                            """
./omni_prod/modification_repository.py-146-                            SELECT modification_id FROM modification_outbox
./omni_prod/modification_repository.py:147:                            WHERE enqueued_at IS NULL
--
./omni_prod/modification_repository.py-155-                        row = cur.fetchone()
./omni_prod/modification_repository.py-156-                        if not row:
./omni_prod/modification_repository.py-157-                            return dispatched
./omni_prod/modification_repository.py-158-                        modification_id = row[0]
./omni_prod/modification_repository.py:159:                        enqueue(modification_id)  # raises -> transaction rolls back, row stays pending
./omni_prod/modification_repository.py-160-                        cur.execute(
./omni_prod/modification_repository.py:161:                            "UPDATE modification_outbox SET enqueued_at = now() WHERE modification_id = %s",
--
./omni_prod/outbox.py-39-        created_at=datetime.now(timezone.utc).isoformat(),
./omni_prod/outbox.py-40-    )
./omni_prod/outbox.py-41-
./omni_prod/outbox.py-42-class PostgresOutboxRepository:
./omni_prod/outbox.py:43:    def enqueue(self, cur, event: OutboxEvent) -> None:
--
./omni_prod/preview_repository.py-95-        for this project. Idempotent: an already-terminal preview is returned
./omni_prod/preview_repository.py-96-        unchanged (`changed=False`). `needs_cleanup` is True whenever the row
./omni_prod/preview_repository.py-97-        is STOPPED but the stop task has not yet confirmed cleanup, so a
./omni_prod/preview_repository.py-98-        retried DELETE re-dispatches a cleanup that previously failed to
./omni_prod/preview_repository.py:99:        enqueue."""
--
./omni_prod/queueing.py-44-        connection=redis_connection(redis_url, **redis_kwargs),
./omni_prod/queueing.py-45-        default_timeout=900,
./omni_prod/queueing.py-46-    )
./omni_prod/queueing.py-47-
./omni_prod/queueing.py:48:def enqueue_build(
--
./omni_prod/queueing.py-57-    # M3: widened from a single `payload` positional to `*args` so this one
./omni_prod/queueing.py-58-    # queue/helper can dispatch to jobs that take more than one plain
./omni_prod/queueing.py-59-    # argument (execute_preview_launch(preview_id, project_id, version_id)),
./omni_prod/queueing.py-60-    # not just the single-value payload M1's execute_live_build_job(build_id)
./omni_prod/queueing.py:61:    # needed. Backward compatible: enqueue_build(url, path, build_id,
./omni_prod/queueing.py:62:    # job_id=...) still enqueues exactly one arg, same as before.
./omni_prod/queueing.py-63-    # M3 Rev2: optional queue_name (default unchanged) for host-scoped
./omni_prod/queueing.py-64-    # preview cleanup -- see preview_host_queue().
./omni_prod/queueing.py-65-    q = queue(redis_url, queue_name, **redis_kwargs)
./omni_prod/queueing.py:66:    return q.enqueue(
--
./omni_prod/worker.py-2-
./omni_prod/worker.py-3-Three choices here come from live evidence on the staging worker host
./omni_prod/worker.py-4-(STATUS.md, 2026-10-07):
./omni_prod/worker.py-5-
./omni_prod/worker.py:6:* No RQ scheduler. Nothing in 148AI uses enqueue_at / enqueue_in or interval
--
./omni_prod/worker.py-13-  can hold the queue and keeps idle traffic predictable: about 4 commands per
./omni_prod/worker.py-14-  wait cycle (heartbeat + BLMOVE), ~86K per month at the default 120 s.
./omni_prod/worker.py-15-
./omni_prod/worker.py-16-* Stale-consumer absorption at start-up. After a deploy replaced the worker
./omni_prod/worker.py:17:  container, a probe job enqueued seconds later was moved out of the queue
--
./tests/financial_fault_harness.py-211-            recovery = maintenance.run_once(pool=pool, preview_repo=PostgresPreviewRepository(pool),
./tests/financial_fault_harness.py-212-                                            jobs=jobs, subscriptions=subs,
./tests/financial_fault_harness.py-213-                                            stop_preview=lambda pid: (_ for _ in ()).throw(AssertionError('unexpected preview')),
./tests/financial_fault_harness.py-214-                                            runtime_host='fault-test-only', queued_ids=lambda: (),
./tests/financial_fault_harness.py:215:                                            enqueue=lambda function, bid: deliveries.append((function, bid)),
--
./tests/integration/test_financial_fault_experiment.py-63-                            return type('Candidates', (), {'fetchall': lambda self: rows})()
./tests/integration/test_financial_fault_experiment.py-64-                        return cursor
./tests/integration/test_financial_fault_experiment.py-65-                yield Proxy()
./tests/integration/test_financial_fault_experiment.py-66-
./tests/integration/test_financial_fault_experiment.py:67:    subs, enqueue = MagicMock(), MagicMock()
./tests/integration/test_financial_fault_experiment.py-68-    try:
./tests/integration/test_financial_fault_experiment.py:69:        outcome = maintenance.recover_lost_running(RacingPool(), subscriptions=subs, enqueue=enqueue)
--
./tests/integration/test_financial_fault_experiment.py-72-        assert status == 'running'
./tests/integration/test_financial_fault_experiment.py-73-        assert bid not in sum(outcome.values(), [])
./tests/integration/test_financial_fault_experiment.py-74-        exposure.assert_not_called()
./tests/integration/test_financial_fault_experiment.py-75-        subs.release.assert_not_called()
./tests/integration/test_financial_fault_experiment.py:76:        enqueue.assert_not_called()
--
./tests/m4d2_rq_job_target.py-9-fake pass.
./tests/m4d2_rq_job_target.py-10-
./tests/m4d2_rq_job_target.py-11-Each function opens its OWN short-lived psycopg connection rather than
./tests/m4d2_rq_job_target.py-12-reusing any pool object from the enqueuing process, because a real queued
./tests/m4d2_rq_job_target.py:13:job's function only ever receives the plain arguments it was enqueued
./tests/m4d2_rq_job_target.py:14:with (see omni_prod.queueing.enqueue_build) -- exactly like the real
--
./tests/test_crash_recovery_and_change_parity.py-45-            return c.execute("SELECT status, error_code, recovery_attempts FROM build_jobs WHERE id=%s", (bid,)).fetchone()
./tests/test_crash_recovery_and_change_parity.py-46-
./tests/test_crash_recovery_and_change_parity.py-47-    def run_once(self, busy=()):
./tests/test_crash_recovery_and_change_parity.py-48-        return maintenance.recover_lost_running(self.pool, subscriptions=self.subs,
./tests/test_crash_recovery_and_change_parity.py:49:                                                enqueue=lambda f, i: self.sent.append((f, i)),
--
./tests/test_crash_recovery_and_change_parity.py-123-            with c.transaction():
./tests/test_crash_recovery_and_change_parity.py-124-                c.execute("UPDATE modification_requests SET heartbeat_at = now() - interval '20 minutes' WHERE id=%s", (m,))
./tests/test_crash_recovery_and_change_parity.py-125-        sent = []
./tests/test_crash_recovery_and_change_parity.py-126-        out = maintenance.recover_lost_running(self.pool, subscriptions=MagicMock(),
./tests/test_crash_recovery_and_change_parity.py:127:                                               enqueue=lambda f, i: sent.append((f, i)), minutes=15)
--
./tests/test_failure_injection.py-67-    def test_queue_interruption_is_redispatched(self):
./tests/test_failure_injection.py-68-        from omni_prod import maintenance
./tests/test_failure_injection.py-69-        sent = []
./tests/test_failure_injection.py-70-        with patch.object(maintenance, 'queued_too_long', return_value=[(maintenance.BUILD_JOB, 'bld_lost')]):
./tests/test_failure_injection.py:71:            maintenance.redispatch_lost(None, queued_ids=lambda: [], enqueue=lambda f, i: sent.append(i), attempts={})
--
./tests/test_intake_assistant_he.py-97-    def turn(self, env, msg, project='p'):
./tests/test_intake_assistant_he.py-98-        with mock.patch.dict(os.environ, {**CLEAR, **env}):
./tests/test_intake_assistant_he.py-99-            self.sup.turn(project_id=project, account_id='a', message=msg)
./tests/test_intake_assistant_he.py-100-
./tests/test_intake_assistant_he.py:101:    def test_switch_off_means_no_enqueue_and_no_db_reads(self):
--
./tests/test_intake_budget_pg.py-463-        def flaky(rid):                         # Redis down on the first pass
./tests/test_intake_budget_pg.py-464-            raise ConnectionError('redis down')
./tests/test_intake_budget_pg.py-465-        with self.assertRaises(ConnectionError):
./tests/test_intake_budget_pg.py-466-            self.svc.relay_once(flaky)
./tests/test_intake_budget_pg.py:467:        self.assertIsNone(self.sql('SELECT enqueued_at FROM intake_outbox WHERE reservation_id = %s', (r.id,))[0][0])
./tests/test_intake_budget_pg.py-468-        self.assertIn(r.id, self.svc.relay_once(delivered.append))
./tests/test_intake_budget_pg.py-469-        self.assertEqual(self.svc.relay_once(delivered.append), [])          # delivered once
./tests/test_intake_budget_pg.py:470:        # crash after the enqueue but before the commit: delivered again -> claim dedups
./tests/test_intake_budget_pg.py:471:        self.sql('UPDATE intake_outbox SET enqueued_at = NULL WHERE reservation_id = %s', (r.id,))
--
./tests/test_intake_budget_pg.py-499-        os.environ['I12_TEST_DB_URL'], os.environ['I12_TEST_COUNTER'] = self.url, counter
./tests/test_intake_budget_pg.py-500-        r = self.svc.reserve(idempotency_key=uuid.uuid4().hex, account_id='acct', project_id='rq', quote_=real_quote(),
./tests/test_intake_budget_pg.py-501-                             caps=B.Caps(Decimal('1'), Decimal('10')), payload=PAYLOAD)
./tests/test_intake_budget_pg.py-502-        for _ in range(3):   # API fast path + two relay re-deliveries, same stable job id
./tests/test_intake_budget_pg.py:503:            q.enqueue('tests.test_intake_budget_pg.rq_job', r.id, job_id=r.id)
./tests/test_intake_budget_pg.py:504:        q.enqueue('tests.test_intake_budget_pg.rq_job', r.id, job_id=f'{r.id}-x')   # even a different job id
--
./tests/test_intake_budget_pg.py-522-        from omni_prod.conversation.store import MemoryConversationStore
./tests/test_intake_budget_pg.py-523-        from omni_prod.conversation.supervisor import ConversationSupervisor
./tests/test_intake_budget_pg.py-524-        from tests.test_conversation_os import MemoryBriefs
./tests/test_intake_budget_pg.py-525-
./tests/test_intake_budget_pg.py:526:        def enqueue(rid):   # stands in for RQ: deliver to a worker thread
./tests/test_intake_budget_pg.py-527-            threading.Thread(target=RW.execute_reservation, args=(self.pool, rid),
./tests/test_intake_budget_pg.py-528-                             kwargs={'gateway_factory': gateway_with(transport)}, daemon=True).start()
./tests/test_intake_budget_pg.py-529-        return ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(),
./tests/test_intake_budget_pg.py:530:                                      reservations=self.svc, enqueue=enqueue)
--
./tests/test_intake_worker_route.py-1-"""Worker-routed intake (Issue #12): no unreserved path exists; the API-side
./tests/test_intake_worker_route.py:2:interpreter reserves before enqueueing and degrades to deterministic on every
--
./tests/test_intake_worker_route.py-27-
./tests/test_intake_worker_route.py-28-class FakeService:
./tests/test_intake_worker_route.py-29-    def __init__(self, *, reserve_exc=None, final=None, never_settles=False):
./tests/test_intake_worker_route.py-30-        self.reserve_exc, self.final, self.never = reserve_exc, final, never_settles
./tests/test_intake_worker_route.py:31:        self.released, self.enqueued, self.reserved = [], [], []
--
./tests/test_intake_worker_route.py-36-        self.reserved.append(kw)
./tests/test_intake_worker_route.py-37-        return B.Reservation('irs_1', kw['idempotency_key'], kw['account_id'], kw['project_id'], kw['lane'], None,
./tests/test_intake_worker_route.py-38-                             kw['quote_'].amount_usd, B.RESERVED)
./tests/test_intake_worker_route.py-39-
./tests/test_intake_worker_route.py:40:    def mark_enqueued(self, rid):
./tests/test_intake_worker_route.py:41:        self.enqueued.append(rid)
--
./tests/test_intake_worker_route.py-49-            return B.Reservation(rid, 'k', 'acct', 'p', 'production', None, Decimal('0.004'), B.EXECUTING)
./tests/test_intake_worker_route.py-50-        return self.final
./tests/test_intake_worker_route.py-51-
./tests/test_intake_worker_route.py-52-
./tests/test_intake_worker_route.py:53:def interp(service, enqueue=lambda rid: None, wait=1.0):
./tests/test_intake_worker_route.py-54-    ticks = iter([0.0] + [0.1 * i for i in range(1, 200)])
./tests/test_intake_worker_route.py:55:    return W.ReservedWorkerInterpreter(service, enqueue, account_id='acct', project_id='p', request_key='rk',
--
./tests/test_intake_worker_route.py-69-
./tests/test_intake_worker_route.py-70-    def test_settled_result_is_revalidated_merged_and_costed(self):
./tests/test_intake_worker_route.py-71-        svc = FakeService(final=settled(B.SETTLED, B.ESTIMATED, Decimal('0.0012'), {'ok': True, 'raw': self.RAW}))
./tests/test_intake_worker_route.py-72-        it = interp(svc).interpret(MSG)
./tests/test_intake_worker_route.py:73:        self.assertEqual(svc.enqueued, ['irs_1'])
--
./tests/test_intake_worker_route.py-85-    def test_timeout_leaves_cost_pending_on_the_reservation(self):
./tests/test_intake_worker_route.py-86-        it = interp(FakeService(never_settles=True), wait=0.5).interpret(MSG)
./tests/test_intake_worker_route.py-87-        self.assertEqual((it.cost_usd, it.cost_state, it.reservation_id), (None, 'PENDING', 'irs_1'))
./tests/test_intake_worker_route.py-88-
./tests/test_intake_worker_route.py:89:    def test_enqueue_failure_releases_immediately(self):
./tests/test_intake_worker_route.py-90-        def down(rid):
./tests/test_intake_worker_route.py-91-            raise ConnectionError('redis down')
./tests/test_intake_worker_route.py-92-        svc = FakeService()
./tests/test_intake_worker_route.py:93:        it = interp(svc, enqueue=down).interpret(MSG)
--
./tests/test_janitor_redispatch.py-15-        with patch.object(maintenance, 'queued_too_long', return_value=[
./tests/test_janitor_redispatch.py-16-                (maintenance.BUILD_JOB, 'bld_lost'), (maintenance.BUILD_JOB, 'bld_waiting'),
./tests/test_janitor_redispatch.py-17-                (maintenance.MODIFICATION_JOB, 'mod_lost')]):
./tests/test_janitor_redispatch.py-18-            out = maintenance.redispatch_lost(None, queued_ids=lambda: ['bld_waiting'],
./tests/test_janitor_redispatch.py:19:                                              enqueue=lambda f, i: sent.append((f, i)), attempts={})
--
./tests/test_janitor_redispatch.py-23-    def test_an_item_is_sent_at_most_three_times(self):
./tests/test_janitor_redispatch.py-24-        sent, attempts = [], {}
./tests/test_janitor_redispatch.py-25-        with patch.object(maintenance, 'queued_too_long', return_value=[(maintenance.BUILD_JOB, 'bld_x')]):
./tests/test_janitor_redispatch.py-26-            for _ in range(5):
./tests/test_janitor_redispatch.py:27:                maintenance.redispatch_lost(None, queued_ids=lambda: [], enqueue=lambda f, i: sent.append(i),
--
./tests/test_janitor_redispatch.py-33-            def connection(self):
./tests/test_janitor_redispatch.py-34-                raise RuntimeError('db down')
./tests/test_janitor_redispatch.py-35-        out = maintenance.run_once(pool=P(), preview_repo=type('R', (), {'mark_expired': lambda self: 0})(),
./tests/test_janitor_redispatch.py-36-                                   jobs=None, subscriptions=None, stop_preview=None, runtime_host='h',
./tests/test_janitor_redispatch.py:37:                                   queued_ids=lambda: [], enqueue=lambda f, i: None)
--
./tests/test_m3_preview_logic.py-47-    ensure_durable_workspace, external_preview_url, is_managed_workdir, parse_docker_port_output,
./tests/test_m3_preview_logic.py-48-    parse_preview_contract, wait_until_healthy, _materialize_repository,
./tests/test_m3_preview_logic.py-49-)
./tests/test_m3_preview_logic.py-50-from omni_prod.project_manifest import ProjectManifest
./tests/test_m3_preview_logic.py:51:from omni_prod.queueing import BUILD_QUEUE, enqueue_build, preview_host_queue
--
./tests/test_m3_preview_logic.py-676-        self.assertEqual(preview_host_queue('ip 10.0.0.5/x'), 'omni-preview-host-ip-10.0.0.5-x')
./tests/test_m3_preview_logic.py-677-        with self.assertRaises(ValueError):
./tests/test_m3_preview_logic.py-678-            preview_host_queue('  ')
./tests/test_m3_preview_logic.py-679-
./tests/test_m3_preview_logic.py:680:    def test_enqueue_build_routes_to_named_queue_and_passes_all_args(self):
./tests/test_m3_preview_logic.py-681-        with patch('omni_prod.queueing.queue') as q:
./tests/test_m3_preview_logic.py:682:            enqueue_build('redis://x', 'omni_prod.worker_tasks.stop_preview_task', 'prv_1',
./tests/test_m3_preview_logic.py-683-                          job_id='j', queue_name='omni-preview-host-a')
./tests/test_m3_preview_logic.py-684-            q.assert_called_once_with('redis://x', 'omni-preview-host-a')
./tests/test_m3_preview_logic.py:685:            args, kwargs = q.return_value.enqueue.call_args
./tests/test_m3_preview_logic.py-686-            self.assertEqual(args, ('omni_prod.worker_tasks.stop_preview_task', 'prv_1'))
./tests/test_m3_preview_logic.py-687-            self.assertEqual(kwargs['job_id'], 'j')
./tests/test_m3_preview_logic.py-688-
./tests/test_m3_preview_logic.py:689:    def test_enqueue_build_default_queue_unchanged(self):
./tests/test_m3_preview_logic.py-690-        with patch('omni_prod.queueing.queue') as q:
./tests/test_m3_preview_logic.py:691:            enqueue_build('redis://x', 'f', 'b1', job_id='b1')
--
./tests/test_m3_preview_logic.py-1057-        out = PostgresBuildRepository(pool).dispatch_pending_outbox(sent.append, older_than_seconds=30)
./tests/test_m3_preview_logic.py-1058-        self.assertEqual((out, sent), (['bld_1', 'bld_2'], ['bld_1', 'bld_2']))
./tests/test_m3_preview_logic.py-1059-        selects = [s for s, _ in cur.executed if s.startswith('SELECT')]
./tests/test_m3_preview_logic.py-1060-        updates = [p for s, p in cur.executed if s.startswith('UPDATE build_outbox')]
./tests/test_m3_preview_logic.py:1061:        self.assertTrue(all('FOR UPDATE SKIP LOCKED' in s and 'enqueued_at IS NULL' in s for s in selects))
./tests/test_m3_preview_logic.py-1062-        self.assertEqual(updates, [('bld_1',), ('bld_2',)])
./tests/test_m3_preview_logic.py-1063-        self.assertEqual(pool.conn.transactions, 3)
./tests/test_m3_preview_logic.py-1064-
./tests/test_m3_preview_logic.py:1065:    def test_enqueue_failure_leaves_row_pending(self):
--
./tests/test_m49_clean_room.py-250-            json={'followup': 'M4D2B_CLASSIFY:missing_requirement M4D2B_IDS:A1 the acceptance check for the '
./tests/test_m49_clean_room.py-251-                              'todo list must keep passing after this fix'})
./tests/test_m49_clean_room.py-252-        self.assertEqual(propose.status_code, 202, propose.text)
./tests/test_m49_clean_room.py-253-        body = propose.json()
./tests/test_m49_clean_room.py:254:        self.assertEqual(body['dispatch'], 'enqueued')
./tests/test_m49_clean_room.py-255-        modification_id = body['modification_id']
./tests/test_m49_clean_room.py-256-
./tests/test_m49_clean_room.py-257-        job = q.fetch_job(modification_id)
./tests/test_m49_clean_room.py:258:        self.assertIsNotNone(job, 'the real production enqueue must have created this real rq job')
--
./tests/test_m4d2b_parity_and_worker.py-20-one patch version behind the pin).
./tests/test_m4d2b_parity_and_worker.py-21-
./tests/test_m4d2b_parity_and_worker.py-22-Item 3 (real RQ production-job execution): unlike
./tests/test_m4d2b_parity_and_worker.py-23-tests/test_m4d2_live_fastapi_redis.py's `LiveRedisRQTests` (which
./tests/test_m4d2b_parity_and_worker.py:24:proved real Redis enqueue of the real `execute_modification_job` job,
--
./tests/test_m4d2b_parity_and_worker.py-184-        return project_id, version.id, key
./tests/test_m4d2b_parity_and_worker.py-185-
./tests/test_m4d2b_parity_and_worker.py-186-    def test_real_worker_process_dequeues_and_executes_execute_modification_job_ambiguous_path(self):
./tests/test_m4d2b_parity_and_worker.py-187-        """REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED. Proofs 1-7: real HTTP
./tests/test_m4d2b_parity_and_worker.py:188:        enqueue of the real job -> a real, separate `rq.Worker` OS process
--
./tests/test_m4d2b_parity_and_worker.py-207-            f'/api/v28/projects/{project_id}/versions/{version_id}/modifications', headers=h,
./tests/test_m4d2b_parity_and_worker.py-208-            json={'followup': 'not sure what to build -- M4D2B_CLASSIFY:ambiguous please clarify the request'})
./tests/test_m4d2b_parity_and_worker.py-209-        self.assertEqual(propose.status_code, 202, propose.text)
./tests/test_m4d2b_parity_and_worker.py-210-        body = propose.json()
./tests/test_m4d2b_parity_and_worker.py:211:        self.assertEqual(body['dispatch'], 'enqueued')
./tests/test_m4d2b_parity_and_worker.py-212-        modification_id = body['modification_id']
./tests/test_m4d2b_parity_and_worker.py-213-
./tests/test_m4d2b_parity_and_worker.py-214-        job = q.fetch_job(modification_id)
./tests/test_m4d2b_parity_and_worker.py:215:        self.assertIsNotNone(job, 'the real production enqueue must have created this real rq job')
--
./tests/test_m4d2b_parity_and_worker.py-289-            f'/api/v28/projects/{project_id}/versions/{version_id}/modifications', headers=h,
./tests/test_m4d2b_parity_and_worker.py-290-            json={'followup': 'fix the todo list -- M4D2B_CLASSIFY:system_bug M4D2B_IDS:A1 per acceptance A1'})
./tests/test_m4d2b_parity_and_worker.py-291-        self.assertEqual(propose.status_code, 202, propose.text)
./tests/test_m4d2b_parity_and_worker.py-292-        modification_id = propose.json()['modification_id']
./tests/test_m4d2b_parity_and_worker.py:293:        self.assertEqual(propose.json()['dispatch'], 'enqueued')
--
./tests/test_m4d2b_parity_and_worker.py-362-        before = self.client.get(f'/api/v28/projects/{project_id}/modifications/{modification_id}', headers=h).json()
./tests/test_m4d2b_parity_and_worker.py-363-        self.assertEqual(before['status'], 'NEEDS_CLARIFICATION')
./tests/test_m4d2b_parity_and_worker.py-364-        completed_at_1 = before['completed_at']
./tests/test_m4d2b_parity_and_worker.py-365-
./tests/test_m4d2b_parity_and_worker.py:366:        from omni_prod.queueing import enqueue_build, BUILD_QUEUE
./tests/test_m4d2b_parity_and_worker.py:367:        enqueue_build(REDIS_URL, 'omni_prod.worker_tasks.execute_modification_job', modification_id,
--
./tests/test_m4d2_live_fastapi_redis.py-153-            json={'followup': 'Add a delete button to each todo item.'})
./tests/test_m4d2_live_fastapi_redis.py-154-        self.assertEqual(propose.status_code, 202, propose.text)
./tests/test_m4d2_live_fastapi_redis.py-155-        body = propose.json()
./tests/test_m4d2_live_fastapi_redis.py-156-        self.assertEqual(body['status'], 'queued')
./tests/test_m4d2_live_fastapi_redis.py:157:        self.assertIn(body['dispatch'], ('enqueued', 'deferred'))
--
./tests/test_m4d2_live_fastapi_redis.py-337-@unittest.skipIf(_SKIP, _SKIP)
./tests/test_m4d2_live_fastapi_redis.py-338-class LiveRedisRQTests(unittest.TestCase):
./tests/test_m4d2_live_fastapi_redis.py-339-    """Section G: is Redis/RQ actually part of M4's production path?
./tests/test_m4d2_live_fastapi_redis.py-340-    v28_propose_modification calls
./tests/test_m4d2_live_fastapi_redis.py:341:    `enqueue_build(redis_url, "omni_prod.worker_tasks.execute_modification_job", modification_id, ...)`
./tests/test_m4d2_live_fastapi_redis.py:342:    (omni_prod/investor_app.py) via `omni_prod.queueing.enqueue_build`,
./tests/test_m4d2_live_fastapi_redis.py:343:    which is real `rq.Queue.enqueue` over a real `redis.Redis` connection
./tests/test_m4d2_live_fastapi_redis.py:344:    -- yes, it is. These tests prove the REAL enqueue -> REAL worker ->
--
./tests/test_m4d2_live_fastapi_redis.py-364-        cls.client = TestClient(iapp.app)
./tests/test_m4d2_live_fastapi_redis.py-365-        import redis
./tests/test_m4d2_live_fastapi_redis.py-366-        cls.redis_conn = redis.Redis.from_url(REDIS_URL)
./tests/test_m4d2_live_fastapi_redis.py-367-
./tests/test_m4d2_live_fastapi_redis.py:368:    def test_propose_modification_over_http_really_enqueues_a_redis_rq_job(self):
--
./tests/test_m4d2_live_fastapi_redis.py-391-        propose = self.client.post(f'/api/v28/projects/{project_id}/versions/{version.id}/modifications',
./tests/test_m4d2_live_fastapi_redis.py-392-                                    headers=h, json={'followup': 'queue me for real'})
./tests/test_m4d2_live_fastapi_redis.py-393-        self.assertEqual(propose.status_code, 202, propose.text)
./tests/test_m4d2_live_fastapi_redis.py-394-        modification_id = propose.json()['modification_id']
./tests/test_m4d2_live_fastapi_redis.py:395:        self.assertEqual(propose.json()['dispatch'], 'enqueued',
./tests/test_m4d2_live_fastapi_redis.py:396:                          'a real, reachable Redis must make the real enqueue_build() call succeed, not fall '
--
./tests/test_m4d2_live_fastapi_redis.py-403-        # Deliberately never run a worker on this job: executing it for real
./tests/test_m4d2_live_fastapi_redis.py-404-        # requires a live LLM provider (ChangeClassifierAgent), a
./tests/test_m4d2_live_fastapi_redis.py-405-        # pre-existing, already-disclosed external dependency unrelated to
./tests/test_m4d2_live_fastapi_redis.py-406-        # M4D.2's Postgres/Redis/FastAPI scope -- see
./tests/test_m4d2_live_fastapi_redis.py:407:        # test_real_rq_worker_pops_and_executes_a_real_enqueued_job below
--
./tests/test_m4d2_live_fastapi_redis.py-409-        # Cancel it so it cannot be picked up by a later test's worker.
./tests/test_m4d2_live_fastapi_redis.py-410-        job.cancel()
./tests/test_m4d2_live_fastapi_redis.py-411-        job.delete()
./tests/test_m4d2_live_fastapi_redis.py-412-
./tests/test_m4d2_live_fastapi_redis.py:413:    def test_real_rq_worker_pops_and_executes_a_real_enqueued_job(self):
./tests/test_m4d2_live_fastapi_redis.py-414-        """Enqueues a small, self-contained real function (not the LLM-
./tests/test_m4d2_live_fastapi_redis.py-415-        dependent execute_modification_job -- that boundary is a
./tests/test_m4d2_live_fastapi_redis.py-416-        pre-existing, already-disclosed external-provider dependency, not
./tests/test_m4d2_live_fastapi_redis.py-417-        an M4D.2 Postgres/Redis/FastAPI concern) through the REAL
./tests/test_m4d2_live_fastapi_redis.py:418:        `omni_prod.queueing.enqueue_build` helper, then runs a REAL
./tests/test_m4d2_live_fastapi_redis.py-419-        `rq.Worker` in burst mode against the REAL Redis queue and proves
./tests/test_m4d2_live_fastapi_redis.py-420-        it actually dequeued and executed the job (result visible via a
./tests/test_m4d2_live_fastapi_redis.py-421-        side effect in Postgres, not just 'job.is_finished')."""
./tests/test_m4d2_live_fastapi_redis.py:422:        from omni_prod.queueing import enqueue_build, BUILD_QUEUE
--
./tests/test_m4d2_live_fastapi_redis.py-429-                    cur.execute(
./tests/test_m4d2_live_fastapi_redis.py-430-                        "CREATE TABLE IF NOT EXISTS m4d2_rq_markers "
./tests/test_m4d2_live_fastapi_redis.py-431-                        "(marker TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")
./tests/test_m4d2_live_fastapi_redis.py-432-
./tests/test_m4d2_live_fastapi_redis.py:433:        job = enqueue_build(REDIS_URL, 'tests.m4d2_rq_job_target.mark_done', marker_table_row_id,
--
./tests/test_m4d2_live_fastapi_redis.py-449-                                  'this row directly to Postgres as independently-checkable proof of execution '
./tests/test_m4d2_live_fastapi_redis.py-450-                                  '(not merely rq reporting is_finished=True)')
./tests/test_m4d2_live_fastapi_redis.py-451-
./tests/test_m4d2_live_fastapi_redis.py-452-    def test_worker_failure_is_recorded_and_does_not_crash_the_worker_or_double_promote(self):
./tests/test_m4d2_live_fastapi_redis.py:453:        from omni_prod.queueing import enqueue_build, BUILD_QUEUE
./tests/test_m4d2_live_fastapi_redis.py-454-        import rq
./tests/test_m4d2_live_fastapi_redis.py-455-
./tests/test_m4d2_live_fastapi_redis.py:456:        job = enqueue_build(REDIS_URL, 'tests.m4d2_rq_job_target.always_fails', 'irrelevant-arg',
--
./tests/test_m4d2_live_fastapi_redis.py-462-        self.assertTrue(job.is_failed, f'status: {job.get_status()}')
./tests/test_m4d2_live_fastapi_redis.py-463-
./tests/test_m4d2_live_fastapi_redis.py-464-        # The worker must still be usable afterward -- a failed job must not
./tests/test_m4d2_live_fastapi_redis.py-465-        # crash the worker process or leave the queue connection unusable.
./tests/test_m4d2_live_fastapi_redis.py:466:        job2 = enqueue_build(REDIS_URL, 'tests.m4d2_rq_job_target.mark_done', f'after-failure-{uuid.uuid4().hex}',
--
./tests/test_m4_acceptance.py-210-        imports fastapi at the top (not installable in this sandbox), but
./tests/test_m4_acceptance.py-211-        its AST can still be inspected directly off disk. The route
./tests/test_m4_acceptance.py-212-        function's own AST must not reference CandidateModificationEngine,
./tests/test_m4_acceptance.py-213-        propose(), or any agent class -- only create()/create_outbox()/
./tests/test_m4_acceptance.py:214:        enqueue_build(). Execution is worker_tasks.execute_modification_job's
--
./tests/test_m4_acceptance.py-225-        attrs_used = {n.attr for n in ast.walk(route_fn) if isinstance(n, ast.Attribute)}
./tests/test_m4_acceptance.py-226-        forbidden = {'CandidateModificationEngine', 'propose', 'ChangeClassifierAgent', 'ProductEvolutionAgent'}
./tests/test_m4_acceptance.py-227-        self.assertFalse(forbidden & names_used, f'route directly touches: {forbidden & names_used}')
./tests/test_m4_acceptance.py-228-        self.assertFalse(forbidden & attrs_used, f'route directly touches: {forbidden & attrs_used}')
./tests/test_m4_acceptance.py:229:        self.assertIn('enqueue_build', names_used)
--
./tests/test_m4_acceptance.py-249-                                    'followup': 'add dark mode', 'target_markets': ('US',), 'rights_evidence': []})
./tests/test_m4_acceptance.py-250-
./tests/test_m4_acceptance.py-251-
./tests/test_m4_acceptance.py-252-# ===========================================================================
./tests/test_m4_acceptance.py:253:# D -- Redis enqueue failure remains recoverable through outbox
./tests/test_m4_acceptance.py-254-# ===========================================================================
./tests/test_m4_acceptance.py-255-
./tests/test_m4_acceptance.py-256-class AcceptanceD(unittest.TestCase):
./tests/test_m4_acceptance.py:257:    def test_D_enqueue_failure_leaves_the_row_pending_for_relay_to_retry(self):
./tests/test_m4_acceptance.py-258-        """See test_modification_repository.py OutboxDispatchTests for the
./tests/test_m4_acceptance.py-259-        full relay contract (FOR UPDATE SKIP LOCKED, one row per
./tests/test_m4_acceptance.py:260:        transaction). Proven here directly: an enqueue() that raises leaves
./tests/test_m4_acceptance.py:261:        the outbox row's enqueued_at untouched, so a later relay pass will
--
./tests/test_m5_build_economics.py-385-
./tests/test_m5_build_economics.py-386-
./tests/test_m5_build_economics.py-387-class DurableBuildRouteReservationTests(unittest.TestCase):
./tests/test_m5_build_economics.py-388-    """M5 remediation: the canonical build route reserves the FULL conservative
./tests/test_m5_build_economics.py:389:    total (LLM + capabilities + generated-app infra + retry) once, before enqueue."""
--
./tests/test_m5_build_economics.py-415-        conn = MagicMock(); conn.__enter__ = lambda s: s; conn.__exit__ = lambda *a: False
./tests/test_m5_build_economics.py-416-        conn.cursor.return_value = cursor
./tests/test_m5_build_economics.py-417-        conn.transaction.return_value = MagicMock(__enter__=lambda s: s, __exit__=lambda *a: False)
./tests/test_m5_build_economics.py-418-        pool = MagicMock(); pool.connection.return_value = conn
./tests/test_m5_build_economics.py:419:        enqueue = MagicMock()
--
./tests/test_m5_build_economics.py-430-             patch.object(investor_app, '_m5_resolve_build_contract', return_value=contract), \
./tests/test_m5_build_economics.py-431-             patch.object(investor_app, '_m5_cost_inputs', cost), \
./tests/test_m5_build_economics.py-432-             patch.object(investor_app, 'PostgresBuildContractRepository'), \
./tests/test_m5_build_economics.py-433-             patch.object(investor_app, 'PostgresBuildRepository', return_value=jobs), \
./tests/test_m5_build_economics.py:434:             patch.object(investor_app, 'enqueue_build', enqueue):
./tests/test_m5_build_economics.py-435-            req = investor_app.V27BuildRequest(prompt='Build a CRM', build_contract_id='bc_1',
./tests/test_m5_build_economics.py-436-                                               idempotency_key=idempotency_key)
./tests/test_m5_build_economics.py-437-            try:
./tests/test_m5_build_economics.py:438:                return investor_app.v28_build_async('prj_1', req, MagicMock()), reserve, enqueue, jobs, None
./tests/test_m5_build_economics.py-439-            except investor_app.HTTPException as exc:
./tests/test_m5_build_economics.py:440:                return None, reserve, enqueue, jobs, exc
./tests/test_m5_build_economics.py-441-
./tests/test_m5_build_economics.py-442-    def test_reservation_is_the_full_conservative_total(self):
./tests/test_m5_build_economics.py:443:        response, reserve, enqueue, jobs, exc = self._run()
./tests/test_m5_build_economics.py-444-        self.assertIsNone(exc)
./tests/test_m5_build_economics.py-445-        # 0.20 LLM + 0.01 image + 0.05 generated-app infra + 0.05 retry
./tests/test_m5_build_economics.py-446-        self.assertEqual(reserve.call_args.kwargs['estimated_provider_cost_usd'], Decimal('0.31'))
./tests/test_m5_build_economics.py:447:        enqueue.assert_called_once()
--
./tests/test_m5_build_economics.py-452-        self.assertEqual(claim['idempotency_key'], 'caller-retry-key-1')
./tests/test_m5_build_economics.py-453-        self.assertEqual(len(claim['request_fingerprint']), 64)
./tests/test_m5_build_economics.py-454-        self.assertEqual(len(claim['quote_fingerprint']), 64)
./tests/test_m5_build_economics.py-455-
./tests/test_m5_build_economics.py:456:    def test_denied_total_reservation_enqueues_nothing(self):
./tests/test_m5_build_economics.py:457:        _, reserve, enqueue, jobs, exc = self._run(reserve_allowed=False)
./tests/test_m5_build_economics.py-458-        self.assertEqual(exc.status_code, 402)
./tests/test_m5_build_economics.py-459-        reserve.assert_called_once()
./tests/test_m5_build_economics.py:460:        enqueue.assert_not_called()
./tests/test_m5_build_economics.py-461-        jobs.create_outbox.assert_not_called()
./tests/test_m5_build_economics.py-462-
./tests/test_m5_build_economics.py-463-    def test_build_without_an_approval_is_refused(self):
./tests/test_m5_build_economics.py-464-        # Directive 2026-10-09 §5: a direct API call does not bypass approval.
./tests/test_m5_build_economics.py:465:        _, reserve, enqueue, jobs, exc = self._run(require_approval='1')
./tests/test_m5_build_economics.py-466-        self.assertEqual(exc.status_code, 409)
./tests/test_m5_build_economics.py-467-        self.assertEqual(exc.detail['error'], 'approval_required')
./tests/test_m5_build_economics.py-468-        reserve.assert_not_called()
./tests/test_m5_build_economics.py:469:        enqueue.assert_not_called()
./tests/test_m5_build_economics.py-470-
./tests/test_m5_build_economics.py-471-    def test_second_approval_of_the_same_plan_returns_the_existing_build(self):
./tests/test_m5_build_economics.py-472-        # Directive 2026-10-09 §5: a double click does not create two builds.
./tests/test_m5_build_economics.py:473:        response, reserve, enqueue, jobs, exc = self._run(existing_build=('bld_first', 'running'))
--
./tests/test_m5_build_economics.py-476-        body = json.loads(response.body)
./tests/test_m5_build_economics.py-477-        self.assertEqual((body['build_id'], body['status'], body['duplicate']), ('bld_first', 'running', True))
./tests/test_m5_build_economics.py-478-        jobs.claim_build_request_idempotency.assert_called_once()
./tests/test_m5_build_economics.py-479-        reserve.assert_not_called()
./tests/test_m5_build_economics.py:480:        enqueue.assert_not_called()
./tests/test_m5_build_economics.py-481-        jobs.create_request.assert_not_called()
./tests/test_m5_build_economics.py-482-
./tests/test_m5_build_economics.py-483-    def test_same_caller_key_replays_the_original_build_before_reservation(self):
./tests/test_m5_build_economics.py:484:        response, reserve, enqueue, jobs, exc = self._run(
--
./tests/test_m5_build_economics.py-489-        self.assertEqual((body['build_id'], body['status'], body['duplicate']),
./tests/test_m5_build_economics.py-490-                         ('bld_replay', 'ready', True))
./tests/test_m5_build_economics.py-491-        jobs.claim_contract_build.assert_not_called()
./tests/test_m5_build_economics.py-492-        reserve.assert_not_called()
./tests/test_m5_build_economics.py:493:        enqueue.assert_not_called()
./tests/test_m5_build_economics.py-494-
./tests/test_m5_build_economics.py-495-    def test_same_caller_key_after_worker_crash_replays_the_in_flight_build_without_new_debit(self):
./tests/test_m5_build_economics.py-496-        for status in ('queued', 'running', 'failed'):
./tests/test_m5_build_economics.py-497-            with self.subTest(status=status):
./tests/test_m5_build_economics.py:498:                response, reserve, enqueue, jobs, exc = self._run(
--
./tests/test_m5_build_economics.py-502-                body = json.loads(response.body)
./tests/test_m5_build_economics.py-503-                self.assertEqual((body['build_id'], body['status'], body['duplicate']),
./tests/test_m5_build_economics.py-504-                                 ('bld_crashed', status, True))
./tests/test_m5_build_economics.py-505-                reserve.assert_not_called()
./tests/test_m5_build_economics.py:506:                enqueue.assert_not_called()
./tests/test_m5_build_economics.py-507-                jobs.create_request.assert_not_called()
./tests/test_m5_build_economics.py-508-
./tests/test_m5_build_economics.py-509-    def test_same_caller_key_with_changed_quote_returns_conflict(self):
./tests/test_m5_build_economics.py:510:        _, reserve, enqueue, jobs, exc = self._run(
--
./tests/test_m5_build_economics.py-512-        )
./tests/test_m5_build_economics.py-513-        self.assertEqual(exc.status_code, 409)
./tests/test_m5_build_economics.py-514-        self.assertEqual(exc.detail['error'], 'idempotency_conflict')
./tests/test_m5_build_economics.py-515-        reserve.assert_not_called()
./tests/test_m5_build_economics.py:516:        enqueue.assert_not_called()
./tests/test_m5_build_economics.py-517-
./tests/test_m5_build_economics.py-518-    def test_legacy_request_without_key_keeps_contract_deduplication_and_retry_path(self):
./tests/test_m5_build_economics.py:519:        response, reserve, enqueue, jobs, exc = self._run(idempotency_key=None)
--
./tests/test_m5_build_economics.py-521-        self.assertEqual(response.status_code, 202)
./tests/test_m5_build_economics.py-522-        jobs.claim_build_request_idempotency.assert_not_called()
./tests/test_m5_build_economics.py-523-        jobs.claim_contract_build.assert_called_once()
./tests/test_m5_build_economics.py-524-        reserve.assert_called_once()
./tests/test_m5_build_economics.py:525:        enqueue.assert_called_once()
./tests/test_m5_build_economics.py-526-
./tests/test_m5_build_economics.py-527-    def test_invalid_caller_key_is_rejected_before_build_admission(self):
./tests/test_m5_build_economics.py:528:        _, reserve, enqueue, jobs, exc = self._run(idempotency_key='not a valid key')
./tests/test_m5_build_economics.py-529-        self.assertEqual(exc.status_code, 422)
./tests/test_m5_build_economics.py-530-        self.assertEqual(exc.detail['error'], 'invalid_idempotency_key')
./tests/test_m5_build_economics.py-531-        jobs.claim_build_request_idempotency.assert_not_called()
./tests/test_m5_build_economics.py-532-        reserve.assert_not_called()
./tests/test_m5_build_economics.py:533:        enqueue.assert_not_called()
./tests/test_m5_build_economics.py-534-
./tests/test_m5_build_economics.py-535-    def test_unknown_required_quote_blocks_before_reservation(self):
./tests/test_m5_build_economics.py-536-        from omni_prod.build_cost_plan import CostQuoteUnknown
./tests/test_m5_build_economics.py:537:        _, reserve, enqueue, _, exc = self._run(cost_inputs_exc=CostQuoteUnknown(['capability media.image.generate has no configured provider quote']))
./tests/test_m5_build_economics.py-538-        self.assertEqual(exc.status_code, 402)
./tests/test_m5_build_economics.py-539-        self.assertEqual(exc.detail['error'], 'cost_quote_unknown')
./tests/test_m5_build_economics.py-540-        reserve.assert_not_called()
./tests/test_m5_build_economics.py:541:        enqueue.assert_not_called()
--
./tests/test_m5_economics_reconciliation.py-15-from omni_prod.build_cost_plan import (
./tests/test_m5_economics_reconciliation.py-16-    CostQuoteUnknown,
./tests/test_m5_economics_reconciliation.py-17-    build_economics_quote,
./tests/test_m5_economics_reconciliation.py-18-    collect_build_cost_inputs,
./tests/test_m5_economics_reconciliation.py:19:    reserve_and_enqueue,
--
./tests/test_m5_economics_reconciliation.py-145-    def test_5_image_quote_pushes_build_over_margin_floor_before_any_provider_call(self):
./tests/test_m5_economics_reconciliation.py-146-        expensive = image_assignment(self.image_req.id, est="0.80", maximum="1.40")
./tests/test_m5_economics_reconciliation.py-147-        quote, _ = self.quote(assignments=expensive, revenue="2.00", margin="0.20")
./tests/test_m5_economics_reconciliation.py-148-        submit = MagicMock()
./tests/test_m5_economics_reconciliation.py:149:        enqueue = MagicMock()
./tests/test_m5_economics_reconciliation.py-150-        reserve = MagicMock()
./tests/test_m5_economics_reconciliation.py-151-        with self.assertRaises(PermissionError):
./tests/test_m5_economics_reconciliation.py:152:            reserve_and_enqueue(quote=enforce_margin_floor(quote), reserve=reserve, enqueue=enqueue)
./tests/test_m5_economics_reconciliation.py:153:        reserve.assert_not_called(); enqueue.assert_not_called(); submit.assert_not_called()
./tests/test_m5_economics_reconciliation.py-154-
./tests/test_m5_economics_reconciliation.py-155-    def test_9_no_paid_provider_is_called_if_total_reservation_fails(self):
./tests/test_m5_economics_reconciliation.py-156-        quote, _ = self.quote(assignments=image_assignment(self.image_req.id), infra=infra_quotes(self.contract))
./tests/test_m5_economics_reconciliation.py-157-        reserve = MagicMock(return_value=SimpleNamespace(allowed=False, reason="paid-provider budget exhausted"))
./tests/test_m5_economics_reconciliation.py:158:        enqueue = MagicMock()
./tests/test_m5_economics_reconciliation.py-159-        with self.assertRaises(PermissionError) as ctx:
./tests/test_m5_economics_reconciliation.py:160:            reserve_and_enqueue(quote=quote, reserve=reserve, enqueue=enqueue)
./tests/test_m5_economics_reconciliation.py-161-        self.assertIn("budget exhausted", str(ctx.exception))
./tests/test_m5_economics_reconciliation.py-162-        reserve.assert_called_once_with(quote.total_authorized_variable_usd)  # the full total, in one reservation
./tests/test_m5_economics_reconciliation.py:163:        enqueue.assert_not_called()
./tests/test_m5_economics_reconciliation.py-164-
./tests/test_m5_economics_reconciliation.py-165-    def test_successful_reservation_covers_the_full_total_once(self):
./tests/test_m5_economics_reconciliation.py-166-        quote, _ = self.quote(assignments=image_assignment(self.image_req.id), infra=infra_quotes(self.contract))
./tests/test_m5_economics_reconciliation.py-167-        reserve = MagicMock(return_value=SimpleNamespace(allowed=True, reason="authorized"))
./tests/test_m5_economics_reconciliation.py:168:        enqueue = MagicMock()
./tests/test_m5_economics_reconciliation.py:169:        reserve_and_enqueue(quote=quote, reserve=reserve, enqueue=enqueue)
./tests/test_m5_economics_reconciliation.py-170-        reserve.assert_called_once_with(D("0.61"))
./tests/test_m5_economics_reconciliation.py:171:        enqueue.assert_called_once()
--
./tests/test_modification_repository.py-201-                                        current_version_id=None, force=False), 'conflict')
./tests/test_modification_repository.py-202-
./tests/test_modification_repository.py-203-
./tests/test_modification_repository.py-204-# ===========================================================================
./tests/test_modification_repository.py:205:# create / create_outbox / mark_outbox_enqueued / dispatch_pending_outbox
--
./tests/test_modification_repository.py-236-        sql, params = cur.executed[0]
./tests/test_modification_repository.py-237-        self.assertIn('INSERT INTO modification_outbox', sql)
./tests/test_modification_repository.py-238-        self.assertEqual(params, ('mod_1',))
./tests/test_modification_repository.py-239-
./tests/test_modification_repository.py:240:    def test_mark_outbox_enqueued_sets_timestamp(self):
./tests/test_modification_repository.py-241-        r, cur = repo_of()
./tests/test_modification_repository.py:242:        r.mark_outbox_enqueued('mod_1')
./tests/test_modification_repository.py-243-        sql, params = cur.executed[0]
./tests/test_modification_repository.py:244:        self.assertIn('SET enqueued_at = now()', sql)
--
./tests/test_modification_repository.py-253-        out = PostgresModificationRepository(pool).dispatch_pending_outbox(sent.append, older_than_seconds=30)
./tests/test_modification_repository.py-254-        self.assertEqual((out, sent), (['mod_1', 'mod_2'], ['mod_1', 'mod_2']))
./tests/test_modification_repository.py-255-        selects = [s for s, _ in cur.executed if s.startswith('SELECT')]
./tests/test_modification_repository.py-256-        updates = [p for s, p in cur.executed if s.startswith('UPDATE modification_outbox')]
./tests/test_modification_repository.py:257:        self.assertTrue(all('FOR UPDATE SKIP LOCKED' in s and 'enqueued_at IS NULL' in s for s in selects))
./tests/test_modification_repository.py-258-        self.assertEqual(updates, [('mod_1',), ('mod_2',)])
./tests/test_modification_repository.py-259-        self.assertEqual(pool.conn.transactions, 3)
./tests/test_modification_repository.py-260-
./tests/test_modification_repository.py:261:    def test_enqueue_failure_leaves_row_pending(self):
--
./tests/test_v7_readiness_regression.py-1-"""V7 regressions: genuine cost gating, outbound intent and sign-in visibility.
./tests/test_v7_readiness_regression.py-2-
./tests/test_v7_readiness_regression.py:3:These tests never enqueue jobs or call a model provider.
-- lease/heartbeat --
./omni_prod/active_jobs.py:12:  * build_jobs.status = 'running' -- whatever its heartbeat. An old heartbeat is NOT proof that the work ended: the
./omni_prod/active_jobs.py:14:    release the gate for it, with --acknowledge-stale <exact id>; the deploy workflow never passes that flag.
./omni_prod/active_jobs.py:16:  * intake_reservations.state IN ('CLAIMED', 'EXECUTING') (the intake consumer, even with an expired lease)
./omni_prod/active_jobs.py:50:                   "SELECT id, status, EXTRACT(EPOCH FROM (now() - COALESCE(heartbeat_at, started_at, created_at)))::int "
./omni_prod/active_jobs.py:62:        # informational only: which running rows also have an old heartbeat (they still block)
./omni_prod/active_jobs.py:63:        out['running_builds_with_old_heartbeat'] = [b[0] for b in running if b[2] > 900 and b[0] not in ack]
./omni_prod/agents_registry.py:175:        _agent("agent.chief_orchestrator", "Chief Orchestrator", ("coordinate product-production agents and release evidence",), CapabilityStatus.PARTIAL, (
./omni_prod/agents_registry.py:176:            "skill.internal.capability.plan", "skill.internal.cost.plan", "skill.internal.release.gate",
./omni_prod/agents_registry.py:214:        _agent("agent.qa", "QA Agent", ("run functional verification and aggregate release evidence",), CapabilityStatus.PARTIAL, (_s("software.test"), "skill.internal.release.gate")),
./omni_prod/agents_registry.py:218:        _agent("agent.security", "Security Agent", ("apply security checks and release gates",), CapabilityStatus.PARTIAL, ("skill.internal.security_review",)),
./omni_prod/agents_registry.py:221:        _agent("agent.deployment", "Deployment Agent", ("publish verified releases and support rollback",), CapabilityStatus.NOT_IMPLEMENTED, (_s("software.deploy.web"),) + publish_skills),
./omni_prod/agent_catalog.py:84:       'material failures are reported and block release by policy', 'agent.security'),
./omni_prod/agent_catalog.py:91:    _r('release_agent', QUALITY, 'Release Agent', 'publish an authorized version',
./omni_prod/agent_catalog.py:92:       ('build', 'deploy', 'smoke', 'release record', 'rollback'),
./omni_prod/agent_catalog.py:182:       ('checkpoints', 'leases', 'compensation', 'restore'), 'crash recovery is proven'),
./omni_prod/agent_catalog.py:185:    _r('release_change_coordinator', PLATFORM, 'Release & Change Coordinator', 'no uncoordinated change',
./omni_prod/agent_os/agents.py:106:     ('secret_detection', 'preview_access_check', 'security_release_gate'), 'quality_gate_agent',
./omni_prod/agent_os/agents.py:121:     ('preview_deploy', 'preview_health_check', 'preview_access_protect'), 'release_agent',
./omni_prod/agent_os/agents.py:123:    ('release_agent', 'Release Agent', 'platform', 'versions and release gates', 'commits a version only when gates pass',
./omni_prod/agent_os/agents.py:124:     ('version_create', 'artifact_commit', 'release_gate'), 'quality_gate_agent',
./omni_prod/agent_os/agents.py:125:     ('omni_prod.worker_tasks:evaluate_release_gates', 'omni_prod.workspace:PostgresProjectWorkspace.commit'), (PAID,),
./omni_prod/agent_os/agents.py:189:     ('security_release_gate', 'release_gate'), '', ('omni_prod.agent_os.meta:quality_gate',), (U('tests/test_agent_os.py'),), {}),
./omni_prod/agent_os/agents.py:207:                           'publish without the release gate'),
./omni_prod/agent_os/agents.py:230:    # 2026-10-10). The release policy (quality gate) is platform-owned.
./omni_prod/agent_os/agents.py:233:    'deployment_agent': ('release_agent',),
./omni_prod/agent_os/departments.py:89:               'test results, repairs', 'release policy mandatory checks', 'repair bounded by rounds and budget'),
./omni_prod/agent_os/departments.py:107:    Department('D17', 'Release, Reliability & Operations', 'release gate, observability, incidents, rollback',
./omni_prod/agent_os/departments.py:108:               ('release_agent', 'quality_gate_agent', 'observability_agent', 'sre_reliability_agent'),
./omni_prod/agent_os/departments.py:111:               'release policy + stage evidence rows', '$0'),
./omni_prod/agent_os/evidence.py:15:                 'rollback restores the exact stored version', 'queued build cancelled + reservation released',
./omni_prod/agent_os/evidence.py:55:# (screenshots uploaded as a workflow artifact), quality, security, release
./omni_prod/agent_os/evidence.py:62:                          'release policy decision', 'durable stage rows'))
./omni_prod/agent_os/meta.py:39:    'provider_routing': ('price/quality routing, fallback, quota release', ('tests/test_provider_quota_and_dialects.py',)),
./omni_prod/agent_os/meta.py:45:    'release': ('release gates and versions', ('tests/test_m3_preview_logic.py',)),
./omni_prod/agent_os/meta.py:121:    ('provider 429', 'tests/test_failure_injection.py::test_429_is_released_and_the_route_is_skipped', 'released at $0, route skipped'),
./omni_prod/agent_os/recorder.py:5:adds the browser, acceptance, security, cost, release and quality-gate tasks
./omni_prod/agent_os/recorder.py:109:            final.append(('security_agent', ('secret_detection', 'security_release_gate'), bool(gates['security'].get('passed')), 'static scan'))
./omni_prod/agent_os/recorder.py:116:            final.append(('release_agent', ('version_create', 'release_gate'), True, 'version committed'))
./omni_prod/agent_os/recorder.py:128:            # The release policy is the independent decision (platform-owned checks).
./omni_prod/agent_os/recorder.py:134:                for agent in ('coding_agent', 'repair_agent', 'release_agent', 'behavioral_acceptance_agent',
./omni_prod/agent_os/recorder.py:148:# Release-policy check that decides each verification stage (platform-owned).
./omni_prod/agent_os/recorder.py:183:    passed (stage results come from the platform-owned release policy, not the
./omni_prod/agent_os/recorder.py:390:            # is decided later by the release policy); never on its own.
./omni_prod/agent_os/recorder.py:456:                self._close(stage, res == 'PASS', {'release_check': check, 'status': res})
./omni_prod/agent_os/recorder.py:472:            self._close('release', True, {'note': 'version committed'})
./omni_prod/agent_os/skills.py:45:    'Deployment': ('deployment_agent', 'release_agent', ('web',), 'host time', 'preview data per project', ()),
./omni_prod/agent_os/skills.py:46:    'Release': ('release_agent', 'quality_gate_agent', ('web',), '$0', 'versions + artifacts', ()),
./omni_prod/agent_os/skills.py:141:    'unit_test_execution': (('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor',), (VERIFY_REPLAY, REHEARSAL_ACCEPT, DEPLOY, U('tests/test_acceptance_coverage.py'), U('tests/test_release_policy.py')), ''),
./omni_prod/agent_os/skills.py:172:    'security_release_gate': (('omni_prod.worker_tasks:evaluate_release_gates',), (PAID, U('tests/test_release_policy.py')), ''),
./omni_prod/agent_os/skills.py:196:    'unused_reservation_release': (('omni_prod.subscription_store:PostgresSubscriptionService',), (FREE, CRASH), ''),
./omni_prod/agent_os/skills.py:222:    # Release
./omni_prod/agent_os/skills.py:225:    'release_evidence_generation': (('omni_prod.worker_tasks:_run_live_build_job',), (PAID,), ''),
./omni_prod/agent_os/skills.py:226:    'release_gate': (('omni_prod.worker_tasks:evaluate_release_gates',), (PAID,), ''),
./omni_prod/agent_os/truth_matrix.py:50:    PlatformCapability('release_policy', ('omni_prod.release_policy:build_report',),
./omni_prod/agent_os/truth_matrix.py:51:                       (VERIFY_REPLAY, U('tests/test_release_policy.py'))),
./omni_prod/agent_os/truth_matrix.py:70:    PlatformCapability('durable_stage_evidence', ('omni_prod.release_policy:persist',),
./omni_prod/agent_os/truth_matrix.py:71:                       (VERIFY_REPLAY, Evidence('integration', 'tests/test_release_policy.py'))),
./omni_prod/agent_os/truth_matrix.py:122:        ('secret_detection', 'security_release_gate')),
./omni_prod/agent_os/truth_matrix.py:123:    Row('Never READY when a mandatory check failed or did not run', 'release policy', 'quality_gate_agent',
./omni_prod/agent_os/truth_matrix.py:124:        platform=('release_policy',), tests=('tests/test_release_policy.py', 'tests/test_release_blocks_on_failed_acceptance.py')),
./omni_prod/agent_os/truth_matrix.py:131:    Row('Version history and rollback', 'versions', 'release_agent', ('version_create',),
./omni_prod/agent_os/truth_matrix.py:133:    Row('Download the product as ZIP', 'export', 'release_agent', platform=('zip_export',), shown_to_customer=True),
./omni_prod/agent_os/truth_matrix.py:134:    Row('Publish to a live address', 'publish', 'deployment_agent', ('release_publish',), platform=('publish',),
./omni_prod/attestation.py:15:            'predicateType':'https://omnicreator.ai/attestation/release/v1',
./omni_prod/brand_native_clients.py:9:        'app/build.gradle.kts':f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{ val ks=System.getenv("ONE48AI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks); storePassword=System.getenv("ONE48AI_ANDROID_STORE_PASSWORD"); keyAlias=System.getenv("ONE48AI_ANDROID_KEY_ALIAS"); keyPassword=System.getenv("ONE48AI_ANDROID_KEY_PASSWORD") }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
./omni_prod/brand_native_clients.py:12:        '.github/workflows/android-aab.yml':'name: 148ai-android-aab\non: [workflow_dispatch]\njobs:\n  aab:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-java@v4\n        with: {distribution: temurin, java-version: "17"}\n      - uses: gradle/actions/setup-gradle@v4\n        with: {gradle-version: "8.9"}\n      - run: gradle bundleRelease\n        env:\n          ONE48AI_ANDROID_KEYSTORE: ${{ secrets.ONE48AI_ANDROID_KEYSTORE }}\n          ONE48AI_ANDROID_STORE_PASSWORD: ${{ secrets.ONE48AI_ANDROID_STORE_PASSWORD }}\n          ONE48AI_ANDROID_KEY_ALIAS: ${{ secrets.ONE48AI_ANDROID_KEY_ALIAS }}\n          ONE48AI_ANDROID_KEY_PASSWORD: ${{ secrets.ONE48AI_ANDROID_KEY_PASSWORD }}\n',
./omni_prod/build_contract.py:141:    release_target: str
./omni_prod/build_contract.py:168:        if not self.product_family.strip() or not self.target.strip() or not self.release_target.strip():
./omni_prod/build_contract.py:169:            raise ValueError("product family, target and release target are required")
./omni_prod/build_contract.py:198:            "release_target": self.release_target,
./omni_prod/build_contract.py:256:            release_target=str(data["release_target"]),
./omni_prod/build_control.py:8:reservation is released by the normal settlement path.
./omni_prod/build_control.py:128:    build repository's: heartbeat + stop flag, live log, stop request."""
./omni_prod/build_control.py:142:                row = conn.execute("UPDATE modification_requests SET heartbeat_at = now() WHERE id = %s "
./omni_prod/capability_executor.py:70:        lease_seconds: int = 60,
./omni_prod/capability_executor.py:76:        if lease_seconds < 1 or max_polls < 1 or max_artifact_bytes < 1:
./omni_prod/capability_executor.py:77:            raise ValueError("lease_seconds, max_polls and max_artifact_bytes must be >= 1")
./omni_prod/capability_executor.py:82:        self.lease_seconds = lease_seconds
./omni_prod/capability_executor.py:261:            lease_seconds=self.lease_seconds,
./omni_prod/capability_executor.py:263:            raise CapabilityExecutionError(f"provider execution lease unavailable: {requirement.id}")
./omni_prod/capability_planner.py:82:                if self._has_any(low, "publish", "release", "signed", "play store", "aab", "פרסום", "חתום"):
./omni_prod/capability_planner.py:83:                    add("target.android.build", "Android release/build target")
./omni_prod/capability_planner.py:86:                if self._has_any(low, "publish", "release", "signed", "app store", "ipa", "פרסום", "חתום"):
./omni_prod/capability_planner.py:87:                    add("target.ios.build", "iOS release/build target")
./omni_prod/capability_repository.py:15:class AttemptLeaseConflict(RuntimeError):
./omni_prod/capability_repository.py:49:    lease_owner: str | None
./omni_prod/capability_repository.py:50:    lease_expires_at: float | None
./omni_prod/capability_repository.py:216:            "lease_owner": None,
./omni_prod/capability_repository.py:217:            "lease_expires_at": 0.0,
./omni_prod/capability_repository.py:222:    def claim_execution_attempt(self, idempotency_key: str, *, worker_id: str, now: float, lease_seconds: int) -> bool:
./omni_prod/capability_repository.py:223:        if lease_seconds < 1:
./omni_prod/capability_repository.py:224:            raise ValueError("lease_seconds must be >= 1")
./omni_prod/capability_repository.py:230:        owner = row.get("lease_owner")
./omni_prod/capability_repository.py:231:        expires = float(row.get("lease_expires_at") or 0)
./omni_prod/capability_repository.py:234:        row["lease_owner"] = worker_id
./omni_prod/capability_repository.py:235:        row["lease_expires_at"] = now + lease_seconds
./omni_prod/capability_repository.py:242:        if worker_id is not None and row.get("lease_owner") != worker_id:
./omni_prod/capability_repository.py:243:            raise AttemptLeaseConflict("worker no longer owns provider execution lease")
./omni_prod/capability_repository.py:262:        if worker_id is not None and row.get("lease_owner") != worker_id:
./omni_prod/capability_repository.py:277:        if attempt.get("lease_owner") != worker_id:
./omni_prod/capability_repository.py:278:            raise AttemptLeaseConflict("lease owner mismatch")
./omni_prod/capability_repository.py:320:                status=row["status"], lease_owner=row.get("lease_owner"),
./omni_prod/capability_repository.py:321:                lease_expires_at=(None if row.get("lease_expires_at") is None else float(row["lease_expires_at"])),
./omni_prod/capability_repository.py:534:            status=row[7], lease_owner=row[8],
./omni_prod/capability_repository.py:535:            lease_expires_at=(None if expires is None else float(expires)),
./omni_prod/capability_repository.py:547:            "lease_owner": attempt.lease_owner, "lease_expires_at": attempt.lease_expires_at,
./omni_prod/capability_repository.py:562:                               idempotency_key, provider_task_id, status, lease_owner,
./omni_prod/capability_repository.py:563:                               lease_expires_at, last_error_code, last_error_message
./omni_prod/capability_repository.py:581:                            idempotency_key, status, lease_owner, lease_expires_at
./omni_prod/capability_repository.py:591:                        "lease_owner": None, "lease_expires_at": None,
./omni_prod/capability_repository.py:595:        self, idempotency_key: str, *, worker_id: str, now: float, lease_seconds: int
./omni_prod/capability_repository.py:597:        if lease_seconds < 1:
./omni_prod/capability_repository.py:598:            raise ValueError("lease_seconds must be >= 1")
./omni_prod/capability_repository.py:600:        expires = now_dt + timedelta(seconds=lease_seconds)
./omni_prod/capability_repository.py:607:                        SET lease_owner=%s, lease_expires_at=%s, updated_at=now()
./omni_prod/capability_repository.py:610:                          AND (lease_owner IS NULL OR lease_owner=%s OR lease_expires_at <= %s)
./omni_prod/capability_repository.py:623:                        """SELECT provider_task_id, status, lease_owner
./omni_prod/capability_repository.py:632:                        raise AttemptLeaseConflict("lease owner mismatch")
./omni_prod/capability_repository.py:641:                        WHERE idempotency_key=%s AND lease_owner=%s
./omni_prod/capability_repository.py:653:                           idempotency_key, provider_task_id, status, lease_owner,
./omni_prod/capability_repository.py:654:                           lease_expires_at, last_error_code, last_error_message
./omni_prod/capability_repository.py:675:                        WHERE idempotency_key=%s AND status=%s AND lease_owner=%s
./omni_prod/capability_repository.py:683:        idempotency_key: str, lease_owner: str, now: float,
./omni_prod/capability_repository.py:684:        lease_seconds: int, pricing_version: str = "legacy-unknown",
./omni_prod/capability_repository.py:692:            idempotency_key, worker_id=lease_owner, now=now, lease_seconds=lease_seconds
./omni_prod/capability_repository.py:695:            if existing.get("lease_owner") != lease_owner:
./omni_prod/capability_repository.py:696:                raise AttemptLeaseConflict("provider execution attempt has an active lease")
./omni_prod/capability_repository.py:703:            lease_owner=current["lease_owner"], lease_expires_at=current["lease_expires_at"],
./omni_prod/capability_repository.py:708:    def record_provider_task_id(self, attempt_id: str, provider_task_id: str, *, lease_owner: str) -> None:
./omni_prod/capability_repository.py:715:        if not self.record_provider_handle(row[0], provider_task_id=provider_task_id, worker_id=lease_owner):
./omni_prod/capability_repository.py:716:            raise AttemptLeaseConflict("provider execution handle update lost lease")
./omni_prod/capability_repository.py:718:    def transition_attempt(self, attempt_id: str, *, expected: str, target: str, lease_owner: str) -> None:
./omni_prod/capability_repository.py:726:            row[0], expected=expected, target=target, worker_id=lease_owner
./omni_prod/capability_repository.py:748:                        """SELECT status, lease_owner FROM provider_execution_attempts
./omni_prod/capability_repository.py:756:                        raise AttemptLeaseConflict("lease owner mismatch")
./omni_prod/capability_repository.py:802:                        WHERE idempotency_key=%s AND lease_owner=%s
./omni_prod/company_os.py:26:               ('strategy alignment',), ('runway', 'north-star build acceptance', 'release readiness')),
./omni_prod/company_os.py:47:    Department('qa', 'QA / Evals / Release', 'Prove behavior before release and prevent regressions.',
./omni_prod/company_os.py:48:               ('unit/integration/E2E', 'benchmarks', 'regression', 'release evidence'),
./omni_prod/company_os.py:50:               ('exceptional release with failed gate'),
./omni_prod/company_os.py:51:               ('all required release gates',), ('escaped bugs', 'benchmark success', 'rollback rate')),
./omni_prod/company_os.py:123:    'release_failure': ('qa', 88, False),
./omni_prod/company_os.py:156:    def release_council(self) -> dict:
./omni_prod/company_os.py:177:            'Ship only green releases; create recovery artifact and checksum.',
./omni_prod/company_os.py:223:            'release_council': self.release_council(),
./omni_prod/company_os.py:227:    def evaluate_release(self, gate_results: Mapping[str, Any], *, founder_public_launch_approved: bool = False) -> dict:
./omni_prod/company_os.py:228:        """Cross-functional release council evaluation.
./omni_prod/conversation/supervisor.py:65:               r'(?:\s+לבנות)?(?:\s+(?:עכשיו|כבר|בבקשה))*|(?:ok\s+)?(?:go|start|let\'?s start)(?:\s+(?:now|please))*')
./omni_prod/conversation/supervisor.py:158:           'content_saved': 'I saved the content you wrote in the project summary, exactly as written. Any earlier approval is cancelled; please approve the updated version.',
./omni_prod/creator_plan.py:124:            "family": contract.product_family, "target": contract.target, "release_target": contract.release_target,
./omni_prod/economics_report.py:129:    READY (release policy READY). Builds with unknown cost are excluded from
./omni_prod/economics_report.py:168:                      '/ builds that ended READY under the release policy',
./omni_prod/evidence_export.py:162:                   'release_ready': ev.get('release_ready'), 'snapshots': _clean(ev.get('repair_snapshots') or ev.get('round_snapshots'))},
./omni_prod/gate_replay.py:182:    """Release-policy decision for a replayed version (no model review ran:
./omni_prod/gate_replay.py:187:    from .worker_tasks import release_quality_report
./omni_prod/gate_replay.py:191:    qr = release_quality_report(f'replay:{vid}', SimpleNamespace(executor=chain), None, result, quality, security,
./omni_prod/gate_replay.py:198:        from .release_policy import persist
./omni_prod/intake/budget.py:15:  claim()          RESERVED -> CLAIMED (lease) -- single conditional UPDATE.
./omni_prod/intake/budget.py:19:  release()        RESERVED/CLAIMED -> RELEASED (provider certainly not contacted).
./omni_prod/intake/budget.py:20:  reconcile()      expired EXECUTING -> UNKNOWN (never released, never replayed);
./omni_prod/intake/budget.py:21:                   expired CLAIMED / stale RESERVED -> RELEASED.
./omni_prod/intake/budget.py:44:RESERVED, CLAIMED, EXECUTING, SETTLED, UNKNOWN, RELEASED = (
./omni_prod/intake/budget.py:45:    'RESERVED', 'CLAIMED', 'EXECUTING', 'SETTLED', 'UNKNOWN', 'RELEASED')
./omni_prod/intake/budget.py:226:SELECT COALESCE(SUM(CASE r.state WHEN 'RELEASED' THEN 0 WHEN 'SETTLED' THEN r.actual_usd ELSE r.quoted_usd END), 0)
./omni_prod/intake/budget.py:229:  AND (%s = false OR r.state NOT IN ('SETTLED', 'RELEASED')
./omni_prod/intake/budget.py:316:    def claim(self, reservation_id: str, *, worker_id: str, lease_seconds: int = 90,
./omni_prod/intake/budget.py:319:        it was released, or it is too old to be useful (then it is released:
./omni_prod/intake/budget.py:326:                    f"claimed_at = now(), lease_expires_at = now() + make_interval(secs => %s), updated_at = now() "
./omni_prod/intake/budget.py:328:                    f"RETURNING {_COLS}", (token, worker_id[:120], lease_seconds, reservation_id, max_age_seconds))
./omni_prod/intake/budget.py:335:        if current is not None and current.state == RESERVED:          # too old: never invoked -> release
./omni_prod/intake/budget.py:336:            self.release(reservation_id, reason='not claimed within its useful age')
./omni_prod/intake/budget.py:339:    def mark_executing(self, reservation: Reservation, *, lease_seconds: int = 90) -> bool:
./omni_prod/intake/budget.py:344:                            "lease_expires_at = now() + make_interval(secs => %s), updated_at = now() "
./omni_prod/intake/budget.py:345:                            "WHERE id = %s AND state = 'CLAIMED' AND claim_token = %s AND lease_expires_at > now() "
./omni_prod/intake/budget.py:346:                            "RETURNING id", (lease_seconds, reservation.id, reservation.claim_token))
./omni_prod/intake/budget.py:414:    # -- RELEASE / RECONCILE ---------------------------------------------------
./omni_prod/intake/budget.py:415:    def release(self, reservation_id: str, *, reason: str) -> bool:
./omni_prod/intake/budget.py:423:                cur.execute("UPDATE intake_reservations SET state = 'RELEASED', updated_at = now(), "
./omni_prod/intake/budget.py:428:                    self._event(cur, reservation_id, before[0], RELEASED, {'reason': reason[:500]})
./omni_prod/intake/budget.py:432:        """Expired leases and abandoned reservations. Never releases funds of an
./omni_prod/intake/budget.py:434:        out = {'unknown': [], 'released': []}
./omni_prod/intake/budget.py:437:                        "(state IN ('CLAIMED', 'EXECUTING') AND lease_expires_at < now()) OR "
./omni_prod/intake/budget.py:446:                                    "failure_reason = 'lease expired during execution: provider outcome and billing "
./omni_prod/intake/budget.py:448:                                    "WHERE id = %s AND state = 'EXECUTING' AND lease_expires_at < now() RETURNING id",
./omni_prod/intake/budget.py:451:                            self._event(cur, rid, EXECUTING, UNKNOWN, {'reason': 'lease expired'})
./omni_prod/intake/budget.py:453:            elif self.release(rid, reason='lease expired before the provider was contacted' if state == CLAIMED
./omni_prod/intake/budget.py:455:                out['released'].append(rid)
./omni_prod/intake/reservation_worker.py:90:                        lease_seconds: int = 90, max_age_seconds: int = 120) -> dict:
./omni_prod/intake/reservation_worker.py:93:    r = svc.claim(reservation_id, worker_id=worker_id, lease_seconds=lease_seconds, max_age_seconds=max_age_seconds)
./omni_prod/intake/reservation_worker.py:102:        svc.release(r.id, reason=str(exc)[:200])
./omni_prod/intake/reservation_worker.py:103:        return {'ok': False, 'error': 'reserved task mismatch', 'state': B.RELEASED}
./omni_prod/intake/reservation_worker.py:107:        svc.release(r.id, reason=f'no model route: {type(exc).__name__}')
./omni_prod/intake/reservation_worker.py:108:        return {'ok': False, 'error': 'no model route', 'state': B.RELEASED}
./omni_prod/intake/reservation_worker.py:109:    if not svc.mark_executing(r, lease_seconds=lease_seconds):
./omni_prod/intake/reservation_worker.py:110:        return {'ok': False, 'error': 'lease lost before execution'}
./omni_prod/intake/reservation_worker.py:148:    maintain = relay pending outbox rows, then reconcile expired leases (one pass each loop)."""
./omni_prod/intake/worker_route.py:83:                self.svc.release(r.id, reason=f'enqueue failed: {type(exc).__name__}')
./omni_prod/intake/worker_route.py:89:        while current is not None and current.state not in (B.SETTLED, B.UNKNOWN, B.RELEASED) and \
./omni_prod/intake/worker_route.py:94:        if current is None or current.state not in (B.SETTLED, B.UNKNOWN, B.RELEASED):
./omni_prod/intake/worker_route.py:98:        if current.state == B.RELEASED:
./omni_prod/intake/worker_route.py:99:            base.dropped.append('model not used: ' + (current.failure_reason or 'released'))
./omni_prod/international_engine.py:12:    release_ready: bool
./omni_prod/international_engine.py:15:    """Release-gated wrapper around the autonomous core.
./omni_prod/international_engine.py:17:    A build is not considered release-ready merely because acceptance tests pass.
./omni_prod/investor_app.py:34:from .native_source import android_project, ios_project, game_project, omni_android_release_project
./omni_prod/investor_app.py:504:class V27ReleaseCouncilRequest(BaseModel):
./omni_prod/investor_app.py:574:    # version is retained for V23 API-client compatibility; product_release is canonical.
./omni_prod/investor_app.py:576:        'product':'148AI','brand_domain':'148ailabs.com','tagline':'Build Anything.','version':'V23 Investor-Grade Prelaunch','product_release':'V24 International Readiness','current_release':'V25 Unified Core','universal_release':'V26 Universal Pro Reviewer Release','rights_release':'V27 Rights & Company OS','launch_candidate':'V28 148AI Launch Candidate',
./omni_prod/investor_app.py:580:            'quality/security release gate','local-first multi-model routing','project memory/versioning','teams/RBAC',
./omni_prod/investor_app.py:582:            'PostgreSQL/Redis/S3 production adapters','release integrity/observability/recovery',
./omni_prod/investor_app.py:704:    # Quality shortfalls are repairable like failed checks (release gate uses
./omni_prod/investor_app.py:788:    return {'mode':'live-autonomous','status':result.status,'release_ready':result.status=='ready' and quality.passed and security.passed and not review_blocked,
./omni_prod/investor_app.py:901:    return {'mode':'v26-live-autonomous','status':result.status,'release_ready':result.status=='ready' and quality.passed and security.passed,
./omni_prod/investor_app.py:908:    return {'release':'V26 Universal Pro','creator_security':['signup/login','PBKDF2 password hashing','signed session tokens','owner-scoped project IDs','cross-user denial'],
./omni_prod/investor_app.py:965:        'release':'V25 Unified Core',
./omni_prod/investor_app.py:999:    repo=omni_android_release_project()
./omni_prod/investor_app.py:1205:@app.post('/api/v27/company-os/release-council/evaluate')
./omni_prod/investor_app.py:1206:def v27_release_council_evaluate(req:V27ReleaseCouncilRequest)->dict:
./omni_prod/investor_app.py:1207:    return _v27.company_os.evaluate_release(req.gates,founder_public_launch_approved=req.founder_public_launch_approved)
./omni_prod/investor_app.py:1231:            'release_ready':result.status=='ready' and quality.passed and security.passed and assessment.publish_allowed,
./omni_prod/investor_app.py:2474:    cancelled at once and its reservation released; a running build stops at
./omni_prod/investor_app.py:2491:        _v28.subscriptions.release(build_id=build_id)
./omni_prod/investor_app.py:2530:        'release_eligible': bool(preview['status'] == 'RUNNING' and acceptance
./omni_prod/investor_app.py:2532:                                 and acceptance.get('release_eligible') is True),
./omni_prod/investor_app.py:2800:        _v28.subscriptions.release(build_id=modification_id)
./omni_prod/investor_app.py:3276:        'release_ready': result.status == 'ready' and quality.passed and security.passed and rights.publish_allowed,
./omni_prod/job_repository.py:411:        """Heartbeat (crash recovery, migration 033) + stop flag in one round trip."""
./omni_prod/job_repository.py:415:                    cur.execute("UPDATE build_jobs SET heartbeat_at = now() WHERE id = %s "
./omni_prod/launch_readiness_v28.py:24:        'release':'V28 148AI Launch Candidate',
./omni_prod/launch_readiness_v28.py:33:        'truth': 'Configuration presence is not live verification. Public launch remains blocked until external integrations are harmlessly tested, domain/trademark gates are cleared, and the founder approves release.',
./omni_prod/maintenance.py:12:   FAILED with error `worker_lost`, and their reservation is released.
./omni_prod/maintenance.py:24:   worker heartbeat (written at every step boundary) is older than
./omni_prod/maintenance.py:28:   after that. Reservations are released for anything that ends.
./omni_prod/maintenance.py:73:                      'provider exposure must be reconciled before funds can be released',
./omni_prod/maintenance.py:74:        evidence_json={'billing': 'exposure_checked_release', 'reaped_by': 'maintenance', 'stale_minutes': minutes})
./omni_prod/maintenance.py:76:        subscriptions.release(build_id=build_id)
./omni_prod/maintenance.py:121:              "AND heartbeat_at IS NOT NULL AND heartbeat_at < now() - make_interval(mins => %s) LIMIT 20"),
./omni_prod/maintenance.py:123:                     "WHERE status = 'RUNNING' AND heartbeat_at IS NOT NULL "
./omni_prod/maintenance.py:124:                     "AND heartbeat_at < now() - make_interval(mins => %s) LIMIT 20"),
./omni_prod/maintenance.py:133:    'build': ("UPDATE build_jobs SET status = 'queued', phase = 'RECOVERING', heartbeat_at = NULL, "
./omni_prod/maintenance.py:135:              "AND heartbeat_at < now() - make_interval(mins => %s)"),
./omni_prod/maintenance.py:136:    'modification': ("UPDATE modification_requests SET status = 'QUEUED', heartbeat_at = NULL, "
./omni_prod/maintenance.py:138:                     "AND heartbeat_at < now() - make_interval(mins => %s)"),
./omni_prod/maintenance.py:159:                                           'WHERE id=%s AND status=%s AND heartbeat_at IS NOT NULL '
./omni_prod/maintenance.py:160:                                           'AND heartbeat_at < now() - make_interval(mins => %s) FOR UPDATE',
./omni_prod/maintenance.py:182:                                    'the reservation was released')
./omni_prod/maintenance.py:193:                subscriptions.release(build_id=item)
./omni_prod/migrate.py:7:--accept-newer (or OMNI_ACCEPT_NEWER_MIGRATIONS) names the exact versions a NEWER release already applied. Only those
./omni_prod/migrations.py:52:    `accept_newer` is the ONLY exception, used to run an OLDER package against a database that a newer release already
./omni_prod/migration_runner.py:11:# Same definition as infra/postgres/005_release_engineering.sql. Migrations
./omni_prod/migration_runner.py:46:    BEGIN/COMMIT destroys that savepoint -- failing on RELEASE with
./omni_prod/mobile_pipeline.py:20:        cmd=(('./gradlew','bundleRelease'),) if f in {'native','react-native'} else (('flutter','build','appbundle','--release'),)
./omni_prod/mobile_pipeline.py:23:        cmd=(('xcodebuild','-scheme','OmniApp','-configuration','Release','archive'),) if f in {'native','react-native'} else (('flutter','build','ipa','--release'),)
./omni_prod/modification_engine.py:96:        gates `worker_tasks.evaluate_release_gates` already applies to a
./omni_prod/native_source.py:14:        'app/build.gradle.kts':f'''plugins {{ id("com.android.application"); id("org.jetbrains.kotlin.android") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n buildTypes {{ release {{ isMinifyEnabled=false; signingConfig = signingConfigs.findByName("release") }} }} }}\n''',
./omni_prod/native_source.py:18:        '.github/workflows/android.yml':'name: android\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-java@v4\n        with: {distribution: temurin, java-version: "17"}\n      - uses: gradle/actions/setup-gradle@v4\n      - run: ./gradlew bundleRelease\n',
./omni_prod/native_source.py:19:        'README.md':'# Android source\nGenerated source. Release signing secrets must be injected by CI; never commit a keystore or passwords.\n',
./omni_prod/native_source.py:57:def omni_android_release_project() -> dict[str, str]:
./omni_prod/native_source.py:60:    Mirrors the V10 release contract while keeping signing material external.
./omni_prod/native_source.py:68:        'app/build.gradle.kts': f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{\n   val ks=System.getenv("OMNI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks)\n   storePassword=System.getenv("OMNI_ANDROID_STORE_PASSWORD")\n   keyAlias=System.getenv("OMNI_ANDROID_KEY_ALIAS")\n   keyPassword=System.getenv("OMNI_ANDROID_KEY_PASSWORD")\n }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
./omni_prod/native_source.py:74:    out['.github/workflows/omni-android-aab.yml'] = '''name: omni-android-aab\non: [workflow_dispatch]\njobs:\n  aab:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-java@v4\n        with: {distribution: temurin, java-version: "17"}\n      - uses: gradle/actions/setup-gradle@v4\n        with: {gradle-version: "8.9"}\n      - run: cd omni-android && gradle bundleRelease\n        env:\n          OMNI_ANDROID_KEYSTORE: ${{ secrets.OMNI_ANDROID_KEYSTORE }}\n          OMNI_ANDROID_STORE_PASSWORD: ${{ secrets.OMNI_ANDROID_STORE_PASSWORD }}\n          OMNI_ANDROID_KEY_ALIAS: ${{ secrets.OMNI_ANDROID_KEY_ALIAS }}\n          OMNI_ANDROID_KEY_PASSWORD: ${{ secrets.OMNI_ANDROID_KEY_PASSWORD }}\n'''
./omni_prod/planning/architect.py:109:        _t('T11', 'security_scan', 'security_agent', ('secret_detection', 'security_release_gate'), ('T04',), 'security',
./omni_prod/planning/architect.py:116:        _t('T12', 'release_gate', 'quality_gate_agent', ('release_gate', 'security_release_gate'),
./omni_prod/planning/architect.py:118:           accept=('every mandatory check PASS; NOT_RUN/UNKNOWN block',), verify='release policy (platform-owned, independent)',
./omni_prod/planning/architect.py:120:        _t('T13', 'version_release', 'release_agent', ('version_create', 'release_gate'), ('T12',), 'release',
./omni_prod/planning/architect.py:142:           gap=f'no execution engine for {fam} in this release'),
./omni_prod/planning/architect.py:184:                             'one repository, preview runtime') if fam in EXECUTABLE else f'{fam}: not executable in this release',
./omni_prod/planning/architect.py:201:                                 'browser flow', 'visual QA desktop + mobile', 'static security scan', 'release policy'],
./omni_prod/planning/architect.py:208:            'milestones': ['requirements approved', 'code generated', 'tests pass', 'preview verified', 'version released'],
./omni_prod/planning/architect.py:221:                'preview': ({'required': True, 'kind': 'private running preview of the released version',
./omni_prod/planning/architect.py:224:                             'decided_by': 'release policy (quality-report/1): NOT_RUN/UNKNOWN block READY'}
./omni_prod/planning/architect.py:225:                            if fam in EXECUTABLE else {'required': False, 'reason': f'{fam} is not executable in this release'}),
./omni_prod/planning/feasibility.py:29:               'visual QA', 'release policy')
./omni_prod/planning/feasibility.py:98:                         'the reviewing model may be the same provider as the author; deterministic checks still gate release'))
./omni_prod/postdeploy_checks.py:23:                both reservations RELEASED, journal readable incrementally.
./omni_prod/postdeploy_checks.py:483:           and (res or {}).get('status') == 'RELEASED', f'api={s} {out} row={row} reservation={res}')
./omni_prod/postdeploy_checks.py:507:           and row[0] == '0' and row[1] == 'released' and row[3] and (res or {}).get('status') == 'RELEASED',
./omni_prod/postdeploy_checks.py:546:    record('cost settlement', res is not None and res['status'] in ('SETTLED', 'RELEASED'),
./omni_prod/postdeploy_checks.py:556:    record_agent_graph(b, 'ready', ('coding_agent', 'qa_agent', 'release_agent', 'quality_gate_agent'))
./omni_prod/preview_repository.py:220:        return None and therefore remain release-ineligible.
./omni_prod/preview_repository.py:276:    def release_eligible(self, preview_id: str, project_id: str) -> bool:
./omni_prod/preview_repository.py:281:        return bool(acceptance and acceptance.get('status') == 'PASS' and acceptance.get('release_eligible') is True)
./omni_prod/preview_runtime.py:172:    never become release-eligible through M5 Task 11.  Malformed plans fail
./omni_prod/preview_runtime.py:223:    bind-then-release TOCTOU), read back with `docker port` -- while
./omni_prod/preview_runtime.py:479:                # port bindings released, so `docker port` fails with "no
./omni_prod/preview_smoke.py:103:        # What the last run did (release policy: NOT_RUN is not PASS).
./omni_prod/product_architect.py:261:        defaults = tuple(role_defaults + static_default + [profile.key, "vercel_release_target"])
./omni_prod/product_architect.py:284:            "release_target": "vercel",
./omni_prod/product_architect.py:314:            release_target="vercel",
./omni_prod/product_architect.py:350:            Requirement("platform-deploy", "Verified immutable release can be deployed separately from preview", "deployment"),
./omni_prod/product_architect.py:416:            Requirement("platform-deploy", "Verified immutable release can be deployed separately from preview", "deployment"),
./omni_prod/qa_budget.py:107:                   WHEN r.status IN ('SETTLED', 'RELEASED') THEN COALESCE(
./omni_prod/qa_budget.py:111:                        CASE WHEN r.status = 'RELEASED' THEN 0 ELSE r.estimated_provider_cost_usd END)
./omni_prod/qa_budget.py:156:    transaction-scoped and released at the end). Raises QABudgetDenied exactly
./omni_prod/quality_gate.py:159:    """A verification pass that also meets the quality bar the release gate
./omni_prod/recovery_simulation.py:5:from .worker_lease import renew, can_claim
./omni_prod/recovery_simulation.py:27:    lease = renew(owner="w1", now=0, ttl_seconds=10)
./omni_prod/recovery_simulation.py:28:    assert not can_claim(lease, now=5, owner="w2")
./omni_prod/recovery_simulation.py:29:    assert can_claim(lease, now=11, owner="w2")
./omni_prod/recovery_simulation.py:39:        "lease_recovered": True,
./omni_prod/redis_circuit_breaker.py:20:    integration testing before production release.
./omni_prod/rehearsal.py:6:the same quality gate the release uses. Writes nothing to the database, opens
./omni_prod/release_gate.py:5:from .release_manifest import verify_release_manifest
./omni_prod/release_gate.py:14:def evaluate_release_gate(root: str | Path) -> GateResult:
./omni_prod/release_gate.py:35:    # Release manifest
./omni_prod/release_gate.py:36:    manifest_ok, manifest_errors = verify_release_manifest(base)
./omni_prod/release_gate.py:37:    checks["release_manifest_valid"] = manifest_ok
./omni_prod/release_manifest.py:15:def build_release_manifest(
./omni_prod/release_manifest.py:31:        if rel == "RELEASE-MANIFEST.json":
./omni_prod/release_manifest.py:44:def write_release_manifest(root: str | Path, *, version: str, test_count: int) -> Path:
./omni_prod/release_manifest.py:46:    manifest = build_release_manifest(base, version=version, test_count=test_count)
./omni_prod/release_manifest.py:47:    path = base / "RELEASE-MANIFEST.json"
./omni_prod/release_manifest.py:51:def verify_release_manifest(root: str | Path) -> tuple[bool, list[str]]:
./omni_prod/release_manifest.py:53:    manifest_path = base / "RELEASE-MANIFEST.json"
./omni_prod/release_manifest.py:55:        return False, ["RELEASE-MANIFEST.json missing"]
./omni_prod/release_manifest.py:69:    current = build_release_manifest(
./omni_prod/release_policy.py:1:"""Release policy: READY only when every mandatory check PASSED (directive
./omni_prod/release_policy.py:25:POLICY_VERSION = 'release-policy/1'
./omni_prod/release_policy.py:31:          'visual', 'quality', 'security', 'review', 'rights', 'capabilities', 'release')
./omni_prod/release_policy.py:126:              'platform:release_policy', True, 'critical',
./omni_prod/release_policy.py:180:        add(Check('acceptance', 'approved_criteria_covered', ap_status, True, 'platform:release_policy', True,
./omni_prod/release_policy.py:221:                  'platform:release_policy', True, 'medium',
./omni_prod/release_policy.py:232:    mode = os.getenv('OMNI_RELEASE_POLICY', 'enforce').strip().lower()
./omni_prod/release_policy.py:240:    return ('release policy: mandatory checks not passed: ' + '; '.join(parts))[:2000]
./omni_prod/routed_gateway.py:211:                self._release_rejected(route, record)
./omni_prod/routed_gateway.py:244:        release = route.max_estimated_cost_usd - metered
./omni_prod/routed_gateway.py:245:        if release > 0:
./omni_prod/routed_gateway.py:246:            self.state.external_spend_usd -= release
./omni_prod/routed_gateway.py:248:    def _release_rejected(self, route: ProviderRoute, record: AttemptRecord) -> None:
./omni_prod/routed_gateway.py:254:        Timeouts and dropped connections are NOT released: those requests may
./omni_prod/runtime_bindings.py:151:    Binding('security_reviewer', ('omni_prod.security_testing:hostile_repository_scan', 'omni_prod.worker_tasks:evaluate_release_gates'),
./omni_prod/runtime_bindings.py:153:            verified_scope=('static hostile-pattern scan gates release',)),
./omni_prod/runtime_bindings.py:175:    Binding('release_change_coordinator',
./omni_prod/skills_registry.py:180:        # Release-record scaffolding only; no generated-app deployment runs yet
./omni_prod/skills_registry.py:233:    _internal_skill("skill.internal.security_review", "Perform security review and release gating", CapabilityStatus.PARTIAL, "omni_prod/security_testing.py"),
./omni_prod/skills_registry.py:234:    _internal_skill("skill.internal.compliance_review", "Apply domain/legal/compliance release gates", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/rights_ip.py"),
./omni_prod/skills_registry.py:236:    _internal_skill("skill.internal.release.gate", "Aggregate release evidence and block false readiness", CapabilityStatus.PARTIAL, "omni_prod/release_gate.py"),
./omni_prod/skill_catalog.py:166:       'janitor releases reservations of lost builds; nothing else'),
./omni_prod/skill_catalog.py:197:    _s('release.prepare', 'delivery', WORKFLOW, (), (), (), _NI),
./omni_prod/skill_catalog.py:198:    _s('deployment.publish', 'delivery', EXECUTABLE, (), ('release.prepare',), (), _NI + ' (promote is in memory only)'),
./omni_prod/subscription_store.py:110:                    # Period renewal is separate from entitlement assignment.
./omni_prod/subscription_store.py:167:    # Additive (reserve/settle/release do not replace authorize/consume, which
./omni_prod/subscription_store.py:180:    # the caller. Everything else in reserve/settle/release is unchanged from
./omni_prod/subscription_store.py:402:    def release(self, *, build_id: str) -> None:
./omni_prod/subscription_store.py:418:                    cur.execute("UPDATE credit_reservations SET status='RELEASED', resolved_at=now() WHERE build_id=%s", (build_id,))
./omni_prod/truth_lock.py:170:M4.95 treats cost as release-critical evidence, not a cosmetic estimate.
./omni_prod/truth_lock.py:182:`local versioned price catalog -> conservative maximum quote -> durable reserve -> optional live quote validation -> provider execution -> measured usage -> actual settlement/release`
./omni_prod/unified_engine.py:156:            'docs/ARCHITECTURE.md': '# Architecture\nFrontend, API, runtime auth, persistence, realtime and release boundaries.\n',
./omni_prod/unified_engine.py:165:            'ci/README.md': '# CI\nRun tests, security scan, SBOM, build and release gates.\n',
./omni_prod/v27_platform.py:179:            'release_council': self.company_os.release_council(),
./omni_prod/verification_contract.py:4:(build release policy, post-deployment smoke, replay). Rules:
./omni_prod/verification_contract.py:20:Check statuses reuse release_policy's vocabulary (PASS, FAIL, NOT_RUN, UNKNOWN,
./omni_prod/verification_contract.py:230:    """Map a release_policy quality-report/1 dict onto the canonical contract.
./omni_prod/verification_contract.py:231:    release-policy/1 treats a required NOT_APPLICABLE check as non-blocking;
./omni_prod/verification_contract.py:244:                              suites={'release_policy': report.get('policy_version', '?')},
./omni_prod/web_saas_acceptance.py:162:    release_eligible: bool
./omni_prod/web_saas_acceptance.py:180:            'status': self.status, 'release_eligible': self.release_eligible, 'summary': self.summary,
./omni_prod/web_saas_acceptance.py:287:            status='PASS' if passed else 'FAIL', release_eligible=passed, summary=summary,
./omni_prod/web_saas_acceptance.py:296:            status='FAIL', release_eligible=False, summary=summary, checks=(),
./omni_prod/worker.py:14:  wait cycle (heartbeat + BLMOVE), ~86K per month at the default 120 s.
./omni_prod/worker_health.py:6:class WorkerHeartbeat:
./omni_prod/worker_health.py:10:def is_stale(heartbeat: WorkerHeartbeat, *, now: datetime, max_age_seconds: int) -> bool:
./omni_prod/worker_health.py:13:    if heartbeat.seen_at.tzinfo is None or now.tzinfo is None:
./omni_prod/worker_health.py:15:    return now - heartbeat.seen_at > timedelta(seconds=max_age_seconds)
./omni_prod/worker_lease.py:5:class Lease:
./omni_prod/worker_lease.py:9:def can_claim(lease: Lease | None, *, now: float, owner: str) -> bool:
./omni_prod/worker_lease.py:12:    if lease is None:
./omni_prod/worker_lease.py:14:    if lease.owner == owner:
./omni_prod/worker_lease.py:16:    return now >= lease.expires_at
./omni_prod/worker_lease.py:18:def renew(*, owner: str, now: float, ttl_seconds: float) -> Lease:
./omni_prod/worker_lease.py:23:    return Lease(owner=owner, expires_at=now + ttl_seconds)
./omni_prod/worker_tasks.py:19:* Billing. Failures no longer blindly `release()`. The directive refers to a
./omni_prod/worker_tasks.py:29:  FAILED with no external spend -> release().
./omni_prod/worker_tasks.py:36:  release readiness as verification AND `assess_repository` AND
./omni_prod/worker_tasks.py:211:        from .release_policy import persist
./omni_prod/worker_tasks.py:217:def release_quality_report(build_id, engine, gateway, result, quality, security, rights):
./omni_prod/worker_tasks.py:220:    from .release_policy import build_report
./omni_prod/worker_tasks.py:237:        logging.getLogger(__name__).exception('release policy report failed for %s', build_id)
./omni_prod/worker_tasks.py:259:               'is released to zero: it was not served and is not billed')
./omni_prod/worker_tasks.py:337:    READY); release() only when a failed build incurred no external spend."""
./omni_prod/worker_tasks.py:341:    subscriptions.release(build_id=build_id)
./omni_prod/worker_tasks.py:342:    return 'released'
./omni_prod/worker_tasks.py:465:        subscriptions.release(build_id=build_id)
./omni_prod/worker_tasks.py:466:        return 'released', {'action': 'released'}, None
./omni_prod/worker_tasks.py:510:def evaluate_release_gates(*, result, quality, security, rights) -> tuple[bool, str | None, str | None]:
./omni_prod/worker_tasks.py:579:    if callable(beat):  # crash recovery: the heartbeat starts at the claim
./omni_prod/worker_tasks.py:583:            logging.getLogger(__name__).warning('first heartbeat failed for %s', build_id, exc_info=True)
./omni_prod/worker_tasks.py:684:        core_ready, error_code, error_message = evaluate_release_gates(
./omni_prod/worker_tasks.py:686:        # Release policy (directive 2026-10-10): a check that did not run is not
./omni_prod/worker_tasks.py:688:        quality_report = release_quality_report(build_id, engine, gateway, result, quality, security, rights)
./omni_prod/worker_tasks.py:691:            from .release_policy import enforcement_mode, explain
./omni_prod/worker_tasks.py:695:                        False, 'release_policy_unavailable',
./omni_prod/worker_tasks.py:696:                        'release policy: required quality report could not be generated')
./omni_prod/worker_tasks.py:698:                    core_ready, error_code, error_message = False, 'release_policy_failed', explain(quality_report)
./omni_prod/worker_tasks.py:764:            'release_ready': ready,
./omni_prod/worker_tasks.py:1037:        # the build (and releases its credits) instead of leaving it QUEUED
./omni_prod/worker_tasks.py:1058:# evaluate_release_gates(), and the candidate this produces is deliberately
./omni_prod/worker_tasks.py:1080:    subscriptions.release(build_id=modification_id)
./omni_prod/worker_tasks.py:1081:    return 'released'
./omni_prod/worker_tasks.py:1132:        # log, like a build (heartbeat at every step boundary).
./omni_prod/worker_tasks.py:1341:        # M5 Task 11: process health and release readiness are deliberately
./omni_prod/worker_tasks.py:1343:        # behavioral acceptance fails; only a PASS report is release-eligible.
./omni_prod/worker_tasks.py:1350:                    status='ERROR', release_eligible=False, summary=summary, checks=(),
./omni_prod/worker_tasks.py:1401:                            report, status='FAIL', release_eligible=False,
./omni_prod/__init__.py:1:__all__ = ['config', 'db', 'queueing', 'storage', 'sandbox', 'health', 'models', 'build_state', 'job_repository', 'deployments', 'usage', 'provenance', 'api_routes', 'idempotency', 'limits', 'model_router', 'rollback', 'worker_health', 'artifact_keys', 'build_budget', 'canary', 'error_taxonomy', 'orchestrator', 'repair_loop', 'retry', 'memory_adapters', 'secret_redaction', 'acceptance_pipeline', 'migrations', 'audit', 'secret_scan', 'canary_controller', 'release_manifest', 'release_gate', 'staging_simulation', 'preflight', 'migration_runner', 'artifact_integrity', 'dependency_inventory', 'sbom', 'cors_policy', 'web_security', 'attestation', 'circuit_breaker', 'outbox', 'worker_lease', 'dead_letter', 'recovery_simulation', 'request_id', 'metrics', 'slo', 'backup_manifest', 'structured_event', 'observability', 'recovery_drill', 'production_adapters', 'redis_circuit_breaker', 'model_gateway', 'model_policy', 'product_spec', 'repository_patch', 'change_policy', 'autonomous_agents', 'autonomous_core', 'modifier_engine', 'model_runtime_config', 'project_manifest', 'sandbox_executor']
./scripts/run_quality_gate.py:12:from omni_prod.release_manifest import verify_release_manifest
./scripts/run_quality_gate.py:27:manifest_ok, errors = verify_release_manifest(root)
./scripts/run_quality_gate.py:28:checks['release_manifest'] = {'ok': manifest_ok, 'errors': errors}
./scripts/run_v25_release_gate.py:8:from omni_prod.release_manifest import verify_release_manifest
./scripts/run_v25_release_gate.py:29:manifest_ok,errors=verify_release_manifest(ROOT)
./scripts/run_v25_release_gate.py:30:ok &= check('release_manifest',manifest_ok,'; '.join(errors[:20]))
./scripts/run_v25_release_gate.py:33:payload={'ok':bool(ok),'release':'V25 Unified Core','checks':checks}
./scripts/run_v26_release_gate.py:8:from omni_prod.release_manifest import verify_release_manifest
./scripts/run_v26_release_gate.py:23:manifest_ok,errors=verify_release_manifest(ROOT);ok &= check('release_manifest',manifest_ok,'; '.join(errors[:20]))
./scripts/run_v26_release_gate.py:25:print(json.dumps({'ok':bool(ok),'release':'V26 Universal Pro Reviewer Release','checks':checks},indent=2))
./scripts/run_v27_release_gate.py:8:from omni_prod.release_manifest import verify_release_manifest
./scripts/run_v27_release_gate.py:31:manifest_ok,errors=verify_release_manifest(ROOT);ok &= check('release_manifest',manifest_ok,'; '.join(errors[:20]))
./scripts/run_v27_release_gate.py:37:print(json.dumps({'ok':bool(ok),'release':'V27 Rights & Company OS Reviewer Release','checks':checks},indent=2))
./scripts/run_v28_release_gate.py:10:from omni_prod.release_manifest import verify_release_manifest
./scripts/run_v28_release_gate.py:88:manifest_ok, errors = verify_release_manifest(ROOT)
./scripts/run_v28_release_gate.py:89:ok &= check('release_manifest', manifest_ok, '; '.join(errors[:30]))
./scripts/run_v28_release_gate.py:110:payload = {'ok': bool(ok), 'release': '148AI V28 Launch Candidate Reviewer', 'checks': checks}
./tests/financial_fault_harness.py:210:                conn.execute("UPDATE build_jobs SET heartbeat_at=now()-interval '20 minutes' WHERE id=%s AND status='running'", (build_id,))
./tests/financial_fault_harness.py:233:        expected_held = (Decimal('0') if status == 'RELEASED' else
./tests/financial_fault_harness.py:235:        expected_credits = 0 if status == 'RELEASED' else reserved_credits
./tests/financial_fault_harness.py:238:                  'reservation_not_released_as_free': cost == 0 or status != 'RELEASED',
./tests/integration/test_financial_fault_experiment.py:27:    assert result['final']['reservation'][0] == ('RELEASED' if fail_ledger else 'RESERVED')
./tests/integration/test_financial_fault_experiment.py:34:def test_recovery_rechecks_heartbeat_after_candidate_scan(monkeypatch):
./tests/integration/test_financial_fault_experiment.py:42:    bid = 'bld_fault_heartbeat_' + uuid.uuid4().hex[:12]
./tests/integration/test_financial_fault_experiment.py:44:        conn.execute("INSERT INTO build_jobs(id, project_id, status, started_at, heartbeat_at) "
./tests/integration/test_financial_fault_experiment.py:61:                            with pool.connection() as heartbeat:
./tests/integration/test_financial_fault_experiment.py:62:                                heartbeat.execute("UPDATE build_jobs SET heartbeat_at=now() WHERE id=%s", (bid,))
./tests/integration/test_financial_fault_experiment.py:75:        subs.release.assert_not_called()
./tests/m5_worker_harness.py:82:            # release policy: the checks of the chain ran and passed
./tests/policy_fixtures.py:2:having RUN and PASSED (release policy: a check that did not run is not a pass).
./tests/test_actual_cost_settlement.py:56:    def test_metered_actual_is_settled_and_the_rest_released(self):
./tests/test_actual_cost_settlement.py:94:    def test_spend_by_a_lost_worker_is_settled_not_released(self):
./tests/test_actual_cost_settlement.py:104:        subs.release.assert_not_called()
./tests/test_agent_os.py:93:            VerificationEngine.check('coding_agent', 'release_agent')   # must be review or the release policy
./tests/test_agent_os.py:175:        self.assertEqual(self.rt.get(qa)['state'], 'READY')         # dependency released it
./tests/test_agent_os.py:234:                                             'quality_report': {'decision': 'READY', 'policy_version': 'release-policy/1'}})
./tests/test_agent_os.py:238:                      'code_review_agent', 'browser_rehearsal_agent', 'behavioral_acceptance_agent', 'release_agent',
./tests/test_agent_os.py:243:        # Verified by the independent release policy, not by tests the repair agent wrote.
./tests/test_build_cancel_and_log.py:112:    def test_stop_before_any_paid_call_releases_the_reservation(self):
./tests/test_build_cancel_and_log.py:117:        h.subs.release.assert_called_once_with(build_id='bld_1')
./tests/test_build_state_machine.py:64:                                             error_code='release_policy_failed'))
./tests/test_conversation_os.py:205:                                                                     'release', 'cost'}
./tests/test_conversation_os.py:352:            sup.turn(project_id='p2', account_id='a', message='blue please')
./tests/test_conversation_os.py:488:        self.assertIsNotNone(coding['verified_by_task'])                       # verified by the release gate
./tests/test_crash_recovery_and_change_parity.py:18:                            "AND column_name='heartbeat_at'").fetchone()
./tests/test_crash_recovery_and_change_parity.py:38:                c.execute("INSERT INTO build_jobs(id, project_id, status, started_at, heartbeat_at, recovery_attempts, "
./tests/test_crash_recovery_and_change_parity.py:58:        # the second loss ends it and releases the reservation
./tests/test_crash_recovery_and_change_parity.py:61:                c.execute("UPDATE build_jobs SET status='running', heartbeat_at = now() - interval '20 minutes' WHERE id=%s", (bid,))
./tests/test_crash_recovery_and_change_parity.py:65:        self.subs.release.assert_called_with(build_id=bid)
./tests/test_crash_recovery_and_change_parity.py:72:    def test_fresh_heartbeat_or_live_worker_is_left_alone(self):
./tests/test_crash_recovery_and_change_parity.py:124:                c.execute("UPDATE modification_requests SET heartbeat_at = now() - interval '20 minutes' WHERE id=%s", (m,))
./tests/test_customer_economics_views.py:31:    "release_ready": True,
./tests/test_dependency_policy.py:134:    def test_release_gate_reports_unsupported_dependency(self):
./tests/test_dependency_policy.py:135:        from omni_prod.worker_tasks import evaluate_release_gates
./tests/test_dependency_policy.py:137:        ok, code, message = evaluate_release_gates(result=SimpleNamespace(status="failed", report=report),
./tests/test_deployment_verification.py:4:deployment smoke red -> release stays blocked) run against a local HTTP stub
./tests/test_deployment_verification.py:19:from omni_prod import release_policy as rp
./tests/test_deployment_verification.py:116:        # the canonical verdict agrees with the release policy decision
./tests/test_deployment_verification.py:234:        self.assertEqual(rep['decision'], 'READY')                                      # release-policy/1 view
./tests/test_evidence_json.py:22:    'billing': 'released',
./tests/test_evidence_json.py:23:    'economics_settlement': {'action': 'released', 'settled_provider_cost_usd': Decimal('0')},
./tests/test_evidence_json.py:94:        self.assertEqual(json.loads(evidence_param)['billing'], 'released')
./tests/test_failure_injection.py:36:    def test_429_is_released_and_the_route_is_skipped(self):
./tests/test_golden_mod_path_live_postgres.py:282:                                                    {'status': 'PASS', 'release_eligible': True}), build_id)
./tests/test_intake_budget_pg.py:235:        """reserve / claim / execute / settle / release / reconcile interleaved."""
./tests/test_intake_budget_pg.py:246:            action = rng.choice(['settle', 'settle_unknown', 'release', 'zero', 'execute_only'])
./tests/test_intake_budget_pg.py:247:            if action == 'release':
./tests/test_intake_budget_pg.py:248:                return self.svc.release(c.id, reason='test') and 'released'
./tests/test_intake_budget_pg.py:267:        recomputed = sum((Decimal(0) if s == 'RELEASED' else (a if s == 'SETTLED' else q)) for s, q, a in rows)
./tests/test_intake_budget_pg.py:361:    def test_unknown_requires_null_amount_reason_and_evidence_to_release(self):
./tests/test_intake_budget_pg.py:371:        self.assertFalse(self.svc.release(r.id, reason='try'))                   # cannot silently release
./tests/test_intake_budget_pg.py:381:    def test_worker_crash_before_provider_releases_after_provider_holds(self):
./tests/test_intake_budget_pg.py:382:        before = self.svc.claim(self.reserve(project='crash').id, worker_id='w', lease_seconds=1)
./tests/test_intake_budget_pg.py:383:        during = self.svc.claim(self.reserve(project='crash').id, worker_id='w', lease_seconds=1)
./tests/test_intake_budget_pg.py:384:        self.svc.mark_executing(during, lease_seconds=1)            # crash after the write-ahead marker
./tests/test_intake_budget_pg.py:387:        self.assertIn(before.id, out['released'])                   # provider certainly not contacted
./tests/test_intake_budget_pg.py:392:        self.assertEqual(self.svc.reconcile(), {'unknown': [], 'released': []})   # idempotent
./tests/test_intake_budget_pg.py:393:        # a late worker cannot resume an expired lease
./tests/test_intake_budget_pg.py:447:    def test_stale_reserved_is_released_and_late_claim_refused(self):
./tests/test_intake_budget_pg.py:451:        self.assertEqual(self.svc.get(r.id).state, B.RELEASED)
./tests/test_intake_complexity.py:97:    ('כןןן', 'approval', 'RISKY'), ('כֵּן', 'approval', 'RISKY'), ('yes please', 'pay_q', 'RISKY'),
./tests/test_intake_worker_route.py:31:        self.released, self.enqueued, self.reserved = [], [], []
./tests/test_intake_worker_route.py:43:    def release(self, rid, *, reason):
./tests/test_intake_worker_route.py:44:        self.released.append((rid, reason))
./tests/test_intake_worker_route.py:89:    def test_enqueue_failure_releases_immediately(self):
./tests/test_intake_worker_route.py:94:        self.assertEqual(svc.released[0][0], 'irs_1')
./tests/test_m3_preview_logic.py:8:machine, the build worker's gate ordering and settle-vs-release billing, the
./tests/test_m3_preview_logic.py:862:            (False, Decimal('0'), 0, 'released', None),
./tests/test_m3_preview_logic.py:871:                    subs.release.assert_not_called()
./tests/test_m3_preview_logic.py:873:                    subs.release.assert_called_once_with(build_id='b')
./tests/test_m3_preview_logic.py:925:        self.engine.executor = verified_chain()  # release policy: checks ran and passed
./tests/test_m3_preview_logic.py:959:        h.subs.release.assert_not_called()
./tests/test_m3_preview_logic.py:962:        self.assertTrue(ev['release_ready'])
./tests/test_m3_preview_logic.py:993:                self.assertFalse(h.final['evidence_json']['release_ready'])
./tests/test_m3_preview_logic.py:1004:    def test_failed_build_without_external_spend_releases(self):
./tests/test_m3_preview_logic.py:1007:        h.subs.release.assert_called_once_with(build_id='bld_1')
./tests/test_m3_preview_logic.py:1009:        self.assertEqual(h.final['evidence_json']['billing'], 'released')
./tests/test_m3_preview_logic.py:1011:    def test_failed_build_with_external_spend_settles_not_releases(self):
./tests/test_m3_preview_logic.py:1015:        h.subs.release.assert_not_called()
./tests/test_m3_preview_logic.py:1024:        h.subs.release.assert_not_called()
./tests/test_m3_preview_logic.py:1026:    def test_exception_before_any_spend_releases_and_reraises(self):
./tests/test_m3_preview_logic.py:1030:        h.subs.release.assert_called_once_with(build_id='bld_1')
./tests/test_m3_preview_logic.py:1034:    def test_memory_workspace_worker_fails_build_and_releases(self):
./tests/test_m3_preview_logic.py:1040:        h.subs.release.assert_called_once()
./tests/test_m3_preview_logic.py:1049:        h.subs.release.assert_not_called()
./tests/test_m495_capability_executor.py:126:    def make_executor(self, provider, repo=None, store=None, *, worker_id="w1", lease_seconds=5):
./tests/test_m495_capability_executor.py:131:            artifact_store=store, worker_id=worker_id, lease_seconds=lease_seconds,
./tests/test_m495_capability_repository.py:6:    AttemptLeaseConflict, MemoryCapabilityRepository, PostgresCapabilityRepository,
./tests/test_m495_capability_repository.py:131:    def test_execution_lease_prevents_parallel_workers_and_expires(self):
./tests/test_m495_capability_repository.py:136:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w1", now=100, lease_seconds=30))
./tests/test_m495_capability_repository.py:137:        self.assertFalse(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=120, lease_seconds=30))
./tests/test_m495_capability_repository.py:138:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=131, lease_seconds=30))
./tests/test_m495_capability_repository.py:160:        self.assertFalse(self.repo.claim_execution_attempt("idem-1", worker_id="w", now=1000, lease_seconds=30))
./tests/test_m495_capability_repository.py:162:    def test_stale_worker_cannot_mutate_after_lease_is_reclaimed(self):
./tests/test_m495_capability_repository.py:167:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w1", now=100, lease_seconds=10))
./tests/test_m495_capability_repository.py:168:        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=111, lease_seconds=10))
./tests/test_m495_capability_repository.py:169:        with self.assertRaises(AttemptLeaseConflict):
./tests/test_m495_capability_repository.py:186:        self.assertIn("lease_expires_at timestamptz", normalized)
./tests/test_m495_capability_repository.py:188:        self.assertNotIn("lease_owner text not null", normalized)
./tests/test_m495_capability_repository.py:232:    def test_transition_attempt_requires_current_lease_owner(self):
./tests/test_m495_capability_repository.py:241:        self.assertIn("lease_owner=%s", lowered)
./tests/test_m495_golden_acceptance.py:127:            worker_id='golden-worker', lease_seconds=30, max_polls=3,
./tests/test_m4d2b_parity_and_worker.py:208:            json={'followup': 'not sure what to build -- M4D2B_CLASSIFY:ambiguous please clarify the request'})
./tests/test_m4d2b_parity_and_worker.py:312:        self.assertFalse(evidence['billing'] == 'settled', 'system_bug is never billable -- must be released, not settled')
./tests/test_m4d2b_parity_and_worker.py:313:        self.assertEqual(evidence['billing'], 'released')
./tests/test_m4d2b_parity_and_worker.py:357:            json={'followup': 'duplicate delivery check -- M4D2B_CLASSIFY:ambiguous please clarify'})
./tests/test_m4d2_live_postgres.py:325:        released, and (b) accept() for a DIFFERENT project Y is completely
./tests/test_m4d2_live_postgres.py:353:        # lock, and only complete after it is released.
./tests/test_m4d2_live_postgres.py:363:        t_release_at = None
./tests/test_m4d2_live_postgres.py:368:        t_release_at = time.monotonic()
./tests/test_m4d2_live_postgres.py:369:        holder.rollback()  # releases the advisory lock (xact-scoped)
./tests/test_m4d2_live_postgres.py:374:        self.assertGreaterEqual(x_result['finished_at'], t_release_at,
./tests/test_m4d2_live_postgres.py:375:                                 'project X accept() must not finish before the blocking lock was released')
./tests/test_m4_worker.py:206:        subs.release.assert_not_called()
./tests/test_m4_worker.py:208:    def test_not_billable_releases_even_with_real_spend(self):
./tests/test_m4_worker.py:214:        self.assertEqual(out, 'released')
./tests/test_m4_worker.py:215:        subs.release.assert_called_once_with(build_id='mod_1')
./tests/test_m4_worker.py:229:        h.subs.release.assert_called_once_with(build_id='mod_1')
./tests/test_m4_worker.py:256:        h.subs.release.assert_called_once_with(build_id='mod_1')
./tests/test_m4_worker.py:264:        h.subs.release.assert_called_once_with(build_id='mod_1')  # still free -- category-driven, not outcome-driven
./tests/test_m4_worker.py:286:        h.subs.release.assert_called_once_with(build_id='mod_1')  # no spend incurred
./tests/test_m4_worker.py:288:    def test_exception_with_real_spend_already_incurred_is_settled_not_released(self):
./tests/test_m4_worker.py:294:        h.subs.release.assert_not_called()
./tests/test_m4_worker.py:300:        h.subs.release.assert_not_called()
./tests/test_m5_build_contract_binding.py:212:        engine.executor = verified_chain()  # release policy: the chain's checks ran and passed
./tests/test_m5_build_economics.py:334:    def test_failed_zero_spend_build_releases_reservation(self):
./tests/test_m5_build_economics.py:340:        self.assertEqual(action,'released')
./tests/test_m5_build_economics.py:341:        self.assertEqual(evidence,{'action':'released'})
./tests/test_m5_build_economics.py:343:        subs.release.assert_called_once_with(build_id='b1')
./tests/test_m5_economics_reconciliation.py:225:    def test_7_actual_lower_than_reserved_releases_unused_reservation(self):
./tests/test_m5_economics_reconciliation.py:243:        self.assertEqual(refund[1][0], D("0.596"))  # 0.61 reserved - 0.014 actual is released
./tests/test_m5_product_architect.py:48:        self.assertEqual(contract.release_target, "vercel")
./tests/test_m5_public_path_truth.py:39:    def test_m5_truth_starts_partial_until_release_gate_proves_candidate(self):
./tests/test_m5_web_saas_acceptance.py:91:    def test_health_only_does_not_create_false_release_pass(self):
./tests/test_m5_web_saas_acceptance.py:102:        self.assertFalse(report.release_eligible)
./tests/test_m5_web_saas_acceptance.py:124:        self.assertTrue(report.release_eligible)
./tests/test_m5_web_saas_acceptance.py:145:    def test_failed_integration_blocks_release_even_when_other_smokes_pass(self):
./tests/test_m5_web_saas_acceptance.py:158:        self.assertFalse(report.release_eligible)
./tests/test_m5_web_saas_acceptance.py:218:            status='FAIL', release_eligible=False, summary='functional request failed', checks=(),
./tests/test_m5_web_saas_acceptance.py:281:            status='PASS', release_eligible=True, summary='ok', checks=(),
./tests/test_m5_web_saas_acceptance.py:302:            status='PASS', release_eligible=True, summary='ok', checks=(),
./tests/test_m5_web_saas_acceptance.py:405:            self.assertTrue(report.release_eligible)
./tests/test_maintenance_live_postgres.py:3:Stuck RUNNING builds are failed as worker_lost and their reservation released;
./tests/test_maintenance_live_postgres.py:48:    def test_stale_running_build_is_failed_and_released(self):
./tests/test_maintenance_live_postgres.py:72:        self.assertEqual(res, 'RELEASED')
./tests/test_migration_rollback_tolerance.py:81:        apply_migrations(self.conn, self.through_039)                           # the release that ships 039, before 040
./tests/test_model_transient_retry.py:30:                                    "Spikes in demand are usually temporary. Please try again later.",
./tests/test_plan_driven_execution.py:358:    """ADWv1 G3: approved criteria -> spec -> behavioural coverage -> mandatory release check."""
./tests/test_plan_driven_execution.py:392:        from omni_prod.release_policy import build_report
./tests/test_plan_driven_execution.py:404:    def test_release_check_statuses(self):
./tests/test_plan_driven_execution.py:419:        from omni_prod.release_policy import build_report
./tests/test_plan_driven_execution.py:454:    def test_deliverable_and_preview_are_defined_by_release_checks(self):
./tests/test_preview_data_durability.py:151:        return AcceptanceReport(status='PASS', release_eligible=True, summary='ok', checks=(),
./tests/test_preview_data_durability.py:179:        self.assertFalse(repo.acceptance.release_eligible)
./tests/test_profit_protection.py:30: service.release.assert_not_called()
./tests/test_provider_quota_and_dialects.py:21:QUOTA = 'model request failed: HTTP 429: You exceeded your current quota, please check your plan and billing details'
./tests/test_qa_budget.py:185:    def test_qa_release_does_not_touch_the_customer_plan(self):
./tests/test_qa_budget.py:187:        _service(_Pool(cur)).release(build_id="bld_qa")
./tests/test_qa_budget.py:188:        self.assertTrue(any("SET status='RELEASED'" in s for s, _ in cur.calls))
./tests/test_qa_budget.py:191:    def test_customer_release_still_restores_plan_counters(self):
./tests/test_qa_budget.py:193:        _service(_Pool(cur)).release(build_id="b")
./tests/test_quality_repairable.py:4:verification passed, traceability 100%, then the release gate rejected it at
./tests/test_quality_repairable.py:16:from omni_prod.worker_tasks import evaluate_release_gates
./tests/test_quality_repairable.py:79:        ok, code, message = evaluate_release_gates(result=result, quality=quality, security=None, rights=None)
./tests/test_quality_repairable.py:86:        self.assertEqual(evaluate_release_gates(result=result, quality=quality, security=None, rights=None)[1],
./tests/test_real_docker_drain_recovery.py:75:    """Two local images built from the host's bash (no registry pull): :1 = previous release, :2 = new release."""
./tests/test_real_docker_drain_recovery.py:167:        # previous release is running
./tests/test_real_docker_drain_recovery.py:239:        self.conn.execute("INSERT INTO build_jobs (id,project_id,status,heartbeat_at) VALUES (%s,%s,'running', now())", (f'bld_{u}', f'p{u}'))
./tests/test_real_docker_drain_recovery.py:244:    def test_0_clean_deploy_drains_gracefully_then_the_new_release_runs(self):
./tests/test_real_docker_drain_recovery.py:339:    def test_7_a_startup_failure_of_the_new_release_is_recovered(self):
./tests/test_registry_audit.py:105:                    'performance_resource_engineer', 'release_change_coordinator', 'privacy_ip_steward',
./tests/test_registry_audit.py:141:        for key in ('game_designer', 'video_creator', 'automation_designer', 'agent_app_builder', 'release_agent'):
./tests/test_release_blocks_on_failed_acceptance.py:7:from omni_prod.worker_tasks import evaluate_release_gates
./tests/test_release_blocks_on_failed_acceptance.py:36:class ReleaseGateTests(unittest.TestCase):
./tests/test_release_blocks_on_failed_acceptance.py:42:        ready, code, message = evaluate_release_gates(result=result, quality=OK, security=OK, rights=RIGHTS)
./tests/test_release_blocks_on_failed_acceptance.py:50:        self.assertFalse(evaluate_release_gates(result=result, quality=OK, security=OK, rights=RIGHTS)[0])
./tests/test_release_policy.py:1:"""Release policy (Production Assurance v2 §4/§5; issue #6 P1): a check that did
./tests/test_release_policy.py:10:from omni_prod.release_policy import FAIL, NOT_RUN, PASS, build_report, enforcement_mode
./tests/test_release_policy.py:105:        with patch.dict(os.environ, {'OMNI_RELEASE_POLICY': 'shadow', 'OMNI_ENV': 'staging'}):
./tests/test_release_policy.py:107:        with patch.dict(os.environ, {'OMNI_RELEASE_POLICY': 'shadow', 'OMNI_ENV': 'development'}):
./tests/test_release_policy.py:118:                    with patch.dict(os.environ, {'OMNI_ENV': environment, 'OMNI_RELEASE_POLICY': 'shadow'}), \
./tests/test_release_policy.py:119:                         patch('omni_prod.release_policy.build_report', side_effect=ValueError('broken report')), \
./tests/test_release_policy.py:122:                    self.assertEqual(h.final['error_code'], 'release_policy_unavailable')
./tests/test_release_policy.py:125:                    self.assertFalse(h.final['evidence_json']['release_ready'])
./tests/test_release_policy.py:129:                        h.subs.release.assert_not_called()
./tests/test_release_policy.py:131:                        h.subs.release.assert_called_once_with(build_id='bld_1')
./tests/test_release_policy.py:136:        with patch.dict(os.environ, {'OMNI_ENV': 'development', 'OMNI_RELEASE_POLICY': 'shadow'}), \
./tests/test_release_policy.py:137:             patch('omni_prod.worker_tasks.release_quality_report', return_value=None):
./tests/test_release_policy.py:144:        self.assertEqual(h.final['error_code'], 'release_policy_failed')
./tests/test_release_policy.py:208:        from omni_prod.release_policy import persist
./tests/test_v13_core.py:9:from omni_prod.worker_health import WorkerHeartbeat, is_stale
./tests/test_v13_core.py:59:        hb = WorkerHeartbeat("w1", now - timedelta(seconds=61))
./tests/test_v15_acceptance.py:53:    def test_canary_bad_release_requests_rollback(self):
./tests/test_v16_release_gate.py:10:from omni_prod.release_manifest import write_release_manifest, verify_release_manifest
./tests/test_v16_release_gate.py:71:            write_release_manifest(root, version="V16", test_count=1)
./tests/test_v16_release_gate.py:72:            ok, errors = verify_release_manifest(root)
./tests/test_v16_release_gate.py:75:            ok, errors = verify_release_manifest(root)
./tests/test_v18_supplychain_security.py:27:        a=build_attestation(subject_name='release.zip',subject_sha256='a'*64,builder='local',metadata={})
./tests/test_v19_reliability.py:7:from omni_prod.worker_lease import Lease, can_claim, renew
./tests/test_v19_reliability.py:46:class LeaseTests(unittest.TestCase):
./tests/test_v19_reliability.py:47:    def test_expired_lease_can_be_reclaimed(self):
./tests/test_v19_reliability.py:48:        l = Lease("w1", 10)
./tests/test_v19_reliability.py:52:    def test_renew(self):
./tests/test_v19_reliability.py:54:            renew(owner="w", now=5, ttl_seconds=10).expires_at, 15
./tests/test_v24_international.py:127:    def test_status_exposes_v24_release(self):
./tests/test_v24_international.py:128:        d=self.c.get('/api/status').json(); self.assertEqual(d['product_release'],'V24 International Readiness'); self.assertGreaterEqual(d['benchmark_catalog_cases'],200)
./tests/test_v25_unified_v10_parity.py:10:from omni_prod.native_source import omni_android_release_project, game_project
./tests/test_v25_unified_v10_parity.py:94:    def test_omni_android_v10_release_contract(self):
./tests/test_v25_unified_v10_parity.py:95:        r=omni_android_release_project()
./tests/test_v25_unified_v10_parity.py:105:        self.assertIn('java-version: "17"',workflow); self.assertIn('gradle-version: "8.9"',workflow); self.assertIn('bundleRelease',workflow)
./tests/test_v25_unified_v10_parity.py:138:        self.assertEqual(d['product_release'],'V24 International Readiness')
./tests/test_v25_unified_v10_parity.py:139:        self.assertEqual(d['current_release'],'V25 Unified Core')
./tests/test_v26_universal_pro.py:53:        self.assertEqual(d['current_release'],'V25 Unified Core')
./tests/test_v26_universal_pro.py:54:        self.assertEqual(d['universal_release'],'V26 Universal Pro Reviewer Release')
./tests/test_v27_rights_company_os.py:61:        council=os.release_council()
./tests/test_v27_rights_company_os.py:66:    def test_operating_company_triage_and_release_council(self):
./tests/test_v27_rights_company_os.py:77:        blocked=os.evaluate_release({
./tests/test_v27_rights_company_os.py:84:        green=os.evaluate_release({k:True for k in (
./tests/test_v27_rights_company_os.py:100:        self.assertEqual(d['rights_release'],'V27 Rights & Company OS')
./tests/test_v27_rights_company_os.py:166:        self.assertIn('release_council',d)
./tests/test_v27_rights_company_os.py:187:        council=self.c.post('/api/v27/company-os/release-council/evaluate',json={'gates':gates,'founder_public_launch_approved':True})
./tests/test_worker_deploy_recovery.py:344:    def test_database_state_blocks_regardless_of_heartbeat_and_queued_work_does_not(self):
./tests/test_worker_deploy_recovery.py:356:                conn.execute("INSERT INTO build_jobs (id, project_id, status, heartbeat_at) VALUES (%s,%s,'running', now() - interval '2 hours')",
./tests/test_worker_deploy_recovery.py:359:                self.assertTrue(s['busy'])                                          # an old heartbeat is NOT proof it ended
./tests/test_worker_deploy_recovery.py:361:                self.assertEqual(s['running_builds_with_old_heartbeat'], [f'bld_s{u}'])
./tests/test_worker_deploy_recovery.py:362:                # only an exact, explicit operator acknowledgement releases it
./tests/test_worker_deploy_recovery.py:365:                conn.execute("INSERT INTO build_jobs (id, project_id, status, heartbeat_at) VALUES (%s,%s,'running', now())", (f'bld_r{u}', f'p{u}'))
./tests/test_worker_deploy_recovery.py:381:                    conn.execute("INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, quoted_usd, quote, state, claim_token, lease_expires_at) "
./tests/test_worker_deploy_recovery.py:383:                                 (f'r{u}', f'k{u}', f'a{u}', f'p{u}', state))   # an EXPIRED lease still blocks
-- retries --
./omni_prod/attempt_ledger.py:83:    retry_count: int | None = None
./omni_prod/attempt_ledger.py:122:        * retry_count: prior attempts of the same logical call. The routed
./omni_prod/attempt_ledger.py:135:        record.retry_count = (record.fallback_rank or 0) if record.kind == 'provider_call' else 0
./omni_prod/attempt_ledger.py:234:            'failure_reason', 'final_outcome', 'retry_count', 'repair_count', 'regenerate_count',
./omni_prod/dead_letter.py:6:    dead_letter: bool
./omni_prod/dead_letter.py:9:def decide_dead_letter(
./omni_prod/recovery_simulation.py:3:from .dead_letter import decide_dead_letter
./omni_prod/recovery_simulation.py:31:    dead = decide_dead_letter(
./omni_prod/recovery_simulation.py:34:    assert dead.dead_letter
./omni_prod/recovery_simulation.py:40:        "dead_letter_reason": dead.reason,
./omni_prod/__init__.py:1:__all__ = ['config', 'db', 'queueing', 'storage', 'sandbox', 'health', 'models', 'build_state', 'job_repository', 'deployments', 'usage', 'provenance', 'api_routes', 'idempotency', 'limits', 'model_router', 'rollback', 'worker_health', 'artifact_keys', 'build_budget', 'canary', 'error_taxonomy', 'orchestrator', 'repair_loop', 'retry', 'memory_adapters', 'secret_redaction', 'acceptance_pipeline', 'migrations', 'audit', 'secret_scan', 'canary_controller', 'release_manifest', 'release_gate', 'staging_simulation', 'preflight', 'migration_runner', 'artifact_integrity', 'dependency_inventory', 'sbom', 'cors_policy', 'web_security', 'attestation', 'circuit_breaker', 'outbox', 'worker_lease', 'dead_letter', 'recovery_simulation', 'request_id', 'metrics', 'slo', 'backup_manifest', 'structured_event', 'observability', 'recovery_drill', 'production_adapters', 'redis_circuit_breaker', 'model_gateway', 'model_policy', 'product_spec', 'repository_patch', 'change_policy', 'autonomous_agents', 'autonomous_core', 'modifier_engine', 'model_runtime_config', 'project_manifest', 'sandbox_executor']
./tests/test_attempt_ledger.py:139:        rows = [(r.task_type, r.retry_count, r.repair_count, r.regenerate_count, r.fallback_count, r.escalation_count)
./tests/test_attempt_ledger.py:157:        self.assertEqual((v.retry_count, v.repair_count, v.escalation_count), (0, 1, 0))
./tests/test_v19_reliability.py:5:from omni_prod.dead_letter import decide_dead_letter
./tests/test_v19_reliability.py:60:            decide_dead_letter(
./tests/test_v19_reliability.py:68:            decide_dead_letter(
./tests/test_v19_reliability.py:70:            ).dead_letter
```


## F2 — LLM / סוכנים

```
-- json.loads בלי הגנה --
./omni_prod/agent_os/departments.py:143:        registry = json.loads((ROOT / 'AGENT_OS_REGISTRY.json').read_text(encoding='utf-8'))
./omni_prod/agent_os/meta.py:69:    matrix = matrix or json.loads(REGRESSION.read_text())
./omni_prod/agent_os/skills.py:19:TAXONOMY: dict[str, list[str]] = json.loads((Path(__file__).with_name('skills_taxonomy.json')).read_text(encoding='utf-8'))
./omni_prod/attachments.py:192:            d['annotation'] = json.loads(d['annotation'])
./omni_prod/auth.py:42:        h=json.loads(_unb64(header)); data=json.loads(_unb64(payload))
./omni_prod/backup_manifest.py:40:    data = json.loads(manifest_path.read_text(encoding="utf-8"))
./omni_prod/behavior_acceptance.py:169:                    parsed = json.loads(line[len('BEHAVIOR-ACCEPTANCE '):])
./omni_prod/brief_repository.py:53:    data = r[3] if isinstance(r[3], dict) else json.loads(r[3])
./omni_prod/browser_fixtures.py:42:        n = int(self.headers.get("Content-Length") or 0); d = json.loads(self.rfile.read(n) or b"{}")
./omni_prod/browser_probe.py:150:                return json.loads(line[len('OMNI_BROWSER_PROBE '):])
./omni_prod/build_contract_repository.py:121:            data = json.loads(data)
./omni_prod/capability_repository.py:386:                        constraints = json.loads(row[5]) if isinstance(row[5], str) else (row[5] or {})
./omni_prod/capability_repository.py:387:                        dependencies = json.loads(row[6]) if isinstance(row[6], str) else (row[6] or [])
./omni_prod/capability_repository.py:455:            constraints = json.loads(row[5]) if isinstance(row[5], str) else (row[5] or {})
./omni_prod/capability_repository.py:456:            dependencies = json.loads(row[6]) if isinstance(row[6], str) else (row[6] or [])
./omni_prod/capability_repository.py:457:            verification = json.loads(row[14]) if isinstance(row[14], str) else (row[14] or {})
./omni_prod/capability_repository.py:458:            evidence = json.loads(row[15]) if isinstance(row[15], str) else (row[15] or {})
./omni_prod/capability_repository.py:487:            usage = json.loads(row[7]) if isinstance(row[7], str) else (row[7] or {})
./omni_prod/capability_repository.py:488:            evidence = json.loads(row[8]) if isinstance(row[8], str) else (row[8] or {})
./omni_prod/capability_repository.py:515:            constraints = json.loads(row[5]) if isinstance(row[5], str) else (row[5] or {})
./omni_prod/capability_repository.py:516:            dependencies = json.loads(row[6]) if isinstance(row[6], str) else (row[6] or [])
./omni_prod/capability_repository.py:517:            verification = json.loads(row[10]) if isinstance(row[10], str) else (row[10] or {})
./omni_prod/consistency_gate.py:100:                json.loads(text)
./omni_prod/consistency_gate.py:268:            plan = json.loads(manifest).get('web_saas_acceptance') or {}
./omni_prod/consistency_gate.py:310:        data = json.loads(raw)
./omni_prod/demo_project.py:119:            payload = json.loads(repository.get('request.json', '{}'))
./omni_prod/dependency_policy.py:275:        data = json.loads(raw)
./omni_prod/dependency_policy.py:309:            data = json.loads(content)
./omni_prod/discovery.py:328:    new = Brief.from_dict(json.loads(json.dumps(brief.to_dict())))
./omni_prod/evidence_export.py:58:    return value if isinstance(value, (dict, list)) else json.loads(value or '{}')
./omni_prod/gate_replay.py:48:        data = json.loads(repo.get('.omni/project.json') or '{}')
./omni_prod/intake/agent.py:59:    return d.Brief.from_dict(json.loads(json.dumps(b.to_dict())))
./omni_prod/intake/benchmark.py:49:    cases = json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']
./omni_prod/intake/budget.py:99:        items = json.loads(raw)
./omni_prod/intake/lanes.py:35:        return json.loads(path.read_text(encoding='utf-8'))
./omni_prod/intelligence/matrix.py:45:    return json.loads(path.read_text(encoding='utf-8'))
./omni_prod/job_repository.py:246:                    contract_json = json.loads(contract_json)
./omni_prod/job_repository.py:248:                    initial_evidence = json.loads(initial_evidence)
./omni_prod/media_gateway.py:40:            with urllib.request.urlopen(req,timeout=self.endpoint.timeout_seconds) as r: body=json.loads(r.read().decode())
./omni_prod/model_catalog.py:92:        items = json.loads(raw)
./omni_prod/model_gateway.py:41:        body = json.loads(raw)
./omni_prod/model_gateway.py:188:            body.setdefault(key, json.loads(raw))
./omni_prod/model_gateway.py:196:                payload = json.loads(resp.read().decode('utf-8'))
./omni_prod/model_gateway.py:271:                return json.loads(candidate, strict=strict), None
./omni_prod/model_runtime_config.py:50:            items = json.loads(raw)
./omni_prod/modification_repository.py:187:            target_markets = json.loads(target_markets)
./omni_prod/modification_repository.py:189:            rights_evidence = json.loads(rights_evidence)
./omni_prod/modification_repository.py:313:            repository_json = json.loads(repository_json)
./omni_prod/modification_repository.py:315:            spec_json = json.loads(spec_json)
./omni_prod/modification_repository.py:412:                            repository_json = json.loads(repository_json)
./omni_prod/modification_repository.py:414:                            spec_json = json.loads(spec_json)
./omni_prod/planning/registry_view.py:22:        return json.loads((ROOT / name).read_text(encoding='utf-8'))
./omni_prod/postdeploy_checks.py:117:        return status, json.loads(raw) if raw else None
./omni_prod/preview_repository.py:266:            evidence = json.loads(evidence)
./omni_prod/preview_runtime.py:136:        data = json.loads(raw)
./omni_prod/preview_runtime.py:179:        data = json.loads(raw)
./omni_prod/project_manifest.py:41:            data = json.loads(raw)
./omni_prod/providers/image_provider.py:365:            return json.loads(resp.read().decode() or "{}")
./omni_prod/providers/managed_web_saas.py:332:    doc = json.loads(policy) if isinstance(policy, str) else dict(policy)
./omni_prod/providers/managed_web_saas.py:585:                  "access_policy": json.loads(policy), "scoped_access_expires_at": creds.get("expires_at")}
./omni_prod/providers/qstash_scheduler.py:73:            return json.loads(raw) if raw else None
./omni_prod/providers/qstash_scheduler.py:166:            metadata = json.loads(_decode(header), object_pairs_hook=_unique_object)
./omni_prod/providers/qstash_scheduler.py:167:            claims = json.loads(_decode(payload), object_pairs_hook=_unique_object)
./omni_prod/providers/r2_credentials.py:28:        doc = json.loads(policy)
./omni_prod/providers/r2_credentials.py:36:        if doc != json.loads(scoped_object_policy(bucket, prefix)):
./omni_prod/providers/replicate_connection.py:64:            body = json.loads(response.read(65537))
./omni_prod/providers/replicate_connection.py:86:            payload = json.loads(body)
./omni_prod/registry_audit.py:111:        return json.loads(LOCK_PATH.read_text(encoding='utf-8'))
./omni_prod/release_manifest.py:56:    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
./omni_prod/remote_sandbox.py:53:                data = json.loads(raw.decode())
./omni_prod/requirement_ledger.py:138:    payload = json.loads(path.read_text(encoding="utf-8"))
./omni_prod/routed_gateway.py:295:                floors.update({str(k): int(v) for k, v in json.loads(raw).items()})
./omni_prod/secrets_manager.py:38:            with self.urlopen(req,timeout=self.config.timeout_seconds) as r: payload=json.loads(r.read().decode())
./omni_prod/secrets_manager.py:104:        return json.loads(raw.decode() or '{}') if raw else {}
./omni_prod/secrets_manager.py:200:            payload = json.loads(raw.decode()) if raw else {}
./omni_prod/semantic_capabilities.py:96:        parsed = json.loads(lines[0][len(LINE_PREFIX):])
./omni_prod/spec_repository.py:61:            data = json.loads(data)
./omni_prod/spec_repository.py:96:            spec = json.loads(spec)
./omni_prod/stripe_billing.py:77:                body = json.loads(response.read().decode('utf-8'))
./omni_prod/stripe_billing.py:109:        event = json.loads(payload.decode('utf-8'))
./omni_prod/visual_qa.py:160:                report = json.loads(line[len('OMNI_VISUAL_QA '):])
./omni_prod/web_saas_acceptance.py:99:        return json.loads(self.text() or 'null')
./omni_prod/web_saas_acceptance.py:414:        decoded = json.loads(text)
./omni_prod/worker_tasks.py:971:        value = _json.loads(value)
./omni_prod/worker_tasks.py:1469:            return json.loads(value) if isinstance(value, str) else value
./scripts/run_hostile_static_suite.py:16:    m=json.loads(r['.omni/project.json']); m['verify'][0]['argv']=['bash','-lc','id']; r['.omni/project.json']=json.dumps(m)
./scripts/run_hostile_static_suite.py:19:    m=json.loads(r['.omni/project.json']); m['verify'][0]['argv']=['python','--privileged']; r['.omni/project.json']=json.dumps(m)
./scripts/run_v25_release_gate.py:23:bench=json.loads((ROOT/'BENCHMARK_V25_OFFLINE.json').read_text(encoding='utf-8'))
./scripts/run_v25_release_gate.py:25:http=json.loads((ROOT/'LIVE_HTTP_V25.json').read_text(encoding='utf-8'))
./scripts/run_v26_release_gate.py:20:http=json.loads((ROOT/'LIVE_HTTP_V26.json').read_text())
./scripts/run_v27_release_gate.py:22:http=json.loads(http_path.read_text()) if http_path.exists() else {}
./scripts/run_v28_http_acceptance.py:22:            return resp.status, (json.loads(raw.decode()) if 'json' in ctype else raw), dict(resp.headers)
./scripts/run_v28_http_acceptance.py:25:        try: payload=json.loads(raw.decode())
./scripts/run_v28_release_gate.py:39:bench = json.loads(bench_path.read_text()) if bench_path.exists() else {}
./scripts/run_v28_release_gate.py:44:http = json.loads(http_path.read_text()) if http_path.exists() else {}
./scripts/run_v28_release_gate.py:65:load = json.loads(load_path.read_text()) if load_path.exists() else {}
./tests/financial_fault_harness.py:122:            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
./tests/integration/test_live_preview_runtime.py:108:            info = json.loads(subprocess.run(['docker', 'inspect', cid], capture_output=True, text=True, check=True).stdout)[0]
./tests/integration/test_m495_provider_adapter.py:34:        payload = json.loads(self.rfile.read(length).decode("utf-8"))
./tests/m4d2b_local_model_server.py:112:            body = json.loads(raw.decode('utf-8'))
./tests/m4d2b_local_model_server.py:115:            payload = json.loads(user_content)
./tests/test_agent_os.py:267:        committed = json.loads(truth_matrix.TRUTH_JSON.read_text())
./tests/test_architect_spec_shape.py:46:        correction = json.loads(gw.calls[1]["user"])
./tests/test_attempt_ledger.py:214:        self.assertEqual(json.loads(row["candidate_set"])[0]["name"], "cheap")
./tests/test_behavior_acceptance_in_build.py:34:        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
./tests/test_browser_probe.py:92:            manifest = json.loads((Path(d) / '.omni/project.json').read_text())
./tests/test_company_loss.py:49:    assert json.loads(params[13])['metering'] == {'input_tokens': 10}
./tests/test_consistency_gate.py:67:        m = json.loads(json.dumps(MANIFEST))
./tests/test_consistency_gate.py:79:        m = json.loads(json.dumps(MANIFEST))
./tests/test_conversation_os.py:46:        cases = json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']
./tests/test_conversation_os.py:280:        row = self.Row(expected_revision + 1, d.Brief.from_dict(json.loads(json.dumps(brief.to_dict()))))
./tests/test_dependency_policy.py:84:            manifest = json.dumps({"build": [argv], "verify": json.loads(MANIFEST)["verify"]})
./tests/test_dependency_policy.py:89:        manifest = json.dumps({**json.loads(MANIFEST), "start": ["sh", "-c", "x"]})
./tests/test_dependency_policy.py:91:        manifest = json.dumps({**json.loads(MANIFEST), "start": ["pip", "install", "flask"]})
./tests/test_dependency_policy.py:97:        manifest = json.dumps({**json.loads(MANIFEST), "runtime": "node:20-slim"})
./tests/test_dependency_policy.py:118:        evidence = json.loads(failure.evidence)
./tests/test_deployment_verification.py:360:                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
./tests/test_evidence_json.py:39:        data = json.loads(dumps_evidence(FAILURE_EVIDENCE))
./tests/test_evidence_json.py:55:        self.assertEqual(json.loads(marker)['evidence_keys'], ['endpoint'])
./tests/test_evidence_json.py:94:        self.assertEqual(json.loads(evidence_param)['billing'], 'released')
./tests/test_failure_injection.py:100:        rows = json.loads(path.read_text())['injections']
./tests/test_infisical_secret_store.py:39:        body = json.loads(req.data) if req.data else {}
./tests/test_j1_real_agent_feature_flag.py:64:        self.assertIn("base_repository_fingerprint", json.loads(gw.calls[0]["user"])["repository"])
./tests/test_m495_asset_evidence.py:17:        payload=json.loads(files['assets/148ai-asset-manifest.json'])
./tests/test_m495_asset_evidence.py:42:        payload=json.loads(files['assets/148ai-asset-manifest.json'])
./tests/test_m495_golden_acceptance.py:169:        manifest = json.loads(CreativeDirector().repository_files(creative, capability_evidence=final)['assets/148ai-asset-manifest.json'])
./tests/test_m495_truth_lock.py:36:        machine=json.loads(files['M4_95_MACHINE_TRUTH.json'])
./tests/test_m495_truth_lock.py:37:        skills=json.loads(files['MASTER_SKILLS_REGISTRY.json'])
./tests/test_m495_truth_lock.py:38:        agents=json.loads(files['MASTER_AGENTS_REGISTRY.json'])
./tests/test_m495_truth_lock.py:60:        machine = json.loads(files['M4_95_MACHINE_TRUTH.json'])
./tests/test_m495_truth_lock.py:61:        providers = json.loads(files['PROVIDER_CATALOG.json'])
./tests/test_m495_truth_lock.py:62:        prices = json.loads(files['PROVIDER_PRICE_CATALOG.json'])
./tests/test_m49_lifecycle.py:152:        persisted_spec = spec_row[0] if isinstance(spec_row[0], dict) else json.loads(spec_row[0])
./tests/test_m5_build_economics.py:476:        body = json.loads(response.body)
./tests/test_m5_build_economics.py:488:        body = json.loads(response.body)
./tests/test_m5_build_economics.py:502:                body = json.loads(response.body)
./tests/test_m5_generated_app_storage_isolation.py:40:        self.credentials[key] = json.loads(policy)
./tests/test_m5_generated_app_storage_isolation.py:143:        policy = json.loads(scoped_object_policy("genapp-objects", "generated-apps/abc/preview/"))
./tests/test_m5_managed_web_saas_profile.py:362:            seen["body"] = json.loads(req.data.decode())
./tests/test_m5_media_provider_adapters.py:82:            body = json.loads(req.data.decode())
./tests/test_m5_web_saas_acceptance.py:291:        payload = json.loads(cur.executed[1][1][1])
./tests/test_m5_web_saas_acceptance.py:334:                return json.loads(self.rfile.read(n) or b'{}')
./tests/test_manifest_shape.py:28:        calls.append(json.loads(req.data)["argv"])
./tests/test_modification_context.py:31:        self.calls.append((system, json.loads(user)))
./tests/test_modification_repository.py:219:        self.assertEqual(json.loads(params[6]), ['US', 'EU', 'IL'])  # default target markets
./tests/test_modification_repository.py:220:        self.assertEqual(json.loads(params[7]), [])  # default rights evidence
./tests/test_modification_repository.py:230:        self.assertEqual(json.loads(params[6]), ['DE', 'FR'])
./tests/test_modification_repository.py:231:        self.assertEqual(json.loads(params[7]), [{'id': 'ev_1'}])
./tests/test_modification_repository.py:357:        self.assertEqual(json.loads(insert_params[2]), {'app.py': 'v2'})
./tests/test_modification_repository.py:358:        self.assertEqual(json.loads(insert_params[3])['title'], 'Todo')
./tests/test_product_evolution.py:66:        sent = json.loads(gateway.calls[0]['user'])
./tests/test_provider_quota_and_dialects.py:182:                        body=json.loads(req.data.decode()))
./tests/test_qstash_scheduler.py:78:        self.assertEqual(json.loads(req.data), {"job": "probe"})
./tests/test_r2_generated_credentials.py:31:    return jwt, json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))), sig
./tests/test_r2_generated_credentials.py:80:            d = json.loads(POLICY)
./tests/test_replicate_connection.py:37:        assert json.loads(req.data) == {'input': {'prompt': 'Original blue bird icon', 'output_format': 'png', 'num_outputs': 1}}
./tests/test_replicate_image_test.py:21:        body = json.loads(req.data)
./tests/test_spec_language.py:47:            again = BuildContract.from_dict(json.loads(json.dumps(c.to_dict(), ensure_ascii=False)))
./tests/test_spec_repository.py:75:        self.assertEqual(json.loads(params[2])['title'], 'Todo')
./tests/test_v22_autonomous_core.py:145:        body = json.loads(self.rfile.read(length))
./tests/test_v22_sandbox_executor.py:46:        data=json.loads(r['.omni/project.json'])
./tests/test_v23_investor_grade.py:84:        self.assertEqual(json.loads(repo['request.json'])['prompt'], prompt)
./tests/test_v24_international.py:117:        m=json.loads(repo['.omni/project.json']); m['verify'][0]['argv']=['bash','-lc','echo hi']; repo['.omni/project.json']=json.dumps(m)
./tests/test_v24_international.py:176:        domain=json.loads(r['domain.json']); self.assertEqual(domain['category'],'commerce'); self.assertIn('Cart',domain['modules'])
./tests/test_v26_universal_pro.py:108:                n=int(self.headers.get('content-length','0')); body=json.loads(self.rfile.read(n))
./tests/test_v27_rights_company_os.py:114:            m=json.loads(f.read('rights/rights-manifest.json'))
./tests/test_v28_148ai_launch.py:68:        manifest=json.loads(x['.148ai/brand-manifest.json'])
./tests/test_vercel_entrypoint.py:20:        config = json.loads(Path('vercel.json').read_text(encoding='utf-8'))
./tests/test_worker_deploy_recovery.py:157:        cfg = json.loads((log.parent / 'cfg.json').read_text())
./tests/test_worker_deploy_recovery.py:168:        cfg = json.loads((log.parent / 'cfg.json').read_text())
./tests/test_worker_deploy_recovery.py:174:        cfg = json.loads((log.parent / 'cfg.json').read_text())
./tests/test_worker_deploy_recovery.py:182:        cfg = json.loads((log.parent / 'cfg.json').read_text())
./tests/test_worker_repository_parity.py:127:        self.assertEqual(json.loads(params[4]), {"core_ready": True})
./tools/deployment_verify.py:218:            data = json.loads(raw.decode('utf-8'))
./tools/deployment_verify.py:285:    return json.loads(text)
./tools/m49_ready_invariant_check.py:56:evidence = evidence_json if isinstance(evidence_json, dict) else json.loads(evidence_json)
./tools/m49_ready_invariant_check.py:96:    repo = repo_json if isinstance(repo_json, dict) else json.loads(repo_json)
./tools/m49_ready_invariant_check.py:97:    spec = spec_json if isinstance(spec_json, dict) else json.loads(spec_json)
-- finish_reason --
./omni_prod/model_gateway.py:191:        self.last_finish_reason = None
./omni_prod/model_gateway.py:217:            self.last_finish_reason = payload.get('stop_reason')
./omni_prod/model_gateway.py:227:            finish = choice.get('finish_reason') if isinstance(choice, dict) else None
./omni_prod/model_gateway.py:229:            raise ModelGatewayError(f'invalid model response shape (finish_reason={finish}, keys={keys})') from exc
./omni_prod/model_gateway.py:231:            raise ModelGatewayError(f"empty model response (finish_reason={choice.get('finish_reason')})")
./omni_prod/model_gateway.py:232:        self.last_finish_reason = choice.get('finish_reason')
./omni_prod/model_gateway.py:235:    last_finish_reason = None
./omni_prod/model_gateway.py:253:            finish = getattr(self, 'last_finish_reason', None)
./omni_prod/model_gateway.py:255:                                    f'finish_reason={finish}; starts {text[:60]!r})') from exc
./tests/test_model_gateway_idempotency.py:19:    return {'id': 'r1', 'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}]}
./tests/test_model_json_parsing.py:26:    gw._urlopen = lambda req, timeout=None: _Resp({'choices': [{'message': {'content': content}, 'finish_reason': finish}]})
./tests/test_model_json_parsing.py:46:        self.assertIn('finish_reason=length', msg)
-- שמות מודלים קשיחים --
./omni_prod/agent_os/providers.py:20:    ('gemini-', COMMERCIAL_APPROVED, 'Gemini API paid tier (billing enabled by the founder, Tier 1, 2026-10-08)',
./omni_prod/agent_os/skills.py:29:    'Architecture': ('architecture_agent', 'code_review_agent', ('web',), 'one model call within the build budget', 'contract data only', ('gemini',)),
./omni_prod/agent_os/skills.py:30:    'UX/UI': ('ux_ui_design_agent', 'qa_agent', ('web',), 'instructions inside generation calls', 'no user data', ('gemini',)),
./omni_prod/agent_os/skills.py:31:    'Frontend': ('frontend_agent', 'browser_rehearsal_agent', ('web',), 'part of code-generation calls', 'synthetic data in tests', ('gemini',)),
./omni_prod/agent_os/skills.py:32:    'Backend': ('backend_agent', 'behavioral_acceptance_agent', ('web',), 'part of code-generation calls', 'synthetic data in tests', ('gemini',)),
./omni_prod/agent_os/skills.py:36:    'Coding': ('coding_agent', 'code_review_agent', ('web',), 'model calls within the build budget', 'generated repository only', ('gemini',)),
./omni_prod/agent_os/skills.py:39:    'Repair': ('repair_agent', 'qa_agent', ('web',), 'model calls within the build budget', 'generated repository only', ('gemini',)),
./omni_prod/agent_os/skills.py:42:    'Provider Routing': ('provider_router_agent', 'compliance_ip_agent', ('web',), 'selection is $0; calls are metered', 'prompts sent to approved providers only', ('gemini', 'openai', 'anthropic')),
./omni_prod/agent_os/skills.py:59:    '2D Games': ('game_engineering_2d_agent', 'game_qa_2d_agent', ('game2d',), 'model calls + browser time', 'no user data', ('gemini',)),
./omni_prod/intake/budget.py:50:DEFAULT_ALLOWED_MODELS = ('gemini-3.1-flash-lite', 'gemini-3.5-flash-lite')
./omni_prod/intake/mode.py:28:RECOMMENDED_MODEL = 'gemini-3.1-flash-lite'
./omni_prod/intelligence/governance.py:26:    'generativelanguage.googleapis.com': 'gemini',
./omni_prod/intelligence/inventory.py:39:LEDGER_OK_CALLS = {'gemini-3.8-flash': 36, 'gemini-3.1-flash-lite': 115, 'gemini-3.5-flash-lite': 2,
./omni_prod/intelligence/inventory.py:40:                   'gpt-6-luna': 0, 'gpt-6.1-sol': 0, 'claude-sonnet-5-5': 0}
./omni_prod/intelligence/inventory.py:120:    _llm('gemini', 'gemini-3-8-flash', 'gemini-3.8-flash', 'Gemini Flash',
./omni_prod/intelligence/inventory.py:126:    _llm('gemini', 'gemini-3-1-flash-lite', 'gemini-3.1-flash-lite', 'Gemini Flash-Lite',
./omni_prod/intelligence/inventory.py:132:    _llm('gemini', 'gemini-3-5-flash-lite', 'gemini-3.5-flash-lite', 'Gemini Flash-Lite',
./omni_prod/intelligence/inventory.py:139:    _llm('openai', 'openai-gpt-6-luna', 'gpt-6-luna', 'GPT Luna',
./omni_prod/intelligence/inventory.py:146:    _llm('openai', 'openai-gpt-6-1-sol', 'gpt-6.1-sol', 'GPT Sol',
./omni_prod/intelligence/inventory.py:154:    _llm('anthropic', 'anthropic-claude-sonnet-5-5', 'claude-sonnet-5-5', 'Claude Sonnet',
./omni_prod/intelligence/inventory.py:162:    _llm('gemini', 'gemini-2-5-flash-lite', 'gemini-2.5-flash-lite', 'Gemini Flash-Lite',
./omni_prod/intelligence/inventory.py:167:    _llm('anthropic', 'anthropic-claude-haiku-5-5', 'claude-haiku-5-5', 'Claude Haiku',
./omni_prod/intelligence/inventory.py:173:    _llm('gemini', 'gemini-3-1-pro-preview', 'gemini-3.1-pro-preview', 'Gemini Pro',
./omni_prod/intelligence/inventory.py:186:    ModelEntry('gemini', 'gemini-3-1-flash-lite-image', 'gemini-3.1-flash-lite-image', 'Gemini pricing page (2026-10-11)',
./omni_prod/intelligence/inventory.py:191:    ModelEntry('gemini', 'gemini-omni-1-1-flash', 'gemini-omni-1.1-flash', 'Gemini deprecations page (2026-10-11)',
./omni_prod/intelligence/inventory.py:196:    ModelEntry('gemini', 'gemini-3-8-flash-lite-tts', 'gemini-3.8-flash-lite-tts', 'Gemini deprecations page (2026-10-11)',
./omni_prod/intelligence/inventory.py:201:    ModelEntry('gemini', 'lyria-3-5', 'lyria-3.5', 'Gemini pricing page (2026-10-11)', 'Lyria', 'music',
./omni_prod/intelligence/lifecycle.py:43:    _l('gemini-3.1-flash-lite', '2027-05-07', 'gemini-3.5-flash-lite', GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:44:    _l('gemini-3.5-flash-lite', None, None, GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:45:    _l('gemini-3.8-flash', None, None, GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:46:    _l('gemini-2.5-flash-lite', None, None, GOOGLE_DEP,
./omni_prod/intelligence/lifecycle.py:48:    _l('gemini-3.1-pro-preview', None, None, GOOGLE_DEP, 'preview model'),
./omni_prod/intelligence/lifecycle.py:49:    _l('gemini-3.1-flash-tts-preview', '2026-11-17', 'gemini-3.8-flash-lite-tts', GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:50:    _l('veo-3.1-generate-preview', '2026-10-22', 'gemini-omni-1.1-flash', GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:51:    _l('veo-3.1-fast-generate-preview', '2026-10-22', 'gemini-omni-1.1-flash', GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:52:    _l('imagen-4.0-generate-001', '2026-08-17', 'gemini-nano-banana-2.1', GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:53:    _l('gemini-2.5-flash-image', '2027-03-15', 'gemini-3.1-flash-lite-image', GOOGLE_DEP),
./omni_prod/intelligence/lifecycle.py:54:    _l('gpt-5-nano-2025-08-07', '2026-12-11', 'gpt-5.6-luna', OPENAI_DEP),
./omni_prod/intelligence/lifecycle.py:55:    _l('gpt-5-mini-2025-08-07', '2026-12-11', 'gpt-5.6-terra', OPENAI_DEP),
./omni_prod/intelligence/lifecycle.py:56:    _l('gpt-5-2025-08-07', '2026-12-11', 'gpt-5.6-sol', OPENAI_DEP),
./omni_prod/intelligence/lifecycle.py:57:    _l('gpt-image-1', '2026-10-23', 'gpt-image-2.5-flare', OPENAI_DEP),
./omni_prod/intelligence/lifecycle.py:59:    _l('tts-1', '2027-01-06', 'gpt-realtime-2.1-mini', OPENAI_DEP),
./omni_prod/intelligence/lifecycle.py:60:    _l('whisper-1', '2027-02-26', 'gpt-transcribe', OPENAI_DEP),
./omni_prod/intelligence/lifecycle.py:61:    _l('gpt-6-luna', None, None, OPENAI_DEP),
./omni_prod/intelligence/prices.py:79:    _row('gemini', 'gemini-3.1-flash-lite', src=GOOGLE, inp='0.25', cached='0.025', out='1.50',
./omni_prod/intelligence/prices.py:81:    _row('gemini', 'gemini-3.5-flash-lite', src=GOOGLE, inp='0.30', cached='0.03', out='2.50'),
./omni_prod/intelligence/prices.py:82:    _row('gemini', 'gemini-3.8-flash', src=GOOGLE, until='2027-01-01', inp='0.75', cached='0.075', out='3.75'),
./omni_prod/intelligence/prices.py:83:    _row('gemini', 'gemini-3.8-flash', src=GOOGLE, frm='2027-01-01', inp='1.50', cached='0.15', out='7.50',
./omni_prod/intelligence/prices.py:85:    _row('gemini', 'gemini-2.5-flash-lite', src=GOOGLE, inp='0.10', out='0.40',
./omni_prod/intelligence/prices.py:87:    _row('gemini', 'gemini-3.1-pro-preview', src=GOOGLE, inp='2.00', out='12.00', note='<=200k prompt tokens; preview'),
./omni_prod/intelligence/prices.py:89:    _row('gemini', 'gemini-3.1-flash-lite-image', src=GOOGLE, inp='0.25', image='0.0336', note='per 1K image'),
./omni_prod/intelligence/prices.py:90:    _row('gemini', 'gemini-nano-banana-2.1', src=GOOGLE, inp='1.50', image='0.0336', note='per 1K image; 2K $0.0504, 4K $0.113'),
./omni_prod/intelligence/prices.py:91:    _row('gemini', 'gemini-omni-1.1-flash', src=GOOGLE, inp='1.50', video_s='0.10', note='about $0.10 per second of 720p video'),
./omni_prod/intelligence/prices.py:92:    _row('gemini', 'gemini-3.8-flash-lite-tts', src=GOOGLE, until='2027-01-01', inp='0.50', audio_s='0.00015',
./omni_prod/intelligence/prices.py:94:    _row('gemini', 'gemini-3.8-flash-lite-tts', src=GOOGLE, frm='2027-01-01', inp='1.00', audio_s='0.0003',
./omni_prod/intelligence/prices.py:96:    _row('gemini', 'gemini-3.8-flash-tts', src=GOOGLE, until='2027-01-01', inp='0.50', audio_s='0.000225',
./omni_prod/intelligence/prices.py:98:    _row('gemini', 'gemini-3.8-flash-tts', src=GOOGLE, frm='2027-01-01', inp='1.00', audio_s='0.00045'),
./omni_prod/intelligence/prices.py:99:    _row('gemini', 'lyria-3.5', src=GOOGLE, song='0.08', note='full song'),
./omni_prod/intelligence/prices.py:100:    _row('gemini', 'lyria-3-clip-preview', src=GOOGLE, song='0.04', note='30 s clip; preview'),
./omni_prod/intelligence/prices.py:101:    _row('gemini', 'gemini-embedding-2', src=GOOGLE, inp='0.20', note='text'),
./omni_prod/intelligence/prices.py:103:    _row('openai', 'gpt-6-luna', src=OPENAI, inp='0.10', cached='0.01', out='0.50'),
./omni_prod/intelligence/prices.py:104:    _row('openai', 'gpt-6.1-sol', src=OPENAI, inp='2.00', cached='0.10', out='10.00'),
./omni_prod/intelligence/prices.py:105:    _row('openai', 'gpt-6-astra', src=OPENAI, inp='10.00', cached='1.00', out='50.00'),
./omni_prod/intelligence/prices.py:106:    _row('openai', 'gpt-image-2.5-flare', src=OPENAI, inp='5.00', out='30.00', note='text input $5, image output $30 per 1M tokens'),
./omni_prod/intelligence/prices.py:107:    _row('openai', 'gpt-transcribe', src=OPENAI, minute='0.0045'),
./omni_prod/intelligence/prices.py:109:    _row('anthropic', 'claude-sonnet-5-5', src=ANTHROPIC, inp='2.00', cached='0.10', out='10.00'),
./omni_prod/intelligence/prices.py:110:    _row('anthropic', 'claude-haiku-5-5', src=ANTHROPIC, inp='0.10', cached='0.01', out='0.50', note='<=100k prompt tokens'),
./omni_prod/intelligence/prices.py:111:    _row('anthropic', 'claude-opus-5-5', src=ANTHROPIC, inp='4.00', cached='0.20', out='20.00'),
./tests/test_agent_os.py:102:        self.assertEqual(commercial_status('gemini-3-8-flash')[0], COMMERCIAL_APPROVED)
./tests/test_agent_os.py:103:        self.assertEqual(commercial_status('local-llama')[0], DEV_ONLY)
./tests/test_agent_os.py:105:        kept = filter_routable([Entry('gemini-x'), Entry('local-y')])
./tests/test_agent_os.py:106:        self.assertEqual([e.endpoint.name for e in kept], ['gemini-x'])
./tests/test_conversation_os.py:217:        self.assertEqual(by['T04']['model_candidates'][0], 'gemini-3.8-flash')
./tests/test_conversation_os.py:218:        self.assertEqual(by['T03']['model_candidates'][0], 'gemini-3.8-flash')
./tests/test_conversation_os.py:393:        for fake in ('scheduled', 'artifacts', 'codex', 'gpts', 'sora', 'chatgpt'):
./tests/test_economics_report.py:13:def a(build, task='codegen', metered='0.05', outcome='ok', authorized='0.10', model='gemini-3.8-flash'):
./tests/test_economics_report.py:22:                    a('b2', metered='0.08'), a('b2', task='repair', metered='0.04', model='gemini-3.1-flash-lite'),
./tests/test_economics_report.py:48:        m = self.r['models']['gemini-3.8-flash']
./tests/test_evidence_json.py:25:    'model_route_events': [{'route': 'gemini-3-8-flash', 'max_estimated_cost_usd': Decimal('0.0123')}],
./tests/test_evidence_json.py:50:        evidence = {'endpoint': _Endpoint('gemini', 'AIza-secret-value')}
./tests/test_intake_assistant_he.py:60:        self.assertEqual(est['model'], 'gemini-3.1-flash-lite')
./tests/test_intake_assistant_he.py:66:        for model in ('gemini-3.1-flash-lite', 'gemini-3.5-flash-lite'):                 # verified conversation models
./tests/test_intake_budget_pg.py:31:                            'allowed_models': ['gemini-3.1-flash-lite', 'gemini-3.5-flash-lite']})
./tests/test_intake_budget_pg.py:136:        self.last_usage = ProviderUsage(provider='gemini', model='gemini-3.1-flash-lite', external=True,
./tests/test_intake_worker_route.py:60:def settled(state, cost_state, actual, result, model='gemini-3.1-flash-lite'):
./tests/test_intake_worker_route.py:62:                         None if state != B.UNKNOWN else 'timeout', None, 'gemini', model, result)
./tests/test_intelligence_plane.py:71:        before = prices.price_at('gemini-3.8-flash', date(2026, 12, 31))
./tests/test_intelligence_plane.py:72:        after = prices.price_at('gemini-3.8-flash', date(2027, 1, 1))
./tests/test_intelligence_plane.py:75:        self.assertEqual(len(prices.history('gemini-3.8-flash')), 2)
./tests/test_intelligence_plane.py:78:        self.assertIsNone(prices.price_at('gpt-5-nano'))
./tests/test_intelligence_plane.py:80:            prices.require_price('gpt-5-nano')
./tests/test_intelligence_plane.py:83:        rows = prices.SCHEDULE + (prices._row('gemini', 'gemini-3.8-flash', src=prices.GOOGLE, inp='1', out='1'),)
./tests/test_intelligence_plane.py:89:        self.assertEqual(lifecycle.state('gemini-3.1-flash-lite', date(2026, 10, 11)), lifecycle.DEPRECATION_ANNOUNCED)
./tests/test_intelligence_plane.py:90:        self.assertEqual(lifecycle.state('gemini-3.1-flash-lite', date(2027, 5, 7)), lifecycle.RETIRED)
./tests/test_intelligence_plane.py:91:        self.assertEqual(lifecycle.state('gemini-2.5-flash-lite'), lifecycle.RESTRICTED)
./tests/test_intelligence_plane.py:92:        self.assertEqual(lifecycle.state('gpt-5-nano-2025-08-07', date(2026, 12, 11)), lifecycle.RETIRED)
./tests/test_intelligence_plane.py:93:        self.assertIn('gemini-3.5-flash-lite', lifecycle.warning('gemini-3.1-flash-lite', date(2027, 3, 1)))
./tests/test_intelligence_plane.py:96:        plan = lifecycle.migration_plan('gemini-3.1-flash-lite', when=date(2026, 10, 11))
./tests/test_intelligence_plane.py:97:        self.assertEqual(plan['successor'], 'gemini-3.5-flash-lite')
./tests/test_intelligence_plane.py:100:        self.assertTrue(lifecycle.migration_plan('gpt-5-nano-2025-08-07')['action'].startswith('blocked'))
./tests/test_intelligence_plane.py:114:        raw = _cat(('flash', 'gemini', self.REAL, 'gemini-3.8-flash', 85, '0.75', '3.75'))
./tests/test_intelligence_plane.py:120:        raw = _cat(('nano', 'openai', 'https://api.openai.com/v1', 'gpt-5-nano', 70, '0.05', '0.40'))
./tests/test_intelligence_plane.py:130:        raw = _cat(('old', 'gemini', self.REAL, 'gemini-3.1-flash-lite', 70, '0.25', '1.50'))
./tests/test_intelligence_plane.py:172:        luna = next(e for e in INVENTORY if e.model_key == 'openai-gpt-6-luna')
./tests/test_intelligence_plane.py:174:        haiku = next(e for e in INVENTORY if e.model_key == 'anthropic-claude-haiku-5-5')
./tests/test_intelligence_plane.py:193:        self.assertEqual(verified, {'gemini-3.8-flash', 'gemini-3.1-flash-lite', 'gemini-3.5-flash-lite'})
./tests/test_intelligence_plane.py:196:        self.assertEqual(blocked, {'gpt-6-luna', 'gpt-6.1-sol', 'claude-sonnet-5-5'})
./tests/test_model_catalog_routing.py:28:    {"name": "gemini-nokey", "provider": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
./tests/test_model_transient_retry.py:22:    {"name": "lite", "provider": "gemini", "base_url": "https://gemini.example/v1", "model": "g-lite",
./tests/test_model_transient_retry.py:24:    {"name": "flash", "provider": "gemini", "base_url": "https://gemini.example/v1", "model": "g-flash",
./tests/test_provider_quota_and_dialects.py:242:        self.assertEqual(status['claude-sonnet-5-5'], 'CONFIGURED')
./tests/test_provider_quota_and_dialects.py:243:        self.assertEqual(status['gpt-6.1-sol'], 'NOT_CONFIGURED')
./tests/test_provider_quota_and_dialects.py:244:        sonnet = next(m for m in models if m.option.model == 'claude-sonnet-5-5')
./tests/test_provider_quota_and_dialects.py:247:        sol = next(m for m in sol if m.option.model == 'gpt-6.1-sol')
./tests/test_task_quality_routing.py:16:                        option=ModelOption('gemini', name, quality, 1000, Decimal(inp), Decimal(out)), max_output_tokens=16384, api_key_env='K')
./tests/test_task_quality_routing.py:72:        gw = self._gw(ProviderUsage(provider='gemini', model='flash', external=True, request_id='r', request_id_source='header', response_id='x', input_tokens=1000, output_tokens=1000, cached_tokens=0, provider_reported_cost_usd=None, usage_reported=True))
./tests/test_v22_autonomous_core.py:107:        ep = ModelEndpoint('local', 'http://127.0.0.1:1/v1', 'qwen', external=False)
./tests/test_v23_investor_grade.py:38:        local = ModelEndpoint('local', 'http://local/v1', 'qwen')
./tests/test_v23_investor_grade.py:50:        local = ModelEndpoint('broken-local', 'http://local/v1', 'qwen')
./tests/test_v23_investor_grade.py:63:        local = ModelEndpoint('broken-local', 'http://local/v1', 'qwen')
-- ספירת טוקנים לפי len --
./omni_prod/attachments.py:117:    if not isinstance(text, str) or len(text) > (MAX_BYTES * 4) // 3 + 8:
-- max_tokens --
./omni_prod/autonomous_agents.py:162:        data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=user, max_tokens=6000)
./omni_prod/autonomous_agents.py:175:            data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=correction, max_tokens=6000)
./omni_prod/autonomous_agents.py:191:            max_tokens=24000,
./omni_prod/autonomous_agents.py:219:                system=_REPAIR_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=20000)
./omni_prod/autonomous_agents.py:235:            system=_REPAIR_SYSTEM_V1, user=json.dumps(payload, ensure_ascii=False), max_tokens=12000)
./omni_prod/autonomous_agents.py:251:            max_tokens=2000,
./omni_prod/intake/budget.py:10:                   = max_tokens, which includes reasoning tokens) from the
./omni_prod/intake/budget.py:52:CEILING_BASIS = ('output bound = max_tokens; reasoning/thinking tokens are billed as output and count against '
./omni_prod/intake/budget.py:53:                 'max_tokens for the allowed OpenAI-compatible routes (catalog _thinking_basis notes); '
./omni_prod/intake/budget.py:112:def quote(*, system: str, user: str, max_tokens: int, task: str = 'conversation',
./omni_prod/intake/budget.py:117:    if not isinstance(max_tokens, int) or max_tokens <= 0 or max_calls != 1:
./omni_prod/intake/budget.py:128:            max_out = int(item.get('max_output_tokens', 8192))
./omni_prod/intake/budget.py:139:        out_tokens = min(max_tokens, max_out)
./omni_prod/intake/budget.py:151:                          'models': priced, 'ceiling_basis': CEILING_BASIS, 'max_tokens': max_tokens})
./omni_prod/intake/interpreter.py:314:    def __init__(self, gateway, *, fallback=None, max_tokens: int = MAX_OUTPUT_TOKENS):
./omni_prod/intake/interpreter.py:317:        self.max_tokens = max_tokens
./omni_prod/intake/interpreter.py:325:                                             max_tokens=self.max_tokens, task='conversation')
./omni_prod/intake/interpreter.py:328:        m = meter(self.gateway, {'max_tokens': self.max_tokens})
./omni_prod/intake/reservation_worker.py:60:    bound = int(quote.get('max_tokens') or 0)
./omni_prod/intake/reservation_worker.py:114:                                    max_tokens=int(payload['max_tokens']),
./omni_prod/intake/worker_route.py:61:            quote = B.quote(system=SYSTEM, user=user, max_tokens=MAX_OUTPUT_TOKENS, task=self.task)
./omni_prod/intake/worker_route.py:69:                                 payload={'system': SYSTEM, 'user': user, 'max_tokens': MAX_OUTPUT_TOKENS,
./omni_prod/model_catalog.py:37:    max_output_tokens: int
./omni_prod/model_catalog.py:61:            'max_output_tokens': self.max_output_tokens,
./omni_prod/model_catalog.py:129:            max_out = int(item.get('max_output_tokens', 8192))
./omni_prod/model_catalog.py:141:        reserved = {'model', 'messages', 'system', 'max_tokens', 'max_completion_tokens', 'temperature', 'stream'}
./omni_prod/model_catalog.py:160:        out.append(CatalogModel(option=option, endpoint=endpoint, max_output_tokens=max_out,
./omni_prod/model_gateway.py:116:    # Request dialect: 'openai' (chat/completions with max_tokens + temperature),
./omni_prod/model_gateway.py:117:    # 'openai_reasoning' (chat/completions; GPT-6-class models reject max_tokens
./omni_prod/model_gateway.py:149:                 max_tokens: int = 4096, idempotency_key: str | None = None) -> str:
./omni_prod/model_gateway.py:152:        if max_tokens < 1:
./omni_prod/model_gateway.py:153:            raise ValueError('max_tokens must be positive')
./omni_prod/model_gateway.py:164:                    'messages': [{'role': 'user', 'content': user}], 'max_tokens': max_tokens}
./omni_prod/model_gateway.py:178:                body['max_completion_tokens'] = max_tokens
./omni_prod/model_gateway.py:181:                body['max_tokens'] = max_tokens
./omni_prod/model_gateway.py:237:    def complete_json(self, *, system: str, user: str, max_tokens: int = 4096) -> dict:
./omni_prod/model_gateway.py:238:        raw = self.complete(system=system, user=user, temperature=0, max_tokens=max_tokens)
./omni_prod/model_probe.py:39:                                 max_tokens=min(PROBE_MAX_TOKENS, model.max_output_tokens))
./omni_prod/product_evolution.py:84:            system=_EVOLUTION_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=24000,
./omni_prod/product_review.py:65:        kwargs = dict(system=_REVIEW_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=3000)
./omni_prod/routed_gateway.py:235:        Rehearsal 2026-10-08: each call reserved its worst case (max_tokens
./omni_prod/routed_gateway.py:304:        is never shorter than one byte), output by the requested max_tokens
./omni_prod/routed_gateway.py:312:        requested = int(kwargs.get('max_tokens', 4096))
./omni_prod/routed_gateway.py:326:            out_tokens = min(requested, model.max_output_tokens)
./omni_prod/routed_gateway.py:330:            candidates.append((order, ProviderRoute(model.endpoint, cost), {**kwargs, 'max_tokens': out_tokens}, option))
./omni_prod/routed_gateway.py:362:        current = int(call_kwargs.get('max_tokens', 0))
./omni_prod/routed_gateway.py:374:        return ProviderRoute(route.endpoint, cost), {**call_kwargs, 'max_tokens': allowance}
./omni_prod/routed_gateway.py:437:                                                         f'{why}; output allowance cut to {f_kwargs["max_tokens"]} tokens '
./omni_prod/routed_gateway.py:485:    def complete(self, *, system: str, user: str, temperature: float = 0.1, max_tokens: int = 4096,
./omni_prod/routed_gateway.py:491:            'max_tokens': max_tokens,
./omni_prod/routed_gateway.py:494:    def complete_json(self, *, system: str, user: str, max_tokens: int = 4096, task: str = 'general') -> dict:
./omni_prod/routed_gateway.py:498:            'max_tokens': max_tokens,
./omni_prod/specialist_agents.py:20:        data=self.gateway.complete_json(system=system,user=json.dumps({'spec':spec,'repository':repository_summary},ensure_ascii=False),max_tokens=5000)
./tests/integration/test_live_model.py:8:        data=OpenAICompatibleGateway(ep).complete_json(system='Return only JSON.',user='Return {"ok":true}.',max_tokens=64)
./tests/integration/test_m5_live_llm_usage.py:36:        text = gateway.complete(system="Reply with the single word: pong", user="ping", max_tokens=5)
./tests/m4d2b_local_model_server.py:5:`{model, messages, temperature, max_tokens}`, responding
./tests/test_architect_spec_shape.py:24:    def complete_json(self, *, system, user, max_tokens):
./tests/test_attempt_ledger.py:81:        TaskTaggedGateway(gw, "classification").complete(system="SYS", user="u", max_tokens=600)
./tests/test_attempt_ledger.py:107:        gw.complete(system="s", user="u", max_tokens=100)
./tests/test_failure_injection.py:26:        return _gw(script, self.models, budget).complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_intake_assistant_he.py:166:        self.assertEqual(g.seen['max_tokens'], MAX_OUTPUT_TOKENS)
./tests/test_intake_assistant_he.py:175:        self.assertEqual((len(payload['user']), payload['max_tokens']), (MAX_MESSAGE_CHARS, MAX_OUTPUT_TOKENS))
./tests/test_intake_budget_pg.py:30:    return B.Quote(amount, {'task': 'conversation', 'max_calls': 1, 'max_tokens': 700,
./tests/test_intake_budget_pg.py:34:PAYLOAD = {'system': 'S', 'user': 'מערכת לניהול ציוד', 'max_tokens': 700, 'prompt_version': 'intake-prompt/2-he-first'}
./tests/test_intake_budget_pg.py:164:    return B.quote(system=SYSTEM, user=user, max_tokens=MAX_OUTPUT_TOKENS)
./tests/test_intake_budget_pg.py:176:            B.quote(system='s', user='u', max_tokens=700, models=('no-such-model',))
./tests/test_intake_budget_pg.py:178:            B.quote(system='s', user='u', max_tokens=0)
./tests/test_intake_budget_pg.py:180:            B.quote(system='s', user='u', max_tokens=700, max_calls=2)
./tests/test_intake_budget_pg.py:192:        routes = gw.ranked_routes({'system': SYSTEM, 'user': 'א' * 4000, 'max_tokens': MAX_OUTPUT_TOKENS},
./tests/test_j1_real_agent_feature_flag.py:53:        self.assertEqual(gw.calls[0]["max_tokens"], 20000)
./tests/test_j1_real_agent_feature_flag.py:63:        self.assertEqual(gw.calls[0]["max_tokens"], 12000)
./tests/test_model_catalog_routing.py:21:     "max_output_tokens": 2000},
./tests/test_model_catalog_routing.py:45:        _FakeGateway.calls.append((self.endpoint.name, kw["max_tokens"]))
./tests/test_model_catalog_routing.py:91:        self.assertEqual(gw.complete(system="s", user="u", max_tokens=500), "ok:groq-mid")
./tests/test_model_catalog_routing.py:101:        self.assertEqual(gw.complete(system="s", user="u", max_tokens=100), "ok:openai-top")
./tests/test_model_catalog_routing.py:104:    def test_max_tokens_clamped_to_model_limit(self):
./tests/test_model_catalog_routing.py:106:        gw.complete(system="s", user="u", max_tokens=9000)
./tests/test_model_catalog_routing.py:112:        gw.complete(system="", user=user, max_tokens=1000)
./tests/test_model_catalog_routing.py:127:            gw.complete(system="s", user="u" * 100, max_tokens=1000)
./tests/test_model_catalog_routing.py:144:        gw.complete(system="s", user="u", max_tokens=100)
./tests/test_modification_context.py:30:    def complete_json(self, *, system, user, max_tokens):
./tests/test_product_evolution.py:26:    max_tokens) -> dict, without any HTTP -- the same substitution
./tests/test_product_evolution.py:33:    def complete_json(self, *, system, user, max_tokens):
./tests/test_product_evolution.py:34:        self.calls.append({'system': system, 'user': user, 'max_tokens': max_tokens})
./tests/test_provider_quota_and_dialects.py:27:                        max_output_tokens=16384, api_key_env='K')
./tests/test_provider_quota_and_dialects.py:76:        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen'), {'ok': 'backup'})
./tests/test_provider_quota_and_dialects.py:82:        gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_provider_quota_and_dialects.py:90:            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_provider_quota_and_dialects.py:102:            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_provider_quota_and_dialects.py:110:        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen'), {'ok': 'strong'})
./tests/test_provider_quota_and_dialects.py:119:            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_provider_quota_and_dialects.py:126:            gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_provider_quota_and_dialects.py:145:        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=10000, task='codegen'), {'ok': 'cheap'})
./tests/test_provider_quota_and_dialects.py:152:            gw.complete_json(system='s', user='u', max_tokens=10000, task='codegen')
./tests/test_provider_quota_and_dialects.py:160:            gw.complete_json(system='s', user='u', max_tokens=100)
./tests/test_provider_quota_and_dialects.py:187:        return gw, gw.complete(system='sys', user='hi', max_tokens=300), seen
./tests/test_provider_quota_and_dialects.py:195:        self.assertNotIn('max_tokens', seen['body'])
./tests/test_provider_quota_and_dialects.py:203:        self.assertEqual(seen['body']['max_tokens'], 300)
./tests/test_provider_quota_and_dialects.py:222:        payload = {'content': [{'type': 'thinking', 'thinking': '...'}], 'stop_reason': 'max_tokens',
./tests/test_provider_quota_and_dialects.py:224:        with self.assertRaisesRegex(ModelGatewayError, 'max_tokens'):
./tests/test_provider_quota_and_dialects.py:257:            parse_model_catalog(json.dumps([{**base, 'extra_body': {'max_tokens': 1}}]), {})
./tests/test_provider_quota_and_dialects.py:286:                                    max_output_tokens=10, api_key_env='OFF_KEY')
./tests/test_provider_quota_and_dialects.py:309:        out = gw.complete_json(system='s', user='u' * 2000, max_tokens=20000, task='repair')
./tests/test_provider_quota_and_dialects.py:317:        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=10000, task='repair'), {'ok': 'weak'})
./tests/test_provider_quota_and_dialects.py:322:        self.assertEqual(gw.complete_json(system='s', user='u', max_tokens=20000, task='architecture'), {'ok': 'weak'})
./tests/test_provider_quota_and_dialects.py:331:        gw.complete_json(system='s', user='u', max_tokens=1000, task='codegen')
./tests/test_skills_runtime_and_review.py:161:                                option=ModelOption('p', name, q, 1000, Decimal(price), Decimal(price)), max_output_tokens=4000, api_key_env='K')
./tests/test_skills_runtime_and_review.py:166:        kw = {'system': 's', 'user': 'u', 'max_tokens': 100}
./tests/test_task_quality_routing.py:16:                        option=ModelOption('gemini', name, quality, 1000, Decimal(inp), Decimal(out)), max_output_tokens=16384, api_key_env='K')
./tests/test_task_quality_routing.py:25:        self.kw = {'system': 's', 'user': 'u', 'max_tokens': 1000}
./tests/test_task_quality_routing.py:73:        gw.complete_json(system='s', user='u', max_tokens=16000)
./tests/test_task_quality_routing.py:79:        gw.complete_json(system='s', user='u', max_tokens=16000)
./tests/test_worker_budget_binding.py:65:            gw.complete(system="s", user="u", max_tokens=100)
```


## F3 — תבניות פרומפט

```
omni_prod/autonomous_core.py:64:        diagnostic = '\n'.join(str(f.get('message', '')) + '\n' + str(f.get('evidence', ''))
omni_prod/autonomous_core.py:169:                'first_failure': (failures[0].get('message', '') + ' | ' + (failures[0].get('evidence') or '')[-300:])
omni_prod/behavior_acceptance.py:183:                               report.build_log + '\n' + message)
omni_prod/browser_probe.py:197:        message = 'the product misbehaves in a real browser: ' + '; '.join(f['message'] for f in blocking[:4])
omni_prod/browser_probe.py:203:                               report.build_log + '\n' + message)
omni_prod/capability_executor.py:318:                f"{state.error_code or state.status}: {state.error_message or 'provider execution failed'}"
omni_prod/conversation/store.py:132:            r = conn.execute(f"SELECT {self._MSG} FROM intake_messages WHERE project_id = %s AND request_key = %s AND role = 'assistant'",
omni_prod/creator_plan.py:103:                             "message": f"{row['kind']}: {row['reason']}"})
omni_prod/creator_plan.py:107:                         "message": f"Product icon generation: {(image_readiness or {}).get('reason', 'not configured')}"})
omni_prod/demo_project.py:13:    cleaned = re.sub(r'\s+', ' ', prompt).strip()
omni_prod/discovery.py:415:_FONT = {'heebo': "'Heebo', system-ui, sans-serif", 'assistant': "'Assistant', system-ui, sans-serif",
omni_prod/discovery.py:416:         'rubik': "'Rubik', system-ui, sans-serif", 'system': 'system-ui, sans-serif'}
omni_prod/intake/contract.py:152:    text_all = brief.prompt + ' ' + ' '.join(str(x) for x in v.values())
omni_prod/intake/interpreter.py:175:            json.dumps(context, ensure_ascii=False)[:2400] + '\nCurrent customer message:\n' + current)
omni_prod/investor_app.py:772:        effective=req.prompt if not context else req.prompt+'\n\nExisting project memory (preserve unless the new request conflicts):\n'+context
omni_prod/investor_app.py:2115:    return (row.brief.prompt + '\n' + d.requirements_text(row.brief))[:12000], row
omni_prod/model_gateway.py:165:            url = self.endpoint.base_url.rstrip('/') + '/messages'
omni_prod/modifier_engine.py:160:    text = ' '.join(f"{f.get('message', '')} {f.get('evidence', '')}" if isinstance(f, dict) else str(f) for f in failures)
omni_prod/postdeploy_checks.py:484:    revision, _ = run_discovery(token, project, CANCEL_PROMPT + ' ב')
omni_prod/postdeploy_checks.py:485:    b = plan_and_build(token, project, revision, CANCEL_PROMPT + ' ב')
omni_prod/postdeploy_checks.py:516:           [f"{e['kind']}: {e['message']}" for e in events][:8])
omni_prod/postdeploy_checks.py:545:           f"version={d.get('result_version_id')} message={str(d.get('error_message'))[:300]}")
omni_prod/postdeploy_checks.py:555:    record('build journal', len(events) >= 3, [f"{e['kind']}: {e['message']}" for e in events][:14])
omni_prod/postdeploy_checks.py:615:           f"reservation={reservation(b)} events={[e['message'] for e in events if e['kind'] in ('info', 'phase')][-4:]}")
omni_prod/product_architect.py:393:                summary=f"Self-contained Web app contract for: {prompt}",
omni_prod/product_architect.py:400:            summary=f"M5 managed Web/SaaS contract for: {prompt}",
omni_prod/product_architect.py:421:        return ProductSpec(title=title, summary=f"Content-only Web site contract for: {prompt}",
omni_prod/rehearsal.py:122:        lines.append(note(f"failure {i + 1} {f['id']}", f['message'] + '\n' + f['evidence']))
omni_prod/routed_gateway.py:310:        text = f"{kwargs.get('system', '')}{kwargs.get('user', '')}"
omni_prod/routed_gateway.py:363:        text = f"{call_kwargs.get('system', '')}{call_kwargs.get('user', '')}"
omni_prod/unified_engine.py:51:        clean = re.sub(r'\s+', ' ', prompt).strip()
omni_prod/worker.py:42:    print(time.strftime("%H:%M:%S") + " " + message, flush=True)
omni_prod/worker_tasks.py:519:                                                'after repair: ' + '; '.join(f.message for f in report_failures))[:2000]
omni_prod/worker_tasks.py:525:                + '; '.join(f.message for f in report_failures))[:2000]
```


## G1 — מספרים קסומים

```
omni_prod/account_tenant.py:37:        if len(token_secret)<32: raise ValueError('token_secret must be at least 32 chars')
omni_prod/account_tenant.py:47:        if len(password)<10: raise ValueError('password must be at least 10 characters')
omni_prod/active_jobs.py:63:        out['running_builds_with_old_heartbeat'] = [b[0] for b in running if b[2] > 900 and b[0] not in ack]
omni_prod/active_jobs.py:133:    return {k: (v[:10] + [f'... +{len(v) - 10} more'] if isinstance(v, list) and len(v) > 10 else v) for k, v in snap.items()}
omni_prod/attachments.py:91:                h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
omni_prod/attachments.py:154:        if not isinstance(note, str) or len(note) > 500:
omni_prod/auth.py:23:    if len(secret)<32: raise ValueError('auth secret must be at least 32 chars')
omni_prod/auth.py:37:    if len(secret)<32: raise AuthError('auth secret unavailable')
omni_prod/autonomous_agents.py:200:    '"base_repository_fingerprint":"sha256:<64 lowercase hex>",'
omni_prod/behavior_acceptance.py:84:    while executor is not None and seen < 20:
omni_prod/billing.py:22:            if not isinstance(value, str) or not value.strip() or len(value) > 300:
omni_prod/browser_probe.py:119:            ok_write = any(200 <= r[2] < 300 for r in writes)
omni_prod/canary_controller.py:28:            status="complete" if new_percent == 100 else "running",
omni_prod/capability_verification.py:24:    if len(prefix) < 20:
omni_prod/capability_verification.py:57:        if len(prefix) < 12 or prefix[:4] != b"RIFF" or prefix[8:12] != b"WEBP":
omni_prod/capability_verification.py:61:        if len(prefix) < 12 or prefix[:4] != b"RIFF" or prefix[8:12] != b"WAVE":
omni_prod/config.py:45:        if env == "production" and len(secret) < 48:
omni_prod/creator_accounts.py:19:        if len(token_secret) < 32:
omni_prod/gate_replay.py:76:            if len(out['examples']) < 12:
omni_prod/gate_replay.py:80:            if len(out['examples']) < 12:
omni_prod/identity_lifecycle.py:396:        if len(token_secret) < 32:
omni_prod/identity_lifecycle.py:433:        if len(password) < 10:
omni_prod/identity_lifecycle.py:542:        if len(new_password) < 10:
omni_prod/intake/budget.py:209:        if not isinstance(v, str) or not v or ':' in v or len(v) > 128:
omni_prod/intake/budget.py:274:        if not idempotency_key or len(idempotency_key) > 300:
omni_prod/intake/complexity.py:148:    if len(complex_hits) >= 2 or (len(message) > 600 and clauses >= 6):
omni_prod/intake/contract.py:88:    if not c.project_goal.strip() or len(c.project_goal) > 2000:
omni_prod/intake/contract.py:97:        if not r.text.strip() or len(r.text) > 2000:
omni_prod/intake/interpreter.py:150:        reqs = [s.strip() for s in re.split(r'(?:\n|•|;|(?<=[.!?])\s)', message or '') if len(s.strip()) > 12][:12]
omni_prod/intake/interpreter.py:268:        if len(val) > 2000 or len(ev) > 500:
omni_prod/intake/interpreter.py:288:    if not isinstance(reply,str) or len(reply)>600:
omni_prod/intelligence/health.py:47:    if status == 402 or 'credit balance' in text or 'no credits' in text or 'insufficient_quota' in text \
omni_prod/intelligence/health.py:50:    if status == 403:
omni_prod/intelligence/health.py:52:    if status == 404 and ('model' in text and ('not found' in text or 'does not exist' in text)):
omni_prod/intelligence/health.py:54:    if status == 429 and any(k in text for k in ('quota', 'resource_exhausted', 'rate limit', 'too many')):
omni_prod/intelligence/health.py:56:    if status == 429:
omni_prod/intelligence/health.py:58:    if status is not None and 500 <= status < 600:
omni_prod/intent_terms.py:19:    return all(ord(ch) < 128 for ch in term)
omni_prod/investor_app.py:3082:    return HTMLResponse('<!doctype html><meta charset="utf-8"><title>148AI R2 diagnostic</title>'
omni_prod/investor_app.py:3083:        '<h1>148AI Preview: R2 configuration fingerprints</h1><pre>' + payload + '</pre>',
omni_prod/model_catalog.py:114:        if not model or len(model) > 200 or any(c in model for c in '\r\n'):
omni_prod/model_gateway.py:73:    if status == 400:
omni_prod/model_gateway.py:90:    if status == 402:
omni_prod/planning/graph.py:109:            if t.max_iterations < 1 or (t.max_iterations > 1 and t.max_iterations > 10):
omni_prod/postdeploy_checks.py:133:            if http('GET', BASE + '/api/v28/m5/status', timeout=3)[0] == 200:
omni_prod/postdeploy_checks.py:211:        if s == 200 and b.get('status') in ('RUNNING', 'FAILED', 'NOT_PREVIEWABLE', 'EXPIRED', 'STOPPED'):
omni_prod/postdeploy_checks.py:233:        return b if s == 200 and b.get('status') in ('STOPPED', 'EXPIRED') else None
omni_prod/postdeploy_checks.py:342:           and (max(versions) < 32 or access_table),
omni_prod/postdeploy_checks.py:387:    ok = all(v == 410 for k, v in refused.items() if k.endswith(('/build', '/patch')) or k.startswith('GET ')) and \
omni_prod/postdeploy_checks.py:388:        all(v == 501 for k, v in refused.items() if k.endswith('/promote'))
omni_prod/postdeploy_checks.py:397:    record('projects load + journal endpoint', s == 200 and any(p.get('id') == project for p in listed.get('projects', []))
omni_prod/postdeploy_checks.py:398:           and s2 == 200 and latest == {'build': None}, f'projects={s} latest={s2} {latest}')
omni_prod/postdeploy_checks.py:410:    record('preview is private by default', anon[0] == 401 and view.get('access_mode') == 'PRIVATE',
omni_prod/postdeploy_checks.py:437:        record('share link works only while shared', s_sh == 200 and shared == 200 and revoked == 401,
omni_prod/postdeploy_checks.py:443:    record('versions listed', s == 200 and len(hist.get('versions', [])) == 2, f'history={s} versions={len(hist.get("versions", []))}')
omni_prod/postdeploy_checks.py:460:    record('ZIP export of a version', es == 200 and expected <= names,
omni_prod/postdeploy_checks.py:465:    record('rollback restores the exact stored version', s_rb == 200 and bool(new_id) and new_id != v1.id
omni_prod/postdeploy_checks.py:482:    record('queued build cancelled', s == 200 and out.get('outcome') == 'cancelled' and row[0] == 'cancelled'
omni_prod/postdeploy_checks.py:498:        return d if s == 200 and d.get('status') in ('ready', 'failed', 'cancelled') else None
omni_prod/postdeploy_checks.py:514:    record('journal resumes after refresh', s == 200 and any(e['kind'] == 'cancel' for e in events)
omni_prod/postdeploy_checks.py:519:    record('cancel is owner/project scoped', s3 == 404, f'cancel via another project -> {s3}')
omni_prod/postdeploy_checks.py:569:        return v if s == 200 and v.get('acceptance_status') not in (None, 'NOT_CONFIGURED', 'PENDING') else None
omni_prod/postdeploy_checks.py:574:           bool(v2) and page[0] == 200 and (v3 or {}).get('status') == 'RUNNING',
omni_prod/postdeploy_checks.py:608:        return d if s == 200 and d.get('status') in ('ready', 'failed', 'cancelled') else None
omni_prod/preflight.py:38:    if not secret or len(secret) < 48 or not _non_placeholder(secret):
omni_prod/preview_access.py:144:            if len(self._denied) > 5000:
omni_prod/preview_repository.py:156:            'data_storage': row[14] if len(row) > 14 else None,
omni_prod/preview_repository.py:157:            'access_mode': row[15] if len(row) > 15 else None,
omni_prod/preview_router.py:5:- GET /_health                 -> 200 "ok"
omni_prod/preview_router.py:6:- GET /_caddy_ask?domain=HOST  -> 200 only for a RUNNING, unexpired preview on
omni_prod/preview_runtime.py:82:    """The deployment cannot run previews correctly (API -> 503)."""
omni_prod/preview_runtime.py:152:    if (not isinstance(start, list) or not start or len(start) > 64
omni_prod/preview_runtime.py:269:    if not label.startswith('prv-') or not all(c in '0123456789abcdef' for c in label[4:]) or len(label) < 12:
omni_prod/preview_runtime.py:339:            if 200 <= status < 400:
omni_prod/preview_smoke.py:46:            verdict = "OK" if 200 <= r.status < 400 else "HTTP %%s" %% r.status
omni_prod/preview_smoke.py:78:        elif len(page.strip()) + len(assets.strip()) < 400 or not any(t in whole for t in controls):
omni_prod/project_manifest.py:53:            if len(out) > 64:
omni_prod/project_manifest.py:58:        if len(builds) > 16:
omni_prod/project_manifest.py:71:        if len(checks) > 64:
omni_prod/project_memory.py:41:        if max_chars < 128:
omni_prod/providers/image_provider.py:392:            if exc.code == 429:
omni_prod/providers/image_provider.py:396:            if 400 <= exc.code < 500:
omni_prod/providers/image_provider.py:416:            if exc.code == 429:
omni_prod/providers/managed_web_saas.py:397:            return code in {"AccessDenied", "403", "Forbidden"} or status == 403
omni_prod/providers/managed_web_saas.py:621:        if not 200 <= status_code < 300:
omni_prod/providers/qstash_scheduler.py:60:        if body is not None and len(body) > 65536:
omni_prod/providers/qstash_scheduler.py:68:                if not 200 <= status < 300:
omni_prod/providers/qstash_scheduler.py:71:                if len(raw) > 262144:
omni_prod/providers/qstash_scheduler.py:77:            if missing_ok and status == 404:
omni_prod/providers/qstash_scheduler.py:161:            if not callable(claim_once) or not isinstance(body, bytes) or len(body) > 1048576:
omni_prod/providers/qstash_scheduler.py:163:            if not isinstance(signature, str) or len(signature) > 16384:
omni_prod/provider_router.py:219:        if 200 <= status_code < 400:
omni_prod/provider_router.py:224:        if status_code == 429 or normalized_error in {"rate_limit", "rate_limited"}:
omni_prod/quality_gate.py:51:        notes = [] if coverage == 100 else [f'acceptance traceability {coverage}%']
omni_prod/quality_gate.py:53:        if coverage < 100:
omni_prod/remote_sandbox.py:22:        if len(self.shared_secret)<32: raise ValueError('sandbox shared secret must be at least 32 chars')
omni_prod/repair_contracts.py:243:        if not path or len(path) > 320:
omni_prod/sandbox_request_policy.py:51:                any(ord(c) < 32 or ord(c) == 127 for c in path)):
omni_prod/sandbox_service.py:52:    if len(secret)<32: raise HTTPException(503,'sandbox shared secret not configured')
omni_prod/secrets_manager.py:241:            if exc.status == 401:
omni_prod/skills_runtime.py:117:    if declarations < 40:
omni_prod/unified_engine.py:308:            'SOURCE_READY', 'SOURCE_READY', launch_score, launch_score == 100, version.checksum,
omni_prod/visual_edit.py:113:    if href and len(href) < 150:
omni_prod/visual_qa.py:72:  if (heb > 20 && heb > lat && getComputedStyle(document.body).direction !== 'rtl') add('rtl_mismatch', document.body, 'Hebrew text rendered ' + getComputedStyle(document.body).direction);
omni_prod/visual_qa.py:77:    if (mobile && (r.width < 24 || r.height < 24) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'))
omni_prod/visual_qa.py:103:    if (checked > 300) break;
omni_prod/visual_qa.py:108:    if (mobile && size < 12) add('tiny_text', el, size + 'px');
omni_prod/visual_qa.py:141:        if len(shot) * 4 // 3 < 70000:
omni_prod/worker_tasks.py:1443:    WHERE l.depth < 64
```


## G2 — קבועים כפולים

```
-- קרדיטים --
./omni_prod/investor_app.py:1716:_M5_BUILD_CREDITS = 60
./omni_prod/investor_app.py:2698:_MODIFICATION_CREDITS = int(os.getenv('OMNI_MODIFICATION_CREDITS', '30'))
-- מחירים --
./omni_prod/agent_os/meta.py:26:CAPABILITY = ROOT / 'PLATFORM_CAPABILITY_MATRIX.json'
./omni_prod/capability_planner.py:13:ASSET_CAPABILITY_KEYS = {
./omni_prod/capability_worker.py:19:DEFAULT_NATIVE_BUILD_CAPABILITIES = frozenset({
./omni_prod/company_loss.py:31:BUDGET_CAPPED_SHORTFALL = 'budget_capped_shortfall'
./omni_prod/conversation/supervisor.py:54:_CAP_HE = {'payments': 'תשלומים', 'sign-in': 'התחברות משתמשים', 'email': 'שליחת מיילים', 'sms': 'הודעות SMS/וואטסאפ',
./omni_prod/intake/budget.py:51:DEFAULT_CAMPAIGN_CAP = Decimal('10')            # Issue #12: acceptance-test campaign hard ceiling
./omni_prod/intelligence/governance.py:13:OMNI_PRICE_GOVERNANCE=off disables the fail-closed rule (diagnostics only);
./omni_prod/model_gateway.py:277:_BAD_ESCAPE = re.compile(r'(?<!\\)((?:\\\\)*)\\(?=[^"\\/bfnrtu])')
./omni_prod/pricing.py:28:_COST_CLASS_ESTIMATE_USD = {
./omni_prod/providers/http_media_provider.py:18:_KIND_BY_CAPABILITY = {
./omni_prod/providers/image_provider.py:58:CAPABILITY_KEY = "media.image.generate"
./omni_prod/provider_pricing.py:13:    PUBLIC_LIST_PRICE = "PUBLIC_LIST_PRICE"
./omni_prod/stripe_billing.py:20:_PRICE_ENV = {
./omni_prod/unified_engine.py:23:BASE_CAPABILITIES = {'analytics', 'auth', 'export', 'roles', 'search'}
./omni_prod/unified_engine.py:107:    return f'''# Omni capability: {cap}\nCAPABILITY = {cap!r}\nENABLED = True\n'''
```


## H1 — באגים קלאסיים

```
-- ארגומנט ברירת מחדל משתנה --
./omni_prod/memory_adapters.py:6:    def __init__(self): self.jobs={}
./omni_prod/memory_adapters.py:18:    def __init__(self): self.objects={}
./omni_prod/memory_adapters.py:25:    def __init__(self): self.history=[]
./tests/test_m495_worker_capabilities.py:32:    def __init__(self): self.calls=[]
./tests/test_m495_worker_capabilities.py:43:    def __init__(self): self.calls=[]
-- is מול == --
./omni_prod/active_jobs.py:19:    other queue registered in Redis, and any RQ worker whose state is 'busy'.
./omni_prod/attempt_ledger.py:125:          never retried automatically, so it is 0 for them.
./omni_prod/autonomous_agents.py:42:    "Security criteria describe safe handling, not an error code: e.g. a name containing quotes or SQL is "
./omni_prod/autonomous_core.py:191:                                  'message': 'Your previous change made the product worse and was discarded; this is '
./omni_prod/failure_replay.py:16:worker host does), and it never says a build is "fixed".
./omni_prod/maintenance.py:11:   the stale limit (default 45 minutes; the job timeout is 15) are moved to
./omni_prod/preview_smoke.py:26:    'use only the Python standard library (no install step runs), write only under /tmp (the rest is '
./omni_prod/subscription_store.py:339:                        # whole shortfall is 148AI's own loss.
./tests/m4d2b_local_model_server.py:91:                'server standing in for a real LLM (no external provider is '
./tests/test_m49_sandbox_security.py:249:        # Confirm the production default really is 256 before relying on
./tests/test_plan_driven_execution.py:224:        engine, gw = self.engine(rec, gen_cost='0.25')        # plan cap for T04 is 0.20
./tests/test_preview_data_durability.py:176:        # The copy is "dead" from the start: it never becomes healthy -> ERROR report, preview stays.
./tests/test_v23_investor_grade.py:107:        # Canonical brand is 148AI (the legacy "Omni Creator" name was retired with M5-UX01).
-- dict.get ואז חשבון --
```


## H2 — סכמה ומיגרציות

```
-- מיגרציות --
-- timestamp --
./infra/postgres/001_control_plane.sql:6:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/001_control_plane.sql:7:    started_at      TIMESTAMPTZ,
./infra/postgres/001_control_plane.sql:8:    finished_at     TIMESTAMPTZ,
./infra/postgres/001_control_plane.sql:24:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/001_control_plane.sql:25:    retired_at      TIMESTAMPTZ
./infra/postgres/002_usage.sql:9:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/003_resilience.sql:6:    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/003_resilience.sql:7:    expires_at          TIMESTAMPTZ,
./infra/postgres/003_resilience.sql:18:    seen_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/003_resilience.sql:27:    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/004_orchestration.sql:13:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/005_release_engineering.sql:5:    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/005_release_engineering.sql:16:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/005_release_engineering.sql:29:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/006_preflight_release.sql:10:    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/007_supply_chain.sql:7:    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/008_outbox_recovery.sql:8:    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/008_outbox_recovery.sql:9:    published_at TIMESTAMPTZ,
./infra/postgres/008_outbox_recovery.sql:11:    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/008_outbox_recovery.sql:25:    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/009_observability_recovery.sql:8:    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
./infra/postgres/009_observability_recovery.sql:9:    verified_at TIMESTAMPTZ
./infra/postgres/009_observability_recovery.sql:18:    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
./infra/postgres/010_international_product.sql:4:  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/010_international_product.sql:10:  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
./infra/postgres/010_international_product.sql:19:  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/010_international_product.sql:27:  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/010_international_product.sql:37:  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/010_international_product.sql:43:  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
./infra/postgres/011_creator_accounts.sql:6:    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/011_creator_accounts.sql:12:    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
./infra/postgres/011_creator_accounts.sql:13:    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/012_creator_subscriptions.sql:7:    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/013_durable_async_builds.sql:17:    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
./infra/postgres/013_durable_async_builds.sql:18:    resolved_at TIMESTAMPTZ
./infra/postgres/013_durable_async_builds.sql:30:    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/013_durable_async_builds.sql:52:    enqueued_at TIMESTAMPTZ,
./infra/postgres/013_durable_async_builds.sql:53:    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
./infra/postgres/014_real_running_preview.sql:15:    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
./infra/postgres/014_real_running_preview.sql:16:    expires_at TIMESTAMPTZ NOT NULL
-- ON DELETE --
./infra/postgres/010_international_product.sql:7:  organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
./infra/postgres/011_creator_accounts.sql:10:    owner_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/postgres/012_creator_subscriptions.sql:2:    user_id TEXT PRIMARY KEY REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/postgres/017_capability_foundation.sql:5:    build_id TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
./infra/postgres/018_identity_lifecycle.sql:12:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/postgres/018_identity_lifecycle.sql:26:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/postgres/018_identity_lifecycle.sql:39:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/postgres/018_identity_lifecycle.sql:49:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/postgres/020_m5_build_contracts.sql:7:    project_id TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE RESTRICT,
./infra/postgres/020_m5_build_contracts.sql:37:    ADD COLUMN IF NOT EXISTS build_contract_id TEXT REFERENCES m5_build_contracts(id) ON DELETE RESTRICT;
./infra/postgres/030_project_briefs_and_approvals.sql:15:    project_id   TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE CASCADE,
./infra/postgres/030_project_briefs_and_approvals.sql:44:    project_id            TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE CASCADE,
./infra/postgres/031_build_cancel_and_events.sql:21:    build_id   TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
./infra/postgres/032_preview_access.sql:22:    preview_id   TEXT NOT NULL REFERENCES project_previews(id) ON DELETE CASCADE,
./infra/postgres/034_agent_runtime.sql:26:    run_id           TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
./infra/postgres/034_agent_runtime.sql:46:    run_id     TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
./infra/postgres/040_build_request_idempotency.sql:14:        REFERENCES build_requests(build_id) ON DELETE CASCADE
./infra/staging/bootstrap_neon_empty.sql:257:  organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:309:    owner_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:320:    user_id TEXT PRIMARY KEY REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:587:    build_id TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:688:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:702:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:715:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:725:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:765:    project_id TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE RESTRICT,
./infra/staging/bootstrap_neon_empty.sql:795:    ADD COLUMN IF NOT EXISTS build_contract_id TEXT REFERENCES m5_build_contracts(id) ON DELETE RESTRICT;
./infra/staging/bootstrap_neon_empty.sql:1055:    project_id   TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1084:    project_id            TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1124:    build_id   TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1162:    preview_id   TEXT NOT NULL REFERENCES project_previews(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1246:    run_id           TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1266:    run_id     TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1580:        REFERENCES build_requests(build_id) ON DELETE CASCADE
./infra/staging/bootstrap_neon_empty.sql:1849:  organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1900:    owner_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:1910:    user_id TEXT PRIMARY KEY REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:2172:    build_id TEXT NOT NULL REFERENCES build_jobs(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:2272:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
./infra/staging/bootstrap_neon_empty.sql:2286:    user_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
-- CHECK --
./infra/postgres/002_usage.sql:6:    quantity        NUMERIC(30, 6) NOT NULL CHECK (quantity >= 0),
./infra/postgres/003_resilience.sql:25:    maximum         NUMERIC(30, 6) NOT NULL CHECK (maximum >= 0),
./infra/postgres/005_release_engineering.sql:27:    test_count      INTEGER NOT NULL CHECK (test_count >= 0),
./infra/postgres/008_outbox_recovery.sql:7:    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
./infra/postgres/009_observability_recovery.sql:6:    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
./infra/postgres/010_international_product.sql:9:  role TEXT NOT NULL CHECK (role IN ('owner','admin','developer','designer','viewer','billing')),
./infra/postgres/012_creator_subscriptions.sql:5:    credits_used INTEGER NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
./infra/postgres/012_creator_subscriptions.sql:6:    provider_spend_usd NUMERIC(14,6) NOT NULL DEFAULT 0 CHECK (provider_spend_usd >= 0),
./infra/postgres/013_durable_async_builds.sql:12:    credits_reserved INTEGER NOT NULL CHECK (credits_reserved >= 0),
./infra/postgres/013_durable_async_builds.sql:16:    status TEXT NOT NULL CHECK (status IN ('RESERVED', 'SETTLED', 'RELEASED')),
./infra/postgres/014_real_running_preview.sql:11:    status TEXT NOT NULL CHECK (status IN ('STARTING', 'RUNNING', 'STOPPED', 'FAILED', 'EXPIRED')),
./infra/postgres/015_preview_lifecycle_and_async_build_parity.sql:11:    CHECK (status IN ('STARTING', 'RUNNING', 'STOPPED', 'FAILED', 'EXPIRED', 'NOT_PREVIEWABLE'));
./infra/postgres/015_preview_lifecycle_and_async_build_parity.sql:19:    ADD COLUMN IF NOT EXISTS host_port INTEGER CHECK (host_port IS NULL OR (host_port BETWEEN 1 AND 65535)),
./infra/postgres/016_durable_modifications.sql:60:    status TEXT NOT NULL CHECK (status IN (
./infra/postgres/016_durable_modifications.sql:64:    classification TEXT CHECK (classification IN ('system_bug', 'missing_requirement', 'change_request', 'ambiguous')),
./infra/postgres/017_capability_foundation.sql:10:    quantity INTEGER NOT NULL CHECK (quantity >= 1),
./infra/postgres/017_capability_foundation.sql:13:    status TEXT NOT NULL DEFAULT 'PLANNED' CHECK (
./infra/postgres/017_capability_foundation.sql:27:    CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
./infra/postgres/017_capability_foundation.sql:28:    CHECK (maximum_cost_usd IS NULL OR maximum_cost_usd >= COALESCE(estimated_cost_usd, 0)),
./infra/postgres/017_capability_foundation.sql:29:    CHECK (actual_cost_usd IS NULL OR actual_cost_usd >= 0),
./infra/postgres/017_capability_foundation.sql:50:    status TEXT NOT NULL DEFAULT 'SUBMITTING' CHECK (
./infra/postgres/017_capability_foundation.sql:77:    estimated_cost_usd NUMERIC(18,8) NOT NULL CHECK (estimated_cost_usd >= 0),
./infra/postgres/017_capability_foundation.sql:78:    maximum_cost_usd NUMERIC(18,8) NOT NULL CHECK (maximum_cost_usd >= estimated_cost_usd),
./infra/postgres/017_capability_foundation.sql:83:    CHECK (actual_cost_usd IS NULL OR actual_cost_usd >= 0),
./infra/postgres/018_identity_lifecycle.sql:18:    CHECK (expires_at > created_at)
./infra/postgres/018_identity_lifecycle.sql:27:    purpose TEXT NOT NULL CHECK (purpose IN ('EMAIL_VERIFY','PASSWORD_RESET')),
./infra/postgres/018_identity_lifecycle.sql:32:    CHECK (expires_at > created_at)
./infra/postgres/018_identity_lifecycle.sql:50:    request_type TEXT NOT NULL CHECK (request_type IN ('DATA_EXPORT','ACCOUNT_DELETION')),
./infra/postgres/018_identity_lifecycle.sql:51:    status TEXT NOT NULL CHECK (status IN ('REQUESTED','PROCESSING','COMPLETED','REJECTED')),
./infra/postgres/020_m5_build_contracts.sql:8:    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
./infra/postgres/020_m5_build_contracts.sql:9:    status TEXT NOT NULL CHECK (status IN ('READY','NEEDS_CLARIFICATION','BLOCKED')),
./infra/postgres/021_generated_app_bindings.sql:12:    environment TEXT NOT NULL CHECK (environment IN ('preview','production')),
./infra/postgres/021_generated_app_bindings.sql:13:    kind TEXT NOT NULL CHECK (kind IN ('database','auth_session','object_storage','scheduled_http','outbound')),
./infra/postgres/021_generated_app_bindings.sql:14:    status TEXT NOT NULL CHECK (status IN ('LIVE','NOT_CONFIGURED','BLOCKED','REVOKED')),
./infra/postgres/021_generated_app_bindings.sql:26:    CONSTRAINT generated_app_bindings_refs_object CHECK (jsonb_typeof(secret_references) = 'object'),
./infra/postgres/021_generated_app_bindings.sql:28:    CONSTRAINT generated_app_bindings_refs_only CHECK (
./infra/postgres/021_generated_app_bindings.sql:31:    CONSTRAINT generated_app_bindings_revoked_at CHECK ((status = 'REVOKED') = (revoked_at IS NOT NULL))
./infra/postgres/026_media_provider_submissions.sql:10:    state TEXT NOT NULL CHECK (state IN ('INTENT','SUBMITTED')),
./infra/postgres/026_media_provider_submissions.sql:14:    CONSTRAINT media_provider_submissions_task CHECK ((state = 'SUBMITTED') = (provider_task_id IS NOT NULL))
./infra/postgres/027_task_attempts.sql:21:    attempt_seq                 INTEGER NOT NULL CHECK (attempt_seq >= 0),
```


## Docker — פלייק בהרצת drain/recovery (2026-10-27)

- **סיווג האירוע:** פלייק; לפי תדריך הבעלים מ־2026-10-27, הרצה חוזרת עברה בלי שינוי קוד.
- **חתימת הכשל המתועדת:** workflow `intake-budget-pg`, בדיקה `tests/test_real_docker_drain_recovery.py:318`: הציפייה `was OOM-killed` מול `preview-worker exit 137 (a job was killed at the 60s deadline)`; תוצאה: 1 failed, 190 passed.
- **מקור חתימת הכשל:** [Issue #150](https://github.com/Shayfly/desktop-tutorial/issues/150). ההנחיה שם: להריץ שוב תחילה; אם ירוק, לתעד פלייק ולעצור.
- **ראיית ההרצה החוזרת:** ״הרצה חוזרת עברה בלי שינוי קוד״ — דיווח הבעלים בתדריך. קישור לריצה, מספר attempt ו־SHA לא נמסרו ולא נמצאו בדיון #150 בעת התיעוד; לא מוצג כאן אימות עצמאי של לוג הריצה.
- **היקף המסקנה:** סיווג האירוע המסוים, לא קביעה שכל כשל Docker או OOM הוא פלייק, ולא ביטול ממצאי OOM היסטוריים ב־CONTROLS.json.
- **טיפול עתידי:** לקרוא רשומה זו לפני חקירה חוזרת של אותה חתימה. אין לחקור שוב את האירוע הסגור ללא ראיה חדשה; כשל שחוזר בריצה חוזרת, חתימה שונה או שינוי קוד מחייבים בדיקה מחדש. אין לשנות assertions או להחליש בדיקות על סמך הסיווג.

### הופעות חוזרות של אותה חתימה (`:318`, `was OOM-killed` not found), 2026-10-27 עד 2026-10-28

| # | ריצה | SHA | ניסיון | תוצאה | מקור הקריאה |
|---|---|---|---|---|---|
| 1 | [40599636376](https://github.com/Shayfly/desktop-tutorial/actions/runs/40599636376) (main #1113) | `0d40f69` | 1, 2 FAIL; 3 PASS | `:318` | הבעלים קרא את הלוג |
| 2 | [40662751345](https://github.com/Shayfly/desktop-tutorial/actions/runs/40662751345) (#170) | `8cac521` | 1, 2 FAIL | `:318`, 1 failed / 223 passed | הבעלים קרא את הלוג |
| 3 | [40688485494](https://github.com/Shayfly/desktop-tutorial/actions/runs/40688485494) (#176) | `4526204` | 1 FAIL | `:318`, 1 failed / 245 passed | הבעלים קרא את הלוג |

- **מספר הטסטים ברשימת pg גדל** מ-190 ל-223 ול-245, כי נוספו קבצים לרשימה (#169, ‏#176). הקשר לתדירות הפלייק הוא **השערה**. הוא לא נמדד.
- **מה הענף הזה מוסיף, מדידה בלבד:** ‏`_OomProbe` ב-test_5. הוא לא משנה ולא מחליש אף assertion, כולל זה של `OOMKilled`.
  - **שיא הזיכרון של ה-cgroup** (‏`memory.peak` ו-`memory.current`) מול המגבלה.
  - **מונה `oom_kill`** מתוך `memory.events`.
  - **זמני האירועים** `oom`, ‏`die`, ‏`kill` ו-`stop` של המנוע, מתחילת ה-drain, מול ה-deadline של 60 שניות.
  - **הדגלים `OOMKilled` ו-`ExitCode`** של `docker inspect`.
  - **הפלט:** שורת `::notice title=oom-measure test_5` בצעד ה-Evidence של pg.
- **ההשערה שהמדידה בודקת:** יש מרוץ בין שני טיימרים. ה-kernel הורג את התהליך על OOM, ובמקביל ה-deadline של 60 שניות שולח SIGKILL. אם ה-deadline מגיע ראשון, התוצאה היא exit 137 בלי `OOMKilled=true`.
  - **מצב ההשערה:** לא הוכחה. המדידה תגיד, ורק אחריה יבוא תיקון.

#### מדידות `oom-measure test_5`, כל מדידה כפי שנרשמה (נרשמות לפני כל החלטה)

| # | ריצה | SHA | test_5 | kill (s) | oom (s) | die (s) | OOMKilled / Exit | peak / limit | oom_kill counter |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [40690977510](https://github.com/Shayfly/desktop-tutorial/actions/runs/40690977510) | `7ec8dc2` | PASS | 2.0 | 2.9 | 2.9 | true / 137 | 4.4 MiB / 48 MiB | 0 |

**קריאה ראשונה, השערה בלבד:**
- **סדר האירועים:** ב-PASS, אירוע `kill` של המנוע מגיע **לפני** `oom` (2.0 שניות מול 2.9). זה מוקדם בהרבה מה-deadline של 60 שניות. המשמעות: המנוע עצמו שולח kill לפני שה-kernel מסמן OOM. כשהסדר יוצא אחרת, ייתכן ש-`OOMKilled` לא מסומן.
- **ה-cgroup:** ‏`peak=4.4MiB` ו-`oom_kill=0`, מול `OOMKilled=true`. סביר שה-probe קורא cgroup שאינו של הקונטיינר, או של הורה שלו. **ערכי הזיכרון והמונה במדידה הזו לא אמינים**, ושורת המדידה צריכה לציין איזה נתיב cgroup נקרא.
- **החלטה:** לא לפני שתירשם לפחות מדידה אחת של FAIL.
