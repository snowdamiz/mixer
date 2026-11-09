package dev.mixer.android;

import android.text.Editable;
import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import android.widget.FrameLayout;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Independent assertions using R58's fixture construction and the unchanged concrete leaves. */
public final class ReflowBoundaryReview {
    private static int checks,cases;
    private static byte[] descriptorBytes;
    private static final Class<?> FIXTURE;
    static {try {FIXTURE=Class.forName("dev.mixer.android.VerticalReflowHostTests$Fixture");}
        catch(ClassNotFoundException e){throw new ExceptionInInitializerError(e);}}
    private static void check(boolean condition,String message){checks++;if(!condition)throw new AssertionError(message);}
    private static Object get(Object target,String name)throws Exception{
        Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);
    }
    private static Object invoke(Class<?> owner,Object target,String name,Class<?>[] types,Object... args)throws Exception{
        Method m=owner.getDeclaredMethod(name,types);m.setAccessible(true);
        try{return m.invoke(target,args);}catch(InvocationTargetException e){
            if(e.getCause() instanceof Exception x)throw x;if(e.getCause() instanceof Error x)throw x;throw e;}
    }
    private static final class F implements AutoCloseable {
        final Object fixture;final NativeRenderer renderer;final NativeOwnerV2 owner;final EditText edit;final FrameLayout root;
        F(AndroidUIProfile profile,boolean vertical,String change,boolean external)throws Exception{
            Constructor<?> ctor=FIXTURE.getDeclaredConstructors()[0];ctor.setAccessible(true);
            fixture=ctor.newInstance(profile,vertical,change.equals("echo")?"Other buffer":"Inspect","Intro",change,external);
            renderer=(NativeRenderer)get(fixture,"renderer");owner=(NativeOwnerV2)get(fixture,"owner");
            edit=(EditText)get(fixture,"edit");root=(FrameLayout)get(fixture,"root");
        }
        @Override public void close(){((AutoCloseableFixture)()->invoke(FIXTURE,fixture,"close",new Class<?>[0])).close();}
    }
    @FunctionalInterface private interface AutoCloseableFixture {
        void call()throws Exception;
        default void close(){try{call();}catch(Exception e){throw new AssertionError("fixture cleanup",e);}}
    }
    private static byte[] packet(String value,String header)throws Exception{
        return (byte[])invoke(VerticalReflowHostTests.class,null,"packet",
            new Class<?>[]{long.class,boolean.class,String.class,String.class,String.class},2L,true,value,header,"");
    }
    private static NativeRenderer.Candidate candidate(F a,F b,boolean target,boolean foreign)throws Exception{
        return (NativeRenderer.Candidate)invoke(VerticalReflowHostTests.class,null,"candidate",
            new Class<?>[]{FIXTURE,FIXTURE,boolean.class,boolean.class},a.fixture,b.fixture,target,foreign);
    }
    private static Throwable preflight(F a,NativeRenderer.Candidate c)throws Exception{
        return (Throwable)invoke(VerticalReflowHostTests.class,null,"preflight",
            new Class<?>[]{FIXTURE,NativeRenderer.Candidate.class},a.fixture,c);
    }
    private static void boundary(AndroidUIProfile profile,boolean vertical,String change,boolean accept)throws Exception{
        try(F a=new F(profile,vertical,"",false);F b=new F(profile,vertical,
            List.of("binding","order","ancestor","echo").contains(change)?change:"",false)){
            check(a.edit.requestFocus(),"focus");a.edit.setSelection(1,4);
            Editable buffer=a.edit.getText();Object binding=a.renderer.inspectV2().get("field").binding;
            int[] before={a.edit.getLeft(),a.edit.getTop(),a.edit.getRight(),a.edit.getBottom()};
            int x=b.edit.getLeft(),y=b.edit.getTop()+29,w=b.edit.getWidth(),h=b.edit.getHeight()+23;
            if(change.equals("x"))x+=1024;if(change.equals("width"))w+=1024;
            if(change.equals("zeroWidth"))w=0;
            b.edit.layout(x,y,x+w,y+h);
            NativeRenderer.Candidate c=candidate(a,b,change.equals("target"),false);
            ConcreteHostProbe.reset();Throwable failure=preflight(a,c);
            check(accept?failure==null:failure instanceof AppearanceDescriptorV2.Failure,
                profile+"/"+vertical+"/"+change+" expected="+accept+" got="+failure);
            check(a.edit.getText()==buffer&&a.renderer.inspectV2().get("field").binding==binding,"exact buffer/binding");
            check(a.edit.getSelectionStart()==1&&a.edit.getSelectionEnd()==4,"exact selection");
            check(a.edit.getLeft()==before[0]&&a.edit.getTop()==before[1]&&a.edit.getRight()==before[2]&&a.edit.getBottom()==before[3],"exact retained frame");
            check(ConcreteHostProbe.events().stream().noneMatch(e->e.receiver==a.edit&&
                (e.method.startsWith("TextView.set")||e.method.startsWith("View.set")||e.method.equals("View.layout")||e.method.equals("View.measure"))),"preflight did native mutation");
            System.out.println("PASS combined-y-height profile="+profile+" vertical="+vertical+" guard="+change+" admitted="+accept);cases++;
        }
    }
    private static void ownership()throws Exception{
        try(F a=new F(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"",false);
            F b=new F(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"",false)){
            NativeRenderer.Candidate c=candidate(a,b,false,true);ConcreteHostProbe.reset();Throwable failure=null;
            try{a.renderer.attachV2(c,a.root);}catch(RuntimeException e){failure=e;}
            check(failure instanceof IllegalArgumentException&&failure.getMessage().contains("stale/foreign/consumed"),"foreign owner attach");
            check(ConcreteHostProbe.events().stream().noneMatch(e->e.method.equals("View.layout")||e.method.equals("ViewGroup.addView")||e.method.equals("TextView.setText")),"foreign owner native writes");
            System.out.println("PASS foreign owner rejected before native mutation");cases++;
        }
    }
    private static boolean frame(Editable buffer,int cs,int ce,int start,int end,EditText edit){
        return edit.getText()==buffer&&edit.getSelectionStart()==start&&edit.getSelectionEnd()==end&&
            BaseInputConnection.getComposingSpanStart(buffer)==cs&&BaseInputConnection.getComposingSpanEnd(buffer)==ce;
    }
    private static void lateFailure(boolean failRollback)throws Exception{
        try(F a=new F(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"",true)){
            check(a.edit.requestFocus(),"late failure focus");InputConnection ic=a.edit.onCreateInputConnection(new EditorInfo());
            check(ic!=null&&ic.setSelection(0,a.edit.getText().length())&&ic.setComposingText("雪 🌿\nReflow",1),"late composition");
            Editable buffer=a.edit.getText();int cs=BaseInputConnection.getComposingSpanStart(buffer),ce=BaseInputConnection.getComposingSpanEnd(buffer);
            int start=a.edit.getSelectionStart(),end=a.edit.getSelectionEnd(),oldX=a.edit.getLeft(),oldY=a.edit.getTop(),oldW=a.edit.getWidth(),oldH=a.edit.getHeight();
            Object binding=a.renderer.inspectV2().get("field").binding;
            RuntimeException original=new IllegalStateException("r60-original-after-live-Y-move");
            boolean[] observed={false,false};
            if(failRollback)a.renderer.testFaultV2(-1,true);
            ConcreteHostProbe.reset();
            ConcreteHostProbe.hook=(method,phase)->{
                ConcreteHostProbe.Event e=ConcreteHostProbe.lastEvent();
                if(e==null||e.receiver!=a.edit||!method.equals("View.layout")||!phase.equals("beforeReturn"))return;
                boolean restoring=e.productionFrames.stream().anyMatch(s->s.methodName().equals("restoreV2"));
                if(restoring){
                    check(a.edit.getLeft()==oldX&&a.edit.getTop()==oldY&&a.edit.getWidth()==oldW&&a.edit.getHeight()==oldH,"restored exact original frame");
                    check(a.renderer.inspectV2().get("field").binding==binding&&frame(buffer,cs,ce,start,end,a.edit),"restore retained exact buffer/spans/selection/binding");
                    observed[1]=true;
                }else if(!observed[0]&&a.edit.getTop()!=oldY){
                    check(frame(buffer,cs,ce,start,end,a.edit),"new frame already lost editor state");observed[0]=true;throw original;
                }
            };
            Throwable outward=null;
            try{a.owner.installExternal(packet(buffer.toString(),"Intro\nSecond\nThird header line"),descriptorBytes);}
            catch(RuntimeException e){outward=e;}finally{ConcreteHostProbe.hook=null;}
            check(observed[0]&&outward!=null&&!a.owner.hasCommittedPresentation(),"late changed-Y fault reached and failed closed");
            check(a.owner.cleanupLedger().primary()==original,"original primary replaced during attachment/rollback");
            if(!failRollback)check(observed[1],"restoration not observed");
            a.owner.close();check(a.owner.cleanupLedger().primary()==original,"close replaced original primary");
            System.out.println("PASS changed-Y late failure rollbackFailure="+failRollback+" originalPrimaryIdentity=true exactRestorationObserved="+observed[1]);cases++;
        }
    }
    private static void geometry(){
        int maximum=AppearanceGeometryV2.MAXIMUM_EXTENT64;
        check(AppearanceGeometryV2.pixelEdge(maximum,16384)==536870912,"maximum edge without integer wrap");
        for(long[] pair:List.of(new long[]{-1,1},new long[]{maximum,1},new long[]{Long.MAX_VALUE,1})){
            boolean rejected=false;try{NativeAppearanceViewsV2.sum(pair);}catch(AppearanceDescriptorV2.Failure e){rejected=true;}
            check(rejected,"bad/overflow sum admitted");
        }
        for(long value:new long[]{-1,(long)maximum+1,Long.MAX_VALUE}){
            boolean rejected=false;try{AppearanceGeometryV2.pixelEdge(value,16384);}catch(AppearanceGeometryV2.Failure e){rejected=true;}
            check(rejected,"invalid pixel edge admitted");
        }
        System.out.println("PASS geometry checked sums and pixel edges reject out-of-domain/overflow before frame policy");cases++;
    }
    public static void main(String[] args)throws Exception{
        Field descriptor=VerticalReflowHostTests.class.getDeclaredField("descriptor");descriptor.setAccessible(true);descriptor.set(null,Files.readAllBytes(Path.of(args[0])));
        descriptorBytes=Files.readAllBytes(Path.of(args[0]));
        boundary(AndroidUIProfile.LEGACY_HORIZONTAL,false,"none",false);
        boundary(AndroidUIProfile.MEASURED_MULTILINE_V2,false,"none",false);
        boundary(AndroidUIProfile.MEASURED_MULTILINE_V2,true,"none",false);
        boundary(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,false,"none",false);
        boundary(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,"none",true);
        for(String change:List.of("x","width","zeroWidth","binding","order","ancestor","echo","target"))
            boundary(AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,true,change,false);
        ownership();geometry();lateFailure(false);lateFailure(true);
        System.out.println("PASS R60 independent cases="+cases+" assertions="+checks+"; actual candidate renderer; controlled Android/JNI leaves");
    }
}
