#!/usr/bin/env python3
"""Exact R62 afterimage application for root; before/after are read-only guards."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def identity(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('operation',choices=('before','apply','after'))
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((OUT/'application-map.json').read_bytes())
    rows = manifest['rows']
    stamp = OUT/'applied-by-root.json'
    after = args.operation == 'after'
    expected = 'after' if after else 'before'
    need(len(rows) == 21 and len({r['path'] for r in rows}) == 21,'Application roster differs')
    for row in rows:
        relative = Path(row['path'])
        need(not relative.is_absolute() and '..' not in relative.parts,'Foreign application path')
        need(not relative.as_posix().startswith(('.github/','gates/')) and relative.name not in ('PLAN.md','STATUS.md','work-graph.json','native-resumption.json'),'Root-owned coordination path in application map')
        image = OUT/row['afterimage']
        need(image.is_file() and not image.is_symlink() and identity(image.read_bytes()) == row['after'],'Afterimage differs: '+row['path'])
        if row['before'] is not None:
            original = OUT/'beforeimages'/relative
            need(original.is_file() and not original.is_symlink() and identity(original.read_bytes()) == row['before'],'Beforeimage differs: '+row['path'])
        path = root/relative
        for parent in [path,*path.parents]:
            need(not parent.is_symlink(),'Symlink in application path')
        wanted = row[expected]
        if wanted is None:
            need(not path.exists(),'New target already exists: '+row['path'])
        else:
            need(path.is_file() and identity(path.read_bytes()) == wanted,'Installed '+expected+' differs: '+row['path'])
    spec = importlib.util.spec_from_file_location('r62_application_owner',root/'scripts/ci/check-android-generated-java.py')
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    source = owner.source_inputs(owner.load_profile(root))
    frozen = json.loads((OUT/('source-after.json' if after else 'source-before.json')).read_bytes())
    need(source == frozen and len(source) == 115,'Installed owning source115 roster differs')
    need(owner.source_digest(source) == manifest['sourceAfter' if after else 'sourceBefore'],'Installed owning source digest differs')
    if args.operation == 'apply':
        need(root != Path(json.loads((OUT/'identities.json').read_bytes())['workspace']),'Projection already contains afterimages')
        need(not stamp.exists(),'Application already recorded')
        # Root coordinates the write lease and acceptance. Every guard precedes writes.
        for row in rows:
            path = root/row['path']
            raw = (OUT/row['afterimage']).read_bytes()
            if row['before'] is None:
                with path.open('xb') as stream:
                    stream.write(raw)
            else:
                path.write_bytes(raw)
        stamp.write_text(json.dumps({'root':str(root),'sourceAfter':manifest['sourceAfter'],'paths':len(rows)},indent=2)+'\n')
    print(json.dumps({'operation':args.operation,'paths':len(rows),'sourceCount':115,
        **({'postApplyGuardRequired':True} if args.operation=='apply' else {'sourceSHA256':owner.source_digest(source)})}))

if __name__ == '__main__':
    main()
