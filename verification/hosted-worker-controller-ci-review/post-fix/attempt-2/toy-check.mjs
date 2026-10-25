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
const parentCode=`const {spawn}=require("node:child_process"); const child=spawn(process.execPath,["-e",${JSON.stringify(descendantCode)}],{stdio:["ignore","inherit","inherit"]});require("node:fs").writeFileSync(${JSON.stringify(join(project,"same-group-pids.json"))},JSON.stringify({parentPID:process.pid,descendantPID:child.pid}));console.log("descendant-pid:"+child.pid);setTimeout(()=>process.exit(0),200);`;
await run("same-group-pipe",["-e",parentCode]);
const same=commands.at(-1);assert.equal(same.processGroupEmpty,true);assert(same.signals.includes("SIGTERM"));assert.equal(same.scratchRemoved,true);
checks.push({name:"same-group-descendant-pipe",signals:same.signals,processGroupEmpty:same.processGroupEmpty,scratchRemoved:same.scratchRemoved});
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

await writeFile(join(import.meta.dirname,"toy-results.json"),JSON.stringify({status:"passed-expected-negative-path-reproduced",helperSHA256:"8e7202ed9fd316ca8e42bfef532cb2678795ef5305071741dceec99ca4d62068",checks,commands},null,2)+"\n");
console.log(JSON.stringify({checks}));
