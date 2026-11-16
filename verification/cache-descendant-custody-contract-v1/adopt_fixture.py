"""Typed prospective cache observer; immutable R8 guards remain binding."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREVIOUS=ROOT/'verification/plan-continuation-2026-11-07/cache-refusal-cleanup-r8'
SOURCE=ROOT/'verification/cache-fixture-shared-input-candidate-v2/check_cache_state.py'
WORKFLOW=ROOT/'.github/workflows/verify.yml'
KIND='cache-descendant-custody-contract-v1'
PREVIOUS_SEAL='b03ce3298336634c28f97502d8b035f4f28de176a4675bce6b083f457fe38e65'
SHIPPING=['adopt_fixture.py','commands.py','process_adapter.py','test_contract.py','test_original.py','workflow-job.yml']
def need(value,message):
    if not value:raise RuntimeError(message)
def digest(path):
    need(path.is_file() and not any(p.is_symlink() for p in [path,*path.parents]),'Regular source required')
    return hashlib.sha256(path.read_bytes()).hexdigest()
def previous():
    need(digest(PREVIOUS/'adopt_fixture.py')=='9ada7e4b63a60d87ef7831c187044155526f90179304959e0972aee0938def30','R8 adapter drift')
    need(digest(PREVIOUS/'sources.json')==PREVIOUS_SEAL,'R8 seal drift')
    spec=importlib.util.spec_from_file_location('cache_closed_r8',PREVIOUS/'adopt_fixture.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    return old
def verify(installed=False,workflow=None):
    old=previous();proof=old.verify(False)
    seal=json.loads((HERE/'sources.json').read_bytes())
    need(seal.get('kind')==KIND and seal.get('schema')==1,'Typed successor required')
    need([r['path']for r in seal['members']]==SHIPPING and seal['member_count']==len(SHIPPING),'Exact successor roster required')
    binding=old.previous().previous().baseline()
    binding.check_rows(HERE,seal['members'])
    need(seal['tree_sha256']==binding.tree(seal['members']),'Successor source tree differs')
    if installed:need(binding.job_text((WORKFLOW if workflow is None else workflow).read_text())==(HERE/'workflow-job.yml').read_text(),'Installed cache job differs')
    return {'kind':KIND,'previous':proof,'sources_sha256':digest(HERE/'sources.json'),'tree_sha256':seal['tree_sha256'],'installed':installed,'compiler_qualified':False,'GA':False}
def install(runner):
    need(digest(Path(runner.__file__))==digest(SOURCE),'Frozen runner differs')
    need((runner.ACTIVE_SECONDS,runner.CLEANUP_SECONDS,runner.CHILD_SECONDS,runner.OUTPUT_CAP)==(600,60,60,8388608),'Budgets differ')
    for name in ['process_adapter.py','commands.py']:exec(compile((HERE/name).read_bytes(),str(HERE/name),'exec'),runner.__dict__)
    return runner
def run_fixture(output,rustc):
    proof=verify(True);old=previous()
    old.verify=lambda installed=False:verify(installed)
    old.install=install
    try:return old.run_fixture(output,rustc)
    finally:need(verify(True)==proof,'Successor changed during fixture')
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('verify');v.add_argument('--workflow-installed',action='store_true')
    r=sub.add_parser('run');r.add_argument('--out',type=Path,required=True);r.add_argument('--rustc',required=True)
    args=p.parse_args()
    if args.command=='verify':print(json.dumps(verify(args.workflow_installed),sort_keys=True));return 0
    return run_fixture(args.out,args.rustc)
if __name__=='__main__':sys.exit(main())
