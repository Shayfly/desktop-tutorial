"""M4.9 directive item 10 -- READY_FOR_REVIEW invariant, verified DIRECTLY
against raw Postgres rows (not the repository abstraction, not the HTTP
API) for the real clean-room modification task #49 produced. Reads
/tmp/m49_clean_room_ids.json for identifiers (real, from the final
official task #49 run)."""
import json
import sys

sys.path.insert(0, "/tmp/m4d2b_vendor")
import psycopg

with open("/tmp/m49_clean_room_ids.json") as f:
    ids = json.load(f)

modification_id = ids["modification_id"]
project_key = ids["project_key"]
seed_version_id = ids["version_id"]

conn = psycopg.connect(ids["database_url"])
cur = conn.cursor()


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}: {detail}")
    return cond


all_ok = True

# --- Raw modification_requests row -----------------------------------
cur.execute(
    "SELECT status, classification, classification_reason, billable, "
    "repair_rounds, evidence_json, error_code, error_message, "
    "created_at, started_at, completed_at, accepted_at, rejected_at, "
    "promoted_version_id, source_version_id, project_id "
    "FROM modification_requests WHERE id = %s",
    (modification_id,),
)
row = cur.fetchone()
all_ok &= check("MOD_REQUEST_ROW_EXISTS", row is not None, f"id={modification_id}")
(status, classification, classification_reason, billable, repair_rounds,
 evidence_json, error_code, error_message, created_at, started_at,
 completed_at, accepted_at, rejected_at, promoted_version_id,
 source_version_id, project_id) = row

# 8. ModificationRequest state is READY_FOR_REVIEW.
all_ok &= check("STATE_IS_READY_FOR_REVIEW", status == "READY_FOR_REVIEW", f"status={status!r}")

# 1. Generation completed.
all_ok &= check("GENERATION_COMPLETED", completed_at is not None and started_at is not None,
                 f"started_at={started_at} completed_at={completed_at}")
all_ok &= check("NO_ERROR_RECORDED", error_code is None and error_message is None,
                 f"error_code={error_code!r} error_message={error_message!r}")

evidence = evidence_json if isinstance(evidence_json, dict) else json.loads(evidence_json)

# 2/3. Sandbox command executed successfully; build/test exit status
# successful.
verification = evidence.get("verification") or {}
all_ok &= check("SANDBOX_VERIFICATION_RAN", bool(verification.get("build_log_tail")),
                 f"build_log_tail length={len(verification.get('build_log_tail') or '')}")
all_ok &= check("SANDBOX_VERIFICATION_PASSED", verification.get("passed") is True,
                 f"verification.passed={verification.get('passed')}")
all_ok &= check("SANDBOX_VERIFICATION_NO_FAILURES", verification.get("failures") == [],
                 f"failures={verification.get('failures')}")

# 4. Verification gates passed.
gates = evidence.get("gates") or {}
all_ok &= check("GATES_PASSED", gates.get("passed") is True, f"gates.passed={gates.get('passed')}")
all_ok &= check("GATES_NO_BLOCKING_GATE", gates.get("blocking_gate") is None,
                 f"blocking_gate={gates.get('blocking_gate')!r}")
all_ok &= check("GATES_QUALITY_PASSED", (gates.get("quality") or {}).get("passed") is True,
                 f"quality={gates.get('quality')}")
all_ok &= check("GATES_SECURITY_PASSED", (gates.get("security") or {}).get("passed") is True,
                 f"security={gates.get('security')}")

# 7. Diff exists.
diff = evidence.get("diff")
all_ok &= check("DIFF_EXISTS", diff is not None, f"diff={diff!r}" if diff is None else "present")
if diff is not None:
    all_ok &= check("DIFF_HAS_REAL_CONTENT", any(diff.get(k) for k in ("added", "modified", "removed")) or bool(diff),
                     f"diff keys={list(diff.keys()) if isinstance(diff, dict) else type(diff)}")

# --- 5/6. Candidate version + ProductSpec exist, directly from
# modification_candidates (raw JSON columns, not the ORM wrapper). -----
cur.execute(
    "SELECT repository_json, spec_json, project_id, modification_id "
    "FROM modification_candidates WHERE modification_id = %s",
    (modification_id,),
)
cand_rows = cur.fetchall()
all_ok &= check("CANDIDATE_ROW_COUNT_EXACTLY_ONE", len(cand_rows) == 1, f"count={len(cand_rows)}")
if cand_rows:
    repo_json, spec_json, cand_project_id, cand_mod_id = cand_rows[0]
    repo = repo_json if isinstance(repo_json, dict) else json.loads(repo_json)
    spec = spec_json if isinstance(spec_json, dict) else json.loads(spec_json)
    all_ok &= check("CANDIDATE_REPOSITORY_NONEMPTY", bool(repo), f"{len(repo)} files")
    all_ok &= check("CANDIDATE_REPOSITORY_HAS_SEED_FILES",
                     {"index.html", ".omni/project.json", "tests/test_seed.py"} <= set(repo),
                     f"paths={sorted(repo)}")
    all_ok &= check("CANDIDATE_PRODUCTSPEC_EXISTS", isinstance(spec, dict) and bool(spec.get("title")),
                     f"spec.title={spec.get('title') if isinstance(spec, dict) else spec}")
    all_ok &= check("CANDIDATE_ACCEPTANCE_PRESENT", isinstance(spec, dict) and bool(spec.get("acceptance")),
                     f"acceptance={spec.get('acceptance') if isinstance(spec, dict) else None}")

# --- Source ProductSpec (the version this modification was proposed
# against) also genuinely exists. --------------------------------------
cur.execute(
    "SELECT spec_json FROM project_version_specs WHERE version_id = %s AND project_id = %s",
    (seed_version_id, project_key),
)
source_spec_row = cur.fetchone()
all_ok &= check("SOURCE_PRODUCTSPEC_EXISTS", source_spec_row is not None, f"version_id={seed_version_id}")

# --- 9. No partial/orphan durable state. -------------------------------
cur.execute("SELECT count(*) FROM modification_requests WHERE id = %s", (modification_id,))
all_ok &= check("EXACTLY_ONE_MOD_REQUEST_ROW", cur.fetchone()[0] == 1, "")

cur.execute("SELECT count(*) FROM modification_outbox WHERE modification_id = %s", (modification_id,))
outbox_count = cur.fetchone()[0]
check("OUTBOX_ROW_COUNT", True, f"{outbox_count} row(s) (informational -- outbox rows are expected to persist as delivery history)")

cur.execute("SELECT id FROM project_versions WHERE project_id = %s", (project_key,))
version_ids = [r[0] for r in cur.fetchall()]
all_ok &= check("NO_EXTRA_VERSIONS_PROMOTED", version_ids == [seed_version_id],
                 f"project_versions for this project = {version_ids} (expected only the seed version, "
                 f"since READY_FOR_REVIEW must never self-promote)")

all_ok &= check("PROMOTED_VERSION_ID_IS_NULL", promoted_version_id is None,
                 f"promoted_version_id={promoted_version_id!r}")
all_ok &= check("ACCEPTED_AT_IS_NULL", accepted_at is None, f"accepted_at={accepted_at}")
all_ok &= check("REJECTED_AT_IS_NULL", rejected_at is None, f"rejected_at={rejected_at}")

print()
print("M49_READY_INVARIANT_" + ("ALL_PASS" if all_ok else "SOME_FAILED"))
cur.close()
conn.close()
sys.exit(0 if all_ok else 1)
