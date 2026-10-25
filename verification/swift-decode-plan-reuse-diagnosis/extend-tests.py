from pathlib import Path
H=Path(__file__).resolve().parent
for lane in ('baseline','source'):
 p=H/lane/'src/experimental_swift_reactor/cache_tests.rs'
 s=p.read_text()
 # Preserve first-attempt sources in command snapshot; final common test has two truthful workloads.
 a='''    let bytes = fixture(0, &body(1, &[0x41, 7, 0x21, 0, 0x20, 0, 0x1a, 0x0b]), 600);'''
 b='''    for wide in [false,true] {
    let helper=body(1,&[0x41,7,0x21,0,0x20,0,0x1a,0x0b]);
    let bytes = if wide {plan_reuse_wide_fixture(&helper,600)} else {fixture(0,&helper,600)};'''
 assert s.count(a)==1;s=s.replace(a,b)
 s=s.replace('"PLAN_IR sweep={sweep}', '"PLAN_IR wide={wide} sweep={sweep}')
 s=s.replace('"PLAN_COST fixed=', '"PLAN_COST wide={wide} fixed=')
 s=s.replace('"PLAN_LRU slots=', '"PLAN_LRU wide={wide} slots=')
 marker='''    finish(cache,c);
}
'''
 ix=s.index(marker,s.index('fn plan_reuse_observation'))
 s=s[:ix]+s[ix:].replace(marker,'''    finish(cache,c);
    }
}
''',1)
 s+='''
// Test-only section builder: every body is admitted by the real complete validator.
fn plan_reuse_wide_fixture(helper:&[u8],definitions:usize) -> Vec<u8> {
    let mut module=fixture(0,helper,definitions);
    let mut cursor=8;
    loop {
        let start=cursor;let id=module[cursor];cursor+=1;
        let mut size=0usize;let mut shift=0;
        loop {let b=module[cursor];cursor+=1;size|=((b&127) as usize)<<shift;if b&128==0 {break}shift+=7;}
        if id==10 {
            module.truncate(start);
            let mut code=vec![];uint(definitions as u32,&mut code);
            for index in 0..definitions {
                let b=if index==28 {&[0,0x41,0,0x0b][..]} else {helper};
                uint(b.len() as u32,&mut code);code.extend_from_slice(b);
            }
            section(10,&code,&mut module);return module;
        }
        cursor+=size;
    }
}
'''
 if lane=='source':
  s=s.replace('assert_eq!(c.usage(None).reservations.live_tickets,7);','assert_eq!(c.usage(None).reservations.live_tickets,9);')
  s=s.replace('let (mut c,mut cache)=plan_reuse_seed(&bytes,budget);\n    let (mut other','let (c,mut cache)=plan_reuse_seed(&bytes,budget);\n    let (mut other')
 p.write_text(s)
p=H/'source/src/experimental_swift_reactor/cache.rs';s=p.read_text();m='    pub fn count(cache: &SwiftFunctionCache) -> usize'
pos=s.index(m,s.index('pub(super) mod plan_inspection'))
s=s[:pos]+'''    pub fn tail_usage(tail:&CacheCleanupTail<'_>) -> SwiftRunUsage {tail.control.usage(None)}
    pub fn summary(cache:&SwiftFunctionCache,f:u32) -> Option<(u32,usize,usize,u32,decode::Counts)> {
        cache.plans[f as usize & (PLAN_CAPACITY-1)].map(|p|(p.function,p.body_offset,p.body_len,p.type_index,p.counts))
    }
'''+s[pos:];p.write_text(s)
