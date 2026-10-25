import assert from "node:assert/strict";
import {readFile,writeFile,access,readdir} from "node:fs/promises";
import {join} from "node:path";
import {run,commands,project,output} from "./toy-helper.mjs";
const checks=[];
const exists=async path=>{try{await access(path);return true;}catch(error){if(error.code==="ENOENT")return false;throw error;}};
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let failed=false;
try{await run("nonzero",["-e",'console.log("expected failure output"); process.exit(7);']);}catch(error){failed=true;}
assert.equal(failed,true);assert.equal(commands.at(-1).exitCode,7);assert.equal(commands.at(-1).scratchRemoved,true);
checks.push({name:"nonzero-exit",expectedFailure:true,recordedExit:commands.at(-1).exitCode,stdoutRetained:await exists(join(output,"nonzero/stdout")),scratchRemoved:true});
const descendantCode='console.log("descendant-ready");setTimeout(()=>{},60000);';
const pidPath=join(project,"escaped.pid");
const escapeParent=`const {spawn}=require("node:child_process");const fs=require("node:fs");const child=spawn(process.execPath,["-e",${JSON.stringify(descendantCode)}],{detached:true,stdio:["ignore","inherit","inherit"]});fs.writeFileSync(${JSON.stringify(pidPath)},String(child.pid));setTimeout(()=>process.exit(0),200);`;
const before=commands.length;let eofError=null,escapedPID=null;
try{await run("escaped-pipe",["-e",escapeParent]);}catch(error){eofError=error.message;}
finally{escapedPID=Number(await readFile(pidPath,"utf8"));try{process.kill(-escapedPID,"SIGTERM");}catch(error){if(error.code!=="ESRCH")throw error;}}
for(let i=0;i<80;i++){try{process.kill(-escapedPID,0);await wait(25);}catch(error){if(error.code==="ESRCH")break;throw error;}}
let escapedGroupEmpty=false;try{process.kill(-escapedPID,0);}catch(error){if(error.code==="ESRCH")escapedGroupEmpty=true;else throw error;}
assert.equal(escapedGroupEmpty,true);assert.equal(eofError,"controller_check_failed: escaped-pipe");assert.equal(commands.length,before+1);assert.equal(commands.at(-1).eofObserved,false);assert.equal(commands.at(-1).scratchRemoved,false);assert.equal(commands.at(-1).eofError,"owned_output_eof_timeout: escaped-pipe");
checks.push({name:"escaped-pipe-EOF-timeout",error:eofError,eofObserved:commands.at(-1).eofObserved,eofError:commands.at(-1).eofError,commandRecordAppended:commands.length!==before,stdoutRetained:await exists(join(output,"escaped-pipe/stdout")),stderrRetained:await exists(join(output,"escaped-pipe/stderr")),commandJSONRetained:await exists(join(output,"escaped-pipe/command.json")),scratchPresent:await exists(join(output,"escaped-pipe/scratch")),escapedPID,escapedGroupRetiredByToySupervisor:escapedGroupEmpty});

const nativeSetTimeout=globalThis.setTimeout;
globalThis.setTimeout=(callback,ms,...args)=>nativeSetTimeout(callback,ms===300000?100:ms===305000?250:ms,...args);
let timedFailure=null;
try{await run("scaled-command-timeout",["-e",'process.on("SIGTERM",()=>{});console.log("term-ignored");setInterval(()=>{},1000);']);}catch(error){timedFailure=error.message;}finally{globalThis.setTimeout=nativeSetTimeout;}
const timed=commands.at(-1);assert.equal(timedFailure,"controller_check_failed: scaled-command-timeout");assert.equal(timed.timedOut,true);assert.equal(timed.exitSignal,"SIGKILL");assert.equal(timed.eofObserved,true);assert.equal(timed.scratchRemoved,true);assert.equal(timed.processGroupEmpty,true);
checks.push({name:"scaled-command-timeout",schedulingOverride:{commandTimeoutMS:100,forceKillMS:250},helperTimerConstantsUnchanged:true,error:timedFailure,timedOut:timed.timedOut,exitSignal:timed.exitSignal,eofObserved:timed.eofObserved,processGroupEmpty:timed.processGroupEmpty,scratchRemoved:timed.scratchRemoved});


const originalKill=process.kill.bind(process);
process.kill=(target,signal)=>{if(target<0 && signal===0){const error=new Error("injected EPERM probe");error.code="EPERM";throw error;}return originalKill(target,signal);};
let probeFailure=null;
try{await run("injected-EPERM-probe",["-e",'console.log("probe-error-output");']);}catch(error){probeFailure=error.message;}finally{process.kill=originalKill;}
const deniedProbe=commands.at(-1);assert.equal(probeFailure,"controller_check_failed: injected-EPERM-probe");assert.equal(deniedProbe.terminalGroupState,null);assert.equal(deniedProbe.processGroupEmpty,false);assert.equal(deniedProbe.directChildTerminal,true);assert.equal(deniedProbe.eofObserved,true);assert.equal(deniedProbe.scratchRemoved,false);assert(deniedProbe.processManagementErrors.every(e=>e.operation==="probe" && e.code==="EPERM"));
checks.push({name:"injected-EPERM-probe",error:probeFailure,terminalGroupState:deniedProbe.terminalGroupState,directChildTerminal:deniedProbe.directChildTerminal,eofObserved:deniedProbe.eofObserved,processGroupEmpty:deniedProbe.processGroupEmpty,scratchRemoved:deniedProbe.scratchRemoved,processManagementErrors:deniedProbe.processManagementErrors,stdoutRetained:await exists(join(output,"injected-EPERM-probe/stdout")),commandJSONRetained:await exists(join(output,"injected-EPERM-probe/command.json"))});
const naturalPidPath=join(project,"same-group-pids.json");
const naturalParent=`const {spawn}=require("node:child_process");const fs=require("node:fs");const child=spawn(process.execPath,["-e",${JSON.stringify(descendantCode)}],{stdio:["ignore","inherit","inherit"]});fs.writeFileSync(${JSON.stringify(naturalPidPath)},JSON.stringify({parentPID:process.pid,descendantPID:child.pid}));setTimeout(()=>process.exit(0),200);`;
let naturalFailure=null;
try{await run("same-group-pipe",["-e",naturalParent]);}catch(error){naturalFailure=error.message;}
const natural=commands.at(-1),naturalPids=JSON.parse(await readFile(naturalPidPath,"utf8"));
assert.equal(natural.name,"same-group-pipe");assert.equal(await exists(join(output,"same-group-pipe/command.json")),true);assert.equal(natural.directChildTerminal,true);assert.equal(natural.eofObserved,true);
if(natural.processManagementErrors.length){assert.equal(naturalFailure,"controller_check_failed: same-group-pipe");assert.equal(natural.scratchRemoved,false);}else{assert.equal(naturalFailure,null);assert.equal(natural.processGroupEmpty,true);assert.equal(natural.scratchRemoved,true);}
checks.push({name:"same-group-pipe-natural-probe",error:naturalFailure,pids:naturalPids,processManagementErrors:natural.processManagementErrors,terminalGroupState:natural.terminalGroupState,processGroupEmpty:natural.processGroupEmpty,scratchRemoved:natural.scratchRemoved,commandJSONRetained:true});

await writeFile(join(import.meta.dirname,"toy-results.json"),JSON.stringify({status:"passed-expected-negative-path-reproduced",helperSHA256:"bb331e5b4b477c6f5a625dca41f4e3525346c5d77982631bc7731aaa75f42d58",checks,commands},null,2)+"\n");
console.log(JSON.stringify({checks}));
