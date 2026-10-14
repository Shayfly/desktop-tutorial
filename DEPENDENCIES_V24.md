# V24 dependency policy

Top-level production packages are pinned in `requirements-production.txt`.
The app/test stack available in the current validation environment was exercised by the V24 suite.
Production-only packages (psycopg/redis/rq at the V24 pins) could not be installed in this isolated validation environment because outbound package download was unavailable.
Therefore the release does **not** claim install-time verification of those three packages here.

For a networked CI/release environment:
1. create a clean Python 3.12 virtualenv;
2. install `requirements-production.txt` and `requirements-test.txt`;
3. run the full test suite and live integration suite;
4. generate a hash-locked transitive requirements file (pip-tools/uv/pip lock workflow) and archive it with the release.
