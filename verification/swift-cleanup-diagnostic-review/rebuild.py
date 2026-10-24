#!/usr/bin/env python3
"""Fresh deterministic replay; no producer retained executable is executed."""
import gzip, json, re, sys
sys.dont_write_bytecode=True
import collect as c

def mir():
    c.mir('baseline','baseline-mir')
    c.mir('candidate','final-qualified-mir')

def completeness():
    import inventory
    producer=c.ROOT/'verification/swift-cleanup-diagnostic'
    expected=json.loads((producer/'inventory-schema.json').read_text())
    functions=[];observed=[]
    # Independent selector starts with the source-delta contract, then scans all
    # compiler body headers, including bare/unqualified names and constants.
    required={'remove_live_at_with_wasi','primitive_pop','primitive_numeric','control_remove','remove_live_at','finish_inner','host_operation_inner'}
    unit=required|{'diagnostic_before_remove','diagnostic_numeric_before_remove','control_after_value_pop'}
    coverage={}
    for config in ['production','unit']:
        text=gzip.decompress((c.HERE/('final-qualified-mir-'+config+'.mir.gz')).read_bytes()).decode()
        headers=[]
        for line in text.splitlines():
            if line.startswith('fn ') or (line.startswith('const ') and 'promoted[' in line):
                name=line.removeprefix('fn ').removeprefix('const ')
                matched=[]
                for n in unit if config=='unit' else required:
                    if re.search(r'(^|::)'+n+r'(?=\(|::)',name):matched.append(n)
                if matched:headers.append(name[:name.index('(')] if line.startswith('fn ') else name)
        rows,fn,captures=inventory.canonical(config,'final-qualified-mir')
        assert sorted(headers)==sorted(f['function'] for f in fn),(config,headers,fn)
        for name in required if config=='production' else unit:
            assert any(re.search(r'(^|::)'+name+r'(?=$|::)',f['function']) for f in fn),(config,name)
        assert any(f['function']=='primitive_pop' for f in fn)
        assert any(f['function']=='primitive_numeric' for f in fn)
        if config=='unit':assert any(f['function']=='diagnostic_before_remove' for f in fn)
        coverage[config]=headers;observed+=rows;functions+=fn
    stable=lambda r:{k:v for k,v in r.items() if k not in ['ownerClass','mirLine']}
    assert list(map(stable,observed))==list(map(stable,[r for r in expected if r['config']!='source']))
    assert len(expected)==5516 and len(functions)==32
    assert len(set(r['field'] for r in expected))==len(expected)
    for r in expected:
        assert r['position'] in {'source','argument','returned','caller'}
        if r['config']!='source': assert r['rustType'] and r['mirType']
    c.save('independent-selector-completeness.json',dict(positivePositions=len(expected),compilerBodies=len(functions),bodyHeaders=coverage,allUnqualifiedPrimitivesPresent=True,independentHeaderSelectorEqualsDeterministicInventory=True,source=c.digest(c.manifest(c.source('candidate')))))
    c.save('fresh-function-manifest.json',functions)
    print('PASS independent complete selector: 5516 positions, 32 bodies',flush=True)

def layouts():
    import layouts
    layouts.main('qualified')
    import type_layouts
    type_layouts.main()

def validate():
    import validate
    validate.main()
    import audit
    audit.identity()

def runtime():
    import runtime
    rows=[]
    for features in ['swift','all']:
        for profile in ['debug','release']:
            rows.append(runtime.build(features,profile,'independent'))
            c.save('runtime-results.json',rows)
    import frozen
    frozen.main()
    import checks
    checks.main()

if __name__=='__main__':
    {'mir':mir,'completeness':completeness,'layouts':layouts,'validate':validate,'runtime':runtime}[sys.argv[1]]()
