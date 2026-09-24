import json
import unittest
from omni_prod.product_spec import ProductSpec
from omni_prod.sandbox import SandboxLimits, SandboxResult
from omni_prod.sandbox_executor import SandboxRepositoryExecutor

SPEC = ProductSpec.from_dict({
    'title':'X','summary':'X app','stack':['python'],
    'requirements':[{'id':'R1','text':'works','kind':'functional','mandatory':True}],
    'acceptance':[{'id':'A1','requirement_id':'R1','text':'tests pass'}],
})

class Runner:
    def __init__(self, codes):
        self.codes=list(codes); self.commands=[]
    def __call__(self, **kwargs):
        self.commands.append(kwargs['command'])
        code=self.codes.pop(0)
        return SandboxResult(code, 'ok' if code==0 else '', 'boom' if code else '')

def repo():
    return {
        'app.py':'print("ok")',
        '.omni/project.json':json.dumps({
            'build':[['python','-m','compileall','-q','.']],
            'verify':[{'name':'acceptance','argv':['python','app.py'],'acceptance_ids':['A1']}],
        })
    }

class SandboxExecutorTests(unittest.TestCase):
    def test_build_and_verify_pass(self):
        runner=Runner([0,0])
        result=SandboxRepositoryExecutor(limits=SandboxLimits(),runner=runner).execute(repository=repo(),spec=SPEC)
        self.assertTrue(result.passed)
        self.assertEqual(runner.commands[0][0],'python')
    def test_verify_failure_maps_to_acceptance_id(self):
        runner=Runner([0,1])
        result=SandboxRepositoryExecutor(limits=SandboxLimits(),runner=runner).execute(repository=repo(),spec=SPEC)
        self.assertFalse(result.passed)
        self.assertEqual(result.failures[0].acceptance_id,'A1')
    def test_unknown_acceptance_reference_rejected(self):
        r=repo()
        data=json.loads(r['.omni/project.json'])
        data['verify'][0]['acceptance_ids']=['NOPE']
        r['.omni/project.json']=json.dumps(data)
        with self.assertRaises(ValueError):
            SandboxRepositoryExecutor(limits=SandboxLimits(),runner=Runner([0])).execute(repository=r,spec=SPEC)
    def test_missing_manifest_rejected(self):
        with self.assertRaises(ValueError):
            SandboxRepositoryExecutor(limits=SandboxLimits(),runner=Runner([])).execute(repository={'app.py':'x'},spec=SPEC)

if __name__=='__main__':
    unittest.main()
