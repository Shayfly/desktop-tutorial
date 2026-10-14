"""Verify the empty Neon bootstrap against the repository's exact migrations."""
import hashlib
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[2]
sources = sorted((root / "infra/postgres").glob("*.sql"))
bootstrap = (root / "infra/staging/bootstrap_neon_empty.sql").read_bytes().decode("utf-8")
expected = {}
for path in sources:
    version, name = path.stem.split("_", 1)
    raw = path.read_bytes()
    section = "-- BEGIN SOURCE " + path.name + "\n" + raw.decode() + "\n-- END SOURCE " + path.name
    assert section in bootstrap, "Bootstrap source drift: " + path.name
    expected[int(version)] = (name, hashlib.sha256(raw).hexdigest())

def query(sql):
    result = subprocess.run(
        ["psql", "-X", "-A", "-t", "-F", "|", "-v", "ON_ERROR_STOP=1", "-c", sql],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip().splitlines()

actual = {}
for row in query("SELECT version, name, sha256 FROM schema_migrations ORDER BY version"):
    version, name, checksum = row.split("|")
    actual[int(version)] = (name, checksum)
assert actual == expected, "Migration ledger does not match repository sources"
required = {
    "creator_accounts", "creator_sessions", "creator_projects",
    "creator_subscriptions", "build_requests", "project_versions", "generated_app_bindings",
}
tables = set(query("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"))
assert required <= tables, "Missing application tables: " + str(required - tables)
# A second application must refuse the non-empty schema and preserve its ledger.
retry = subprocess.run(
    ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-f", str(root / "infra/staging/bootstrap_neon_empty.sql")],
    capture_output=True, text=True,
)
assert retry.returncode != 0, "Bootstrap unexpectedly accepted an existing schema"
assert "Bootstrap requires an empty public schema" in retry.stderr, retry.stderr
assert len(query("SELECT version FROM schema_migrations")) == len(expected)
print("Verified", len(expected), "exact migrations, application tables, and safe rerun refusal.")
