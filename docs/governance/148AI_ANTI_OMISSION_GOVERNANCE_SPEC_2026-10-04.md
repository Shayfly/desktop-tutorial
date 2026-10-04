# 148AI Anti-Omission Governance Gate — Specification

Date: 2026-10-04

## Purpose
Prevent a task, capability, skill, agent, external proof, or product requirement from being marked complete merely because related code exists or an implementer remembers it as complete.

## Required ledger record
Every canonical requirement must have: `requirement_id`, `source_spec`, `description`, `milestone`, `dependencies`, `implementation_paths`, `test_ids`, `evidence_refs`, `external_gates`, `commit_sha`, `status`, `last_verified_at`, `superseded_by`.

## Allowed statuses
`NOT_IMPLEMENTED`, `PARTIAL`, `IMPLEMENTED_NOT_VERIFIED`, `VERIFIED_LOCAL`, `GATED_EXTERNAL`, `VERIFIED_EXTERNAL`, `BLOCKED`, `SUPERSEDED`.

## CI failures
CI must fail if a requirement claimed VERIFIED has no named test/evidence, if required files/tests are absent, if a registry item lacks mandatory metadata, if a spec requirement has no ledger entry, if a dependency is missing, or if generated truth docs drift from the ledger/code.

## Completion rule
A milestone can be accepted only when every non-superseded required record is either VERIFIED at the required proof level or explicitly BLOCKED/GATED with the milestone policy allowing that gate.
