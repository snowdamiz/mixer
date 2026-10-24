"""Extract the accepted Frozen run/call as static literal orchestration."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
base=(HERE/'baseline/src/experimental/execution/mod.rs').read_text()
borrow=(HERE/'baseline/src/experimental/execution/borrowed.rs').read_text()
def body(name):
 start=base.index('    fn '+name+'(');brace=base.index('{',start);at=brace+1;depth=1
 while depth:depth+=(base[at]=='{')-(base[at]=='}');at+=1
 return start,at,brace,base[brace+1:at-1]
leaves=[]
def leaf(name,args,tokens):
 args=', '.join('$'+x+':ident' for x in args)
 content=tokens.replace('self','$s')
 for arg in [x.split(':')[0][1:] for x in args.split(', ') if x]:
  if arg=='s':continue
  import re
  content=re.sub(r'\b'+arg+r'\b','$'+arg,content)
 leaves.append('    ('+name+' '+args.replace(', ', ', ')+') => {'+content+'\n    };')
# Rather than opaque runtime mode wrappers, leaves expand directly into each
# existing owner. The shared loop/match is the only instruction choreography.
_,_,_,run=body('run');_,_,_,call=body('call')
start=run.index('            let frame =');end=run.index('            self.function =')
fetch=run[start:end];leaf('fetch',['s','instruction','target','frame'],fetch)
run=run[:start]+'            $leaf!(fetch $this, instruction, target, frame);\n'+run[end:]
start=run.index('            self.function =');end=run.index('            let mut finished')
leaf('prefix',['s','instruction','frame'],run[start:end]);run=run[:start]+'            $leaf!(prefix $this, instruction, frame);\n'+run[end:]
# Local/global owner views contain incompatible mutable-error borrowing. Preserve
# the Frozen tokens verbatim; Swift leaves validate and access original arenas.
for name,opening,closing in [
 ('local_get','                Operation::LocalGet(index) => {','                Operation::LocalSet(index)'),
 ('local_set','                Operation::LocalSet(index) | Operation::LocalTee(index) => {','                Operation::GlobalGet(index)'),
 ('global_get','                Operation::GlobalGet(index) => {','                Operation::GlobalSet(index)'),
 ('global_set','                Operation::GlobalSet(index) => {','                Operation::Block {'),
 ('indirect','                Operation::CallIndirect(index) => {','                Operation::MemorySize =>')]:
 a=run.index(opening);b=run.index(closing,a);segment=run[a:b];a0=segment.index('{')+1;z=segment.rfind('}')
 # invocation target explicitly carries all hygienic identifiers.
 args=['s','index']+(['instruction'] if name=='local_set' else [])
 leaf(name,args,segment[a0:z]);inv='$leaf!('+name+' $this, index'+(', instruction' if name=='local_set' else '')+');'
 run=run[:a]+segment[:a0]+'\n                    '+inv+'\n                },\n'+run[b:]
# Shared scalar semantics stay literal in the match, with a defensive Swift hook.
run=run.replace('                Operation::Select => {','                Operation::Select => {\n                    $leaf!(select_guard $this);')
# All existing structural and memory algorithms remain one existing shared body.
run=run.replace('return Err(self.trap("unreachable"))','return Err($leaf!(trap self, "unreachable"))')
run=run.replace('self.push(', '$leaf!(push self, ').replace('self.pop()','$leaf!(pop self)').replace('self.pop32()','$leaf!(pop32 self)')
# Push calls now need their macro closing delimiter, easiest exact known patterns.
run=run.replace('$leaf!(push self, value)?','$leaf!(push self, value)?')
# The replacement above already changes only the callee opening and original
# close is the macro close: `$leaf!(push self, value)`.
run=run.replace('self.call(function)?','$leaf!(call self, function)?')
for original,kind in [('self.grow()?','growth'),('self.copy()?','copy'),('self.fill()?','fill'),('self.load(opcode, offset)?','load'),('self.store(opcode, offset)?','store'),('self.numeric(opcode, false)?','numeric'),('self.numeric(opcode, true)?','saturating')]:
 args=', opcode, offset' if kind in ['load','store'] else ', opcode' if kind in ['numeric','saturating'] else ''
 run=run.replace(original,'$leaf!('+kind+' self'+args+')?')
run=run.replace('borrowed::shared_memory_size!(self, frozen_bulk_memory_leaf)?','$leaf!(memory_size self)?')
# Control mapping is a literal shared match; only actual owner-specific leaf differs.
run=run.replace('borrowed::shared_control_arm!', '$control!').replace('frozen_control_leaf','$control_leaf')
a=run.index('            if finished {');z=run.rfind('        }')
leaf('finish',['s','finished'],run[a:z]);run=run[:a]+'            $leaf!(publication self);\n            $leaf!(finish self, finished);\n'+run[z:]
# Call extraction retains the same parameter/base/floor/import ordering.
a=call.index('        let params =');z=call.index('        self.work(params)?;')
leaf('parameters',['s','function'],call[a:z].replace('let params =','').rstrip().removesuffix(';'))
call=call[:a]+'        let params = $leaf!(parameters self, function);\n'+call[z:]
call=call.replace('self.work(params)?','$leaf!(parameter_work self, params, function)?')
a=call.index('        let base =');z=call.index('        if self.cache.spans().execution_import(function).is_some()')
leaf('base',['s','params'],call[a:z].replace('let base =',''))
# The floor statement references base and frame; keep this leaf statement-based.
leaves.pop();leaf('base',['s','params','base'],call[a:z]);call=call[:a]+'        $leaf!(base self, params, base);\n'+call[z:]
call=call.replace('self.cache.spans().execution_import(function).is_some()','$leaf!(is_import self, function)')
a=call.index('            // The Call');z=call.index('        } else {',a)
leaf('import',['s','function','base'],call[a:z]);call=call[:a]+'            $leaf!{import self, function, base}\n'+call[z:]

# One shared indirect orchestration, including selector consumption, scan debit,
# structural decision and the exact same selected-target call route.
ind=base[base.index('                Operation::CallIndirect(index) => {'):base.index('                Operation::MemorySize =>',base.index('                Operation::CallIndirect(index) => {'))]
ind=ind[ind.index('{')+1:ind.rfind('}')]
a=ind.index('                    let function =');b=ind.index('                    let expected =')
leaf('table_target',['s','selector'],ind[a:b].replace('let function =','').rstrip().removesuffix(';'))
ind=ind[:a]+'                    let function = $leaf!(table_target self, selector);\n'+ind[b:]
a=ind.index('                    let expected =');b=ind.index('                    let actual =')
leaf('expected_type',['s','index'],ind[a:b].replace('let expected =','').rstrip().removesuffix(';'))
ind=ind[:a]+'                    let expected = $leaf!(expected_type self, index);\n'+ind[b:]
a=ind.index('                    let actual =');b=ind.index('                    let scan =')
leaf('actual_type',['s','function'],ind[a:b].replace('let actual =','').rstrip().removesuffix(';'))
ind=ind[:a]+'                    let actual = $leaf!(actual_type self, function);\n'+ind[b:]
a=ind.index('                    if self.cache.spans().execution_type(index)');b=ind.index('                    {',a) if '                    {' in ind[a:] else -1
# Original pretty source puts the opening brace on its own line.
expr=ind[a:ind.index('{',a)].removeprefix('                    if ').strip()
leaf('signature_mismatch',['s','index','function'],expr)
ind=ind[:a]+ind[a:].replace(expr,'$leaf!(signature_mismatch self, index, function)',1)
ind=ind.replace('self.pop32()','$leaf!(pop32 self)').replace('self.invariant()','$leaf!(invariant self)').replace('self.trap("indirect_call_type_mismatch")','$leaf!(trap self, "indirect_call_type_mismatch")').replace('self.call(function)','$leaf!(call self, function)')
leaves=[x for x in leaves if not x.startswith('    (indirect ')]
leaves.append('    (indirect $s:ident, $index:ident) => {shared_indirect!{$s,frozen_dispatch_leaf,$index}};')
leaves.append('    (invariant $s:ident) => {$s.invariant()};')
ind=ind.replace('self','$this').replace('index)','$index)').replace(' self, index',' self, $index').replace('$this, index','$this, $index')
borrow+='\n#[allow(unused_macros)]\nmacro_rules! shared_indirect {\n    ($this:ident,$leaf:ident,$index:ident) => {'+ind+'\n    };\n}\npub(crate) use shared_indirect;\n'
# Frozen leaf primitive expansions preserve successful ordering and every token.
leaves += [
 '    (select_guard $s:ident) => {};', '    (publication $s:ident) => {};',
 '    (trap $s:ident, $code:expr) => {$s.trap($code)};',
 '    (push $s:ident, $value:expr) => {$s.push($value)};',
 '    (pop $s:ident) => {$s.pop()};', '    (pop32 $s:ident) => {$s.pop32()};',
 '    (call $s:ident, $function:ident) => {$s.call($function)};',
 '    (parameter_work $s:ident, $params:ident, $function:ident) => {$s.work($params)};',
 '    (is_import $s:ident, $function:ident) => {$s.cache.spans().execution_import($function).is_some()};',
 '    (memory_size $s:ident) => {borrowed::shared_memory_size!($s, frozen_bulk_memory_leaf)};',
 '    (growth $s:ident) => {$s.grow()};', '    (copy $s:ident) => {$s.copy()};', '    (fill $s:ident) => {$s.fill()};',
 '    (load $s:ident, $opcode:ident, $offset:ident) => {$s.load($opcode,$offset)};',
 '    (store $s:ident, $opcode:ident, $offset:ident) => {$s.store($opcode,$offset)};',
 '    (numeric $s:ident, $opcode:ident) => {$s.numeric($opcode,false)};',
 '    (saturating $s:ident, $opcode:ident) => {$s.numeric($opcode,true)};',
]
borrow+='\n// Complete static run/call orchestration; original Frozen tokens are retained.\n#[allow(unused_macros)]\nmacro_rules! frozen_dispatch_leaf {\n'+'\n'.join(leaves)+'\n}\npub(crate) use frozen_dispatch_leaf;\n'
import re
run=re.sub(r'\$leaf!\((fetch|prefix|local_get|local_set|global_get|global_set|indirect|select_guard|publication|finish)([^;\n]*)\);', r'$leaf!{\1\2}',run)
run=run.replace('self','$this').replace('borrowed::','crate::experimental::execution::borrowed::')
call=call.replace('$leaf!(base self, params, base);','$leaf!{base self, params, base}')
call=call.replace('self','$this').replace('function','$function')
borrow+='\n#[allow(unused_macros)]\nmacro_rules! shared_run {\n    ($this:ident,$leaf:ident,$control:ident,$control_leaf:ident) => {'+run+'\n    };\n}\npub(crate) use shared_run;\n'
borrow+='\n#[allow(unused_macros)]\nmacro_rules! shared_call {\n    ($this:ident,$leaf:ident,$function:ident) => {'+call+'\n    };\n}\npub(crate) use shared_call;\n'
out=base
for name,inv in [('call','borrowed::shared_call!(self, borrowed::frozen_dispatch_leaf, function)'),('run','borrowed::shared_run!(self, borrowed::frozen_dispatch_leaf, borrowed::shared_control_arm, frozen_control_leaf)')]:
 # Macro paths are passed as identifiers by importing once at the module boundary.
 inv=inv.replace('borrowed::frozen_dispatch_leaf','frozen_dispatch_leaf').replace('borrowed::shared_control_arm,','shared_control_arm,')
 a,z,b,_=body(name);out=out.replace(base[a:z],base[a:b+1]+'\n        '+inv+'\n    }')
out=out.replace('borrowed::shared_call!(self, frozen_dispatch_leaf, function)', 'borrowed::shared_call!{self, frozen_dispatch_leaf, function}').replace('borrowed::shared_run!(self, frozen_dispatch_leaf, shared_indirect, shared_control_arm, frozen_control_leaf)', 'borrowed::shared_run!{self, frozen_dispatch_leaf, shared_indirect, shared_control_arm, frozen_control_leaf}')
out=out.replace('use borrowed::{','use borrowed::{frozen_dispatch_leaf, shared_indirect, shared_control_arm, ')
(HERE/'candidate/src/experimental/execution/mod.rs').write_text(out)
(HERE/'candidate/src/experimental/execution/borrowed.rs').write_text(borrow)
