import collect as c
import re,difflib

def item(text,key):
 a=text.index(key);b=text.index('{',a)+1;depth=1
 while depth:depth+=(text[b]=='{')-(text[b]=='}');b+=1
 return text[a:b]
def main():
 records={};methods={}
 for label in ['baseline','candidate']:
  code,attempt,out,err=c.run(['cargo','rustc','--lib','--offline','--locked','--all-features','--','-Zunpretty=expanded'],tree=c.HERE/label,env_extra={'RUSTC_BOOTSTRAP':'1'},label='expanded-'+label)
  assert code==0
  body=item(out.decode(),'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',body,re.M)
  assert len(names)==39 and len(set(names))==39
  methods[label]={n:item(body,'fn '+n+'(') for n in names}
  records[label]={'attempt':str(attempt.relative_to(c.HERE)),'methods':{n:c.sha(b.encode()) for n,b in methods[label].items()}}
 diff=''.join(difflib.unified_diff(methods['baseline']['run'].splitlines(True),methods['candidate']['run'].splitlines(True)))
 c.save(c.HERE/'frozen-run.diff',diff.encode())
 c.save(c.HERE/'frozen-identity.json',records)
 assert methods['baseline']==methods['candidate'],[n for n in methods['baseline'] if methods['baseline'][n]!=methods['candidate'][n]]
 print('Frozen 39 expanded methods exact')
if __name__=='__main__':main()
