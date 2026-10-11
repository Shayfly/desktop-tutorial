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
   await page.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(u.pathname==='/api/v28/me')return route.fulfill({status:401,contentType:'application/json',body:'{}'});
    if(u.pathname.includes('/conversation')) {
     calls.push(route.request().postDataJSON());
     if(failSend){failSend=false;return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:{error:'attachments_not_ready'}})});}
     return route.fulfill({contentType:'application/json',body:JSON.stringify({messages:[],discovery:fixture,turn:{actions:[]}})});
    }
    if(u.pathname.includes('/build-contracts'))return route.fulfill({contentType:'application/json',body:JSON.stringify({can_build:true,brief_revision:1,capabilities:[],infrastructure:[],product:{},blockers:[],clarification_questions:[]})});
    if(u.pathname==='/fixture')return route.fulfill({contentType:'text/html',body:fs.readFileSync(process.env.BASELINE_HTML||path.join(__dirname,'../omni_prod/assets/index.html'),'utf8')});
    if(u.pathname==='/assets/app.js' && process.env.BASELINE_APP)return route.fulfill({path:process.env.BASELINE_APP});
    if(u.pathname.startsWith('/assets/'))return route.fulfill({path:path.join(__dirname,'../omni_prod',u.pathname)});
    return route.fulfill({status:404,body:''});
   });
   await page.goto('http://fixture.test/fixture');
   await page.evaluate(d=>{S.projectId='p';S.lang='he';S.disc=d;S.chat={messages:[]};S.tab='req';
     S.signedIn=true;S.me={email:'fixture@example.test'};showView();renderDiscovery();renderTabs();},fixture);
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
