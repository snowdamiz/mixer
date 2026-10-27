package dev.mixer.android;
import android.app.Activity;
import android.view.*;
import android.widget.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.function.Consumer;

/** Five separate legacy positives. No V2 disposition or successor authority. */
public final class V1PositiveWitness {
 private V1PositiveWitness(){}private static int checks;
 private static final String DESC="(Ldev/mixer/android/NativeRenderer$Record;Ldev/mixer/android/UiPacket$Node;Ljava/util/Map;)V";
 private static final Map<Integer,String> METHODS=Map.of(111,"ViewGroup.removeViewAt",220,"ViewGroup.addView",262,"View.setLayoutParams",381,"MarginLayoutParams.setMarginEnd",398,"View.setLayoutParams");
 private static final IdentityHashMap<Object,String> identities=new IdentityHashMap<>();private static final Map<Integer,Map<String,Object>> entry=new HashMap<>(),rows=new LinkedHashMap<>();private static final List<Map<String,Object>> allEvents=new ArrayList<>();private static String stage;private static NativeRenderer renderer;
 private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
 private static String id(Object value){if(value==null)return null;return identities.computeIfAbsent(value,x->x.getClass().getName()+"#"+(identities.size()+1));}
 private static Object read(Object target,String name){if(target==null)return null;for(Class<?> type=target.getClass();type!=null;type=type.getSuperclass())try{Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(target);}catch(NoSuchFieldException absent){/* continue */}catch(IllegalAccessException failure){throw new AssertionError(failure);}return null;}
 private static Map<String,Object> map(Object...pairs){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)m.put((String)pairs[i],pairs[i+1]);return m;}
 private static Map<String,Object> snapshot(Object receiver){
  Map<String,Object> s=map("identity",id(receiver),"class",receiver.getClass().getName());
  if(receiver instanceof View){s.put("tag",read(receiver,"tag"));s.put("parent",id(read(receiver,"parent")));Object lp=read(receiver,"layoutParams");s.put("layout_params",id(lp));s.put("layout_params_class",lp==null?null:lp.getClass().getName());if(lp!=null)for(String f:List.of("width","height","marginEnd","bottomMargin","gravity"))s.put(f,read(lp,f));}
  if(receiver instanceof ViewGroup){List<?> children=(List<?>)read(receiver,"children");List<Object> ids=new ArrayList<>(),tags=new ArrayList<>();for(Object child:children){ids.add(id(child));tags.add(read(child,"tag"));}s.put("child_ids",ids);s.put("child_tags",tags);s.put("child_count",children.size());}
  if(receiver instanceof ViewGroup.LayoutParams)for(String f:List.of("width","height","marginEnd","bottomMargin"))s.put(f,read(receiver,f));return s;
 }
 private static void observe(ConcreteHostProbe.Event event){
  check(allEvents.size()<8192,"finite legacy event bound");List<Object> frames=new ArrayList<>();Integer selected=null;
  for(var frame:event.productionFrames){frames.add(map("class",frame.className(),"method",frame.methodName(),"descriptor",frame.descriptor(),"bci",frame.bytecodeIndex()));if(frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("children")&&frame.descriptor().equals(DESC)&&METHODS.containsKey(frame.bytecodeIndex())&&METHODS.get(frame.bytecodeIndex()).equals(event.method))selected=frame.bytecodeIndex();}
  allEvents.add(map("sequence",allEvents.size(),"stage",stage,"method",event.method,"phase",event.phase,"receiver_identity",id(event.receiver),"production_frames",frames));
  if(selected==null||rows.containsKey(selected))return;
  Map<String,Object> state=snapshot(event.receiver);if((selected==111||selected==220)&&!"root".equals(state.get("tag")))return;if(selected==262&&!"back".equals(state.get("tag")))return;if(selected==398&&!"section".equals(state.get("tag")))return;
  Map<String,Object> point=map("stage",stage,"sequence",allEvents.size()-1,"method",event.method,"phase",event.phase,"native_count",ConcreteHostProbe.count(event.method,event.phase),"receiver",state,"production_frames",frames);
  if(event.phase.equals("entry"))entry.put(selected,point);
  else if(event.phase.equals("beforeReturn")&&entry.containsKey(selected))rows.put(selected,map("id","legacy-v1-children-bci-"+selected,"bci",selected,"method",event.method,"caller_class","dev.mixer.android.NativeRenderer","caller_method","children","caller_descriptor",DESC,"renderer_identity",id(renderer),"authority_mode","LEGACY_V1","captured_attempt_identity",null,"v2_fence",id(read(renderer,"v2Fence")),"entry",entry.get(selected),"before_return",point));
 }
 private static byte[] packet(long revision)throws Exception{Method m=NativeOwnerV2ConcreteHostTests.class.getDeclaredMethod("packet",long.class);m.setAccessible(true);return(byte[])m.invoke(null,revision);}
 private static View apply(long revision)throws Exception{
  stage="legacy-apply-"+revision;ConcreteHostProbe.reset();NativeOutcomeProbe.begin(outcome->{});Consumer<ConcreteHostProbe.Event> observer=V1PositiveWitness::observe;ConcreteHostProbe.installQualificationHook(observer);View actual;Throwable escaped=null;
  try{actual=renderer.apply(UiPacket.decode(packet(revision)));}catch(RuntimeException|Error failure){escaped=failure;throw failure;}finally{ConcreteHostProbe.clearQualificationHook(observer);NativeOutcomeProbe.end();check(NativeOutcomeProbe.clean(),"each legacy attempt cleanliness latched before next begin");}
  check(actual==renderer.view("root")&&renderer.packet.revision.equals(Long.toString(revision)),"actual enclosing apply return/current packet");
  for(Map<String,Object> row:rows.values())if(!row.containsKey("enclosing_result"))row.put("enclosing_result",map("stage",stage,"original_result_kind","view-reference","actual_identity",id(actual),"expected_identity",id(renderer.view("root")),"same_reference",true,"normal_return",true,"escaped_exception",escaped));return actual;
 }
 @SuppressWarnings("unchecked") private static Map<String,Object> state(Map<String,Object> row,String phase){return(Map<String,Object>)((Map<String,Object>)row.get(phase)).get("receiver");}
 private static void write(StringBuilder out,Object value){if(value instanceof Map<?,?> m){out.append('{');boolean comma=false;for(var e:m.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,e.getKey());out.append(':');write(out,e.getValue());}out.append('}');}else if(value instanceof List<?> a){out.append('[');for(int i=0;i<a.size();i++){if(i>0)out.append(',');write(out,a.get(i));}out.append(']');}else if(value instanceof Number n)out.append(n);else Json.write(out,value);}
 public static void main(String[] args)throws Exception{
  Activity activity=new Activity();renderer=new NativeRenderer(activity,ignored->{});View root=apply(1);View text=renderer.view("text");((ViewGroup)root).addView(new View(activity));apply(2);check(renderer.view("text")==text,"legacy exact generation reuse");check(rows.keySet().equals(METHODS.keySet()),"all five exact positive BCIs observed");
  Map<String,Object> remove=rows.get(111),add=rows.get(220),frame=rows.get(262),margin=rows.get(381),linear=rows.get(398);
  check(state(remove,"entry").get("child_count").equals(2)&&state(remove,"before_return").get("child_count").equals(1)&&state(remove,"before_return").get("child_tags").equals(List.of("section")),"removeViewAt actual stray child removal");
  check(state(add,"entry").get("child_count").equals(0)&&state(add,"before_return").get("child_count").equals(1)&&state(add,"before_return").get("child_tags").equals(List.of("section")),"addView actual root child once");
  check(state(frame,"before_return").get("layout_params_class").equals("android.widget.FrameLayout$LayoutParams")&&state(frame,"before_return").get("width").equals(-2)&&state(frame,"before_return").get("height").equals(-2),"FrameLayout exact normal layout result");
  check(state(margin,"before_return").get("marginEnd").equals(0)&&state(margin,"before_return").get("width").equals(-2),"horizontal default spacing exact original margin result");
  check(state(linear,"before_return").get("layout_params_class").equals("android.widget.LinearLayout$LayoutParams")&&state(linear,"before_return").get("width").equals(-1)&&state(linear,"before_return").get("height").equals(-2),"LinearLayout exact normal layout result");
  Map<String,Object> output=map("scope","Five separate actual V1 positives, no V2/OTA/native qualification","checks",checks,"rows",new ArrayList<>(rows.values()),"event_sequence",allEvents,"all_five_present",true,"policy_or_full_matrix_accepted",false);StringBuilder encoded=new StringBuilder();write(encoded,output);Files.writeString(Path.of(args[0]),encoded+"\n");System.out.println("PASS five separate V1 positives checks="+checks+" BCIs111/220/262/381/398; actual enclosing legacy apply returns");
 }
}
