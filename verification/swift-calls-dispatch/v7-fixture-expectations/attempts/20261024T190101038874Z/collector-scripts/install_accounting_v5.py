import collect as c
import json,difflib
before=c.manifest(c.HERE/'candidate')
s=json.loads((c.HERE/'accounting-v5-summary.json').read_text());c.save(c.HERE/'preinstall-v5-query-bindings.json',s['queryBindings'])
changes={}
for rel,begin,end,generated in [
 ('src/experimental_swift_reactor/call_dispatch.rs','// CALL_DISPATCH_ACCOUNTING_BEGIN','// CALL_DISPATCH_ACCOUNTING_END','positive-positions-v5.rs'),
 ('src/experimental/execution/borrowed.rs','// CALL_DISPATCH_KIND_ACCOUNTING_BEGIN','// CALL_DISPATCH_KIND_ACCOUNTING_END','kind-positions-v5.rs')]:
 p=c.HERE/'candidate'/rel;old=p.read_text();a=old.index(begin);b=old.index(end,a)+len(end);new=old[:a]+begin+'\n'+(c.HERE/generated).read_text()+end+old[b:];p.write_text(new)
 changes[rel]={'before':c.sha(old.encode()),'after':c.sha(new.encode()),'generated':generated,'generatedSHA256':c.sha((c.HERE/generated).read_bytes())}
 c.save(c.HERE/('installed-v5-'+p.name+'.diff'),''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))).encode())
c.save(c.HERE/'install-accounting-v5.json',{'argv':['python3',str(c.HERE/'install_accounting_v5.py')],'beforeSourceClosure':c.sha(c.enc(before)),'afterSourceClosure':c.sha(c.enc(c.manifest(c.HERE/'candidate'))),'changes':changes,'qualifiedRuntime':False})
