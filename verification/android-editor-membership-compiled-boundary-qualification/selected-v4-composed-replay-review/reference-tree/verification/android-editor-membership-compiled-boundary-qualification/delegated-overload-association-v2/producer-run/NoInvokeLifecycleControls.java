package dev.mixer.android;
import java.lang.reflect.*;
import java.lang.invoke.MethodType;
import java.nio.file.*;
import java.util.*;
/** Finite bodies only: twelve flag assignments and two empty lifecycle lambdas. */
public final class NoInvokeLifecycleControls {
 private NoInvokeLifecycleControls(){}
 private record Body(String method,String field,boolean value){}
 private static final List<Body> BODIES=List.of(
  new Body("lambda$onFocusChanged$2","focusLost",true),new Body("lambda$onFocusChanged$3","focusLost",false),
  new Body("lambda$onWindowFocusChanged$5","windowFocusLost",true),new Body("lambda$onWindowFocusChanged$6","windowFocusLost",false),
  new Body("lambda$onWindowVisibilityChanged$8","windowHidden",true),new Body("lambda$onWindowVisibilityChanged$9","windowHidden",false),
  new Body("lambda$onVisibilityAggregated$11","aggregateHidden",true),new Body("lambda$onVisibilityAggregated$12","aggregateHidden",false),
  new Body("lambda$onVisibilityChanged$14","viewHidden",true),new Body("lambda$onVisibilityChanged$15","viewHidden",false),
  new Body("lambda$onDetachedFromWindow$17","detached",true),new Body("lambda$onDetachedFromWindow$18",null,false),
  new Body("lambda$onAttachedToWindow$20",null,false),new Body("lambda$onAttachedToWindow$21","detached",false));
 private static final List<String> FLAGS=List.of("focusLost","windowFocusLost","windowHidden","aggregateHidden","viewHidden","detached");
 private static int checks;
 private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
 private static Map<String,Object> map(Object...pairs){Map<String,Object> out=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)out.put((String)pairs[i],pairs[i+1]);return out;}
 private static Field field(Class<?> type,String name)throws ReflectiveOperationException{Field value=type.getDeclaredField(name);value.setAccessible(true);return value;}
 private static Map<Field,Object> snapshot(Object receiver)throws IllegalAccessException{Map<Field,Object> out=new LinkedHashMap<>();for(Class<?> type=receiver.getClass();type!=null&&type!=Object.class;type=type.getSuperclass()){Field[] fields=type.getDeclaredFields();Arrays.sort(fields,Comparator.comparing(Field::getName));for(Field value:fields)if(!Modifier.isStatic(value.getModifiers())){value.setAccessible(true);out.put(value,value.get(receiver));}}return out;}
 private static List<Object> typed(Map<Field,Object> values){List<Object> out=new ArrayList<>();for(var entry:values.entrySet()){Field value=entry.getKey();out.add(map("declaring_class",value.getDeclaringClass().getName(),"field",value.getName(),"type",value.getType().getName(),"value",OutcomeCapture.actual(entry.getValue())));}return out;}
 public static void main(String[] args)throws Exception{
  Field descriptor=field(EditorImplementationTests.class,"descriptor");descriptor.set(null,Files.readAllBytes(Path.of(args[0])));Object fixture=DirectBoundaryStates.fixture("hello");Object receiver=DirectBoundaryStates.get(fixture,"edit");NativeOwnerV2 owner=(NativeOwnerV2)DirectBoundaryStates.get(fixture,"owner");android.os.Handler queue=(android.os.Handler)DirectBoundaryStates.get(fixture,"queue");List<Object> rows=new ArrayList<>();Map<Field,Object> original=snapshot(receiver);
  try{
   for(Body body:BODIES)for(boolean initial:List.of(false,true)){
    for(String name:FLAGS)field(receiver.getClass(),name).setBoolean(receiver,initial);
    Map<Field,Object> before=snapshot(receiver),expected=new LinkedHashMap<>(before);if(body.field()!=null)expected.put(field(receiver.getClass(),body.field()),body.value());
    Method method=receiver.getClass().getDeclaredMethod(body.method());method.setAccessible(true);String desc=MethodType.methodType(method.getReturnType(),method.getParameterTypes()).descriptorString();check(desc.equals("()V")&&method.isSynthetic(),"exact selected synthetic void descriptor");
    ConcreteHostProbe.reset();OutcomeCapture capture=new OutcomeCapture();capture.begin();Object result=null;Throwable escaped=null;try{result=method.invoke(receiver);}catch(InvocationTargetException failure){escaped=failure.getCause();}finally{capture.end();}
    boolean clean=capture.clean();Map<Field,Object> after=snapshot(receiver);check(result==null&&escaped==null,"actual normal void reflection result");check(typed(after).equals(typed(expected)),"all bounded direct instance fields match independently selected single assignment or empty body");check(clean&&capture.rows.isEmpty()&&ConcreteHostProbe.events().isEmpty(),"zero native events/outcomes with per-attempt clean latch");
    String id=receiver.getClass().getName().replace('.','/')+'#'+body.method()+desc;rows.add(map("subject_id",id,"case_id",body.method()+"-initial-"+initial,"actual_method",map("class",receiver.getClass().getName(),"method",body.method(),"descriptor",desc),"receiver_identity",DirectBoundaryStates.identity(receiver),"initial_flags",initial,"selected_assignment",body.field()==null?null:map("field",body.field(),"type","boolean","value",body.value()),"before_fields",typed(before),"actual_fields",typed(after),"expected_fields",typed(expected),"actual_outcome",Map.of("kind","void"),"expected_outcome",Map.of("kind","void"),"native_events",0,"native_outcomes",0,"attempt_clean_latched",clean,"status","passed-finite-no-invoke-body","scope","Selected lambda body only. No enclosing lifecycle callback, authority, cleanup or loss-observation credit."));
   }
  }finally{for(var entry:original.entrySet())if(!Modifier.isFinal(entry.getKey().getModifiers()))entry.getKey().set(receiver,entry.getValue());owner.close();queue.drainAll(8);ConcreteHostProbe.reset();}
  Files.writeString(Path.of(args[1]),DirectBoundaryStates.json(map("schema",1,"subjects",BODIES.size(),"invocations",rows.size(),"checks",checks,"rows",rows,"enclosing_lifecycle_obligations","pending"))+"\n");System.out.println("PASS fourteen no-invoke lifecycle bodies: "+rows.size()+" calls / "+checks+" checks; enclosing lifecycle pending");
 }
}
