from pathlib import Path
import shutil
D=Path(__file__).resolve().parent;E=D/'full-candidate-v1'
E.mkdir(exist_ok=False)
for name in ('DirectBoundaryStates.java','QueryBoundaryStates.java','LegacyBoundaryStates.java'):
 s=(D/name).read_text()
 if name!='LegacyBoundaryStates.java':
  s=s.replace('DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();','DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();OutcomeCapture outcomes=new OutcomeCapture();') if name.startswith('Query') else s.replace('Trace trace=new Trace();','Trace trace=new Trace();OutcomeCapture outcomes=new OutcomeCapture();')
  s=s.replace('ConcreteHostProbe.hook=(method,phase)->{','java.util.function.Consumer<ConcreteHostProbe.Event> selectedHook=event->{String method=event.method,phase=event.phase;')
  # The original ordinary hook remains available to unchanged scenario bodies. Injection uses the separately selected after-hook lifetime.
  s=s.replace('   };\n   try{result=operation', '   };ConcreteHostProbe.installQualificationHook(selectedHook);\n   try{result=operation')
  s=s.replace('};\n   try{result=operation','};ConcreteHostProbe.installQualificationHook(selectedHook);\n   try{result=operation')
  s=s.replace('ConcreteHostProbe.hook=null;row.put("operation_end_sequence"','ConcreteHostProbe.clearQualificationHook(selectedHook);row.put("operation_end_sequence"')
  s=s.replace('ConcreteHostProbe.reset();ConcreteHostProbe.auditSink=trace::event;','ConcreteHostProbe.reset();outcomes.begin();ConcreteHostProbe.auditSink=trace::event;')
  s=s.replace('ConcreteHostProbe.auditSink=null;ConcreteHostProbe.reset();','ConcreteHostProbe.auditSink=null;outcomes.end();row.put("actual_native_outcomes",outcomes.rows);row.put("outcome_probe_clean",outcomes.clean());if(!outcomes.clean()&&validation==null)validation=new AssertionError("unclean passive outcome/hook lifetime");ConcreteHostProbe.reset();')
 else:
  # Select a scenario with both actual phases of the exact call, avoiding old positive-only hint substitutions.
  old='String scenario=witnesses.contains("smoke")?"smoke":witnesses.contains("positive")?"positive":witnesses.isEmpty()?null:str(witnesses.get(0));'
  s=s.replace(old,'String scenario=item.get("selected_scenario") instanceof String selectedScenario?selectedScenario:witnesses.isEmpty()?null:str(witnesses.get(0));')
  s=s.replace('DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();','DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();OutcomeCapture outcomes=new OutcomeCapture();List<Object> selectedOwnerJni=new ArrayList<>();')
  s=s.replace('ConcreteHostProbe.reset();ConcreteHostProbe.auditSink=e->{trace.event(e);if(fired[0]', 'ConcreteHostProbe.reset();outcomes.begin();ConcreteHostProbe.auditSink=e->{trace.event(e);if(fired[0]&&active()==fixture[0]&&e.method.equals("NativeBridge.commitV2")&&e.phase.equals("entry"))selectedOwnerJni.add(Map.of("method",e.method,"phase",e.phase,"sequence_index",trace.sequence.size()-1));};java.util.function.Consumer<ConcreteHostProbe.Event> selectedHook=e->{if(fired[0]')
  s=s.replace('  };\n  try{run.invoke', '  };ConcreteHostProbe.installQualificationHook(selectedHook);\n  try{run.invoke')
  s=s.replace('finally{ConcreteHostProbe.auditSink=null;ConcreteHostProbe.hook=null;}','finally{ConcreteHostProbe.clearQualificationHook(selectedHook);ConcreteHostProbe.auditSink=null;ConcreteHostProbe.hook=null;outcomes.end();}')
  s=s.replace('NativeBridge.commitCalls==commits[0],"no late commit after selected terminal callback"','selectedOwnerJni.isEmpty(),"no late commit for selected owner after selected terminal callback"')
  s=s.replace('row.put("selected_hook_fired",fired[0]);','row.put("actual_native_outcomes",outcomes.rows);row.put("outcome_probe_clean",outcomes.clean());row.put("selected_owner_jni_after_hook",selectedOwnerJni);row.put("enclosing_actual_outcome",escaped==null?Map.of("kind","void"):Map.of("kind","exception","class",escaped.getClass().getName(),"identity",DirectBoundaryStates.identity(escaped)));if(!outcomes.clean()&&validation==null)validation=new AssertionError("unclean passive outcome/hook lifetime");row.put("selected_hook_fired",fired[0]);')
 (E/name).write_text(s)
shutil.copy2(__file__,E/'prepare_full_candidate.py')
