import collect as c
import json
root=c.ROOT/'verification/swift-calls-dispatch-root-review';proposal=c.HERE/'compiler-constant-exception-positions-v3.json';selected=root/'compiler-constant-exception-positions-v3.json';assert c.sha(proposal.read_bytes())==c.sha(selected.read_bytes())=='7e6ad2e8a89125dae4350837cf2b55a1e8f0891c90d20bb7d2ffa974cc085965'
assert (root/'compiler-constant-exception-amendment-v3.json').exists()
p=c.HERE/'candidate/src/experimental_swift_reactor/call_dispatch.rs';s=p.read_text();a=s.index('// CALL_DISPATCH_ACCOUNTING_BEGIN');b=s.index('// CALL_DISPATCH_ACCOUNTING_END',a)+len('// CALL_DISPATCH_ACCOUNTING_END');p.write_text(s[:a]+'// CALL_DISPATCH_ACCOUNTING_BEGIN\n'+(c.HERE/'positive-positions-v3.rs').read_text()+'// CALL_DISPATCH_ACCOUNTING_END'+s[b:])
p=c.HERE/'candidate/src/experimental/execution/borrowed.rs';s=p.read_text();a=s.index('// CALL_DISPATCH_KIND_ACCOUNTING_BEGIN');b=s.index('// CALL_DISPATCH_KIND_ACCOUNTING_END',a)+len('// CALL_DISPATCH_KIND_ACCOUNTING_END');p.write_text(s[:a]+'// CALL_DISPATCH_KIND_ACCOUNTING_BEGIN\n'+(c.HERE/'kind-positions-v3.rs').read_text()+'// CALL_DISPATCH_KIND_ACCOUNTING_END'+s[b:])
