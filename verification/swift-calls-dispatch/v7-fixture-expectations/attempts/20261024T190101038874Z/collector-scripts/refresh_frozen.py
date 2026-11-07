"""Refresh candidate expansion; preserve exact independently selected baseline evidence."""
import collect as c
from frozen_identity import item
import re
old=c.read_json(c.HERE.parent/'frozen-identity.json')
code,attempt,out,err=c.run(['cargo','rustc','--lib','--offline','--locked','--all-features','--','-Zunpretty=expanded'],env_extra={'RUSTC_BOOTSTRAP':'1'},label='v6-expanded-candidate')
assert code==0
body=item(out.decode(),'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',body,re.M)
assert len(names)==len(set(names))==39
methods={n:c.sha(item(body,'fn '+n+'(').encode())for n in names}
assert methods==old['baseline']['methods']==old['candidate']['methods']
c.save(c.HERE/'frozen-identity.json',{'baseline':old['baseline'],'candidate':{'attempt':str(attempt.relative_to(c.HERE)),'methods':methods}})
c.save(c.HERE/'frozen-run.diff',b'')
print('V6 candidate39methods exact against selected unchanged baseline')
