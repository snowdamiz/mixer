#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,re,sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(vm):
 p=[vm/'Cargo.toml',vm/'Cargo.lock']
 for d in ['src','tests','include']:p+=sorted(f for f in (vm/d).rglob('*') if f.is_file())
 return {str(f.relative_to(vm)):sha(f) for f in p}
def method(s,name):
 a=s.index('fn '+name+'(');b=s.index('{',a);i=b+1;n=1
 while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
def build(dest):
 baseline=files(ROOT/'vm'); assert hashlib.sha256(enc(baseline)).hexdigest()=='4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
 for name in baseline:
  p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'vm'/name,p)
 borrowed=dest/'src/experimental/execution/borrowed.rs';s=borrowed.read_text()
 prefix='macro_rules! frozen_control_methods {\n    () => {\n';a=s.index(prefix);start=a+len(prefix);end=s.index('\n    };\n}',start);body=s[start:end]
 body=body.replace('let frame = self.frames.last().ok_or_else(|| self.invariant())?;','$leaf!(frame $this, frame);')
 body=body.replace('self.controls[index]', '$leaf!(copy_control $this, index)')
 body=body.replace('self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = pc;','$leaf!(set_pc $this, pc);')
 body=body.replace('self.values.truncate(control.height);','$leaf!(truncate_values $this, $leaf!(height $control));')
 body=body.replace('self.controls.truncate(if control.kind == Kind::Loop {\n                index + 1\n            } else {\n                index\n            });','$leaf!(truncate_controls $this, if $leaf!(loop $control) {\n                index + 1\n            } else {\n                index\n            });')
 for old,new in [('control.result = false;','$leaf!(clear $control);'),('control.kind == Kind::Loop','$leaf!(loop $control)'),('control.kind == Kind::Function','$leaf!(function $control)'),('control.end + 1','$leaf!(after_end $this, $control)'),('depth as usize + 1','$leaf!(depth_offset $this, depth)'),('control.start','$leaf!(start $control)'),('control.height','$leaf!(height $control)'),('control.result','$leaf!(result $control)'),('frame.controls','$leaf!(floor frame)'),('self.pop()','$leaf!(pop $this)'),('self.push(value)','$leaf!(push $this, value)'),('self.observe()','$leaf!(observe $this)'),('self.invariant()','$leaf!(invariant $this)'),('self.values','$leaf!(values $this)'),('self.controls','$leaf!(controls $this)'),('self\n                .controls','$leaf!(controls $this)')]:body=body.replace(old,new)
 body=re.sub(r'\bself\b','$this',body);body=re.sub(r'(?<!\$)\bcontrol\b','$control',body)
 marker='fn close_control(&mut $this, $control: Control) -> Result<(), ExecutionFailure> {\n';assert marker in body;body=body.replace(marker,marker+'            $($close_prelude)*\n');body=body.replace('ExecutionFailure','$failure')
 s=s[:a]+'''macro_rules! frozen_control_methods {
    () => { shared_control_methods!(self, ExecutionFailure, frozen_control_leaf, control, {}); };
}

#[allow(unused_macros)]
macro_rules! shared_control_methods {
    ($this:ident, $failure:ty, $leaf:ident, $control:ident, {$($close_prelude:tt)*}) => {
'''+body+'''
    };
}

#[allow(unused_macros)]
macro_rules! frozen_control_leaf {
    (pop $s:ident) => { $s.pop() };
    (push $s:ident, $v:expr) => { $s.push($v) };
    (invariant $s:ident) => { $s.invariant() };
    (values $s:ident) => { $s.values };
    (controls $s:ident) => { $s.controls };
    (frame $s:ident, $f:ident) => { let $f = $s.frames.last().ok_or_else(|| $s.invariant())?; };
    (floor $f:ident) => { $f.controls };
    (result $c:ident) => { $c.result };
    (height $c:ident) => { $c.height };
    (loop $c:ident) => { $c.kind == Kind::Loop };
    (function $c:ident) => { $c.kind == Kind::Function };
    (clear $c:ident) => { $c.result = false };
    (start $c:ident) => { $c.start };
    (after_end $s:ident, $c:ident) => { $c.end + 1 };
    (depth_offset $s:ident, $d:ident) => { $d as usize + 1 };
    (truncate_values $s:ident, $h:expr) => { $s.values.truncate($h) };
    (truncate_controls $s:ident, $h:expr) => { $s.controls.truncate($h) };
    (observe $s:ident) => { $s.observe() };
    (set_pc $s:ident, $pc:expr) => { $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc = $pc };
    (copy_control $s:ident, $index:ident) => { $s.controls[$index] };
    (selected $s:ident, $target:ident) => { $target.ok_or_else(|| $s.invariant())? };
    (room $s:ident) => { $s.room_control() };
    (depth_limit $s:ident) => { $s.cache.spans().limits().control_depth };
    (depth_error $s:ident, $f:ident) => { $s.error(
        ExecutionFailureKind::ControlExhausted, "control_depth_exceeded",
        ($s.controls.len() - $f.controls + 1) as u64,
        $s.cache.spans().limits().control_depth as u64,
    ) };
    (publish $s:ident, $kind:ident, $f:ident, $end:ident, $result:ident) => {
        $s.controls.push(control_record!($kind, $f.pc, $end, $s.values.len(), $result.is_some()))
    };
    (false_pc $s:ident, $alternative:ident, $end:ident) => {
        $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc = $alternative.map_or($end, |v| v + 1)
    };
    (else_pc $s:ident, $end:ident) => { $s.frames.last_mut().ok_or_else(unreachable_failure)?.pc = $end };
    (pop_control $s:ident) => { $s.controls.pop().ok_or_else(|| $s.invariant()) };
    (block_guard $s:ident, $kind:ident, $end:ident, $alternative:ident) => {};
}

#[allow(unused_macros)]
macro_rules! control_record {
    ($kind:ident, $start:expr, $end:ident, $height:expr, $result:expr) => {
        Control {
            kind: match $kind { ControlKind::Block => Kind::Block, ControlKind::Loop => Kind::Loop, ControlKind::If => Kind::If },
            start: $start, $end, height: $height, result: $result,
        }
    };
}

#[allow(unused_imports)]
pub(super) use frozen_control_leaf;
#[allow(unused_imports)]
pub(super) use control_record;
#[allow(unused_imports)]
pub(crate) use shared_control_methods;
#[cfg(feature = "experimental-span-execution")]
#[allow(unused_imports)]
pub(super) use frozen_control_methods;
'''
 # shared must exist for Swift-only; Frozen wrapper remains span-only.
 s=s.replace('// Private literal control methods, emitted on the original frozen owner.','// Literal helpers and inline arms are shared at compile time; no runtime adapter.')
 borrowed.write_text(s)
 owner=dest/'src/experimental/execution/mod.rs';o=owner.read_text();o=o.replace('borrowed::frozen_control_methods!();','borrowed::frozen_control_methods!();')
 # Frozen wrapper invokes local macros by name, so import the private leaf/methods.
 o=o.replace('use crate::{Cancellation, Value};','use crate::{Cancellation, Value};\n#[allow(unused_imports)]\nuse borrowed::{control_record, frozen_control_leaf, shared_control_methods};')
 # Inline arm bodies are extracted from original source, then substitutable only at leaves.
 arm_start=o.index('                Operation::Block {',o.index('fn run('));arm_end=o.index('                Operation::Call(function)',arm_start)
 block=o[arm_start:arm_end]; old=block
 arms={}
 pat=re.compile(r'                Operation::(Block \{|Else \{|End =>|Br\(depth\) =>|BrIf\(depth\) =>|BrTable \{|Return =>)')
 chunks=list(pat.finditer(block))
 for i,m in enumerate(chunks):
  chunk=block[m.start():chunks[i+1].start() if i+1<len(chunks) else len(block)]
  which=m.group(1).split()[0].split('(')[0];head,bodypart=chunk.split('=>',1);bodypart=bodypart.strip().removesuffix(',')
  if bodypart.startswith('{'): bodypart=bodypart[1:-1].strip()
  original_body=bodypart
  if which=='Block':
   bodypart=bodypart.replace('self.room_control()?;', '$leaf!{block_guard $this, kind, end, alternative}\nself.room_control()?;',1)
   bodypart=bodypart.replace('self.room_control()','$leaf!(room $this)')
   bodypart=bodypart.replace('let frame = self.frames.last().ok_or_else(|| self.invariant())?;','$leaf!(frame $this, frame);')
   push_start=bodypart.index('self.controls.push(Control {');push_end=bodypart.index('\n                    if !cond',push_start)
   bodypart=bodypart[:push_start]+'$leaf!(publish $this, kind, frame, end, result);'+bodypart[push_end:]
   error_start=bodypart.index('self.error(');error_end=bodypart.index('));',error_start)+1
   bodypart=bodypart[:error_start]+'$leaf!(depth_error $this, frame)'+bodypart[error_end:]
   bodypart=bodypart.replace('self.cache.spans().limits().control_depth','$leaf!(depth_limit $this)')
   bodypart=bodypart.replace('self.frames.last_mut().ok_or_else(unreachable_failure)?.pc =\n                            alternative.map_or(end, |v| v + 1);','$leaf!(false_pc $this, alternative, end);')
   params=', $kind:ident, $result:ident, $end:ident, $alternative:ident';args=', kind, result, end, alternative'
   for name in ['kind','result','end','alternative']:bodypart=re.sub(r'\b'+name+r'\b','$'+name,bodypart)
  else:
   if which=='Else':bodypart=bodypart.replace('self.frames.last_mut().ok_or_else(unreachable_failure)?.pc = end','$leaf!(else_pc $this, end)');params=', $end:ident';args=', end';bodypart=re.sub(r'\bend\b','$end',bodypart)
   elif which in ['Br','BrIf']:params=', $depth:ident';args=', depth';bodypart=re.sub(r'\bdepth\b','$depth',bodypart)
   elif which=='BrTable':params=', $target:ident';args=', target';bodypart=re.sub(r'\btarget\b','$target',bodypart)
   else:params='';args=''
  for a,b in [('self.controls.pop().ok_or_else(|| self.invariant())','$leaf!(pop_control $this)'),('control.kind == Kind::Function','$leaf!(function control)'),('frame.controls','$leaf!(floor frame)'),('self.controls','$leaf!(controls $this)'),('self.pop32()','$this.pop32()'),('self.observe()','$leaf!(observe $this)'),('self.invariant()','$leaf!(invariant $this)')]:bodypart=bodypart.replace(a,b)
  bodypart=bodypart.replace('$target.ok_or_else(|| $leaf!(invariant $this))?', '$leaf!(selected $this, $target)')
  bodypart=re.sub(r'\bself\b','$this',bodypart);bodypart=re.sub(r'\bfinished\b','$finished',bodypart)
  arms[which]=(bodypart,params,args,head,original_body)
 new=''
 for which,(bodypart,params,args,head,original_body) in arms.items():
  invocation='borrowed::shared_control_arm! {'+which+', self, frozen_control_leaf, finished'+args+'}'
  new+=head+'=> '+(invocation if which in ['Br','Return'] else '{ '+invocation+''+' }')+',\n'
 o=o[:arm_start]+new+o[arm_end:]
 shared='\n#[allow(unused_macros)]\nmacro_rules! shared_control_arm {\n'
 for which,(bodypart,params,args,head,original_body) in arms.items():shared+='    ('+which+', $this:ident, $leaf:ident, $finished:ident'+params+') => {\n'+bodypart+'\n    };\n'
 shared+='}\n#[allow(unused_imports)]\npub(crate) use shared_control_arm;\n'
 borrowed.write_text(borrowed.read_text()+shared)
 o+='''
#[cfg(feature = "experimental-swift-reactor")]
impl Control {
    pub(crate) fn result(self) -> bool { self.result }
    pub(crate) fn height(self) -> usize { self.height }
    pub(crate) fn start(self) -> usize { self.start }
    pub(crate) fn end(self) -> usize { self.end }
    pub(crate) fn is_loop(self) -> bool { self.kind == Kind::Loop }
    pub(crate) fn is_function(self) -> bool { self.kind == Kind::Function }
    pub(crate) fn is_if(self) -> bool { self.kind == Kind::If }
    pub(crate) fn clear_result(&mut self) { self.result = false; }
    pub(crate) fn decoded(kind: ControlKind, start: usize, end: usize, height: usize, result: bool) -> Self {
        borrowed::control_record!(kind, start, end, height, result)
    }
}
'''
 owner.write_text(o)
 frame=dest/'src/experimental_swift_reactor/frame_operations.rs';f=frame.read_text()
 f=f.replace('    pub drained: Option<FrameDrainReport>,\n}','    pub drained: Option<FrameDrainReport>,\n    pub controlled: Option<Result<bool, SwiftRunFailure>>,\n}',1)
 f=f.replace('let clean = parts.frames.is_empty()','let clean = storage.controlled.is_none()\n            && parts.frames.is_empty()',1)
 f=f.replace('// ACCOUNTING_GENERATED_START','#[path = "control_operations.rs"]\npub(super) mod control_operations;\n// ACCOUNTING_GENERATED_START',1)
 f=f.replace('Some(nested) => ACTIVE_BYTES.checked_add(nested),','Some(nested) => match ACTIVE_BYTES.checked_add(nested) {\n            Some(bytes) => bytes.checked_add(control_operations::ACTIVE_BYTES), None => None,\n        },',1)
 frame.write_text(f)
 execution=dest/'src/experimental_swift_reactor/execution.rs';e=execution.read_text()
 e=e.replace('Some(header) => header\n                                                .checked_add(frame_operations::PERMANENT_BYTES),','Some(header) => match header.checked_add(frame_operations::PERMANENT_BYTES) {\n                                                Some(header) => header.checked_add(frame_operations::control_operations::PERMANENT_BYTES), None => None,\n                                            },',1)
 execution.write_text(e)
 tests=dest/'src/experimental_swift_reactor/frame_operations_tests.rs';t=tests.read_text().replace('        drained: None,\n    })','        drained: None,\n        controlled: None,\n    })').replace('        drained,\n    });','        drained,\n        controlled: None,\n    });');tests.write_text(t)
 shutil.copyfile(HERE/'overlay/src/experimental_swift_reactor/control_operations.rs',dest/'src/experimental_swift_reactor/control_operations.rs')
 return baseline
if __name__=='__main__':
 dest=Path(sys.argv[1]);baseline=build(dest);(HERE/'baseline-manifest.json').write_bytes(enc(baseline));print(dest)
