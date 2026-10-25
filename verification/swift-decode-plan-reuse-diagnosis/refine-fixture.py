from pathlib import Path
H=Path(__file__).resolve().parent
for lane in ('baseline','source'):
 p=H/lane/'src/experimental_swift_reactor/cache_tests.rs';s=p.read_text()
 a='''            for index in 0..definitions {
                let b=if index==28 {&[0,0x41,0,0x0b][..]} else {helper};'''
 b='''            let mut rich=vec![0,0x01];rich.extend(std::iter::repeat_n(0x01,511));rich.push(0x0b);
            for index in 0..definitions {
                let b=if index==28 {&[0,0x41,0,0x0b][..]} else if index==0 {helper} else {&rich};'''
 assert a in s;s=s.replace(a,b);p.write_text(s)
