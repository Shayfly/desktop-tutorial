# tests/fixtures/repair_repro is a GENERATED-APP fixture with an intentional bug: its own tests fail on purpose and
# run only inside the executor under test (tests/test_repair_fingerprint.py), never in this repository's suite.
collect_ignore_glob = ['repair_repro/*']
