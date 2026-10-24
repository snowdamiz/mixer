import collect as c
import re,json
rows=json.loads((c.HERE/'inventory-schema.json').read_text());result={}
for r in rows:
 ty=r['type']
 if re.search(r'alloc::|std::sys::|thread::local_impl|niche_types|::private::|::execution::Kind|\bAtomic<bool>|^!$|\{[^}]+\}$',ty):
  category='reference' if ty.startswith('&')else'raw-pointer'if ty.startswith('*')else'nonowning-nonnull'if ty.startswith('std::ptr::NonNull')else'FnDef'if re.search(r'\{[^}]+\}$',ty)else'owning-value'
  group=result.setdefault(ty,{'type':ty,'category':category,'positions':[],'configs':set(),'functions':set()})
  group['positions'].append({'field':r['field'],'position':r['position'],'function':r.get('function'),'header':r.get('header'),'mirType':r.get('mirType'),'kind':r['kind'],'config':r['config']});group['configs'].add(r['config']);group['functions'].add(r.get('function'))
for g in result.values():g['configs']=sorted(g['configs']);g['functions']=sorted(g['functions']);g['positionCount']=len(g['positions'])
c.save(c.HERE/'unnameable-positions.json',list(result.values()));print([(g['type'],g['category'],g['positionCount']) for g in result.values()])
