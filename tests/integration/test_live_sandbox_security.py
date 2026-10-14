import os, shutil, tempfile, unittest
from pathlib import Path
from omni_prod.sandbox import SandboxLimits, run_sandbox

@unittest.skipUnless(os.getenv('OMNI_RUN_LIVE_SANDBOX')=='1' and shutil.which('docker'),'requires isolated Docker host and OMNI_RUN_LIVE_SANDBOX=1')
class LiveSandboxSecurityTests(unittest.TestCase):
    def run_cmd(self, code):
        with tempfile.TemporaryDirectory() as td:
            Path(td,'x.txt').write_text('safe')
            return run_sandbox(source_dir=td,build_id='live-hostile',limits=SandboxLimits(timeout_seconds=10),command=['python','-c',code])
    def test_network_is_disabled(self): self.assertNotEqual(self.run_cmd("import socket; socket.create_connection(('1.1.1.1',53),2)").returncode,0)
    def test_root_filesystem_is_readonly(self): self.assertNotEqual(self.run_cmd("open('/etc/omni-pwn','w').write('x')").returncode,0)
    def test_source_mount_is_readonly(self): self.assertNotEqual(self.run_cmd("open('/workspace/x.txt','w').write('x')").returncode,0)
