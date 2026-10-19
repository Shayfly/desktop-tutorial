# db-identity — staging worker database (2026-10-19T06:14:43Z)

- run_id: [39208780505](https://github.com/Shayfly/desktop-tutorial/actions/runs/39208780505)
- source: container omni-worker-worker-1 environment (.env not found at /home/omni/actions-runner/_work/desktop-tutorial/desktop-tutorial/infra/worker-host)
- host: `ep-floral-bread-b1weu1th-pooler.c-5.eu-central-1.aws.neon.tech`
- dbname: `neondb`
- sha256(OMNI_DATABASE_URL)[:8]: `4dbc8f3f`
- db_fingerprint sha256(host|dbname)[:12]: `d2eb0b8c775f`
- Neon endpoint (pooler suffix removed): `ep-floral-bread-b1weu1th`

Compare with Production: GET /api/v28/deployment -> schema.db_host / schema.db_fingerprint.
A '-pooler' host and the direct host of the same Neon endpoint are the same database
but produce different db_fingerprint values; compare the Neon endpoint.
