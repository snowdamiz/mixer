#!/usr/bin/env python3
"""Audit and seal exact private transition evidence, without building or publishing."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def need(ok,what):
    if not ok: raise RuntimeError(what)
def main():
    candidate=HERE/'2026-10-23-candidate-2/receipt.json'; r=json.loads(candidate.read_bytes())
    need(sha(candidate.read_bytes())=='68f42282f4c1eaa9a7503e00b3fa0135d9d1ea01f2760f12d7524ae73e45413f','candidate pin')
    for p,d in r['source_files'].items():need(sha((Path(r['export'])/p).read_bytes())==d,'export '+p)
    for p,d in r['owned_files'].items():need(sha((ROOT/p).read_bytes())==d,'owned '+p)
    for p,d in r['baseline_files'].items():need(sha(subprocess.check_output(['git','show',r['dependency_revision']+':'+p],cwd=ROOT))==d,'Git '+p)
    for c in r['commands']:need(sha((ROOT/c['log']).read_bytes())==c['sha256'],'log '+c['name'])
    for mode,v in r['retained_products'].items():
        for p,d in v['files'].items():need(sha((Path(v['directory'])/p).read_bytes())==d,'retained '+mode+'/'+p)
    for outputs in r['artifacts'].values():
        for o in outputs:need(sha(Path(o['path']).read_bytes())==o['sha256'] and Path(o['path']).stat().st_size==o['bytes'],'artifact '+o['path'])
    for p,d in r['native_files'].items():need(sha((Path(r['native_copy'])/p).read_bytes())==d,'native '+p)
    old=json.loads((HERE/'candidate-1-host-cache-preservation.json').read_bytes())
    for p,d in old['files'].items():need(sha((Path(old['directory'])/p).read_bytes())==d,'prior TSan '+p)
    oldsources=json.loads((HERE/'candidate-1-preservation.json').read_bytes())
    for p,d in oldsources['files'].items():need(sha((ROOT/p).read_bytes())==d,'prior source '+p)
    reviews={
      'verification/capability-recovery-transitions-root-review/negative-cold-interruption/receipt.json':'bd5b01d4241694cf120c967be6b4b615e266ebc2d9d1d74eb6697b4aea6e4ba6',
      'verification/capability-recovery-transitions-root-review/cold-recovery-replay/receipt.json':'3e0a002bb2905e5817b11e649069eeae781a379e25fdd8c7e172b986ebd30d8b'}
    for p,d in reviews.items():need(sha((ROOT/p).read_bytes())==d,'review '+p)
    files={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['final-receipt.json','evidence-manifest.sha256','seal.log']}
    manifest=''.join(d+'  '+p+'\n' for p,d in sorted(files.items())).encode()
    (HERE/'evidence-manifest.sha256').write_bytes(manifest)
    result={'status':'Private transition scope passed; root cold-recovery regression replay passed. Coordinator/concrete composition and wider gates remain separate.',
      'model':'gpt-6.1-sol','reasoning_effort':'xhigh','dependency_revision':r['dependency_revision'],
      'candidate_receipt':str(candidate.relative_to(ROOT)),'candidate_receipt_sha256':sha(candidate.read_bytes()),
      'source_manifest_sha256':r['source_manifest_sha256'],'source_files':len(r['source_files']),'baseline_Git_files':len(r['baseline_files']),
      'commands':len(r['commands']),'new_test_functions':24,'all_debug_test_functions':78,'all_release_test_functions':78,'scoped_tsan_test_functions':24,
      'retained_files':sum(len(v['files']) for v in r['retained_products'].values()),'cross_client_artifacts':sum(len(v) for v in r['artifacts'].values()),
      'root_reviews':reviews,'root_replay_executions':9,'old_tsan_files_preserved':len(old['files']),
      'owned_files':r['owned_files'],'evidence_manifest_sha256':sha(manifest),'evidence_files':len(files),'seal_script_sha256':sha(Path(__file__).read_bytes()),
      'limitations':r['limitations']+['No public coordinator/concrete-adapter lifecycle composition. Synthetic test milestone reports are not actual product/UI/FieldLog health.', 'Controlled close/reopen is not process-crash or physical-device evidence.', 'Baseline six-case Signals is frozen; later root control-wake API and unfinished integration sources excluded.']}
    (HERE/'final-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'audit passed','source_files':result['source_files'],'baseline_Git_files':result['baseline_Git_files'],'commands':result['commands'],'retained_files':result['retained_files'],'artifacts':result['cross_client_artifacts'],'final_receipt_sha256':sha((HERE/'final-receipt.json').read_bytes()),'evidence_manifest_sha256':sha(manifest)},indent=2))
if __name__=='__main__':main()
