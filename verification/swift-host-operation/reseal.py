#!/usr/bin/env python3
"""Seal the final offline verifier after strengthening optional full-live-closure checking."""
import collect as c
import verify
p=c.HERE
c.command('qualified-full-live-closure-verifier',['python3','-B',str(p/'verify.py'),'--preseal','--live-baseline'])
c.save('preseal-verification.json',verify.check(preseal=True,live=True))
bindings={str(x.relative_to(p)):c.sha(x.read_bytes())for x in sorted(p.rglob('*'))if x.is_file()and x!=p/'seal.json'}
c.save('seal.json',dict(schema=1,exactExcludedPath='seal.json',files=bindings,documentation='docs/swift-host-operation-implementation.md',documentationSHA256=c.sha((c.ROOT/'docs/swift-host-operation-implementation.md').read_bytes()),boundFiles=len(bindings),completedUTC=c.now()))
print(verify.check(live=True))
