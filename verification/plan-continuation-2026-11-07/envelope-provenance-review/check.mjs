import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import {createHash} from 'node:crypto';

export async function runChecks(root) {
  const base=path.join(root,'verification/plan-continuation-2026-11-07');
  const assertions=[], inputs=[];
  const sha=b=>createHash('sha256').update(b).digest('hex');
  const check=(label,ok)=>{assertions.push({label,passed:!!ok});};
  async function read(p) {
    const canonical=await fs.realpath(p), st=await fs.stat(canonical);
    if(!st.isFile()||st.size>3000000)throw Error('Input exceeds file-only review scope: '+p);
    const b=await fs.readFile(canonical);
    inputs.push({path:p,canonical,bytes:b.length,sha256:sha(b)});
    return b;
  }
  const json=async p=>JSON.parse(await read(p));
  const p=part=>path.join(base,part);
  const prior=await json(p('envelope-actual-review/review.json'));
  const sealBytes=await read(p('envelope-actual-review/seal.json'));
  const seal=JSON.parse(sealBytes);
  check('Pinned prior review seal',sha(sealBytes)==='fae6ca715cb9de6260b908b46803700a553b5b98beee3a8c0a16bbd2ddb44b68');
  check('Prior seal member count',seal.member_count===145 && seal.members.length===145);
  let sealedBytes=0;
  for(const m of seal.members) {
    if(path.isAbsolute(m.path)||m.path.split('/').includes('..'))throw Error('Unsafe seal member');
    const b=await read(p('envelope-actual-review/'+m.path));sealedBytes+=b.length;
    check('Prior sealed member '+m.path,b.length===m.bytes&&sha(b)===m.sha256);
  }
  check('Prior seal total bytes',sealedBytes===694640&&sealedBytes===seal.total_bytes);
  const prov=await json(p('envelope-provenance/provenance.json'));
  const metadata={};
  for(const [name,pin] of Object.entries(prov.providerRecords)) {
    const b=await read(p('envelope-provenance/'+name));
    check('Provider metadata pin '+name,b.length===pin.bytes&&sha(b)===pin.sha256);
    metadata[name]=JSON.parse(b);
  }
  const run=metadata['run.json'];
  const jobs=metadata['attempt-1-jobs.json'].jobs;
  const job=jobs.find(j=>j.id===128544872058);
  const connectorJob=metadata['jobs.json'].jobs.find(j=>j.id===128544872058);
  const art=metadata['artifacts.json'].artifacts.find(a=>a.id===13592908052);
  const revision='df7b67ace3441707049d47c289cefaed83dcdc6c';
  const archiveSHA='9a837ebd67d865b2bc4f5cc7e53f6e245ecdd1b49731f2be49e68279384890af';
  check('Run repository, ID, attempt and source',run.repository.full_name==='snowdamiz/mixer'&&run.id===42419571138&&run.run_attempt===1&&run.head_sha===revision&&run.head_commit.id===revision&&run.head_commit.tree_id===prior.git_tree&&run.path==='.github/workflows/verify.yml'&&run.event==='push');
  check('Run is completed; whole workflow failure preserved',run.status==='completed'&&run.conclusion==='failure');
  check('Exact attempt jobs complete and unique Swift selection',metadata['attempt-1-jobs.json'].total_count===jobs.length&&jobs.filter(j=>j.id===128544872058).length===1);
  check('Swift job source, attempt and success',job.name==='swift'&&job.run_id===run.id&&job.run_attempt===1&&job.head_sha===revision&&job.status==='completed'&&job.conclusion==='success');
  const projectSteps=steps=>steps.map(({name,status,conclusion,number})=>({name,status,conclusion,number}));
  check('Connector matches raw job and all steps',connectorJob.name===job.name&&connectorJob.run_id===run.id&&connectorJob.status===job.status&&connectorJob.conclusion===job.conclusion&&JSON.stringify(connectorJob.steps)===JSON.stringify(projectSteps(job.steps)));
  const expectedNames=['Bind reviewed envelope and prospective compiler selection','Guarded envelope and prospective compiler adoption controls','Standalone analyzer envelope with prospectively selected compiler','Verify prospective envelope adoption source postflight','Preserve standalone analyzer envelope receipts'];
  for(let i=0;i<expectedNames.length;i++) {const s=job.steps.find(s=>s.number===8+i);check('Envelope step '+(8+i),s?.name===expectedNames[i]&&s.status==='completed'&&s.conclusion==='success');}
  check('Artifact provider identity',art.id===13592908052&&art.workflow_run.id===run.id&&art.workflow_run.head_sha===revision&&art.workflow_run.repository_id===run.repository.id&&art.digest==='sha256:'+archiveSHA&&art.size_in_bytes===770713&&art.name==='analyzer-envelope-host-'+revision&&!art.expired);
  const upload=job.steps.find(s=>s.number===12);
  check('Artifact created within exact upload step',art.created_at>=upload.started_at&&art.created_at<=upload.completed_at);
  check('Prior reviewed identity agrees',prior.revision===revision&&prior.archive_sha256===archiveSHA&&prior.run_root_attribution===run.id&&prior.artifact_root_attribution===art.id&&prior.artifact_data_accepted&&prior.compiler_identity.release==='1.99.1');
  const acquisition=await json(p('envelope-provenance/bounded-acquisition.json'));
  const script=await read(p('envelope-provenance/acquire_bounded.py'));
  check('Acquisition script hash',sha(script)===acquisition.scriptSHA256&&sha(script)==='d78b383d349444a32e9907b0dd251d813b5a59583f30c701de999b24a9b65599');
  check('Exact artifact acquisition command',JSON.stringify(acquisition.argv)===JSON.stringify(['gh','api','repos/snowdamiz/mixer/actions/artifacts/13592908052/zip'])&&acquisition.artifact===art.id&&acquisition.expectedSHA256===archiveSHA);
  check('Successful bounded body and direct child custody',acquisition.status==='passed-complete-bounded-acquisition'&&acquisition.exit===0&&acquisition.directChildReaped===true&&acquisition.bodyCompleted===true&&acquisition.ownedGroupAbsent===true&&acquisition.pid===acquisition.ownedPGID&&Number.isInteger(acquisition.pid)&&acquisition.pid>0);
  check('Both pipe EOFs and reader closure',acquisition.streamEOF.stdout===true&&acquisition.streamEOF.stderr===true&&acquisition.pipeReadersClosed===true);
  check('Acquisition caps and recorded elapsed',acquisition.limits.seconds===15&&acquisition.limits.cleanupSeconds===5&&acquisition.limits.stdoutBytes===2000000&&acquisition.limits.stderrBytes===65536&&acquisition.elapsedSeconds>=0&&acquisition.elapsedSeconds<15&&acquisition.streams.stdout.bytes<=2000000&&acquisition.streams.stderr.bytes<=65536);
  check('Clean terminal evidence',acquisition.signals.length===0&&acquisition.cleanupErrors.length===0&&!('failure' in acquisition)&&acquisition.streams.stderr.bytes===0&&acquisition.streams.stderr.sha256===sha(Buffer.alloc(0)));
  check('Transport limitation retained',acquisition.limitations.includes('gh internal HTTP events and provider disposal are not separately instrumented'));
  for(const archive of [acquisition.archive,'/tmp/mixer-20261107-ci-df7-envelope.zip']) {const b=await read(archive);check('Complete archive identity '+archive,b.length===770713&&sha(b)===archiveSHA&&sha(b)===acquisition.streams.stdout.sha256&&b.length===acquisition.streams.stdout.bytes);}
  const workflow=await read(path.join(root,'.github/workflows/verify.yml'));
  const text=workflow.toString('utf8'), nl=String.fromCharCode(10), start=text.indexOf(nl+'  swift:'+nl)+1, end=text.indexOf(nl+'  swift-capability-native:'+nl)+1;
  check('Workflow source bound to prior review',sha(workflow)==='5cc067d90adaadbb4741e8e0e25bf1ecace4fa2d5ce87cbe13cfddb92fc67325');
  check('Exact sealed Swift job source',start>0&&end>start&&sha(text.slice(start,end))==='0e3ed51a0de31b06a00fa24d1276c58790de7ccc72c72bc9633869601acb4c3f');
  const manifest=await json(p('envelope-actual-review/input-manifest.json'));
  const historical=manifest.filter(m=>m.path.includes('/rust-1991-first-actual-result/')||m.path.includes('/rust-1991-actual-audit-preparation-v2/')||m.path.endsWith('/envelope-rust-1991-default-ci-adoption/root-selection.json'));
  for(const m of historical){const b=await read(m.path);check('Historical source/record unchanged '+m.path,b.length===m.bytes&&sha(b)===m.sha256);}
  for(const input of [...inputs]) {const b=await fs.readFile(input.canonical);check('Input stable '+input.path,b.length===input.bytes&&sha(b)===input.sha256);}
  const failed=assertions.filter(a=>!a.passed);
  return {schema:1,scope:'Pure file/JSON/hash addendum; no workload replay, acquisition, process probe or runtime execution',passed:failed.length===0,assertionCount:assertions.length,failed,inputs,assertions,priorSealSHA256:sha(sealBytes),priorReviewSHA256:seal.members.find(m=>m.path==='REVIEW.md').sha256,identity:{repository:'snowdamiz/mixer',run:run.id,attempt:1,swiftJob:job.id,revision,gitTree:prior.git_tree,artifact:art.id,archiveBytes:770713,archiveSHA256:archiveSHA,compiler:prior.compiler_identity},acquisition,providerRunConclusion:run.conclusion,historicalFilesChecked:historical.length};
}
