#!/usr/bin/env python3
import pathlib,sys
out=pathlib.Path(__file__).resolve().parent
p=out/'.scratch/candidate/src/experimental_swift_reactor/cache.rs'
probe=(out/'layout-probe.rs').read_text()
if sys.argv[1]=='install':
    text=p.read_text();assert 'mod count_plan_layout_probe' not in text;p.write_text(text+'\n'+probe)
elif sys.argv[1]=='remove':
    text=p.read_text();assert text.endswith('\n'+probe);p.write_text(text[:-len('\n'+probe)])
else:raise SystemExit('unknown action')
