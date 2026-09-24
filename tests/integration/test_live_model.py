import os, unittest
from omni_prod.model_gateway import ModelEndpoint, OpenAICompatibleGateway

@unittest.skipUnless(os.getenv('OMNI_RUN_LIVE_MODEL')=='1','requires OMNI_RUN_LIVE_MODEL=1 and configured local endpoint')
class LiveModelTests(unittest.TestCase):
    def test_local_model_returns_json(self):
        ep=ModelEndpoint('live-local',os.getenv('OMNI_LOCAL_MODEL_URL','http://127.0.0.1:8001/v1'),os.getenv('OMNI_LOCAL_MODEL_ID','omni-local'),timeout_seconds=120)
        data=OpenAICompatibleGateway(ep).complete_json(system='Return only JSON.',user='Return {"ok":true}.',max_tokens=64)
        self.assertTrue(data.get('ok'))
