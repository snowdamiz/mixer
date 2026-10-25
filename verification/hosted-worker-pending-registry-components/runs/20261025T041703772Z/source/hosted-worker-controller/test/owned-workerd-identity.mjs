// Test-only process ownership checks. Never select a kill target by basename.
import {spawnSync} from "node:child_process";
import {realpathSync,statSync} from "node:fs";

const fail=reason=>{throw new Error("owned_workerd_identity_"+reason);};
const fileStat=path=>statSync(path,{bigint:true});

function processTable(){
  const result=spawnSync("/bin/ps",["-axo","pid=,ppid=,comm="],{encoding:"utf8",timeout:5_000,maxBuffer:8*1024*1024});
  if(result.error||result.status!==0||!Number.isSafeInteger(result.pid)||typeof result.stdout!=="string")fail("unreadable");
  const rows=[];
  for(const line of result.stdout.split("\n")){
    if(!line.trim())continue;
    const match=line.trim().match(/^(\d+)\s+(\d+)\s+(.+)$/);
    if(!match)fail("unreadable");
    const pid=Number(match[1]),parentPid=Number(match[2]);
    if(!Number.isSafeInteger(pid)||pid<=0||!Number.isSafeInteger(parentPid)||parentPid<0)fail("unreadable");
    // ps is this synchronous observation's own short-lived direct child.
    // Exclude only its exact spawn PID, never a process name.
    if(pid!==result.pid)rows.push({pid,parentPid,command:match[3]});
  }
  return rows;
}

export function selectOwnedWorkerd({ownerPid,executable,platform,processes,canonicalPath=realpathSync,stat=fileStat}){
  if(!Number.isSafeInteger(ownerPid)||ownerPid<=0||typeof executable!=="string"||!executable.startsWith("/"))fail("unreadable");
  if(platform!=="linux"&&platform!=="darwin")fail("unsupported_platform");
  if(!Array.isArray(processes)||processes.some(row=>!row||!Number.isSafeInteger(row.parentPid)))fail("unreadable");
  const children=processes.filter(row=>row.parentPid===ownerPid);
  if(children.some(row=>!Number.isSafeInteger(row.pid)||row.pid<=0)||new Set(children.map(row=>row.pid)).size!==children.length)fail("ambiguous");
  let installed=executable,expectedStat;
  if(platform==="linux"){
    try{installed=canonicalPath(executable);expectedStat=stat(installed);if(!expectedStat.isFile())fail("unreadable");}
    catch{fail("unreadable");}
  }
  const matches=[];
  for(const row of children){
    if(platform==="darwin"){
      // Preserve the existing macOS full-path comm check. Darwin ps comm is
      // argv[0], so this remains a trusted local test-harness identity check.
      if(row.command===executable)matches.push({pid:row.pid,parentPid:ownerPid,executable});
      continue;
    }
    try{
      const procExe="/proc/"+row.pid+"/exe",actual=canonicalPath(procExe),actualStat=stat(procExe);
      if(!actualStat.isFile())fail("unreadable");
      if(actual===installed&&actualStat.dev===expectedStat.dev&&actualStat.ino===expectedStat.ino)
        matches.push({pid:row.pid,parentPid:ownerPid,executable:installed,device:String(actualStat.dev),inode:String(actualStat.ino)});
    }catch{fail("unreadable");}
  }
  if(matches.length!==1)fail("ambiguous");
  return matches[0];
}

export function killOwnedWorkerd(executable,{platform=process.platform,ownerPid=process.pid,readProcesses=processTable,canonicalPath=realpathSync,stat=fileStat,signal=(pid,value)=>process.kill(pid,value)}={}){
  const inspect=()=>{
    let processes;try{processes=readProcesses();}catch{fail("unreadable");}
    return selectOwnedWorkerd({ownerPid,executable,platform,processes,canonicalPath,stat});
  };
  const selected=inspect(),rechecked=inspect();
  // Two complete observations must agree, including the direct owner and
  // Linux executable vnode. No await or other user work precedes the signal.
  if(JSON.stringify(selected)!==JSON.stringify(rechecked))fail("changed");
  signal(rechecked.pid,"SIGKILL");
  return {...rechecked,signal:"SIGKILL",identitySource:platform==="linux"?"proc-exe-realpath-and-inode":"darwin-ps-full-path-comm",parentRechecked:true};
}
