/* UI-only fixture tests in real Chromium; no live-provider/build claims. */
const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('node:assert/strict');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox','--disable-gpu']}:{} )});
 try {
  for(const width of [390,1440]) {
   const page=await browser.newPage({viewport:{width,height:844}});
   const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'customer_flow_fixture.json'),'utf8'));
   const calls=[];
   let failSend=false;
   let blockedBuild=false,buildCalls=0;
   await page.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(u.pathname==='/api/v28/me')return route.fulfill({status:401,contentType:'application/json',body:'{}'});
    if(u.pathname.includes('/conversation')) {
     calls.push(route.request().postDataJSON());
     if(failSend){failSend=false;return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:{error:'attachments_not_ready'}})});}
     return route.fulfill({contentType:'application/json',body:JSON.stringify({messages:[],discovery:fixture,turn:{actions:[]}})});
    }
    if(u.pathname.includes('/approvals')){blockedBuild=true;await new Promise(r=>setTimeout(r,150));return route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:{error:'capability_not_feasible',findings:[{item:'sign-in (roles)',outcome:'BLOCKED'}]}})});}
    if(u.pathname.endsWith('/builds')){buildCalls++;return route.fulfill({status:500,body:'{}'});}
    if(u.pathname.includes('/build-contracts'))return route.fulfill({contentType:'application/json',body:JSON.stringify({can_build:!blockedBuild,brief_revision:1,capabilities:[],infrastructure:[],product:{},blockers:blockedBuild?[{code:'capability_not_feasible',message:'unsupported',findings:[{item:'sign-in (roles)',outcome:'BLOCKED'}]}]:[],clarification_questions:[]})});
    if(u.pathname==='/fixture')return route.fulfill({contentType:'text/html',body:fs.readFileSync(process.env.BASELINE_HTML||path.join(__dirname,'../omni_prod/assets/index.html'),'utf8')});
    if(u.pathname==='/assets/app.js' && process.env.BASELINE_APP)return route.fulfill({path:process.env.BASELINE_APP});
    if(u.pathname.startsWith('/assets/'))return route.fulfill({path:path.join(__dirname,'../omni_prod',u.pathname)});
    return route.fulfill({status:404,body:''});
   });
   // boot() asks /api/v28/me, which this fixture answers 401. If that 401 is handled AFTER the signed-in state
   // below is injected, app.js signs the "user" out and the edit button disappears (CI flake on 0ee20fe).
   // Wait until the app has finished handling it: the body promise resolves, the app's 401 handling runs as
   // microtasks, and this marker resolves one macrotask later -- after all of them.
   await page.addInitScript(()=>{
     const f=window.fetch.bind(window);
     window.fetch=(input,init)=>{
       const p=f(input,init);
       if(String(input).endsWith('/api/v28/me'))window.__meHandled=p.then(r=>{const t=r.text.bind(r);
         r.text=()=>{const body=t();window.__meHandled=body.then(()=>new Promise(res=>setTimeout(res,0)),()=>{});return body;};
         return r;},()=>{});
       return p;};
   });
   await page.goto('http://fixture.test/fixture');
   await page.waitForFunction(()=>window.__meHandled!==undefined);
   await page.evaluate(async()=>{let m;do{m=window.__meHandled;await m;}while(m!==window.__meHandled);});
   await page.evaluate(d=>{S.projectId='p';S.lang='he';S.disc=d;S.chat={messages:[]};S.tab='req';
     S.signedIn=true;S.me={email:'fixture@example.test'};showView();renderDiscovery();renderTabs();openTab('req');},fixture);
   await page.locator('#discoveryPanel button').filter({hasText:'שינוי'}).first().click();
   // Editing one answer must expose the rest without any request to the server.
   assert.equal(await page.locator('#discoveryPanel fieldset[data-q=font]').count(),1,'all decisions stay editable');
   await page.locator('#discoveryPanel textarea[name=q_color]').fill('ורוד עדין ושמנת');
   await page.locator('#discoveryPanel details.fontPicker summary').click();
   await page.locator('#discoveryPanel input[name=q_font][value=rubik]').check();
   assert.equal(calls.length,0,'draft edits must not update the server');
   await page.locator('#ctxMinimize').click();
   assert.equal(await page.locator('#ctx').evaluate(el=>el.classList.contains('open')),false);
   await page.locator('#ctxTabs button').filter({hasText:'דרישות'}).click();
   assert.equal(await page.locator('textarea[name=q_color]').inputValue(),'ורוד עדין ושמנת','minimize preserves draft');
   await page.locator('#updateBriefBtn').click();
   await page.waitForFunction(()=>S.tab==='plan');
   assert.equal(calls.length,1,'one explicit update applies the batch');
   assert.equal(calls[0].answers.color,'ורוד עדין ושמנת');
   assert.equal(calls[0].answers.font,'rubik');
   assert.equal(await page.locator('#confirmBtn').count(),1,'build approval stays available');
   failSend=true;
   await page.evaluate(async()=>{$('chatInput').value='תשתמש בזה כלוגו';await sendChat({message:'תשתמש בזה כלוגו',attachment_ids:['att_fixture']},'תשתמש בזה כלוגו');});
   assert.equal(await page.locator('#chatInput').inputValue(),'תשתמש בזה כלוגו','failed send retains customer text');
   await page.evaluate(async()=>{await sendChat({message:'תשתמש בזה כלוגו',attachment_ids:['att_fixture']},'תשתמש בזה כלוגו');});
   assert.equal(calls[1].request_key,calls[2].request_key,'retry cannot create a second paid turn');
   await page.locator('#confirmBtn').click();
   // Authorization is asynchronous; jump immediately to a truthful pending
   // screen without showing an imaginary started build.
   await page.waitForFunction(()=>buildStarting);
   assert.equal(await page.locator('#ctxTitle').textContent(),'בנייה');
   assert.match(await page.locator('#buildMsg').textContent(),/מאמתים אישור/);
   await page.waitForFunction(()=>!buildStarting&&S.plan&&!S.plan.can_build);
   assert.equal(buildCalls,0,'blocked approval starts no build');
   assert.equal(await page.locator('#progressPanel').evaluate(el=>el.hidden),true,'no fake build progress');
   assert.equal(await page.locator('#confirmBtn').isDisabled(),true,'fresh quote blocks approval');
   assert.match(await page.locator('#planMsg').textContent(),/הבנייה לא התחילה/);
   assert.match(await page.locator('#planMsg').textContent(),/התחברות והרשאות/,'409 names the missing capability');
   assert.match(await page.locator('#planMsg').textContent(),/ערכו|לערוך/,'409 tells the customer what to do');
   assert.match(await page.locator('#planPanel').textContent(),/התחברות והרשאות/);
   const namedError=await page.evaluate(()=>{
    const detail={error:'capability_not_feasible',findings:[{item:'calendar integration',reason:'not connected',alternative:'Connect the calendar or remove this requirement.'}]};
    const he=explain(new ApiError(409,detail));S.lang='en';
    const en=explain(new ApiError(409,detail));S.lang='he';return {he,en};
   });
   for(const text of [namedError.he,namedError.en]){
    assert.match(text,/calendar integration/,'other item names are preserved');
    assert.match(text,/Connect the calendar/,'specific remedy is preserved');
    assert.doesNotMatch(text,/undefined/);
   }
   if(width===390){
    await page.evaluate(()=>{S.projects=[{id:'p',title:'פרויקט בדיקה'},{id:'other',title:'פרויקט נוסף'}];renderProjects();});
    for(const pane of ['chat','preview','edit']){
     await page.locator(`#mobileTabs button[data-pane="${pane}"]`).click();
     await page.locator('#mobileMenuBtn').click();
     assert.equal(await page.locator('#workspaceView').getAttribute('data-pane'),pane,'menu preserves active pane');
     assert.equal(await page.locator('#sidebar').getAttribute('aria-modal'),'true');
     assert.equal(await page.locator('#mobileMenuBtn').getAttribute('aria-expanded'),'true');
     await page.locator('#sbSearch').fill('נוסף');
     assert.equal(await page.locator('#sbProjects button').count(),1,'project search works in drawer');
     await page.keyboard.press('Escape');
     assert.equal(await page.locator('#sidebar').evaluate(el=>el.inert),true);
     assert.equal(await page.locator('#mobileMenuBtn').evaluate(el=>document.activeElement===el),true,'focus returns to menu');
     await page.locator('#mobileMenuBtn').click();
     await page.locator('#sbCollapse').click();
     assert.equal(await page.locator('#mobileMenuBtn').getAttribute('aria-expanded'),'false');
    }
    await page.locator('#mobileMenuBtn').click();
    await page.locator('#newProjectTopBtn').click();
    assert.equal(await page.locator('#newProjectDialog').evaluate(el=>el.open),true,'new project accessible from drawer');
    await page.locator('#newProjectCancel').click();
   }else{
    await page.locator('#sbOpen').click();await page.locator('#sbCollapse').click();await page.locator('#sbOpen').click();
    assert.equal(await page.locator('#sidebar').evaluate(el=>el.inert),false);
   }
   await page.close();console.log(`PASS customer edit flow ${width}px`);
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
