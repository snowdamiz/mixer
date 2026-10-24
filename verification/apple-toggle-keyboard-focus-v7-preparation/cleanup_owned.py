#!/usr/bin/env python3
"""Remove only exact scratch paths created under this unsealed preparation."""
import datetime
import pathlib
import shutil
import run as r
b=r.BASE
r.require(not (b/'packet-seal.json').exists(),'Sealed cleanup receipt is immutable')
manifest=r.read(b/'build-products-manifest.json');before=r.h.tree(r.h.PRODUCTS)
r.require(before==manifest['products'],'Runner products changed before scratch cleanup')
paths=['build/Build/Intermediates.noindex','build/CompilationCache.noindex','build/Index.noindex','build/Logs','build/ModuleCache.noindex','build/SDKStatCaches.noindex','build/info.plist','.scratch']
removed=[]
for name in paths:
 p=b/name
 r.require(p.resolve()==p and p.is_relative_to(b),'Only exact canonical owned scratch')
 if not p.exists():continue
 if name=='.scratch':r.require(p.is_dir() and not list(p.iterdir()),'Host fixture scratch must already be empty')
 size=sum(x.stat().st_size for x in p.rglob('*') if x.is_file()) if p.is_dir() else p.stat().st_size
 if p.is_dir():shutil.rmtree(p)
 else:p.unlink()
 removed.append(dict(path=str(p.relative_to(r.ROOT)),bytes=size,absentAfter=not p.exists()))
r.require(r.h.tree(r.h.PRODUCTS)==before,'Scratch cleanup changed runner products')
r.h.write(b/'cleanup.json',dict(schema='mixer.apple-toggle.keyboard-v7-owned-build-scratch-cleanup.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),removed=removed,bytesRemoved=sum(v['bytes'] for v in removed),runnerProductsPreserved=True,nativeInstanceCreated=False,nativeInstanceQueried=False,nativeCleanupRequired=False,otherProjectProcessesOrDataTouched=False,scope='Exact owned host/build scratch only; product tree and archive retained for independent review and separately selected diagnostic'))
print('owned build scratch removed; runner products retained')
