#!/usr/bin/env python3
"""Measure exact closed-composition binding checks; never dispatch native work."""
import importlib, json, pathlib, shutil, statistics, sys, tempfile, time
HERE=pathlib.Path(__file__).resolve().parent
REPO=HERE.parents[2]
scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-settings-bindings-',dir='/tmp')).resolve()
report={'scope':'host-only import and binding checks; no native dispatch','scratch':str(scratch)}
try:
 selected=scratch/'selected';shutil.copytree(HERE/'baseline-runtime',selected)
 selection=json.loads((REPO/'verification/apple-passive-lifecycle-runtime-preparation/selection-template.json').read_text())
 root=json.loads((HERE.parent/'apple-runtime/root-selection.json').read_text())
 selection.update(repositoryRoot=str(REPO),outputBase=str(scratch/'output'),productsRoot=str(scratch/'unused-products'),trustedRootSelection=root)
 (selected/'runtime-selection.json').write_text(json.dumps(selection))
 sys.path.insert(0,str(selected));m=importlib.import_module('composition')
 runs=[]
 for _ in range(158):
  start=time.monotonic();m.bindings.check(m.RUNTIME_ROOTS);runs.append(time.monotonic()-start)
 report.update(checks=len(runs),seconds=runs,totalSeconds=sum(runs),medianSeconds=statistics.median(runs),maxSeconds=max(runs),registeredModules=len(m.bindings.registered),selectedFiles=len(m.bindings.files))
finally:
 shutil.rmtree(scratch);report['scratchRemoved']=not scratch.exists();(HERE/'binding-probe.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='seconds'},indent=2))
