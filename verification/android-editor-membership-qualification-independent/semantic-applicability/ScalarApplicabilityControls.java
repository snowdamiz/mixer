package dev.mixer.android;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
/** Finite actual-value tests for misleading method names; host source only. */
public final class ScalarApplicabilityControls {
 private ScalarApplicabilityControls(){}private static int checks;
 private static void check(boolean v,String message){checks++;if(!v)throw new AssertionError(message);}
 private static OwnerLifecycleV2.Snapshot snapshot(boolean pending,Object failure){return new OwnerLifecycleV2.Snapshot(OwnerLifecycleV2.Phase.RETIRED,7,true,false,false,null,null,null,new Object(),OwnerLifecycleV2.Reason.CLOSED,null,false,false,pending,null,null,failure);}
 public static void main(String[] args)throws Exception{
  ConcreteHostProbe.reset();Method close=AppearanceGeometryV2.class.getDeclaredMethod("close");close.setAccessible(true);
  AppearanceGeometryV2.Command a=(AppearanceGeometryV2.Command)close.invoke(null),b=(AppearanceGeometryV2.Command)close.invoke(null);
  check(a.op()==AppearanceGeometryV2.Op.close&&a.points().isEmpty(),"close is path Command factory");check(a!=b&&a.equals(b),"distinct equal allocated Commands");
  boolean immutable=false;try{a.points().add(new AppearanceGeometryV2.Point(1,2));}catch(UnsupportedOperationException expected){immutable=true;}check(immutable,"points immutable");
  Object[] failures={null,new Object(),new AssertionError("data not thrown")};
  for(boolean pending:new boolean[]{false,true})for(Object failure:failures){OwnerLifecycleV2.Snapshot s=snapshot(pending,failure);check(s.closePending()==pending,"stored pending primitive");check(s.closeFailure()==failure,"stored diagnostic identity including Error data");}
  NativeAppearanceViewsV2.NativeField.Attempt attempt=new NativeAppearanceViewsV2.NativeField.Attempt(null,null);NativeEditorConnectionV2.Base adapter=new NativeEditorConnectionV2.Base(null,attempt);
  check(adapter.getHandler()==null,"bootstrap null on current JVM thread");AtomicReference<Object> result=new AtomicReference<>();Object sentinel=new Object();result.set(sentinel);
  Thread thread=new Thread(()->{try{result.set(adapter.getHandler());}catch(Throwable failure){result.set(failure);}},"owned-scalar-getHandler-review");thread.start();thread.join(2000);check(!thread.isAlive(),"bounded JVM thread reaped");check(result.get()==null,"bootstrap null on another JVM thread");check(adapter.field==null&&adapter.attempt==attempt&&adapter.target==null&&attempt.target==null&&!attempt.revoked,"captured identities unchanged");
  String[][] enums={{"NativeAppearanceViewsV2$NativeField$Phase","IDLE","CREATING","ACTIVE","DRAINING","CLOSING","QUARANTINED"},{"NativeAppearanceViewsV2$NativeField$Close","NOT_REQUESTED","DEFERRED","ATTEMPTED","RETURNED","FAILED_UNCERTAIN","NO_TARGET"},{"NativeAppearanceViewsV2$Replacement$Stage","SNAPSHOTTING","CLOSING","NATIVE","DONE"}};
  for(String[] record:enums){Class<?> type=Class.forName("dev.mixer.android."+record[0]);Method values=type.getDeclaredMethod("values"),valueOf=type.getDeclaredMethod("valueOf",String.class);values.setAccessible(true);valueOf.setAccessible(true);Object[] first=(Object[])values.invoke(null),second=(Object[])values.invoke(null);check(first!=second&&first.length==record.length-1,"values fresh array, exact size");for(int i=0;i<first.length;i++){Enum<?> value=(Enum<?>)first[i];check(value.name().equals(record[i+1])&&value.ordinal()==i&&value==second[i],"declared enum order/identity");check(valueOf.invoke(null,record[i+1])==value,"valueOf exact constant");}first[0]=null;check(((Object[])values.invoke(null))[0]==second[0],"caller array mutation cannot alter enum roster");for(String invalid:new String[]{"missing",null}){Throwable failure=null;try{valueOf.invoke(null,new Object[]{invalid});}catch(InvocationTargetException expected){failure=expected.getCause();}check(invalid==null?failure instanceof NullPointerException:failure instanceof IllegalArgumentException,"valueOf explicit invalid-name exception");}}
  check(ConcreteHostProbe.events().isEmpty(),"factory/accessor/enum/getHandler controls produced zero native probe events");
  System.out.println("PASS actual scalar/factory/accessor/enum controls checks="+checks+"; exact values and any-thread getHandler; no native callback or cleanup credit");
 }
}
