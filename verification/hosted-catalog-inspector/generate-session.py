#!/usr/bin/env python3
"""Bind a semantic-only qualification delta from the exact accepted SESSION."""
import ast,difflib,hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
tree=ast.parse((HERE/'inputs/oracle/inspector.py').read_text())
original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SESSION' for t in n.targets))
qualified=original
for name in ['jsonb_build_object','current_setting','current_database']:
 qualified=qualified.replace(name+'(','pg_catalog.'+name+'(')
assert qualified.replace('pg_catalog.','')==original
for name,value in [('session-original.sql',original),('session.sql',qualified)]: (HERE/'component/priv'/name).write_text(value+'\n')
(HERE/'session-qualification.diff').write_text(''.join(difflib.unified_diff((original+'\n').splitlines(True),(qualified+'\n').splitlines(True),fromfile='accepted-original-SESSION',tofile='pg_catalog-qualified-SESSION')))
result={'schema':1,'only_builtin_function_qualification':True,'original_sha256':hashlib.sha256((original+'\n').encode()).hexdigest(),'qualified_sha256':hashlib.sha256((qualified+'\n').encode()).hexdigest(),'selected_fields_unchanged':True}
(HERE/'session-selection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
