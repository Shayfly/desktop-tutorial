/* The owner, 2026-11-16. Real Chromium, fixture API only; no live build is claimed.
   1. One truth for the approval state (production 11:10-11:11): the panel's plan was fetched while the spec waited for
      approval and stayed on screen after the chat approved it -- the chat said "approve the budget", the panel still
      offered "approve the spec", and the customer approved twice. After the approval the panel must show the build
      approval, fetched again, and no spec button.
   2. The empty question: a message that asks the question in words gets buttons only; a message that does not, gets
      the question on the card. Either way the question is on the screen exactly once. */
const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('node:assert/strict');
const path=require('path');
const json=body=>({contentType:'application/json',body:JSON.stringify(body)});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox','--disable-gpu']}:{} )});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'customer_flow_fixture.json'),'utf8'));
  let approved=false,planCalls=0,approvals=0;
  const plan=()=>({can_build:approved,brief_revision:fixture.brief.revision,brief_fingerprint:'f'.repeat(64),capabilities:[],
    infrastructure:[],product:{},clarification_questions:[],credits_required:500,
    blockers:approved?[]:[{code:'spec_not_approved',message:'המפרט עוד לא אושר'}]});
  const gate1={messages:[{role:'assistant',content:'שלב 1 מתוך 2 — זה המפרט שהבנתי.'}],discovery:fixture,plan_id:null,
    turn:{actions:[{type:'approve_spec',brief_revision:fixture.brief.revision,brief_fingerprint:'f'.repeat(64),canon:{status:'OK',facts:[]}}]}};
  const gate2={messages:[...gate1.messages,{role:'customer',content:'כן, זה נכון'},
      {role:'assistant',content:'שלב 2 מתוך 2 — מעולה. הכנתי תוכנית. כדי להתחיל לבנות, לחצו על "לאשר ולהתחיל לבנות".'}],discovery:fixture,plan_id:'plan_1',
    turn:{actions:[{type:'show_plan',brief_revision:fixture.brief.revision},{type:'approve_build',brief_revision:fixture.brief.revision}]}};
  await page.route('**/*',async route=>{
   const u=new URL(route.request().url());const p=u.pathname;
   if(p==='/api/v28/me')return route.fulfill({status:401,contentType:'application/json',body:'{}'});
   if(p==='/fixture')return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(__dirname,'../omni_prod/assets/index.html'),'utf8')});
   if(p==='/assets/app.js' && process.env.BASELINE_APP)return route.fulfill({path:process.env.BASELINE_APP});
   if(p.startsWith('/assets/'))return route.fulfill({path:path.join(__dirname,'../omni_prod',p)});
   if(p.includes('/build-contracts')){planCalls++;return route.fulfill(json(plan()));}
   if(p.endsWith('/spec-approval')){approvals++;approved=true;return route.fulfill(json(gate2));}   // gate 1's own route
   if(p.includes('/conversation'))return route.fulfill(json(approved?gate2:gate1));
   return route.fulfill({status:404,contentType:'application/json',body:'{}'});
  });
  await page.addInitScript(()=>{
    const f=window.fetch.bind(window);
    window.fetch=(input,init)=>{const p=f(input,init);
      if(String(input).endsWith('/api/v28/me'))window.__meHandled=p.then(r=>{const t=r.text.bind(r);
        r.text=()=>{const body=t();window.__meHandled=body.then(()=>new Promise(res=>setTimeout(res,0)),()=>{});return body;};
        return r;},()=>{});
      return p;};
  });
  await page.goto('http://fixture.test/fixture');
  await page.waitForFunction(()=>window.__meHandled!==undefined);
  await page.evaluate(async()=>{let m;do{m=window.__meHandled;await m;}while(m!==window.__meHandled);});
  await page.evaluate(()=>{S.projectId='p';S.lang='he';S.signedIn=true;S.me={email:'fixture@example.test'};showView();});

  // --- 1. the approval state
  await page.evaluate(g=>applyConversation(g),gate1);           // gate 1 on screen: the panel's plan is fetched ...
  await page.waitForFunction(()=>S.plan&&S.plan.can_build===false);
  assert.equal(planCalls,1,'the plan is fetched once at gate 1');
  assert.equal(await page.evaluate(()=>S.plan.blockers[0].code),'spec_not_approved','... and it waits on the spec approval');
  await page.locator('#thread .acts button').filter({hasText:'כן, זה נכון'}).click();   // the customer approves in the chat
  await page.waitForFunction(()=>S.chat&&S.chat.plan_id==='plan_1');
  await page.waitForFunction(()=>S.plan&&S.plan.can_build===true,null,{timeout:5000}).catch(()=>{});
  assert.equal(approvals,1,'one approval was sent');
  assert.equal(planCalls,2,'the plan is fetched again after the approval (it was fetched before it)');
  await page.locator('#thread .acts button').filter({hasText:'לאשר ולהתחיל לבנות'}).click();   // what the chat now asks for
  await page.waitForFunction(()=>S.tab==='plan');
  assert.equal(await page.locator('#planPanel button').filter({hasText:'כן, זה נכון'}).count(),0,
    'the panel no longer offers to approve a spec the chat already approved');
  assert.equal(await page.locator('#confirmBtn').isDisabled(),false,'the panel offers the build approval the chat asks for');
  assert.doesNotMatch(await page.locator('#planPanel').textContent(),/המפרט עוד לא אושר/);
  assert.doesNotMatch(await page.locator('#planPanel').textContent(),/צריך לאשר שהבנתי נכון/);   // the panel's own words for the same blocker (plain words 2026-11-21)
  assert.equal(approvals,1,'the customer is not sent to approve the spec a second time');
  // a plan blocked by something that is NOT an approval is kept: no refetch on every turn
  await page.evaluate(()=>{S.plan={...S.plan,can_build:false,blockers:[{code:'capability_not_feasible',message:'x'}]};});
  const before=planCalls;
  await page.evaluate(g=>applyConversation(g),gate2);
  assert.equal(planCalls,before,'a plan that does not wait on an approval is not fetched again');
  console.log('PASS approval state: one truth for chat and panel');

  // --- 2. the question, once
  const q={id:'personal_data',field:'personal_data',text:'האם יישמרו פרטים אישיים של אנשים (שם, טלפון, מייל)?',kind:'choice',delegable:false,
    options:[{value:'yes',label:'כן'},{value:'no',label:'לא'}]};
  const count=async()=>page.locator('#thread').evaluate((el,text)=>el.textContent.split(text).length-1,q.text);
  await page.evaluate(([q])=>{S.plan={can_build:true,blockers:[],capabilities:[],infrastructure:[],product:{},clarification_questions:[]};
    applyConversation({messages:[{role:'assistant',content:'שאלה אחת לפני שממשיכים: '+q.text}],discovery:S.disc,turn:{questions:[q],actions:[]}});},[q]);
  assert.equal(await count(),1,'asked in words: the card adds buttons, not the question again');
  assert.equal(await page.locator('#thread .quick .qq').count(),0);
  assert.equal(await page.locator('#thread .quick .opts button').count(),2,'the buttons are there');
  await page.evaluate(([q])=>applyConversation({messages:[{role:'assistant',content:'הבנתי, אתר לחנות דלתות.'}],discovery:S.disc,
    turn:{questions:[q],actions:[]}}),[q]);
  assert.equal(await count(),1,'not asked in words: the card carries the question');
  assert.equal(await page.locator('#thread .quick .qq').count(),1);
  console.log('PASS the question is on screen exactly once');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
