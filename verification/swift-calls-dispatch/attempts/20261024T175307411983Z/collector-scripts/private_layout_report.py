import collect as c
import gzip,json,re
rows=json.loads((c.HERE/'private-layout-attempts.json').read_text());data={}
for r in rows:
 a=c.HERE/r['attempt'];text=gzip.decompress((a/'stdout.log.gz').read_bytes()).decode()+gzip.decompress((a/'stderr.log.gz').read_bytes()).decode()
 current=None;types={}
 for line in text.splitlines():
  m=re.fullmatch(r'print-type-size type: `(.+)`: (\d+) bytes, alignment: (\d+) bytes',line)
  if m:current=m[1];types[current]={'bytes':int(m[2]),'alignment':int(m[3]),'detail':[]}
  elif line.startswith('print-type-size ') and current:types[current]['detail'].append(line.removeprefix('print-type-size '))
 data[r['name']]={'attempt':r['attempt'],'types':{name:layout for name,layout in types.items() if any(x in name for x in ['EagerStorage','eager::State','UsizeNoHighBit','execution::Kind','Align8','ArcInner','Atomic<bool>']) or name=='!'}}
c.save(c.HERE/'unnameable-layout-evidence.json',data)
for context,v in data.items():
 print(context)
 for name,value in v['types'].items():print(name,value['bytes'],value['alignment'])
