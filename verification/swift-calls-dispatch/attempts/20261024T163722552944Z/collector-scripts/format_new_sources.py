import collect as c
for name in ['call_dispatch.rs','call_dispatch_tests.rs']:
 rel='src/experimental_swift_reactor/'+name
 code,attempt,out,err=c.run(['rustfmt','--edition','2021','--config','skip_children=true','--emit','stdout',rel],label='format-new-'+name)
 assert code==0
 (c.HERE/'candidate'/rel).write_bytes(out)
