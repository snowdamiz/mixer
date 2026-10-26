package dev.mixer.android;

import android.app.Activity;
import android.content.res.Configuration;
import android.os.Build;
import android.widget.FrameLayout;
import java.util.List;
import java.util.function.Consumer;

/** Independent cases against the actual unmodified production reader/Observer. */
public final class IndependentEnvironmentTests {
    private static int cases, assertions;
    private static final class Fatal extends LinkageError { private static final long serialVersionUID=1L; }
    private static void ok(boolean condition,String name) { assertions++; if(!condition)throw new AssertionError(name); }
    private static Throwable failure(Runnable run) { try { run.run(); } catch(RuntimeException|Error e) { return e; } throw new AssertionError("failure expected"); }
    private static final class F implements AutoCloseable {
        final Activity a=new Activity(); final FrameLayout root=new FrameLayout(a); final NativeRenderer renderer=new NativeRenderer();
        NativeEnvironmentV2.Observer observer; int notifications;
        F() { ObserverHostProbe.reset(); renderer.context=a; }
        void construct() { observer=new NativeEnvironmentV2.Observer(a,root,(s,c,rc,p,e)->notifications++); }
        void open() { construct(); observer.register(); observer.bindRenderer(renderer); }
        NativeEnvironmentPlatformV2.Snapshot snapshot() { return NativeEnvironmentPlatformV2.snapshot(a,root); }
        @Override public void close() { if(observer!=null)observer.close(); }
    }
    private static void absent(NativeEnvironmentPlatformV2.Observed<?> o,NativeEnvironmentPlatformV2.Status status,String name) {
        ok(o.status==status,name+" status"); ok(o.value==null,name+" cannot carry value"); ok(o.failure==null,name+" cannot carry exception");
    }
    private static void sdk() {
        for(int sdk=28;sdk<=36;sdk++)try(F f=new F()) {
            Build.VERSION.SDK_INT=sdk;
            var s=f.snapshot();
            var all=List.of(s.frame,s.dark,s.rtl,s.locale,s.density1024,s.bodyProfile,s.insets,s.fontAdjustment,s.contrast,s.highContrast,s.animator);
            for(var o:all)ok((o.status==NativeEnvironmentPlatformV2.Status.KNOWN)==(o.value!=null),"only known value sdk"+sdk);
            if(sdk<30)absent(s.insets,NativeEnvironmentPlatformV2.Status.UNAVAILABLE_SEMANTICS,"exact insets");
            if(sdk<31)absent(s.fontAdjustment,NativeEnvironmentPlatformV2.Status.UNAVAILABLE_API,"font");
            if(sdk<34)absent(s.contrast,NativeEnvironmentPlatformV2.Status.UNAVAILABLE_API,"contrast");
            if(sdk<36)absent(s.highContrast,NativeEnvironmentPlatformV2.Status.UNAVAILABLE_API,"high");
            ok(ObserverHostProbe.calls.isEmpty(),"snapshot no subscription");
            ok(ObserverHostProbe.readCounts.containsKey("contrast")== (sdk>=34),"guard contrast");
            ok(ObserverHostProbe.readCounts.containsKey("high")== (sdk>=36),"guard high");
            ok(ObserverHostProbe.readCounts.containsKey("insets")== (sdk>=30),"guard typed insets");
            if(sdk<36) { ok(failure(f::construct) instanceof AppearanceDescriptorV2.Failure,"closed pre36");ok(ObserverHostProbe.calls.isEmpty(),"closed without add"); }
            cases++;
        }
    }
    private static void originalReadIdentity() {
        for(String field:List.of("config","metrics","locale","token","direction","dp","sp","insets","contrast","high","animator"))try(F f=new F()) {
            f.open(); RuntimeException primary=new SecurityException("independent-"+field);
            ObserverHostProbe.failingRead=field; ObserverHostProbe.readFailure=primary;
            ok(failure(f.observer::capture)==primary,"actual observer primary identity "+field);
            Fatal fatal=new Fatal(); ObserverHostProbe.readFailure=fatal;
            ok(failure(f.observer::capture)==fatal,"fatal observer read identity "+field);
            ObserverHostProbe.failingRead=null; cases++;
        }
    }
    private static void changed(String name,Consumer<F> change) {
        try(F f=new F()) {
            f.open(); var capture=f.observer.capture();
            ObserverHostProbe.readCounts.clear(); change.accept(f);
            ok(!capture.current(f.renderer),"stale complete tuple "+name);
            for(String field:List.of("config","metrics","locale","token","direction","dp","sp","insets","contrast","high","animator"))
                ok(ObserverHostProbe.readCounts.containsKey(field),"second read field "+field+" after "+name);
            cases++;
        }
    }
    private static void completeSecondRead() {
        changed("scheme",f->f.a.getResources().config.uiMode=Configuration.UI_MODE_NIGHT_YES);
        changed("direction",f->f.root.direction=1);
        changed("locale",f->f.a.getResources().config.locales.locale=java.util.Locale.forLanguageTag("ar-EG"));
        changed("density",f->f.a.getResources().metrics.density=2);
        changed("body",f->ObserverHostProbe.sp=21);
        changed("width",f->f.root.width=300); changed("height",f->f.root.height=600);
        changed("top inset",f->f.root.rootInsets.value.top=1); changed("left inset",f->f.root.rootInsets.value.left=1);
        changed("right inset",f->f.root.rootInsets.value.right=1); changed("bottom inset",f->f.root.rootInsets.value.bottom=1);
        changed("root x",f->f.root.x=1); changed("root y",f->f.root.y=1);
        changed("window width",f->f.a.getWindow().getDecorView().width=300);
        changed("window height",f->f.a.getWindow().getDecorView().height=600);
        changed("font undefined",f->f.a.getResources().config.fontWeightAdjustment=Integer.MAX_VALUE);
        changed("font nonzero",f->f.a.getResources().config.fontWeightAdjustment=1);
        changed("negative contrast",f->ObserverHostProbe.contrast=-.5f);
        changed("positive contrast",f->ObserverHostProbe.contrast=.5f);
        changed("nonfinite contrast",f->ObserverHostProbe.contrast=Float.NaN);
        changed("high contrast",f->ObserverHostProbe.highContrast=true);
        changed("reduced motion",f->ObserverHostProbe.animator=0);
        changed("missing animator",f->ObserverHostProbe.animatorMissing=true);
        changed("undefined night",f->f.a.getResources().config.uiMode=0);
        changed("unresolved direction",f->f.root.direction=3);
        changed("empty locale",f->f.a.getResources().config.locales.empty=true);
        for(String field:List.of("config","metrics","locale","direction","dp","sp","insets","contrast","high","animator"))try(F f=new F()) {
            f.open();var capture=f.observer.capture();ObserverHostProbe.failingRead=field;
            ObserverHostProbe.readFailure=new IllegalArgumentException(field);
            ok(!capture.current(f.renderer),"recoverable current false "+field);
            Fatal fatal=new Fatal();ObserverHostProbe.readFailure=fatal;
            ok(failure(()->capture.current(f.renderer))==fatal,"fatal current propagates "+field);
            ObserverHostProbe.failingRead=null;cases++;
        }
        try(F f=new F()) {
            f.open();var capture=f.observer.capture();f.observer.invalidate();ObserverHostProbe.readCounts.clear();
            ok(!capture.current(f.renderer),"generation fenced");ok(ObserverHostProbe.readCounts.isEmpty(),"stale generation avoids reads");cases++;
        }
        try(F f=new F()) {
            f.open();var capture=f.observer.capture();f.root.windowToken=new Object();ObserverHostProbe.readCounts.clear();
            ok(!capture.current(f.renderer),"token fenced");ok(!ObserverHostProbe.readCounts.containsKey("config"),"token short circuit");cases++;
        }
    }
    private static void exactRetainedTargetsAndFreshReads() {
        try(F f=new F()) {
            f.construct();var oldMode=f.a.modes;var oldHigh=f.a.accessibility;var oldExecutor=f.a.executor;
            f.a.modes=new android.app.UiModeManager();f.a.accessibility=new android.view.accessibility.AccessibilityManager();
            f.a.executor=r->{throw new AssertionError("replacement executor must not register");};
            f.observer.register();f.observer.bindRenderer(f.renderer);
            ok(ObserverHostProbe.targets[5]==oldMode&&ObserverHostProbe.targets[6]==oldHigh,"retained manager acquisition");
            ok(ObserverHostProbe.executors[5]==oldExecutor&&ObserverHostProbe.executors[6]==oldExecutor,"retained executors");
            var capture=f.observer.capture();f.a.modes.local=.5f;
            ok(!capture.current(f.renderer),"read replacement manager not constructor target");f.a.modes.local=0;
            f.a.accessibility.local=true;ok(!capture.current(f.renderer),"read replacement accessibility manager");
            f.a.accessibility.local=false;ok(capture.current(f.renderer),"restored complete tuple");
            f.observer.close();ok(ObserverHostProbe.live[5]==null&&ObserverHostProbe.live[6]==null,"removal original exact handles");cases++;
        }
    }
    private static void callbacksAndFailures() {
        for(int slot:new int[]{5,6})for(int phase:new int[]{0,1})try(F f=new F()) {
            f.construct();RuntimeException primary=new IllegalStateException("add "+slot+" "+phase);
            ObserverHostProbe.hooks[phase][slot]=f.observer::close;
            ObserverHostProbe.faults[phase][slot]=primary;
            ok(failure(f.observer::register)==primary,"reentrant throwing add identity");
            ok(f.observer.cleanupLedger().primary()==primary,"ledger primary add");
            for(int acquired=0;acquired<=slot;acquired++)ok(ObserverHostProbe.calls.contains("remove"+acquired),"independent removal "+acquired);
            for(int untouched=slot+1;untouched<8;untouched++)ok(!ObserverHostProbe.calls.contains("add"+untouched),"unattempted later add");
            cases++;
        }
        for(int slot:new int[]{5,6}) {
            F f=new F();f.open();Object listener=ObserverHostProbe.last[slot];f.observer.close();int before=f.notifications;
            ObserverHostProbe.readCounts.clear();
            if(slot==5)((android.app.UiModeManager.ContrastChangeListener)listener).onContrastChanged(1);
            else((android.view.accessibility.AccessibilityManager.HighContrastTextStateChangeListener)listener).onHighContrastTextStateChanged(true);
            ok(f.notifications==before,"retired stale callback silent");ok(ObserverHostProbe.readCounts.isEmpty(),"retired callback no reads");cases++;
        }
        for(int slot:new int[]{5,6}) {
            F f=new F();f.construct();RuntimeException primary=new IllegalStateException("ordinary add");Fatal fatal=new Fatal();
            ObserverHostProbe.faults[1][slot]=primary;ObserverHostProbe.faults[2][0]=fatal;
            ok(failure(f.observer::register)==fatal,"fatal cleanup takes precedence");
            ok(f.observer.cleanupLedger().primary()==primary,"original primary retained");
            ok(f.observer.cleanupLedger().firstFatal()==fatal,"fatal identity retained");
            for(int acquired=0;acquired<=slot;acquired++)ok(ObserverHostProbe.calls.contains("remove"+acquired),"cleanup continues "+acquired);
            cases++;
        }
        for(int slot:new int[]{5,6})for(boolean fatal:new boolean[]{false,true}) {
            F f=new F();f.open();Throwable chosen=fatal?new Fatal():new SecurityException("remove");ObserverHostProbe.faults[2][slot]=chosen;
            ok(failure(f.observer::close)==chosen,"remove failure preserved");ok(f.observer.cleanupLedger().failure(slot)==chosen,"uncertain remove ledger");
            ok(f.observer.cleanupLedger().state(slot)==NativeEnvironmentV2.Observer.FAILED_UNCERTAIN,"uncertain remove state");
            ok(ObserverHostProbe.calls.contains("remove7"),"later cleanup attempted");cases++;
        }
    }
    private static void safeAreaAndNeutrality() {
        try(F f=new F()) {
            f.root.x=10;f.root.y=20;f.root.width=300;f.root.height=600;f.root.direction=1;
            var insets=f.root.rootInsets.value;insets.top=30;insets.left=15;insets.right=20;insets.bottom=30;
            f.open();var safe=f.observer.capture().value.safeArea64();
            ok(safe.top()==640&&safe.leading()==640&&safe.bottom()==640&&safe.trailing()==320,"safe root intersection RTL");cases++;
        }
        try(F f=new F()) {
            f.a.getResources().config.locales.locale=java.util.Locale.ROOT;f.open();
            ok(f.observer.capture().value.localeIdentifier().equals("und"),"und admitted actual result");
            for(float motion:new float[]{0,.25f,1,100}) {ObserverHostProbe.animator=motion;ok(f.observer.capture().value.accessibility().reduceMotion()==(motion==0),"known actual motion");cases++;}
        }
    }
    public static void main(String[] args) { sdk();originalReadIdentity();completeSecondRead();exactRetainedTargetsAndFreshReads();callbacksAndFailures();safeAreaAndNeutrality();System.out.println("PASS independent actual reader/Observer cases="+cases+" assertions="+assertions+"; JVM finite leaves only; native runtime pending"); }
}
