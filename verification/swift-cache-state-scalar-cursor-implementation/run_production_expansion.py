#!/usr/bin/env python3
import os,json
from run_host import ROOT,RUST,run,sha
r=run('production-expanded',[RUST,'--edition=2021','--crate-type=lib','--crate-name','cache_fixture','-Zunpretty=expanded',ROOT/'source/library/analyzer.rs'],dict(os.environ,RUSTC_BOOTSTRAP='1'))
assert r.returncode==0
s=r.stdout.decode()
for needle in ['fn cache_core<','static COMMIT_FAULT','static CLEANUP_FAULT','static SORT_MOVES','static SORT_COMPARISONS','mod selected_scalar_controls']:
 assert needle not in s,needle
(ROOT/'proofs/production-expansion.json').write_text(json.dumps({'schema':1,'actual_compiler_expansion':True,'command_receipt':'evidence/production-expanded.json','stdout_sha256':sha(ROOT/'evidence/production-expanded.stdout'),'test_only_hooks_absent':True,'no_compiler_expansion_budget_or_OTA_authority':True},indent=2)+'\n')
