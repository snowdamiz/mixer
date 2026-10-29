import * as fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
const A='verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/';
const C='verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/';
const D='verification/android-view-api-focused-actual-review/jdk-data-actual-review/';
function sha(b){return createHash('sha256').update(b).digest('hex');}
function parse(b){return JSON.parse(b.toString('utf8'),(k,v,c)=>typeof v==='number'&&!Number.isSafeInteger(v)?BigInt(c.source):v);}
function canon(v){if(typeof v==='bigint')return v.toString();if(v===null||typeof v==='number'||typeof v==='boolean')return JSON.stringify(v);if(typeof v==='string')return JSON.stringify(v).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));if(Array.isArray(v))return '['+v.map(canon).join(',')+']';return '{'+Object.keys(v).sort().map(k=>canon(k)+':'+canon(v[k])).join(',')+'}';}
export async function review(base){
 const inputs={},checks=[]; const ck=(name,pass)=>{checks.push({name,pass:!!pass});if(!pass)throw new Error(name);};
 async function read(path,cap=1048576){if(/(?:\.raw-data\.bin|artifact\.zip|\.tar\.gz)$/.test(path))throw new Error('raw or archive path forbidden');const st=await fs.lstat(base+'/'+path);if(!st.isFile()||st.isSymbolicLink()||st.size>cap)throw new Error('metadata/source size or type refused');const b=await fs.readFile(base+'/'+path);inputs[path]={bytes:b.length,sha256:sha(b)};return b;}
 const rb=await read(A+'local/actual-comparison-004.stdout',25*1024*1024),r=parse(rb);
 const sb=await read(A+'result-summary.json'),s=parse(sb);
 ck('report complete bytes and hash',rb.length===19914808&&sha(rb)==='860fdf3c949ad1c084cc16e9983ebc65e0293ba8062f701705600501e5ef8d8a');
 ck('summary exact bytes and hash',sb.length===7617&&sha(sb)==='686bf444ff17bce6131b38dd22e79f4b146cc63c8931c9493a06cb2eeaa5c158');
 const cp=rb.subarray(0,-1),canonical=canon(r);
 ck('canonical payload exact lossless roundtrip',rb.at(-1)===10&&cp.toString('utf8')===canonical&&cp.length===19914807&&sha(cp)==='dccf29b5239f9d5c71aea05c07d13d72f0f4abc3796d2b2674bad7dfbd2d255e');
 ck('root report hash fields',s.report.bytes===rb.length&&s.report.sha256===sha(rb)&&s.report.canonical_json_bytes===cp.length&&s.report.canonical_json_sha256===sha(cp));
 const stderr=await read(A+'local/actual-comparison-004.stderr'),st=parse(stderr);
 ck('stderr exact summary binding',stderr.length===359&&sha(stderr)==='4cfd8238f74c583fdfade7bd679c5f4446af9834808fe7945071e1329140ec7f'&&st.json_bytes===cp.length&&st.json_sha256===sha(cp)&&canon(st)===canon(s.stderr.summary));
 const ct=r.results['lib/ct.sym'],jr=r.results['lib/jrt-fs.jar'];
 ck('exact two result members',canon(Object.keys(r.results).sort())===canon(['lib/ct.sym','lib/jrt-fs.jar']));
 const count={};
 for(const [member,row] of Object.entries(r.results))for(const side of ['official','observed']){
  const order=row.global_metadata_changes[side].entry_order;
  count[member+'/'+side]={entries:order.length,files:order.filter(x=>!x.endsWith('/')).length,directories:order.filter(x=>x.endsWith('/')).length};
  ck(member+'/'+side+' complete unique entry order',new Set(order).size===order.length&&order.length===row[side].entries);
 }
 ck('ct counts',Object.values(count).slice(0,2).every(x=>x.entries===15710&&x.files===13653&&x.directories===2057));
 const removed=ct.payload_changes.filter(x=>x.official!==null&&x.observed===null),added=ct.payload_changes.filter(x=>x.official===null&&x.observed!==null),map=new Map(added.map(x=>[x.path,x])),empty=sha('');
 ck('ct change rows partition',ct.payload_changes.length===408&&removed.length===204&&added.length===204&&map.size===204);
 const pairs=[];
 for(const x of removed){const y=map.get(x.path.slice(0,-1));ck('empty directory pair '+x.path,x.path.endsWith('//')&&!x.path.endsWith('///')&&!!y&&!y.path.endsWith('//')&&[x.official,y.observed].every(z=>z.directory===true&&z.bytes===0&&z.crc32===0&&z.sha256===empty));pairs.push({official:x.path,observed:y.path,empty_payload_sha256:empty});}
 pairs.sort((a,b)=>a.official<b.official?-1:a.official>b.official?1:0);
 ck('pairing is unambiguous',new Set(pairs.map(x=>x.official)).size===204&&new Set(pairs.map(x=>x.observed)).size===204);
 const co=ct.global_metadata_changes.official.entry_order,ca=ct.global_metadata_changes.observed.entry_order,os=new Set(co),as=new Set(ca);
 ck('raw entry set differences exactly pair names',canon(co.filter(x=>!as.has(x)).sort())===canon(pairs.map(x=>x.official).sort())&&canon(ca.filter(x=>!os.has(x)).sort())===canon(pairs.map(x=>x.observed).sort()));
 ck('all ct file names identical and no changed file payload row',canon(co.filter(x=>!x.endsWith('/')).sort())===canon(ca.filter(x=>!x.endsWith('/')).sort())&&ct.payload_changes.every(x=>(!x.official||x.official.directory)&&(!x.observed||x.observed.directory)));
 const savedPairs=parse(await read(A+'empty-directory-name-pairs.json'));
 ck('derived pairs equal saved rows',canon(pairs)===canon(savedPairs));
 ck('root pair rows compact insertion-order hash',sha(JSON.stringify(pairs))===s.derived_content_findings.ct_sym.directory_pair_rows_sha256);
 ck('jrt exact 61-entry payload map',jr.official.entries===61&&jr.observed.entries===61&&jr.payload_changes.length===0&&jr.official.payload_map_sha256===jr.observed.payload_map_sha256&&canon([...jr.global_metadata_changes.official.entry_order].sort())===canon([...jr.global_metadata_changes.observed.entry_order].sort()));
 ck('jrt only changed compressed stream is empty META-INF directory',jr.compressed_stream_changes.length===1&&jr.compressed_stream_changes[0].path==='META-INF/'&&jr.compressed_stream_changes[0].official.bytes===2&&jr.compressed_stream_changes[0].observed.bytes===0&&jr.compressed_stream_changes[0].observed.sha256===empty);
 const expanded=Object.values(r.results).flatMap(x=>[x.official,x.observed]).reduce((a,x)=>a+x.uncompressed_bytes,0);
 ck('all four ZIP expanded counts reconcile',expanded===24742972&&r.zip_actual_uncompressed_bytes_all===expanded&&s.expanded_zip_bytes_all===expanded);
 ck('official tar count and exact identity',r.official_archive.tar_members===543&&r.official_archive.gzip_delivered_bytes===332994560&&r.official_archive.archive.bytes===193594705&&r.official_archive.archive.sha256==='8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711');
 for(const [member,row] of Object.entries(r.results)){const su=s.results[member];ck(member+' summaries and classification reconcile',canon(row.official)===canon(su.official)&&canon(row.observed)===canon(su.observed)&&row.outcome===su.outcome&&row.outcome===st.outcomes[member]&&row.payload_changes.length===su.payload_change_rows&&row.compressed_stream_changes.length===su.compressed_stream_change_rows&&row.metadata_changes.length===su.metadata_change_rows&&row.all_indexed_bytes_accounted===true&&su.all_indexed_bytes_accounted===true&&!!row.global_metadata_changes===su.global_metadata_changed);}
 const wb=await read(C+'compare_actual_data_directory_suffix.py'),cb=await read(C+'compare_data.py'),tb=await read(C+'check_synthetic_directory_suffix.py');
 ck('exact comparator wrapper checker identities',sha(wb)==='d6525178607afec30783b3a685a156e3bfc3afb43a82dc99b78b73f8138e86db'&&sha(cb)==='703248739576b3d0df9b370e3cc83d9342889d630dae7a440e19e8bdd7482f9d'&&sha(tb)==='bf95b9440b984cad326b40e6a715f1c7753f253c4391319460cd3f1bd4ab66bb');
 const controlsB=await read(A+'directory-suffix-controls.json'),controls=parse(controlsB);
 ck('104 guarded synthetic controls retained',sha(controlsB)==='72cce875f026f33ac4b72ea16adce7436041d57b1b8f27ef3c1ef51b90aab46b'&&controls.checks.length===104&&controls.checks.every(x=>x.pass===true)&&controls.passed===104&&controls.failed===0&&controls.source_sha256===sha(cb)&&controls.real_archive_or_observation_read===false);
 const g=r.guarded_wrapper,reads=g.stable_input_reads;
 ck('exact five stable acquisitions',canon(Object.keys(reads).sort())===canon(['archive','audit','lib/ct.sym','lib/jrt-fs.jar','source'].sort()));
 for(const [key,x] of Object.entries(reads))ck(key+' stable single acquisition',canon(x.before_stat)===canon(x.after_stat)&&canon(x.before_stat)===canon(x.named_after_stat)&&x.before_stat[6]===x.bytes&&(x.before_stat[2]&0o170000)===0o100000&&x.before_stat[3]===1&&x.file_opens===1&&x.sequential_read_passes===1&&x.symlink_components_followed===false);
 const auditB=await read(D+'actual-review-receipt.json'),audit=parse(auditB),sealB=await read(D+'actual-review-seal.json');
 ck('audit input and seal bound',sha(auditB)===g.successful_audit.sha256&&auditB.length===g.successful_audit.bytes&&sha(auditB)===reads.audit.sha256&&sha(sealB)===g.successful_audit_seal.sha256);
 ck('source and official archive input bound',sha(cb)===reads.source.sha256&&cb.length===reads.source.bytes&&sha(cb)===g.source.sha256&&canon({bytes:reads.archive.bytes,sha256:reads.archive.sha256})===canon(r.official_archive.archive));
 for(const [member,row] of Object.entries(r.results)){ck(member+' raw identity cross-binds',canon(row.official.raw)===canon(r.official_archive.selected[member])&&canon(row.observed.raw)===canon({bytes:reads[member].bytes,sha256:reads[member].sha256})&&row.observed.raw.bytes===g.observed_raw[member].bytes&&row.observed.raw.sha256===g.observed_raw[member].sha256&&row.observed.raw.sha256!==row.official.raw.sha256);}
 const ws=wb.toString('utf8');
 ck('guard installed before subject evaluation by bound source',ws.indexOf('sys.addaudithook(_audit)')<ws.indexOf('_original_exec(_original_compile(loaded["source"]')&&g.source_evaluated_after_denials===true&&g.subprocesses===0&&g.Java_or_JVM===false);
 ck('isolated Python context',g.runtime.isolated===true&&g.runtime.no_site===true&&g.runtime.dont_write_bytecode===true&&g.runtime.executable==='/opt/homebrew/bin/python3'&&canon(g.runtime)===canon(s.execution.python));
 const lim=g.self_limit_results;
 ck('CPU and output limits enforced exactly',lim.cpu.enforced===true&&lim.cpu.requested===120&&canon(lim.cpu.after)==='[120,120]'&&lim.file_size.enforced===true&&lim.file_size.requested===67174401&&canon(lim.file_size.after)==='[67174401,67174401]');
 ck('AS fallback precise and unchanged without wall claim',lim.address_space.enforced===false&&lim.address_space.requested===1073741824&&lim.address_space.error==='current limit exceeds maximum limit'&&canon(lim.address_space.before)===canon(lim.address_space.after)&&g.limits.external_wall_seconds_enforced===null&&s.execution.address_space_limit_enforced===false&&s.execution.external_wall_limit_enforced===false);
 const failed=[];
 for(const n of ['001','002','003']){const b=await read(A+'local/actual-comparison-'+n+'.stdout'),e=await read(A+'local/actual-comparison-'+n+'.stderr'),f=parse(b);ck('failure '+n+' preserved',f.actual_comparison_completed===false&&f.runtime_admitted===false&&e.length===0);failed.push({invocation:Number(n),bytes:b.length,sha256:sha(b),stage:f.stage,error:f.error});}
 ck('001 original self-limit refusal',failed[0].sha256==='7468177df7925fa85c1f633d47b989a020d8dbfd8c1df07e0fe386a6d334e1c9'&&failed[0].stage==='self-limits');
 ck('002 original generic parser refusal',failed[1].sha256==='3290b820f7a25e1bc508efec5d90bda9321aa57d37d0e7cb602131ea50558e11'&&failed[1].stage==='fixed-two-member-comparison');
 ck('003 exact localized failure',failed[2].sha256==='e0aa3fa2e373b89d32f016d03f685d1d87be24ddb39e755764ba87660f922e91');
 const one=parse(await read(A+'first-execution-refusal.json')),two=parse(await read(A+'second-execution-refusal.json')),three=parse(await read(A+'context-refusal.json'));
 const select=parse(await read(A+'directory-suffix-selection.json'));
 ck('campaign exhausted at four invocations and three archive acquisitions',one.archive_or_raw_reads===0&&two.invocation===2&&two.failure.stage==='fixed-two-member-comparison'&&Object.keys(three.context.stable_input_reads).length===5&&select.comparison_invocations_total_ceiling===4&&select.archive_read_invocations_total_ceiling===3&&select.remaining_after_this_invocation===0&&s.execution.invocations_total===4&&s.execution.archive_read_invocations===3&&s.execution.remaining_allowance===0&&s.exit_code===0);
 const ob=await read(D+'local/recovery-001/extracted/04-observation.json'),obs=parse(ob),eb=await read(D+'local/recovery-001/extracted/09-expected-runtime-members.json'),expected=parse(eb);
 ck('observation and expected74 identities bound to outer audit',sha(ob)==='052e3b24464376dafc82e2e3cc4f6e044fd4412f7d36e6be94e8dce00af32c1c'&&sha(eb)==='c75e64616ebb599f7337df7d7026286f1fd2d300347b59e28fb8a1051fdef13f'&&audit.outer_zip.members.some(x=>x.sha256===sha(ob)&&x.bytes===ob.length)&&audit.outer_zip.members.some(x=>x.sha256===sha(eb)&&x.bytes===eb.length));
 ck('complete74 ordinary stable source reports',expected.length===74&&obs.members.length===74&&new Set(obs.members.map(x=>x.path)).size===74&&obs.expected_members_observed===74&&obs.refused_members.length===0&&obs.unexpected_membership_observed===false&&canon(obs.members.map(x=>x.path).sort())===canon(expected.map(x=>x.path).sort()));
 const em=new Map(expected.map(x=>[x.path,x]));const differences=[];
 for(const x of obs.members){ck(x.path+' exact expected and stable record',canon(x.expected)===canon(em.get(x.path))&&x.observed.status==='stable-regular-file'&&canon(x.observed.before)===canon(x.observed.after)&&x.observed.bytes===x.observed.before.size&&(x.observed.before.mode&0o170000)===0o100000);if(x.expected.bytes!==x.observed.bytes||x.expected.sha256!==x.observed.sha256)differences.push({path:x.path,official:{bytes:x.expected.bytes,sha256:x.expected.sha256},observed:{bytes:x.observed.bytes,sha256:x.observed.sha256}});}
 ck('only two full-file pins differ',canon(differences.map(x=>x.path).sort())===canon(['lib/ct.sym','lib/jrt-fs.jar'])&&obs.members.length-differences.length===72&&differences.every(x=>canon(x.observed)===canon(r.results[x.path].observed.raw)));
 ck('observed total bytes reconcile',obs.members.reduce((a,x)=>a+x.observed.bytes,0)===198637181&&obs.jdk_actual_bytes_read===198637181);
 ck('no authority promoted',r.runtime_admitted===false&&r.cause_or_provider_provenance_established===false&&r.prepared13_or152_pass===false&&r.old_focused_allowance_reused===false&&g.runtime_admitted===false&&Object.values(r.results).every(x=>x.runtime_admitted===false)&&Object.values(s.admission).every(x=>x===false));
 return {schema:1,status:'accepted-scoped-data-classification-preparation-only',command:'Node REPL import actual_result_review.mjs; await review(workspace)',tool:'mcp__node_repl.js; fs/crypto and lossless JSON data only',inputs,checks,passed:checks.length,failed:0,derived:{counts:count,directory_pairs:pairs.length,directory_pair_rows_compact_insertion_order_sha256:sha(JSON.stringify(pairs)),directory_pair_rows_canonical_sorted_keys_sha256:sha(canon(pairs)),ct_file_payload_or_name_change_rows:0,jrt_payload_change_rows:0,jrt_compressed_change_path:'META-INF/',expanded_zip_bytes:expanded,official_tar_entries:543,observed_runtime_members:74,exact_official_matches:72,whole_file_pin_differences:differences,observed_runtime_total_bytes:198637181},failure_history:failed,campaign:{invocations:4,archive_acquisitions:3,remaining_allowance:0,second_run_acquisition_basis:'bound wrapper control flow; original failure omitted per-input receipts; no retrospective receipts invented'},decision:{data_classification_accepted:true,separate_exact74_package_observed_profile_preparation_supported:true,runtime_execution_authorized:false,official_archive_profile_mutation_supported:false,automatic_pin_learning_supported:false,provider_provenance:false,old_mismatch_cause:false,actual13_or152:false,canonical_source_pair:false,native_OTA_GA:false},limitations:['Data-only verification of complete report and source-bound observation; no archive/raw-member rereads or decompression.','Guard assertions are bound source and receipt evidence, not hostile-code sandbox or kernel attestation.','Package metadata and selected MD5 match do not authenticate package distribution provenance.','Provider ImageVersion discrepancy remains 20261026.354.1 artifact versus 20261025.353.1 setup-log summary.'],archive_or_raw_file_reads:0,comparator_or_runtime_executions:0};
}
