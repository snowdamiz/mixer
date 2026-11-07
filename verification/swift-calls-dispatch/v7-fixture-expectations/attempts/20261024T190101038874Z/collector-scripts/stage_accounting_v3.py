import collect as c
import json,runpy
code,*_=c.run(['python3','-B',str(c.HERE/'inventory_v3.py')],label='full-compiler-v3-accounting-generation');assert code==0
summary=json.loads((c.HERE/'accounting-v3-summary.json').read_text());assert not any('pending'in k for k in summary['methods'])
assert (c.ROOT/'verification/swift-calls-dispatch-root-review/compiler-unstable-global-amendment-v3.json').exists()
runpy.run_path(str(c.HERE/'install_accounting_v3.py'))
runpy.run_path(str(c.HERE/'format_new_sources.py'))
code,*_=c.run(['cargo','rustc','--lib','--locked','--offline','--all-features','--','--test','--emit=mir'],label='stable-complete-v3-unit-compile');raise SystemExit(code)
