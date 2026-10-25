from pathlib import Path
import json,hashlib,tarfile,difflib,os
ROOT=Path(__file__).resolve().parents[2]; P=Path(__file__).resolve().parent; S=P/'.scratch'
manifest=json.loads((P/'baseline-source-manifest.json').read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def replace(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a));return s.replace(a,b)
def prepare():
 assert len(manifest)==132
 assert all(sha((ROOT/'vm'/n).read_bytes())==h for n,h in manifest.items())
 S.mkdir(exist_ok=False)
 ownership={}
 for owner in ['baseline','candidate','build-baseline','build-candidate','tmp-baseline','tmp-candidate']:
  d=S/owner;d.mkdir();st=d.stat();ownership[owner]={'dev':st.st_dev,'ino':st.st_ino}
 for side in ['baseline','candidate']:
  for n in manifest:
   d=S/side/n;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes((ROOT/'vm'/n).read_bytes())
 (P/'scratch-ownership.json').write_text(json.dumps(ownership,indent=2)+'\n')
 n='src/experimental/cache/borrowed.rs';f=S/'candidate'/n;s=f.read_text()
 s=replace(s,"    type Scratch<'a>;","    type Scratch<'a>;\n    #[cfg(test)]\n    fn ordered_diagnostic(_: &mut Self::Meter<'_, '_>, _: [u64;11]) {}")
 s=replace(s,'    fn release_pin(&mut self) -> Result<(), F>;','    fn release_pin(&mut self) -> Result<(), F>;\n    #[cfg(test)]\n    fn ordered_release(&mut self, _: [u64;11]) {}')
 s=replace(s,'    parts.pins[pin.slot()] = PinRecord::default();\n    Ok(())','''    parts.pins[pin.slot()] = PinRecord::default();
    #[cfg(test)] {
        let entry=slot.entry().expect("checked entry");
        operation.ordered_release([12,entry.function as u64,entry.body_offset as u64,u64::MAX,entry.type_index as u64,record.entry as u64,pin.slot() as u64,pin.nonce(),entry.bytes as u64,0,slot.pins() as u64]);
    }
    Ok(())''')
 s=replace(s,'    let hit = M::resident_lookup(parts.slots, &mut parts.scratch, function, meter)?;','''    let hit = M::resident_lookup(parts.slots, &mut parts.scratch, function, meter)?;
    #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(2,defined,hit.map_or(u64::MAX,|n|n as u64),u64::MAX,0,u64::from(hit.is_some()),0,0));''')
 s=replace(s,'        meter.step(CacheStep::Planning);','''        #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(5,defined,u64::MAX,u64::MAX,0,bytes as u64,base as u64,capacity as u64));
        meter.step(CacheStep::Planning);''')
 s=replace(s,'                M::resident_remove(parts.slots, &mut parts.scratch, index, meter)?;','''                #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(6,defined,index as u64,u64::MAX,0,bytes as u64,0,0));
                M::resident_remove(parts.slots, &mut parts.scratch, index, meter)?;''')
 s=replace(s,'                let old = parts.slots[index].take().expect("planned entry");','''                let old = parts.slots[index].take().expect("planned entry");
                #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(7,defined,index as u64,u64::MAX,0,bytes as u64,0,0));''')
 s=replace(s,'                meter.usage_mut().evicted(bytes);','''                meter.usage_mut().evicted(bytes);
                #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(8,defined,index as u64,u64::MAX,0,bytes as u64,0,0));''')
 s=replace(s,'        let decoded = M::build(parts.snapshot, defined, counts, &mut parts.scratch, meter);','''        #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(9,defined,u64::MAX,u64::MAX,0,bytes as u64,0,0));
        let decoded = M::build(parts.snapshot, defined, counts, &mut parts.scratch, meter);''')
 s=replace(s,'        meter.step(CacheStep::Publication);','''        #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(10,defined,u64::MAX,u64::MAX,0,bytes as u64,0,0));
        meter.step(CacheStep::Publication);''')
 s=replace(s,'    *parts.next_nonce = nonce;\n    Ok(pin)','''    *parts.next_nonce = nonce;
    #[cfg(test)] M::ordered_diagnostic(meter,ordered_event(11,defined,index as u64,pin_slot as u64,pin.nonce(),u64::from(hit.is_none()),slot.entry().expect("resident entry").bytes as u64,slot.pins() as u64));
    Ok(pin)''')
 s+='''\n#[cfg(test)]
pub(crate) fn ordered_event(kind:u64,body:FunctionSpanView<'_>,slot:u64,pin_slot:u64,nonce:u64,a:u64,b:u64,c:u64)->[u64;11]{
[kind,body.absolute_index as u64,body.body_offset as u64,body.body.len() as u64,body.type_index as u64,slot,pin_slot,nonce,a,b,c]
}\n'''
 f.write_text(s)
 f=S/'candidate/src/experimental_swift_reactor/control.rs';s=f.read_text();s+='''\n#[cfg(test)]
impl RuntimeControl {
    pub(crate) fn ordered_coordinates(&self)->(u64,u64){(self.cache_work,self.instructions)}
}\n''';f.write_text(s)
 f=S/'candidate/src/experimental_swift_reactor/cache.rs';s=f.read_text()
 s=replace(s,'impl ReleaseControl<SwiftRunFailure> for CacheControl<\'_> {','''impl ReleaseControl<SwiftRunFailure> for CacheControl<'_> {
    #[cfg(test)]
    fn ordered_release(&mut self,event:[u64;11]){super::cache_tests::ordered_observer::observe(event,self.control.ordered_coordinates());}''')
 s=replace(s,'        self.control.check_header(cache)?;\n        pin::<SwiftMode>(','''        #[cfg(test)] super::cache_tests::ordered_observer::acquire(function,self.control.control.ordered_coordinates());
        let result=(|| {
        self.control.check_header(cache)?;
        pin::<SwiftMode>(''')
 s=replace(s,'            &mut self.control,\n        )\n    }\n    pub(crate) fn complete<T>','''            &mut self.control,
        )})();
        #[cfg(test)] if let Err(ref failure)=result {super::cache_tests::ordered_observer::failure(failure,false);}
        result
    }
    pub(crate) fn complete<T>''')
 s=replace(s,'impl CacheMode for SwiftMode {','''impl CacheMode for SwiftMode {
    #[cfg(test)]
    fn ordered_diagnostic(meter:&mut SwiftMeter<'_, '_>,event:[u64;11]){super::cache_tests::ordered_observer::observe(event,meter.operation.control.ordered_coordinates());}''')
 s=replace(s,'        let policy = policy(snapshot, body, meter)?;\n        if scratch.plans.len()','''        #[cfg(test)] Self::ordered_diagnostic(meter,ordered_event(3,body,u64::MAX,u64::MAX,0,0,0,(body.absolute_index&511) as u64));
        let policy = policy(snapshot, body, meter)?;
        if scratch.plans.len()''')
 s=replace(s,'        if let Some(plan) = &scratch.plans[index] {','''        #[cfg(test)] let mut ordered_prior=u64::MAX;
        if let Some(plan) = &scratch.plans[index] {''')
 s=replace(s,'            meter.work(1)?; // actual function identity probe','''            meter.work(1)?; // actual function identity probe
            #[cfg(test)] {ordered_prior=plan.function as u64;}''')
 s=replace(s,'                return Ok(plan.counts);','''                #[cfg(test)] Self::ordered_diagnostic(meter,ordered_event(4,body,u64::MAX,u64::MAX,0,2,u64::MAX,index as u64));
                return Ok(plan.counts);''')
 s=replace(s,'        Ok(counts)\n    }\n    fn build(','        #[cfg(test)] Self::ordered_diagnostic(meter,ordered_event(4,body,u64::MAX,u64::MAX,0,u64::from(ordered_prior!=u64::MAX),ordered_prior,index as u64));\n        Ok(counts)\n    }\n    fn build(')
 f.write_text(s)
 f=S/'candidate/src/experimental_swift_reactor/cache_tests.rs'
 s=f.read_text();s+='\nmod ordered_wire {\n'+(P/'writer.rs').read_text()+'\n}\n'+(P/'observer.rs').read_text();f.write_text(s)
 for side in ['baseline','candidate']:
  files={n:sha((S/side/n).read_bytes()) for n in manifest};(P/(side+'-manifest.json')).write_text(json.dumps(files,sort_keys=True,indent=2)+'\n')
  with tarfile.open(P/(side+'-source.tar.gz'),'w:gz') as t:
   for n in manifest:t.add(S/side/n,arcname=n,recursive=False)
 patches=[]
 for n in manifest:
  a=(S/'baseline'/n).read_bytes();b=(S/'candidate'/n).read_bytes()
  if a!=b:patches.extend(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
 (P/'candidate.patch').write_text(''.join(patches))
 assert sum((S/'baseline'/n).read_bytes()!=(S/'candidate'/n).read_bytes() for n in manifest)==4
 print('prepared complete132 baseline/candidate; copied delta4 files')
if __name__=='__main__':prepare()
