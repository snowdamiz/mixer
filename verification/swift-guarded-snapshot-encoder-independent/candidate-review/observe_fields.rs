// Independent actual proof observation, appended only to the owned review copy.
// No encoder helper, record_word, mapping, inventory or serialized bytes used.
#[cfg(any(test,mixer_snapshot_encoder_host))]
pub(crate) fn independent_snapshot_fields(initial:&crate::experimental_swift_reactor::InitialProfileBorrowV1<'_>)->String {
 let p=initial.snapshot_proof_v2();let m=&p.metadata;let u=&p.usage;let o=&p.observations;
 let array=|v:&[u64]|format!("{:?}",v);
 let pair=|v:Option<u32>|match v{None=>[0u64,0],Some(n)=>[1,n as u64]};
 let mut rows:Vec<String>=Vec::new();
 let mut part=Vec::new();for i in 0..m.signatures.len(){let v=m.signatures.get(i).unwrap();part.push(format!("[{}, {}, \"{:?}\"]",v.first,v.count,v.result));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.parameters.len(){part.push(format!("[\"{:?}\"]",m.parameters.get(i).unwrap()));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.imports.len(){let v=m.imports.get(i).unwrap();part.push(array(&[v.module.offset as u64,v.module.bytes as u64,v.name.offset as u64,v.name.bytes as u64,v.type_index as u64]));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.functions.len(){let v=m.functions.get(i).unwrap();part.push(array(&[v.body.offset as u64,v.body.bytes as u64,v.type_index as u64]));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.globals.len(){let v=m.globals.get(i).unwrap();part.push(format!("[\"{:?}\",{},{},{}]",v.ty,u8::from(v.mutable),v.initializer.offset,v.initializer.bytes));}rows.push(format!("[{}]",part.join(",")));
 let mut part=Vec::new();for i in 0..m.exports.len(){let v=m.exports.get(i).unwrap();part.push(array(&[v.name.offset as u64,v.name.bytes as u64,v.kind as u64,v.index as u64]));}rows.push(format!("[{}]",part.join(",")));
 for buffer in [&m.data,&m.elements]{let mut part=Vec::new();for i in 0..buffer.len(){let v=buffer.get(i).unwrap();part.push(array(&[v.payload.offset as u64,v.payload.bytes as u64,v.destination as u64,v.count as u64]));}rows.push(format!("[{}]",part.join(",")));}
 let inventories=[m.signatures.independent_inventory(),m.parameters.independent_inventory(),m.imports.independent_inventory(),m.functions.independent_inventory(),m.globals.independent_inventory(),m.exports.independent_inventory(),m.data.independent_inventory(),m.elements.independent_inventory()];
 let inventories:Vec<String>=inventories.iter().map(|v|format!("[{},{},{},{},\"{:?}\"]",v.0,v.1,v.2,v.3,v.4)).collect();
 let usage=array(&[u.input_visible_bytes as u64,u.source_bytes as u64,u.metadata_reserved as u64,u.scratch_reserved as u64,u.metadata_peak_reserved as u64,u.scratch_peak_reserved as u64,u.total_peak_reserved as u64,u.work_used,u.elapsed_micros,u.deadline_ms]);
 let mm=pair(o.memory_declared_maximum);let tm=pair(o.table_declared_maximum);
 let observations=array(&[o.types as u64,o.type_parameters as u64,o.imported_functions as u64,o.defined_functions as u64,o.validated_bodies as u64,o.instructions as u64,o.globals as u64,o.exports as u64,o.data_segments as u64,o.element_segments as u64,o.max_parameters_plus_locals as u64,o.max_operand_values as u64,o.max_control_depth as u64,o.memory_minimum as u64,mm[0],mm[1],o.memory_host_maximum as u64,o.table_minimum as u64,tm[0],tm[1]]);
 let memory=m.memory.unwrap();let table=m.table.unwrap();let mm=pair(m.declarations.memory_maximum);let tm=pair(m.declarations.table_maximum);
 let metadata=array(&[1,memory.0 as u64,memory.1 as u64,1,table.0 as u64,table.1 as u64,mm[0],mm[1],tm[0],tm[1],m.declarations.memory_offset as u64,m.declarations.table_offset as u64,m.instructions as u64]);
 let resolved:Vec<String>=p.imports.iter().map(|v|format!("\"{:?}\"",v)).collect();
 format!("\"source\":\"{}\",\"sections\":[{}],\"inventories\":[{}],\"instructions\":{},\"usage\":{},\"observations\":{},\"metadata\":{},\"resolved_names\":[{}],\"policy\":\"{}\"",p.source.iter().map(|v|format!("{v:02x}")).collect::<String>(),rows.join(","),inventories.join(","),m.instructions,usage,observations,metadata,resolved.join(","),p.policy_identity())
}
