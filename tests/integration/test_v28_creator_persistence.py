import os, unittest, uuid
from omni_prod.db import DatabasePool
from omni_prod.creator_accounts import PostgresAccountService
from omni_prod.subscription_store import PostgresSubscriptionService

RUN=os.getenv('OMNI_RUN_V28_CREATOR_POSTGRES')=='1'

@unittest.skipUnless(RUN,'requires migrated live Postgres and OMNI_RUN_V28_CREATOR_POSTGRES=1')
class V28CreatorPersistenceLiveTests(unittest.TestCase):
    def setUp(self):
        url=os.environ['OMNI_DATABASE_URL']; self.pool=DatabasePool(url).open(); self.secret='live-persist-'+'p'*48
    def tearDown(self): self.pool.close()
    def test_account_and_project_survive_service_instance_change(self):
        email=f'persist-{uuid.uuid4().hex}@example.com'; a=PostgresAccountService(token_secret=self.secret,pool=self.pool)
        acct,token=a.register(email=email,password='StrongPass123!'); p=a.create_project(owner_id=acct.id,title='Persistent')
        b=PostgresAccountService(token_secret=self.secret,pool=self.pool); logged,_=b.login(email=email,password='StrongPass123!')
        self.assertEqual(logged.id,acct.id); self.assertEqual(b.require_project(owner_id=acct.id,project_id=p.id).title,'Persistent')
    def test_subscription_usage_survives_service_instance_change(self):
        email=f'sub-{uuid.uuid4().hex}@example.com'; a=PostgresAccountService(token_secret=self.secret,pool=self.pool); acct,_=a.register(email=email,password='StrongPass123!')
        s1=PostgresSubscriptionService(pool=self.pool); s1.assign_plan(acct.id,'basic'); d=s1.authorize(user_id=acct.id,cost_class='standard',credits=10); s1.consume(user_id=acct.id,decision=d)
        s2=PostgresSubscriptionService(pool=self.pool); snap=s2.snapshot(acct.id); self.assertEqual(snap['plan']['code'],'basic'); self.assertEqual(snap['credits_used'],10)
