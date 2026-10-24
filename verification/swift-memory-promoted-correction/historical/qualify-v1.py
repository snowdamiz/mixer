#!/usr/bin/env python3
"""Bounded correction qualification; all builds use archived private sources."""
import subprocess,json
from run import run,SCRATCH,HERE,b

def step(script,*args):
 p=subprocess.run(['python3','-B',str(HERE/script),*args]);assert p.returncode==0,(script,p.returncode)

for name,argv in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('rustfmt',['rustfmt','--version']),('python',['python3','--version']),('host',['uname','-a']),('git',['git','rev-parse','HEAD'])]:
 assert run('tool-'+name,argv).returncode==0
assert run('collector-regression',['python3','-B',str(HERE/'collector_regression.py')],SCRATCH/'candidate/vm').returncode==0
step('matrix.py','corrected')
step('regressions.py','corrected')
step('canonical_probe.py')
step('metadata.py','binary')
step('frozen_identity.py','corrected')
for feature,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  assert run('check-'+feature+('-release' if release else '-debug'),['cargo','check','--lib','--locked','--offline',*flags,*(['--release'] if release else [])],SCRATCH/'candidate/vm').returncode==0
print('bounded correction qualification completed',flush=True)
