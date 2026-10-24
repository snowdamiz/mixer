#!/usr/bin/env python3
"""Copy selected Mixer inputs; never enroll a deployment observation."""
import ast, hashlib, json, pathlib, shutil
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
UP=ROOT/'verification/hosted-catalog-wildcard-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
bindings=[]
for source,target in [
 ('candidate/inspector.py','inputs/oracle/inspector.py'),
 ('candidate/raw_validation.py','inputs/oracle/raw_validation.py'),
 ('candidate/enforcement.sql','inputs/oracle/enforcement.sql'),
 ('candidate/frozen/catalog.sql','inputs/oracle/frozen/catalog.sql'),
 ('candidate/enforcement.sql','component/priv/enforcement.sql'),
 ('candidate/frozen/catalog.sql','component/priv/catalog.sql'),
 ('candidate/frozen/schema.sql','inputs/schema.sql'),
 ('selected-expected.json','component/priv/selected-expected.json'),
 ('receipt.json','inputs/upstream-receipt.json'),
 ('source-manifest.json','inputs/upstream-source-manifest.json')]:
 p=UP/source; b=p.read_bytes();t=HERE/target;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 bindings.append({'path':str(p.relative_to(ROOT)),'copy':target,'sha256':sha(b),'bytes':len(b)})
for source,target in [
 ('verification/hosted-catalog-wildcard-review/receipt.json','inputs/independent-review-receipt.json'),
 ('docs/hosted-authority-schema-contract.md','inputs/hosted-authority-schema-contract.md'),
 ('AGENTS.md','inputs/AGENTS.md'),('hosted/mix.exs','inputs/hosted-mix.exs'),
 ('hosted/mix.lock','inputs/hosted-mix.lock'),('THIRD_PARTY.yml','inputs/THIRD_PARTY.yml')]:
 p=ROOT/source;b=p.read_bytes();t=HERE/target;t.write_bytes(b)
 bindings.append({'path':source,'copy':target,'sha256':sha(b),'bytes':len(b)})
assert sha((HERE/'component/priv/selected-expected.json').read_bytes())=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
assert sha((HERE/'inputs/upstream-receipt.json').read_bytes())=='cc82538ba0709c831cf2b0579109a93cd419a972318fb84576e8ec03071d295f'
assert sha((HERE/'inputs/independent-review-receipt.json').read_bytes())=='29b1c85a284af222309930657bf05c39d00294b3ec4a4cb9a6a12343ee7d9e71'
# Translate the accepted descriptor constants, not the Python implementation.
tree=ast.parse((HERE/'inputs/oracle/raw_validation.py').read_text());namespace={}
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GROUPS' for t in node.targets):namespace['groups']=ast.literal_eval(node.value)
 if isinstance(node,ast.FunctionDef) and node.name=='validate_legacy':
  scope={}
  for statement in node.body:
   if isinstance(statement,ast.Assign):
    value=eval(compile(ast.Expression(statement.value),'accepted-domains','eval'),{'__builtins__':{}},scope)
    for target in statement.targets:scope[target.id]=value
  namespace['legacy']=scope['legacy']
(HERE/'component/priv/domains.json').write_text(json.dumps(namespace,sort_keys=True,indent=2)+'\n')
(HERE/'input-manifest.json').write_text(json.dumps(bindings,indent=2)+'\n')
print(json.dumps({'copied_bindings':len(bindings),'selected_sha256':sha((HERE/'component/priv/selected-expected.json').read_bytes())}))
