# Omni Creator V18 — Supply Chain + Web Security

- Dependency inventory + lock status.
- CycloneDX 1.5 SBOM.
- CORS strict policy: no wildcard; HTTPS-only in production.
- HTTP security headers including CSP/HSTS/nosniff/frame deny/referrer/permissions/COOP/CORP.
- Local release attestation explicitly marked UNSIGNED.
- Live HTTP verification is required on the exact final ZIP.

`requirements-production.txt` still contains ranges, so dependency lock remains BLOCKED until a real CI resolver produces a hashed lockfile.
