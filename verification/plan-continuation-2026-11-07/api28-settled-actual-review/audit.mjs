import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import path from 'node:path';
const root='/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4';
const base=root+'/verification/plan-continuation-2026-11-07';
const selected=base+'/api28-terminal-parser-review-r3';
const runtime=selected+'/runtime-attempt';
const own=base+'/api28-settled-actual-review';
const started=Date.now(), deadline=started+55000;
const read=async p=>fs.readFile(p,'utf8'), get=async p=>JSON.parse(await read(p));
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const normalize=v=>Array.isArray(v)?v.map(normalize):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,normalize(v[k])])):v;
const equal=(a,b)=>JSON.stringify(normalize(a))===JSON.stringify(normalize(b));
const checks=[], hashes={}, issues=[];
function check(name,ok,detail){checks.push({name,passed:!!ok,...(detail===undefined?{}:{detail})});if(!ok)issues.push(name);}
async function identity(p){
 if(Date.now()>deadline)throw Error('55-second direct-file audit bound');
 if(hashes[p])return hashes[p];
 if(!p.startsWith(root+'/')&&!p.startsWith('/opt/homebrew/'))throw Error('Unapproved read path');
 const real=await fs.realpath(p);
 if(!real.startsWith(root+'/')&&!real.startsWith('/opt/homebrew/'))throw Error('Unapproved resolved path');
 if(p.includes('cache-custody-actual-controls-fix-r4'))throw Error('Held path refused');
 const f=await fs.open(p,'r'), h=crypto.createHash('sha256');let bytes=0;
 try{const buffer=Buffer.alloc(1024*1024);for(;;){if(Date.now()>deadline)throw Error('55-second direct-file audit bound');const r=await f.read(buffer,0,buffer.length,null);if(!r.bytesRead)break;h.update(buffer.subarray(0,r.bytesRead));bytes+=r.bytesRead;}}finally{await f.close();}
 return hashes[p]={bytes,sha256:h.digest('hex'),realPath:real};
}
const compact=x=>({bytes:x.bytes,sha256:x.sha256});
async function bound(p,expected){const a=await identity(p);return equal(compact(a),compact(expected))&&(!expected.realPath||a.realPath===expected.realPath);}
const receipt=await get(runtime+'/receipt.json'), packet=await get(selected+'/controller-packet.json'), review=await get(selected+'/review.json');
const rootResult=await get(base+'/api28-settled-root-runtime-r3/result.json'), admission=await get(base+'/api28-settled-root-runtime-r3/admission.json');
const pkg=await get(base+'/api28-capture-settling/runtime-packet.json'), packageReview=await get(base+'/api28-capture-review/review.json');
const fixed={
 [runtime+'/receipt.json']:'8ed04011080ff9eefebf5e47aa271e7ff67e905baee1ef9193d2a043ca75766a',
 [selected+'/run_api28.py']:'ceed6350482dca07b366bc45196fd2334d1620fa7bff885b58d75a7f97b0ba14',
 [selected+'/controller-packet.json']:'9dbf4ddd2f19a3d89b2cdb2868674fb946edecf5d1d3de4be54a915c03f459ec',
 [selected+'/cleanup_control.py']:'8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df',
 [pkg.apk.path]:'af9502a62cf9174bdf929e957b1d93a4866fa8237f67fcaec1e81bd284ed2304',
 [base+'/api28-capture-review/review.json']:'a7208cec4d3ab3eadacd206264ace303232beb1cc2ccf8948bc9f62d7439955e'
};
for(const [p,h] of Object.entries(fixed))check('exact hash '+p.slice(base.length+1),(await identity(p)).sha256===h);
check('root admission exact accepted projection',admission.authorized===true&&admission.attemptLimit===1&&equal(admission.controllerReview,review)&&await bound(selected+'/controller-packet.json',admission.packet)&&await bound(base+'/api28-capture-review/review.json',admission.packageReview));
const projection=await get(selected+'/projection-provenance.json');let projectionDrift=[];
for(const [rel,e] of Object.entries(projection.files))if(!await bound(selected+'/'+rel,e)||!await bound(e.source,e))projectionDrift.push(rel);
check('all132 projection and immutable producer identities',Object.keys(projection.files).length===132&&projectionDrift.length===0,projectionDrift);
let bindingDrift=[];
for(const [p,e] of Object.entries(packet.bindings))if(!await bound(p,e))bindingDrift.push(p);
check('all1215 exact source/tool/retained-evidence bindings',Object.keys(packet.bindings).length===1215&&bindingDrift.length===0,bindingDrift);
const roster=await get(selected+'/assertion-roster.json');
const startup=await read(runtime+'/024-app-logcat-before-startup.stdout'), terminalLog=await read(runtime+'/026-all-assertion-logs.stdout');
const output=await read(runtime+'/025-exact-api28-instrumentation.stdout');
const passLines=s=>s.split(/\r?\n/).filter(l=>l.includes('MixerLowerApi: PASS '));
const pass=s=>passLines(s).map(l=>l.split('MixerLowerApi: PASS ')[1]);
check('both raw captures contain exact34 ordered assertions',roster.length===34&&equal(pass(startup),roster)&&equal(pass(terminalLog),roster)&&equal(receipt.result.assertions,roster));
const fields={}, duplicates=[], records=output.replaceAll('\r\n','\n').trimEnd().split('\n');
for(const line of records){if(line.startsWith('INSTRUMENTATION_RESULT: ')){const kv=line.slice(24),i=kv.indexOf('=');const k=kv.slice(0,i);if(Object.hasOwn(fields,k))duplicates.push(k);fields[k]=kv.slice(i+1);}}
check('one final canonical terminal -1',equal(records.filter(l=>l.trimStart().startsWith('INSTRUMENTATION_CODE')),['INSTRUMENTATION_CODE: -1'])&&records.at(-1)==='INSTRUMENTATION_CODE: -1');
check('raw result fields exact and unique',duplicates.length===0&&equal(fields,receipt.result.fields)&&fields.checks==='34'&&fields.sdk==='28'&&fields.abi==='arm64-v8a'&&fields.nativePacketBytes==='2254'&&fields.nativePacketNodes==='12'&&fields.nativeRevision==='1',{duplicates,fields});
check('no reported instrumentation or cleanup failure',!records.some(l=>/INSTRUMENTATION_FAILED|(?:failure|failureStage|failureTrace|cleanupFailure)=/.test(l))&&!receipt.failure&&!receipt.outputLimitFailure);
const pidSet=[...new Set(passLines(terminalLog).map(l=>l.trim().split(/\s+/)[2]))];
const appLines=terminalLog.split('\n').filter(l=>pidSet.includes(l.trim().split(/\s+/)[2]));
const errorPattern=/FATAL EXCEPTION|UnsatisfiedLinkError|NoClassDefFoundError|NoSuchMethodError|VerifyError|ExceptionInInitializerError|AbstractMethodError|IncompatibleClassChangeError|MixerLowerApi:\s*FAIL|Fatal signal/i;
const appErrorLines=appLines.filter(l=>errorPattern.test(l));
check('one appPID and no recorded app linkage/fatal failure',pidSet.length===1&&appErrorLines.length===0,{pidSet,appErrorLines});
const otherLinkageWarnings=terminalLog.split('\n').filter(l=>/dlopen failed|UnsatisfiedLinkError|NoClassDefFoundError|NoSuchMethodError|VerifyError|FATAL EXCEPTION/i.test(l)&&!pidSet.includes(l.trim().split(/\s+/)[2]));
let rawBytes=0;const commands=[];
for(const c of receipt.commands){
 const out=await fs.readFile(c.logs.stdout),err=await fs.readFile(c.logs.stderr);
 rawBytes+=out.length+err.length;
 const ok=c.state==='TERMINAL'&&c.direct_child_reaped&&c.stdout_eof&&c.stderr_eof&&c.owned_group_absent&&c.terminal_custody&&c.cleanup_errors.length===0&&c.stop===null&&c.output_limit===8388608&&c.aggregate_limit===67108864&&c.output_bytes===out.length+err.length&&c.output_bytes<=8388608;
 commands.push({...c,rawBytes:out.length+err.length,stdoutSHA256:digest(out),stderrSHA256:digest(err),verified:!!ok});
}
check('29 raw-command custody/reap/EOF/absence/output records',commands.length===29&&commands.every(c=>c.verified));
check('one native instance and instrumentation command',receipt.nativeInstancesStarted===1&&commands.filter(c=>c.label==='exact-api28-instrumentation').length===1&&commands.find(c=>c.label==='exact-api28-instrumentation').exit_code===0);
check('aggregate output exact and under64MiB',rawBytes===receipt.cleanup.aggregateBytes&&rawBytes<=67108864,{rawBytes});
check('recorded terminal cleanup and source postflight',receipt.cleanup.allTerminalCustody&&receipt.cleanup.hold===null&&receipt.cleanup.scratchRemoved&&receipt.cleanup.retainedListenerClosed&&receipt.privateADBKeysRemoved&&receipt.postflightStable);
check('no settings command',!commands.some(c=>c.argv.includes('settings')||c.argv.includes('setprop')||c.argv.includes('wm')));
check('sourcepair9 separated from rawPAIR8 and live103',receipt.sourcePair===9&&receipt.result.actualAPKSourcePair===9&&receipt.result.historicalEmittedPair===8&&receipt.liveCLIQualifiedByFrozenAPK===false&&receipt.frozenAPKSource101===packet.sourceDigest101&&receipt.liveCanonical103===packet.liveCanonicalDigest&&fields.gate==='PAIR8-LOWER-API-ART-LINKAGE');
check('actual API28 arm64 identity',receipt.observedRuntime['ro.build.version.sdk']==='28'&&receipt.observedRuntime['ro.product.cpu.abi']==='arm64-v8a'&&receipt.observedRuntime['ro.kernel.qemu']==='1'&&receipt.consoleIdentity.name===receipt.avd.name&&receipt.consoleIdentity.serial===receipt.targetSerial);
const images={};
for(const [name,expected] of Object.entries(receipt.screenshots)){
 const bytes=await fs.readFile(runtime+'/'+name);const retrieval=commands.find(c=>c.label==='retrieve-'+name);
 images[name]={...compact(await identity(runtime+'/'+name)),width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20),capture:receipt.result.captureReadiness[name]};
 check('exact unmodified screenshot '+name,images[name].bytes===expected.bytes&&images[name].sha256===expected.sha256&&images[name].sha256===retrieval.stdoutSHA256&&images[name].width===1080&&images[name].height===2400);
 const raw=fields[name+'.captureReadiness'];const captures=terminalLog.split('\n').filter(l=>l.includes('MixerLowerApi: CAPTURE '+name+' ')).map(l=>l.split('MixerLowerApi: CAPTURE '+name+' ')[1]);
 const m=Object.fromEntries(raw.split(';').flatMap((item,i,all)=>{if(!item.includes('='))return [];const j=item.indexOf('=');return [[item.slice(0,j),item.slice(j+1)+(item.startsWith('geometry=')?';'+all[i+1]:'')]];}));
 const a=receipt.result.captureReadiness[name].measured;
 check('CAPTURE identity geometry timing corroboration '+name,equal(captures,[raw])&&equal(m,a)&&Number(a.samples)===21&&a.quietMs==='1000'&&a.timeoutMs==='5000'&&Number(a.captureStartedUptimeMs)-Number(a.stableSinceUptimeMs)>=1000&&Number(a.captureStartedUptimeMs)-Number(a.startedUptimeMs)<5000&&Number(a.captureReturnedUptimeMs)>=Number(a.captureStartedUptimeMs)&&a.geometry==='0,0,1080,2400;0,63,1080,2211');
}
const external={};
for(const phase of ['before','after']){
 const dir=base+'/root-native-preservation/api28-settled-r3-'+phase;
 const r=await get(dir+'/receipt.json'), raw=await get(dir+'/000-known-external-device-states.stdout'),states={};
 for(const [runtime,devices]of Object.entries(raw.devices))for(const d of devices)states[d.udid]={runtime,name:d.name,state:d.state,isAvailable:d.isAvailable};
 check('external raw8 states and terminal custody '+phase,Object.keys(states).length===8&&equal(states,r.allDeviceStates)&&r.commands.every(c=>c.terminal_custody&&c.direct_child_reaped&&c.stdout_eof&&c.stderr_eof&&c.owned_group_absent)&&await bound(dir+'/receipt.json',rootResult[phase==='before'?'externalBefore':'externalAfter']));
 external[phase]={...compact(await identity(dir+'/receipt.json')),states,protected:r.protectedUUIDs};
}
check('all8 external states unchanged, both protectedBooted',equal(external.before.states,external.after.states)&&external.after.protected.every(u=>external.after.states[u].state==='Booted'));
check('root recorded exact ports released',equal(rootResult.portsVerifiedReleased,[5678,5679,60871])&&rootResult.allCommandsTerminal===true);
const host={};
for(const mode of ['normal','optimized']){
 const h=await get(selected+'/host-'+mode+'.json'),i=await get(selected+'/independent-'+mode+'.json'),s=await get(selected+'/review-supervisor-'+mode+'/receipt.json');
 check('genuine fresh134 host receipts '+mode,h.mode===mode&&h.status==='passed'&&h.tests===134&&h.cases.length===134&&h.errors.length===0&&h.failures.length===0&&await bound(selected+'/host-'+mode+'.json',review.hostReceipts[mode]));
 check('51 parser and4 independent fake cases '+mode,i.status==='passed'&&Object.keys(i.parserCases).length===51&&Object.values(i.parserCases).every(c=>c.accepted===c.expected)&&Object.keys(i.entrypointCases).length===4&&Object.entries(i.entrypointCases).every(([k,c])=>c.exitCode===(k==='canonical'?0:1)));
 check('host supervisor terminal custody '+mode,s.cleanup.allTerminalCustody&&s.commands.every(c=>c.terminal_custody&&c.direct_child_reaped&&c.stdout_eof&&c.stderr_eof&&c.owned_group_absent));
 host[mode]={receipt:compact(await identity(selected+'/host-'+mode+'.json')),status:h.status,tests:h.tests,parserCases:Object.keys(i.parserCases).length,entrypointCases:i.entrypointCases,actualFreshReceiptAdmission:i.actualFreshReceiptAdmission,supervisorCleanup:s.cleanup};
}
const producerNormal=selected.replace('review-r3','fix-r3')+'/host-normal.json',old=await get(producerNormal);
check('original producer normal failure preserved',old.status==='failed'&&old.tests===134&&await bound(producerNormal,(await get(selected+'/result.json')).failuresPreserved.producerNormal));
const packageCommands=await get(base+'/api28-capture-settling/attempt-1/commands/commands.json');
const pc=Array.isArray(packageCommands)?packageCommands:packageCommands.commands;
const signatureCommand=pc.find(c=>c.label==='verify-signature');
const signatureOutput=await read(base+'/api28-capture-settling/attempt-1/commands/018-verify-signature.stdout');
check('retained exactAPK signature verification',signatureCommand.exit_code===0&&signatureCommand.terminal_custody&&signatureCommand.argv.includes(pkg.apk.path)&&signatureOutput.includes('Verified using v3 scheme (APK Signature Scheme v3): true')&&signatureOutput.includes('Number of signers: 1')&&signatureOutput.includes('83527bc921cee5a49730703daccb5f303e20d4ef1ea255a3a3470654bf259ef9'));
check('accepted package DEX/native source provenance',packageReview.verdict==='ACCEPT'&&packageReview.scope==='CAPTURE_SOURCE_AND_STRICT_PACKAGE_ONLY'&&equal(pkg.apk,packageReview.apk)&&equal(pkg.productDEX,packageReview.DEX.product)&&equal(pkg.harnessDEX,packageReview.DEX.harness)&&pkg.productClassfiles===216&&pkg.productDEXDefinitions===389&&pkg.harnessDEXDefinitions===15&&pkg.definitionIntersection.length===0&&Object.keys(pkg.nativeLibraries).length===18);
const frozen=Object.entries(projection.files).filter(([p])=>p.startsWith('frozen-source101/'));
check('frozen101 count and live103 count',frozen.length===101&&Object.keys(packet.liveCanonicalInputs).length===103);
const audit={schema:1,recordedAt:new Date().toISOString(),scope:'Direct file audit only; historical runtime/cleanup evidence, no new process or device observation',checks,issues,allPassed:issues.length===0,assertions:roster,resultFields:fields,commands,images,external,host,source:{runtimeHEAD:receipt.currentHEAD,runtimeTree:receipt.currentTree,frozen101:receipt.frozenAPKSource101,live103:receipt.liveCanonical103,projectionFiles:Object.keys(projection.files).length,packetBindings:Object.keys(packet.bindings).length},rawLogSummary:{appPID:pidSet,appErrorLines,otherLinkageWarnings,startupMatchesRecorded:startup.trimEnd()===receipt.startupAppLog.trimEnd(),instrumentationMatchesRecorded:output.trimEnd()===receipt.instrumentationOutput.trimEnd()},signature:{command:signatureCommand,output:signatureOutput,verificationScope:'Historical apksigner log plus exact APK hash; no independent crypto recomputation'},historicalFailure:{status:old.status,tests:old.tests,errors:old.errors,failures:old.failures},cleanup:{...receipt.cleanup,privateADBKeysRemoved:receipt.privateADBKeysRemoved,postflightStable:receipt.postflightStable,portsRootAttestation:rootResult.portsVerifiedReleased,currentProcessObservation:false},fileIdentities:hashes,elapsedSeconds:(Date.now()-started)/1000,execution:{tool:'mcp__node_repl__js direct node:fs/promises and node:crypto',newChildProcesses:0,pythonAudits:0,nativeCommands:0,processProbes:0,network:0,heldScratchAccess:0}};
await fs.writeFile(own+'/audit.json',JSON.stringify(audit,null,2)+'\n',{flag:'wx'});
export default audit;
