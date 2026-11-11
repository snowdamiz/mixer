import {readFileSync} from 'node:fs';
import {createBrowserSessionClient} from './api/browser-session-client.js';
import {createBrowserSessionController} from './state/browser-session-controller.js';
const fixture=JSON.parse(readFileSync(process.argv[2],'utf8'));
const traffic=[];
const check=(ok,label)=>{if(!ok)throw Error(label);};
let cookie=fixture.firstCookie;
const transport=async(path,init)=>{
 check(init.credentials==='same-origin','actual client same-origin');
 const headers=new Headers(init.headers);headers.set('cookie','__Host-mixer-session='+cookie);
 const r=await fetch(new URL(path,fixture.origin),{...init,headers});
 traffic.push({path:new URL(path,fixture.origin).pathname,status:r.status});return r;
};
const wait=async(f)=>{const end=performance.now()+6000;while(!f()){if(performance.now()>end)throw Error('client deadline');await new Promise(r=>setTimeout(r,10));}};
const c=createBrowserSessionController({fetch:transport});
try{
 c.revalidate();await wait(()=>traffic.length>0);await new Promise(r=>setTimeout(r,50));
 check(c.getSession().kind==='unavailable','unknown cookie actual503 unavailable');
 cookie=fixture.activeCookie;c.revalidate();await wait(()=>c.getSession().kind==='ready');
 const m=await createBrowserSessionClient({fetch:transport}).read();
 check(m.state==='authenticated'&&m.expires_at===fixture.expires,'actual client admitted expiry');
 const s=c.getSession();check(s.kind==='ready','retry ready');
 const a=await s.client.organizations();check(a.organizations.length===50&&a.next_cursor!==null,'org page50');
 const b=await s.client.organizations({cursor:a.next_cursor});check(b.organizations.length===3&&b.next_cursor===null,'org continuation3');
 check(![...a.organizations,...b.organizations].some(x=>x.id==='org-b'),'foreign tenant hidden');
 const p=await s.client.projects('org-a');check(p.projects.length===50&&p.next_cursor!==null,'project page50');
 const q=await s.client.projects('org-a',{cursor:p.next_cursor});check(q.projects.length===3&&q.next_cursor===null,'project continuation3');
 console.log(JSON.stringify({synthetic_fixture:true,httpOnly_fixture_cookie_attached_outside_product:true,client_unchanged:true,session_retry:true,pagination:true,traffic}));
}catch(e){console.error('CLIENT_FAILURE '+(e?.code??e?.message??'closed'));process.exitCode=1;}finally{c.dispose();}
