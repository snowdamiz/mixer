import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {cp,mkdir,readdir,readFile,writeFile,stat} from 'node:fs/promises';
import {resolve,relative,join} from 'node:path';
import {createRequire} from 'node:module';
const project=import.meta.dirname,root=resolve(project,'../../..'),packet=resolve(project,'..');
const stamp=new Date().toISOString().replace(/[-:.]/g,''),run=join(packet,'runs',stamp);
await mkdir(join(run,'source'),{recursive:true});
const hash=b=>createHash('sha256').update(b).digest('hex');
const entries=[];
async function collect(dir){for(const ent of (await readdir(dir,{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))){if(ent.name==='dist')continue;const path=join(dir,ent.name);if(ent.isDirectory())await collect(path);else{const rel=relative(project,path),bytes=await readFile(path);entries.push({path:rel,sha256:hash(bytes),bytes:bytes.length});await mkdir(resolve(run,'source',rel,'..'),{recursive:true});await cp(path,join(run,'source',rel));}}}
await collect(project);
const sourceDigest=hash(entries.map(e=>`${e.path}\0${e.sha256}\0${e.bytes}\n`).join(''));
await writeFile(join(run,'source-manifest.json'),JSON.stringify({algorithm:'sha256',sourceDigest,entries},null,2)+'\n');
const require=createRequire(resolve(root,'hosted-worker-controller/package.json'));
const workerd=require('workerd').default;
const versions={node:process.version,platform:process.platform,architecture:process.arch,miniflare:require('miniflare/package.json').version,typescript:require('typescript/package.json').version,workersTypes:require('@cloudflare/workers-types/package.json').version,workerd:spawnSync(workerd,['--version'],{encoding:'utf8'}).stdout.trim()};
const commands=[];
for(const [name,args] of [['build',[join(project,'build.mjs')]],['test',[join(project,'test/run.mjs')]]]){
 const started=new Date().toISOString(),r=spawnSync(process.execPath,args,{encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024,env:{...process.env,MIXER_PENDING_ENGINE_REPORT:join(run,'report.json')}});
 await writeFile(join(run,name+'.stdout.log'),r.stdout??'');await writeFile(join(run,name+'.stderr.log'),r.stderr??'');
 commands.push({name,command:[process.execPath,...args],cwd:process.cwd(),startedUTC:started,finishedUTC:new Date().toISOString(),exitCode:r.status,signal:r.signal,error:r.error?.message??null,stdoutEOF:true,stderrEOF:true});
 process.stdout.write(r.stdout??'');process.stderr.write(r.stderr??'');
 if(r.status!==0)break;
}
const report=await readFile(join(run,'report.json'),'utf8').then(JSON.parse,()=>null);
const status=commands.length===2&&commands.every(c=>c.exitCode===0)&&report?.status==='passed'?'passed':'failed';
const receipt={schema:1,status,observedUTC:new Date().toISOString(),run:relative(root,run),sourceDigest,baselineRevision:'8b9b4950 (root supplied, live source snapshot separately bound)',frozenComponentDigest:'4b5df151a39ac703ef76705cf7d6d7a6c10ac69f4a2c5e6f2a33f2f1e6dd0078',versions,commands,groupsPassed:report?.results.filter(r=>r.status==='passed').length??0,groupsDefined:report?.cases??null,cleanup:report?.cleanup??[],limitations:report?.limitations??['build did not pass'],productionIntegration:false,deployedQualification:false,gaAccepted:false};
await writeFile(join(run,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');await writeFile(join(packet,'latest-run.json'),JSON.stringify({run:relative(root,run),receiptSHA256:hash(await readFile(join(run,'receipt.json'))),sourceDigest,status},null,2)+'\n');
console.log(JSON.stringify({status,run:receipt.run,sourceDigest,groupsPassed:receipt.groupsPassed,groupsDefined:receipt.groupsDefined}));
if(status!=='passed')process.exitCode=1;
