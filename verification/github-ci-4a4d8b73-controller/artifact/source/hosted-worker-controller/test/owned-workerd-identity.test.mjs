import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {once} from "node:events";
import {realpathSync} from "node:fs";
import test from "node:test";
import {killOwnedWorkerd,selectOwnedWorkerd} from "./owned-workerd-identity.mjs";

const ownerPid=400,executable="/installed/workerd",installed="/canonical/workerd";
const file=(dev=1n,ino=2n)=>({dev,ino,isFile:()=>true});
const row=(pid=401,parentPid=ownerPid,command="workerd")=>({pid,parentPid,command});
function linux(overrides={}){
  return {ownerPid,executable,platform:"linux",processes:[row()],
    canonicalPath:path=>path===executable?installed:path==="/proc/401/exe"?installed:"/other/workerd",
    stat:()=>file(),...overrides};
}
const rejects=(fn,reason)=>assert.throws(fn,{message:"owned_workerd_identity_"+reason});

test("Linux basename comm accepts only canonical installed executable and vnode",()=>{
  assert.deepEqual(selectOwnedWorkerd(linux()),{pid:401,parentPid:ownerPid,executable:installed,device:"1",inode:"2"});
});
test("wrong owner is never an executable candidate",()=>{
  const calls=[];
  rejects(()=>selectOwnedWorkerd(linux({processes:[row(401,999)],canonicalPath:path=>{calls.push(path);return installed;}})),"ambiguous");
  assert.deepEqual(calls,[executable]);
});
test("same basename at a different executable path cannot authorize a kill",()=>{
  rejects(()=>selectOwnedWorkerd(linux({canonicalPath:path=>path===executable?installed:"/other/workerd"})),"ambiguous");
});
test("same path with a different executable vnode cannot authorize a kill",()=>{
  rejects(()=>selectOwnedWorkerd(linux({stat:path=>file(1n,path===installed?2n:3n)})),"ambiguous");
});
test("one exact candidate may coexist with a readable different direct child",()=>{
  const selected=selectOwnedWorkerd(linux({processes:[row(),row(402)],stat:path=>file(1n,path==="/proc/402/exe"?3n:2n)}));
  assert.equal(selected.pid,401);
});
test("missing candidate fails closed",()=>rejects(()=>selectOwnedWorkerd(linux({processes:[]})),"ambiguous"));
test("multiple exact candidates fail closed",()=>{
  rejects(()=>selectOwnedWorkerd(linux({processes:[row(),row(402)],canonicalPath:()=>installed})),"ambiguous");
});
test("duplicate candidate PID fails closed",()=>{
  rejects(()=>selectOwnedWorkerd(linux({processes:[row(),row()]})),"ambiguous");
});
test("unreadable or vanished candidate exe fails closed even with another exact match",()=>{
  for(const code of ["EACCES","ENOENT"]){
    rejects(()=>selectOwnedWorkerd(linux({processes:[row(),row(402)],canonicalPath:path=>{
      if(path==="/proc/402/exe")throw Object.assign(new Error(code),{code});return installed;
    }})),"unreadable");
  }
});
test("missing or unreadable installed executable fails closed",()=>{
  rejects(()=>selectOwnedWorkerd(linux({canonicalPath:()=>{throw new Error("ENOENT");}})),"unreadable");
});
test("deleted proc executable target fails closed",()=>{
  rejects(()=>selectOwnedWorkerd(linux({canonicalPath:path=>path===executable?installed:installed+" (deleted)"})),"ambiguous");
});
test("unreadable executable vnode fails closed",()=>{
  rejects(()=>selectOwnedWorkerd(linux({stat:path=>{if(path.startsWith("/proc/"))throw new Error("EACCES");return file();}})),"unreadable");
});
test("Darwin retains direct-parent exact full-path comm selection",()=>{
  const select=processes=>selectOwnedWorkerd({ownerPid,executable,platform:"darwin",processes,canonicalPath:()=>assert.fail("Darwin must preserve current path selection")});
  assert.equal(select([row(401,ownerPid,executable),row(402,999,executable),row(403,ownerPid,"workerd")]).pid,401);
  rejects(()=>select([row(401,999,executable)]),"ambiguous");
  rejects(()=>select([row(401,ownerPid,executable),row(402,ownerPid,executable)]),"ambiguous");
});
test("unsupported platform fails closed",()=>rejects(()=>selectOwnedWorkerd(linux({platform:"win32"})),"unsupported_platform"));
test("recheck losing the direct parent sends no signal",()=>{
  let calls=0;const signals=[];
  rejects(()=>killOwnedWorkerd(executable,{...linux(),readProcesses:()=>[row(401,++calls===1?ownerPid:999)],signal:(...args)=>signals.push(args)}),"ambiguous");
  assert.deepEqual(signals,[]);
});
test("recheck with a different exact PID sends no signal",()=>{
  let calls=0;const signals=[];
  rejects(()=>killOwnedWorkerd(executable,{...linux({canonicalPath:()=>installed}),readProcesses:()=>[row(++calls===1?401:402)],signal:(...args)=>signals.push(args)}),"changed");
  assert.deepEqual(signals,[]);
});
test("recheck becoming unreadable sends no signal",()=>{
  let calls=0;const signals=[];
  rejects(()=>killOwnedWorkerd(executable,{...linux(),readProcesses:()=>{if(++calls===2)throw new Error("observation_failed");return [row()];},signal:(...args)=>signals.push(args)}),"unreadable");
  assert.deepEqual(signals,[]);
});
test("recheck changing installed and running vnode sends no signal",()=>{
  let calls=0;const signals=[];
  rejects(()=>killOwnedWorkerd(executable,{...linux(),readProcesses:()=>{calls++;return [row()];},stat:()=>file(1n,BigInt(calls)),signal:(...args)=>signals.push(args)}),"changed");
  assert.deepEqual(signals,[]);
});
test("two matching observations send exactly SIGKILL to the exact owned PID",()=>{
  let observations=0;const signals=[];
  const receipt=killOwnedWorkerd(executable,{...linux(),readProcesses:()=>{observations++;return [row()];},signal:(...args)=>signals.push(args)});
  assert.equal(observations,2);assert.deepEqual(signals,[[401,"SIGKILL"]]);assert.equal(receipt.parentRechecked,true);
});
test("live host identity kills and reaps only this test's exact direct child",async()=>{
  const child=spawn(process.execPath,["-e","setInterval(()=>{},1000)"],{stdio:"ignore"});
  const terminal=once(child,"exit");
  try{
    await once(child,"spawn");
    const receipt=killOwnedWorkerd(process.execPath);
    assert.equal(receipt.pid,child.pid);assert.equal(receipt.parentPid,process.pid);
    assert.equal(receipt.executable,process.platform==="linux"?realpathSync(process.execPath):process.execPath);
    assert.deepEqual(await terminal,[null,"SIGKILL"]);
  }finally{
    if(child.exitCode===null&&child.signalCode===null){child.kill("SIGKILL");await terminal;}
  }
});
