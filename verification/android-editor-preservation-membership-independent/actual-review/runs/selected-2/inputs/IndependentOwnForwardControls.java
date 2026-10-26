package dev.mixer.android;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;

/** Root-selected replacement expectation for one exact own-forward boolean.
 * No other private identity, scope, count or product byte is mutated.
 */
public final class IndependentOwnForwardControls {
    private IndependentOwnForwardControls() {}
    private static int assertions;
    private static void check(boolean yes,String why){assertions++;if(!yes)throw new AssertionError(why);}
    private static Field field(Object o,String n){try{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f;}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static Object get(Object o,String n){try{return field(o,n).get(o);}catch(IllegalAccessException e){throw new AssertionError(e);}}
    private static void put(Object o,String n,Object v){try{field(o,n).set(o,v);}catch(IllegalAccessException e){throw new AssertionError(e);}}
    private static Object invoke(Object o,String n,Object... args){for(Method m:o.getClass().getDeclaredMethods())if(m.getName().equals(n)&&m.getParameterCount()==args.length)try{m.setAccessible(true);return m.invoke(o,args);}catch(InvocationTargetException e){return rethrow(e.getCause());}catch(ReflectiveOperationException e){throw new AssertionError(e);}throw new AssertionError(n);}
    private static Object rethrow(Throwable t){if(t instanceof Error e)throw e;if(t instanceof RuntimeException e)throw e;throw new AssertionError(t);}
    private static int number(Object o,String n){return (Integer)get(o,n);}
    private static boolean flag(Object o,String n){return (Boolean)get(o,n);}
    private static void refused(Runnable r,Object... watched){try{Method m=IndependentPreservationCompletionControls.class.getDeclaredMethod("refusedWithoutEffects",Runnable.class,Object[].class);m.setAccessible(true);m.invoke(null,new Object[]{r,watched});}catch(InvocationTargetException e){rethrow(e.getCause());}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static Object fixture(){try{Class<?> c=Class.forName("dev.mixer.android.IndependentPreservationCompletionControls$Fixture");Constructor<?> init=c.getDeclaredConstructor(boolean.class,boolean.class);init.setAccessible(true);return init.newInstance(true,true);}catch(InvocationTargetException e){return rethrow(e.getCause());}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static final class State {
        final Object fixture;final NativeRenderer renderer;final NativeAppearanceViewsV2.NativeField a,c;final NativeOwnerV2.Fence fence;
        Object candidate,journal,state,member,packet,records;NativeAppearanceViewsV2.FieldPreservation first,second;boolean injected,reported;
        State(Object f){fixture=f;renderer=(NativeRenderer)get(f,"renderer");a=(NativeAppearanceViewsV2.NativeField)get(f,"a");c=(NativeAppearanceViewsV2.NativeField)get(f,"c");fence=(NativeOwnerV2.Fence)get(f,"fence");}
        void capture(){
            if(candidate!=null||a.record.fieldPreservation==null||c.record.fieldPreservation==null)return;
            candidate=get(renderer,"v2Pending");journal=get(candidate,"journal");first=a.record.fieldPreservation;second=c.record.fieldPreservation;
            for(Object s:(Object[])get(journal,"states"))if(get(s,"record")==a.record)state=s;
            check(state!=null&&flag(state,"forwardPreserved")&&first.counted&&second.counted&&number(renderer,"outstandingEditorNativeCalls")==3,"real own forward candidate holds actual A/C plus entered B3");
            member=get(state,"membership");check(member!=null&&get(member,"state")==state&&get(member,"scope")==first,"actual captured original membership retained as oracle");
            packet=get(renderer,"packet");records=get(renderer,"v2Records");
        }
        Object[] watched(){return new Object[]{renderer,fence,candidate,journal,state,member,first,second,a.record,c.record,renderer.cleanupLedger()};}
        void held(int shared){
            check(first.counted&&second.counted&&!first.released&&!second.released,"both genuine original preservation claims retained");
            check(a.record.fieldPreservation==first&&c.record.fieldPreservation==second,"original callback registrations retained");
            check(number(candidate,"heldPreservations")==2&&number(renderer,"outstandingFieldPreservations")==2&&number(renderer,"outstandingEditorNativeCalls")==shared,"exact preservation/candidate/shared tally custody");
            check(!flag(journal,"complete")&&get(renderer,"packet")==packet&&get(renderer,"v2Records")==records,"no success completion or presentation publication");
            check(get(state,"membership")==member&&get(member,"scope")==first&&get(member,"state")==state,"captured original member never replaced");
        }
        void mutate(){
            put(state,"forwardPreserved",false);injected=true;
            // The sole hostile mutation has happened. Both ordinary endpoints must be inert.
            refused(()->a.record.input.fieldPreservationBegin(a.record,first),watched());
            refused(()->a.record.input.fieldPreservationEnd(a.record,first),watched());held(3);
        }
    }
    public static void main(String[] args)throws Exception{
        Field descriptor=IndependentPreservationCompletionControls.class.getDeclaredField("descriptor");descriptor.setAccessible(true);descriptor.set(null,Files.readAllBytes(Path.of(args[1])));
        boolean nativeBoundary=args[0].equals("native");check(nativeBoundary||args[0].equals("commit"),"explicit selected native/commit boundary");
        Object f=fixture();State s=new State(f);Object observer=get(s.renderer,"v2Environment");var original=(NativeEnvironmentV2.Sink)get(observer,"sink");
        NativeEnvironmentV2.Sink reporter=(source,change,cause,primary,fatal)->{if(s.injected&&!s.reported){s.reported=true;s.held(3);check(!flag(s.candidate,"used"),"actual reporter precedes original outer attach failure retirement");if(nativeBoundary)check(flag(s.journal,"failedInvoked")&&number(s.journal,"completion")==3,"native direct own failure claimed before reporting");}original.changed(source,change,cause,primary,fatal);};
        put(observer,"sink",reporter);
        try{
            ConcreteHostProbe.hook=(m,p)->{
                if(m.equals("View.invalidate")&&p.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==s.a)s.capture();
                boolean boundary=nativeBoundary?m.equals("View.invalidate")&&p.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==s.a:m.equals("NativeBridge.commitV2")&&p.equals("beforeReturn");
                if(!s.injected&&s.candidate!=null&&boundary){
                    s.mutate();
                    if(nativeBoundary){boolean refused=false;try{invoke(s.renderer,"completeFailedV2",s.candidate,null,null);}catch(IllegalArgumentException|IllegalStateException expected){refused=true;}check(refused,"first own malformed failed endpoint reports/refuses");throw new IllegalStateException("selected own-forward native exit after failure consumption");}
                }
            };
            boolean returned=false;Throwable escaped=null;try{returned=(Boolean)invoke(f,"edit");}catch(RuntimeException|Error e){escaped=e;}finally{ConcreteHostProbe.hook=null;put(observer,"sink",original);}
            if(escaped instanceof AssertionError failure)throw failure;
            check(s.injected&&s.reported&&!returned&&s.fence.terminal,"selected own-forward cannot authorize success at either boundary");
            check(flag(s.journal,"failedInvoked")&&number(s.journal,"completion")==4,"known-own malformed failed endpoint consumed exactly once");s.held(2);
            if(nativeBoundary)check(flag(s.candidate,"used")&&get(s.renderer,"v2Pending")==null,"unchanged outer attach catch retires failed candidate without success publication");
            else check(!flag(s.candidate,"used"),"commit-side membership refusal has no candidate success consumption");
            check(s.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"actual unproven native custody remains busy");
            if(!nativeBoundary)check(invoke(invoke(get(f,"coordinator"),"cleanupLedger"),"rollback").toString().equals("NOT_REQUESTED"),"engine success followed by malformed membership fabricates no rollback");
            refused(()->invoke(s.renderer,"completeFailedV2",s.candidate,null,null),s.watched());
            refused(()->invoke(s.renderer,"finishV2",s.candidate,s.journal),s.watched());
            // Restore only the exact injected boolean. Consumed endpoint must remain inert.
            put(s.state,"forwardPreserved",true);s.held(2);
            refused(()->invoke(s.renderer,"completeFailedV2",s.candidate,null,null),s.watched());
            refused(()->invoke(s.renderer,"finishV2",s.candidate,s.journal),s.watched());
            Field checks=IndependentPreservationCompletionControls.class.getDeclaredField("checks");checks.setAccessible(true);
            System.out.println("PASS selected exact own-forward "+args[0]+" / "+assertions+" assertions; unchanged-helper="+checks.get(null)+"; sole mutation forwardPreserved true->false->true; held2/busy/FAILED_DONE");
        }finally{ConcreteHostProbe.hook=null;put(observer,"sink",original);invoke(f,"close");}
    }
}
