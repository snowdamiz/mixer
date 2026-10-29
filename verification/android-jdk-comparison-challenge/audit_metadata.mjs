import * as fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
export async function audit(base) {
  const paths = [
    'verification/android-view-api-boundary-linux-tool-profile/archive-manifest.json',
    'verification/android-view-api-boundary-linux-tool-profile/analyze_archive.py',
    'verification/android-view-api-boundary-linux-tool-profile/derivation-receipt.json',
    'verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/compare_data.py',
    'verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/compare_actual_data_portable_limits.py',
    'verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/local/actual-comparison-002.stdout'
  ];
  const inputs = {}, texts = {};
  for (const path of paths) {
    const s = await fs.lstat(base + '/' + path);
    if (!s.isFile() || s.isSymbolicLink() || s.size > 262144) throw new Error('metadata/source bound refused');
    const data = await fs.readFile(base + '/' + path);
    inputs[path] = {bytes:data.length, sha256:createHash('sha256').update(data).digest('hex')};
    texts[path] = data.toString('utf8');
  }
  const manifest=JSON.parse(texts[paths[0]]), failure=JSON.parse(texts[paths[5]]);
  const checks=[];
  function check(name, ok, detail) { checks.push({name,pass:!!ok,detail}); if(!ok) throw new Error(name); }
  check('frozen-comparator-identity', inputs[paths[3]].sha256 === '156ce9f6ab5d5da580c788c051cbc98229ad641bd150810ef0bb93c92c2ff8c2', inputs[paths[3]]);
  check('frozen-wrapper-identity', inputs[paths[4]].sha256 === '0f2fbcd46ed3ab2da8c5d62742a5ba4e192fc60daaba50ab795f3148d37703fe', inputs[paths[4]]);
  check('root-not-preserved-as-member-row', manifest.member_count===543 && manifest.members.length===542 && manifest.members.every(x=>x.path!==manifest.archive_root), {member_count:manifest.member_count,persisted_rows:manifest.members.length});
  const bad = manifest.members.filter(x=>x.path.split('/').some(p=>p===''||p==='.'||p==='..'));
  check('all-persisted-components-already-canonical',bad.length===0,{checked:manifest.members.length,bad});
  const analyzer=texts[paths[1]];
  check('historical-analyzer-erases-trailing-slash-spelling',analyzer.includes('name = member.name.rstrip("/")'), {expression:'member.name.rstrip("/")'});
  const witness = manifest.members.find(x=>x.type==='symlink');
  const canonical = manifest.archive_root+'/'+witness.path;
  const candidates=[canonical,canonical+'/'];
  const project = x=>x.replace(/\/+$/,'');
  check('retained-data-does-not-distinguish-two-input-spellings',project(candidates[0])===project(candidates[1]),{hypothetical_not_observed:true,type:witness.type,candidates,persisted:canonical});
  check('failure-does-not-localize-parser-call',failure.stage==='fixed-two-member-comparison' && failure.error==='empty/dot/traversal name' && !('name' in failure) && !('site' in failure),failure);
  const comp=texts[paths[3]];
  check('same-refusal-shared-by-tar-and-zip',comp.includes('safe_name(member.name, member.isdir(), maximum=4096, depth=64)') && comp.includes('canonical_name = safe_name(name, directory)') && comp.includes('expected = inspect_zip(official[member]') && comp.includes('actual = inspect_zip(observed_raw_by_member[member]'),{candidate_sites:['official_tar','official_zip/lib/ct.sym','observed_zip/lib/ct.sym','official_zip/lib/jrt-fs.jar','observed_zip/lib/jrt-fs.jar']});
  return {schema:1,status:'metadata-challenge-complete-no-parser-correction-selected',command:'Node REPL: import audit_metadata.mjs; await audit(workspace)',tool:'mcp__node_repl.js',execution_environment:'persistent Node REPL; version unavailable without forbidden process metadata access',inputs,checks,archive_or_raw_file_reads:0,actual_data_comparisons:0,product_or_native_execution:false,runtime_admitted:false};
}
