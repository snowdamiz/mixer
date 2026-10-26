#!/usr/bin/env python3
"""Exact small first-ten-control checkpoint; no product execution."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parent
ROOT=REVIEW.parents[2]
MANIFEST=HERE/'manifest.json'
EXCLUDED={MANIFEST,HERE/'manifest.sha256',HERE/'seal-result.json'}


def record(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())


def read(p):return json.loads(p.read_text())


def prepare():
    candidate=REVIEW/'admission/candidate-4-manifest.json'
    assert record(candidate)['sha256']=='69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5'
    admitted=REVIEW/'admission/candidate-4-admission.json'
    assert record(admitted)['sha256']=='dabbcb66df621c37238d358adb54c89abfce006c399f4ad4eba1373c746eb5ea'
    compiled=read(REVIEW/'targeted-3/01-compile.command.json');assert compiled['exit_code']==0 and len(compiled['source_map'])==89
    authored=REVIEW/'attempts/003-counted-first10-controls.java'
    runner=REVIEW/'attempts/003-targeted-runner.py'
    assert record(authored)==compiled['source_map']['IndependentOwnerFocusReview.java']
    assert record(runner)['sha256']==compiled['independent_runner_sha256']
    paths={candidate,admitted,authored,runner,REVIEW/'record_tool_versions.py',Path(__file__)}
    for name,value in compiled['source_map'].items():
        p=authored if name=='IndependentOwnerFocusReview.java' else REVIEW/name
        assert record(p)==value;paths.add(p)
        if name!='IndependentOwnerFocusReview.java':assert read(candidate)['files'][name.removeprefix('candidate-4/')]==value
    rows=[]
    for command in sorted((REVIEW/'targeted-3').glob('03-*.command.json')):
        raw=read(command);assert raw['exit_code']==0 and raw['forced_termination'] is None
        stdout=command.with_name(command.name.replace('.command.json','.stdout'))
        results=[json.loads(x) for x in stdout.read_text().splitlines()]
        assert len(results)==2 and results[-1]['assertionSummary'] and results[-1]['assertions']>0
        rows.append(dict(mode=results[-1]['mode'],assertions=results[-1]['assertions'],exit_code=0,raw_result=str(stdout.relative_to(ROOT))))
    assert len(rows)==10 and sum(row['assertions'] for row in rows)==55
    for p in (REVIEW/'targeted-3').glob('*.command.json'):
        value=read(p);assert value['forced_termination'] is None
        assert value['limits']==dict(wall_seconds=120,stdout_bytes=2097152,stderr_bytes=2097152,owned_children=1)
        tool=Path(value['argv'][0]).name;assert value['executable_sha256']==read(REVIEW/'tools'/f'{tool}.command.json')['executable_sha256']
    cleanup=read(REVIEW/'targeted-3/cleanup.json')
    assert cleanup['owned_children_reaped'] and cleanup['exclusive_scratch_removed'] and not cleanup['native_or_capture_started'] and not(REVIEW/'scratch').exists()
    for directory in ['targeted-3','tools']:
        paths.update(p for p in (REVIEW/directory).rglob('*') if p.is_file())
    paths.update(REVIEW/name for name in ['independent-descriptor.json','independent-packet-1.json','independent-packet-2.json'])
    paths.update([REVIEW.parent/'leaf-review-1/run_leaf_sanity.py',REVIEW.parent/'preaccess/site-input-map.json',REVIEW.parent/'leaf-review-1/admission/leaf-manifest-3.json'])
    paths.update(p for p in HERE.rglob('*') if p.is_file() and p not in EXCLUDED)
    return paths,rows


def main():
    paths,rows=prepare();mode=sys.argv[1:]
    if mode==['--seal']:
        assert not any(p.exists() for p in EXCLUDED)
        receipt=dict(schema=1,scope='Ten independent actual frozen4 controls only',candidate_manifest_sha256='69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5',
            controls=rows,unique_controls=10,actual_assertions=55,original_uncounted_runs_preserved=['targeted-1','targeted-2'],counted_repeat='targeted-3',
            implementation_accepted=False,complete_matrix=False,CLI_consumer_qualified=False,native_qualified=False,source_mutations=False)
        (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');paths.add(HERE/'receipt.json')
        files={str(p.relative_to(ROOT)):record(p) for p in sorted(paths)}
        MANIFEST.write_text(json.dumps(dict(schema=1,scope='Exact frozen4 first10 independent controls; incomplete implementation qualification',files=files,members=len(files),bytes=sum(v['bytes'] for v in files.values()),
            excluded_metadata=['manifest.json','manifest.sha256','seal-result.json'],command=['python3','-B',str(Path(__file__).relative_to(ROOT)),'--seal'],python=sys.version),indent=2,sort_keys=True)+'\n')
        (HERE/'manifest.sha256').write_text(record(MANIFEST)['sha256']+'  manifest.json\n')
    elif mode!=['--check']:raise SystemExit('expected --seal or --check')
    paths,_=prepare();actual={str(p.relative_to(ROOT)):record(p) for p in sorted(paths)}
    assert actual==read(MANIFEST)['files']
    assert (HERE/'manifest.sha256').read_text()==record(MANIFEST)['sha256']+'  manifest.json\n'
    result=dict(status='frozen4-first10-control-checkpoint-verified',manifest_sha256=record(MANIFEST)['sha256'],members=len(actual),bytes=sum(v['bytes'] for v in actual.values()),
        actual_controls=10,actual_assertions=55,implementation_accepted=False,full_matrix_complete=False)
    if mode==['--seal']:(HERE/'seal-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    else:assert read(HERE/'seal-result.json')==result
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
