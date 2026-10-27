import sys
import run_review as r
kind,mode=sys.argv[1:]
for fixture,wasi in [('baseline','none'),('segments','none'),('segments','some'),('segments','zero')]:
 directory=r.HERE/'runs'/f'{kind}-{mode}-{fixture}-{wasi}'
 if not (directory/'comparison.json').exists():r.selected(kind,mode,fixture,wasi)
if not (r.HERE/'commands'/f'{kind}-{mode}-ordinary').exists():r.ordinary(kind,mode)
if not (r.HERE/'layouts'/f'{kind}-{mode}.json').exists():r.layouts(kind,mode)
