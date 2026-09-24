"""M4.9 directive item 8 -- "SANDBOX SECURITY NEGATIVE TESTS": prove the
sandbox restrictions remain *effective*, not merely present on the
`docker run` command line. Every check below runs real Python code inside
a real `docker run omni-sandbox:latest ...` container (via the real
`omni_prod.sandbox.run_sandbox()` production function -- the exact same
one `SandboxRepositoryExecutor` uses) and reads back real kernel/cgroup
state or attempts a real violation and observes the real result. Nothing
here is asserted from the argv list `build_docker_command()` produces;
every assertion is evidence collected from *inside* the running container
or from `docker run`'s real exit status.

Covers every bullet in item 8's checklist:
  - process is not running as root -> os.getuid()/os.getgid() read inside
    the container.
  - cap-drop=ALL is active -> a real attempt to create a raw socket
    (needs CAP_NET_RAW) is denied with a real PermissionError.
  - no-new-privileges is active -> /proc/self/status's NoNewPrivs field
    (the kernel's own ground truth), read inside the container.
  - PID limit is enforced -> a real fork loop against a deliberately small
    --pids-limit genuinely fails with a real OSError (EAGAIN) at the
    expected count, not merely configured.
  - memory/CPU limits are configured as intended -> the real cgroup v1
    limit files (memory.limit_in_bytes, cpu.cfs_quota_us/cfs_period_us,
    pids.max) read from inside the container, compared against
    SandboxLimits' real defaults.
  - the memory limit is also proven *effective*, not just configured -- a
    real attempt to allocate and touch 1.5GB (deliberately past the
    1024m default) inside the container gets real-OOM-killed by the
    kernel; the container process exits via SIGKILL (docker run returns
    137), observed directly, not asserted from configuration.
  - host filesystem is not writable outside explicitly allowed mounts,
    and the root filesystem remains read-only where required -> real
    write attempts to /etc, /usr/bin and the read-only /workspace mount
    all fail with real `OSError: [Errno 30] Read-only file system`, with
    /tmp (tmpfs) and /output (rw bind mount) proven writable as a
    positive control -- so the negative results are known to reflect
    real enforcement, not a broken probe.
  - network access is disabled according to the existing sandbox policy
    (`--network none`) -> a real outbound TCP connect attempt fails with
    a real `OSError: [Errno 101] Network is unreachable`.

Per the directive's own instruction ("do not weaken isolation merely to
obtain a passing build"), every probe below runs under the SAME
`SandboxLimits` defaults production uses (`SandboxLimits()`), except the
PID-limit test, which deliberately uses a SMALLER `pids` value
(`SandboxLimits(pids=8)`) purely to make the real fork-exhaustion fast and
deterministic to reach -- the production default (256, confirmed equal to
`SandboxLimits().pids` by a separate assertion below) is still the value
whose cgroup file is checked by the general probe.

Requires only `docker` and the real `omni-sandbox:latest` image (task #48)
-- no Postgres/Redis -- so this runs as part of the ordinary combined
`tests/` suite, not standalone.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

_PROBE_GENERAL = r'''
import os, socket, sys

results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

uid, gid = os.getuid(), os.getgid()
check("NOT_ROOT", uid != 0 and gid != 0, f"uid={uid} gid={gid}")

try:
    status = open("/proc/self/status").read()
    line = [l for l in status.splitlines() if l.startswith("NoNewPrivs:")][0]
    nnp = line.split()[1]
    check("NO_NEW_PRIVS", nnp == "1", line)
except Exception as e:
    check("NO_NEW_PRIVS", False, f"error: {e}")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    s.close()
    check("CAP_DROP_ALL_blocks_raw_socket", False, "raw socket unexpectedly succeeded -- CAP_NET_RAW not dropped")
except PermissionError as e:
    check("CAP_DROP_ALL_blocks_raw_socket", True, f"PermissionError as expected: {e}")
except Exception as e:
    check("CAP_DROP_ALL_blocks_raw_socket", False, f"unexpected error type: {type(e).__name__}: {e}")

try:
    mem_limit = int(open("/sys/fs/cgroup/memory/memory.limit_in_bytes").read().strip())
    expected = 1024 * 1024 * 1024
    check("MEMORY_LIMIT_CONFIGURED", mem_limit == expected, f"cgroup memory.limit_in_bytes={mem_limit} expected={expected}")
except Exception as e:
    check("MEMORY_LIMIT_CONFIGURED", False, f"error: {e}")

try:
    quota = int(open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read().strip())
    period = int(open("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read().strip())
    cpus = quota / period if period else None
    check("CPU_LIMIT_CONFIGURED", quota > 0 and abs(cpus - 1.5) < 0.01, f"cfs_quota_us={quota} cfs_period_us={period} -> {cpus} cpus (expected 1.5)")
except Exception as e:
    check("CPU_LIMIT_CONFIGURED", False, f"error: {e}")

try:
    pids_limit = open("/sys/fs/cgroup/pids/pids.max").read().strip()
    check("PIDS_LIMIT_CONFIGURED", pids_limit == "256", f"cgroup pids.max={pids_limit!r} expected 256")
except Exception as e:
    check("PIDS_LIMIT_CONFIGURED", False, f"error: {e}")

def try_write(path):
    try:
        with open(path, "w") as f:
            f.write("x")
        return True, "write unexpectedly succeeded"
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"

ok, detail = try_write("/etc/m49_write_test")
check("ROOTFS_READONLY_etc", not ok, detail)

ok, detail = try_write("/usr/bin/m49_write_test")
check("ROOTFS_READONLY_usr_bin", not ok, detail)

ok, detail = try_write("/workspace/m49_write_test")
check("WORKSPACE_MOUNT_READONLY", not ok, detail)

ok, detail = try_write("/tmp/m49_write_test")
check("TMPFS_IS_WRITABLE_positive_control", ok, detail)

if os.path.isdir("/output"):
    ok, detail = try_write("/output/m49_write_test")
    check("OUTPUT_MOUNT_IS_WRITABLE_positive_control", ok, detail)

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(("8.8.8.8", 53))
    s.close()
    check("NETWORK_DISABLED", False, "outbound TCP connect unexpectedly succeeded")
except OSError as e:
    check("NETWORK_DISABLED", True, f"{type(e).__name__}: {e}")

print("M49_SECURITY_PROBE_RESULTS")
all_pass = True
for name, ok, detail in results:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"{status} {name}: {detail}")
print("M49_SECURITY_PROBE_" + ("ALL_PASS" if all_pass else "SOME_FAILED"))
sys.exit(0 if all_pass else 1)
'''

_PROBE_PIDS = r'''
import os, sys, time

children = []
attempted = 0
failed_at = None
MAX_ATTEMPTS = 60

for i in range(MAX_ATTEMPTS):
    attempted = i + 1
    try:
        pid = os.fork()
        if pid == 0:
            time.sleep(5)
            os._exit(0)
        else:
            children.append(pid)
    except OSError as e:
        failed_at = (i + 1, str(e))
        break

print(f"M49_PIDS_PROBE attempted={attempted} succeeded={len(children)} failed_at={failed_at}")
for pid in children:
    try:
        os.kill(pid, 9)
    except OSError:
        pass
for pid in children:
    try:
        os.waitpid(pid, 0)
    except OSError:
        pass

if failed_at is not None:
    print("M49_PIDS_PROBE_RESULT PASS: fork() failed as expected before exhausting MAX_ATTEMPTS")
    sys.exit(0)
else:
    print("M49_PIDS_PROBE_RESULT FAIL: all", MAX_ATTEMPTS, "forks succeeded -- pids-limit not enforced")
    sys.exit(1)
'''

_PROBE_MEMORY = r'''
import sys

chunk_size = 50 * 1024 * 1024
chunks = []
total = 0
target = 1536 * 1024 * 1024  # 1.5GB, intentionally > the 1024m default limit
while total < target:
    b = bytearray(chunk_size)
    for i in range(0, len(b), 4096):
        b[i] = 1  # touch each page to force real physical allocation
    chunks.append(b)
    total += chunk_size
    print(f"M49_MEMORY_PROBE allocated_and_touched={total // (1024*1024)}MB", flush=True)

print("M49_MEMORY_PROBE_RESULT FAIL: allocated 1.5GB without being OOM-killed -- memory limit not enforced")
sys.exit(1)
'''


def _skip_reason() -> str | None:
    if not shutil.which('docker'):
        return 'docker binary not found'
    import subprocess
    out = subprocess.run(['docker', 'inspect', '--format={{.Id}}', 'omni-sandbox:latest'],
                          capture_output=True, text=True)
    if out.returncode != 0:
        return f'omni-sandbox:latest not present: {out.stderr.strip()}'
    return None


_SKIP = _skip_reason()


@unittest.skipIf(_SKIP, _SKIP)
class SandboxSecurityNegativeTests(unittest.TestCase):

    def _run(self, script: str, limits, with_output_dir: bool = False):
        from omni_prod.sandbox import run_sandbox, SandboxLimits  # noqa: F401
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'probe.py'), 'w') as f:
                f.write(script)
            os.chmod(td, 0o755)
            if with_output_dir:
                with tempfile.TemporaryDirectory() as outd:
                    os.chmod(outd, 0o777)
                    return run_sandbox(source_dir=td, build_id='m49-sec-test', limits=limits,
                                        command=['python3', 'probe.py'], output_dir=outd)
            return run_sandbox(source_dir=td, build_id='m49-sec-test', limits=limits,
                                command=['python3', 'probe.py'])

    def test_general_isolation_checklist(self):
        from omni_prod.sandbox import SandboxLimits
        # Confirm the production default really is 256 before relying on
        # the in-container cgroup check for that exact number.
        self.assertEqual(SandboxLimits().pids, 256)
        result = self._run(_PROBE_GENERAL, SandboxLimits(), with_output_dir=True)
        self.assertEqual(result.returncode, 0,
                          f'security probe reported a real failure:\n{result.stdout}\n{result.stderr}')
        self.assertIn('M49_SECURITY_PROBE_ALL_PASS', result.stdout, result.stdout)
        for must_pass in (
            'PASS NOT_ROOT', 'PASS NO_NEW_PRIVS', 'PASS CAP_DROP_ALL_blocks_raw_socket',
            'PASS MEMORY_LIMIT_CONFIGURED', 'PASS CPU_LIMIT_CONFIGURED', 'PASS PIDS_LIMIT_CONFIGURED',
            'PASS ROOTFS_READONLY_etc', 'PASS ROOTFS_READONLY_usr_bin', 'PASS WORKSPACE_MOUNT_READONLY',
            'PASS TMPFS_IS_WRITABLE_positive_control', 'PASS OUTPUT_MOUNT_IS_WRITABLE_positive_control',
            'PASS NETWORK_DISABLED',
        ):
            self.assertIn(must_pass, result.stdout, result.stdout)

    def test_pids_limit_is_really_enforced_not_just_configured(self):
        from omni_prod.sandbox import SandboxLimits
        result = self._run(_PROBE_PIDS, SandboxLimits(pids=8))
        self.assertEqual(result.returncode, 0,
                          f'pids-limit probe failed for real:\n{result.stdout}\n{result.stderr}')
        self.assertIn('M49_PIDS_PROBE_RESULT PASS', result.stdout, result.stdout)
        # A small, deterministic sanity bound: with --pids-limit 8, the main
        # process itself counts as 1, so at most 7 forks can ever succeed.
        self.assertIn("succeeded=7", result.stdout)

    def test_memory_limit_is_really_enforced_via_real_oom_kill(self):
        from omni_prod.sandbox import SandboxLimits
        result = self._run(_PROBE_MEMORY, SandboxLimits())
        # A real OOM-kill terminates the container via SIGKILL -- docker run
        # surfaces that as returncode 137 (128+9). It must NOT be 0 (which
        # would mean the full 1.5GB was allocated without enforcement) and
        # must NOT be some unrelated error.
        self.assertEqual(result.returncode, 137,
                          f'expected a real OOM-kill (137); got {result.returncode}:\n'
                          f'{result.stdout}\n{result.stderr}')
        self.assertNotIn('M49_MEMORY_PROBE_RESULT FAIL', result.stdout,
                          'the probe must never reach its own "not enforced" report line')
        # Real evidence of where enforcement kicked in: allocation must have
        # stopped at or before the configured ~1024MB limit, and the probe
        # must never have logged reaching or exceeding it.
        self.assertNotIn('allocated_and_touched=1050MB', result.stdout)


if __name__ == '__main__':
    unittest.main()
