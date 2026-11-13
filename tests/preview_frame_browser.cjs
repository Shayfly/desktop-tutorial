/* Michael 2026-11-13: the preview toolbar (refresh / open in a new tab / who can open / the data note) sits OUTSIDE
   the page's frame, never over it. On a phone it covered the hero: it was inside the same bordered box as the page.
   Real Chromium at 390 and 1440 px, fixture page only. */
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');const assert=require('node:assert/strict');
const PAGE='<!doctype html><html dir="rtl"><body style="margin:0"><header style="height:120px;background:#6b4226">HERO</header><p>x</p></body></html>';
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox','--disable-gpu']}:{} )});
 try{
  for(const width of [390,1440]){
   const p=await browser.newPage({viewport:{width,height:800}});
   await p.route('**/*',r=>{const u=new URL(r.request().url());
    if(u.pathname==='/api/v28/me')return r.fulfill({status:401,body:'{}',contentType:'application/json'});
    if(u.pathname==='/fixture')return r.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(__dirname,'../omni_prod/assets/index.html'),'utf8')});
    if(u.pathname.startsWith('/assets/'))return r.fulfill({path:path.join(__dirname,'../omni_prod',u.pathname)});
    return r.fulfill({status:404,body:''});});
   await p.goto('http://fixture.test/fixture');await p.waitForTimeout(600);
   await p.evaluate(html=>{S.lang='he';S.signedIn=true;S.me={email:'x@example.test'};S.projectId='p';showView();
    document.querySelector('.workspace').dataset.pane='preview';
    $('previewEmpty').hidden=true;const f=$('previewFrame');f.hidden=false;f.srcdoc=html;
    const n=$('previewDataNote');n.hidden=false;n.textContent='הנתונים נשמרים';
    const s=$('previewSharing');s.hidden=false;s.innerHTML='<span>מי יכול לפתוח: </span><select><option>רק אני</option></select>';},PAGE);
   await p.waitForTimeout(300);
   const r=await p.evaluate(()=>{const box=id=>$(id).getBoundingClientRect();const vp=$('viewport');
     const frame=getComputedStyle(vp);
     return {vpTop:box('viewport').top,frameTop:box('previewFrame').top,
       bars:['previewDataNote','previewSharing'].map(id=>({id,inside:vp.contains($(id)),bottom:box(id).bottom})),
       chromeInside:vp.contains(document.querySelector('.chrome')),chromeBottom:document.querySelector('.chrome').getBoundingClientRect().bottom,
       vpBorder:frame.borderTopWidth,browserBorder:getComputedStyle(document.querySelector('.browser')).borderTopWidth};});
   assert.equal(r.chromeInside,false,`${width}: the toolbar is inside the page frame`);
   assert.ok(r.chromeBottom<=r.vpTop,`${width}: the toolbar overlaps the page frame`);
   for(const b of r.bars){assert.equal(b.inside,false,`${width}: ${b.id} is inside the page frame`);
     assert.ok(b.bottom<=r.vpTop,`${width}: ${b.id} overlaps the page frame`);}
   assert.equal(r.vpBorder,'1px',`${width}: the frame is the page's own border`);
   assert.equal(r.browserBorder,'0px',`${width}: the toolbar and the page are no longer one bordered box`);
   assert.ok(r.frameTop>=r.vpTop,`${width}: the page starts inside its frame`);
   console.log(`PASS preview toolbar outside the page frame ${width}px`);
   await p.close();
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
