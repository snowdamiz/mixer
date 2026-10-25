import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {spawn, spawnSync} from 'node:child_process';
import {readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {join, resolve, relative} from 'node:path';
const base=import.meta.dirname,root=resolve(base,'../..'),producer=join(root,'verification/hosted-worker-pending-registry-components');
const sha=b=>createHash('sha256').update(b).digest('hex');
const bindings={};
async function bind(p){bindings[relative(root,p)]=sha(await readFile(p));}
const tested=JSON.parse(await readFile(join(producer,'runs/20261025T042823425Z/source-manifest.json'),'utf8'));
for(const [p,h] of Object.entries(tested)){await bind(join(root,p));if(bindings[p]!==h)throw new Error('source_changed:'+p);}
const compiled=JSON.parse(await readFile(join(producer,'runs/20261025T042823425Z/compiled-manifest.json'),'utf8'));
for(const [p,h] of Object.entries(compiled)){const file=join(producer,'candidate',p);await bind(file);if(bindings[relative(root,file)]!==h)throw new Error('compiled_changed:'+p);}
for(const p of ['receipt.json','integration.patch','artifact-manifest.json','runs/20261025T042823425Z/receipt.json','runs/20261025T042823425Z/commands.json','runs/20261025T042823425Z/test-report.json'])await bind(join(producer,p));
for(const p of ['worker.mjs','focused-controls.mjs','run-review.mjs'])await bind(join(base,p));
await writeFile(join(base,'source-manifest.json'),JSON.stringify(bindings,null,2)+'\n');
const require=createRequire(join(root,'hosted-worker-controller/package.json')),workerd=require('workerd').default;
const versions={node:process.version,workerd:spawnSync(workerd,['--version'],{encoding:'utf8',timeout:5000}).stdout.trim(),miniflare:JSON.parse(await readFile(join(root,'hosted-worker-controller/node_modules/miniflare/package.json'),'utf8')).version,platform:process.platform,arch:process.arch};
const sourceRevision=spawnSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',timeout:5000}).stdout.trim();
const scratch=join(base,'runtime-scratch');await mkdir(scratch,{recursive:true});
const argv=[process.execPath,join(base,'focused-controls.mjs')],startedUTC=new Date().toISOString();
const child=spawn(argv[0],argv.slice(1),{cwd:root,detached:true,stdio:['ignore','pipe','pipe'],env:{...process.env,TMPDIR:scratch,TEMP:scratch,TMP:scratch}});
const out=[],err=[];let stdoutEOF=false,stderrEOF=false,exitCode=null,exitSignal=null,timedOut=false;
child.stdout.on('data',b=>out.push(b));child.stderr.on('data',b=>err.push(b));child.stdout.on('end',()=>stdoutEOF=true);child.stderr.on('end',()=>stderrEOF=true);child.on('exit',(c,s)=>{exitCode=c;exitSignal=s;});
const alive=()=>{try{process.kill(-child.pid,0);return true;}catch(e){if(e.code==='ESRCH')return false;throw e;}};
const signal=s=>{try{process.kill(-child.pid,s);}catch(e){if(e.code!=='ESRCH')throw e;}};
const timer=setTimeout(()=>{timedOut=true;signal('SIGTERM');},45000),kill=setTimeout(()=>signal('SIGKILL'),50000);
await new Promise((res,rej)=>{child.once('close',res);child.once('error',rej);});clearTimeout(timer);clearTimeout(kill);
if(alive())signal('SIGKILL');
await rm(scratch,{recursive:true,force:true});
await writeFile(join(base,'focused.stdout'),Buffer.concat(out));await writeFile(join(base,'focused.stderr'),Buffer.concat(err));
const command={argv,cwd:root,startedUTC,endedUTC:new Date().toISOString(),exitCode,exitSignal,timedOut,directChildClosed:true,stdoutEOF,stderrEOF,groupAbsent:!alive(),scratchRemoved:true,stdoutSHA256:sha(Buffer.concat(out)),stderrSHA256:sha(Buffer.concat(err))};
await writeFile(join(base,'command.json'),JSON.stringify(command,null,2)+'\n');
await writeFile(join(base,'runtime-receipt.json'),JSON.stringify({schema:1,sourceRevision,testedProducerSourceSHA256:sha(JSON.stringify(tested)),reviewSourceSHA256:sha(JSON.stringify(bindings)),versions,command,sourceBindingsVerified:Object.keys(tested).length,compiledBindingsVerified:Object.keys(compiled).length,scope:'independent-focused-components-only'},null,2)+'\n');
console.log(JSON.stringify(command));process.exitCode=exitCode??1;
