/* Michael 2026-11-13 (production, a new project "מאפייה"): the build tab showed the live log of ANOTHER project's run.
   Two projects, a build in A, open B: no line of A in B's build, versions or requirements -- and an explicit empty
   state. Also when A's answers arrive after the switch to B (a slow network). Real Chromium, fixture API only. */
const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('node:assert/strict');
const path=require('path');
const json=body=>({contentType:'application/json',body:JSON.stringify(body)});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox','--disable-gpu']}:{} )});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844}});
  let slowA=0;
  await page.route('**/*',async route=>{
   const u=new URL(route.request().url());const p=u.pathname;
   if(p==='/api/v28/me')return route.fulfill({status:401,contentType:'application/json',body:'{}'});
   if(p==='/fixture')return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(__dirname,'../omni_prod/assets/index.html'),'utf8')});
   if(p.startsWith('/assets/'))return route.fulfill({path:path.join(__dirname,'../omni_prod',p)});
   const m=p.match(/^\/api\/v28\/projects\/([AB])\/(.*)$/);
   if(!m)return route.fulfill({status:404,body:''});
   const [,project,rest]=m;
   if(project==='A'&&slowA)await new Promise(r=>setTimeout(r,slowA));
   if(project==='A'){
    if(rest==='builds/latest')return route.fulfill(json({build:{build_id:'bA',status:'ready'}}));
    if(rest==='builds/bA')return route.fulfill(json({build_id:'bA',status:'ready',phase:'READY',evidence:{}}));
    if(rest.startsWith('builds/bA/events'))return route.fulfill(json({build_id:'bA',events:[
      {seq:1,kind:'info',at:'2026-11-12T19:06:50Z',message:'A-LINE מתקן את מה שנכשל בבדיקות'},
      {seq:2,kind:'info',at:'2026-11-12T19:09:19Z',message:'A-LINE סבב בדיקות 5: כל הבדיקות עברו'}]}));
    if(rest==='builds/bA/plan')return route.fulfill(json({tasks:[]}));
    if(rest==='history')return route.fulfill(json({versions:[{id:'vA_from_project_A',message:'A-VERSION',created_at:'2026-11-12T19:10:00Z'}]}));
    if(rest.startsWith('conversation'))return route.fulfill(json({messages:[{role:'customer',content:'A-REQ בית קפה'}],turn:{actions:[]}}));
   } else {
    if(rest==='builds/latest')return route.fulfill(json({build:null}));
    if(rest==='history')return route.fulfill(json({versions:[]}));
    if(rest.startsWith('conversation'))return route.fulfill(json({messages:[{role:'customer',content:'B-REQ מאפייה'}],turn:{actions:[]}}));
   }
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
  await page.evaluate(()=>{S.lang='he';S.signedIn=true;S.me={email:'fixture@example.test'};showView();});

  const openBuildTabOfB=async()=>page.evaluate(()=>{   // what "approve and build" shows before a build exists
    $('progressPanel').hidden=false;resetBuildPanel();renderLog();openTab('build');});
  const text=id=>page.locator('#'+id).evaluate(el=>el.textContent);
  const assertNothingOfA=async label=>{
    for(const id of ['progressPanel','versionsPanel','discoveryPanel','thread'])
      if(await page.locator('#'+id).count()){
        const t=await text(id);
        assert.ok(!/A-LINE|A-VERSION|vA_from_project_A|A-REQ/.test(t),`${label}: #${id} shows project A: ${t.slice(0,200)}`);
      }
    assert.equal(await page.evaluate(()=>S.build),null,`${label}: S.build belongs to A`);
  };

  // 1. A has a build: its log is shown in A (the fixture works) ...
  await page.evaluate(()=>selectProject('A'));
  assert.match(await text('liveLogList'),/A-LINE/,'project A shows its own log');
  // ... 2. then B: nothing of A, and the empty state says so
  await page.evaluate(()=>selectProject('B'));
  await openBuildTabOfB();
  await assertNothingOfA('switch A -> B');
  assert.match(await text('liveLogList'),/אין בנייה עדיין בפרויקט הזה/,'explicit empty state in B');

  // 3. A's answers arrive AFTER the switch to B (slow network): they are dropped
  slowA=400;
  await page.evaluate(()=>{selectProject('A');});            // not awaited: A's requests are in flight
  await page.evaluate(()=>selectProject('B'));
  await page.waitForTimeout(1500);                           // every request of A has answered by now
  await openBuildTabOfB();
  await assertNothingOfA('late answers of A');
  assert.match(await text('liveLogList'),/אין בנייה עדיין בפרויקט הזה/,'explicit empty state after late answers');
  console.log('::notice title=project scope (browser)::two projects, a build in A: B shows no line of A (build, versions, requirements), also with late answers');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
