import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {readFile,writeFile,access} from "node:fs/promises";
import {join} from "node:path";
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const child=spawn(process.execPath,[join(import.meta.dirname,"child.mjs")],{detached:true,stdio:["ignore","pipe","pipe"]});
const stdout=[],stderr=[];child.stdout.on("data",b=>stdout.push(b));child.stderr.on("data",b=>stderr.push(b));let exitCode=null,exited=false;child.on("exit",code=>{exited=true;exitCode=code;});
let returned=null,innerGroupEmpty=false,wrapperExitedBeforeSupervisorCleanup=false,error=null;
try{
 for(let i=0;i<800;i++){try{returned=JSON.parse(await readFile(join(import.meta.dirname,"returned.json"),"utf8"));break;}catch(e){if(e.code!=="ENOENT")throw e;}await wait(25);}
 assert(returned,"helper did not write terminal receipt within20s");
 for(let i=0;i<40&&!exited;i++)await wait(25);
 wrapperExitedBeforeSupervisorCleanup=exited;assert.equal(wrapperExitedBeforeSupervisorCleanup,true);assert.equal(exitCode,0);
 const r=returned.record;assert.equal(r.directChildTerminal,false);assert.equal(r.directChildUnrefOnFailure,true);assert.equal(r.processGroupEmpty,false);assert.equal(r.terminalGroupState,true);assert.equal(r.eofObserved,false);assert.equal(r.scratchRemoved,false);assert.equal(r.timedOut,true);assert(r.processManagementErrors.length>=4);assert.equal(returned.failure,"controller_check_failed: denied-termination-ceiling");
}catch(e){error=e.stack;}
finally{
 if(returned?.record?.pid){try{process.kill(-returned.record.pid,"SIGKILL");}catch(e){if(e.code!=="ESRCH")throw e;}
 for(let i=0;i<80;i++){try{process.kill(-returned.record.pid,0);await wait(25);}catch(e){if(e.code==="ESRCH"){innerGroupEmpty=true;break;}throw e;}}}
 if(!exited){try{process.kill(-child.pid,"SIGKILL");}catch(e){if(e.code!=="ESRCH")throw e;}}
}
const result={status:error?"failed":"passed",error,schedulingOverride:{commandTimeoutMS:100,forceKillMS:150,directChildCeilingMS:200,EOFTimeoutMS:150},monotonicGroupGraceUnchanged:true,wrapperPID:child.pid,wrapperExitedBeforeSupervisorCleanup,wrapperExitCode:exitCode,ownedInnerGroupRetiredBySupervisor:innerGroupEmpty,returned,stdout:Buffer.concat(stdout).toString(),stderr:Buffer.concat(stderr).toString()};
await writeFile(join(import.meta.dirname,"supervisor-results.json"),JSON.stringify(result,null,2)+"\n");console.log(JSON.stringify({status:result.status,wrapperExitedBeforeSupervisorCleanup,ownedInnerGroupRetiredBySupervisor:innerGroupEmpty}));assert.equal(error,null);assert.equal(innerGroupEmpty,true);
