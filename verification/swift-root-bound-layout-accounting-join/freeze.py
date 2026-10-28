#!/usr/bin/env python3
"""Run finite source/data checks and seal this proposal; no product command."""
from pathlib import Path
import contextlib
import datetime
import io
import json
import sys
import time
import build
import check

D=Path(__file__).resolve().parent
def own(path):return {'path':path.relative_to(D).as_posix(),**build.hashed(path)}
def put(path,obj):
    with path.open('x') as handle:json.dump(obj,handle,indent=2,sort_keys=True);handle.write('\n')
def main():
    start=time.monotonic();assert not (D/'seal.json').exists();out=D/'commands/final-offline';out.mkdir(parents=True)
    transcript=io.StringIO()
    with contextlib.redirect_stdout(transcript):report=check.main()
    (out/'stdout').write_text(transcript.getvalue());(out/'stderr').write_bytes(b'');put(D/'controls-result.json',report)
    receipt={'schema':1,'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'python_tool':build.row(Path(sys.executable).resolve()),
        'source_scripts':[own(D/n) for n in ['contract.py','build.py','check.py','freeze.py']],
        'source146_tree':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
        'input_manifest':own(D/'input-manifest.json'),'outputs':[own(out/'stdout'),own(out/'stderr')],
        'exit':0,'elapsed_seconds':time.monotonic()-start,'limits':{'wall_seconds':55,'compiler_parser_runtime_child_replays':0},
        'scope':'Source-only proposed accounting join; exact shape observations accepted upstream, all pricing/peak/backing/funding remain pending.'}
    put(out/'receipt.json',receipt)
    members=[own(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='seal.json']
    seal={'schema':1,'status':'FROZEN_SOURCE_ONLY_PROPOSED_LAYOUT_ACCOUNTING_JOIN','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'members':members,'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'tree_sha256':build.sha(build.canonical(members)),
        'root_layout_acceptance_sha256':build.hashed(build.A)['sha256'],'catalogue_shapes':29,'named_shapes':28,
        'place_binding_coverage':report['place_binding_coverage'],'integrity_controls':report['controls_passed'],
        'fully_closed_numeric_storage_charge_obligations':0,'work_storage_prices_peaks_backing_funding_full_ownership_GA_accepted':False,
        'compiler_parser_runtime_child_replays':0}
    put(D/'seal.json',seal)
    print(json.dumps({'status':seal['status'],'members':len(members),'seal_sha256':build.sha((D/'seal.json').read_bytes()),'tree_sha256':seal['tree_sha256'],'integrity_controls':report['controls_passed'],'fully_closed_storage_charge_obligations':0}))
if __name__=='__main__':main()
