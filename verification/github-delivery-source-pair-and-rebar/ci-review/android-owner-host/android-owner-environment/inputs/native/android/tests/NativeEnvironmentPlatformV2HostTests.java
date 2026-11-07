package dev.mixer.android;

import android.app.Activity;
import android.content.res.Configuration;
import android.os.Build;
import android.widget.FrameLayout;
import java.lang.reflect.Modifier;
import java.lang.reflect.Method;
import java.util.List;
import static dev.mixer.android.NativeEnvironmentPlatformV2.Status.*;

/** Actual reader/Observer, finite faulting framework leaves. No Android runtime claims. */
public final class NativeEnvironmentPlatformV2HostTests {
    private static int cases,checks;
    private static final class Fatal extends LinkageError { private static final long serialVersionUID=1L; }
    private static void check(boolean value,String why) { checks++; if(!value)throw new AssertionError(why); }
    private static Throwable thrown(Runnable action) { try{action.run();}catch(RuntimeException|Error failure){return failure;}throw new AssertionError("expected failure"); }
    private static void status(NativeEnvironmentPlatformV2.Observed<?> value,NativeEnvironmentPlatformV2.Status expected) {
        check(value.status==expected,"status "+value.status+" expected "+expected);
        check((value.value!=null)==(expected==KNOWN),"unknown observation acquired a value");
        check(value.reason!=null&&!value.reason.isEmpty(),"missing reason");
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();
        final FrameLayout root=new FrameLayout(activity);
        final NativeRenderer renderer=new NativeRenderer();
        NativeEnvironmentV2.Observer observer;
        Fixture(){ObserverHostProbe.reset();renderer.context=activity;}
        NativeEnvironmentPlatformV2.Snapshot snapshot(){return NativeEnvironmentPlatformV2.snapshot(activity,root);}
        void open(){observer=new NativeEnvironmentV2.Observer(activity,root,(source,change,cause,primary,fatal)->renderer.environmentInvalidatedV2());observer.register();observer.bindRenderer(renderer);}
        @Override public void close(){if(observer!=null)observer.close();}
    }
    private static void sdkMatrix(){
        for(int sdk=28;sdk<=36;sdk++)try(Fixture f=new Fixture()){
            Build.VERSION.SDK_INT=sdk;NativeEnvironmentPlatformV2.Snapshot s=f.snapshot();
            status(s.frame,KNOWN);status(s.dark,KNOWN);status(s.rtl,KNOWN);status(s.locale,KNOWN);status(s.density1024,KNOWN);status(s.bodyProfile,KNOWN);status(s.animator,KNOWN);
            status(s.insets,sdk<30?UNAVAILABLE_SEMANTICS:KNOWN);status(s.fontAdjustment,sdk<31?UNAVAILABLE_API:KNOWN);
            status(s.contrast,sdk<34?UNAVAILABLE_API:KNOWN);status(s.highContrast,sdk<36?UNAVAILABLE_API:KNOWN);
            check(ObserverHostProbe.calls.isEmpty(),"diagnostics subscribed");
            check(ObserverHostProbe.readCounts.containsKey("insets")== (sdk>=30),"typed insets branch");
            check(ObserverHostProbe.readCounts.containsKey("contrast")== (sdk>=34),"contrast branch");
            check(ObserverHostProbe.readCounts.containsKey("high")== (sdk>=36),"high branch");
            if(sdk<34)check(thrown(()->NativeEnvironmentPlatformV2.contrastListener(f.activity,()->{})) instanceof IllegalStateException,"early contrast handle");
            if(sdk<36){check(thrown(()->NativeEnvironmentPlatformV2.highContrastListener(f.activity,()->{})) instanceof IllegalStateException,"early high handle");check(thrown(f::open) instanceof AppearanceDescriptorV2.Failure,"pre36 admission opened");check(ObserverHostProbe.calls.isEmpty(),"pre36 admission acquired");}
            else{f.open();check(f.observer.capture().current(f.renderer),"known neutral API36");}
            cases++;
        }
    }
    private static void observations(){
        try(Fixture f=new Fixture()){
            for(int night:new int[]{0,48,64}){f.activity.getResources().config.uiMode=night;status(f.snapshot().dark,UNDEFINED);cases++;}
            for(int night:new int[]{Configuration.UI_MODE_NIGHT_NO,Configuration.UI_MODE_NIGHT_YES}){f.activity.getResources().config.uiMode=night;status(f.snapshot().dark,KNOWN);cases++;}
            f.activity.getResources().config.uiMode=Configuration.UI_MODE_NIGHT_NO;
            for(int dir:new int[]{-1,2,3}){f.root.direction=dir;status(f.snapshot().rtl,UNDEFINED);cases++;}f.root.direction=0;
            f.activity.getResources().config.locales.empty=true;status(f.snapshot().locale,UNDEFINED);f.activity.getResources().config.locales.empty=false;cases++;
            f.activity.getResources().config.locales.locale=null;status(f.snapshot().locale,UNDEFINED);cases++;
            f.activity.getResources().config.locales.locale=java.util.Locale.ROOT;status(f.snapshot().locale,KNOWN);check(f.snapshot().locale.value.equals("und"),"und policy changed");cases++;
            for(float value:new float[]{0,-1,Float.NaN,Float.POSITIVE_INFINITY,.124f,16.01f}){f.activity.getResources().metrics.density=value;status(f.snapshot().density1024,UNDEFINED);cases++;}f.activity.getResources().metrics.density=1;
            f.root.rootInsets=null;status(f.snapshot().insets,UNDEFINED);cases++;
            f.root.rootInsets=new android.view.WindowInsets();f.root.rootInsets.value.top=-1;status(f.snapshot().insets,UNDEFINED);cases++;
            f.root.rootInsets.value.top=0;
            f.activity.getResources().config.fontWeightAdjustment=Integer.MAX_VALUE;status(f.snapshot().fontAdjustment,UNDEFINED);cases++;
            f.activity.getResources().config.fontWeightAdjustment=1;status(f.snapshot().fontAdjustment,KNOWN);cases++;
            for(float value:new float[]{-2,2,Float.NaN,Float.NEGATIVE_INFINITY,Float.POSITIVE_INFINITY}){ObserverHostProbe.contrast=value;status(f.snapshot().contrast,UNDEFINED);cases++;}
            for(float value:new float[]{-1,0,1}){ObserverHostProbe.contrast=value;status(f.snapshot().contrast,KNOWN);check(f.snapshot().contrast.value==value,"contrast fabricated");cases++;}
            for(float value:new float[]{-1,Float.NaN,Float.NEGATIVE_INFINITY,Float.POSITIVE_INFINITY}){ObserverHostProbe.animator=value;status(f.snapshot().animator,UNDEFINED);cases++;}
            for(float value:new float[]{0,.25f,1,100}){ObserverHostProbe.animator=value;status(f.snapshot().animator,KNOWN);check(f.snapshot().animator.value==value,"motion fabricated");cases++;}
            ObserverHostProbe.animatorMissing=true;status(f.snapshot().animator,UNDEFINED);cases++;
        }
        for(String invalid:List.of("","\u0000","\u202e","\ud800","\udc00","x".repeat(129),"é".repeat(65))){
            try{Method m=NativeEnvironmentPlatformV2.class.getDeclaredMethod("validLocale",String.class);m.setAccessible(true);check(!(Boolean)m.invoke(null,invalid),"bad Unicode locale accepted");}catch(ReflectiveOperationException e){throw new AssertionError(e);}cases++;
        }
    }
    private static void bodyAndFrame(){
        int[] anchors={896,960,1024,1088,1216,1344,1472,1792,2112,2560,3008,3392};
        try(Fixture f=new Fixture()){
            for(int i=0;i<anchors.length;i++){
                ObserverHostProbe.sp=anchors[i]/64f;check(f.snapshot().bodyProfile.value==i,"body anchor "+i);cases++;
                if(i>0){ObserverHostProbe.sp=(anchors[i]+anchors[i-1])/128f;check(f.snapshot().bodyProfile.value==i,"body tie up "+i);cases++;}
            }
            for(float value:new float[]{13.9f,53.1f,0,-1,Float.NaN,Float.POSITIVE_INFINITY}){ObserverHostProbe.sp=value;status(f.snapshot().bodyProfile,UNDEFINED);cases++;}
            ObserverHostProbe.sp=17;ObserverHostProbe.dp=0;status(f.snapshot().bodyProfile,UNDEFINED);cases++;
            ObserverHostProbe.dp=Float.NaN;status(f.snapshot().bodyProfile,UNDEFINED);cases++;
            f.root.attached=false;status(f.snapshot().frame,UNDEFINED);f.root.attached=true;cases++;
            f.root.windowToken=null;status(f.snapshot().frame,UNDEFINED);cases++;
            f.root.windowToken=new Object();f.root.width=0;status(f.snapshot().frame,UNDEFINED);cases++;
            f.root.width=320;f.activity.destroyed=true;status(f.snapshot().frame,UNDEFINED);cases++;
        }
        try(Fixture f=new Fixture()){
            f.root.x=10;f.root.y=20;f.root.width=200;f.root.height=400;
            f.root.rootInsets.value.top=30;f.root.rootInsets.value.left=15;f.root.rootInsets.value.bottom=10;f.root.rootInsets.value.right=20;
            f.open();AppearanceResolverV2.SafeArea s=f.observer.capture().value.safeArea64();
            check(s.top()==640&&s.leading()==320&&s.bottom()==0&&s.trailing()==0,"root inset intersection changed");cases++;
        }
    }
    private static void failures(){
        for(String source:List.of("config","metrics","locale","token","direction","dp","sp","insets","contrast","high","animator")){
            try(Fixture f=new Fixture()){
                ObserverHostProbe.failingRead=source;ObserverHostProbe.readFailure=new SecurityException(source);
                NativeEnvironmentPlatformV2.Snapshot s=f.snapshot();
                NativeEnvironmentPlatformV2.Observed<?> observed=switch(source){case "config"->s.dark;case "metrics"->s.density1024;case "locale"->s.locale;case "token"->s.frame;case "direction"->s.rtl;case "dp","sp"->s.bodyProfile;case "insets"->s.insets;case "contrast"->s.contrast;case "high"->s.highContrast;default->s.animator;};
                status(observed,READ_FAILED);check(observed.failure==ObserverHostProbe.readFailure,"read failure identity lost");cases++;
                Fatal fatal=new Fatal();ObserverHostProbe.readFailure=fatal;check(thrown(f::snapshot)==fatal,"fatal read demoted: "+source);cases++;
            }
        }
        try(Fixture f=new Fixture()){
            f.open();NativeEnvironmentV2 capture=f.observer.capture();ObserverHostProbe.failingRead="animator";ObserverHostProbe.readFailure=new SecurityException();check(!capture.current(f.renderer),"failed second read current");cases++;
            Fatal fatal=new Fatal();ObserverHostProbe.readFailure=fatal;check(thrown(()->capture.current(f.renderer))==fatal,"current linkage demoted");cases++;
        }
    }
    private static void admissionAndSecondRead(){
        List<java.util.function.Consumer<Fixture>> rejected=List.of(
            f->f.activity.getResources().config.uiMode=0, f->f.root.direction=2,
            f->f.activity.getResources().config.fontWeightAdjustment=Integer.MAX_VALUE,
            f->f.activity.getResources().config.fontWeightAdjustment=1,
            f->ObserverHostProbe.contrast=-1, f->ObserverHostProbe.contrast=1,
            f->ObserverHostProbe.contrast=Float.NaN, f->ObserverHostProbe.highContrast=true,
            f->ObserverHostProbe.animatorMissing=true, f->ObserverHostProbe.animator=-1,
            f->f.root.rootInsets=null, f->f.activity.getResources().config.locales.empty=true);
        for(java.util.function.Consumer<Fixture> mutation:rejected)try(Fixture f=new Fixture()){
            f.open();NativeEnvironmentV2 capture=f.observer.capture();int before=ObserverHostProbe.reads;
            mutation.accept(f);check(!capture.current(f.renderer),"second complete read admitted change");check(ObserverHostProbe.reads>before,"second read bypassed");
            check(thrown(f.observer::capture) instanceof AppearanceDescriptorV2.Failure,"malformed capture admitted");cases++;
        }
        try(Fixture f=new Fixture()){
            ObserverHostProbe.animator=0;f.open();check(f.observer.capture().value.accessibility().reduceMotion(),"known reduced motion lost");cases++;
            NativeEnvironmentV2 capture=f.observer.capture();f.observer.invalidate();int before=ObserverHostProbe.reads;check(!capture.current(f.renderer),"invalid generation current");check(ObserverHostProbe.reads==before,"invalid generation read native");cases++;
        }
        try(Fixture f=new Fixture()){
            f.open();NativeEnvironmentV2 capture=f.observer.capture();f.root.windowToken=new Object();check(!capture.current(f.renderer),"changed token current");cases++;
        }
    }
    private static void targetsAndAuthority(){
        try(Fixture f=new Fixture()){
            java.util.concurrent.Executor executor=f.activity.executor;
            android.app.UiModeManager modes=f.activity.modes;
            android.view.accessibility.AccessibilityManager accessibility=f.activity.accessibility;
            f.observer=new NativeEnvironmentV2.Observer(f.activity,f.root,(s,c,rc,p,e)->{});
            f.activity.executor=command->{throw new AssertionError("replacement executor");};
            f.activity.modes=new android.app.UiModeManager();f.activity.accessibility=new android.view.accessibility.AccessibilityManager();
            f.observer.register();f.observer.bindRenderer(f.renderer);
            check(ObserverHostProbe.targets[5]==modes&&ObserverHostProbe.targets[6]==accessibility,"registration target replaced");
            check(ObserverHostProbe.executors[5]==executor&&ObserverHostProbe.executors[6]==executor,"registration executor replaced");
            f.observer.close();check(ObserverHostProbe.live[5]==null&&ObserverHostProbe.live[6]==null,"exact target not removed");cases++;
        }
        for(var constructor:NativeEnvironmentV2.class.getDeclaredConstructors())check(Modifier.isPrivate(constructor.getModifiers()),"capture constructor exposed");
        for(Class<?> type:List.of(NativeEnvironmentPlatformV2.Snapshot.class,NativeEnvironmentPlatformV2.Observed.class)){
            for(var field:type.getDeclaredFields())check(Modifier.isFinal(field.getModifiers()),"mutable diagnostic field");
            for(var constructor:type.getDeclaredConstructors())check(Modifier.isPrivate(constructor.getModifiers()),"diagnostic construction exposed");
        }
        cases++;
    }
    public static void main(String[] args){sdkMatrix();observations();bodyAndFrame();failures();admissionAndSecondRead();targetsAndAuthority();System.out.println("PASS actual platform/Observer host cases="+cases+" assertions="+checks+"; SDK28..36 finite leaves only; native linkage/runtime pending");}
}
