import collect as c
for name in ['call_dispatch.rs','call_dispatch_tests.rs']:
 rel='src/experimental_swift_reactor/'+name
 code,attempt,out,err=c.run(['rustfmt','--edition','2021','--config','skip_children=true','--emit','stdout',rel],label='format-new-'+name)
 assert code==0
 prefix=(str(c.HERE/'candidate'/rel)+':\n\n').encode();assert out.startswith(prefix)
 c.save(attempt/'normalization.json',{'operation':'remove only rustfmt stdout filename display prefix','prefix':prefix.decode(),'rawSHA256':c.sha(out),'sourceSHA256':c.sha(out[len(prefix):])})
 (c.HERE/'candidate'/rel).write_bytes(out[len(prefix):])
