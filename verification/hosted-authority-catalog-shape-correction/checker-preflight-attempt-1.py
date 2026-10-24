import pathlib,json,gzip,sys
p=pathlib.Path('verification/hosted-authority-catalog-shape-correction');sys.path.insert(0,str(p/'candidate'));from inspector import validate,normalize,canonical
r=p/'attempt-1';expected=json.loads((p/'selected-expected.json').read_bytes())
def load(path):
 path=pathlib.Path(path);return json.loads(path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes()))
for sub in ['corrected','independent']:
 counts={True:0,False:0};summ=load(r/sub/'summary.json')
 for e in summ['captures']:
  ob=load(r/sub/e.get('file',e.get('path')));raw=ob['raw']
  try:validate(raw,expected);accept=True
  except ValueError:accept=False
  counts[accept]+=1
  try:assert canonical(normalize(raw))==canonical(ob['normalized'])
  except Exception as e:print('NORMALIZATION ERROR',sub,e);raise
 print(sub,counts)
